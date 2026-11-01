"""Pruebas de humo: el servicio responde y el ORM funciona de punta a punta
(migraciones + consultas). Demo trae datos de muestra; Anita arranca vacía.

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
    assert respuesta.json() == {"estado": "ok", "modulos_degradados": [], "eventos_con_fallas": []}


def test_las_rutas_de_datos_exigen_haber_iniciado_sesion(cliente):
    # Sin token no se ve ni el resumen ni las ventas de nadie
    assert cliente.get("/api/dashboard/resumen").status_code == 401
    assert cliente.get("/api/ventas/").status_code == 401
    assert cliente.get("/api/compras/proveedores").status_code == 401


def test_resumen_dashboard(cliente, cabeceras_demo):
    respuesta = cliente.get("/api/dashboard/resumen", headers=cabeceras_demo)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    # Las cifras de siempre de la demo, ahora calculadas desde sus tablas
    assert datos["ventas_hoy"] == "485.50"
    assert datos["ventas_cerradas"] == 12
    assert len(datos["ordenes_activas"]) == 3
    assert datos["fiados_por_cobrar"] == "132.50"
    assert datos["clientes_con_fiado"] == 4
    assert datos["ventas_rapidas_pendientes"] == 3
    assert datos["secciones_no_disponibles"] == []
    # Tres pedidos: el atrasado primero (por fecha), luego mañana y pasado
    assert [p["proveedor"] for p in datos["pedidos_por_llegar"]] == [
        "Abarrotes El Sol", "Distribuidora Norte", "Avícola San Pedro",
    ]
    # Coherencia: la proyección de mañana es exactamente el pedido que llega mañana
    assert datos["proyeccion_manana"] == datos["pedidos_por_llegar"][1]["monto"] == "320.00"
    assert datos["motivo_proyeccion"] == "Llega pedido de Distribuidora Norte"
    # El fiado abierto de la Sra. Flora muestra su deuda ya fiada (no la orden en curso)
    flora = next(o for o in datos["ordenes_activas"] if o["nombre"] == "Sra. Flora")
    assert (flora["monto"], flora["deuda_cliente"]) == ("12.00", "45.00")


def test_resumen_dashboard_anita_arranca_en_cero(cliente, cabeceras_anita):
    # Anita es una empresa real que recién empieza: nada inventado
    respuesta = cliente.get("/api/dashboard/resumen", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ventas_hoy"] == "0.00"
    assert datos["ordenes_activas"] == []
    assert datos["pedidos_por_llegar"] == []


def test_ventas_vacias(cliente, cabeceras_anita):
    respuesta = cliente.get("/api/ventas/", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_clientes_vacios(cliente, cabeceras_anita):
    respuesta = cliente.get("/api/ventas/clientes", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_proveedores_vacios(cliente, cabeceras_anita):
    respuesta = cliente.get("/api/compras/proveedores", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_ordenes_compra_vacias(cliente, cabeceras_anita):
    respuesta = cliente.get("/api/compras/ordenes", headers=cabeceras_anita)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


# ---- Reiniciar los datos de práctica (D-19) ----

def test_reiniciar_demo_borra_lo_practicado_y_siembra_de_nuevo(cliente, cabeceras_demo):
    cliente.post("/api/ventas/", json={"uuid": "00000000-0000-4000-8000-000000000001", "tipo": "orden_activa"}, headers=cabeceras_demo)
    assert len(cliente.get("/api/ventas/abiertas", headers=cabeceras_demo).json()) == 4

    assert cliente.post("/api/dashboard/demo/reiniciar", headers=cabeceras_demo).status_code == 204

    assert len(cliente.get("/api/ventas/abiertas", headers=cabeceras_demo).json()) == 3
    assert cliente.get("/api/dashboard/resumen", headers=cabeceras_demo).json()["ventas_hoy"] == "485.50"


def test_un_negocio_real_no_se_puede_reiniciar(cliente, cabeceras_anita):
    # Borra toda la base: jamás debe ser posible con datos reales
    orden = {"uuid": "00000000-0000-4000-8000-000000000002", "tipo": "orden_activa"}
    cliente.post("/api/ventas/", json=orden, headers=cabeceras_anita)
    assert cliente.post("/api/dashboard/demo/reiniciar", headers=cabeceras_anita).status_code == 403
    assert len(cliente.get("/api/ventas/abiertas", headers=cabeceras_anita).json()) == 1
