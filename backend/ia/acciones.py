"""Acciones que el Asistente puede SUGERIR (ADR-037). Nunca las ejecuta.

El modelo termina su respuesta con una línea como `ACCION: ir_a ventas` y
aquí se convierte en un botón con texto completo ("Ir a Ventas") que el
operador decide tocar. Se eligió una línea de texto y no "tool calling"
porque los modelos muy pequeños que correrán en el dispositivo la siguen de
forma más confiable, y es trivial de enseñar con fine-tuning.

Solo se aceptan pantallas de una lista blanca: lo que el modelo invente se
descarta en silencio.
"""

import re

PANTALLAS = {
    "caja": "Ir a la Caja de hoy",
    "ventas": "Ir a Ventas",
    "fiados": "Ir a Fiados",
}

MAX_ACCIONES = 2

# Red de seguridad: si el modelo no escribió la línea ACCION pero sí indicó una
# pantalla ("ve a la pantalla fiados"), igual se ofrece el botón. Los modelos
# muy pequeños olvidan el formato más que el contenido.
_MENCION = re.compile(
    r"\b(?:pantalla|secci[oó]n|men[uú])\s+(?:de\s+)?(?:la\s+|los\s+)?[«\"']?(?P<destino>fiados|ventas|caja)\b",
    re.IGNORECASE,
)

_LINEA = re.compile(
    # Sin ancla al inicio: algunos modelos la pegan al final de la última frase
    r"\s*\bACCI[OÓ]N\s*:\s*(?P<tipo>\w+)\s+(?P<destino>[\wáéíóú]+)\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extraer(texto: str) -> tuple[str, list[dict[str, str]]]:
    """Separa las líneas ACCION del texto y devuelve (texto limpio, acciones válidas)."""
    acciones: list[dict[str, str]] = []
    for coincidencia in _LINEA.finditer(texto):
        tipo = coincidencia["tipo"].lower()
        destino = coincidencia["destino"].lower()
        if tipo == "ir_a" and destino in PANTALLAS and all(a["pantalla"] != destino for a in acciones):
            acciones.append({"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]})
    limpio = _LINEA.sub("", texto)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio).strip()
    if not acciones:
        for mencion in _MENCION.finditer(limpio):
            destino = mencion["destino"].lower()
            if all(a["pantalla"] != destino for a in acciones):
                acciones.append({"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]})
    return limpio, acciones[:MAX_ACCIONES]
