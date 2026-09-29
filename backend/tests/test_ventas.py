"""Módulo Ventas: escrituras idempotentes, totales del servidor y deuda derivada.

Se prueba contra Anita (base vacía) para que las cifras sean exactas; demo
trae datos de muestra.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


def nuevo() -> str:
    return str(uuid4())


@pytest.fixture()
def api(cabeceras_anita):
    with TestClient(app) as cliente_http:
        cliente_http.headers.update(cabeceras_anita)
        yield cliente_http


def abrir_orden(api, **extra) -> str:
    uuid = nuevo()
    respuesta = api.post("/api/ventas/", json={"uuid": uuid, "tipo": "orden_activa", **extra})
    assert respuesta.status_code == 201, respuesta.text
    return uuid


def agregar(api, venta, nombre, monto, **extra):
    return api.post(
        f"/api/ventas/{venta}/items",
        json={"uuid": nuevo(), "nombre_producto": nombre, "monto": monto, **extra},
    )


def crear_cliente(api, nombre="Sra. Flora", **extra) -> str:
    uuid = nuevo()
    assert api.post("/api/ventas/clientes", json={"uuid": uuid, "nombre": nombre, **extra}).status_code == 201
    return uuid


# ------------------------------------------------------------------ orden activa

def test_orden_activa_de_punta_a_punta(api):
    orden = abrir_orden(api, nombre_orden="Restaurante Doña Carmen")
    agregar(api, orden, "Pollo", "18.00")
    respuesta = agregar(api, orden, "Arroz 5 kg", "24.50")
    assert respuesta.json()["venta"]["monto_total"] == "42.50"

    cobro = api.post(f"/api/ventas/{orden}/cobrar", json={"metodo_pago": "yape_plin"})
    assert cobro.status_code == 200
    venta = cobro.json()["venta"]
    assert (venta["estado"], venta["metodo_pago"]) == ("pagada_cerrada", "yape_plin")

    resumen = api.get("/api/dashboard/resumen").json()
    assert (resumen["ventas_hoy"], resumen["ventas_cerradas"]) == ("42.50", 1)
    assert resumen["ordenes_activas"] == []


def test_el_total_lo_calcula_el_servidor_aunque_el_cliente_mande_otro(api):
    # D-11: el monto de una orden es Σ items; no se acepta un total del cliente
    respuesta = api.post("/api/ventas/", json={"uuid": nuevo(), "tipo": "orden_activa", "monto": "999"})
    assert respuesta.status_code == 422


def test_quitar_un_producto_recalcula_el_total(api):
    orden = abrir_orden(api)
    item = nuevo()
    api.post(f"/api/ventas/{orden}/items", json={"uuid": item, "nombre_producto": "Gaseosa", "monto": "9.50"})
    agregar(api, orden, "Pan", "14.00")
    respuesta = api.delete(f"/api/ventas/{orden}/items/{item}")
    assert respuesta.json()["venta"]["monto_total"] == "14.00"
    # Quitar otra vez (reintento) no falla ni cambia nada
    assert api.delete(f"/api/ventas/{orden}/items/{item}").json()["venta"]["monto_total"] == "14.00"


def test_varias_ordenes_abiertas_en_paralelo(api):
    ordenes = [abrir_orden(api, nombre_orden=f"Mesa {i}") for i in range(1, 4)]
    for orden in ordenes:
        agregar(api, orden, "Menú", "10.00")
    api.post(f"/api/ventas/{ordenes[1]}/cobrar", json={})
    abiertas = [v["uuid"] for v in api.get("/api/ventas/abiertas").json()]
    assert abiertas == [ordenes[0], ordenes[2]]


def test_no_se_cobra_una_orden_vacia(api):
    orden = abrir_orden(api)
    assert api.post(f"/api/ventas/{orden}/cobrar", json={}).status_code == 422


def test_una_orden_cerrada_no_acepta_mas_productos(api):
    orden = abrir_orden(api)
    agregar(api, orden, "Pan", "1.00")
    api.post(f"/api/ventas/{orden}/cobrar", json={})
    assert agregar(api, orden, "Pan", "1.00").status_code == 409


def test_anular_una_orden_vacia(api):
    orden = abrir_orden(api)
    assert api.delete(f"/api/ventas/{orden}").status_code == 204
    assert api.get(f"/api/ventas/{orden}").status_code == 404
    assert api.delete(f"/api/ventas/{orden}").status_code == 204  # idempotente


# ------------------------------------------------------------------ idempotencia (ADR-032)

def test_reenviar_la_misma_venta_no_la_duplica(api):
    uuid = nuevo()
    cuerpo = {"uuid": uuid, "tipo": "orden_activa"}
    assert api.post("/api/ventas/", json=cuerpo).status_code == 201
    assert api.post("/api/ventas/", json=cuerpo).status_code == 200
    assert len(api.get("/api/ventas/").json()) == 1


def test_reenviar_el_mismo_item_no_suma_dos_veces(api):
    orden = abrir_orden(api)
    cuerpo = {"uuid": nuevo(), "nombre_producto": "Aceite", "monto": "12.00"}
    assert api.post(f"/api/ventas/{orden}/items", json=cuerpo).status_code == 201
    repetido = api.post(f"/api/ventas/{orden}/items", json=cuerpo)
    assert repetido.status_code == 200
    assert repetido.json()["venta"]["monto_total"] == "12.00"


def test_cobrar_dos_veces_no_crea_dos_pagos(api):
    orden = abrir_orden(api)
    agregar(api, orden, "Pollo", "18.00")
    api.post(f"/api/ventas/{orden}/cobrar", json={})
    assert api.post(f"/api/ventas/{orden}/cobrar", json={}).status_code == 200
    assert api.get("/api/dashboard/resumen").json()["ventas_hoy"] == "18.00"


def test_un_uuid_no_se_puede_reusar_para_otra_cosa(api):
    uuid = nuevo()
    api.post("/api/ventas/", json={"uuid": uuid, "tipo": "orden_activa"})
    cliente = crear_cliente(api)
    otro = api.post("/api/ventas/", json={"uuid": uuid, "tipo": "fiado", "cliente_uuid": cliente})
    assert otro.status_code == 409


def test_la_hora_del_dispositivo_se_respeta_al_sincronizar(api):
    # Venta hecha sin red a las 10:00 y enviada después: cuenta a las 10:00
    from datetime import timedelta

    from fechas import ahora_utc

    hace_una_hora = (ahora_utc() - timedelta(hours=1)).replace(microsecond=0)
    uuid = nuevo()
    api.post("/api/ventas/", json={"uuid": uuid, "tipo": "orden_activa", "ocurrido_en": hace_una_hora.isoformat()})
    abierta_en = api.get(f"/api/ventas/{uuid}").json()["abierta_en"]
    assert abierta_en.startswith(hace_una_hora.strftime("%Y-%m-%dT%H:%M"))


def test_una_hora_imposible_del_dispositivo_se_reemplaza(api):
    uuid = nuevo()
    api.post("/api/ventas/", json={"uuid": uuid, "tipo": "orden_activa", "ocurrido_en": "2099-01-01T00:00:00Z"})
    assert not api.get(f"/api/ventas/{uuid}").json()["abierta_en"].startswith("2099")


# ------------------------------------------------------------------ fiado y deuda

def test_fiado_suma_a_la_deuda_y_el_abono_la_baja(api):
    flora = crear_cliente(api)
    fiado = api.post("/api/ventas/", json={"uuid": nuevo(), "tipo": "fiado", "cliente_uuid": flora}).json()
    uuid = fiado["venta"]["uuid"]
    agregar(api, uuid, "Leche", "8.00")
    agregar(api, uuid, "Azúcar", "4.00")
    assert api.post(f"/api/ventas/{uuid}/fiar", json={}).json()["venta"]["estado"] == "fiada"
    assert api.get(f"/api/ventas/clientes/{flora}").json()["deuda"] == "12.00"

    abono = api.post("/api/ventas/abonos", json={"uuid": nuevo(), "cliente_uuid": flora, "monto": "5.00"})
    assert abono.status_code == 201
    assert abono.json()["deuda_restante"] == "7.00"

    resumen = api.get("/api/dashboard/resumen").json()
    assert (resumen["fiados_por_cobrar"], resumen["clientes_con_fiado"]) == ("7.00", 1)
    # Un fiado no es dinero en caja: no cuenta en "Vendiste hoy"
    assert resumen["ventas_hoy"] == "0.00"


def test_fiado_sobre_el_limite_se_guarda_con_aviso(api):
    # La entrega ya ocurrió: no se rechaza, se avisa (principio 3 del servicio)
    flora = crear_cliente(api, limite_credito="10.00")
    uuid = api.post("/api/ventas/", json={"uuid": nuevo(), "tipo": "fiado", "cliente_uuid": flora}).json()["venta"]["uuid"]
    agregar(api, uuid, "Arroz", "15.00")
    respuesta = api.post(f"/api/ventas/{uuid}/fiar", json={})
    assert respuesta.status_code == 200
    assert "límite" in respuesta.json()["avisos"][0]
    assert api.get(f"/api/ventas/clientes/{flora}").json()["deuda"] == "15.00"


def test_una_orden_activa_se_puede_fiar_al_final(api):
    julio = crear_cliente(api, nombre="Don Julio")
    orden = abrir_orden(api)
    agregar(api, orden, "Cerveza", "7.00")
    venta = api.post(f"/api/ventas/{orden}/fiar", json={"cliente_uuid": julio}).json()["venta"]
    assert (venta["tipo"], venta["cliente_nombre"], venta["deuda_cliente"]) == ("fiado", "Don Julio", "7.00")


def test_no_se_puede_fiar_sin_cliente(api):
    orden = abrir_orden(api)
    agregar(api, orden, "Pan", "1.00")
    assert api.post(f"/api/ventas/{orden}/fiar", json={}).status_code == 422


def test_pagar_de_mas_deja_saldo_a_favor(api):
    flora = crear_cliente(api)
    respuesta = api.post("/api/ventas/abonos", json={"uuid": nuevo(), "cliente_uuid": flora, "monto": "3.00"})
    assert respuesta.json()["deuda_restante"] == "-3.00"
    assert "a favor" in respuesta.json()["avisos"][0]


def test_lista_de_fiados_del_que_mas_debe_al_que_menos(api):
    for nombre, monto in (("Luis", "5.00"), ("Rosa", "20.00")):
        cliente = crear_cliente(api, nombre=nombre)
        uuid = api.post("/api/ventas/", json={"uuid": nuevo(), "tipo": "fiado", "cliente_uuid": cliente}).json()["venta"]["uuid"]
        agregar(api, uuid, "Abarrotes", monto)
        api.post(f"/api/ventas/{uuid}/fiar", json={})
    assert [(c["nombre"], c["deuda"]) for c in api.get("/api/ventas/fiados").json()] == [
        ("Rosa", "20.00"), ("Luis", "5.00"),
    ]


def test_buscar_clientes_por_nombre(api):
    crear_cliente(api, nombre="Sra. Flora")
    crear_cliente(api, nombre="Don Julio")
    assert [c["nombre"] for c in api.get("/api/ventas/clientes", params={"buscar": "flo"}).json()] == ["Sra. Flora"]


# ------------------------------------------------------------------ venta rápida

def test_venta_rapida_cuenta_en_caja_y_se_formaliza_si_cuadra(api):
    uuid = nuevo()
    respuesta = api.post("/api/ventas/", json={"uuid": uuid, "tipo": "venta_rapida", "monto": "20.00"})
    assert respuesta.json()["venta"]["estado"] == "pendiente_formalizar"
    resumen = api.get("/api/dashboard/resumen").json()
    assert (resumen["ventas_hoy"], resumen["ventas_rapidas_pendientes"]) == ("20.00", 1)

    agregar(api, uuid, "Papa", "12.00")
    descuadre = api.post(f"/api/ventas/{uuid}/formalizar")
    assert descuadre.status_code == 422
    assert "S/ 12.00" in descuadre.json()["detail"] and "S/ 20.00" in descuadre.json()["detail"]

    agregar(api, uuid, "Cebolla", "8.00")
    assert api.post(f"/api/ventas/{uuid}/formalizar").json()["venta"]["estado"] == "pagada_cerrada"
    resumen = api.get("/api/dashboard/resumen").json()
    # El detalle no cambia el dinero cobrado ni lo cuenta dos veces
    assert (resumen["ventas_hoy"], resumen["ventas_rapidas_pendientes"]) == ("20.00", 0)


def test_venta_rapida_exige_monto(api):
    assert api.post("/api/ventas/", json={"uuid": nuevo(), "tipo": "venta_rapida"}).status_code == 422


# ------------------------------------------------------------------ validación de entrada

@pytest.mark.parametrize("monto", ["-1", "1.234", "abc"])
def test_montos_invalidos_se_rechazan(api, monto):
    orden = abrir_orden(api)
    assert agregar(api, orden, "Pan", monto).status_code == 422


def test_uuid_con_formato_invalido_se_rechaza(api):
    assert api.post("/api/ventas/", json={"uuid": "hola", "tipo": "orden_activa"}).status_code == 422


def test_las_ventas_de_un_proyecto_no_se_ven_en_otro(api, cabeceras_demo):
    orden = abrir_orden(api)
    with TestClient(app) as otro:
        assert otro.get(f"/api/ventas/{orden}", headers=cabeceras_demo).status_code == 404
