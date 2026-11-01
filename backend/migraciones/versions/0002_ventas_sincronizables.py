"""Ventas sincronizables: dinero en céntimos, uuid del dispositivo y estado "fiada".

- ADR-035: todo monto pasa de NUMERIC (coma flotante en SQLite) a céntimos
  enteros. Los datos existentes se convierten ANTES de cambiar el tipo.
- ADR-032: clientes, ventas, items y pagos llevan `uuid` (identidad pública
  y clave de idempotencia). Las filas existentes reciben uno nuevo.
- Items de venta: enlace opcional a Inventario (`producto_uuid`, sin clave
  foránea entre módulos) y `cantidad_num` en milésimas.
- Restricciones de montos no negativos y `actualizado_en` para datos maestros.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabla, columna) de dinero que pasan a céntimos
MONTOS = [
    ("clientes", "limite_credito"),
    ("ventas", "monto_total"),
    ("items_venta", "monto"),
    ("pagos", "monto"),
    ("ordenes_compra", "monto_total"),
    ("ordenes_compra", "monto_real"),
    ("items_orden_compra", "monto"),
    ("items_orden_compra", "monto_sustituto"),
]

CON_UUID = ["clientes", "ventas", "items_venta", "pagos"]


def _rellenar_uuids(tabla: str) -> None:
    conexion = op.get_bind()
    ids = conexion.execute(sa.text(f"SELECT id FROM {tabla} WHERE uuid IS NULL")).scalars().all()
    for id_fila in ids:
        conexion.execute(
            sa.text(f"UPDATE {tabla} SET uuid = :uuid WHERE id = :id"),
            {"uuid": str(uuid4()), "id": id_fila},
        )


def upgrade() -> None:
    # 1) Datos: soles → céntimos, mientras la columna aún es NUMERIC
    for tabla, columna in MONTOS:
        op.execute(
            f"UPDATE {tabla} SET {columna} = CAST(ROUND({columna} * 100) AS INTEGER) "
            f"WHERE {columna} IS NOT NULL"
        )

    # 2) uuid: se agrega nulo, se rellena, y recién entonces se exige
    for tabla in CON_UUID:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("uuid", sa.String(36), nullable=True))
        _rellenar_uuids(tabla)

    with op.batch_alter_table("clientes") as batch:
        batch.add_column(sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE clientes SET actualizado_en = creado_en")

    # 3) Tipos y restricciones (batch = recrear tabla copiando filas)
    with op.batch_alter_table("clientes") as batch:
        batch.alter_column("uuid", existing_type=sa.String(36), nullable=False)
        batch.alter_column("actualizado_en", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column("limite_credito", existing_type=sa.Numeric(10, 2), type_=sa.Integer())
        batch.create_unique_constraint("uq_clientes_uuid", ["uuid"])

    with op.batch_alter_table("ventas") as batch:
        batch.alter_column("uuid", existing_type=sa.String(36), nullable=False)
        batch.alter_column(
            "monto_total", existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False
        )
        batch.create_unique_constraint("uq_ventas_uuid", ["uuid"])
        batch.create_index("ix_ventas_estado_cerrada_en", ["estado", "cerrada_en"])
        batch.create_check_constraint("ck_venta_monto_no_negativo", "monto_total >= 0")

    with op.batch_alter_table("items_venta") as batch:
        batch.alter_column("uuid", existing_type=sa.String(36), nullable=False)
        batch.alter_column(
            "monto", existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False
        )
        batch.add_column(sa.Column("producto_uuid", sa.String(36), nullable=True))
        batch.add_column(sa.Column("cantidad_num", sa.Integer(), nullable=True))
        batch.create_unique_constraint("uq_items_venta_uuid", ["uuid"])
        batch.create_index("ix_items_venta_producto_uuid", ["producto_uuid"])
        batch.create_check_constraint("ck_item_venta_monto_no_negativo", "monto >= 0")

    with op.batch_alter_table("pagos") as batch:
        batch.alter_column("uuid", existing_type=sa.String(36), nullable=False)
        batch.alter_column(
            "monto", existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False
        )
        batch.create_unique_constraint("uq_pagos_uuid", ["uuid"])
        batch.create_check_constraint("ck_pago_monto_positivo", "monto > 0")

    with op.batch_alter_table("ordenes_compra") as batch:
        batch.alter_column(
            "monto_total", existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False
        )
        batch.alter_column("monto_real", existing_type=sa.Numeric(10, 2), type_=sa.Integer())

    with op.batch_alter_table("items_orden_compra") as batch:
        batch.alter_column(
            "monto", existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False
        )
        batch.alter_column("monto_sustituto", existing_type=sa.Numeric(10, 2), type_=sa.Integer())

    # El RUC ya era único, pero sin nombre: se le da uno para poder migrarlo
    with op.batch_alter_table("proveedores") as batch:
        batch.create_unique_constraint("uq_proveedores_ruc", ["ruc"])


def downgrade() -> None:
    with op.batch_alter_table("proveedores") as batch:
        batch.drop_constraint("uq_proveedores_ruc", type_="unique")

    for tabla, columna in [("items_orden_compra", "monto"), ("items_orden_compra", "monto_sustituto"),
                           ("ordenes_compra", "monto_total"), ("ordenes_compra", "monto_real")]:
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column(columna, existing_type=sa.Integer(), type_=sa.Numeric(10, 2))

    with op.batch_alter_table("pagos") as batch:
        batch.drop_constraint("ck_pago_monto_positivo", type_="check")
        batch.drop_constraint("uq_pagos_uuid", type_="unique")
        batch.alter_column("monto", existing_type=sa.Integer(), type_=sa.Numeric(10, 2))
        batch.drop_column("uuid")

    with op.batch_alter_table("items_venta") as batch:
        batch.drop_constraint("ck_item_venta_monto_no_negativo", type_="check")
        batch.drop_index("ix_items_venta_producto_uuid")
        batch.drop_constraint("uq_items_venta_uuid", type_="unique")
        batch.drop_column("cantidad_num")
        batch.drop_column("producto_uuid")
        batch.alter_column("monto", existing_type=sa.Integer(), type_=sa.Numeric(10, 2))
        batch.drop_column("uuid")

    with op.batch_alter_table("ventas") as batch:
        batch.drop_constraint("ck_venta_monto_no_negativo", type_="check")
        batch.drop_index("ix_ventas_estado_cerrada_en")
        batch.drop_constraint("uq_ventas_uuid", type_="unique")
        batch.alter_column("monto_total", existing_type=sa.Integer(), type_=sa.Numeric(10, 2))
        batch.drop_column("uuid")

    with op.batch_alter_table("clientes") as batch:
        batch.drop_constraint("uq_clientes_uuid", type_="unique")
        batch.alter_column("limite_credito", existing_type=sa.Integer(), type_=sa.Numeric(10, 2))
        batch.drop_column("actualizado_en")
        batch.drop_column("uuid")

    for tabla, columna in MONTOS:
        op.execute(f"UPDATE {tabla} SET {columna} = {columna} / 100.0 WHERE {columna} IS NOT NULL")
