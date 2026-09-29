"""Esquemas del Asistente."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


class PreguntaEntrada(BaseModel):
    # Una pregunta del puesto cabe de sobra en 500 caracteres; el tope evita
    # enviar textos enormes (y su costo) al proveedor de IA
    mensaje: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RespuestaSalida(BaseModel):
    respuesta: str
