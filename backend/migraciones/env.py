"""Entorno de Alembic (deuda D-03).

Hay una base por proyecto, así que no se usa una URL fija: quien migra pasa
la conexión ya abierta en `config.attributes["connection"]` (ver
`migraciones/ejecutar.py`). Para generar una revisión nueva en desarrollo:

    cd backend
    alembic revision --autogenerate -m "descripcion"

(usa `alembic.ini`, que apunta a una base SQLite temporal).
"""

import importlib

from alembic import context
from sqlalchemy import create_engine

from database import Base

config = context.config


def _metadatos_de_todos_los_modulos():
    """Solo para --autogenerate: todas las tablas forman un único historial.

    Al migrar en runtime no se importan modelos: las revisiones son
    operaciones explícitas, y un módulo roto no debe impedir migrar.
    """
    for modulo in ("ventas", "compras", "inventario"):
        importlib.import_module(f"modules.{modulo}.models")
    return Base.metadata


def _configurar(conexion, metadatos=None) -> None:
    context.configure(
        connection=conexion,
        target_metadata=metadatos,
        # SQLite no sabe ALTER COLUMN: "batch" recrea la tabla copiando datos
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


conexion_compartida = config.attributes.get("connection")
if conexion_compartida is not None:
    _configurar(conexion_compartida)
else:
    url = config.get_main_option("sqlalchemy.url")
    with create_engine(url).connect() as conexion:
        _configurar(conexion, _metadatos_de_todos_los_modulos())
        conexion.commit()
