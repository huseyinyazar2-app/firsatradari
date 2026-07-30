"""add ingestion run counters

Revision ID: d9764b257f9d
Revises: 9752c25a7b36
Create Date: 2026-07-29 21:17:14.431718
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9764b257f9d"
down_revision: str | Sequence[str] | None = "9752c25a7b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalized_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost",
            sa.Numeric(precision=12, scale=6),
            nullable=False,
            server_default="0",
        ),
    )
    for column in columns:
        op.add_column("ingestion_runs", column)
        op.alter_column("ingestion_runs", column.name, server_default=None)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "estimated_cost")
    op.drop_column("ingestion_runs", "duplicate_item_count")
    op.drop_column("ingestion_runs", "normalized_item_count")
    op.drop_column("ingestion_runs", "response_count")
