"""Inventario (ADR-031): libro de movimientos, idempotencia, aislamiento de
módulos y ausencia de condiciones de carrera en el stock."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import eventos
from main import app


def nuevo() -> str:
    return str(uuid4())


@pytest.fixture()
def api(cabeceras_anita):
    with TestClient(app) as cliente_http:
        cliente_http.headers.update(cabeceras_anita)
        yield cliente_http


def crear_producto(api, nombre="Arroz", unidad="kg", stock="10", **extra) -> str:
    uuid = nuevo()
    respuesta = api.post(
        "/api/inventario/productos",
        json={"uuid": uuid, "nombre": nombre, "unidad": unidad, "stock_inicial": stock, **extra},
    )
    assert respuesta.status_code == 201, respuesta.text
    return uuid


def producto(api, uuid) -> dict:
    return next(p for p in api.get("/api/inventario/productos").json() if p["uuid"] == uuid)


def vender(api, producto_uuid, cantidad, monto="1.00", item=None):
    orden = nuevo()
    api.post("/api/ventas/", json={"uuid": orden, "tipo": "orden_activa"})
    return orden, api.post(
        f"/api/ventas/{orden}/items",
        json={
            "uuid": item or nuevo(), "nombre_producto": "Arroz", "monto": monto,
            "producto_uuid": producto_uuid, "cantidad_num": cantidad,
        },
    )


def test_vender_descuenta_del_stock(api):
    arroz = crear_producto(api, stock="10")
    vender(api, arroz, "2.5")
    assert producto(api, arroz)["stock_actual"] == "7.500"


def test_quitar_el_item_devuelve_el_stock(api):
    arroz = crear_producto(api, stock="10")
    item = nuevo()
    orden, _ = vender(api, arroz, "3", item=item)
    api.delete(f"/api/ventas/{orden}/items/{item}")
    assert producto(api, arroz)["stock_actual"] == "10.000"
    motivos = [m["motivo"] for m in api.get(f"/api/inventario/productos/{arroz}/movimientos").json()]
    assert motivos == ["anulacion_venta", "venta", "ajuste"]


def test_reenviar_la_venta_no_descuenta_dos_veces(api):
    arroz = crear_producto(api, stock="10")
    item = nuevo()
    orden, _ = vender(api, arroz, "1", item=item)
    cuerpo = {"uuid": item, "nombre_producto": "Arroz", "monto": "1.00", "producto_uuid": arroz, "cantidad_num": "1"}
    api.post(f"/api/ventas/{orden}/items", json=cuerpo)
    api.post(f"/api/ventas/{orden}/items", json=cuerpo)
    assert producto(api, arroz)["stock_actual"] == "9.000"


def test_vender_mas_de_lo_que_hay_se_guarda_con_aviso(api):
    # La venta ocurrió: el sistema no la rechaza, marca el descuadre
    arroz = crear_producto(api, stock="1")
    _, respuesta = vender(api, arroz, "3")
    assert respuesta.status_code == 201
    assert "cuenta cuánto hay" in respuesta.json()["avisos"][0]
    assert [p["nombre"] for p in api.get("/api/inventario/descuadres").json()] == ["Arroz"]
    assert producto(api, arroz)["descuadre"] is True


def test_el_conteo_fisico_ajusta_contra_el_stock_del_momento(api):
    arroz = crear_producto(api, stock="10")
    vender(api, arroz, "4")
    ajuste = nuevo()
    respuesta = api.post("/api/inventario/ajustes", json={"uuid": ajuste, "producto_uuid": arroz, "contado": "5"})
    assert respuesta.json()["diferencia"] == "-1.000"
    # Reenviar el mismo conteo no vuelve a ajustar
    api.post("/api/inventario/ajustes", json={"uuid": ajuste, "producto_uuid": arroz, "contado": "5"})
    assert producto(api, arroz)["stock_actual"] == "5.000"


def test_merma_y_stock_minimo(api):
    arroz = crear_producto(api, stock="5", stock_minimo="3")
    api.post("/api/inventario/mermas", json={"uuid": nuevo(), "producto_uuid": arroz, "cantidad": "2", "nota": "Se mojó"})
    assert producto(api, arroz)["bajo_minimo"] is True
    assert [p["nombre"] for p in api.get("/api/inventario/productos", params={"solo_bajo_minimo": True}).json()] == ["Arroz"]


def test_nombres_de_producto_no_se_repiten(api):
    crear_producto(api, nombre="Arroz")
    respuesta = api.post("/api/inventario/productos", json={"uuid": nuevo(), "nombre": "arroz"})
    assert respuesta.status_code == 409


def test_vender_sin_producto_no_toca_el_inventario(api):
    arroz = crear_producto(api, stock="10")
    orden = nuevo()
    api.post("/api/ventas/", json={"uuid": orden, "tipo": "orden_activa"})
    api.post(f"/api/ventas/{orden}/items", json={"uuid": nuevo(), "nombre_producto": "Arroz", "monto": "5.00"})
    assert producto(api, arroz)["stock_actual"] == "10.000"


def test_producto_inexistente_avisa_y_la_venta_sigue(api):
    _, respuesta = vender(api, nuevo(), "1")
    assert respuesta.status_code == 201
    assert "no está en el inventario" in respuesta.json()["avisos"][0]


def test_si_inventario_falla_la_venta_se_guarda_igual(api, monkeypatch):
    # "El fallo de un módulo no derriba a otro", dentro de una transacción
    def roto(_sesion, _datos):
        raise RuntimeError("disco lleno")

    monkeypatch.setitem(eventos._suscriptores["venta.item_registrado"], "inventario.descontar", roto)
    arroz = crear_producto(api, stock="10")
    orden, respuesta = vender(api, arroz, "1", monto="4.00")
    assert respuesta.status_code == 201
    assert api.get(f"/api/ventas/{orden}").json()["monto_total"] == "4.00"
    assert producto(api, arroz)["stock_actual"] == "10.000"
    assert "inventario.descontar" in api.get("/api/salud").json()["eventos_con_fallas"]
    eventos.fallos.clear()


def test_la_conciliacion_esta_vacia(api):
    arroz = crear_producto(api, stock="10")
    for _ in range(3):
        vender(api, arroz, "1.25")
    assert api.get("/api/inventario/conciliacion").json() == []


def _producto_con_stock(stock: str) -> str:
    from database import sesion_escritura_para
    from modules.inventario.schemas import ProductoEntrada
    from modules.inventario.servicio import crear_producto

    with sesion_escritura_para("anita") as sesion:
        producto, _ = crear_producto(
            sesion, ProductoEntrada(uuid=nuevo(), nombre="Arroz", unidad="kg", stock_inicial=Decimal(stock))
        )
        return producto.uuid


def test_ventas_simultaneas_no_pierden_descuentos():
    """Condición de carrera (auditor #1): muchos hilos venden el mismo producto
    a la vez, cada uno con su propia sesión y transacción, como FastAPI con
    varias peticiones en paralelo. El stock final debe ser exacto."""
    import modules.inventario.router  # noqa: F401 — registra la suscripción
    from database import sesion_escritura_para
    from modules.inventario.models import Producto
    from modules.inventario.servicio import conciliar
    from modules.ventas import servicio
    from modules.ventas.schemas import ItemEntrada, VentaEntrada

    arroz = _producto_con_stock("100")

    def vender_uno(_):
        with sesion_escritura_para("anita") as sesion:
            orden, _ = servicio.crear_venta(sesion, VentaEntrada(uuid=nuevo(), tipo="orden_activa"))
            servicio.agregar_item(
                sesion, orden.uuid,
                ItemEntrada(uuid=nuevo(), nombre_producto="Arroz", monto=Decimal("1"),
                            producto_uuid=arroz, cantidad_num=Decimal("0.5")),
            )

    with ThreadPoolExecutor(max_workers=8) as hilos:
        list(hilos.map(vender_uno, range(40)))

    with sesion_escritura_para("anita") as sesion:
        final = sesion.query(Producto).filter_by(uuid=arroz).one()
        assert final.stock_actual == Decimal("80.000")  # 100 − 40 × 0.5
        assert conciliar(sesion) == []


def test_items_simultaneos_en_la_misma_orden_suman_bien():
    """El total de una orden se recalcula leyendo sus items y escribiendo la
    suma: sin BEGIN IMMEDIATE, dos meseros agregando a la vez se pisarían."""
    from database import sesion_escritura_para
    from modules.ventas import servicio
    from modules.ventas.schemas import ItemEntrada, VentaEntrada

    with sesion_escritura_para("anita") as sesion:
        orden, _ = servicio.crear_venta(sesion, VentaEntrada(uuid=nuevo(), tipo="orden_activa"))
        orden_uuid = orden.uuid

    def agregar_uno(_):
        with sesion_escritura_para("anita") as sesion:
            servicio.agregar_item(
                sesion, orden_uuid, ItemEntrada(uuid=nuevo(), nombre_producto="Menú", monto=Decimal("2.50"))
            )

    with ThreadPoolExecutor(max_workers=8) as hilos:
        list(hilos.map(agregar_uno, range(40)))

    with sesion_escritura_para("anita") as sesion:
        venta = servicio.buscar_venta(sesion, orden_uuid)
        assert len(venta.items) == 40
        assert venta.monto_total == Decimal("100.00")
