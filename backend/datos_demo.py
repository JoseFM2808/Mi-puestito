"""Datos de muestra del proyecto "demo" (nunca de un proyecto real).

Son los mismos que la Demo 1 mostraba fijos en pantalla (Restaurante Doña
Carmen, Sra. Flora, Distribuidora Norte…), pero ahora guardados como ventas,
clientes y pedidos de verdad en la base de demo. Así el Dashboard de demo se
calcula igual que el de un negocio real, y lo que el operador practique en
demo (abrir órdenes, cobrar, fiar) se refleja en su caja.

Se cargan UNA vez, cuando la base de demo está vacía. Las fechas son
relativas al momento de cargarlas (el día peruano de ese momento).
"""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from database import sesion_para
from fechas import ahora_utc, dia_peruano, rango_utc_del_dia
from proyectos import PROYECTOS

D = Decimal

# 9 ventas cobradas + 3 ventas rápidas por completar = 12 ventas, S/ 485.50
VENTAS_COBRADAS = [
    ("Menú del día x3", D("45.00")), ("Pollo 1.5 kg", D("38.50")), ("Abarrotes varios", D("52.00")),
    ("Verduras", D("27.50")), ("Pedido restaurante", D("61.00")), ("Frutas", D("33.00")),
    ("Carne 1 kg", D("48.50")), ("Arroz 5 kg + aceite", D("55.00")), ("Lácteos", D("41.00")),
]
VENTAS_RAPIDAS = [D("22.00"), D("29.50"), D("32.50")]

# Clientes con fiado: deuda = fiado − abonos. Total S/ 132.50 entre 4.
FIADOS = [
    ("Sra. Flora", "987654321", D("80.00"), [D("60.00")], [D("15.00")]),
    ("Don Julio", None, None, [D("30.00")], []),
    ("Sra. Rosa", None, None, [D("20.00"), D("12.50")], []),
    ("Luis (mototaxi)", None, None, [D("25.00")], []),
]


def _hora_de_hoy(indice: int, total: int) -> datetime:
    """Un momento de hoy (Lima) antes de ahora, repartido entre las ventas."""
    inicio, _ = rango_utc_del_dia(dia_peruano())
    ahora = ahora_utc()
    tramo = (ahora - inicio) / (total + 1)
    return inicio + tramo * (indice + 1)


