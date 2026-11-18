"""Reglas del módulo Caja (D-24, ADR-051).

En caja = lo que había al abrir + lo que entró − lo que salió, por separado en efectivo y en
Yape. Ventas y Gastos no se importan al cargar este módulo: se leen dentro de un `try`, y si
uno falla esa parte queda en cero y se nombra en `no_disponibles` (un módulo caído no tumba
la caja, igual que en el Dashboard).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fechas import dia_peruano, momento_de_operacion, rango_utc_del_dia

from .models import AperturaCaja
from .schemas import AperturaEntrada, CajaDelDia, SaldoPorMedio

CERO = Decimal("0.00")
MEDIOS = ("efectivo", "yape_plin")


def abrir(sesion: Session, datos: AperturaEntrada) -> AperturaCaja:
    """Abre la caja del día de `ocurrido_en`. Si ya estaba abierta, corrige sus saldos
    (gana la última apertura de ese día: es un dato maestro, no un movimiento)."""
    dia = dia_peruano(momento_de_operacion(datos.ocurrido_en))
    apertura = sesion.scalar(select(AperturaCaja).where(AperturaCaja.dia == dia))
    if apertura is None:
        apertura = AperturaCaja(uuid=datos.uuid, dia=dia, creado_en=momento_de_operacion(datos.ocurrido_en))
        sesion.add(apertura)
    apertura.efectivo_inicial = datos.efectivo_inicial
    apertura.yape_inicial = datos.yape_inicial
    sesion.commit()
    return apertura


def _ingresos(sesion: Session, dia: date) -> dict[str, Decimal]:
    """Ventas cobradas y abonos de fiado del día, por medio de pago (tabla `pagos` de Ventas)."""
    from modules.ventas.models import Pago

    desde, hasta = rango_utc_del_dia(dia)
    filas = sesion.execute(
        select(Pago.metodo_pago, func.coalesce(func.sum(Pago.monto), 0))
        .where(Pago.creado_en >= desde, Pago.creado_en < hasta)
        .group_by(Pago.metodo_pago)
    ).all()
    totales = dict.fromkeys(MEDIOS, CERO)
    for medio, monto in filas:
        totales[getattr(medio, "value", medio)] = Decimal(monto)
    return totales


def _egresos(sesion: Session, dia: date) -> dict[str, Decimal]:
    from modules.gastos.servicio import total_por_medio

    return total_por_medio(sesion, dia)


def del_dia(sesion: Session, dia: date) -> CajaDelDia:
    apertura = sesion.scalar(select(AperturaCaja).where(AperturaCaja.dia == dia))
    inicial = {
        "efectivo": apertura.efectivo_inicial if apertura else CERO,
        "yape_plin": apertura.yape_inicial if apertura else CERO,
    }
    no_disponibles: list[str] = []
    partes: dict[str, dict[str, Decimal]] = {}
    for nombre, calcular in (("ventas", _ingresos), ("gastos", _egresos)):
        try:
            partes[nombre] = calcular(sesion, dia)
        except Exception:  # noqa: BLE001 — sin Ventas o sin Gastos la caja igual se muestra
            sesion.rollback()
            partes[nombre] = dict.fromkeys(MEDIOS, CERO)
            no_disponibles.append(nombre)
    ingresos, egresos = partes["ventas"], partes["gastos"]
    return CajaDelDia(
        dia=dia,
        abierta=apertura is not None,
        inicial=SaldoPorMedio(**inicial),
        ingresos=SaldoPorMedio(**ingresos),
        egresos=SaldoPorMedio(**egresos),
        en_caja=SaldoPorMedio(**{m: inicial[m] + ingresos[m] - egresos[m] for m in MEDIOS}),
        no_disponibles=no_disponibles,
    )
