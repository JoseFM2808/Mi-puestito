"""Lo que el Asistente recuerda del negocio (D-26, ADR-052).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memorias_asistente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("texto", sa.String(160), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_memorias_asistente_uuid"),
    )


def downgrade() -> None:
    op.drop_table("memorias_asistente")
