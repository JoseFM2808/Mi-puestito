"""Router del módulo Caja (D-24, ADR-051): apertura del día y "En caja ahora"."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import obtener_sesion, obtener_sesion_escritura
from fechas import dia_peruano

from . import servicio
from .schemas import AperturaEntrada, CajaDelDia

router = APIRouter(prefix="/api/caja", tags=["caja"])


@router.post("/apertura", response_model=CajaDelDia)
def abrir(datos: AperturaEntrada, sesion: Session = Depends(obtener_sesion_escritura)):
    """Con cuánto empieza la caja hoy, en efectivo y en Yape. Repetirla corrige los saldos."""
    apertura = servicio.abrir(sesion, datos)
    return servicio.del_dia(sesion, apertura.dia)


@router.get("", response_model=CajaDelDia)
def del_dia(dia: date | None = Query(default=None), sesion: Session = Depends(obtener_sesion)):
    """Cuánto hay en caja (hoy si no se indica el día): inicial + ingresos − egresos, por medio."""
    return servicio.del_dia(sesion, dia or dia_peruano())
