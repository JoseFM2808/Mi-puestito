"""¿El puesto es rentable? (docs/03-modulos/Modulo-Analisis.md, Fase 7).

Solo lee: ventas cobradas (Ventas), pagos a proveedores y gastos (Gastos), fiados (Ventas) y el
costo de la última compra (Inventario, D-22). Ninguno se importa al cargar el módulo; cada parte
se calcula dentro de un `try` y, si falla, queda en cero y se nombra en `no_disponibles`.

- Vendido: igual que "Vendiste hoy" (ventas pagadas y rápidas, por `cerrada_en`), sumado por día peruano.
- Resultado del negocio = vendido − pagado a proveedores − gastos del puesto.
- Libre = resultado del negocio − gastos de la casa.
- Ganancia por producto: lo vendido de cada producto del inventario menos cantidad × costo de la
  última compra. Es un estimado: el costo real de cada venta pudo ser otro.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from fechas import dia_peruano, rango_utc_del_dia

from .schemas import AnalisisDelPeriodo, DiaDelPeriodo, GananciaPorProducto, Periodo

CERO = Decimal("0.00")
MAX_PRODUCTOS = 5


def rango(periodo: Periodo, hoy: date) -> tuple[date, date]:
    """Primer y último día (inclusive) del período, en días peruanos."""
    if periodo == "semana":  # de lunes a hoy
        return hoy - timedelta(days=hoy.weekday()), hoy
    if periodo == "mes":
        return hoy.replace(day=1), hoy
    fin = hoy.replace(day=1) - timedelta(days=1)
    return fin.replace(day=1), fin


def _utc(desde: date, hasta: date):
    return rango_utc_del_dia(desde)[0], rango_utc_del_dia(hasta)[1]


def _ventas(sesion: Session, desde: date, hasta: date) -> tuple[dict[date, Decimal], int]:
    from modules.ventas.servicio import ventas_del_rango

    por_dia: dict[date, Decimal] = defaultdict(lambda: CERO)
    cobradas = ventas_del_rango(sesion, *_utc(desde, hasta))
    for venta in cobradas:
        por_dia[dia_peruano(venta.cerrada_en)] += venta.monto_total
    return por_dia, len(cobradas)


def _gastos(sesion: Session, desde: date, hasta: date) -> tuple[dict[date, Decimal], dict[str, Decimal]]:
    from modules.gastos.models import AmbitoGasto, CategoriaGasto, Gasto

    inicio, fin = _utc(desde, hasta)
    por_dia: dict[date, Decimal] = defaultdict(lambda: CERO)
    totales = {"proveedores": CERO, "puesto": CERO, "casa": CERO}
    for gasto in sesion.scalars(select(Gasto).where(Gasto.creado_en >= inicio, Gasto.creado_en < fin)):
        por_dia[dia_peruano(gasto.creado_en)] += gasto.monto
        if gasto.categoria == CategoriaGasto.PROVEEDOR:
            totales["proveedores"] += gasto.monto
        elif gasto.ambito == AmbitoGasto.HOGAR:
            totales["casa"] += gasto.monto
        else:
            totales["puesto"] += gasto.monto
    return por_dia, totales


def _fiados(sesion: Session) -> Decimal:
    from modules.ventas.servicio import deudas_por_cliente

    return sum((d for d in deudas_por_cliente(sesion).values() if d > 0), CERO)


def _mejores_productos(sesion: Session, desde: date, hasta: date) -> list[GananciaPorProducto]:
    from modules.inventario.models import Producto
    from modules.ventas.models import EstadoVenta, ItemVenta, Venta

    inicio, fin = _utc(desde, hasta)
    filas = sesion.execute(
        select(ItemVenta.producto_uuid, ItemVenta.monto, ItemVenta.cantidad_num)
        .join(Venta, ItemVenta.venta_id == Venta.id)
        .where(
            ItemVenta.producto_uuid.is_not(None),
            Venta.estado.in_([EstadoVenta.PAGADA_CERRADA, EstadoVenta.FIADA]),
            Venta.cerrada_en >= inicio,
            Venta.cerrada_en < fin,
        )
    ).all()
    vendidos = {f[0] for f in filas}
    productos = {p.uuid: p for p in sesion.scalars(select(Producto).where(Producto.uuid.in_(vendidos)))}
    vendido: dict[str, Decimal] = defaultdict(lambda: CERO)
    costo: dict[str, Decimal] = defaultdict(lambda: CERO)
    for uuid, monto, cantidad in filas:
        producto = productos.get(uuid)
        if producto is None or producto.costo_ultimo is None:
            continue
        vendido[uuid] += monto
        costo[uuid] += (producto.costo_ultimo * (cantidad or Decimal("0"))).quantize(Decimal("0.01"))
    ranking = sorted(vendido, key=lambda u: vendido[u] - costo[u], reverse=True)[:MAX_PRODUCTOS]
    return [
        GananciaPorProducto(
            nombre=productos[u].nombre, vendido=vendido[u], ganancia_estimada=vendido[u] - costo[u]
        )
        for u in ranking
    ]


def del_periodo(sesion: Session, periodo: Periodo, hoy: date | None = None) -> AnalisisDelPeriodo:
    hoy = hoy or dia_peruano()
    desde, hasta = rango(periodo, hoy)
    no_disponibles: list[str] = []

    def intentar(nombre: str, calcular, vacio):
        try:
            return calcular()
        except Exception:  # noqa: BLE001 — un módulo caído no tumba el análisis
            sesion.rollback()
            no_disponibles.append(nombre)
            return vacio

    ventas_por_dia, ventas = intentar("ventas", lambda: _ventas(sesion, desde, hasta), ({}, 0))
    sin_gastos = {"proveedores": CERO, "puesto": CERO, "casa": CERO}
    gastos_por_dia, gastos = intentar("gastos", lambda: _gastos(sesion, desde, hasta), ({}, sin_gastos))
    fiados = intentar("fiados", lambda: _fiados(sesion), CERO)
    mejores = intentar("inventario", lambda: _mejores_productos(sesion, desde, hasta), [])

    vendido = sum(ventas_por_dia.values(), CERO)
    resultado = vendido - gastos["proveedores"] - gastos["puesto"]
    dias = [desde + timedelta(days=n) for n in range((hasta - desde).days + 1)]
    return AnalisisDelPeriodo(
        periodo=periodo,
        desde=desde,
        hasta=hasta,
        vendido=vendido,
        ventas=ventas,
        pagado_a_proveedores=gastos["proveedores"],
        gastos_del_puesto=gastos["puesto"],
        gastos_de_la_casa=gastos["casa"],
        resultado_del_negocio=resultado,
        libre=resultado - gastos["casa"],
        fiados_por_cobrar=fiados,
        por_dia=[
            DiaDelPeriodo(dia=d, vendido=ventas_por_dia.get(d, CERO), gastado=gastos_por_dia.get(d, CERO))
            for d in dias
        ],
        mejores_productos=mejores,
        no_disponibles=no_disponibles,
    )
