"""Router del Dashboard / Caja Diaria.

Cada proyecto ve su propio resumen (autenticado por token, ver seguridad.py),
calculado desde sus propias tablas de Ventas y Compras (`servicio.py`).
El día es el de Lima, no el del reloj del servidor.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import obtener_sesion
from fechas import dia_peruano
from proyectos import PROYECTOS
from seguridad import proyecto_autenticado

from .schemas import ResumenDashboard
from .servicio import calcular_resumen

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenDashboard)
def obtener_resumen(sesion: Session = Depends(obtener_sesion)) -> ResumenDashboard:
    """Resumen del día actual y proyección del día siguiente."""
    return calcular_resumen(sesion, dia_peruano())


@router.post("/demo/reiniciar", status_code=status.HTTP_204_NO_CONTENT)
def reiniciar_demo(proyecto: str = Depends(proyecto_autenticado)) -> None:
    """Vuelve a sembrar los datos de práctica con las fechas de hoy (D-19).

    Un token de negocio real recibe 403: esto borra todo lo que hay en la base.
    """
    if PROYECTOS[proyecto].es_real:
        raise HTTPException(status_code=403, detail="Esta opción es solo para los datos de práctica.")
    import datos_demo

    datos_demo.reiniciar()
