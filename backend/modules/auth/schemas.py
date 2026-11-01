"""Esquemas del login."""

from pydantic import BaseModel


class IngresoEntrada(BaseModel):
    nombre_usuario: str
    pin: str


class CuentaVisible(BaseModel):
    """Lo que la pantalla de ingreso necesita para mostrar un botón por negocio."""

    nombre_usuario: str
    nombre_proyecto: str
    es_real: bool


class IngresoSalida(BaseModel):
    token: str
    proyecto: str
    nombre_proyecto: str
    es_real: bool
