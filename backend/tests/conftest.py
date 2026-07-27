"""Configuración de los tests.

La BD se apunta a un archivo temporal ANTES de importar la aplicación:
database.py lee MI_PUESTITO_BD al importarse. Así los tests nunca tocan
la base de datos de desarrollo (./mi_puestito.db).
"""

import os
import tempfile

_directorio_temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["MI_PUESTITO_BD"] = f"sqlite:///{_directorio_temporal.name}/prueba.db"

import pytest  # noqa: E402 — debe importarse después de fijar la variable


@pytest.fixture(scope="session", autouse=True)
def _cerrar_conexiones_al_final():
    """Libera el archivo SQLite antes de que se borre el directorio temporal.

    En Windows no se puede eliminar un archivo con conexiones abiertas (a
    diferencia de POSIX): sin este dispose(), la limpieza del directorio
    temporal fallaba con PermissionError al terminar la suite.
    """
    yield
    from database import engine

    engine.dispose()


@pytest.fixture(autouse=True)
def base_de_datos_limpia():
    """Cada test empieza con las tablas vacías.

    Sin esto, un test que guarda datos hace fallar a otro que espera una tabla
    vacía, y el resultado depende del orden de ejecución: la suite pasaría hoy
    y fallaría al añadir un archivo o al correr en paralelo.
    """
    from database import Base, engine

    Base.metadata.create_all(bind=engine)
    yield
    with engine.begin() as conexion:
        for tabla in reversed(Base.metadata.sorted_tables):
            conexion.execute(tabla.delete())
