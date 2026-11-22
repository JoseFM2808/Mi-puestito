"""Categoría de cada producto, para ver qué tipo de producto deja más ganancia (Modulo-Analisis).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("productos") as batch:
        batch.add_column(sa.Column("categoria", sa.String(40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("productos") as batch:
        batch.drop_column("categoria")
