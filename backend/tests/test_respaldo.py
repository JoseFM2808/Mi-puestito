"""Respaldo y restauración del archivo de datos (Fase 5). Lo que está en juego son las ventas."""

import sqlite3
from contextlib import closing
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import database
import rutas
from main import app
from migraciones.ejecutar import migrar
from modules.respaldo import servicio

cliente = TestClient(app)


def uuid() -> str:
    return str(uuid4())


def abrir_orden(h, nombre: str) -> None:
    cuerpo = {"uuid": uuid(), "tipo": "orden_activa", "nombre_orden": nombre}
    assert cliente.post("/api/ventas/", json=cuerpo, headers=h).status_code == 201


def ordenes(h) -> list[str]:
    return sorted(v["nombre_orden"] for v in cliente.get("/api/ventas/abiertas", headers=h).json())


def copia(h) -> bytes:
    r = cliente.get("/api/respaldo/copia", headers=h)
    assert r.status_code == 200
    return r.content


def restaurar(h, contenido: bytes):
    return cliente.post(
        "/api/respaldo/restaurar",
        content=contenido,
        headers={**h, "Content-Type": "application/octet-stream"},
    )


def modificar(contenido: bytes, tmp_path, *sentencias: str) -> bytes:
    """Altera una copia, como lo haría un archivo manipulado o de otra versión."""
    archivo = tmp_path / f"{uuid()}.db"
    archivo.write_bytes(contenido)
    with closing(sqlite3.connect(archivo)) as base:
        for sentencia in sentencias:
            base.execute(sentencia)
        base.commit()
    return archivo.read_bytes()


def test_restaurar_vuelve_exactamente_a_lo_guardado(cabeceras_anita):
    abrir_orden(cabeceras_anita, "Mesa 1")
    guardada = copia(cabeceras_anita)
    abrir_orden(cabeceras_anita, "Mesa 2")
    assert ordenes(cabeceras_anita) == ["Mesa 1", "Mesa 2"]

    assert restaurar(cabeceras_anita, guardada).status_code == 204
    assert ordenes(cabeceras_anita) == ["Mesa 1"]
    # Y se sigue pudiendo registrar: la base quedó sana y sin la tabla de la copia
    abrir_orden(cabeceras_anita, "Mesa 3")
    assert ordenes(cabeceras_anita) == ["Mesa 1", "Mesa 3"]
    with database.motor_de("anita").connect() as conexion:
        tablas = conexion.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars().all()
    assert servicio.TABLA_INFO not in tablas


def test_la_copia_es_un_archivo_descargable_que_no_queda_en_cache(cabeceras_demo):
    r = cliente.get("/api/respaldo/copia", headers=cabeceras_demo)
    assert r.content.startswith(b"SQLite format 3\x00")
    assert r.headers["cache-control"] == "no-store"
    assert 'filename="mi-puestito-demo-' in r.headers["content-disposition"]


def test_la_copia_incluye_lo_ultimo_registrado_con_wal(cabeceras_anita, tmp_path):
    abrir_orden(cabeceras_anita, "Recién registrada")
    archivo = tmp_path / "copia.db"
    archivo.write_bytes(copia(cabeceras_anita))
    with closing(sqlite3.connect(archivo)) as base:
        assert base.execute("SELECT nombre_orden FROM ventas").fetchall() == [("Recién registrada",)]
        assert base.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_la_practica_no_se_restaura_sobre_un_negocio_real(cabeceras_demo, cabeceras_anita):
    abrir_orden(cabeceras_anita, "Venta real")
    r = restaurar(cabeceras_anita, copia(cabeceras_demo))
    assert r.status_code == 409
    assert "otro negocio" in r.json()["detail"]
    assert ordenes(cabeceras_anita) == ["Venta real"]


@pytest.mark.parametrize(
    "contenido",
    [b"", b"no soy una base", b"SQLite format 3\x00" + b"\x00" * 200, b"SQLite format 3\x00basura" * 400],
)
def test_un_archivo_cualquiera_se_rechaza_sin_tocar_nada(cabeceras_anita, contenido):
    abrir_orden(cabeceras_anita, "Mesa 1")
    assert restaurar(cabeceras_anita, contenido).status_code == 400
    assert ordenes(cabeceras_anita) == ["Mesa 1"]


def test_un_sqlite_de_otra_app_se_rechaza(cabeceras_anita, tmp_path):
    archivo = tmp_path / "ajeno.db"
    with closing(sqlite3.connect(archivo)) as base:
        base.execute("CREATE TABLE fotos (id INTEGER)")
        base.commit()
    assert restaurar(cabeceras_anita, archivo.read_bytes()).status_code == 400


