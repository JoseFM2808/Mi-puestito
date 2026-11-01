"""Inventario como libro mayor de movimientos (ADR-031).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("codigo_barras", sa.String(32), nullable=True),
        sa.Column(
            "unidad",
            sa.Enum("unidad", "kg", "litro", name="unidad", native_enum=False),
            nullable=False,
        ),
        sa.Column("precio_venta", sa.Integer(), nullable=True),
        sa.Column("stock_actual", sa.Integer(), nullable=False),
        sa.Column("stock_minimo", sa.Integer(), nullable=True),
        sa.Column("tiene_vencimiento", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_productos_uuid"),
        sa.UniqueConstraint("nombre", name="uq_productos_nombre"),
        sa.UniqueConstraint("codigo_barras", name="uq_productos_codigo_barras"),
    )
    op.create_table(
        "movimientos_inventario",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column(
            "motivo",
            sa.Enum(
                "venta", "anulacion_venta", "compra", "ajuste", "merma",
                name="motivomovimiento", native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("origen_tipo", sa.String(40), nullable=False),
        sa.Column("origen_ref", sa.String(36), nullable=False),
        sa.Column("nota", sa.String(200), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("delta != 0", name="ck_movimiento_delta_no_cero"),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origen_tipo", "origen_ref", name="uq_movimiento_origen"),
    )
    op.create_index(
        "ix_movimientos_inventario_producto_id", "movimientos_inventario", ["producto_id"]
    )
    op.create_index(
        "ix_movimientos_inventario_creado_en", "movimientos_inventario", ["creado_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_movimientos_inventario_creado_en", table_name="movimientos_inventario")
    op.drop_index("ix_movimientos_inventario_producto_id", table_name="movimientos_inventario")
    op.drop_table("movimientos_inventario")
    op.drop_table("productos")
