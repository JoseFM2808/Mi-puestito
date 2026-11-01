"""Aplica las migraciones al arrancar, una base de datos por proyecto.

Reemplaza a `create_all` (deuda D-03): con datos reales del vendedor, cambiar
una tabla exige migrarla sin perder una sola venta.

Dos cuidados propios de SQLite:
- ALTER en modo "batch" recrea tablas (crear nueva → copiar → borrar vieja).
  Con `foreign_keys=ON`, borrar la tabla vieja dispararía los ON DELETE
  CASCADE y se llevaría los items de cada venta. Por eso las claves se
  apagan durante la migración (fuera de transacción, como exige SQLite) y al
  final `PRAGMA foreign_key_check` confirma que nada quedó huérfano.
- Las bases creadas antes de Alembic (con create_all) no tienen tabla
  `alembic_version`: se marcan en la revisión 0001, que es exactamente ese
  esquema, y desde ahí se migran.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from rutas import directorio_recursos

REVISION_BASE = "0001"


class MigracionFallida(RuntimeError):
    """La migración dejó filas huérfanas: se revierte entera."""


def directorio_migraciones() -> Path:
    return directorio_recursos() / "migraciones"


def configuracion() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(directorio_migraciones()))
    return cfg


def migrar(motor: Engine, revision: str = "head") -> None:
    cfg = configuracion()
    es_sqlite = motor.dialect.name == "sqlite"
    with motor.connect() as conexion:
        crudo = conexion.connection.driver_connection
        if es_sqlite:
            crudo.execute("PRAGMA foreign_keys=OFF")
        try:
            with conexion.begin():
                cfg.attributes["connection"] = conexion
                tablas = set(inspect(conexion).get_table_names())
                if tablas - {"alembic_version"} and "alembic_version" not in tablas:
                    command.stamp(cfg, REVISION_BASE)
                command.upgrade(cfg, revision)
                if es_sqlite:
                    huerfanas = conexion.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                    if huerfanas:
                        raise MigracionFallida(f"Filas huérfanas tras migrar: {huerfanas[:5]}")
        finally:
            if es_sqlite:
                crudo.execute("PRAGMA foreign_keys=ON")
