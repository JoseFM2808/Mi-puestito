"""Reglas de negocio de Compras (docs/03-modulos/Modulo-Compras.md).

Principios que este archivo hace cumplir:

1. **Idempotencia (ADR-032):** cada operación trae el `uuid` del dispositivo; la
   cola offline puede reenviar sin duplicar. La recepción no lleva uuid propio: es
   idempotente porque un producto ya confirmado no vuelve a aplicarse.
2. **Totales en el servidor:** `monto_total` es Σ items y `monto_real` es Σ lo
   efectivamente recibido, calculados aquí, nunca recibidos del cliente.
3. **Una recepción confirmada no se reescribe:** ya movió stock. Reenviarla igual no
   hace nada; cambiarla da 409 (se corrige con un ajuste de Inventario).
4. **Independencia:** Compras solo anuncia `compra.item_recibido`; si Inventario no
   está o falla, la recepción se guarda igual (eventos.py).
"""

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

import eventos
from fechas import momento_de_operacion

from .models import (
    AliasProveedor,
    EstadoOrdenCompra,
    EstadoRecepcion,
    ItemOrdenCompra,
    OrdenCompra,
    Proveedor,
)
from .schemas import (
    CambioEstadoEntrada,
    OrdenCompraSalida,
    OrdenEntrada,
    ProductoFrecuente,
    ProveedorEntrada,
    RecepcionEntrada,
)

CERO = Decimal("0.00")
# Órdenes recientes que se miran para sugerir productos
ORDENES_PARA_SUGERIR = 30
MAX_FRECUENTES = 10

_AVANCE = [EstadoOrdenCompra.BORRADOR, EstadoOrdenCompra.PENDIENTE, EstadoOrdenCompra.EN_CAMINO]
_POR_RECIBIR = {EstadoOrdenCompra.PENDIENTE, EstadoOrdenCompra.EN_CAMINO}


class ErrorDeCompra(Exception):
    """Error de negocio con mensaje para el operador y código HTTP."""

    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# ---------------------------------------------------------------- proveedores

def _por_uuid(sesion: Session, uuid: str) -> Proveedor | None:
    """Por su uuid o por el de un alias: un pedido hecho sin red puede usar cualquiera."""
    proveedor = sesion.scalar(select(Proveedor).where(Proveedor.uuid == uuid))
    if proveedor is not None:
        return proveedor
    alias = sesion.get(AliasProveedor, uuid)
    return sesion.get(Proveedor, alias.proveedor_id) if alias else None


def buscar_proveedor(sesion: Session, uuid: str) -> Proveedor:
    proveedor = _por_uuid(sesion, uuid)
    if proveedor is None:
        raise ErrorDeCompra("No encontramos a ese proveedor.", 404)
    return proveedor


def consulta_proveedores(busqueda: str | None):
    """Por nombre, empresa o RUC, en orden alfabético."""
    consulta = select(Proveedor).order_by(Proveedor.nombre)
    if busqueda and busqueda.strip():
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Proveedor.nombre).like(patron),
                func.lower(Proveedor.empresa).like(patron),
                Proveedor.ruc.like(patron),
            )
        )
    return consulta


def crear_proveedor(sesion: Session, datos: ProveedorEntrada) -> tuple[Proveedor, bool]:
    existente = _por_uuid(sesion, datos.uuid)
    if existente is not None:
        return existente, False
    if datos.ruc:
        con_ruc = sesion.scalar(select(Proveedor).where(Proveedor.ruc == datos.ruc))
        if con_ruc is not None:
            # El RUC identifica a la empresa: es el mismo proveedor registrado dos veces (D-25)
            momento = momento_de_operacion(datos.ocurrido_en)
            sesion.add(AliasProveedor(uuid=datos.uuid, proveedor_id=con_ruc.id, creado_en=momento))
            sesion.commit()
            return con_ruc, False
    proveedor = Proveedor(
        uuid=datos.uuid,
        nombre=datos.nombre,
        empresa=datos.empresa,
        ruc=datos.ruc,
        telefono=datos.telefono or None,
        categoria=datos.categoria or None,
        creado_en=momento_de_operacion(datos.ocurrido_en),
    )
    sesion.add(proveedor)
    sesion.commit()
    return proveedor, True


