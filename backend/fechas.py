"""Fecha y hora del negocio.

El puesto está en Perú: el "día" que ve el vendedor es el día calendario de
Lima, no el del reloj del servidor. Usar `date.today()` en un servidor en UTC
adelanta el día cada tarde a partir de las 19:00 hora peruana, y entonces la
proyección "Mañana necesitas en caja" cita un pedido que la interfaz muestra
como pasado mañana.

El usuario nunca ingresa fecha, hora ni zona: se detectan aquí.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ZONA_PERU = ZoneInfo("America/Lima")


def ahora_utc() -> datetime:
    """Instante actual en UTC (lo que se guarda en la base de datos)."""
    return datetime.now(timezone.utc)


def ahora_peru() -> datetime:
    """Instante actual en hora peruana (lo que ve el vendedor)."""
    return datetime.now(ZONA_PERU)


def dia_peruano(momento: datetime | None = None) -> date:
    """Día calendario peruano de un instante (por defecto, ahora)."""
    if momento is None:
        return ahora_peru().date()
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(ZONA_PERU).date()
