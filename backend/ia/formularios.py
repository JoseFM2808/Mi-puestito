"""Formularios que el Asistente LLENA y el operador confirma: pago de fiado, gasto y merma (D-28).

Igual que la orden de venta (ADR-049, `borrador.py`), pero para un solo registro por respuesta.
El modelo termina con UNA de estas líneas:

    ABONO: Sra. Rosa | 10.00 | efectivo
    GASTO: 5.00 | transporte | efectivo | puesto | pasaje al mercado
    MERMA: 2 x Leche Gloria | vencido

La app abre la pantalla con el formulario ya llenado; nada se guarda hasta que el operador toca
el botón de siempre ("Guardar abono", "Guardar gasto", "Guardar merma").

Reglas que no dependen del modelo (las aplica `validar`):
- Solo si el operador pidió registrar algo (lo decide el router con `pide_ir_o_hacer`).
- Un monto que el operador no dijo se descarta: el campo queda vacío para que lo escriba él.
- Medio, ámbito y categoría solo de listas cerradas; lo que no calce toma el valor por defecto.
"""

import re
from decimal import Decimal, InvalidOperation

from .cifras import _numeros

MEDIOS = {"efectivo", "yape_plin"}
AMBITOS = {"puesto", "hogar"}
CATEGORIAS = {"alquiler", "servicios", "transporte", "alimentacion", "educacion", "otros"}
MAX_TEXTO = 80
MAX_CANTIDAD = Decimal("9999")

_FIN = r"[ \t]*\.?[ \t]*$"


def linea_de_control(nombre: str) -> re.Pattern:
    """`NOMBRE: …` en su propia línea (en cualquier caso) o pegada al final de una frase, como hacen
    algunos modelos (ahí solo en mayúsculas: en una frase normal la palabra no es una línea de control)."""
    inicio = rf"(?:^[ \t]*(?i:{nombre})|(?<=[.!?])[ \t]+{nombre})"
    return re.compile(inicio + r"[ \t]*:[ \t]*(?P<resto>[^\n]+?)" + _FIN, re.MULTILINE)


_ABONO = linea_de_control("ABONO")
_GASTO = linea_de_control("GASTO")
_MERMA = linea_de_control("MERMA")
_CANTIDAD_Y_PRODUCTO = re.compile(
    r"^(?P<cantidad>\d+(?:[.,]\d{1,3})?)\s*(?:x|×|\*|de)?\s*(?P<producto>.+)$", re.IGNORECASE
)


def _texto(valor: str | None) -> str | None:
    limpio = (valor or "").strip(" .,;:-\"'«»")[:MAX_TEXTO]
    return limpio or None


def _monto(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        monto = Decimal(valor.strip().replace("S/", "").replace(",", ".").strip())
    except InvalidOperation:
        return None
    return f"{monto.quantize(Decimal('0.01'))}" if Decimal("0") < monto <= Decimal("99999") else None


def _medio(valor: str | None) -> str:
    texto = (valor or "").strip().lower()
    return "yape_plin" if "yape" in texto or "plin" in texto else "efectivo"


def _partes(resto: str) -> list[str]:
    return [p.strip() for p in resto.split("|")]


def separar(texto: str) -> tuple[str, dict | None]:
    """Quita las líneas ABONO / GASTO / MERMA y devuelve (texto limpio, el primer formulario válido)."""
    formulario: dict | None = None
    for patron, tipo in ((_ABONO, "abono"), (_GASTO, "gasto"), (_MERMA, "merma")):
        for linea in patron.finditer(texto):
            if formulario is None:
                formulario = _leer(tipo, _partes(linea["resto"]))
        texto = patron.sub("", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip(), formulario


def _leer(tipo: str, partes: list[str]) -> dict | None:
    if tipo == "abono":
        cliente = _texto(partes[0] if partes else None)
        if not cliente:
            return None
        return {
            "tipo": "abono",
            "cliente": cliente,
            "monto": _monto(partes[1] if len(partes) > 1 else None),
            "medio": _medio(partes[2] if len(partes) > 2 else None),
        }
    if tipo == "gasto":
        categoria = (partes[1] if len(partes) > 1 else "").strip().lower()
        ambito = (partes[3] if len(partes) > 3 else "").strip().lower()
        return {
            "tipo": "gasto",
            "monto": _monto(partes[0] if partes else None),
            "categoria": categoria if categoria in CATEGORIAS else "otros",
            "medio": _medio(partes[2] if len(partes) > 2 else None),
            "ambito": ambito if ambito in AMBITOS else "puesto",
            "nota": _texto(partes[4] if len(partes) > 4 else None),
        }
    # merma: "2 x Leche Gloria | vencido"
    encontrado = _CANTIDAD_Y_PRODUCTO.match(partes[0] if partes else "")
    if not encontrado:
        return None
    try:
        cantidad = Decimal(encontrado["cantidad"].replace(",", "."))
    except InvalidOperation:
        return None
    producto = _texto(encontrado["producto"])
    if not producto or not (Decimal("0") < cantidad <= MAX_CANTIDAD):
        return None
    return {
        "tipo": "merma",
        "producto": producto,
        "cantidad": f"{cantidad.normalize():f}",
        "nota": _texto(partes[1] if len(partes) > 1 else None),
    }


# Palabras que dicen la categoría de un gasto sin dudas. Solo corrigen un "otros" del modelo: si
# eligió una categoría, se respeta (el operador la ve y la puede cambiar)
_PALABRAS_DE_CATEGORIA = {
    "transporte": r"pasaje\w*|mototaxi\w*|combi\w*|taxi\w*|transporte|flete\w*|carrera",
    "alquiler": r"alquiler|renta",
    "servicios": r"luz|agua|internet|celular|recarga|gas",
    "educacion": r"colegio|útiles|utiles|pensión|pension|matrícula|matricula",
    "alimentacion": r"almuerzo|desayuno|cena|comida|mercado",
}
_CATEGORIA_POR_PALABRA = [
    (re.compile(rf"\b(?:{palabras})\b", re.IGNORECASE), categoria)
    for categoria, palabras in _PALABRAS_DE_CATEGORIA.items()
]


def validar(formulario: dict, dicho_por_el_operador: str) -> dict:
    """Deja el monto solo si el operador lo dijo (el modelo no pone montos) y, si el modelo dejó un
    gasto en "otros", lo clasifica por las palabras del operador cuando no hay duda."""
    if formulario.get("monto") and Decimal(formulario["monto"]) not in _numeros(dicho_por_el_operador):
        formulario = {**formulario, "monto": None}
    if formulario.get("tipo") == "gasto" and formulario.get("categoria") == "otros":
        categorias = {cat for patron, cat in _CATEGORIA_POR_PALABRA if patron.search(dicho_por_el_operador)}
        if len(categorias) == 1:
            formulario = {**formulario, "categoria": categorias.pop()}
    return formulario