def productos_frecuentes(sesion: Session, proveedor_uuid: str) -> list[ProductoFrecuente]:
    """Lo que más se le pide, según sus últimas órdenes (lo más reciente manda el monto)."""
    proveedor = buscar_proveedor(sesion, proveedor_uuid)
    ordenes = sesion.scalars(
        select(OrdenCompra)
        .where(OrdenCompra.proveedor_id == proveedor.id, OrdenCompra.estado != EstadoOrdenCompra.BORRADOR)
        .options(selectinload(OrdenCompra.items))
        .order_by(OrdenCompra.creado_en.desc(), OrdenCompra.id.desc())
        .limit(ORDENES_PARA_SUGERIR)
    ).all()
    por_nombre: dict[str, ProductoFrecuente] = {}
    for orden in ordenes:
        for item in orden.items:
            clave = item.nombre_producto.lower()
            if clave in por_nombre:
                por_nombre[clave].veces += 1
            else:
                por_nombre[clave] = ProductoFrecuente(
                    nombre_producto=item.nombre_producto, cantidad=item.cantidad, monto=item.monto, veces=1
                )
    # sorted es estable: a igual frecuencia queda primero lo pedido más recientemente
    return sorted(por_nombre.values(), key=lambda p: -p.veces)[:MAX_FRECUENTES]


# ---------------------------------------------------------------- órdenes

def buscar_orden(sesion: Session, uuid: str) -> OrdenCompra:
    orden = sesion.scalar(
        select(OrdenCompra)
        .where(OrdenCompra.uuid == uuid)
        .options(selectinload(OrdenCompra.items), selectinload(OrdenCompra.proveedor))
    )
    if orden is None:
        raise ErrorDeCompra("No encontramos ese pedido.", 404)
    return orden


def a_salida(orden: OrdenCompra) -> OrdenCompraSalida:
    return OrdenCompraSalida(
        uuid=orden.uuid,
        proveedor_uuid=orden.proveedor.uuid,
        proveedor=orden.proveedor.nombre,
        proveedor_telefono=orden.proveedor.telefono,
        estado=orden.estado,
        fecha_estimada_llegada=orden.fecha_estimada_llegada,
        monto_total=orden.monto_total,
        monto_real=orden.monto_real,
        notas=orden.notas,
        items=orden.items,
    )


def crear_orden(sesion: Session, datos: OrdenEntrada) -> tuple[OrdenCompra, bool]:
    if sesion.scalar(select(OrdenCompra.id).where(OrdenCompra.uuid == datos.uuid)) is not None:
        return buscar_orden(sesion, datos.uuid), False
    proveedor = buscar_proveedor(sesion, datos.proveedor_uuid)
    momento = momento_de_operacion(datos.ocurrido_en)
    orden = OrdenCompra(
        uuid=datos.uuid,
        proveedor=proveedor,
        estado=EstadoOrdenCompra(datos.estado),
        fecha_estimada_llegada=datos.fecha_estimada_llegada,
        monto_total=sum((item.monto for item in datos.items), CERO),
        notas=datos.notas or None,
        creado_en=momento,
        actualizado_en=momento,
        items=[
            ItemOrdenCompra(
                uuid=item.uuid,
                nombre_producto=item.nombre_producto,
                cantidad=item.cantidad or None,
                monto=item.monto,
            )
            for item in datos.items
        ],
    )
    sesion.add(orden)
    sesion.commit()
    return orden, True


def cambiar_estado(sesion: Session, uuid: str, datos: CambioEstadoEntrada) -> OrdenCompra:
    """Solo hacia adelante. Repetir el mismo estado no hace nada (reintento de la cola)."""
    orden = buscar_orden(sesion, uuid)
    nuevo = EstadoOrdenCompra(datos.estado)
    if orden.estado == nuevo:
        return orden
    if orden.estado not in _AVANCE or _AVANCE.index(nuevo) < _AVANCE.index(orden.estado):
        raise ErrorDeCompra("Ese pedido ya avanzó: no se puede volver atrás.")
    orden.estado = nuevo
    sesion.commit()
    return orden


