"""Módulo Compras: alta de proveedores, pedidos y checklist de recepción (D-16)."""

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


def proveedor(h, **campos) -> dict:
    cuerpo = {"uuid": uuid(), "nombre": "Distribuidora Sur", **campos}
    r = cliente.post("/api/compras/proveedores", json=cuerpo, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def pedido(h, prov: dict, items: list[tuple[str, str]] | None = None, **campos) -> dict:
    cuerpo = {
        "uuid": uuid(),
        "proveedor_uuid": prov["uuid"],
        "items": [
            {"uuid": uuid(), "nombre_producto": n, "cantidad": "1 saco", "monto": m}
            for n, m in (items or [("Arroz", "100.00"), ("Azúcar", "50.50")])
        ],
        **campos,
    }
    r = cliente.post("/api/compras/ordenes", json=cuerpo, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["orden"]


def recibir(h, orden: dict, *estados: dict | str):
    items = []
    for item, estado in zip(orden["items"], estados, strict=True):
        extra = estado if isinstance(estado, dict) else {"estado": estado}
        items.append({"item_uuid": item["uuid"], **extra})
    return cliente.post(f"/api/compras/ordenes/{orden['uuid']}/recepcion", json={"items": items}, headers=h)


# ---- Proveedores ----

def test_registrar_proveedor_es_idempotente_y_no_exige_ruc(h):
    cuerpo = {"uuid": uuid(), "nombre": "Avícola Norte", "telefono": "999111222"}
    assert cliente.post("/api/compras/proveedores", json=cuerpo, headers=h).status_code == 201
    r = cliente.post("/api/compras/proveedores", json=cuerpo, headers=h)
    assert r.status_code == 200
    assert len(cliente.get("/api/compras/proveedores", headers=h).json()) == 1


def test_el_mismo_ruc_no_se_registra_dos_veces(h):
    proveedor(h, ruc="20123456789", nombre="Norte SAC")
    r = cliente.post(
        "/api/compras/proveedores",
        json={"uuid": uuid(), "nombre": "Otro", "ruc": "20123456789"},
        headers=h,
    )
    assert r.status_code == 409
    assert "Norte SAC" in r.json()["detail"]


@pytest.mark.parametrize("ruc", ["123", "2012345678a", "201234567890"])
def test_un_ruc_mal_escrito_se_rechaza(h, ruc):
    r = cliente.post("/api/compras/proveedores", json={"uuid": uuid(), "nombre": "X", "ruc": ruc}, headers=h)
    assert r.status_code == 422


def test_buscar_proveedor_por_nombre_empresa_o_ruc(h):
    proveedor(h, nombre="Juana", empresa="Abarrotes El Sol", ruc="20999999999")
    proveedor(h, nombre="Pedro", empresa="Avícola Luna")
    for busqueda, esperado in (("juan", "Juana"), ("LUNA", "Pedro"), ("20999", "Juana")):
        r = cliente.get("/api/compras/proveedores", params={"busqueda": busqueda}, headers=h)
        assert [p["nombre"] for p in r.json()] == [esperado]


def test_sugiere_lo_que_mas_se_le_pide_a_ese_proveedor(h):
    sur, otro = proveedor(h), proveedor(h, nombre="Otro")
    pedido(h, sur, [("Arroz", "100.00"), ("Aceite", "40.00")])
    pedido(h, sur, [("arroz", "120.00")])  # mismo producto aunque cambien las mayúsculas
    pedido(h, otro, [("Pollo", "50.00")])
    frecuentes = cliente.get(f"/api/compras/proveedores/{sur['uuid']}/frecuentes", headers=h).json()
    assert [(f["nombre_producto"], f["veces"]) for f in frecuentes] == [("arroz", 2), ("Aceite", 1)]
    assert frecuentes[0]["monto"] == "120.00"  # el de la última vez


def test_un_borrador_no_alimenta_las_sugerencias(h):
    sur = proveedor(h)
    pedido(h, sur, [("Arroz", "100.00")], estado="borrador")
    assert cliente.get(f"/api/compras/proveedores/{sur['uuid']}/frecuentes", headers=h).json() == []


# ---- Órdenes ----

def test_el_total_lo_calcula_el_servidor(h):
    orden = pedido(h, proveedor(h), monto_total="1.00")  # un total del cliente se ignora
    assert orden["monto_total"] == "150.50"
    assert orden["estado"] == "pendiente"
    assert orden["monto_real"] is None


def test_crear_orden_es_idempotente(h):
    sur = proveedor(h)
    cuerpo = {
        "uuid": uuid(),
        "proveedor_uuid": sur["uuid"],
        "items": [{"uuid": uuid(), "nombre_producto": "Arroz", "monto": "10.00"}],
    }
    assert cliente.post("/api/compras/ordenes", json=cuerpo, headers=h).status_code == 201
    assert cliente.post("/api/compras/ordenes", json=cuerpo, headers=h).status_code == 200
    assert len(cliente.get("/api/compras/ordenes", headers=h).json()) == 1


def test_una_orden_necesita_proveedor_existente_y_productos(h):
    item = {"uuid": uuid(), "nombre_producto": "Arroz", "monto": "10.00"}
    r = cliente.post(
        "/api/compras/ordenes", json={"uuid": uuid(), "proveedor_uuid": uuid(), "items": [item]}, headers=h
    )
    assert r.status_code == 404
    r = cliente.post(
        "/api/compras/ordenes",
        json={"uuid": uuid(), "proveedor_uuid": proveedor(h)["uuid"], "items": []},
        headers=h,
    )
    assert r.status_code == 422


def test_el_estado_solo_avanza(h):
    orden = pedido(h, proveedor(h), estado="borrador")
    ruta = f"/api/compras/ordenes/{orden['uuid']}/estado"
    assert cliente.patch(ruta, json={"estado": "pendiente"}, headers=h).json()["orden"]["estado"] == "pendiente"
    assert cliente.patch(ruta, json={"estado": "en_camino"}, headers=h).json()["orden"]["estado"] == "en_camino"
    assert cliente.patch(ruta, json={"estado": "en_camino"}, headers=h).status_code == 200  # reintento
    assert cliente.patch(ruta, json={"estado": "pendiente"}, headers=h).status_code == 409
    assert cliente.patch(ruta, json={"estado": "recibida"}, headers=h).status_code == 422


def test_filtrar_ordenes_por_estado(h):
    sur = proveedor(h)
    pedido(h, sur, estado="borrador")
    pendiente = pedido(h, sur)
    r = cliente.get("/api/compras/ordenes", params={"estado": ["pendiente", "en_camino"]}, headers=h)
    assert [o["uuid"] for o in r.json()] == [pendiente["uuid"]]


# ---- Recepción ----

def test_el_monto_real_cuenta_solo_lo_que_llego(h):
    orden = pedido(h, proveedor(h), [("Arroz", "100.00"), ("Azúcar", "50.00"), ("Aceite", "30.00")])
    r = recibir(
        h, orden,
        "recibido",
        "no_recibido",
        {"estado": "cambiado", "producto_sustituto": "Aceite Sol", "monto_sustituto": "35.50"},
    )
    assert r.status_code == 200, r.text
    resultado = r.json()["orden"]
    assert resultado["estado"] == "recibida"
    assert resultado["monto_total"] == "180.00"  # lo planificado no se toca
    assert resultado["monto_real"] == "135.50"


def test_lo_dejado_pendiente_mantiene_el_pedido_abierto(h):
    orden = pedido(h, proveedor(h))
    parcial = recibir(h, orden, "recibido", "pendiente").json()["orden"]
    assert parcial["estado"] == "pendiente"
    assert parcial["monto_real"] == "100.00"

    final = recibir(h, parcial, "recibido", "recibido").json()["orden"]
    assert final["estado"] == "recibida"
    assert final["monto_real"] == "150.50"


def test_reenviar_la_recepcion_no_cambia_nada(h):
    orden = pedido(h, proveedor(h))
    primero = recibir(h, orden, "recibido", "no_recibido").json()["orden"]
    segundo = recibir(h, orden, "recibido", "no_recibido")
    assert segundo.status_code == 200
    assert segundo.json()["orden"] == primero


def test_una_recepcion_confirmada_no_se_reescribe(h):
    orden = pedido(h, proveedor(h))
    recibir(h, orden, "recibido", "recibido")
    assert recibir(h, orden, "no_recibido", "recibido").status_code == 409
    assert recibir(h, orden, "pendiente", "recibido").status_code == 409


def test_un_cambio_exige_sustituto_y_monto(h):
    orden = pedido(h, proveedor(h))
    assert recibir(h, orden, {"estado": "cambiado"}, "recibido").status_code == 422
    r = recibir(h, orden, {"estado": "recibido", "monto_sustituto": "1.00"}, "recibido")
    assert r.status_code == 422


def test_no_se_recibe_un_borrador_ni_un_producto_ajeno(h):
    sur = proveedor(h)
    assert recibir(h, pedido(h, sur, estado="borrador"), "recibido", "recibido").status_code == 409
    ajeno = pedido(h, sur)["items"][0]["uuid"]
    r = cliente.post(
        f"/api/compras/ordenes/{pedido(h, sur)['uuid']}/recepcion",
        json={"items": [{"item_uuid": ajeno, "estado": "recibido"}]},
        headers=h,
    )
    assert r.status_code == 404


def test_cerrar_solo_tras_recibir(h):
    orden = pedido(h, proveedor(h))
    ruta = f"/api/compras/ordenes/{orden['uuid']}/cerrar"
    assert cliente.post(ruta, headers=h).status_code == 409
    recibir(h, orden, "recibido", "recibido")
    assert cliente.post(ruta, headers=h).json()["orden"]["estado"] == "cerrada"
    assert cliente.post(ruta, headers=h).status_code == 200  # reintento


# ---- Hacia el Dashboard ----

def _resumen(h) -> dict:
    return cliente.get("/api/dashboard/resumen", headers=h).json()


def test_lo_recibido_sale_de_los_pedidos_por_llegar(h):
    orden = pedido(h, proveedor(h), fecha_estimada_llegada="2030-01-15")
    assert [p["uuid"] for p in _resumen(h)["pedidos_por_llegar"]] == [orden["uuid"]]
    recibir(h, orden, "recibido", "recibido")
    assert _resumen(h)["pedidos_por_llegar"] == []


def test_un_pedido_parcial_solo_proyecta_lo_que_falta(h):
    orden = pedido(h, proveedor(h), fecha_estimada_llegada="2030-01-15")
    recibir(h, orden, "recibido", "pendiente")
    assert _resumen(h)["pedidos_por_llegar"][0]["monto"] == "50.50"


# ---- Hacia Inventario, por evento ----

def _producto(h, nombre="Arroz", stock="5") -> dict:
    r = cliente.post(
        "/api/inventario/productos",
        json={"uuid": uuid(), "nombre": nombre, "unidad": "kg", "stock_inicial": stock},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _stock(h, nombre) -> str:
    productos = cliente.get("/api/inventario/productos", headers=h).json()
    return next(p["stock_actual"] for p in productos if p["nombre"] == nombre)


def test_recibir_suma_al_stock_una_sola_vez(h):
    _producto(h)
    orden = pedido(h, proveedor(h))
    entrada = {"estado": "recibido", "cantidad_stock": "50"}
    assert recibir(h, orden, entrada, "no_recibido").status_code == 200
    assert float(_stock(h, "Arroz")) == 55
    recibir(h, orden, entrada, "no_recibido")  # la cola reenvía
    assert float(_stock(h, "Arroz")) == 55


def test_un_cambio_suma_al_stock_del_sustituto(h):
    _producto(h)
    _producto(h, "Arroz Costeño", "0")
    orden = pedido(h, proveedor(h))
    cambio = {
        "estado": "cambiado",
        "producto_sustituto": "arroz costeño",
        "monto_sustituto": "90.00",
        "cantidad_stock": "45",
    }
    recibir(h, orden, cambio, "no_recibido")
    assert float(_stock(h, "Arroz Costeño")) == 45
    assert float(_stock(h, "Arroz")) == 5


def test_sin_cantidad_o_sin_producto_la_recepcion_se_guarda_igual(h):
    _producto(h)
    orden = pedido(h, proveedor(h))
    r = recibir(h, orden, "recibido", {"estado": "recibido", "cantidad_stock": "2"})
    assert r.status_code == 200
    assert float(_stock(h, "Arroz")) == 5  # no dijeron cuánto: no se adivina
    assert any("Azúcar" in aviso for aviso in r.json()["avisos"])


def test_si_inventario_falla_la_recepcion_se_guarda_igual(h, monkeypatch):
    from modules.inventario import servicio as inventario

    _producto(h)
    def explota(sesion, producto, *args, **kwargs):
        raise RuntimeError("inventario caído")

    monkeypatch.setattr(inventario, "registrar_movimiento", explota)
    orden = pedido(h, proveedor(h))
    r = recibir(h, orden, {"estado": "recibido", "cantidad_stock": "50"}, "recibido")
    assert r.status_code == 200
    assert r.json()["orden"]["estado"] == "recibida"


def test_compras_exige_sesion():
    assert cliente.get("/api/compras/ordenes").status_code == 401
    assert cliente.post("/api/compras/proveedores", json={}).status_code == 401
