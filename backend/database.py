"""Conexión a la base de datos.

SQLite en local/desarrollo; el mismo código funciona con PostgreSQL en nube
cambiando solo la URL (ver docs/02-arquitectura/Stack-Tecnologico.md).
"""

import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, TypeDecorator, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from rutas import ruta_base_datos

# En desarrollo: ./mi_puestito.db. En el ejecutable: carpeta de datos del
# usuario (ver rutas.py). Siempre se puede forzar con MI_PUESTITO_BD.
URL_BASE_DATOS = os.environ.get("MI_PUESTITO_BD", f"sqlite:///{ruta_base_datos()}")

engine = create_engine(
    URL_BASE_DATOS,
    # SQLite: FastAPI atiende cada petición en su propio hilo
    connect_args={"check_same_thread": False} if URL_BASE_DATOS.startswith("sqlite") else {},
)

if URL_BASE_DATOS.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(conexion, _registro):
        """SQLite ignora las claves foráneas salvo que se activen por conexión.

        Sin esto, los `ondelete="CASCADE"` de los modelos no se aplicarían y
        borrar una venta dejaría sus items y pagos huérfanos.
        """
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SesionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class FechaHoraUTC(TypeDecorator):
    """Fecha y hora siempre con zona horaria, guardada en UTC.

    SQLite no almacena la zona: `DateTime(timezone=True)` devolvería fechas
    "ingenuas" y compararlas con fechas con zona rompe en tiempo de ejecución
    (un riesgo real al sincronizar con PostgreSQL, ver [[Sincronizacion-Offline]]).
    Este tipo normaliza a UTC al guardar y vuelve a marcar UTC al leer, de modo
    que el código siempre trabaja con fechas conscientes de su zona.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            # Una fecha sin zona se interpreta como UTC (así la generamos)
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    """Base declarativa común a todos los módulos."""


def obtener_sesion():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    sesion: Session = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
