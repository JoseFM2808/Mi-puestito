"""El Asistente: protegido por sesión, no inventa cifras y se degrada bien
sin llave configurada. Sin llamadas reales a NVIDIA (se simula ia.servicio)."""

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
