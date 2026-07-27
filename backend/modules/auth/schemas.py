"""Esquemas del login."""

from pydantic import BaseModel


class IngresoEntrada(BaseModel):
    nombre_usuario: str
    pin: str


class IngresoSalida(BaseModel):
    token: str
    proyecto: str
    nombre_proyecto: str
    es_real: bool
