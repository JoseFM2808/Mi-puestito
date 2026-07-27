"""Login simple: cada usuario abre SOLO su propio proyecto."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def cliente():
    with TestClient(app) as cliente_http:
        yield cliente_http


def test_demo_entra_con_su_pin_fijo(cliente):
    respuesta = cliente.post(
        "/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "0000"}
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["proyecto"] == "demo"
    assert datos["nombre_proyecto"] == "Demo"
    assert datos["es_real"] is False
    assert datos["token"]


def test_anita_entra_con_el_pin_de_entorno(cliente):
    # conftest.py fija MI_PUESTITO_ANITA_PIN=999999 para que sea predecible
    respuesta = cliente.post(
        "/api/auth/ingresar", json={"nombre_usuario": "anita", "pin": "999999"}
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["proyecto"] == "anita"
    assert datos["es_real"] is True


def test_pin_incorrecto_no_entra(cliente):
    respuesta = cliente.post(
        "/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "1111"}
    )
    assert respuesta.status_code == 401


def test_usuario_desconocido_no_entra(cliente):
    respuesta = cliente.post(
        "/api/auth/ingresar", json={"nombre_usuario": "nadie", "pin": "0000"}
    )
    assert respuesta.status_code == 401


def test_el_token_de_demo_no_abre_los_datos_de_anita(cliente):
    """El token queda ligado al proyecto: no hay forma de "elevarlo" a otro."""
    token_demo = cliente.post(
        "/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "0000"}
    ).json()["token"]

    respuesta = cliente.get(
        "/api/dashboard/resumen", headers={"Authorization": f"Bearer {token_demo}"}
    )
    # El token de demo siempre ve el resumen ficticio de demo, nunca el de anita
    assert respuesta.json()["ventas_hoy"] == "485.50"


def test_sin_cabecera_de_autorizacion_no_entra(cliente):
    assert cliente.get("/api/dashboard/resumen").status_code == 401


def test_token_con_formato_invalido_es_rechazado(cliente):
    respuesta = cliente.get(
        "/api/dashboard/resumen", headers={"Authorization": "Bearer basura-sin-formato"}
    )
    assert respuesta.status_code == 401
