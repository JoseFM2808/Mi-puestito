"""Proveedor genérico para cualquier API compatible con OpenAI (ADR-036).

NVIDIA NIM, Ollama, llama.cpp (`llama-server`), vLLM y LM Studio exponen
`POST {url}/chat/completions` con el mismo formato. Un solo cliente HTTP
(`httpx`, sin SDK de ningún proveedor) sirve para la nube de hoy y para el
modelo pequeño en el dispositivo de mañana: cambiar es cambiar la URL.
"""

import re

import httpx

# Algunos modelos de razonamiento escriben su borrador entre <think>…</think>:
# el operador solo debe ver la respuesta.
_PENSAMIENTO = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Otros lo escriben como texto normal (visto el 2026-10-08 con Nemotron 3.5:
# "Here's a thinking process: …" en inglés, cortado por max_tokens).
_BORRADOR = re.compile(
    r"^\s*(here'?s a thinking process|thinking process|okay,? (so|let'?s)|let me think|we need to|"
    r"the user (asks|is asking|wants))",
    re.IGNORECASE,
)
# Markdown que en una burbuja de texto plano se vería como asteriscos
_NEGRITA = re.compile(r"(\*\*|__)(.+?)\1")

MAX_TOKENS = 450


class RespuestaVacia(Exception):
    """El modelo contestó, pero sin texto útil."""


class RespuestaConBorrador(RespuestaVacia):
    """El modelo devolvió su razonamiento en vez de la respuesta: no se muestra."""


def limpiar(texto: str) -> str:
    sin_borrador = _PENSAMIENTO.sub("", texto or "")
    return _NEGRITA.sub(r"\2", sin_borrador).strip()


def es_borrador(texto: str) -> bool:
    return bool(_BORRADOR.match(texto or ""))


class ProveedorCompatibleOpenAI:
    def __init__(self, url_base: str, api_key: str | None = None):
        self._url = f"{url_base.rstrip('/')}/chat/completions"
        self._api_key = api_key

    async def responder(
        self,
        mensajes: list[dict[str, str]],
        modelo: str,
        tiempo_limite: float,
        extra: dict | None = None,
    ) -> str:
        """Texto final del modelo. `extra` son parámetros propios de su familia
        (p. ej. apagar el razonamiento, ver `configuracion.ajustes_para`)."""
        cabeceras = {"Accept": "application/json"}
        if self._api_key:
            cabeceras["Authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=tiempo_limite) as cliente:
            respuesta = await cliente.post(
                self._url,
                headers=cabeceras,
                json={
                    "model": modelo,
                    "messages": mensajes,
                    "max_tokens": MAX_TOKENS,
                    "temperature": 0.3,
                    "stream": False,
                    **(extra or {}),
                },
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        eleccion = datos["choices"][0]
        mensaje = eleccion["message"]
        crudo = mensaje.get("content") or ""
        razonamiento = mensaje.get("reasoning_content") or mensaje.get("reasoning") or ""
        # Si el contenido ES el razonamiento (o empieza como uno), no hay respuesta que mostrar
        if es_borrador(crudo) or (razonamiento and crudo.strip() == razonamiento.strip()):
            raise RespuestaConBorrador(modelo)
        texto = limpiar(crudo)
        if not texto:
            raise RespuestaVacia(modelo)
        return texto
