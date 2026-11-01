"""Compras con identidad del dispositivo: uuid en proveedores, órdenes e items (ADR-032).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-01
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CON_UUID = ["proveedores", "ordenes_compra", "items_orden_compra"]


def upgrade() -> None:
    # Se agrega nulo, se rellena y recién entonces se exige: migrar no pierde filas
    conexion = op.get_bind()
    for tabla in CON_UUID:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("uuid", sa.String(36), nullable=True))
        ids = conexion.execute(sa.text(f"SELECT id FROM {tabla}")).scalars().all()
        for id_fila in ids:
            conexion.execute(
                sa.text(f"UPDATE {tabla} SET uuid = :uuid WHERE id = :id"),
                {"uuid": str(uuid4()), "id": id_fila},
            )
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column("uuid", existing_type=sa.String(36), nullable=False)
            batch.create_unique_constraint(f"uq_{tabla}_uuid", ["uuid"])


def downgrade() -> None:
    for tabla in CON_UUID:
        with op.batch_alter_table(tabla) as batch:
            batch.drop_constraint(f"uq_{tabla}_uuid", type_="unique")
            batch.drop_column("uuid")
