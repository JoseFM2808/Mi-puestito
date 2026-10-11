"""Configuración de la capa de IA (ADR-036). Todo por variables de entorno.

| Variable | Default | Para qué |
|---|---|---|
| `MI_PUESTITO_IA_PROVEEDOR` | `nvidia` | `nvidia` (NIM en la nube) o `local` (Ollama, llama.cpp…) |
| `MI_PUESTITO_IA_URL` | según proveedor | Base de una API compatible con OpenAI (`/v1`) |
| `NVIDIA_API_KEY` | — | Llave de NVIDIA. Nunca en el repo ni en archivos del proyecto |
| `MI_PUESTITO_IA_API_KEY` | — | Llave de un proveedor local, si la pide |
| `MI_PUESTITO_IA_MODELOS` | ver abajo | Modelos en orden de prioridad, separados por coma |
| `MI_PUESTITO_IA_TIMEOUT` | `12` | Segundos máximos por modelo antes de probar el siguiente |
| `MI_PUESTITO_IA_REGISTRO` | vacío | `demo` o `todos`: guarda intercambios seudonimizados (ADR-038) |

El orden de modelos sale, de mayor a menor prioridad, de: la variable
`MI_PUESTITO_IA_MODELOS` (o la antigua `NVIDIA_MODELOS_PRIORIDAD`), el
archivo `ia_modelos.json` que escribe `python -m ia.verificar` en la carpeta
de datos (solo nombres y latencias, nunca la llave), y la lista por defecto.
"""

import json
import os
from dataclasses import dataclass

import rutas

URLS = {
    "nvidia": "https://integrate.api.nvidia.com/v1",
    # Ollama expone una API compatible con OpenAI en este puerto
    "local": "http://127.0.0.1:11434/v1",
}

# Medido el 2026-10-08 con la llave del owner y el prompt real del Asistente:
# Nemotron 3.5 Lightning (MoE, ~3B activos) 1.2 s y gpt-oss-20b 1.7 s, ambos
# correctos con el razonamiento apagado. Gemma 4 31B (la familia del modelo
# local futuro) no respondió en 45 s: queda de respaldo hasta que lo haga.
MODELOS_NVIDIA = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "openai/gpt-oss-20b",
    "google/gemma-4-31b-it",
]

# Parámetros por familia: el Asistente necesita respuestas directas, no el
# borrador de un modelo de razonamiento (lento, en inglés y cortado).
AJUSTES_POR_FAMILIA = {
    "nvidia/nemotron": {"chat_template_kwargs": {"enable_thinking": False}},
    "openai/gpt-oss": {"reasoning_effort": "low"},
}


def ajustes_para(modelo: str) -> dict:
    for prefijo, ajustes in AJUSTES_POR_FAMILIA.items():
        if modelo.startswith(prefijo):
            return ajustes
    return {}

ARCHIVO_MODELOS = "ia_modelos.json"


@dataclass(frozen=True)
class ConfiguracionIA:
    proveedor: str
    url_base: str
    api_key: str | None
    modelos: tuple[str, ...]
    tiempo_limite: float
    registro: str  # "", "demo" o "todos"

    @property
    def lista(self) -> bool:
        """True si hay con qué responder (la nube necesita llave; lo local no)."""
        return bool(self.modelos) and (self.proveedor != "nvidia" or bool(self.api_key))


def _lista(texto: str | None) -> list[str]:
    return [parte.strip() for parte in (texto or "").split(",") if parte.strip()]


def modelos_verificados(proveedor: str) -> list[str]:
    """Orden que dejó `python -m ia.verificar` para este proveedor, si existe."""
    ruta = rutas.directorio_datos() / ARCHIVO_MODELOS
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if datos.get("proveedor") != proveedor:
        return []
    filas = datos.get("modelos", [])
    # Solo los que respondieron BIEN la prueba; si ninguno acertó, los que respondieron
    correctos = [m["modelo"] for m in filas if m.get("responde") and m.get("correcto", True)]
    return correctos or [m["modelo"] for m in filas if m.get("responde")]


def leer() -> ConfiguracionIA:
    """Se lee en cada consulta: cambiar una variable no exige reiniciar."""
    proveedor = (os.environ.get("MI_PUESTITO_IA_PROVEEDOR") or "nvidia").strip().lower()
    if proveedor not in URLS:
        proveedor = "nvidia"
    if proveedor == "nvidia":
        api_key = os.environ.get("NVIDIA_API_KEY") or None
        por_defecto = MODELOS_NVIDIA
    else:
        api_key = os.environ.get("MI_PUESTITO_IA_API_KEY") or None
        por_defecto = []  # local: el modelo instalado lo elige quien lo instala

    modelos = (
        _lista(os.environ.get("MI_PUESTITO_IA_MODELOS"))
        or _lista(os.environ.get("NVIDIA_MODELOS_PRIORIDAD"))
        or modelos_verificados(proveedor)
        or por_defecto
    )
    try:
        tiempo = float(os.environ.get("MI_PUESTITO_IA_TIMEOUT") or 12)
    except ValueError:
        tiempo = 12.0
    registro = (os.environ.get("MI_PUESTITO_IA_REGISTRO") or "").strip().lower()
    return ConfiguracionIA(
        proveedor=proveedor,
        url_base=(os.environ.get("MI_PUESTITO_IA_URL") or URLS[proveedor]).rstrip("/"),
        api_key=api_key,
        modelos=tuple(modelos),
        tiempo_limite=tiempo,
        registro=registro if registro in ("demo", "todos") else "",
    )
