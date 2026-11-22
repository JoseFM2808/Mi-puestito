"""Router del módulo Análisis (Fase 7): ¿el puesto es rentable? Solo lectura."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import obtener_sesion

from . import servicio
from .schemas import AnalisisDelPeriodo, Periodo

router = APIRouter(prefix="/api/analisis", tags=["analisis"])


@router.get("", response_model=AnalisisDelPeriodo)
def del_periodo(periodo: Periodo = Query("semana"), sesion: Session = Depends(obtener_sesion)):
    """Vendido, pagado a proveedores, gastos del puesto y de la casa, y lo que quedó libre."""
    return servicio.del_periodo(sesion, periodo)
