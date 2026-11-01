"""Reglas de negocio de Ventas (docs/03-modulos/Modulo-Ventas.md).

Principios que este archivo hace cumplir:

1. **Idempotencia (ADR-032):** cada operación trae el `uuid` generado en la
   tablet. Si ya existe, se devuelve lo existente: reenviar no duplica.
2. **Totales en el servidor (D-11):** `monto_total` de una orden activa o
   fiado es SIEMPRE Σ items, recalculado en la misma transacción.
3. **Lo que ya ocurrió no se rechaza:** una venta es un hecho físico. Si
   supera el límite de crédito o deja el stock negativo, se guarda igual y se
   devuelve un aviso. Solo se rechaza lo que es un error de captura (formalizar
   con un detalle que no cuadra) o una transición imposible.
4. **Deuda derivada:** Σ ventas fiadas − Σ abonos, nunca un saldo guardado.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import eventos
from fechas import momento_de_operacion

from .models import Cliente, EstadoVenta, ItemVenta, MetodoPago, Pago, TipoVenta, Venta
from .schemas import (
    AbonoEntrada,
    ClienteCambios,
    ClienteEntrada,
    CobroEntrada,
    FiarEntrada,
    ItemEntrada,
    VentaEntrada,
    VentaSalida,
)

CERO = Decimal("0.00")


class ErrorDeVenta(Exception):
    """Error de negocio con mensaje para el operador y código HTTP."""

    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def soles(monto: Decimal) -> str:
    return f"S/ {monto:.2f}"


# ---------------------------------------------------------------- consultas

def buscar_cliente(sesion: Session, uuid: str) -> Cliente:
    cliente = sesion.scalar(select(Cliente).where(Cliente.uuid == uuid))
    if cliente is None:
        raise ErrorDeVenta("No encontramos a ese cliente.", 404)
    return cliente


def buscar_venta(sesion: Session, uuid: str) -> Venta:
    venta = sesion.scalar(
        select(Venta).where(Venta.uuid == uuid).options(selectinload(Venta.items))
    )
    if venta is None:
        raise ErrorDeVenta("No encontramos esa venta.", 404)
    return venta


def deuda_de(sesion: Session, cliente_id: int) -> Decimal:
    """Σ ventas fiadas − Σ abonos a cuenta. Negativo = saldo a favor."""
    fiado = sesion.scalar(
        select(func.coalesce(func.sum(Venta.monto_total), 0)).where(
            Venta.cliente_id == cliente_id, Venta.estado == EstadoVenta.FIADA
        )
    )
    abonos = sesion.scalar(
        select(func.coalesce(func.sum(Pago.monto), 0)).where(
            Pago.cliente_id == cliente_id, Pago.venta_id.is_(None)
        )
    )
    # SUM hereda el tipo Dinero de la columna: SQLAlchemy ya devuelve soles
    return Decimal(fiado or 0) - Decimal(abonos or 0)


def deudas_por_cliente(sesion: Session) -> dict[int, Decimal]:
    """Deuda de cada cliente con fiado, en dos consultas agregadas (sin N+1)."""
    fiado = dict(
        sesion.execute(
            select(Venta.cliente_id, func.sum(Venta.monto_total))
            .where(Venta.estado == EstadoVenta.FIADA)
            .group_by(Venta.cliente_id)
        ).all()
    )
    abonos = dict(
        sesion.execute(
            select(Pago.cliente_id, func.sum(Pago.monto))
            .where(Pago.cliente_id.is_not(None), Pago.venta_id.is_(None))
            .group_by(Pago.cliente_id)
        ).all()
    )
    return {
        cliente_id: Decimal(fiado.get(cliente_id) or 0) - Decimal(abonos.get(cliente_id) or 0)
        for cliente_id in set(fiado) | set(abonos)
    }


def a_salida_con_deudas(venta: Venta, deudas: dict[int, Decimal]) -> VentaSalida:
    """Venta para la API, con la deuda del cliente tomada de `deudas`
    (calculadas una sola vez para toda una lista: sin N+1)."""
    cliente = venta.cliente
    deuda = None
    if cliente is not None and venta.tipo == TipoVenta.FIADO:
        deuda = deudas.get(cliente.id, CERO)
    return VentaSalida(
        uuid=venta.uuid,
        tipo=venta.tipo,
        cliente_uuid=cliente.uuid if cliente else None,
        cliente_nombre=cliente.nombre if cliente else None,
        nombre_orden=venta.nombre_orden,
        estado=venta.estado,
        monto_total=venta.monto_total,
        metodo_pago=venta.metodo_pago,
        abierta_en=venta.abierta_en,
        cerrada_en=venta.cerrada_en,
        items=venta.items,
        deuda_cliente=deuda,
    )


def a_salida(sesion: Session, venta: Venta) -> VentaSalida:
    deudas = {venta.cliente.id: deuda_de(sesion, venta.cliente.id)} if venta.cliente else {}
    return a_salida_con_deudas(venta, deudas)


# ---------------------------------------------------------------- clientes

def crear_cliente(sesion: Session, datos: ClienteEntrada) -> tuple[Cliente, bool]:
    existente = sesion.scalar(select(Cliente).where(Cliente.uuid == datos.uuid))
    if existente is not None:
        return existente, False
    cliente = Cliente(
        uuid=datos.uuid,
        nombre=datos.nombre,
        telefono=datos.telefono,
        limite_credito=datos.limite_credito,
        creado_en=momento_de_operacion(datos.ocurrido_en),
    )
    sesion.add(cliente)
    sesion.commit()
    return cliente, True


def editar_cliente(sesion: Session, uuid: str, cambios: ClienteCambios) -> Cliente:
    """Datos maestros: gana la última edición (LWW, ADR-031)."""
    cliente = buscar_cliente(sesion, uuid)
    if cambios.nombre is not None:
        cliente.nombre = cambios.nombre
    if cambios.telefono is not None:
        cliente.telefono = cambios.telefono or None
    if cambios.quitar_limite:
        cliente.limite_credito = None
    elif cambios.limite_credito is not None:
        cliente.limite_credito = cambios.limite_credito
    sesion.commit()
    return cliente


# ---------------------------------------------------------------- ventas

def crear_venta(sesion: Session, datos: VentaEntrada) -> tuple[Venta, bool]:
    existente = sesion.scalar(select(Venta).where(Venta.uuid == datos.uuid))
    if existente is not None:
        if existente.tipo != datos.tipo:
            raise ErrorDeVenta("Ese código de venta ya se usó para otra venta.", 409)
        return existente, False

    cliente = buscar_cliente(sesion, datos.cliente_uuid) if datos.cliente_uuid else None
    if datos.tipo == TipoVenta.FIADO and cliente is None:
        raise ErrorDeVenta("Para fiar hay que elegir a qué cliente.", 422)

    momento = momento_de_operacion(datos.ocurrido_en)
    venta = Venta(
        uuid=datos.uuid,
        tipo=datos.tipo,
        cliente=cliente,
        nombre_orden=datos.nombre_orden,
        abierta_en=momento,
    )

    if datos.tipo == TipoVenta.VENTA_RAPIDA:
        # Solo monto: se cobra en el acto y el detalle se completa después
        if datos.monto is None:
            raise ErrorDeVenta("La venta rápida necesita el monto cobrado.", 422)
        metodo = datos.metodo_pago or MetodoPago.EFECTIVO
        venta.estado = EstadoVenta.PENDIENTE_FORMALIZAR
        venta.monto_total = datos.monto
        venta.metodo_pago = metodo
        venta.cerrada_en = momento
        venta.pagos.append(Pago(uuid=datos.uuid, monto=datos.monto, metodo_pago=metodo, creado_en=momento))
    elif datos.monto is not None:
        raise ErrorDeVenta("El monto de una orden se calcula con sus productos.", 422)

    sesion.add(venta)
    sesion.commit()
    return venta, True


def _recalcular_total(venta: Venta) -> None:
    # La venta rápida conserva el monto cobrado; las demás son Σ items (D-11)
    if venta.tipo != TipoVenta.VENTA_RAPIDA:
        venta.monto_total = sum((item.monto for item in venta.items), CERO)


def agregar_item(sesion: Session, venta_uuid: str, datos: ItemEntrada) -> tuple[Venta, list[str]]:
    venta = buscar_venta(sesion, venta_uuid)
    existente = sesion.scalar(select(ItemVenta).where(ItemVenta.uuid == datos.uuid))
    if existente is not None:
        if existente.venta_id != venta.id:
            raise ErrorDeVenta("Ese código de producto ya se usó en otra venta.", 409)
        return venta, []

    if venta.estado not in (EstadoVenta.ABIERTA, EstadoVenta.PENDIENTE_FORMALIZAR):
        raise ErrorDeVenta("Esta venta ya se cerró: abre una nueva para seguir vendiendo.")
    if datos.producto_uuid and datos.cantidad_num is None:
        raise ErrorDeVenta("Para descontar del inventario falta la cantidad.", 422)

    item = ItemVenta(
        uuid=datos.uuid,
        nombre_producto=datos.nombre_producto,
        cantidad=datos.cantidad,
        monto=datos.monto,
        producto_uuid=datos.producto_uuid,
        cantidad_num=datos.cantidad_num,
    )
    venta.items.append(item)
    _recalcular_total(venta)
    sesion.flush()

    avisos = eventos.publicar(
        sesion,
        "venta.item_registrado",
        item_uuid=item.uuid,
        producto_uuid=item.producto_uuid,
        cantidad=item.cantidad_num,
        nombre_producto=item.nombre_producto,
    )
    sesion.commit()
    return venta, avisos


def quitar_item(sesion: Session, venta_uuid: str, item_uuid: str) -> tuple[Venta, list[str]]:
    """Corregir una orden abierta. Idempotente: quitar dos veces no falla."""
    venta = buscar_venta(sesion, venta_uuid)
    item = next((i for i in venta.items if i.uuid == item_uuid), None)
    if item is None:
        return venta, []
    if venta.estado != EstadoVenta.ABIERTA:
        raise ErrorDeVenta("Solo se pueden quitar productos de una orden abierta.")

    avisos = eventos.publicar(
        sesion,
        "venta.item_anulado",
        item_uuid=item.uuid,
        producto_uuid=item.producto_uuid,
        cantidad=item.cantidad_num,
        nombre_producto=item.nombre_producto,
    )
    venta.items.remove(item)
    _recalcular_total(venta)
    sesion.commit()
    return venta, avisos


def cobrar(sesion: Session, venta_uuid: str, datos: CobroEntrada) -> Venta:
    venta = buscar_venta(sesion, venta_uuid)
    if venta.estado == EstadoVenta.PAGADA_CERRADA:
        return venta  # reintento: ya estaba cobrada
    if venta.tipo == TipoVenta.VENTA_RAPIDA:
        raise ErrorDeVenta("La venta rápida ya se cobró: solo falta completar su detalle.")
    if venta.estado == EstadoVenta.FIADA:
        raise ErrorDeVenta("Esta venta ya se fió. Para cobrarla, registra un abono del cliente.")
    if not venta.items:
        raise ErrorDeVenta("La orden no tiene productos todavía.", 422)

    momento = momento_de_operacion(datos.ocurrido_en)
    venta.estado = EstadoVenta.PAGADA_CERRADA
    venta.metodo_pago = datos.metodo_pago
    venta.cerrada_en = momento
    if venta.monto_total > 0:
        # El pago usa el uuid de la venta: cobrar dos veces no crea dos pagos
        venta.pagos.append(
            Pago(uuid=venta.uuid, monto=venta.monto_total, metodo_pago=datos.metodo_pago, creado_en=momento)
        )
    sesion.commit()
    return venta


def fiar(sesion: Session, venta_uuid: str, datos: FiarEntrada) -> tuple[Venta, list[str]]:
    venta = buscar_venta(sesion, venta_uuid)
    if venta.estado == EstadoVenta.FIADA:
        return venta, []
    if venta.estado != EstadoVenta.ABIERTA or venta.tipo == TipoVenta.VENTA_RAPIDA:
        raise ErrorDeVenta("Solo se puede fiar una orden abierta.")
    if not venta.items:
        raise ErrorDeVenta("La orden no tiene productos todavía.", 422)

    if datos.cliente_uuid:
        venta.cliente = buscar_cliente(sesion, datos.cliente_uuid)
    if venta.cliente is None:
        raise ErrorDeVenta("Para fiar hay que elegir a qué cliente.", 422)

    cliente = venta.cliente
    deuda_previa = deuda_de(sesion, cliente.id)
    venta.tipo = TipoVenta.FIADO
    venta.estado = EstadoVenta.FIADA
    venta.cerrada_en = momento_de_operacion(datos.ocurrido_en)
    sesion.commit()

    avisos = []
    deuda_nueva = deuda_previa + venta.monto_total
    if cliente.limite_credito is not None and deuda_nueva > cliente.limite_credito:
        avisos.append(
            f"{cliente.nombre} ahora debe {soles(deuda_nueva)} y su límite es "
            f"{soles(cliente.limite_credito)}. El fiado se guardó igual."
        )
    return venta, avisos


def formalizar(sesion: Session, venta_uuid: str) -> Venta:
    venta = buscar_venta(sesion, venta_uuid)
    if venta.estado == EstadoVenta.PAGADA_CERRADA:
        return venta
    if venta.estado != EstadoVenta.PENDIENTE_FORMALIZAR:
        raise ErrorDeVenta("Solo las ventas rápidas se completan con su detalle.")
    if not venta.items:
        raise ErrorDeVenta("Agrega al menos un producto a la venta rápida.", 422)
    suma = sum((item.monto for item in venta.items), CERO)
    if suma != venta.monto_total:
        raise ErrorDeVenta(
            f"El detalle suma {soles(suma)} y la venta fue de {soles(venta.monto_total)}. "
            "Corrige los montos para que cuadren.",
            422,
        )
    venta.estado = EstadoVenta.PAGADA_CERRADA
    sesion.commit()
    return venta


def anular_orden_vacia(sesion: Session, venta_uuid: str) -> None:
    venta = sesion.scalar(select(Venta).where(Venta.uuid == venta_uuid))
    if venta is None:
        return  # ya anulada
    if venta.estado != EstadoVenta.ABIERTA or venta.items:
        raise ErrorDeVenta("Solo se puede anular una orden abierta y sin productos.")
    sesion.delete(venta)
    sesion.commit()


# ---------------------------------------------------------------- abonos

def registrar_abono(sesion: Session, datos: AbonoEntrada) -> tuple[Pago, Decimal, list[str]]:
    cliente = buscar_cliente(sesion, datos.cliente_uuid)
    existente = sesion.scalar(select(Pago).where(Pago.uuid == datos.uuid))
    if existente is not None:
        return existente, deuda_de(sesion, cliente.id), []

    abono = Pago(
        uuid=datos.uuid,
        cliente=cliente,
        monto=datos.monto,
        metodo_pago=datos.metodo_pago,
        creado_en=momento_de_operacion(datos.ocurrido_en),
    )
    sesion.add(abono)
    sesion.commit()

    restante = deuda_de(sesion, cliente.id)
    avisos = []
    if restante < 0:
        avisos.append(f"{cliente.nombre} pagó de más: tiene {soles(-restante)} a favor.")
    return abono, restante, avisos


def ventas_del_rango(sesion: Session, inicio: datetime, fin: datetime):
    """Ventas cobradas (en caja) cerradas entre inicio y fin."""
    return sesion.scalars(
        select(Venta).where(
            Venta.estado.in_([EstadoVenta.PAGADA_CERRADA, EstadoVenta.PENDIENTE_FORMALIZAR]),
            Venta.cerrada_en >= inicio,
            Venta.cerrada_en < fin,
        )
    ).all()
