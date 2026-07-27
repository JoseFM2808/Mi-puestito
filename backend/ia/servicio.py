"""Orquestación del Asistente: arma el contexto, prueba modelos por prioridad
de velocidad y devuelve la primera respuesta que llegue a tiempo.

Prioridad por velocidad: se intenta primero el modelo más chico/rápido; si
falla o tarda más que `tiempo_limite`, se prueba el siguiente. El operador
del puesto necesita respuestas rápidas mientras atiende clientes — un modelo
grande que tarda 20 segundos no sirve aunque responda mejor.

Los identificadores de modelo son del catálogo de NVIDIA NIM
(build.nvidia.com) y son configurables por variable de entorno porque ese
catálogo cambia con el tiempo; no dependas de que esta lista por defecto siga
existiendo tal cual — conviene confirmarla en el catálogo antes de producción.
"""

import os

from .nvidia import ProveedorNvidia

# De más rápido/chico a más grande/capaz. Ajustable con NVIDIA_MODELOS_PRIORIDAD
# (nombres separados por coma) sin tocar código.
MODELOS_PRIORIDAD_DEFECTO = [
    "meta/llama-3.2-3b-instruct",
    "meta/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1",
]

TIEMPO_LIMITE_SEGUNDOS = float(os.environ.get("MI_PUESTITO_IA_TIMEOUT", "8"))

PROMPT_SISTEMA = """Eres el Asistente de Mi Puestito, una app para vendedores \
informales en Perú. Responde SIEMPRE en español, en frases cortas y simples, \
sin tecnicismos: quien te lee puede tener baja fluidez lectora. Nunca uses \
solo un color o un ícono para comunicar algo, siempre acompaña con palabras.

Este es el estado actual del negocio ("Caja de hoy"), en formato de datos:
{contexto}

Si te preguntan algo que no está en esta información, dilo con honestidad y \
sugiere en qué parte de la app podría revisarlo. No inventes cifras."""


class AsistenteNoDisponible(Exception):
    """El Asistente no pudo responder (sin llave configurada, o todos los
    modelos fallaron o tardaron demasiado)."""


def _modelos_por_prioridad() -> list[str]:
    configurados = os.environ.get("NVIDIA_MODELOS_PRIORIDAD")
    if configurados:
        return [modelo.strip() for modelo in configurados.split(",") if modelo.strip()]
    return MODELOS_PRIORIDAD_DEFECTO


async def preguntar(mensaje_usuario: str, contexto_json: str) -> str:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise AsistenteNoDisponible(
            "El Asistente todavía no está configurado en esta computadora "
            "(falta la variable de entorno NVIDIA_API_KEY)."
        )

    proveedor = ProveedorNvidia(api_key)
    mensajes = [
        {"role": "system", "content": PROMPT_SISTEMA.format(contexto=contexto_json)},
        {"role": "user", "content": mensaje_usuario},
    ]

    ultimo_error: Exception | None = None
    for modelo in _modelos_por_prioridad():
        try:
            return await proveedor.responder(mensajes, modelo, TIEMPO_LIMITE_SEGUNDOS)
        except Exception as error:  # noqa: BLE001 — se prueba el siguiente modelo
            ultimo_error = error
            continue

    raise AsistenteNoDisponible(
        "El Asistente no pudo responder ahora mismo. Intenta de nuevo en un momento."
    ) from ultimo_error
