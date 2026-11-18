"""Borrador de venta: el Asistente LLENA una orden y el operador la confirma (ADR-049).

Cuando el operador pide registrar una venta y dice qué lleva ("quiero registrar una orden
de 2 fideos Anita, cada uno a 4.80"), el modelo termina su respuesta con una línea por
producto:

    VENTA: 2 x Fideos Anita a 4.80

y, si dijo para quién es, `PARA: Sra. Bertha` (el nombre de la orden). Aquí se convierte
en un borrador que la app muestra en Ventas, ya llenado, con "Guardar orden". El Asistente
nunca guarda: el operador revisa y confirma.

Reglas que no dependen del modelo:
- Solo hay borrador si el operador pidió registrar algo (`acciones.pide_ir_o_hacer`).
- Un precio que el operador no dijo se descarta (queda en blanco y la app propone el precio
  del inventario): el modelo no puede poner precios. Igual que el verificador de cifras.
- Cantidades y precios con topes; nombres cortos; a lo sumo `MAX_ITEMS` productos.
"""

import re
from decimal import Decimal, InvalidOperation

from .cifras import _numeros

MAX_ITEMS = 10
MAX_NOMBRE = 80
MAX_CANTIDAD = Decimal("9999")
MAX_PRECIO = Decimal("99999")

_LINEA = re.compile(
    # Sin ancla al inicio: algunos modelos la pegan al final de la última frase.
    # "2 x Fideos", "1 kg x Arroz", "1 kilo de Arroz": la unidad escrita se tolera y se ignora
    r"\s*\bVENTA\s*:\s*(?P<cantidad>\d+(?:[.,]\d{1,3})?)\s*"
    r"(?:(?:kg|kilos?|kilogramos?|l|lt|litros?|unid(?:ad(?:es)?)?\.?|u)\s+)?"
    r"(?:x|×|\*|de)\s*(?P<nombre>[^\n]+?)"
    r"(?:\s+a\s+(?:S/\.?\s*)?(?P<precio>\d+(?:[.,]\d{1,2})?)(?:\s*soles)?(?:\s+(?:c/u|cada\s+uno))?)?\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Un precio de relleno que algunos modelos escriben cuando el operador no lo dijo: "a <precio>", "a ..."
_PRECIO_DE_RELLENO = re.compile(r"\s+a\s+(?:<[^>]*>|\.{2,}|_+|precio|\?+)\s*$", re.IGNORECASE)
# El texto del modelo habla de una orden llenada ("revisa la orden y toca Guardar orden")
HABLA_DE_UNA_ORDEN_LLENADA = re.compile(r"guardar\s+orden|revisa\s+la\s+orden|orden\s+llenada", re.IGNORECASE)
PEDIR_PRODUCTOS = "Dime qué productos lleva y cuántos de cada uno, y te lleno la orden en Ventas."
# Para quién es la orden ("PARA: Sra. Bertha"): será el nombre de la orden
_PARA = re.compile(r"\s*\bPARA\s*:\s*(?P<nombre>[^\n]{1,60}?)\s*\.?\s*$", re.IGNORECASE | re.MULTILINE)


def _decimal(texto: str | None) -> Decimal | None:
    if not texto:
        return None
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None


def separar(texto: str) -> tuple[str, list[dict[str, str | None]]]:
    """Quita las líneas VENTA del texto y devuelve (texto limpio, items en bruto)."""
    items: list[dict[str, str | None]] = []
    for linea in _LINEA.finditer(texto):
        cantidad = _decimal(linea["cantidad"])
        nombre = _PRECIO_DE_RELLENO.sub("", linea["nombre"]).strip(" .,;:-\"'«»")[:MAX_NOMBRE]
        precio = _decimal(linea["precio"])
        if not nombre or cantidad is None or not (Decimal("0") < cantidad <= MAX_CANTIDAD):
            continue
        if precio is not None and not (Decimal("0") <= precio <= MAX_PRECIO):
            precio = None
        items.append({
            "nombre": nombre,
            "cantidad": f"{cantidad.normalize():f}",
            "precio": f"{precio.quantize(Decimal('0.01'))}" if precio is not None else None,
        })
    limpio = re.sub(r"\n{3,}", "\n\n", _LINEA.sub("", texto)).strip()
    return limpio, items[:MAX_ITEMS]


def separar_para(texto: str) -> tuple[str, str | None]:
    """Quita la línea PARA del texto y devuelve (texto limpio, para quién es la orden)."""
    encontrado = _PARA.search(texto)
    para = encontrado["nombre"].strip(" .,;:-\"'«»") if encontrado else None
    limpio = re.sub(r"\n{3,}", "\n\n", _PARA.sub("", texto)).strip()
    return limpio, para or None


def validar(items: list[dict[str, str | None]], dicho_por_el_operador: str) -> list[dict[str, str | None]]:
    """Deja solo los precios que el operador dijo: lo demás lo completa él o el inventario."""
    dichos = _numeros(dicho_por_el_operador)
    return [
        {**item, "precio": item["precio"] if item["precio"] and Decimal(item["precio"]) in dichos else None}
        for item in items
    ]
