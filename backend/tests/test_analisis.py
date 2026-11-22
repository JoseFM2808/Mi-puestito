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
        json={"uuid": producto, "nombre": "Fideos", "unidad": "unidad", "stock_inicial": "0", "categoria": " abarrotes "},
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
    datos = analisis(h, "mes")
    assert datos["mejores_productos"] == [{"nombre": "Fideos", "vendido": "10.00", "ganancia_estimada": "4.00"}]
    # La categoría se escribe como sea y se agrupa con la primera letra en mayúscula
    assert datos["por_categoria"] == [{"categoria": "Abarrotes", "vendido": "10.00", "ganancia_estimada": "4.00"}]


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


# ---- Kardex mensual del inventario ----


def _mover(sesion, producto, delta, motivo, cuando, origen="prueba"):
    from modules.inventario.models import MovimientoInventario

    sesion.add(
        MovimientoInventario(
            producto_id=producto.id,
            delta=delta,
            motivo=motivo,
            origen_tipo=origen,
            origen_ref=uuid(),
            creado_en=cuando,
        )
    )


def test_kardex_del_mes_cuadra_con_el_libro_de_movimientos():
    from datetime import datetime, timezone
    from decimal import Decimal as D

    from database import sesion_para
    from modules.analisis.servicio import kardex_del_mes
    from modules.inventario.models import MotivoMovimiento as M
    from modules.inventario.models import Producto, Unidad

    def utc(dia, hora=15):
        return datetime(2026, dia[0], dia[1], hora, tzinfo=timezone.utc)

    with sesion_para("anita") as sesion:
        arroz = Producto(nombre="Arroz", unidad=Unidad.KG)
        leche = Producto(nombre="Leche", unidad=Unidad.UNIDAD)
        sesion.add_all([arroz, leche])
        sesion.flush()
        _mover(sesion, arroz, D("50"), M.AJUSTE, utc((10, 20)))  # registrado en octubre
        _mover(sesion, arroz, D("-5"), M.VENTA, utc((10, 25)))
        _mover(sesion, arroz, D("20"), M.COMPRA, utc((11, 3)))
        _mover(sesion, arroz, D("-8.5"), M.VENTA, utc((11, 4)))
        _mover(sesion, arroz, D("1.5"), M.ANULACION_VENTA, utc((11, 4)))  # se quitó de una orden
        _mover(sesion, arroz, D("-2"), M.MERMA, utc((11, 5)))
        _mover(sesion, arroz, D("-1"), M.AJUSTE, utc((11, 6)))  # conteo
        _mover(sesion, arroz, D("-3"), M.VENTA, utc((12, 1)))  # diciembre: no cuenta
        # 1 de noviembre a las 02:00 UTC todavía es 31 de octubre en Lima
        _mover(sesion, leche, D("12"), M.AJUSTE, datetime(2026, 11, 1, 2, tzinfo=timezone.utc), "stock_inicial")
        _mover(sesion, leche, D("6"), M.AJUSTE, utc((11, 10)), "stock_inicial")  # no pasa, pero se separa igual
        sesion.commit()

        kardex = kardex_del_mes(sesion, "2026-11", hoy=date(2026, 12, 2))

    assert (kardex.mes, kardex.desde, kardex.hasta) == ("2026-11", date(2026, 11, 1), date(2026, 11, 30))
    arroz_k, leche_k = kardex.productos
    assert (arroz_k.nombre, arroz_k.unidad) == ("Arroz", "kg")
    assert (arroz_k.inicial, arroz_k.compras, arroz_k.vendido, arroz_k.mermas, arroz_k.ajustes, arroz_k.final) == (
        D("45"), D("20"), D("7"), D("2"), D("-1"), D("55")
    )
    # El registro del 31 de octubre (hora de Lima) ya es parte de lo que había; el de noviembre va aparte
    assert (leche_k.inicial, leche_k.registrado, leche_k.ajustes, leche_k.final) == (D("12"), D("6"), D("0"), D("18"))


def test_el_kardex_del_mes_actual_llega_hasta_hoy_y_un_mes_futuro_no_existe(h):
    r = cliente.get("/api/analisis/kardex", headers=h)
    assert r.status_code == 200
    assert r.json()["productos"] == []
    assert cliente.get("/api/analisis/kardex?mes=2999-01", headers=h).status_code == 422
    assert cliente.get("/api/analisis/kardex?mes=2026-13", headers=h).status_code == 422


def test_la_categoria_se_cambia_y_se_quita(h):
    producto = uuid()
    cliente.post("/api/inventario/productos", json={"uuid": producto, "nombre": "Leche"}, headers=h)
    r = cliente.patch(f"/api/inventario/productos/{producto}", json={"categoria": "lácteos"}, headers=h)
    assert r.json()["categoria"] == "Lácteos"
    r = cliente.patch(f"/api/inventario/productos/{producto}", json={"precio_venta": "4.00"}, headers=h)
    assert r.json()["categoria"] == "Lácteos"  # omitirla no la toca
    r = cliente.patch(f"/api/inventario/productos/{producto}", json={"categoria": "  "}, headers=h)
    assert r.json()["categoria"] is None
