"""Proveedor NVIDIA NIM (catálogo build.nvidia.com, API compatible con OpenAI).

Se usa `httpx` en vez de un SDK propio de un proveedor: mantiene la capa de
IA agnóstica, ya que un cliente HTTP genérico sirve igual para NVIDIA que
para cualquier otro servicio con API compatible con OpenAI el día de mañana.
"""

import httpx

URL_CHAT = "https://integrate.api.nvidia.com/v1/chat/completions"


class ProveedorNvidia:
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def responder(
        self, mensajes: list[dict[str, str]], modelo: str, tiempo_limite: float
    ) -> str:
        async with httpx.AsyncClient(timeout=tiempo_limite) as cliente:
            respuesta = await cliente.post(
                URL_CHAT,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                json={
                    "model": modelo,
                    "messages": mensajes,
                    "max_tokens": 400,
                    "temperature": 0.3,
                    "stream": False,
                },
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            return datos["choices"][0]["message"]["content"]
