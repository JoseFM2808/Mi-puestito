"""Análisis (Fase 7): ¿el puesto es rentable?"""

from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app

cliente = TestClient(app)


def uuid() -> str:
    return str(uuid4())


@pytest.fixture()
def h(cabeceras_anita):
    # Negocio sin datos de muestra: cada test ve solo lo que crea
    return cabeceras_anita


def analisis(h, periodo="semana") -> dict:
    r = cliente.get(f"/api/analisis?periodo={periodo}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_vendido_menos_proveedores_y_gastos_es_lo_que_queda_libre(h):
    cliente.post(
        "/api/ventas/",
        json={"uuid": uuid(), "tipo": "venta_rapida", "monto": "30.00", "metodo_pago": "efectivo"},
        headers=h,
    )
    for monto, ambito, categoria in (("5.00", "puesto", "transporte"), ("7.00", "hogar", "alimentacion")):
        cliente.post(
            "/api/gastos",
            json={"uuid": uuid(), "monto": monto, "medio": "efectivo", "ambito": ambito, "categoria": categoria},
            headers=h,
        )
    # Un pedido pagado al proveedor llega como gasto de categoría proveedor (ADR-051)
    prov = cliente.post("/api/compras/proveedores", json={"uuid": uuid(), "nombre": "Sur"}, headers=h).json()
    orden = cliente.post(
        "/api/compras/ordenes",
        json={
            "uuid": uuid(),
            "proveedor_uuid": prov["uuid"],
            "items": [{"uuid": uuid(), "nombre_producto": "Arroz", "cantidad": "1 saco", "monto": "20.00"}],
        },
        headers=h,
    ).json()["orden"]
    items = [{"item_uuid": i["uuid"], "estado": "recibido"} for i in orden["items"]]
    cliente.post(f"/api/compras/ordenes/{orden['uuid']}/recepcion", json={"items": items}, headers=h)
    cliente.post(f"/api/compras/ordenes/{orden['uuid']}/cerrar", json={"medio": "efectivo"}, headers=h)

    datos = analisis(h)
    assert (datos["vendido"], datos["ventas"]) == ("30.00", 1)
    assert (datos["pagado_a_proveedores"], datos["gastos_del_puesto"], datos["gastos_de_la_casa"]) == (
        "20.00",
        "5.00",
        "7.00",
    )
    assert (datos["resultado_del_negocio"], datos["libre"]) == ("5.00", "-2.00")
    hoy = next(d for d in datos["por_dia"] if d["vendido"] != "0.00")
    assert (hoy["vendido"], hoy["gastado"]) == ("30.00", "32.00")


def test_la_ganancia_por_producto_usa_el_costo_de_la_ultima_compra(h):
    producto = uuid()
    cliente.post(
        "/api/inventario/productos",
        json={"uuid": producto, "nombre": "Fideos", "unidad": "unidad", "stock_inicial": "0"},
        headers=h,
    )
    # Compra de 10 unidades por S/ 30.00 → costo S/ 3.00 cada una (D-22)
    prov = cliente.post("/api/compras/proveedores", json={"uuid": uuid(), "nombre": "Sur"}, headers=h).json()
    orden = cliente.post(
        "/api/compras/ordenes",
        json={
            "uuid": uuid(),
            "proveedor_uuid": prov["uuid"],
            "items": [{"uuid": uuid(), "nombre_producto": "Fideos", "cantidad": "1 caja", "monto": "30.00"}],
        },
        headers=h,
    ).json()["orden"]
    items = [{"item_uuid": orden["items"][0]["uuid"], "estado": "recibido", "cantidad_stock": "10"}]
    cliente.post(f"/api/compras/ordenes/{orden['uuid']}/recepcion", json={"items": items}, headers=h)
    # Se venden 2 a S/ 5.00 cada uno
    venta = uuid()
    cliente.post("/api/ventas/", json={"uuid": venta, "tipo": "orden_activa"}, headers=h)
    cliente.post(
        f"/api/ventas/{venta}/items",
        json={"uuid": uuid(), "nombre_producto": "Fideos", "monto": "10.00", "producto_uuid": producto, "cantidad_num": "2"},
        headers=h,
    )
    cliente.post(f"/api/ventas/{venta}/cobrar", json={"metodo_pago": "efectivo"}, headers=h)
    assert analisis(h, "mes")["mejores_productos"] == [
        {"nombre": "Fideos", "vendido": "10.00", "ganancia_estimada": "4.00"}
    ]


@pytest.mark.parametrize(
    ("periodo", "hoy", "desde", "hasta"),
    [
        ("semana", date(2026, 11, 19), date(2026, 11, 16), date(2026, 11, 19)),  # jueves → desde el lunes
        ("mes", date(2026, 11, 19), date(2026, 11, 1), date(2026, 11, 19)),
        ("mes_pasado", date(2026, 3, 5), date(2026, 2, 1), date(2026, 2, 28)),
        ("mes_pasado", date(2026, 1, 10), date(2025, 12, 1), date(2025, 12, 31)),
    ],
)
def test_los_periodos_van_por_dia_peruano(periodo, hoy, desde, hasta):
    from modules.analisis.servicio import rango

    assert rango(periodo, hoy) == (desde, hasta)


def test_si_un_modulo_falla_el_analisis_igual_responde(h, monkeypatch):
    from modules.analisis import servicio

    def roto(*_):
        raise RuntimeError("gastos caído")

    monkeypatch.setattr(servicio, "_gastos", roto)
    datos = analisis(h)
    assert datos["no_disponibles"] == ["gastos"]
    assert datos["libre"] == datos["vendido"]


def test_un_periodo_desconocido_se_rechaza(h):
    assert cliente.get("/api/analisis?periodo=anio", headers=h).status_code == 422