def cargar_si_vacio() -> bool:
    """Carga los datos de muestra en demo si su base está vacía. True si cargó."""
    if "demo" not in PROYECTOS or PROYECTOS["demo"].es_real:
        return False

    from modules.compras.models import (
        EstadoOrdenCompra,
        EstadoRecepcion,
        ItemOrdenCompra,
        OrdenCompra,
        Proveedor,
    )
    from modules.ventas.models import (
        Cliente,
        EstadoVenta,
        ItemVenta,
        MetodoPago,
        Pago,
        TipoVenta,
        Venta,
    )

    sesion = sesion_para("demo")
    try:
        hay_algo = sesion.scalar(select(func.count()).select_from(Venta)) or sesion.scalar(
            select(func.count()).select_from(Proveedor)
        )
        if hay_algo:
            return False

        hoy = dia_peruano()
        total = len(VENTAS_COBRADAS) + len(VENTAS_RAPIDAS) + 4
        momento = iter(_hora_de_hoy(i, total) for i in range(total))

        for nombre, monto in VENTAS_COBRADAS:
            cuando = next(momento)
            sesion.add(Venta(
                tipo=TipoVenta.ORDEN_ACTIVA, estado=EstadoVenta.PAGADA_CERRADA, monto_total=monto,
                metodo_pago=MetodoPago.EFECTIVO, abierta_en=cuando, cerrada_en=cuando,
                items=[ItemVenta(nombre_producto=nombre, monto=monto)],
                pagos=[Pago(monto=monto, metodo_pago=MetodoPago.EFECTIVO, creado_en=cuando)],
            ))
        for monto in VENTAS_RAPIDAS:
            cuando = next(momento)
            sesion.add(Venta(
                tipo=TipoVenta.VENTA_RAPIDA, estado=EstadoVenta.PENDIENTE_FORMALIZAR,
                monto_total=monto, metodo_pago=MetodoPago.YAPE_PLIN, abierta_en=cuando, cerrada_en=cuando,
                pagos=[Pago(monto=monto, metodo_pago=MetodoPago.YAPE_PLIN, creado_en=cuando)],
            ))

        hace_una_semana = ahora_utc() - timedelta(days=7)
        clientes = {}
        for nombre, telefono, limite, fiados, abonos in FIADOS:
            cliente = Cliente(nombre=nombre, telefono=telefono, limite_credito=limite,
                              creado_en=hace_una_semana)
            clientes[nombre] = cliente
            for monto in fiados:
                sesion.add(Venta(
                    tipo=TipoVenta.FIADO, cliente=cliente, estado=EstadoVenta.FIADA, monto_total=monto,
                    abierta_en=hace_una_semana, cerrada_en=hace_una_semana,
                    items=[ItemVenta(nombre_producto="Abarrotes", monto=monto)],
                ))
            for monto in abonos:
                sesion.add(Pago(cliente=cliente, monto=monto, creado_en=hace_una_semana + timedelta(days=3)))

        # Órdenes abiertas ahora mismo (el panel de órdenes activas)
        abiertas = [
            (TipoVenta.ORDEN_ACTIVA, None, "Restaurante Doña Carmen", [
                ("Pollo", "1 kg", D("18.00")), ("Papa amarilla", "5 kg", D("20.00")),
                ("Arroz", "5 kg", D("24.00")), ("Aceite", "1 L", D("12.00")), ("Cebolla", "3 kg", D("12.00")),
            ]),
            (TipoVenta.ORDEN_ACTIVA, None, None, [
                ("Gaseosa", "2 L", D("9.50")), ("Pan", "20 unid.", D("14.00")),
            ]),
            (TipoVenta.FIADO, clientes["Sra. Flora"], None, [
                ("Leche", "2 tarros", D("8.00")), ("Azúcar", "1 kg", D("4.00")),
            ]),
        ]
        for tipo, cliente, nombre_orden, items in abiertas:
            cuando = next(momento)
            sesion.add(Venta(
                tipo=tipo, cliente=cliente, nombre_orden=nombre_orden, estado=EstadoVenta.ABIERTA,
                monto_total=sum((m for _, _, m in items), D("0")), abierta_en=cuando,
                items=[ItemVenta(nombre_producto=n, cantidad=c, monto=m) for n, c, m in items],
            ))

        # Pedidos a proveedores: uno mañana (la proyección), uno pasado, uno atrasado
        # Teléfonos ficticios: el botón "Llamar" de la demo no debe sonarle a nadie
        norte = Proveedor(nombre="Distribuidora Norte", ruc="20123456789", telefono="900000001")
        pedidos = [
            (norte, 1, EstadoOrdenCompra.EN_CAMINO,
             [("Arroz", "2 sacos", D("180.00")), ("Aceite", "1 caja", D("140.00"))]),
            (Proveedor(nombre="Avícola San Pedro", telefono="900000002"), 2, EstadoOrdenCompra.PENDIENTE,
             [("Pollo", "15 kg", D("145.00"))]),
            (Proveedor(nombre="Abarrotes El Sol"), -1, EstadoOrdenCompra.EN_CAMINO,
             [("Azúcar", "1 saco", D("88.00"))]),
            (norte, -7, EstadoOrdenCompra.CERRADA,
             [("Arroz", "2 sacos", D("175.00")), ("Fideos", "1 caja", D("60.00"))]),
        ]
        for proveedor, dias, estado, items in pedidos:
            total = sum((m for _, _, m in items), D("0"))
            cerrada = estado == EstadoOrdenCompra.CERRADA
            sesion.add(OrdenCompra(
                proveedor=proveedor, estado=estado,
                fecha_estimada_llegada=hoy + timedelta(days=dias),
                monto_total=total, monto_real=total if cerrada else None,
                creado_en=ahora_utc() + timedelta(days=min(dias, 0)),
                items=[
                    ItemOrdenCompra(
                        nombre_producto=n, cantidad=c, monto=m,
                        estado_recepcion=EstadoRecepcion.RECIBIDO if cerrada else EstadoRecepcion.PENDIENTE,
                    )
                    for n, c, m in items
                ],
            ))

        sesion.commit()
        return True
    finally:
        sesion.close()


def reiniciar() -> None:
    """Borra lo practicado en demo y vuelve a sembrar con las fechas de hoy (D-19).

    Solo actúa sobre el proyecto de práctica: un negocio real nunca pasa por aquí.
    """
    if "demo" not in PROYECTOS or PROYECTOS["demo"].es_real:
        raise ValueError("Solo se reinicia un proyecto de práctica")

    # Registran sus tablas en Base.metadata aunque el módulo aún no se haya importado
    from database import Base, sesion_escritura_para
    from modules.compras import models as _compras  # noqa: F401
    from modules.inventario import models as _inventario  # noqa: F401
    from modules.ventas import models as _ventas  # noqa: F401

    sesion = sesion_escritura_para("demo")
    try:
        for tabla in reversed(Base.metadata.sorted_tables):
            sesion.execute(tabla.delete())
        sesion.commit()
    finally:
        sesion.close()
    cargar_si_vacio()
