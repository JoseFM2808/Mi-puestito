"""Router del módulo Ventas.

Lecturas con sesión de lectura; escrituras con sesión de escritura (BEGIN
IMMEDIATE en SQLite, D-02). Toda escritura es idempotente por `uuid`
(ADR-032): responde 201 si creó algo y 200 si ya existía (reintento de la
cola offline). Las reglas viven en `servicio.py`; aquí solo HTTP.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import obtener_sesion, obtener_sesion_escritura

from . import servicio
from .models import Cliente, EstadoVenta, Venta
from .schemas import (
    AbonoEntrada,
    AbonoSalida,
    ClienteCambios,
    ClienteConDeuda,
    ClienteEntrada,
    ClienteSalida,
    CobroEntrada,
    FiarEntrada,
    ItemEntrada,
    ResultadoVenta,
    VentaEntrada,
    VentaSalida,
)

router = APIRouter(prefix="/api/ventas", tags=["ventas"])

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


def _http(error: servicio.ErrorDeVenta) -> HTTPException:
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


def _resultado(sesion: Session, venta: Venta, avisos: list[str] | None = None) -> ResultadoVenta:
    return ResultadoVenta(venta=servicio.a_salida(sesion, venta), avisos=avisos or [])


# ------------------------------------------------------------------ lecturas

@router.get("/", response_model=list[VentaSalida])
def listar_ventas(
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
    estado: EstadoVenta | None = None,
):
    """Ventas con sus items, de la más reciente a la más antigua.

    `selectinload` trae items y clientes en consultas agrupadas: sin él, una
    lista de N ventas dispararía N+1 consultas sobre el SQLite de la tablet.
    """
    consulta = (
        select(Venta)
        .options(selectinload(Venta.items), selectinload(Venta.cliente))
        .order_by(Venta.abierta_en.desc())
        .offset(desde)
        .limit(limite)
    )
    if estado is not None:
        consulta = consulta.where(Venta.estado == estado)
    deudas = servicio.deudas_por_cliente(sesion)
    return [
        servicio.a_salida_con_deudas(venta, deudas) for venta in sesion.scalars(consulta).all()
    ]


@router.get("/abiertas", response_model=list[VentaSalida])
def ordenes_abiertas(sesion: Session = Depends(obtener_sesion)):
    """Panel de órdenes activas: todo lo que sigue abierto ahora, en orden de apertura."""
    consulta = (
        select(Venta)
        .where(Venta.estado == EstadoVenta.ABIERTA)
        .options(selectinload(Venta.items), selectinload(Venta.cliente))
        .order_by(Venta.abierta_en)
    )
    deudas = servicio.deudas_por_cliente(sesion)
    return [servicio.a_salida_con_deudas(v, deudas) for v in sesion.scalars(consulta).all()]


@router.get("/clientes", response_model=list[ClienteSalida])
def listar_clientes(
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = Query(None, max_length=60, description="Parte del nombre"),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Clientes en orden alfabético; `buscar` filtra por nombre al registrar un fiado."""
    consulta = select(Cliente).order_by(Cliente.nombre).offset(desde).limit(limite)
    if buscar:
        consulta = consulta.where(Cliente.nombre.ilike(f"%{buscar.strip()}%"))
    return sesion.scalars(consulta).all()


@router.get("/fiados", response_model=list[ClienteConDeuda])
def clientes_que_deben(sesion: Session = Depends(obtener_sesion)):
    """Clientes con deuda pendiente, del que más debe al que menos."""
    deudas = {cid: d for cid, d in servicio.deudas_por_cliente(sesion).items() if d > 0}
    if not deudas:
        return []
    clientes = sesion.scalars(select(Cliente).where(Cliente.id.in_(deudas))).all()
    salida = [
        ClienteConDeuda(**ClienteSalida.model_validate(c).model_dump(), deuda=deudas[c.id])
        for c in clientes
    ]
    return sorted(salida, key=lambda c: c.deuda, reverse=True)


@router.get("/clientes/{uuid}", response_model=ClienteConDeuda)
def ficha_cliente(uuid: str, sesion: Session = Depends(obtener_sesion)):
    try:
        cliente = servicio.buscar_cliente(sesion, uuid)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    return ClienteConDeuda(
        **ClienteSalida.model_validate(cliente).model_dump(),
        deuda=servicio.deuda_de(sesion, cliente.id),
    )


# ------------------------------------------------------------------ escrituras