@pytest.mark.parametrize(
    "sentencia",
    [
        "CREATE TRIGGER espia AFTER INSERT ON ventas BEGIN DELETE FROM clientes; END",
        "CREATE VIEW espia AS SELECT * FROM clientes",
    ],
)
def test_una_copia_con_codigo_escondido_se_rechaza(cabeceras_anita, tmp_path, sentencia):
    manipulada = modificar(copia(cabeceras_anita), tmp_path, sentencia)
    assert restaurar(cabeceras_anita, manipulada).status_code == 400


def test_una_copia_de_una_version_mas_nueva_se_rechaza(cabeceras_anita, tmp_path):
    futura = modificar(copia(cabeceras_anita), tmp_path, "UPDATE alembic_version SET version_num = '9999'")
    r = restaurar(cabeceras_anita, futura)
    assert r.status_code == 409
    assert "versión más nueva" in r.json()["detail"]


def test_una_copia_de_una_version_anterior_se_migra(cabeceras_anita, tmp_path, monkeypatch):
    # Una base real en la revisión 0003, antes de que Compras tuviera uuid
    archivo = tmp_path / "antigua.db"
    monkeypatch.setenv("MI_PUESTITO_BD", f"sqlite:///{archivo}")
    motor = database._crear_motor("antigua")
    monkeypatch.delenv("MI_PUESTITO_BD")
    migrar(motor, "0003")
    motor.dispose()
    antigua = modificar(
        archivo.read_bytes(),
        tmp_path,
        f"CREATE TABLE {servicio.TABLA_INFO} (proyecto TEXT, creado_en TEXT)",
        f"INSERT INTO {servicio.TABLA_INFO} VALUES ('anita', '2026-09-01')",
        "INSERT INTO proveedores (id, nombre, creado_en) VALUES (1, 'Norte', '2026-09-01 10:00:00')",
    )
    assert restaurar(cabeceras_anita, antigua).status_code == 204
    proveedores = cliente.get("/api/compras/proveedores", headers=cabeceras_anita).json()
    assert [p["nombre"] for p in proveedores] == ["Norte"]
    assert len(proveedores[0]["uuid"]) == 36


def test_antes_de_restaurar_se_guarda_lo_que_habia(cabeceras_anita, tmp_path):
    guardada = copia(cabeceras_anita)
    abrir_orden(cabeceras_anita, "Lo que había")
    assert restaurar(cabeceras_anita, guardada).status_code == 204

    anteriores = sorted((rutas.directorio_datos() / "respaldos").glob("antes-de-restaurar-anita-*.db"))
    with closing(sqlite3.connect(anteriores[-1])) as base:
        assert ("Lo que había",) in base.execute("SELECT nombre_orden FROM ventas").fetchall()


def test_si_falla_al_migrar_los_datos_vuelven_a_como_estaban(cabeceras_anita, monkeypatch):
    guardada = copia(cabeceras_anita)
    abrir_orden(cabeceras_anita, "No se debe perder")

    def falla(_motor):
        raise RuntimeError("migración rota")

    monkeypatch.setattr(servicio, "migrar", falla)
    r = restaurar(cabeceras_anita, guardada)
    assert r.status_code == 409
    assert "quedaron como estaban" in r.json()["detail"]
    assert ordenes(cabeceras_anita) == ["No se debe perder"]


def test_un_archivo_enorme_se_rechaza_antes_de_leerlo(cabeceras_anita, monkeypatch):
    monkeypatch.setattr(servicio, "TAMANO_MAXIMO", 10)
    assert restaurar(cabeceras_anita, b"x" * 11).status_code == 413


def test_sin_espacio_en_disco_no_se_empieza(cabeceras_anita, monkeypatch):
    monkeypatch.setattr(servicio, "espacio_suficiente", lambda _tamano: False)
    assert restaurar(cabeceras_anita, b"SQLite format 3\x00").status_code == 507


def test_exige_sesion():
    assert cliente.get("/api/respaldo/copia").status_code == 401
    assert cliente.post("/api/respaldo/restaurar", content=b"x").status_code == 401


def test_cada_token_solo_descarga_su_negocio(cabeceras_demo, cabeceras_anita, tmp_path):
    abrir_orden(cabeceras_anita, "Secreto de Anita")
    archivo = tmp_path / "demo.db"
    archivo.write_bytes(copia(cabeceras_demo))
    with closing(sqlite3.connect(archivo)) as base:
        nombres = base.execute("SELECT nombre_orden FROM ventas").fetchall()
    assert ("Secreto de Anita",) not in nombres
