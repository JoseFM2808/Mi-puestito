"""Smoke tests de la Demo 1: el esqueleto responde y el ORM funciona
de punta a punta (create_all + consultas sobre la BD vacía).

Todas las rutas de datos exigen sesión (login); solo /api/salud es pública.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def cliente():
    # El context manager ejecuta el ciclo de vida (create_all + usuarios)
    with TestClient(app) as cliente_http:
        yield cliente_http


def test_salud(cliente):
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    # Con todos los módulos sanos, ninguno aparece degradado
    assert respuesta.json() == {"estado": "ok", "modulos_degradados": []}


def test_las_rutas_de_datos_exigen_haber_iniciado_sesion(cliente):
    # Sin token no se ve ni el resumen ni las ventas de nadie
    assert cliente.get("/api/dashboard/resumen").status_code == 401
    assert cliente.get("/api/ventas/").status_code == 401
    assert cliente.get("/api/compras/proveedores").status_code == 401


def test_resumen_dashboard(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/dashboard/resumen", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ventas_hoy"] == "485.50"
    assert datos["ventas_cerradas"] == 12
    assert len(datos["ordenes_activas"]) == 3
    assert len(datos["pedidos_por_llegar"]) == 2
    # Coherencia: la proyección de mañana corresponde al pedido que llega mañana
    assert datos["proyeccion_manana"] == datos["pedidos_por_llegar"][0]["monto"]


def test_resumen_dashboard_anita_arranca_en_cero(cliente, cabeceras_anita):
    # Anita es una empresa real que recién empieza: nada inventado
    respuesta = cliente.get("/api/dashboard/resumen", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ventas_hoy"] == "0"
    assert datos["ordenes_activas"] == []
    assert datos["pedidos_por_llegar"] == []


def test_ventas_vacias(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/ventas/", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_clientes_vacios(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/ventas/clientes", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_proveedores_vacios(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/compras/proveedores", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_ordenes_compra_vacias(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/compras/ordenes", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    assert respuesta.json() == []
