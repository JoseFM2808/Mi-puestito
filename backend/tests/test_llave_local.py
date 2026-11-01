"""Llave de IA guardada desde la pantalla (D-14). Solo valores de prueba: nunca una llave real."""

import sys

import pytest
from fastapi.testclient import TestClient

import rutas
import seguridad
from ia import configuracion, llave_local
from main import app

LLAVE_DE_PRUEBA = "llave-de-prueba-no-es-real-123456"

# El servidor ve al cliente como la misma computadora, igual que en el .exe
desde_el_equipo = TestClient(app, client=("127.0.0.1", 50000))
desde_otro_equipo = TestClient(app, client=("192.168.1.50", 50000))


@pytest.fixture(autouse=True)
def carpeta_y_cifrado_de_prueba(monkeypatch, tmp_path):
    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("MI_PUESTITO_IA_PROVEEDOR", raising=False)
    monkeypatch.setattr(seguridad, "ENTORNO", "local")
    # Reversible y distinto del texto en claro: permite correr esto también en Linux
    monkeypatch.setattr(llave_local, "disponible", lambda: True)
    monkeypatch.setattr(llave_local, "_cifrar", lambda texto: bytes(b ^ 0x5A for b in texto))
    monkeypatch.setattr(llave_local, "_descifrar", lambda texto: bytes(b ^ 0x5A for b in texto))

    async def acepta(llave, url, modelo):
        return False

    monkeypatch.setattr(llave_local, "rechazada_por_el_proveedor", acepta)
    return tmp_path


def _estado(h, cliente=desde_el_equipo) -> dict:
    return cliente.get("/api/asistente/estado", headers=h).json()


def test_sin_llave_se_ofrece_guardarla(cabeceras_demo):
    assert _estado(cabeceras_demo) == {"listo": False, "puede_guardar_llave": True, "llave_guardada": False}


def test_guardar_la_llave_activa_el_asistente_y_nunca_la_devuelve(cabeceras_demo, tmp_path):
    r = desde_el_equipo.post("/api/asistente/llave", json={"llave": LLAVE_DE_PRUEBA}, headers=cabeceras_demo)
    assert r.status_code == 200
    assert r.json() == {"listo": True, "puede_guardar_llave": True, "llave_guardada": True}
    assert LLAVE_DE_PRUEBA not in r.text
    assert LLAVE_DE_PRUEBA not in desde_el_equipo.get("/api/asistente/estado", headers=cabeceras_demo).text

    assert configuracion.leer().api_key == LLAVE_DE_PRUEBA
    assert LLAVE_DE_PRUEBA.encode() not in (tmp_path / llave_local.ARCHIVO).read_bytes()


def test_la_variable_de_entorno_manda_sobre_la_guardada(cabeceras_demo, monkeypatch):
    llave_local.guardar(LLAVE_DE_PRUEBA)
    monkeypatch.setenv("NVIDIA_API_KEY", "otra-llave-de-prueba-000000000")
    assert configuracion.leer().api_key == "otra-llave-de-prueba-000000000"


def test_quitar_la_llave(cabeceras_demo, tmp_path):
    llave_local.guardar(LLAVE_DE_PRUEBA)
    r = desde_el_equipo.delete("/api/asistente/llave", headers=cabeceras_demo)
    assert r.json()["listo"] is False
    assert not (tmp_path / llave_local.ARCHIVO).exists()
    assert desde_el_equipo.delete("/api/asistente/llave", headers=cabeceras_demo).status_code == 200


@pytest.mark.parametrize("mala", ["corta", "con espacios en medio de la llave de prueba", "x" * 301, ""])
def test_una_llave_mal_copiada_se_rechaza_sin_repetirla(cabeceras_demo, mala, tmp_path):
    r = desde_el_equipo.post("/api/asistente/llave", json={"llave": mala}, headers=cabeceras_demo)
    assert r.status_code == 400
    if mala:
        assert mala not in r.text
    assert not (tmp_path / llave_local.ARCHIVO).exists()


def test_si_nvidia_la_rechaza_no_se_guarda(cabeceras_demo, monkeypatch, tmp_path):
    async def rechaza(llave, url, modelo):
        return True

    monkeypatch.setattr(llave_local, "rechazada_por_el_proveedor", rechaza)
    r = desde_el_equipo.post("/api/asistente/llave", json={"llave": LLAVE_DE_PRUEBA}, headers=cabeceras_demo)
    assert r.status_code == 400
    assert LLAVE_DE_PRUEBA not in r.text
    assert not (tmp_path / llave_local.ARCHIVO).exists()


def test_otro_equipo_de_la_red_no_puede_cambiarla(cabeceras_demo, tmp_path):
    # El PIN de demo es público: con él no se puede reemplazar la llave del dueño
    assert _estado(cabeceras_demo, desde_otro_equipo)["puede_guardar_llave"] is False
    r = desde_otro_equipo.post("/api/asistente/llave", json={"llave": LLAVE_DE_PRUEBA}, headers=cabeceras_demo)
    assert r.status_code == 403
    assert desde_otro_equipo.delete("/api/asistente/llave", headers=cabeceras_demo).status_code == 403
    assert not (tmp_path / llave_local.ARCHIVO).exists()


def test_en_produccion_no_se_guarda_desde_la_pantalla(cabeceras_demo, monkeypatch):
    monkeypatch.setattr(seguridad, "ENTORNO", "production")
    r = desde_el_equipo.post("/api/asistente/llave", json={"llave": LLAVE_DE_PRUEBA}, headers=cabeceras_demo)
    assert r.status_code == 403


def test_fuera_de_windows_no_se_guarda(cabeceras_demo, monkeypatch):
    monkeypatch.setattr(llave_local, "disponible", lambda: False)
    assert _estado(cabeceras_demo)["puede_guardar_llave"] is False
    r = desde_el_equipo.post("/api/asistente/llave", json={"llave": LLAVE_DE_PRUEBA}, headers=cabeceras_demo)
    assert r.status_code == 403
    assert llave_local.leer() is None


def test_exige_sesion():
    assert desde_el_equipo.get("/api/asistente/estado").status_code == 401
    assert desde_el_equipo.post("/api/asistente/llave", json={"llave": "x"}).status_code == 401
    assert desde_el_equipo.delete("/api/asistente/llave").status_code == 401


def test_un_archivo_danado_equivale_a_no_tener_llave(monkeypatch, tmp_path):
    (tmp_path / llave_local.ARCHIVO).write_bytes(b"basura")

    def falla(_):
        raise OSError("DPAPI")

    monkeypatch.setattr(llave_local, "_descifrar", falla)
    assert llave_local.leer() is None


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI solo existe en Windows")
def test_dpapi_real_cifra_y_descifra(monkeypatch, tmp_path):
    monkeypatch.undo()
    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    llave_local.guardar(LLAVE_DE_PRUEBA)
    guardado = (tmp_path / llave_local.ARCHIVO).read_bytes()
    assert LLAVE_DE_PRUEBA.encode() not in guardado
    assert llave_local.leer() == LLAVE_DE_PRUEBA
    # Un bit cambiado no se descifra: no devuelve basura como si fuera la llave
    (tmp_path / llave_local.ARCHIVO).write_bytes(guardado[:-1] + bytes([guardado[-1] ^ 1]))
    assert llave_local.leer() is None
