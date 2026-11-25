"""La nube (Vercel + Neon, ADR-058): PostgreSQL con un esquema por proyecto.

Las pruebas que necesitan una base PostgreSQL de verdad corren solo si hay una configurada
(`DATABASE_URL` o `MI_PUESTITO_POSTGRES_URL`): en el CI las corre el job con el servicio de
Postgres, y en Staging local `DATABASE_URL=postgresql://… pytest`. Toda la suite corre igual
sobre Postgres en ese job.
"""

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import database
from main import app


def test_la_url_de_neon_usa_el_driver_de_psycopg(monkeypatch):
    monkeypatch.delenv("MI_PUESTITO_POSTGRES_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@ep-x.neon.tech/neondb?sslmode=require")
    assert database.url_postgres() == "postgresql+psycopg://u:p@ep-x.neon.tech/neondb?sslmode=require"
    monkeypatch.setenv("MI_PUESTITO_POSTGRES_URL", "postgresql://otra/base")
    assert database.url_postgres() == "postgresql+psycopg://otra/base"


def test_sin_url_de_la_nube_sigue_siendo_sqlite(monkeypatch):
    monkeypatch.delenv("MI_PUESTITO_POSTGRES_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database.url_postgres() is None


@pytest.mark.parametrize("clave", ["demo; drop schema x", "Demo", "", "a" * 41])
def test_una_clave_rara_no_llega_a_un_nombre_de_esquema(clave):
    with pytest.raises(ValueError):
        database.esquema_de(clave)


con_postgres = pytest.mark.skipif(database.url_postgres() is None, reason="Sin PostgreSQL configurado")


@con_postgres
def test_cada_proyecto_vive_en_su_esquema(cabeceras_demo, cabeceras_anita):
    cliente = TestClient(app)
    cliente.post("/api/ventas/", json={"uuid": "8b0b7c1e-1111-4a6a-9c3e-000000000001", "tipo": "orden_activa", "nombre_orden": "Mesa demo"}, headers=cabeceras_demo)
    motor = create_engine(database.url_postgres())
    with motor.connect() as conexion:
        en_demo = conexion.exec_driver_sql("SELECT count(*) FROM proyecto_demo.ventas WHERE nombre_orden = 'Mesa demo'").scalar()
        en_anita = conexion.exec_driver_sql("SELECT count(*) FROM proyecto_anita.ventas WHERE nombre_orden = 'Mesa demo'").scalar()
    motor.dispose()
    assert (en_demo, en_anita) == (1, 0)


@con_postgres
def test_una_escritura_toma_el_candado_de_su_proyecto_y_no_el_de_otro():
    motor = create_engine(database.url_postgres())
    escritura = database.sesion_escritura_para("demo")
    try:
        escritura.execute(database.text_select_1())  # abre la transacción: SET LOCAL + candado
        with motor.connect() as otra:
            libre_demo = otra.exec_driver_sql(f"SELECT pg_try_advisory_xact_lock({database.candado_de('demo')})").scalar()
            libre_anita = otra.exec_driver_sql(f"SELECT pg_try_advisory_xact_lock({database.candado_de('anita')})").scalar()
        assert (libre_demo, libre_anita) == (False, True)
    finally:
        escritura.rollback()
        escritura.close()
        motor.dispose()


@con_postgres
def test_dos_instancias_que_migran_a_la_vez_no_chocan():
    from migraciones.ejecutar import migrar

    errores = []

    def migrar_en_otra_instancia():
        motor = database._crear_motor("demo")  # motor propio, como otra instancia de la función
        try:
            migrar(motor)
        except Exception as error:  # noqa: BLE001
            errores.append(error)
        finally:
            motor.dispose()

    hilos = [threading.Thread(target=migrar_en_otra_instancia) for _ in range(3)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert errores == []


@con_postgres
def test_el_respaldo_de_archivo_explica_que_en_la_nube_no_hace_falta(cabeceras_anita):
    r = TestClient(app).get("/api/respaldo/copia", headers=cabeceras_anita)
    assert r.status_code == 409
    assert "nube" in r.json()["detail"]


@con_postgres
def test_en_la_nube_el_limite_de_intentos_es_comun_a_todas_las_instancias(monkeypatch):
    """Un contador por instancia dejaría repartir intentos para adivinar el PIN (ADR-058)."""
    import intentos_nube
    import seguridad

    monkeypatch.setattr(seguridad, "ENTORNO", "production")
    intentos_nube.limpiar("anita")
    try:
        for _ in range(seguridad.INTENTOS_LIBRES):
            assert seguridad.verificar_credenciales("anita", "000001") is None
            seguridad._intentos.clear()  # la siguiente petición cae en otra instancia: memoria vacía
        with pytest.raises(seguridad.DemasiadosIntentos):
            seguridad.verificar_credenciales("anita", "999999")
    finally:
        intentos_nube.limpiar("anita")
        intentos_nube.olvidar_motor()
