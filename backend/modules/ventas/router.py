"""Router del módulo Ventas.

Demo 1: solo lectura para probar el ORM de punta a punta. El registro de
ventas (órdenes activas, fiado, venta rápida) llega en la demo del módulo.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import obtener_sesion

from .models import Cliente, Venta
from .schemas import ClienteSalida, VentaSalida

router = APIRouter(prefix="/api/ventas", tags=["ventas"])

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


@router.get("/", response_model=list[VentaSalida])
def listar_ventas(
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Lista las ventas con sus items, de la más reciente a la más antigua.

    `selectinload` trae todos los items en UNA consulta extra: sin él, una
    lista de N ventas dispararía N+1 consultas sobre el archivo SQLite de la
    tablet. La paginación evita cargar el historial completo.
    """
    consulta = (
        select(Venta)
        .options(selectinload(Venta.items))
        .order_by(Venta.abierta_en.desc())
        .offset(desde)
        .limit(limite)
    )
    return sesion.scalars(consulta).all()


@router.get("/clientes", response_model=list[ClienteSalida])
def listar_clientes(
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Lista los clientes (necesarios para el fiado)."""
    consulta = select(Cliente).order_by(Cliente.nombre).offset(desde).limit(limite)
    return sesion.scalars(consulta).all()
