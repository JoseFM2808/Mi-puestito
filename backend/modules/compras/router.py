"""Router del módulo Compras y Proveedores.

Igual que Ventas: lecturas con sesión de lectura, escrituras con sesión de
escritura (BEGIN IMMEDIATE, D-02) e idempotentes por `uuid` (ADR-032): 201 si creó
algo y 200 si ya existía. Las reglas viven en `servicio.py`; aquí solo HTTP.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import obtener_sesion, obtener_sesion_escritura

from . import servicio
from .models import EstadoOrdenCompra, OrdenCompra
from .schemas import (
    CambioEstadoEntrada,
    OrdenCompraSalida,
    OrdenEntrada,
    ProductoFrecuente,
    ProveedorEntrada,
    ProveedorSalida,
    RecepcionEntrada,
    ResultadoOrden,
)

router = APIRouter(prefix="/api/compras", tags=["compras"])

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


def _http(error: servicio.ErrorDeCompra) -> HTTPException:
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


# ---------------------------------------------------------------- proveedores

@router.get("/proveedores", response_model=list[ProveedorSalida])
def listar_proveedores(
    sesion: Session = Depends(obtener_sesion),
    busqueda: str | None = Query(None, max_length=120),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Proveedores en orden alfabético; `busqueda` filtra por nombre, empresa o RUC."""
    return sesion.scalars(servicio.consulta_proveedores(busqueda).offset(desde).limit(limite)).all()


@router.post("/proveedores", response_model=ProveedorSalida, status_code=status.HTTP_201_CREATED)
def registrar_proveedor(
    datos: ProveedorEntrada,
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion_escritura),
):
    """Alta de proveedor, también cuando se registra a sí mismo en la tablet."""
    try:
        proveedor, creado = servicio.crear_proveedor(sesion, datos)
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return proveedor


@router.get("/proveedores/{uuid}/frecuentes", response_model=list[ProductoFrecuente])
def listar_frecuentes(uuid: str, sesion: Session = Depends(obtener_sesion)):
    """Productos que se le suelen pedir a este proveedor, para sugerirlos al armar un pedido."""
    try:
        return servicio.productos_frecuentes(sesion, uuid)
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error


# ---------------------------------------------------------------- órdenes

@router.get("/ordenes", response_model=list[OrdenCompraSalida])
def listar_ordenes(
    sesion: Session = Depends(obtener_sesion),
    estado: list[EstadoOrdenCompra] | None = Query(None),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Órdenes con sus items, de la más reciente primero.

    `selectinload` evita el N+1: sin él, N órdenes provocarían N consultas
    extra (una por cada lista de items y otra por cada proveedor).
    """
    consulta = (
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.items), selectinload(OrdenCompra.proveedor))
        .order_by(OrdenCompra.creado_en.desc(), OrdenCompra.id.desc())
        .offset(desde)
        .limit(limite)
    )
    if estado:
        consulta = consulta.where(OrdenCompra.estado.in_(estado))
    return [servicio.a_salida(orden) for orden in sesion.scalars(consulta).all()]


@router.post("/ordenes", response_model=ResultadoOrden, status_code=status.HTTP_201_CREATED)
def crear_orden(
    datos: OrdenEntrada,
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion_escritura),
):
    """Nuevo pedido. El total se calcula aquí, desde los productos."""
    try:
        orden, creada = servicio.crear_orden(sesion, datos)
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error
    if not creada:
        respuesta.status_code = status.HTTP_200_OK
    return ResultadoOrden(orden=servicio.a_salida(orden))


@router.patch("/ordenes/{uuid}/estado", response_model=ResultadoOrden)
def cambiar_estado(
    uuid: str, datos: CambioEstadoEntrada, sesion: Session = Depends(obtener_sesion_escritura)
):
    """Borrador → Pendiente → En camino. La llegada y el cierre tienen su propia ruta."""
    try:
        return ResultadoOrden(orden=servicio.a_salida(servicio.cambiar_estado(sesion, uuid, datos)))
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error


@router.post("/ordenes/{uuid}/recepcion", response_model=ResultadoOrden)
def registrar_recepcion(
    uuid: str, datos: RecepcionEntrada, sesion: Session = Depends(obtener_sesion_escritura)
):
    """Checklist de llegada: recalcula el monto real y avisa a Inventario lo recibido."""
    try:
        orden, avisos = servicio.registrar_recepcion(sesion, uuid, datos)
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error
    return ResultadoOrden(orden=servicio.a_salida(orden), avisos=avisos)


@router.post("/ordenes/{uuid}/cerrar", response_model=ResultadoOrden)
def cerrar_orden(uuid: str, sesion: Session = Depends(obtener_sesion_escritura)):
    """El pedido ya llegó y se saldó con el proveedor."""
    try:
        return ResultadoOrden(orden=servicio.a_salida(servicio.cerrar_orden(sesion, uuid)))
    except servicio.ErrorDeCompra as error:
        raise _http(error) from error
