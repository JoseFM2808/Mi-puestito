"""Eventos entre módulos, sin dependencias cruzadas (AGENTS.md).

Ventas no conoce a Inventario: solo anuncia "se vendió este item". Si el
módulo Inventario está cargado, se suscribió y descuenta el stock en la
MISMA transacción; si no existe o falla, la venta se guarda igual.

Cada suscriptor corre dentro de un SAVEPOINT: si lanza, se deshace solo lo
suyo y la operación principal continúa. Es la regla "el fallo de un módulo
no derriba a otro" aplicada a una sola transacción.
"""

import logging
from collections import defaultdict
from collections.abc import Callable

from sqlalchemy.orm import Session

registro = logging.getLogger("mi_puestito.eventos")

# Un suscriptor recibe la sesión y los datos; puede devolver avisos en
# lenguaje simple para mostrarle al operador ("El arroz quedó en −2 kg").
Suscriptor = Callable[[Session, dict], list[str] | None]

_suscriptores: dict[str, dict[str, Suscriptor]] = defaultdict(dict)

# Últimos fallos de suscriptores, para /api/salud
fallos: dict[str, str] = {}


def suscribir(evento: str, nombre: str, funcion: Suscriptor) -> None:
    """Registra `funcion` para `evento`. Registrar dos veces el mismo nombre
    la reemplaza (importar un módulo dos veces no duplica descuentos)."""
    _suscriptores[evento][nombre] = funcion


def cancelar_suscripcion(evento: str, nombre: str) -> None:
    _suscriptores[evento].pop(nombre, None)


def publicar(sesion: Session, evento: str, **datos) -> list[str]:
    """Avisa a los suscriptores dentro de la transacción de `sesion`.

    Devuelve los avisos que los suscriptores quieran mostrar al operador.
    """
    avisos: list[str] = []
    for nombre, funcion in list(_suscriptores[evento].items()):
        try:
            with sesion.begin_nested():
                resultado = funcion(sesion, datos)
            if resultado:
                avisos.extend(resultado)
            fallos.pop(nombre, None)
        except Exception as error:  # noqa: BLE001 — aislar es justamente el punto
            fallos[nombre] = f"{evento}: {error}"
            registro.warning("El suscriptor %s falló en %s: %s", nombre, evento, error)
    return avisos
