"""Proveedor NVIDIA NIM (catálogo build.nvidia.com, API compatible con OpenAI).

Es un caso particular del proveedor genérico (`compatible_openai.py`): solo
fija la URL. Se conserva como nombre explícito para quien busque "NVIDIA" en
el código; la capa sigue agnóstica (ADR-036).
"""

from .compatible_openai import ProveedorCompatibleOpenAI
from .configuracion import URLS

URL_CHAT = f"{URLS['nvidia']}/chat/completions"


class ProveedorNvidia(ProveedorCompatibleOpenAI):
    def __init__(self, api_key: str):
        super().__init__(URLS["nvidia"], api_key)
