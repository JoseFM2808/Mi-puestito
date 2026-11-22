"""Los MD de los módulos como contexto del Asistente en runtime (Fase 6, AGENTS.md: "estos MD son el
contexto que alimenta al AI Companion en runtime").

Cada pantalla tiene su `README.md` en `frontend/src/modules/<módulo>/`, con la tabla "Qué acciones
permite" (qué se hace y con qué botón). Cuando el operador pide ayuda ("¿cómo…?", "¿dónde…?", "¿qué
toco?"), se agregan al prompt las filas de la pantalla en la que está y de la que nombra: así el
Asistente cita los botones tal como son hoy, sin que nadie copie el manual a mano en `GUIA_APP`.

En el ejecutable los README viajan como datos (`MiPuestito.spec`, carpeta `guias/`). Si faltan, el
Asistente sigue con la guía compacta de siempre.
"""

import re
from functools import lru_cache
from pathlib import Path

import rutas

# Pantalla de la app → carpeta de su módulo en el frontend
MODULO_DE_PANTALLA = {
    "caja": "dashboard",
    "ventas": "ventas",
    "fiados": "fiados",
    "compras": "compras",
    "inventario": "inventario",
    "gastos": "gastos",
    "analisis": "analisis",
}
NOMBRE_DE_PANTALLA = {
    "caja": "Caja de hoy",
    "ventas": "Ventas",
    "fiados": "Fiados",
    "compras": "Compras",
    "inventario": "Inventario",
    "gastos": "Gastos",
    "analisis": "¿Cómo me va?",
}

# Palabras que nombran una pantalla aunque el operador no esté en ella
_TEMAS = {
    "ventas": r"vend\w*|venta\w*|orden\w*|cobr\w*",
    "fiados": r"fiad\w*|deb\w*|deud\w*|abon\w*|pag[oó]\b",
    "compras": r"compr\w*|pedid\w*|proveedor\w*|lleg[oó]\w*",
    "inventario": r"inventario|stock|producto\w*|merma\w*|venci\w*|c[oó]digo",
    "gastos": r"gast\w*|alquiler|pasaje\w*",
    "analisis": r"gan[eéa]\w*|rentab\w*|semana|mes\b|kardex",
    "caja": r"caja|gaveta",
}
_TEMA = {pantalla: re.compile(rf"\b(?:{palabras})", re.IGNORECASE) for pantalla, palabras in _TEMAS.items()}

# Pide ayuda para usar la app (no una cifra)
_PIDE_AYUDA = re.compile(
    r"\b(?:c[oó]mo|d[oó]nde|qu[eé]\s+(?:toco|hago|aprieto|bot[oó]n)|para\s+qu[eé]|no\s+(?:s[eé]|entiendo|encuentro)|"
    r"ay[uú]d\w*|expl[ií]ca\w*|se\s+puede)\b",
    re.IGNORECASE,
)
MAX_PANTALLAS = 2
MAX_CARACTERES = 1500


def directorio_guias() -> Path:
    if rutas.es_ejecutable():
        return rutas.directorio_recursos() / "guias"
    return Path(__file__).resolve().parents[2] / "frontend" / "src" / "modules"


def _limpiar(celda: str) -> str:
    sin_codigo = re.sub(r"`[^`]*`", "", celda)
    sin_marcas = sin_codigo.replace("**", "").replace("\\|", "|")
    sin_referencias = re.sub(r"\s*\((?:D|ADR)-\d+\)|\s*\(\s*\)", "", sin_marcas)
    return " ".join(sin_referencias.split()).strip(" ,;")


def acciones_de(readme: str) -> list[str]:
    """Las filas de "Qué acciones permite" como "<qué se hace>: <cómo>"."""
    seccion = re.search(r"^## Qué acciones permite\s*$(?P<cuerpo>.*?)(?=^## |\Z)", readme, re.M | re.S)
    if not seccion:
        return []
    filas = []
    for linea in seccion["cuerpo"].splitlines():
        celdas = [c for c in re.split(r"(?<!\\)\|", linea.strip())[1:-1]]
        if len(celdas) < 2 or set("".join(celdas).strip()) <= set("-: "):
            continue
        accion, como = _limpiar(celdas[0]), _limpiar(celdas[1])
        if accion and como and accion.lower() not in {"acción", "accion"}:
            filas.append(f"{accion}: {como}")
    return filas


@lru_cache(maxsize=16)
def _guia(modulo: str) -> tuple[str, ...]:
    try:
        return tuple(acciones_de((directorio_guias() / modulo / "README.md").read_text(encoding="utf-8")))
    except OSError:
        return ()


def pide_ayuda(mensaje: str) -> bool:
    return bool(_PIDE_AYUDA.search(mensaje))


def para_la_pregunta(mensaje: str, pantalla_actual: str | None) -> str:
    """Las acciones de la pantalla abierta y de la que se nombra, si el operador pide ayuda; si no, ""."""
    if not pide_ayuda(mensaje):
        return ""
    # Primero la pantalla de la que habla; después la que tiene abierta
    pantallas = [p for p in MODULO_DE_PANTALLA if _TEMA[p].search(mensaje)]
    if pantalla_actual in MODULO_DE_PANTALLA and pantalla_actual not in pantallas:
        pantallas.append(pantalla_actual)
    bloques = []
    for pantalla in pantallas[:MAX_PANTALLAS]:
        filas = _guia(MODULO_DE_PANTALLA[pantalla])
        if filas:
            bloques.append(f"{NOMBRE_DE_PANTALLA[pantalla]}:\n" + "\n".join(f"- {f}" for f in filas))
    return "\n".join(bloques)[:MAX_CARACTERES]
