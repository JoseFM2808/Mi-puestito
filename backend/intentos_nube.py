"""Límite de intentos de PIN compartido entre instancias de la nube (D-04, ADR-058).

En el programa local el contador vive en memoria: hay un solo proceso. En Vercel cada petición
puede caer en una instancia distinta de la función, y un contador por instancia dejaría repartir
intentos para adivinar un PIN de 6 dígitos. Con PostgreSQL configurado, el contador vive en la
tabla `public.mi_puestito_intentos`, igual para todas las instancias, y se actualiza de forma
atómica (`INSERT … ON CONFLICT … RETURNING`).

Misma regla que la local (`seguridad.py`): tras INTENTOS_LIBRES fallos seguidos, cada fallo
duplica la espera hasta un tope; un acierto borra el contador.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_motor: Engine | None = None

_CREAR = text(
    """
    CREATE TABLE IF NOT EXISTS public.mi_puestito_intentos (
        usuario TEXT PRIMARY KEY,
        fallos INTEGER NOT NULL,
        bloqueado_hasta TIMESTAMPTZ
    )
    """
)


def _conexion():
    global _motor
    if _motor is None:
        from database import url_postgres

        _motor = create_engine(
            url_postgres(),
            connect_args={"prepare_threshold": None},
            pool_size=1,
            max_overflow=2,
            pool_pre_ping=True,
        )
        with _motor.begin() as conexion:
            conexion.execute(_CREAR)
    return _motor.begin()


def segundos_de_espera(usuario: str) -> int:
    """Cuántos segundos faltan para poder volver a intentar (0 = puede intentar)."""
    with _conexion() as conexion:
        hasta = conexion.execute(
            text("SELECT bloqueado_hasta FROM public.mi_puestito_intentos WHERE usuario = :u"), {"u": usuario}
        ).scalar()
    if hasta is None:
        return 0
    restante = (hasta - datetime.now(timezone.utc)).total_seconds()
    return int(restante) + 1 if restante > 0 else 0


def registrar_fallo(usuario: str, libres: int, espera_inicial: int, espera_maxima: int) -> None:
    with _conexion() as conexion:
        fallos = conexion.execute(
            text(
                "INSERT INTO public.mi_puestito_intentos (usuario, fallos) VALUES (:u, 1) "
                "ON CONFLICT (usuario) DO UPDATE SET fallos = mi_puestito_intentos.fallos + 1 "
                "RETURNING fallos"
            ),
            {"u": usuario},
        ).scalar()
        exceso = fallos - libres
        if exceso >= 0:
            espera = min(espera_inicial * 2**exceso, espera_maxima)
            conexion.execute(
                text("UPDATE public.mi_puestito_intentos SET bloqueado_hasta = :h WHERE usuario = :u"),
                {"u": usuario, "h": datetime.now(timezone.utc) + timedelta(seconds=espera)},
            )


def limpiar(usuario: str) -> None:
    with _conexion() as conexion:
        conexion.execute(text("DELETE FROM public.mi_puestito_intentos WHERE usuario = :u"), {"u": usuario})


def olvidar_motor() -> None:
    """Solo para tests: cierra las conexiones."""
    global _motor
    if _motor is not None:
        _motor.dispose()
        _motor = None
