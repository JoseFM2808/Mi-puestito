"""Registro de proyectos (espacios de trabajo).

Cada proyecto es un negocio independiente con su propia base de datos: nada
de un proyecto se mezcla con otro. Hoy hay dos:

- **demo**: toda la información ficticia que ya existía en la Demo 1
  (Restaurante Doña Carmen, Sra. Flora, Distribuidora Norte…). Sirve para
  mostrar la app sin arriesgar datos reales.
- **anita**: la primera empresa real. Arranca vacía; sus cifras son las
  ventas y compras que Anita registre de verdad.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Proyecto:
    clave: str
    nombre: str
    """Nombre visible en la pantalla de ingreso y en la barra superior."""
    es_real: bool
    """False = datos de muestra; True = negocio real, se trata con cuidado."""


PROYECTOS: dict[str, Proyecto] = {
    "demo": Proyecto(clave="demo", nombre="Demo", es_real=False),
    "anita": Proyecto(clave="anita", nombre="Anita", es_real=True),
}


def proyecto_valido(clave: str) -> bool:
    return clave in PROYECTOS
