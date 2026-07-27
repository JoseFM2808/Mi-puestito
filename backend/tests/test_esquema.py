"""Garantías del esquema: nada de dinero suelto ni filas huérfanas.

Estas reglas son baratas hoy y caras después: añadirlas cuando ya existan
ventas reales obligaría a migrar la base de datos del vendedor.

Se prueban contra el proyecto "demo": el esquema es idéntico para todos los
proyectos (demo, anita, o cualquier otro que se registre después).
"""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import sesion_para
from modules.compras.models import ItemOrdenCompra, OrdenCompra, Proveedor
from modules.ventas.models import Cliente, ItemVenta, Pago, TipoVenta, Venta


@pytest.fixture()
def sesion():
    s = sesion_para("demo")
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def test_un_pago_no_puede_quedar_sin_destino(sesion):
    # Dinero registrado a nadie haría mentir a la deuda derivada
    sesion.add(Pago(venta_id=None, cliente_id=None, monto=Decimal("10.00")))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_un_fiado_exige_cliente(sesion):
    # Un fiado sin cliente no se podría cobrar nunca
    sesion.add(Venta(tipo=TipoVenta.FIADO, monto_total=Decimal("20.00")))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_una_venta_rapida_no_exige_cliente(sesion):
    sesion.add(Venta(tipo=TipoVenta.VENTA_RAPIDA, monto_total=Decimal("20.00")))
    sesion.commit()  # no debe lanzar


def test_borrar_una_venta_se_lleva_sus_items_y_pagos(sesion):
    cliente = Cliente(nombre="Sra. Flora")
    venta = Venta(tipo=TipoVenta.FIADO, cliente=cliente, monto_total=Decimal("30.00"))
    venta.items.append(ItemVenta(nombre_producto="Arroz", monto=Decimal("30.00")))
    venta.pagos.append(Pago(cliente=cliente, monto=Decimal("10.00")))
    sesion.add(venta)
    sesion.commit()

    sesion.delete(venta)
    sesion.commit()

    assert sesion.scalars(select(ItemVenta)).all() == []
    assert sesion.scalars(select(Pago)).all() == []
    # El cliente sobrevive: su historial se borra, su ficha no
    assert sesion.scalars(select(Cliente)).all() != []


def test_no_se_registra_dos_veces_el_mismo_ruc(sesion):
    sesion.add(Proveedor(nombre="Distribuidora Norte", ruc="20123456789"))
    sesion.commit()
    sesion.add(Proveedor(nombre="Distribuidora Norte S.A.", ruc="20123456789"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_varios_proveedores_pueden_no_tener_ruc(sesion):
    # El RUC es opcional: dos proveedores informales sin RUC conviven
    sesion.add_all([Proveedor(nombre="Casera del mercado"), Proveedor(nombre="Don Julio")])
    sesion.commit()  # no debe lanzar


def test_borrar_una_orden_se_lleva_sus_items(sesion):
    proveedor = Proveedor(nombre="Avícola San Pedro")
    orden = OrdenCompra(proveedor=proveedor, monto_total=Decimal("145.00"))
    orden.items.append(ItemOrdenCompra(nombre_producto="Pollo", monto=Decimal("145.00")))
    sesion.add(orden)
    sesion.commit()

    sesion.delete(orden)
    sesion.commit()

    assert sesion.scalars(select(ItemOrdenCompra)).all() == []