def _misma_confirmacion(item: ItemOrdenCompra, entrada) -> bool:
    return (
        item.estado_recepcion == entrada.estado
        and item.producto_sustituto == entrada.producto_sustituto
        and item.monto_sustituto == entrada.monto_sustituto
    )


def monto_recibido(orden: OrdenCompra) -> Decimal:
    """Lo que hay que pagar por lo que llegó de verdad (Σ recibido + Σ sustitutos)."""
    total = CERO
    for item in orden.items:
        if item.estado_recepcion == EstadoRecepcion.RECIBIDO:
            total += item.monto
        elif item.estado_recepcion == EstadoRecepcion.CAMBIADO:
            total += item.monto_sustituto or CERO
    return total


def registrar_recepcion(
    sesion: Session, uuid: str, datos: RecepcionEntrada
) -> tuple[OrdenCompra, list[str]]:
    """Checklist de llegada. Los productos dejados en "pendiente" pueden confirmarse después."""
    orden = buscar_orden(sesion, uuid)
    if orden.estado == EstadoOrdenCompra.BORRADOR:
        raise ErrorDeCompra("Ese pedido aún es un borrador: confírmalo antes de recibirlo.")

    por_uuid = {item.uuid: item for item in orden.items}
    faltantes = [e.item_uuid for e in datos.items if e.item_uuid not in por_uuid]
    if faltantes:
        raise ErrorDeCompra("Uno de los productos no es de este pedido.", 404)

    avisos: list[str] = []
    for entrada in datos.items:
        item = por_uuid[entrada.item_uuid]
        if entrada.estado == EstadoRecepcion.PENDIENTE:
            if item.estado_recepcion != EstadoRecepcion.PENDIENTE:
                raise ErrorDeCompra(f"«{item.nombre_producto}» ya se confirmó: no puede volver a pendiente.")
            continue
        if item.estado_recepcion != EstadoRecepcion.PENDIENTE:
            if _misma_confirmacion(item, entrada):
                continue  # reintento de la cola: ya se aplicó, stock incluido
            raise ErrorDeCompra(f"«{item.nombre_producto}» ya se confirmó de otra manera.")

        item.estado_recepcion = entrada.estado
        item.producto_sustituto = entrada.producto_sustituto
        item.monto_sustituto = entrada.monto_sustituto
        if entrada.estado == EstadoRecepcion.NO_RECIBIDO:
            continue
        sesion.flush()
        cambiado = entrada.estado == EstadoRecepcion.CAMBIADO
        avisos += eventos.publicar(
            sesion,
            "compra.item_recibido",
            item_uuid=item.uuid,
            nombre_producto=item.producto_sustituto if cambiado else item.nombre_producto,
            cantidad=entrada.cantidad_stock,
            monto=item.monto_sustituto if cambiado else item.monto,
            ocurrido_en=datos.ocurrido_en,
        )

    if orden.estado in _POR_RECIBIR:
        orden.monto_real = monto_recibido(orden)
        if all(item.estado_recepcion != EstadoRecepcion.PENDIENTE for item in orden.items):
            orden.estado = EstadoOrdenCompra.RECIBIDA
    sesion.commit()
    return orden, avisos


def cerrar_orden(sesion: Session, uuid: str) -> OrdenCompra:
    """Cuenta saldada: de Recibida a Cerrada. Cerrar dos veces no hace nada."""
    orden = buscar_orden(sesion, uuid)
    if orden.estado == EstadoOrdenCompra.CERRADA:
        return orden
    if orden.estado != EstadoOrdenCompra.RECIBIDA:
        raise ErrorDeCompra("Solo se cierra un pedido que ya llegó.")
    orden.estado = EstadoOrdenCompra.CERRADA
    sesion.commit()
    return orden