@router.post("/clientes", response_model=ClienteSalida, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    datos: ClienteEntrada, respuesta: Response, sesion: Session = Depends(obtener_sesion_escritura)
):
    cliente, creado = servicio.crear_cliente(sesion, datos)
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return cliente


@router.patch("/clientes/{uuid}", response_model=ClienteSalida)
def editar_cliente(
    uuid: str, cambios: ClienteCambios, sesion: Session = Depends(obtener_sesion_escritura)
):
    try:
        return servicio.editar_cliente(sesion, uuid, cambios)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error


@router.post("/abonos", response_model=AbonoSalida, status_code=status.HTTP_201_CREATED)
def registrar_abono(
    datos: AbonoEntrada, respuesta: Response, sesion: Session = Depends(obtener_sesion_escritura)
):
    """Abono a la cuenta de un cliente (paga parte o todo su fiado)."""
    try:
        existia = sesion.scalar(select(servicio.Pago.id).where(servicio.Pago.uuid == datos.uuid))
        abono, restante, avisos = servicio.registrar_abono(sesion, datos)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    if existia:
        respuesta.status_code = status.HTTP_200_OK
    return AbonoSalida(
        uuid=abono.uuid,
        cliente_uuid=datos.cliente_uuid,
        monto=abono.monto,
        metodo_pago=abono.metodo_pago,
        creado_en=abono.creado_en,
        deuda_restante=restante,
        avisos=avisos,
    )


@router.post("/", response_model=ResultadoVenta, status_code=status.HTTP_201_CREATED)
def crear_venta(
    datos: VentaEntrada, respuesta: Response, sesion: Session = Depends(obtener_sesion_escritura)
):
    """Abre una orden activa o un fiado, o registra una venta rápida (ya cobrada)."""
    try:
        venta, creada = servicio.crear_venta(sesion, datos)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    if not creada:
        respuesta.status_code = status.HTTP_200_OK
    return _resultado(sesion, venta)


@router.get("/{uuid}", response_model=VentaSalida)
def ver_venta(uuid: str, sesion: Session = Depends(obtener_sesion)):
    try:
        return servicio.a_salida(sesion, servicio.buscar_venta(sesion, uuid))
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
def anular_orden(uuid: str, sesion: Session = Depends(obtener_sesion_escritura)):
    """Anula una orden abierta por error, solo si aún no tiene productos."""
    try:
        servicio.anular_orden_vacia(sesion, uuid)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error


@router.post("/{uuid}/items", response_model=ResultadoVenta, status_code=status.HTTP_201_CREATED)
def agregar_item(
    uuid: str, datos: ItemEntrada, respuesta: Response,
    sesion: Session = Depends(obtener_sesion_escritura),
):
    try:
        cantidad_antes = sesion.scalar(
            select(servicio.ItemVenta.id).where(servicio.ItemVenta.uuid == datos.uuid)
        )
        venta, avisos = servicio.agregar_item(sesion, uuid, datos)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    if cantidad_antes:
        respuesta.status_code = status.HTTP_200_OK
    return _resultado(sesion, venta, avisos)


@router.delete("/{uuid}/items/{item_uuid}", response_model=ResultadoVenta)
def quitar_item(uuid: str, item_uuid: str, sesion: Session = Depends(obtener_sesion_escritura)):
    try:
        venta, avisos = servicio.quitar_item(sesion, uuid, item_uuid)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    return _resultado(sesion, venta, avisos)


@router.post("/{uuid}/cobrar", response_model=ResultadoVenta)
def cobrar(uuid: str, datos: CobroEntrada, sesion: Session = Depends(obtener_sesion_escritura)):
    """Cierra una orden cobrándola: queda "Pagada y Cerrada"."""
    try:
        return _resultado(sesion, servicio.cobrar(sesion, uuid, datos))
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error


@router.post("/{uuid}/fiar", response_model=ResultadoVenta)
def fiar(uuid: str, datos: FiarEntrada, sesion: Session = Depends(obtener_sesion_escritura)):
    """Cierra una orden a crédito: suma a la deuda del cliente."""
    try:
        venta, avisos = servicio.fiar(sesion, uuid, datos)
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error
    return _resultado(sesion, venta, avisos)


@router.post("/{uuid}/formalizar", response_model=ResultadoVenta)
def formalizar(uuid: str, sesion: Session = Depends(obtener_sesion_escritura)):
    """Completa una venta rápida con su detalle (debe cuadrar con lo cobrado)."""
    try:
        return _resultado(sesion, servicio.formalizar(sesion, uuid))
    except servicio.ErrorDeVenta as error:
        raise _http(error) from error

