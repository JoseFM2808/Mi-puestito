"""Router del módulo Inventario (Fase 2 del producto, ADR-031).

Importar este router suscribe Inventario a los eventos de Ventas: desde ese
momento cada item vendido con `producto_uuid` descuenta stock. Si este
módulo no carga, Ventas sigue funcionando igual (sin descontar).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import eventos
from database import obtener_sesion, obtener_sesion_escritura

from . import servicio
from .models import MovimientoInventario, Producto
from .schemas import (
    AjusteEntrada,
    AjusteSalida,
    Descuadre,
    MermaEntrada,
    MovimientoSalida,
    ProductoCambios,
    ProductoConEstado,
    ProductoEntrada,
    ProductoSalida,
)

router = APIRouter(prefix="/api/inventario", tags=["inventario"])

eventos.suscribir("venta.item_registrado", "inventario.descontar", servicio.al_vender_item)
eventos.suscribir("venta.item_anulado", "inventario.devolver", servicio.al_anular_item)


def _http(error: servicio.ErrorDeInventario) -> HTTPException:
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


def _con_estado(producto: Producto) -> ProductoConEstado:
    return ProductoConEstado(
        **ProductoSalida.model_validate(producto).model_dump(),
        bajo_minimo=producto.stock_minimo is not None and producto.stock_actual <= producto.stock_minimo,
        descuadre=producto.stock_actual < 0,
    )


@router.get("/productos", response_model=list[ProductoConEstado])
def listar_productos(
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = Query(None, max_length=60),
    solo_bajo_minimo: bool = False,
    limite: int = Query(100, ge=1, le=500),
    desde: int = Query(0, ge=0),
):
    consulta = select(Producto).order_by(Producto.nombre).offset(desde).limit(limite)
    if buscar:
        consulta = consulta.where(Producto.nombre.ilike(f"%{buscar.strip()}%"))
    if solo_bajo_minimo:
        consulta = consulta.where(
            Producto.stock_minimo.is_not(None), Producto.stock_actual <= Producto.stock_minimo
        )
    return [_con_estado(p) for p in sesion.scalars(consulta).all()]


@router.post("/productos", response_model=ProductoConEstado, status_code=status.HTTP_201_CREATED)
def crear_producto(
    datos: ProductoEntrada, respuesta: Response, sesion: Session = Depends(obtener_sesion_escritura)
):
    try:
        producto, creado = servicio.crear_producto(sesion, datos)
    except servicio.ErrorDeInventario as error:
        raise _http(error) from error
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return _con_estado(producto)


@router.patch("/productos/{uuid}", response_model=ProductoConEstado)
def editar_producto(
    uuid: str, cambios: ProductoCambios, sesion: Session = Depends(obtener_sesion_escritura)
):
    try:
        return _con_estado(servicio.editar_producto(sesion, uuid, cambios))
    except servicio.ErrorDeInventario as error:
        raise _http(error) from error


@router.get("/productos/{uuid}/movimientos", response_model=list[MovimientoSalida])
def movimientos_de(
    uuid: str,
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(50, ge=1, le=200),
    desde: int = Query(0, ge=0),
):
    """Por qué cambió el stock: cada venta, compra y ajuste, del más reciente al más antiguo."""
    try:
        producto = servicio.buscar_producto(sesion, uuid)
    except servicio.ErrorDeInventario as error:
        raise _http(error) from error
    return sesion.scalars(
        select(MovimientoInventario)
        .where(MovimientoInventario.producto_id == producto.id)
        .order_by(MovimientoInventario.creado_en.desc(), MovimientoInventario.id.desc())
        .offset(desde)
        .limit(limite)
    ).all()


@router.post("/ajustes", response_model=AjusteSalida)
def ajustar(datos: AjusteEntrada, sesion: Session = Depends(obtener_sesion_escritura)):
    """Conteo físico: deja el stock en lo contado y registra la diferencia."""
    try:
        producto, diferencia = servicio.ajustar_por_conteo(sesion, datos)
    except servicio.ErrorDeInventario as error:
        raise _http(error) from error
    return AjusteSalida(producto=producto, diferencia=diferencia)


@router.post("/mermas", response_model=ProductoConEstado)
def registrar_merma(datos: MermaEntrada, sesion: Session = Depends(obtener_sesion_escritura)):
    try:
        return _con_estado(servicio.registrar_merma(sesion, datos))
    except servicio.ErrorDeInventario as error:
        raise _http(error) from error


@router.get("/descuadres", response_model=list[ProductoConEstado])
def descuadres(sesion: Session = Depends(obtener_sesion)):
    """Productos con stock negativo: se vendió más de lo registrado. Toca contar."""
    consulta = select(Producto).where(Producto.stock_actual < 0).order_by(Producto.nombre)
    return [_con_estado(p) for p in sesion.scalars(consulta).all()]


@router.get("/conciliacion", response_model=list[Descuadre])
def conciliacion(sesion: Session = Depends(obtener_sesion)):
    """Control interno: debe estar SIEMPRE vacío (stock = Σ movimientos)."""
    return [
        Descuadre(producto=p, stock_segun_movimientos=calculado)
        for p, calculado in servicio.conciliar(sesion)
    ]
