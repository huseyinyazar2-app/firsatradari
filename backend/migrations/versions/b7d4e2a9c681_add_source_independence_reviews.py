"""add source independence reviews

Revision ID: b7d4e2a9c681
Revises: a1e7c5d3b942
Create Date: 2026-07-31 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d4e2a9c681"
down_revision: str | Sequence[str] | None = "a1e7c5d3b942"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_independence_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f(
                "fk_source_independence_reviews_source_id_data_sources"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_source_independence_reviews"),
        ),
        sa.UniqueConstraint(
            "source_id",
            "version",
            name="source_independence_review_version",
        ),
    )
    op.create_index(
        "ix_source_independence_reviews_source_time",
        "source_independence_reviews",
        ["source_id", "reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_independence_reviews_source_time",
        table_name="source_independence_reviews",
    )
    op.drop_table("source_independence_reviews")
