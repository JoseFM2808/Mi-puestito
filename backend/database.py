"""Conexión a la base de datos.

Cada proyecto (demo / anita) tiene su propio archivo SQLite: nunca comparten
motor ni sesión, así un dato de práctica jamás puede aparecer mezclado con
los datos reales de una empresa. El mismo código funciona con PostgreSQL en
la nube cambiando solo la URL (ver docs/02-arquitectura/Stack-Tecnologico.md).

Concurrencia (deuda D-02, ADR-031): FastAPI atiende cada petición en su
propio hilo. En SQLite se activa WAL (lectores y un escritor a la vez sin
bloquearse), `busy_timeout` (esperar en vez de fallar con "database is
locked") y las sesiones de escritura abren con `BEGIN IMMEDIATE`: toman el
candado de escritura al empezar, así un "leer y luego escribir" nunca se
cruza con otro y ninguna venta pisa a otra.
"""

import os
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import Depends
from sqlalchemy import DateTime, Integer, MetaData, TypeDecorator, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from rutas import ruta_base_datos
from seguridad import proyecto_autenticado


class Base(DeclarativeBase):
    """Base declarativa común a todos los módulos.

    Índices y restricciones únicas con nombre predecible: Alembic necesita
    nombres para poder modificarlos o borrarlos en una migración futura.
    """

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
        }
    )


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


class _DecimalEnEntero(TypeDecorator):
    """Decimal en Python, entero exacto en la base de datos.

    SQLite guarda `NUMERIC` como número de coma flotante: sumar cientos de
    montos puede dar 485.4999… Guardar enteros (céntimos, milésimas) hace
    exacta cada suma, también la de `SUM()` en SQL. Decisión aplazada en el
    Plan de Trabajo "hasta Ventas real": se resuelve aquí (ADR-035).
    """

    impl = Integer
    cache_ok = True
    decimales = 2

    @property
    def _factor(self) -> int:
        return 10**self.decimales

    def process_bind_param(self, value, dialect) -> int | None:
        if value is None:
            return None
        cuantizado = Decimal(value).quantize(Decimal(1).scaleb(-self.decimales), ROUND_HALF_UP)
        return int(cuantizado * self._factor)

    def process_result_value(self, value, dialect) -> Decimal | None:
        if value is None:
            return None
        return (Decimal(int(value)) / self._factor).quantize(Decimal(1).scaleb(-self.decimales))


class Dinero(_DecimalEnEntero):
    """Soles con 2 decimales, guardados como céntimos enteros."""

    cache_ok = True  # SQLAlchemy no lo hereda: cada subclase lo declara
    decimales = 2


class Cantidad(_DecimalEnEntero):
    """Cantidades de inventario (unidades o kg) con 3 decimales, en milésimas."""

    cache_ok = True
    decimales = 3


def _url_para(proyecto: str) -> str:
    # MI_PUESTITO_BD fuerza la URL de un único proyecto (usado en tests)
    forzada = os.environ.get("MI_PUESTITO_BD")
    if forzada:
        return forzada
    return f"sqlite:///{ruta_base_datos(proyecto)}"


def _crear_motor(proyecto: str) -> Engine:
    url = _url_para(proyecto)
    es_sqlite = url.startswith("sqlite")
    motor = create_engine(
        url,
        # SQLite: FastAPI atiende cada petición en su propio hilo
        connect_args={"check_same_thread": False} if es_sqlite else {},
    )
    if es_sqlite:

        @event.listens_for(motor, "connect")
        def _configurar_conexion(conexion, _registro):
            # El driver deja de abrir transacciones por su cuenta: las abre
            # SQLAlchemy en el evento "begin" de abajo (receta oficial de
            # SQLAlchemy para que BEGIN IMMEDIATE y SAVEPOINT funcionen).
            conexion.isolation_level = None
            cursor = conexion.cursor()
            # SQLite ignora las claves foráneas salvo que se activen por
            # conexión: sin esto, los ondelete="CASCADE" no se aplicarían
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        @event.listens_for(motor, "begin")
        def _abrir_transaccion(conexion):
            escritura = conexion.get_execution_options().get("escritura", False)
            conexion.exec_driver_sql("BEGIN IMMEDIATE" if escritura else "BEGIN")

    return motor


_motores: dict[str, Engine] = {}
_fabricas_sesion: dict[str, sessionmaker] = {}
_fabricas_escritura: dict[str, sessionmaker] = {}


def motor_de(proyecto: str) -> Engine:
    """Motor de un proyecto, creado y cacheado la primera vez que se pide."""
    if proyecto not in _motores:
        _motores[proyecto] = _crear_motor(proyecto)
    return _motores[proyecto]


def migrar_todos_los_proyectos() -> None:
    """Lleva la base de datos de cada proyecto a la última versión del esquema."""
    from migraciones.ejecutar import migrar
    from proyectos import PROYECTOS

    for clave in PROYECTOS:
        migrar(motor_de(clave))


def _fabrica_de(proyecto: str) -> sessionmaker:
    if proyecto not in _fabricas_sesion:
        _fabricas_sesion[proyecto] = sessionmaker(
            bind=motor_de(proyecto), autocommit=False, autoflush=False
        )
    return _fabricas_sesion[proyecto]


def _fabrica_escritura_de(proyecto: str) -> sessionmaker:
    if proyecto not in _fabricas_escritura:
        _fabricas_escritura[proyecto] = sessionmaker(
            bind=motor_de(proyecto).execution_options(escritura=True),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _fabricas_escritura[proyecto]


def sesion_para(proyecto: str) -> Session:
    """Sesión directa de un proyecto, para scripts y tests fuera de FastAPI.

    Quien la usa es responsable de cerrarla (a diferencia de `obtener_sesion`,
    que es una dependencia y se encarga sola).
    """
    return _fabrica_de(proyecto)()


def sesion_escritura_para(proyecto: str) -> Session:
    """Como `sesion_para`, pero cada transacción toma el candado de escritura."""
    return _fabrica_escritura_de(proyecto)()


def obtener_sesion(proyecto: str = Depends(proyecto_autenticado)):
    """Dependencia de FastAPI: sesión de LECTURA del proyecto autenticado.

    Cada request solo puede tocar la base de datos del proyecto al que su
    token le da acceso — nunca la de otro.
    """
    sesion: Session = _fabrica_de(proyecto)()
    try:
        yield sesion
    finally:
        sesion.close()


def obtener_sesion_escritura(proyecto: str = Depends(proyecto_autenticado)):
    """Dependencia de FastAPI para endpoints que escriben (ventas, pagos…).

    La transacción abre con BEGIN IMMEDIATE en SQLite: dos cobros simultáneos
    se atienden uno después del otro, nunca intercalados.
    """
    sesion: Session = _fabrica_escritura_de(proyecto)()
    try:
        yield sesion
    finally:
        sesion.close()
