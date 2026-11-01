"""Verificador de cifras: ningún monto inventado llega al operador (ADR-042).

Un modelo de lenguaje puede escribir "te deben S/ 130.00" cuando el dato dice
132.50 (visto el 2026-11-01 con la evaluación de `ia.evaluar`). En una caja eso
es peor que no responder, y pedirle que no invente no es una garantía. Esta
revisión sí lo es: todo monto de la respuesta debe existir en los datos o en lo
que dijo el operador. Si no, la respuesta se descarta.

Se permite aritmética solo con cifras que dio el operador ("vendí 120 y me deben
45" → 165). Una suma entre cifras del contexto se rechaza a propósito: con tantas
cifras, casi cualquier monto inventado saldría de alguna combinación (45 − 32.50
"justificaría" el S/ 12.50 inventado de este mes).
"""

import re
from decimal import Decimal, InvalidOperation

# "S/ 12", "S/12.50", "12.50 soles", "12 soles" o un decimal de dos cifras suelto
_MONTO = re.compile(
    r"S/\.?\s?(?P<soles>\d+(?:[.,]\d{1,2})?)"
    r"|(?P<palabra>\d+(?:[.,]\d{1,2})?)\s*soles\b"
    r"|(?<![\d.,/-])(?P<suelto>\d+[.,]\d{2})(?![\d.,/-])",
    re.IGNORECASE,
)
_NUMERO = re.compile(r"\d+(?:[.,]\d{1,2})?")


def _normal(texto: str) -> Decimal | None:
    try:
        return Decimal(texto.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _numeros(texto: str) -> set[Decimal]:
    return {n for n in (_normal(m) for m in _NUMERO.findall(texto)) if n is not None}


def montos_en(texto: str) -> set[Decimal]:
    """Montos de dinero mencionados en una respuesta (no conteos ni fechas)."""
    encontrados = set()
    for coincidencia in _MONTO.finditer(texto):
        monto = _normal(coincidencia["soles"] or coincidencia["palabra"] or coincidencia["suelto"])
        if monto is not None:
            encontrados.add(monto)
    return encontrados


def cifras_no_respaldadas(respuesta: str, contexto: str, dicho_por_el_operador: str = "") -> set[Decimal]:
    """Montos de la respuesta que no salen de los datos ni de lo que dijo el operador."""
    del_operador = _numeros(dicho_por_el_operador)
    permitidos = _numeros(contexto) | del_operador | {Decimal("0.00")}
    for a in del_operador:
        for b in del_operador:
            permitidos |= {a + b, abs(a - b)}
    return montos_en(respuesta) - permitidos
