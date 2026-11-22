"""Router del módulo Análisis (Fase 7): ¿el puesto es rentable? Solo lectura."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import obtener_sesion

from . import servicio
from .schemas import AnalisisDelPeriodo, KardexDelMes, Periodo

router = APIRouter(prefix="/api/analisis", tags=["analisis"])


@router.get("", response_model=AnalisisDelPeriodo)
def del_periodo(periodo: Periodo = Query("semana"), sesion: Session = Depends(obtener_sesion)):
    """Vendido, pagado a proveedores, gastos del puesto y de la casa, y lo que quedó libre."""
    return servicio.del_periodo(sesion, periodo)


@router.get("/kardex", response_model=KardexDelMes)
def kardex(
    mes: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    sesion: Session = Depends(obtener_sesion),
):
    """Kardex mensual del inventario: lo que había, entró, salió y quedó de cada producto."""
    try:
        return servicio.kardex_del_mes(sesion, mes)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
