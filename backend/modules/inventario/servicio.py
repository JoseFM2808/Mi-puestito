"""Reglas de Inventario (ADR-031): todo cambio de stock es un movimiento.

`registrar_movimiento` es la ÚNICA función que toca `stock_actual`, y lo hace
con un incremento atómico en SQL (`stock_actual = stock_actual + :delta`),
nunca leyendo el valor en Python para escribirlo después: así dos ventas
simultáneas no se pisan aunque la base no fuera SQLite con BEGIN IMMEDIATE.
"""

from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from fechas import momento_de_operacion

from .models import MotivoMovimiento, MovimientoInventario, Producto, Unidad
from .schemas import AjusteEntrada, MermaEntrada, ProductoCambios, ProductoEntrada


class ErrorDeInventario(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


UNIDAD_TEXTO = {Unidad.UNIDAD: "unid.", Unidad.KG: "kg", Unidad.LITRO: "L"}


def cantidad_legible(producto: Producto, cantidad: Decimal) -> str:
    return f"{cantidad.normalize():f} {UNIDAD_TEXTO[producto.unidad]}"


def buscar_producto(sesion: Session, uuid: str) -> Producto:
    producto = sesion.scalar(select(Producto).where(Producto.uuid == uuid))
    if producto is None:
        raise ErrorDeInventario("No encontramos ese producto.", 404)
    return producto


def registrar_movimiento(
    sesion: Session,
    producto: Producto,
    delta: Decimal,
    motivo: MotivoMovimiento,
    origen_tipo: str,
    origen_ref: str,
    nota: str | None = None,
    ocurrido_en=None,
) -> tuple[MovimientoInventario, bool]:
    """Inserta el movimiento y ajusta la caché de stock en la misma transacción.

    Idempotente por (origen_tipo, origen_ref): si ya se aplicó, no hace nada.
    Devuelve (movimiento, fue_nuevo).
    """
    existente = sesion.scalar(
        select(MovimientoInventario).where(
            MovimientoInventario.origen_tipo == origen_tipo,
            MovimientoInventario.origen_ref == origen_ref,
        )
    )
    if existente is not None:
        return existente, False

    movimiento = MovimientoInventario(
        producto_id=producto.id,
        delta=delta,
        motivo=motivo,
        origen_tipo=origen_tipo,
        origen_ref=origen_ref,
        nota=nota,
        creado_en=momento_de_operacion(ocurrido_en),
    )
    sesion.add(movimiento)
    sesion.flush()  # la restricción única salta aquí si hubo carrera en PostgreSQL
    sesion.execute(
        update(Producto)
        .where(Producto.id == producto.id)
        .values(stock_actual=Producto.stock_actual + delta)
        .execution_options(synchronize_session=False)
    )
    sesion.refresh(producto)
    return movimiento, True


def aviso_si_negativo(producto: Producto) -> list[str]:
    if producto.stock_actual < 0:
        return [
            f"Según el sistema, {producto.nombre} quedó en "
            f"{cantidad_legible(producto, producto.stock_actual)}. "
            "La venta se guardó; cuando puedas, cuenta cuánto hay de verdad."
        ]
    return []


# ---------------------------------------------------------------- productos

def crear_producto(sesion: Session, datos: ProductoEntrada) -> tuple[Producto, bool]:
    existente = sesion.scalar(select(Producto).where(Producto.uuid == datos.uuid))
    if existente is not None:
        return existente, False
    if sesion.scalar(select(Producto.id).where(func.lower(Producto.nombre) == datos.nombre.lower())):
        raise ErrorDeInventario(f"Ya existe un producto llamado «{datos.nombre}».")
    if datos.codigo_barras and sesion.scalar(
        select(Producto.id).where(Producto.codigo_barras == datos.codigo_barras)
    ):
        raise ErrorDeInventario("Ese código de barras ya es de otro producto.")

    producto = Producto(
        uuid=datos.uuid,
        nombre=datos.nombre,
        codigo_barras=datos.codigo_barras,
        unidad=datos.unidad,
        precio_venta=datos.precio_venta,
        stock_minimo=datos.stock_minimo,
        tiene_vencimiento=datos.tiene_vencimiento,
        creado_en=momento_de_operacion(datos.ocurrido_en),
    )
    sesion.add(producto)
    sesion.flush()
    if datos.stock_inicial:
        registrar_movimiento(
            sesion, producto, datos.stock_inicial, MotivoMovimiento.AJUSTE,
            "stock_inicial", producto.uuid, "Stock al registrar el producto", datos.ocurrido_en,
        )
    sesion.commit()
    return producto, True


def editar_producto(sesion: Session, uuid: str, cambios: ProductoCambios) -> Producto:
    """Datos maestros (precio, mínimo, nombre): gana la última edición.

    El stock NO se edita aquí: se corrige con un ajuste (conteo físico).
    """
    producto = buscar_producto(sesion, uuid)
    for campo in ("nombre", "precio_venta", "stock_minimo", "codigo_barras", "tiene_vencimiento"):
        valor = getattr(cambios, campo)
        if valor is not None:
            setattr(producto, campo, valor)
    sesion.commit()
    return producto


# ---------------------------------------------------------------- ajustes

def ajustar_por_conteo(sesion: Session, datos: AjusteEntrada) -> tuple[Producto, Decimal]:
    """El operador contó lo que hay: el delta se calcula en el servidor, con
    el candado de escritura tomado, contra el stock de ESE momento."""
    producto = buscar_producto(sesion, datos.producto_uuid)
    ya = sesion.scalar(
        select(MovimientoInventario).where(
            MovimientoInventario.origen_tipo == "ajuste",
            MovimientoInventario.origen_ref == datos.uuid,
        )
    )
    if ya is not None:
        return producto, ya.delta

    delta = datos.contado - producto.stock_actual
    if delta != 0:
        registrar_movimiento(
            sesion, producto, delta, MotivoMovimiento.AJUSTE, "ajuste", datos.uuid,
            datos.nota or "Conteo físico", datos.ocurrido_en,
        )
    sesion.commit()
    return producto, delta


def registrar_merma(sesion: Session, datos: MermaEntrada) -> Producto:
    producto = buscar_producto(sesion, datos.producto_uuid)
    registrar_movimiento(
        sesion, producto, -datos.cantidad, MotivoMovimiento.MERMA, "merma", datos.uuid,
        datos.nota, datos.ocurrido_en,
    )
    sesion.commit()
    return producto


def conciliar(sesion: Session) -> list[tuple[Producto, Decimal]]:
    """Productos cuya caché de stock no coincide con Σ movimientos.

    Debe devolver siempre []. Si no, algo escribió stock sin movimiento.
    """
    sumas = dict(
        sesion.execute(
            select(MovimientoInventario.producto_id, func.sum(MovimientoInventario.delta))
            .group_by(MovimientoInventario.producto_id)
        ).all()
    )
    descuadrados = []
    for producto in sesion.scalars(select(Producto)).all():
        # SUM hereda el tipo Cantidad: ya viene en unidades, no en milésimas
        calculado = Decimal(sumas.get(producto.id) or 0)
        if calculado != producto.stock_actual:
            descuadrados.append((producto, calculado))
    return descuadrados


# ---------------------------------------------------------------- eventos de Ventas

def al_vender_item(sesion: Session, datos: dict) -> list[str]:
    """Suscriptor de "venta.item_registrado": descuenta del stock."""
    if not datos.get("producto_uuid") or not datos.get("cantidad"):
        return []  # venta sin inventario: nada que descontar
    producto = sesion.scalar(select(Producto).where(Producto.uuid == datos["producto_uuid"]))
    if producto is None:
        return [f"«{datos['nombre_producto']}» no está en el inventario: no se descontó stock."]
    registrar_movimiento(
        sesion, producto, -datos["cantidad"], MotivoMovimiento.VENTA,
        "item_venta", datos["item_uuid"],
    )
    return aviso_si_negativo(producto)


def al_recibir_compra(sesion: Session, datos: dict) -> list[str]:
    """Suscriptor de "compra.item_recibido": suma al stock lo que llegó.

    Compras habla por nombre (el nombre del producto es único en el sistema). Sin
    cantidad no se mueve nada: "2 packs" no dice cuántas unidades son, y no se adivina.
    """
    if not datos.get("cantidad"):
        return []
    producto = sesion.scalar(
        select(Producto).where(func.lower(Producto.nombre) == datos["nombre_producto"].lower())
    )
    if producto is None:
        return [f"«{datos['nombre_producto']}» no está en el inventario: no se sumó al stock."]
    registrar_movimiento(
        sesion, producto, datos["cantidad"], MotivoMovimiento.COMPRA,
        "item_compra", datos["item_uuid"], ocurrido_en=datos.get("ocurrido_en"),
    )
    return []


def al_anular_item(sesion: Session, datos: dict) -> list[str]:
    """Suscriptor de "venta.item_anulado": devuelve al stock lo descontado."""
    if not datos.get("producto_uuid") or not datos.get("cantidad"):
        return []
    producto = sesion.scalar(select(Producto).where(Producto.uuid == datos["producto_uuid"]))
    vendido = sesion.scalar(
        select(MovimientoInventario).where(
            MovimientoInventario.origen_tipo == "item_venta",
            MovimientoInventario.origen_ref == datos["item_uuid"],
        )
    )
    if producto is None or vendido is None:
        return []  # nunca se descontó: nada que devolver
    registrar_movimiento(
        sesion, producto, -vendido.delta, MotivoMovimiento.ANULACION_VENTA,
        "item_venta_anulado", datos["item_uuid"],
    )
    return []
