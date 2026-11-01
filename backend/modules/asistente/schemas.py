"""Esquemas del Asistente."""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class TurnoPrevio(BaseModel):
    """Un mensaje anterior de la conversación, para que el Asistente tenga memoria."""

    rol: Literal["operador", "asistente"]
    # Se recorta en vez de rechazar: una respuesta larga del Asistente no debe
    # impedir hacer la siguiente pregunta
    texto: Annotated[str, BeforeValidator(lambda valor: str(valor)[:1000])]


class PreguntaEntrada(BaseModel):
    # Una pregunta del puesto cabe de sobra en 500 caracteres; el tope evita
    # enviar textos enormes (y su costo) al proveedor de IA
    mensaje: Texto
    historial: list[TurnoPrevio] = Field(default_factory=list, max_length=12)


class LlaveEntrada(BaseModel):
    # Sin restricciones de Pydantic a propósito: un 422 repetiría la llave en su
    # respuesta. El largo se valida en el router, con un mensaje que no la incluye.
    llave: str


class EstadoAsistente(BaseModel):
    """Nunca lleva la llave: solo si hay una y si se puede guardar desde la pantalla."""

    listo: bool
    puede_guardar_llave: bool
    llave_guardada: bool


class AccionSugerida(BaseModel):
    """Un botón que el Asistente propone; el operador decide si lo toca."""

    tipo: Literal["ir_a"]
    pantalla: str
    etiqueta: str


class RespuestaSalida(BaseModel):
    respuesta: str
    acciones: list[AccionSugerida] = []
    # Para valorar la respuesta ("Me sirvió" / "No me sirvió")
    id_respuesta: str
    modelo: str


class ValoracionEntrada(BaseModel):
    id_respuesta: Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
    util: bool
