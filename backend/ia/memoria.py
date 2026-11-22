"""Lo que el Asistente recuerda del negocio (D-26, ADR-052).

Decisión del owner (2026-11-17): como en los asistentes grandes, una memoria que se alimenta de lo
que cuenta el usuario, con un límite que obliga a repensar qué guardar para mejorar con el tiempo.

- El modelo propone un recuerdo con una línea `RECORDAR: <hecho corto>`.
- Una regla fija decide si se guarda: el operador tiene que haber pedido recordar algo o contado
  algo que dura ("acuérdate", "siempre", "prefiero"…). Una pregunta de cifras no deja recuerdos.
- Límite `MAX_RECUERDOS`. Al pasarlo, se **consolida**: el modelo reescribe la lista en
  `RECUERDOS_TRAS_CONSOLIDAR` hechos (une repetidos, quita lo viejo o contradicho). Si falla, se
  quedan los más nuevos: nunca se crece sin límite.
"""

import logging
import re

registro = logging.getLogger("mi_puestito.ia")

MAX_RECUERDOS = 20
RECUERDOS_TRAS_CONSOLIDAR = 15
MAX_TEXTO = 160

# En su propia línea o, como hacen algunos modelos con VENTA y ACCION, pegada al final de una frase
# (ahí solo en mayúsculas: "para recordar: …" en una frase normal no es una línea de control)
_LINEA = re.compile(
    r"(?:^[ \t]*(?i:recordar)|(?<=[.!?])[ \t]+RECORDAR)[ \t]*:[ \t]*(?P<hecho>[^\n]+?)[ \t]*$", re.MULTILINE
)
# "1. …", "2) …", "- …": la lista consolidada a veces llega numerada aunque se pida sin numerar
_VINETA = re.compile(r"^[ \t]*(?:\d{1,2}[.)]|[-•*])[ \t]*")

# Señales de que el operador quiere que algo se recuerde o contó algo que dura
_PIDE_RECORDAR = re.compile(
    r"\b(?:acu[eé]rdate|recuerda\w*|recordar|no\s+(?:te\s+)?olvides|ten\s+en\s+cuenta|siempre|nunca|"
    r"prefiero|me\s+gusta|todos\s+los|cada\s+(?:d[ií]a|semana|mes|lunes|martes|mi[eé]rcoles|jueves|viernes|"
    r"s[aá]bado|domingo))\b",
    re.IGNORECASE,
)


def separar(texto: str) -> tuple[str, list[str]]:
    """Quita las líneas RECORDAR y devuelve (texto limpio, hechos propuestos)."""
    hechos = []
    for linea in _LINEA.finditer(texto):
        hecho = linea["hecho"].strip(" .,;:-\"'«»")[:MAX_TEXTO]
        if hecho:
            hechos.append(hecho)
    limpio = re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", _LINEA.sub("", texto))).strip()
    return limpio, hechos


def pide_recordar(mensaje_del_operador: str) -> bool:
    return bool(_PIDE_RECORDAR.search(mensaje_del_operador))


def sin_repetidos(existentes: list[str], nuevos: list[str]) -> list[str]:
    """Los nuevos que no están ya (sin importar mayúsculas ni puntos al final)."""
    vistos = {_clave(t) for t in existentes}
    salida = []
    for hecho in nuevos:
        if _clave(hecho) not in vistos:
            vistos.add(_clave(hecho))
            salida.append(hecho)
    return salida


def _clave(texto: str) -> str:
    return re.sub(r"[\s.]+", " ", texto.lower()).strip()


PROMPT_CONSOLIDAR = """Eres la memoria del Asistente de un puesto de venta en Perú. Estas son las cosas que \
recuerdas del negocio, de la más vieja a la más nueva:

{recuerdos}

Reescribe la lista en COMO MÁXIMO {maximo} hechos cortos, útiles para atender mejor al vendedor: une los \
repetidos, si dos se contradicen deja el más nuevo, y quita lo que ya no sirva. No inventes nada. \
Responde SOLO con los hechos, uno por línea, sin numerar."""


async def consolidar(recuerdos: list[str], proveedor, modelo: str, tiempo_limite: float) -> list[str]:
    """Pide al modelo que repiense qué guardar. Si falla o responde de más, se quedan los más nuevos."""
    respaldo = recuerdos[-RECUERDOS_TRAS_CONSOLIDAR:]
    mensajes = [
        {
            "role": "user",
            "content": PROMPT_CONSOLIDAR.format(
                recuerdos="\n".join(f"- {r}" for r in recuerdos), maximo=RECUERDOS_TRAS_CONSOLIDAR
            ),
        }
    ]
    try:
        texto = await proveedor.responder(mensajes, modelo, tiempo_limite)
    except Exception as error:  # noqa: BLE001 — sin modelo, se recorta
        registro.warning("No se pudo consolidar la memoria: %s", error)
        return respaldo
    hechos = [_VINETA.sub("", linea).strip()[:MAX_TEXTO] for linea in texto.splitlines()]
    hechos = [h for h in hechos if h]
    if not hechos or len(hechos) > RECUERDOS_TRAS_CONSOLIDAR:
        return respaldo
    return hechos
