"""Configuración de los tests.

Cada proyecto (demo / anita) vive en un archivo SQLite dentro de UNA carpeta
temporal por sesión de pruebas: se redirige `rutas.directorio_datos()` antes
de que cualquier motor se cree, así los tests nunca tocan la carpeta de datos
real del vendedor. `MI_PUESTITO_ANITA_PIN` se fija para que el PIN de Anita
sea predecible en las pruebas (si no, se generaría al azar en cada corrida).
"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MI_PUESTITO_ANITA_PIN", "999999")

_directorio_temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

import rutas  # noqa: E402

# Reasignar el atributo del módulo (no "from rutas import directorio_datos"):
# las funciones de rutas.py resuelven este nombre en su propio namespace en
# cada llamada, así que sobreescribirlo aquí redirige a TODAS las que lo usan.
rutas.directorio_datos = lambda: Path(_directorio_temporal.name)

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cerrar_conexiones_al_final():
    """Libera los archivos SQLite antes de que se borre el directorio temporal.

    En Windows no se puede eliminar un archivo con conexiones abiertas (a
    diferencia de POSIX): sin este dispose(), la limpieza del directorio
    temporal fallaba con PermissionError al terminar la suite.
    """
    yield
    from database import _motores

    for motor in _motores.values():
        motor.dispose()


@pytest.fixture(autouse=True)
def base_de_datos_limpia():
    """Cada test empieza con las tablas vacías, en todos los proyectos.

    Sin esto, un test que guarda datos hace fallar a otro que espera una tabla
    vacía, y el resultado depende del orden de ejecución: la suite pasaría hoy
    y fallaría al añadir un archivo o al correr en paralelo.
    """
    from database import Base, crear_tablas_todos_los_proyectos, motor_de
    from proyectos import PROYECTOS

    crear_tablas_todos_los_proyectos()
    yield
    for clave in PROYECTOS:
        with motor_de(clave).begin() as conexion:
            for tabla in reversed(Base.metadata.sorted_tables):
                conexion.execute(tabla.delete())


@pytest.fixture()
def token_demo():
    """Token válido del proyecto demo, sin pasar por el endpoint de login."""
    from seguridad import crear_token

    return crear_token("demo")


@pytest.fixture()
def token_anita():
    """Token válido del proyecto real (Anita), sin pasar por el login."""
    from seguridad import crear_token

    return crear_token("anita")


@pytest.fixture()
def cabeceras_demo(token_demo):
    return {"Authorization": f"Bearer {token_demo}"}


@pytest.fixture()
def cabeceras_anita(token_anita):
    return {"Authorization": f"Bearer {token_anita}"}
