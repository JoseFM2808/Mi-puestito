"""El Asistente: protegido por sesión, no inventa cifras y se degrada bien
sin llave configurada. Sin llamadas reales a NVIDIA (se simula ia.servicio)."""

import re

import pytest
from fastapi.testclient import TestClient

import ia.servicio as ia_servicio
from main import app


@pytest.fixture()
def cliente():
    with TestClient(app) as cliente_http:
        yield cliente_http


def test_exige_sesion_iniciada(cliente):
    respuesta = cliente.post("/api/asistente/preguntar", json={"mensaje": "hola"})
    assert respuesta.status_code == 401


def test_responde_usando_el_resumen_del_proyecto(cliente, cabeceras_demo, monkeypatch):
    contextos_recibidos = []

    async def preguntar_falso(mensaje_usuario, contexto_json):
        contextos_recibidos.append((mensaje_usuario, contexto_json))
        return "Vendiste S/ 485.50 hoy."

    monkeypatch.setattr(ia_servicio, "preguntar", preguntar_falso)
    # El router importó la función por nombre: hay que parchear también ahí
    import modules.asistente.router as router_asistente

    monkeypatch.setattr(router_asistente, "preguntar", preguntar_falso)

    respuesta = cliente.post(
        "/api/asistente/preguntar",
        json={"mensaje": "¿cuánto vendí hoy?"},
        headers=cabeceras_demo,
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"respuesta": "Vendiste S/ 485.50 hoy."}
    # El contexto que recibió el "modelo" es el resumen real de demo (485.50),
    # no un dato inventado
    assert "485.50" in contextos_recibidos[0][1]


def test_anita_y_demo_reciben_contextos_distintos(cliente, cabeceras_anita, monkeypatch):
    contextos_recibidos = []

    async def preguntar_falso(mensaje_usuario, contexto_json):
        contextos_recibidos.append(contexto_json)
        return "ok"

    import modules.asistente.router as router_asistente

    monkeypatch.setattr(router_asistente, "preguntar", preguntar_falso)

    cliente.post(
        "/api/asistente/preguntar", json={"mensaje": "hola"}, headers=cabeceras_anita
    )
    # Anita es una empresa real recién empezada: su contexto no tiene las
    # cifras ficticias de demo
    assert "485.50" not in contextos_recibidos[0]


def test_se_degrada_con_claridad_sin_llave_configurada(cliente, cabeceras_demo, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    respuesta = cliente.post(
        "/api/asistente/preguntar", json={"mensaje": "hola"}, headers=cabeceras_demo
    )
    assert respuesta.status_code == 503
    assert "NVIDIA_API_KEY" in respuesta.json()["detail"]


# ---- Privacidad (ADR-034): el proveedor externo nunca ve nombres reales ----

def test_el_modelo_no_ve_nombres_y_el_operador_si(cliente, cabeceras_demo, monkeypatch):
    enviado = {}

    async def modelo_falso(mensaje_usuario, contexto_json):
        enviado["pregunta"], enviado["contexto"] = mensaje_usuario, contexto_json
        # El modelo responde con el alias que vino en la pregunta, que debe ser
        # el mismo con el que la Sra. Flora aparece en el contexto
        alias = re.search(r"Cliente \d+", mensaje_usuario).group(0)
        assert f'"nombre": "{alias}"' in contexto_json
        return f"{alias} debe S/ 45.00."

    import modules.asistente.router as router_asistente

    monkeypatch.setattr(router_asistente, "preguntar", modelo_falso)
    respuesta = cliente.post(
        "/api/asistente/preguntar",
        json={"mensaje": "¿Cuánto debe la sra. flora?"},
        headers=cabeceras_demo,
    )

    for nombre in ("Flora", "Doña Carmen", "Distribuidora Norte", "Avícola"):
        assert nombre.lower() not in enviado["contexto"].lower()
    assert "flora" not in enviado["pregunta"].lower()
    # Las cifras sí viajan: sin ellas el Asistente no sirve
    assert "485.50" in enviado["contexto"]
    # Y el operador lee el nombre real
    assert respuesta.json()["respuesta"] == "Sra. Flora debe S/ 45.00."


def test_los_rotulos_genericos_no_se_ocultan():
    from ia.privacidad import Seudonimos

    alias = Seudonimos()
    assert alias.cliente("Orden 2") == "Orden 2"
    assert alias.cliente("Sra. Flora") == "Cliente 1"
    assert alias.cliente("Sra. Flora") == "Cliente 1"  # estable dentro de la consulta


def test_reidentificar_no_confunde_cliente_1_con_cliente_12():
    from ia.privacidad import Seudonimos

    alias = Seudonimos()
    nombres = [f"Persona {i}" for i in range(1, 13)]
    for nombre in nombres:
        alias.cliente(nombre)
    assert alias.reidentificar("Cliente 12 y Cliente 1") == "Persona 12 y Persona 1"


def test_una_pregunta_enorme_se_rechaza(cliente, cabeceras_demo):
    respuesta = cliente.post(
        "/api/asistente/preguntar", json={"mensaje": "x" * 501}, headers=cabeceras_demo
    )
    assert respuesta.status_code == 422


def test_sin_dashboard_el_asistente_sigue_respondiendo(cliente, cabeceras_demo, monkeypatch):
    # D-06: el Asistente ya no depende del router del Dashboard
    import modules.asistente.router as router_asistente
    import modules.dashboard.servicio as servicio_dashboard

    def roto(*_):
        raise RuntimeError("tabla dañada")

    async def modelo_falso(mensaje_usuario, contexto_json):
        return contexto_json

    monkeypatch.setattr(servicio_dashboard, "calcular_resumen", roto)
    monkeypatch.setattr(router_asistente, "preguntar", modelo_falso)
    respuesta = cliente.post("/api/asistente/preguntar", json={"mensaje": "hola"}, headers=cabeceras_demo)
    assert respuesta.status_code == 200
    assert "no están disponibles" in respuesta.json()["respuesta"]
