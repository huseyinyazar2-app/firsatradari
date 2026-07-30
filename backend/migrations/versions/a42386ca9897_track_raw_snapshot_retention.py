"""track raw snapshot retention

Revision ID: a42386ca9897
Revises: d9764b257f9d
Create Date: 2026-07-29 21:19:13.589804
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a42386ca9897"
down_revision: str | Sequence[str] | None = "d9764b257f9d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_snapshots",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE raw_snapshots AS snapshot
        SET retention_until =
            snapshot.observed_at + source.retention_days * INTERVAL '1 day'
        FROM data_sources AS source
        WHERE source.id = snapshot.source_id
          AND source.retention_days IS NOT NULL
          AND source.retention_days > 0
        """
    )
    op.create_index(
        op.f("ix_raw_snapshots_retention_until"),
        "raw_snapshots",
        ["retention_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_raw_snapshots_retention_until"),
        table_name="raw_snapshots",
    )
    op.drop_column("raw_snapshots", "retention_until")
