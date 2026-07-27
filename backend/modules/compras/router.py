"""Router del módulo Compras y Proveedores.

Demo 1: solo lectura para probar el ORM de punta a punta. Las operaciones de
registro de proveedores, órdenes de pedido y checklist de recepción llegan en
la demo del módulo Compras.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import obtener_sesion

from .models import OrdenCompra, Proveedor
from .schemas import OrdenCompraSalida, ProveedorSalida

router = APIRouter(prefix="/api/compras", tags=["compras"])

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


@router.get("/proveedores", response_model=list[ProveedorSalida])
def listar_proveedores(
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Lista los proveedores registrados, en orden alfabético."""
    consulta = select(Proveedor).order_by(Proveedor.nombre).offset(desde).limit(limite)
    return sesion.scalars(consulta).all()


@router.get("/ordenes", response_model=list[OrdenCompraSalida])
def listar_ordenes(
    sesion: Session = Depends(obtener_sesion),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    desde: int = Query(0, ge=0),
):
    """Lista las órdenes de compra con sus items, de la más reciente primero.

    `selectinload` evita el N+1: sin él, N órdenes provocarían N consultas
    extra (una por cada lista de items).
    """
    consulta = (
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.items))
        .order_by(OrdenCompra.creado_en.desc())
        .offset(desde)
        .limit(limite)
    )
    return sesion.scalars(consulta).all()
