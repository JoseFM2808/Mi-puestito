"""Conexión a la base de datos.

Cada proyecto (demo / anita) tiene su propio archivo SQLite: nunca comparten
motor ni sesión, así un dato de práctica jamás puede aparecer mezclado con
los datos reales de una empresa. El mismo código funciona con PostgreSQL en
la nube cambiando solo la URL (ver docs/02-arquitectura/Stack-Tecnologico.md).
"""

import os
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy import DateTime, TypeDecorator, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from rutas import ruta_base_datos
from seguridad import proyecto_autenticado


class Base(DeclarativeBase):
    """Base declarativa común a todos los módulos."""


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


def _url_para(proyecto: str) -> str:
    # MI_PUESTITO_BD fuerza la URL de un único proyecto (usado en tests)
    forzada = os.environ.get("MI_PUESTITO_BD")
    if forzada:
        return forzada
    return f"sqlite:///{ruta_base_datos(proyecto)}"


def _crear_motor(proyecto: str) -> Engine:
    url = _url_para(proyecto)
    motor = create_engine(
        url,
        # SQLite: FastAPI atiende cada petición en su propio hilo
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    if url.startswith("sqlite"):

        @event.listens_for(motor, "connect")
        def _activar_claves_foraneas(conexion, _registro):
            """SQLite ignora las claves foráneas salvo que se activen por conexión.

            Sin esto, los `ondelete="CASCADE"` de los modelos no se aplicarían
            y borrar una venta dejaría sus items y pagos huérfanos.
            """
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return motor


_motores: dict[str, Engine] = {}
_fabricas_sesion: dict[str, sessionmaker] = {}


def motor_de(proyecto: str) -> Engine:
    """Motor de un proyecto, creado y cacheado la primera vez que se pide."""
    if proyecto not in _motores:
        _motores[proyecto] = _crear_motor(proyecto)
    return _motores[proyecto]


def crear_tablas_de(proyecto: str) -> None:
    Base.metadata.create_all(bind=motor_de(proyecto))


def crear_tablas_todos_los_proyectos() -> None:
    from proyectos import PROYECTOS

    for clave in PROYECTOS:
        crear_tablas_de(clave)


def _fabrica_de(proyecto: str) -> sessionmaker:
    if proyecto not in _fabricas_sesion:
        _fabricas_sesion[proyecto] = sessionmaker(
            bind=motor_de(proyecto), autocommit=False, autoflush=False
        )
    return _fabricas_sesion[proyecto]


def sesion_para(proyecto: str) -> Session:
    """Sesión directa de un proyecto, para scripts y tests fuera de FastAPI.

    Quien la usa es responsable de cerrarla (a diferencia de `obtener_sesion`,
    que es una dependencia y se encarga sola).
    """
    return _fabrica_de(proyecto)()


def obtener_sesion(proyecto: str = Depends(proyecto_autenticado)):
    """Dependencia de FastAPI: sesión del proyecto autenticado en el token.

    Cada request solo puede tocar la base de datos del proyecto al que su
    token le da acceso — nunca la de otro.
    """
    sesion: Session = _fabrica_de(proyecto)()
    try:
        yield sesion
    finally:
        sesion.close()
