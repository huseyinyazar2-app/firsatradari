"""add raw snapshot purge state

Revision ID: 4f8a2c7d1e90
Revises: f3c5d8e0b679
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f8a2c7d1e90"
down_revision: str | Sequence[str] | None = "f3c5d8e0b679"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_snapshots",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_raw_snapshots_purged_at"),
        "raw_snapshots",
        ["purged_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_raw_snapshots_purged_at"),
        table_name="raw_snapshots",
    )
    op.drop_column("raw_snapshots", "purged_at")
