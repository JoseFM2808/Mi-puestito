"""Interfaz agnóstica de proveedor de IA.

Regla no negociable del proyecto (AGENTS.md): "Nunca acoplar el código a un
proveedor de IA específico. Toda llamada a un modelo pasa por la capa de
abstracción de IA." Ningún módulo fuera de `ia/` debe importar un cliente de
NVIDIA, OpenAI, Anthropic, etc. directamente: todos hablan con `servicio.py`.
"""

from typing import Protocol


class ProveedorIA(Protocol):
    """Cualquier proveedor (NVIDIA hoy; local, OpenAI u otro mañana) implementa esto."""

    async def responder(
        self, mensajes: list[dict[str, str]], modelo: str, tiempo_limite: float
    ) -> str:
        """Devuelve el texto de la respuesta. Debe lanzar si el modelo falla
        o no contesta a tiempo, para que el llamador pruebe el siguiente."""
        ...
