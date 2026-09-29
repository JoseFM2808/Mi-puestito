"""Router del Dashboard / Caja Diaria.

Cada proyecto ve su propio resumen (autenticado por token, ver seguridad.py),
calculado desde sus propias tablas de Ventas y Compras (`servicio.py`).
El día es el de Lima, no el del reloj del servidor.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import obtener_sesion
from fechas import dia_peruano

from .schemas import ResumenDashboard
from .servicio import calcular_resumen

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenDashboard)
def obtener_resumen(sesion: Session = Depends(obtener_sesion)) -> ResumenDashboard:
    """Resumen del día actual y proyección del día siguiente."""
    return calcular_resumen(sesion, dia_peruano())
