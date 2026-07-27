"""El día del negocio es el de Lima, no el del reloj del servidor."""

from datetime import datetime, timezone

from fechas import ZONA_PERU, dia_peruano


def test_de_noche_en_lima_sigue_siendo_el_dia_anterior():
    # 04:00 UTC del 8 de julio son las 23:00 del 7 en Lima: para el vendedor
    # el día todavía no cambió. Con date.today() en un servidor UTC, la
    # proyección "Mañana necesitas en caja" apuntaría a un día de más.
    momento = datetime(2026, 7, 8, 4, 0, tzinfo=timezone.utc)
    assert dia_peruano(momento).isoformat() == "2026-07-07"


def test_el_dia_cambia_a_las_cinco_utc():
    assert dia_peruano(datetime(2026, 7, 8, 5, 0, tzinfo=timezone.utc)).isoformat() == "2026-07-08"


def test_acepta_fechas_sin_zona_como_utc():
    # Así se guardan históricamente en SQLite antes de FechaHoraUTC
    assert dia_peruano(datetime(2026, 7, 8, 4, 0)).isoformat() == "2026-07-07"


def test_la_zona_es_la_de_peru():
    assert str(ZONA_PERU) == "America/Lima"
    # Perú no aplica horario de verano: siempre UTC-5
    enero = datetime(2026, 1, 15, 12, 0, tzinfo=ZONA_PERU).utcoffset()
    julio = datetime(2026, 7, 15, 12, 0, tzinfo=ZONA_PERU).utcoffset()
    assert enero == julio
