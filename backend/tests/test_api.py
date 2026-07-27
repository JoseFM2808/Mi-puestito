"""Smoke tests de la Demo 1: el esqueleto responde y el ORM funciona
de punta a punta (create_all + consultas sobre la BD vacía)."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def cliente():
    # El context manager ejecuta el ciclo de vida (create_all)
    with TestClient(app) as cliente_http:
        yield cliente_http


def test_salud(cliente):
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    # Con todos los módulos sanos, ninguno aparece degradado
    assert respuesta.json() == {"estado": "ok", "modulos_degradados": []}


def test_resumen_dashboard(cliente):
    respuesta = cliente.get("/api/dashboard/resumen")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ventas_hoy"] == "485.50"
    assert datos["ventas_cerradas"] == 12
    assert len(datos["ordenes_activas"]) == 3
    assert len(datos["pedidos_por_llegar"]) == 2
    # Coherencia: la proyección de mañana corresponde al pedido que llega mañana
    assert datos["proyeccion_manana"] == datos["pedidos_por_llegar"][0]["monto"]


def test_ventas_vacias(cliente):
    respuesta = cliente.get("/api/ventas/")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_clientes_vacios(cliente):
    respuesta = cliente.get("/api/ventas/clientes")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_proveedores_vacios(cliente):
    respuesta = cliente.get("/api/compras/proveedores")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_ordenes_compra_vacias(cliente):
    respuesta = cliente.get("/api/compras/ordenes")
    assert respuesta.status_code == 200
    assert respuesta.json() == []
