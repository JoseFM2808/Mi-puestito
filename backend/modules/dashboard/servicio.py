"""Cálculo del resumen de Caja Diaria desde las tablas reales (D-01).

El Dashboard LEE de Ventas y Compras pero no depende de ellos: si uno no
puede cargarse, su parte del resumen sale en cero y se informa en
`secciones_no_disponibles`, y el resto se sigue mostrando.

Demo y negocio real usan exactamente este mismo cálculo; la diferencia es
solo que la base de demo trae datos de muestra (ver `datos_demo.py`).
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from fechas import rango_utc_del_dia

from .schemas import OrdenActivaResumen, PedidoPorLlegar, ResumenDashboard

CERO = Decimal("0.00")
MAX_PEDIDOS = 10


def _seccion_ventas(sesion: Session, hoy: date) -> dict:
    from modules.ventas import servicio as ventas
    from modules.ventas.models import EstadoVenta, TipoVenta, Venta

    inicio, fin = rango_utc_del_dia(hoy)
    cobradas = ventas.ventas_del_rango(sesion, inicio, fin)
    deudas = ventas.deudas_por_cliente(sesion)
    positivas = [d for d in deudas.values() if d > 0]

    abiertas = sesion.scalars(
        select(Venta)
        .where(Venta.estado == EstadoVenta.ABIERTA)
        .options(selectinload(Venta.cliente))
        .order_by(Venta.abierta_en)
    ).all()

    def nombre(venta, posicion: int) -> str:
        if venta.cliente is not None:
            return venta.cliente.nombre
        return venta.nombre_orden or f"Orden {posicion}"

    return {
        "ventas_hoy": sum((v.monto_total for v in cobradas), CERO),
        "ventas_cerradas": len(cobradas),
        "ordenes_activas": [
            OrdenActivaResumen(
                uuid=v.uuid,
                nombre=nombre(v, i),
                tipo=v.tipo.value,
                monto=v.monto_total,
                deuda_cliente=deudas.get(v.cliente_id, CERO) if v.tipo == TipoVenta.FIADO else None,
            )
            for i, v in enumerate(abiertas, start=1)
        ],
        "fiados_por_cobrar": sum(positivas, CERO),
        "clientes_con_fiado": len(positivas),
        "ventas_rapidas_pendientes": sesion.scalar(
            select(func.count()).select_from(Venta).where(
                Venta.estado == EstadoVenta.PENDIENTE_FORMALIZAR
            )
        ),
    }


def _seccion_compras(sesion: Session, hoy: date) -> dict:
    from modules.compras.models import EstadoOrdenCompra, OrdenCompra

    ordenes = sesion.scalars(
        select(OrdenCompra)
        .where(
            OrdenCompra.estado.in_([EstadoOrdenCompra.PENDIENTE, EstadoOrdenCompra.EN_CAMINO]),
            OrdenCompra.fecha_estimada_llegada.is_not(None),
        )
        .options(selectinload(OrdenCompra.proveedor))
        .order_by(OrdenCompra.fecha_estimada_llegada)
        .limit(MAX_PEDIDOS)
    ).all()

    manana = hoy + timedelta(days=1)
    de_manana = [o for o in ordenes if o.fecha_estimada_llegada == manana]
    if not de_manana:
        motivo = "Mañana no llega ningún pedido"
    elif len(de_manana) == 1:
        motivo = f"Llega pedido de {de_manana[0].proveedor.nombre}"
    else:
        motivo = f"Llegan {len(de_manana)} pedidos: " + ", ".join(o.proveedor.nombre for o in de_manana)

    return {
        "proyeccion_manana": sum((o.monto_total for o in de_manana), CERO),
        "motivo_proyeccion": motivo,
        "pedidos_por_llegar": [
            PedidoPorLlegar(
                id=o.id,
                proveedor=o.proveedor.nombre,
                fecha_estimada=o.fecha_estimada_llegada,
                monto=o.monto_total,
            )
            for o in ordenes
        ],
    }


def calcular_resumen(sesion: Session, hoy: date) -> ResumenDashboard:
    datos: dict = {
        "ventas_hoy": CERO,
        "ventas_cerradas": 0,
        "ordenes_activas": [],
        "fiados_por_cobrar": CERO,
        "clientes_con_fiado": 0,
        "ventas_rapidas_pendientes": 0,
        "proyeccion_manana": CERO,
        "motivo_proyeccion": "Aún no hay pedidos por llegar",
        "pedidos_por_llegar": [],
    }
    no_disponibles = []
    for nombre, seccion in (("ventas", _seccion_ventas), ("compras", _seccion_compras)):
        try:
            datos.update(seccion(sesion, hoy))
        except Exception:  # noqa: BLE001 — un módulo caído no tumba la caja
            sesion.rollback()
            no_disponibles.append(nombre)
    return ResumenDashboard(**datos, secciones_no_disponibles=no_disponibles)
