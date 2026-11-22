"""Costo de la última compra y fecha de vencimiento de cada producto (D-22).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("productos") as batch:
        batch.add_column(sa.Column("costo_ultimo", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("vence_el", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("productos") as batch:
        batch.drop_column("vence_el")
        batch.drop_column("costo_ultimo")
