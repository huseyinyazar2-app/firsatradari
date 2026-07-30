"""add clustering input definition

Revision ID: 0a5d9e7c2b64
Revises: f6c2a8d4b193
Create Date: 2026-07-30 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0a5d9e7c2b64"
down_revision: str | Sequence[str] | None = "f6c2a8d4b193"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "problem_clustering_runs",
        sa.Column(
            "input_definition",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )
    op.alter_column(
        "problem_clustering_runs",
        "input_definition",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("problem_clustering_runs", "input_definition")
