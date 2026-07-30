"""add stack exchange questions

Revision ID: 9d2f6a4c1b80
Revises: 8c4e1b7d2a63
Create Date: 2026-07-31 03:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9d2f6a4c1b80"
down_revision: str | Sequence[str] | None = "8c4e1b7d2a63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stack_exchange_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site", sa.String(length=80), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(length=800), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("answer_count", sa.Integer(), nullable=False),
        sa.Column("is_answered", sa.Boolean(), nullable=False),
        sa.Column("accepted_answer_id", sa.BigInteger(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("bounty_amount", sa.Integer(), nullable=True),
        sa.Column("content_license", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at_source",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at_source",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_edit_at_source",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id"],
            ["entities.id"],
            name=op.f("fk_stack_exchange_questions_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f(
                "fk_stack_exchange_questions_snapshot_id_raw_snapshots"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_stack_exchange_questions"),
        ),
        sa.UniqueConstraint(
            "site",
            "question_id",
            name="stack_exchange_site_question",
        ),
    )
    op.create_index(
        "ix_stack_exchange_question_site_activity",
        "stack_exchange_questions",
        ["site", "last_activity_at_source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stack_exchange_question_site_activity",
        table_name="stack_exchange_questions",
    )
    op.drop_table("stack_exchange_questions")
