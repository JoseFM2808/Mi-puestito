"""Alias de proveedores: el mismo RUC registrado sin red en dos tablets (D-25).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alias_proveedores",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("proveedor_id", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index("ix_alias_proveedores_proveedor_id", "alias_proveedores", ["proveedor_id"])


def downgrade() -> None:
    op.drop_index("ix_alias_proveedores_proveedor_id", table_name="alias_proveedores")
    op.drop_table("alias_proveedores")
