"""Migraciones (D-03): el esquema real sale de Alembic, y migrar nunca pierde datos.

Cada test usa su propio archivo SQLite temporal, con la misma configuración
de conexión que producción (WAL, claves foráneas, BEGIN explícito).
"""

import importlib
from decimal import Decimal

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

import database
from migraciones.ejecutar import configuracion, migrar


@pytest.fixture()
def motor(tmp_path, monkeypatch):
    monkeypatch.setenv("MI_PUESTITO_BD", f"sqlite:///{tmp_path / 'prueba.db'}")
    motor = database._crear_motor("prueba")
    yield motor
    motor.dispose()


def _metadatos():
    for modulo in ("ventas", "compras", "inventario"):
        importlib.import_module(f"modules.{modulo}.models")
    return database.Base.metadata


def _revision_actual(motor) -> str:
    with motor.connect() as conexion:
        return conexion.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def test_el_esquema_migrado_coincide_con_los_modelos(motor):
    # Si alguien cambia un modelo sin escribir su migración, esto falla
    migrar(motor)
    with motor.connect() as conexion:
        diferencias = compare_metadata(
            MigrationContext.configure(conexion, opts={"compare_type": True}), _metadatos()
        )
    assert diferencias == []


def test_migrar_dos_veces_no_cambia_nada(motor):
    migrar(motor)
    migrar(motor)
    assert _revision_actual(motor) == "0004"


def test_migrar_datos_de_la_demo_1_conserva_items_y_pasa_a_centimos(motor):
    # Una base con datos en el esquema viejo (NUMERIC, sin uuid)
    migrar(motor, "0001")
    with motor.begin() as c:
        c.execute(text("INSERT INTO clientes (id, nombre, limite_credito, creado_en) "
                       "VALUES (1, 'Sra. Flora', 100.5, '2026-09-01 10:00:00')"))
        c.execute(text("INSERT INTO ventas (id, tipo, cliente_id, estado, monto_total, abierta_en) "
                       "VALUES (1, 'fiado', 1, 'abierta', 30.5, '2026-09-01 10:00:00')"))
        c.execute(text("INSERT INTO items_venta (id, venta_id, nombre_producto, monto) "
                       "VALUES (1, 1, 'Arroz', 30.5)"))
        c.execute(text("INSERT INTO pagos (id, cliente_id, monto, metodo_pago, creado_en) "
                       "VALUES (1, 1, 10.25, 'efectivo', '2026-09-02 10:00:00')"))

    migrar(motor)

    with motor.connect() as c:
        # Recrear "ventas" en modo batch NO debe disparar el ON DELETE CASCADE
        assert c.execute(text("SELECT COUNT(*) FROM items_venta")).scalar_one() == 1
        assert c.execute(text("SELECT monto_total FROM ventas")).scalar_one() == 3050
        assert c.execute(text("SELECT monto FROM pagos")).scalar_one() == 1025
        assert c.execute(text("SELECT limite_credito FROM clientes")).scalar_one() == 10050
        uuids = c.execute(text("SELECT uuid FROM ventas UNION ALL SELECT uuid FROM items_venta "
                               "UNION ALL SELECT uuid FROM pagos UNION ALL SELECT uuid FROM clientes"))
        assert all(len(u) == 36 for u in uuids.scalars())

    from modules.ventas.models import Venta

    with Session(motor) as sesion:
        venta = sesion.scalars(select(Venta)).one()
        assert venta.monto_total == Decimal("30.50")
        assert venta.items[0].monto == Decimal("30.50")


def test_migrar_compras_conserva_pedidos_y_les_da_uuid(motor):
    migrar(motor, "0003")
    with motor.begin() as c:
        c.execute(text("INSERT INTO proveedores (id, nombre, creado_en) VALUES (1, 'Norte', '2026-09-01 10:00:00')"))
        c.execute(text("INSERT INTO ordenes_compra (id, proveedor_id, estado, monto_total, creado_en, actualizado_en) "
                       "VALUES (1, 1, 'en_camino', 3050, '2026-09-01 10:00:00', '2026-09-01 10:00:00')"))
        c.execute(text("INSERT INTO items_orden_compra (id, orden_compra_id, nombre_producto, monto, estado_recepcion) "
                       "VALUES (1, 1, 'Arroz', 3050, 'pendiente')"))

    migrar(motor)

    with motor.connect() as c:
        # Recrear "ordenes_compra" en modo batch NO debe disparar el ON DELETE CASCADE
        assert c.execute(text("SELECT COUNT(*) FROM items_orden_compra")).scalar_one() == 1
        uuids = c.execute(text("SELECT uuid FROM proveedores UNION ALL SELECT uuid FROM ordenes_compra "
                               "UNION ALL SELECT uuid FROM items_orden_compra")).scalars().all()
        assert len(set(uuids)) == 3 and all(len(u) == 36 for u in uuids)


def test_una_base_creada_antes_de_alembic_se_marca_y_se_migra(motor):
    # Así quedaron las bases de la Demo 1: tablas de create_all, sin alembic_version
    migrar(motor, "0001")
    with motor.begin() as c:
        c.execute(text("DROP TABLE alembic_version"))

    migrar(motor)

    assert _revision_actual(motor) == "0004"
    assert "productos" in inspect(motor).get_table_names()


def test_las_migraciones_se_pueden_revertir(motor):
    # El downgrade es la red de seguridad si una versión sale mal
    migrar(motor)
    cfg = configuracion()
    with motor.connect() as conexion:
        conexion.connection.driver_connection.execute("PRAGMA foreign_keys=OFF")
        with conexion.begin():
            cfg.attributes["connection"] = conexion
            command.downgrade(cfg, "0001")
    assert _revision_actual(motor) == "0001"
    assert "productos" not in inspect(motor).get_table_names()
    migrar(motor)
    assert _revision_actual(motor) == "0004"
