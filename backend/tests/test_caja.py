"""Caja con saldo inicial y Gastos (D-24, ADR-051).

La caja empieza con un saldo en efectivo y otro en Yape; lo cobrado los sube por su medio de
pago, y los gastos (incluido "Ya le pagué" al proveedor) los bajan.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import eventos
from main import app

cliente = TestClient(app)


def uuid() -> str:
    return str(uuid4())


@pytest.fixture()
def h(cabeceras_anita):
    # Negocio sin datos de muestra: cada test ve solo lo que crea
    return cabeceras_anita


def caja(h) -> dict:
    r = cliente.get("/api/caja", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def abrir(h, efectivo="100.00", yape="50.00", **extra) -> dict:
    r = cliente.post(
        "/api/caja/apertura",
        json={"uuid": uuid(), "efectivo_inicial": efectivo, "yape_inicial": yape, **extra},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def gasto(h, monto, medio="efectivo", **campos) -> dict:
    cuerpo = {"uuid": campos.pop("uuid", uuid()), "monto": monto, "medio": medio, **campos}
    r = cliente.post("/api/gastos", json=cuerpo, headers=h)
    assert r.status_code in (200, 201), r.text
    return r.json()


def venta_rapida(h, monto, metodo="efectivo"):
    r = cliente.post(
        "/api/ventas/",
        json={"uuid": uuid(), "tipo": "venta_rapida", "monto": monto, "metodo_pago": metodo},
        headers=h,
    )
    assert r.status_code == 201, r.text


def test_sin_abrir_la_caja_lo_dice_y_todo_esta_en_cero(h):
    datos = caja(h)
    assert datos["abierta"] is False
    assert datos["en_caja"] == {"efectivo": "0.00", "yape_plin": "0.00"}


def test_la_caja_empieza_con_efectivo_y_yape(h):
    datos = abrir(h, "120.50", "30.00")
    assert datos["abierta"] is True
    assert datos["inicial"] == {"efectivo": "120.50", "yape_plin": "30.00"}
    assert datos["en_caja"] == {"efectivo": "120.50", "yape_plin": "30.00"}


def test_abrir_otra_vez_el_mismo_dia_corrige_los_saldos(h):
    abrir(h, "100.00", "0.00")
    datos = abrir(h, "90.00", "10.00")
    assert datos["inicial"] == {"efectivo": "90.00", "yape_plin": "10.00"}


def test_lo_cobrado_suma_por_su_medio_y_los_gastos_restan(h):
    abrir(h, "100.00", "50.00")
    venta_rapida(h, "25.00", "efectivo")
    venta_rapida(h, "12.50", "yape_plin")
    gasto(h, "8.00", "efectivo", categoria="transporte")
    gasto(h, "20.00", "yape_plin", ambito="hogar", categoria="alimentacion")
    datos = caja(h)
    assert datos["ingresos"] == {"efectivo": "25.00", "yape_plin": "12.50"}
    assert datos["egresos"] == {"efectivo": "8.00", "yape_plin": "20.00"}
    assert datos["en_caja"] == {"efectivo": "117.00", "yape_plin": "42.50"}


def test_un_gasto_reenviado_no_se_cuenta_dos_veces_y_anularlo_lo_devuelve(h):
    abrir(h)
    mismo = uuid()
    gasto(h, "10.00", uuid=mismo)
    gasto(h, "10.00", uuid=mismo)
    assert caja(h)["egresos"]["efectivo"] == "10.00"
    assert cliente.delete(f"/api/gastos/{mismo}", headers=h).status_code == 204
    assert cliente.delete(f"/api/gastos/{mismo}", headers=h).status_code == 204
    assert caja(h)["egresos"]["efectivo"] == "0.00"


def test_los_gastos_del_dia_separan_el_puesto_del_hogar(h):
    gasto(h, "15.00", categoria="alquiler")
    gasto(h, "7.50", "yape_plin", ambito="hogar", categoria="educacion")
    datos = cliente.get("/api/gastos", headers=h).json()
    assert [g["categoria"] for g in datos["gastos"]] == ["alquiler", "educacion"]
    assert (datos["del_puesto"], datos["del_hogar"]) == ("15.00", "7.50")
    assert datos["total"] == {"efectivo": "15.00", "yape_plin": "7.50"}


@pytest.mark.parametrize("monto", ["0", "-5.00", "1.234"])
def test_un_gasto_sin_monto_valido_se_rechaza(h, monto):
    r = cliente.post("/api/gastos", json={"uuid": uuid(), "monto": monto, "medio": "efectivo"}, headers=h)
    assert r.status_code == 422


# ---- "Ya le pagué": el pago del pedido sale de la caja ----


def _pedido_recibido(h, monto="80.00") -> dict:
    prov = cliente.post(
        "/api/compras/proveedores", json={"uuid": uuid(), "nombre": "Distribuidora Sur"}, headers=h
    ).json()
    orden = cliente.post(
        "/api/compras/ordenes",
        json={
            "uuid": uuid(),
            "proveedor_uuid": prov["uuid"],
            "items": [{"uuid": uuid(), "nombre_producto": "Arroz", "cantidad": "1 saco", "monto": monto}],
        },
        headers=h,
    ).json()["orden"]
    items = [{"item_uuid": i["uuid"], "estado": "recibido"} for i in orden["items"]]
    r = cliente.post(f"/api/compras/ordenes/{orden['uuid']}/recepcion", json={"items": items}, headers=h)
    assert r.status_code == 200, r.text
    return orden


def test_pagar_el_pedido_lo_descuenta_de_la_caja_una_sola_vez(h):
    abrir(h, "200.00", "0.00")
    orden = _pedido_recibido(h, "80.00")
    for _ in range(2):  # la cola offline puede reenviar el cierre
        r = cliente.post(f"/api/compras/ordenes/{orden['uuid']}/cerrar", json={"medio": "efectivo"}, headers=h)
        assert r.status_code == 200, r.text
    assert caja(h)["en_caja"]["efectivo"] == "120.00"
    gastos = cliente.get("/api/gastos", headers=h).json()["gastos"]
    assert [(g["categoria"], g["monto"], g["descripcion"]) for g in gastos] == [
        ("proveedor", "80.00", "Pedido de Distribuidora Sur")
    ]


def test_cerrar_sin_decir_con_que_se_pago_no_toca_la_caja(h):
    abrir(h, "200.00", "0.00")
    orden = _pedido_recibido(h)
    assert cliente.post(f"/api/compras/ordenes/{orden['uuid']}/cerrar", headers=h).status_code == 200
    assert caja(h)["en_caja"]["efectivo"] == "200.00"


def test_si_gastos_falla_el_pedido_se_cierra_igual(h):
    orden = _pedido_recibido(h)

    def roto(sesion, datos):
        raise RuntimeError("gastos caído")

    eventos.suscribir("compra.pagada", "gastos.pago_de_pedido", roto)
    try:
        r = cliente.post(f"/api/compras/ordenes/{orden['uuid']}/cerrar", json={"medio": "yape_plin"}, headers=h)
        assert r.status_code == 200
        assert r.json()["orden"]["estado"] == "cerrada"
    finally:
        from modules.gastos.servicio import al_pagar_pedido

        eventos.suscribir("compra.pagada", "gastos.pago_de_pedido", al_pagar_pedido)


def test_si_un_modulo_falla_la_caja_igual_se_muestra(h, monkeypatch):
    from modules.caja import servicio

    def roto(sesion, dia):
        raise RuntimeError("ventas caído")

    abrir(h, "50.00", "5.00")
    monkeypatch.setattr(servicio, "_ingresos", roto)
    datos = caja(h)
    assert datos["no_disponibles"] == ["ventas"]
    assert datos["en_caja"] == {"efectivo": "50.00", "yape_plin": "5.00"}
