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


def test_secreto_vacio_en_el_entorno_no_deja_firmar_con_llave_vacia(monkeypatch):
    # config/.env.example trae MI_PUESTITO_SECRETO= vacío: con el default de
    # os.environ.get la llave HMAC sería "" y cualquiera falsificaría tokens
    import seguridad

    monkeypatch.setenv("MI_PUESTITO_SECRETO", "")
    llave = seguridad._secreto_de_firma()
    assert len(llave) == 64

    monkeypatch.setenv("MI_PUESTITO_SECRETO", "llave-de-produccion")
    assert seguridad._secreto_de_firma() == b"llave-de-produccion"


# ---- Límite de intentos (D-04) ----

def test_tras_cinco_fallos_hay_que_esperar(cliente):
    for _ in range(5):
        assert cliente.post("/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "1"}).status_code == 401
    bloqueado = cliente.post("/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "0000"})
    # Ni el PIN correcto entra mientras dura la espera: no se puede seguir adivinando
    assert bloqueado.status_code == 429
    assert "Espera" in bloqueado.json()["detail"]
    assert int(bloqueado.headers["Retry-After"]) > 0


def test_la_espera_termina_y_el_acierto_limpia_el_contador(cliente, monkeypatch):
    import seguridad

    reloj = [1000.0]
    monkeypatch.setattr(seguridad.time, "monotonic", lambda: reloj[0])
    for _ in range(5):
        cliente.post("/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "1"})
    reloj[0] += seguridad.ESPERA_INICIAL_SEGUNDOS + 1
    assert cliente.post("/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "0000"}).status_code == 200
    assert "demo" not in seguridad._intentos


def test_cada_fallo_extra_duplica_la_espera(monkeypatch):
    import seguridad

    reloj = [0.0]
    monkeypatch.setattr(seguridad.time, "monotonic", lambda: reloj[0])
    for _ in range(7):
        seguridad._registrar_fallo("x")
    assert seguridad._intentos["x"].bloqueado_hasta == seguridad.ESPERA_INICIAL_SEGUNDOS * 4


def test_los_intentos_de_un_usuario_no_bloquean_a_otro(cliente):
    for _ in range(6):
        cliente.post("/api/auth/ingresar", json={"nombre_usuario": "demo", "pin": "1"})
    assert cliente.post("/api/auth/ingresar", json={"nombre_usuario": "anita", "pin": "999999"}).status_code == 200


# ---- Secreto obligatorio en producción (D-09) ----

def test_produccion_sin_secreto_no_arranca(monkeypatch):
    import seguridad

    monkeypatch.setattr(seguridad, "ENTORNO", "production")
    monkeypatch.setenv("MI_PUESTITO_SECRETO", "corto")
    with pytest.raises(seguridad.ConfiguracionInsegura):
        seguridad._secreto_de_firma()
    monkeypatch.setenv("MI_PUESTITO_SECRETO", "a" * 64)
    assert seguridad._secreto_de_firma() == b"a" * 64
