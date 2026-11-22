"""Pedido a un proveedor que el Asistente LLENA y el operador guarda (Fase 6, capacidad 4).

Igual que la orden de venta (ADR-049) y los formularios de D-28, ahora para Compras. Cuando el
operador pide hacer un pedido ("pídele a Distribuidora Norte 2 sacos de arroz por 180"), el modelo
termina con una línea por producto y, si dijo a quién, una con el proveedor:

    COMPRA: Arroz | 2 sacos | 180.00
    PROVEEDOR: Distribuidora Norte

La app abre «Nuevo pedido» con el proveedor elegido (o su alta, si es nuevo) y los productos
listos: los que tienen monto van al pedido; los demás esperan a que el operador escriba cuánto
cuestan. Nada se guarda hasta que toca «Guardar pedido».

Reglas que no dependen del modelo (las aplica `validar` y el router):
- Solo si el operador pidió hacer algo (`acciones.pide_ir_o_hacer`).
- Un monto que el operador no dijo se descarta: el modelo no pone precios.
- La cantidad es texto libre, como en Compras ("2 sacos"): el stock solo sube con cantidad explícita
  al recibir (ADR-045).
"""

import re
from decimal import Decimal, InvalidOperation

from .cifras import _numeros

MAX_ITEMS = 10
MAX_TEXTO = 80
MAX_CANTIDAD_TEXTO = 60
MAX_MONTO = Decimal("99999")

_FIN = r"[ \t]*\.?[ \t]*$"
_COMPRA = re.compile(r"^[ \t]*COMPRA[ \t]*:[ \t]*(?P<resto>[^\n]+?)" + _FIN, re.IGNORECASE | re.MULTILINE)
_PROVEEDOR = re.compile(
    r"^[ \t]*PROVEEDOR[ \t]*:[ \t]*(?P<nombre>[^\n]{1,80}?)" + _FIN, re.IGNORECASE | re.MULTILINE
)
# Relleno que algunos modelos escriben en vez de dejar el campo vacío
_RELLENO = re.compile(r"^(?:<[^>]*>|\.{2,}|_+|\?+|-+|monto|cantidad|ninguno|n/?a)$", re.IGNORECASE)


def _texto(valor: str | None, maximo: int = MAX_TEXTO) -> str | None:
    limpio = (valor or "").strip(" .,;:-\"'«»")[:maximo]
    return None if not limpio or _RELLENO.match(limpio) else limpio


def _monto(valor: str | None) -> str | None:
    texto = (valor or "").strip().lower().replace("s/", "").replace("soles", "").replace(",", ".").strip()
    if not texto:
        return None
    try:
        monto = Decimal(texto)
    except InvalidOperation:
        return None
    return f"{monto.quantize(Decimal('0.01'))}" if Decimal("0") < monto <= MAX_MONTO else None


def separar(texto: str) -> tuple[str, dict | None]:
    """Quita las líneas COMPRA y PROVEEDOR y devuelve (texto limpio, pedido en bruto o None)."""
    items = []
    for linea in _COMPRA.finditer(texto):
        partes = [p.strip() for p in linea["resto"].split("|")]
        producto = _texto(partes[0] if partes else None)
        if not producto:
            continue
        items.append({
            "producto": producto,
            "cantidad": _texto(partes[1] if len(partes) > 1 else None, MAX_CANTIDAD_TEXTO),
            "monto": _monto(partes[2] if len(partes) > 2 else None),
        })
    encontrado = _PROVEEDOR.search(texto)
    proveedor = _texto(encontrado["nombre"]) if encontrado else None
    limpio = re.sub(r"\n{3,}", "\n\n", _PROVEEDOR.sub("", _COMPRA.sub("", texto))).strip()
    if not items:
        return limpio, None
    return limpio, {"proveedor": proveedor, "items": items[:MAX_ITEMS]}


def validar(pedido: dict, dicho_por_el_operador: str) -> dict:
    """Deja solo los montos que el operador dijo: lo demás lo escribe él."""
    dichos = _numeros(dicho_por_el_operador)
    return {
        **pedido,
        "items": [
            {**item, "monto": item["monto"] if item["monto"] and Decimal(item["monto"]) in dichos else None}
            for item in pedido["items"]
        ],
    }
