"""Esquemas del Asistente."""

from pydantic import BaseModel


class PreguntaEntrada(BaseModel):
    mensaje: str


class RespuestaSalida(BaseModel):
    respuesta: str
