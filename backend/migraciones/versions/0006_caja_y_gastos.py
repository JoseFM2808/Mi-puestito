"""Caja con saldo inicial y gastos (D-24, ADR-051).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aperturas_caja",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("efectivo_inicial", sa.Integer(), nullable=False),
        sa.Column("yape_inicial", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("efectivo_inicial >= 0", name="ck_apertura_efectivo_no_negativo"),
        sa.CheckConstraint("yape_inicial >= 0", name="ck_apertura_yape_no_negativo"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_aperturas_caja_uuid"),
        sa.UniqueConstraint("dia", name="uq_aperturas_caja_dia"),
    )
    op.create_table(
        "gastos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("monto", sa.Integer(), nullable=False),
        sa.Column(
            "medio", sa.Enum("efectivo", "yape_plin", name="mediodepago", native_enum=False), nullable=False
        ),
        sa.Column("ambito", sa.Enum("puesto", "hogar", name="ambitogasto", native_enum=False), nullable=False),
        sa.Column(
            "categoria",
            sa.Enum(
                "proveedor", "alquiler", "servicios", "transporte", "alimentacion", "educacion", "otros",
                name="categoriagasto", native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("descripcion", sa.String(120), nullable=True),
        sa.Column("orden_compra_uuid", sa.String(36), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("monto > 0", name="ck_gasto_monto_positivo"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_gastos_uuid"),
        sa.UniqueConstraint("orden_compra_uuid", name="uq_gastos_orden_compra_uuid"),
    )
    op.create_index("ix_gastos_creado_en", "gastos", ["creado_en"])


def downgrade() -> None:
    op.drop_index("ix_gastos_creado_en", table_name="gastos")
    op.drop_table("gastos")
    op.drop_table("aperturas_caja")
