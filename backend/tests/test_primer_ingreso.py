"""D-07: el PIN generado en el primer arranque se muestra en la pantalla de ingreso, solo en la
misma computadora y hasta que el dueño lo anota. Nunca en la consola ni en disco."""

import json

import pytest
from fastapi.testclient import TestClient

import rutas
import seguridad
from main import app

desde_el_equipo = TestClient(app, client=("127.0.0.1", 50000))
desde_otro_equipo = TestClient(app, client=("192.168.1.50", 50000))


@pytest.fixture(autouse=True)
def primer_arranque(monkeypatch, tmp_path):
    """Una carpeta de datos vacía y sin PIN fijado por variable: como en la PC del puesto."""
    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.delenv("MI_PUESTITO_ANITA_PIN", raising=False)
    monkeypatch.setattr(seguridad, "ENTORNO", "local")
    seguridad._pines_por_mostrar.clear()
    yield tmp_path
    seguridad._pines_por_mostrar.clear()


def _arrancar(capsys) -> str:
    seguridad.asegurar_usuarios_iniciales()
    return capsys.readouterr().out


def test_el_pin_no_va_a_la_consola_ni_al_disco(capsys, primer_arranque):
    consola = _arrancar(capsys)
    [(usuario, pin)] = seguridad.pines_por_mostrar()
    assert usuario == "anita"
    assert pin not in consola and "pantalla de" in consola
    assert pin not in (primer_arranque / "usuarios.json").read_text()


def test_solo_esta_computadora_lo_ve(capsys):
    _arrancar(capsys)
    [(_, pin)] = seguridad.pines_por_mostrar()
    assert desde_el_equipo.get("/api/auth/primer-ingreso").json() == [
        {"nombre_usuario": "anita", "nombre_proyecto": "Anita", "pin": pin}
    ]
    assert desde_otro_equipo.get("/api/auth/primer-ingreso").json() == []
    assert desde_otro_equipo.post("/api/auth/primer-ingreso/anita/anotado").status_code == 403


def test_en_un_servidor_no_se_entrega_por_la_red(capsys, monkeypatch):
    monkeypatch.setattr(seguridad, "ENTORNO", "production")
    consola = _arrancar(capsys)
    assert desde_el_equipo.get("/api/auth/primer-ingreso").json() == []
    # Sin pantalla local, la consola del servidor es el único camino
    assert seguridad.pines_por_mostrar()[0][1] in consola


def test_ya_lo_anote_lo_esconde_y_el_pin_sigue_valiendo(capsys, primer_arranque):
    _arrancar(capsys)
    [(_, pin)] = seguridad.pines_por_mostrar()
    assert desde_el_equipo.post("/api/auth/primer-ingreso/anita/anotado").status_code == 204
    assert desde_el_equipo.get("/api/auth/primer-ingreso").json() == []
    assert "pin_por_mostrar" not in json.loads((primer_arranque / "usuarios.json").read_text())["anita"]
    assert seguridad.verificar_credenciales("anita", pin) == "anita"


def test_entrar_con_el_pin_tambien_lo_esconde(capsys):
    _arrancar(capsys)
    [(_, pin)] = seguridad.pines_por_mostrar()
    assert desde_el_equipo.post("/api/auth/ingresar", json={"nombre_usuario": "anita", "pin": pin}).status_code == 200
    assert desde_el_equipo.get("/api/auth/primer-ingreso").json() == []


def test_si_se_cierra_sin_anotarlo_al_volver_hay_otro_pin(capsys):
    _arrancar(capsys)
    [(_, primero)] = seguridad.pines_por_mostrar()
    seguridad._pines_por_mostrar.clear()  # se cerró el programa: la memoria se pierde
    _arrancar(capsys)
    [(_, segundo)] = seguridad.pines_por_mostrar()
    assert seguridad.verificar_credenciales("anita", segundo) == "anita"
    if primero != segundo:
        assert seguridad.verificar_credenciales("anita", primero) is None


def test_un_pin_fijado_por_variable_no_se_muestra(capsys, monkeypatch):
    monkeypatch.setenv("MI_PUESTITO_ANITA_PIN", "123456")
    _arrancar(capsys)
    assert seguridad.pines_por_mostrar() == []
