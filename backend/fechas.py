"""Fecha y hora del negocio.

El puesto está en Perú: el "día" que ve el vendedor es el día calendario de
Lima, no el del reloj del servidor. Usar `date.today()` en un servidor en UTC
adelanta el día cada tarde a partir de las 19:00 hora peruana, y entonces la
proyección "Mañana necesitas en caja" cita un pedido que la interfaz muestra
como pasado mañana.

El usuario nunca ingresa fecha, hora ni zona: se detectan aquí.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ZONA_PERU = ZoneInfo("America/Lima")

# Una operación hecha sin red llega con la hora del dispositivo. Se acepta si
# es razonable; si el reloj de la tablet está muy desfasado, manda el servidor.
TOLERANCIA_FUTURO = timedelta(minutes=5)
ANTIGUEDAD_MAXIMA = timedelta(days=30)


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


def rango_utc_del_dia(dia: date) -> tuple[datetime, datetime]:
    """Inicio y fin (exclusivo) en UTC del día calendario peruano `dia`.

    "Vendiste hoy" filtra por este rango: el día corta a la medianoche de
    Lima, no a la del servidor.
    """
    inicio = datetime.combine(dia, time.min, tzinfo=ZONA_PERU)
    return inicio.astimezone(timezone.utc), (inicio + timedelta(days=1)).astimezone(timezone.utc)


def momento_de_operacion(ocurrido_en: datetime | None) -> datetime:
    """Hora en que ocurrió una operación registrada en el dispositivo.

    Con red, es ahora. Sin red, la tablet envía su hora al sincronizar: la
    venta de las 10:00 enviada a las 15:00 debe contarse a las 10:00. Si esa
    hora es imposible (futuro o demasiado antigua) se usa la del servidor.
    """
    ahora = ahora_utc()
    if ocurrido_en is None:
        return ahora
    if ocurrido_en.tzinfo is None:
        ocurrido_en = ocurrido_en.replace(tzinfo=timezone.utc)
    if ocurrido_en > ahora + TOLERANCIA_FUTURO or ocurrido_en < ahora - ANTIGUEDAD_MAXIMA:
        return ahora
    return min(ocurrido_en, ahora)
