"""add reviewed ontology claims

Revision ID: d9a3f6b1c472
Revises: c4e8a1d7f209
Create Date: 2026-07-31 02:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9a3f6b1c472"
down_revision: str | Sequence[str] | None = "c4e8a1d7f209"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_claims",
        sa.Column(
            "created_by",
            sa.String(length=200),
            nullable=False,
            server_default="system:legacy-evidence-graph",
        ),
    )
    op.alter_column(
        "evidence_claims",
        "created_by",
        server_default=None,
    )
    op.create_table(
        "claim_commercial_outcome_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["evidence_claims.id"],
            name=op.f(
                "fk_claim_commercial_outcome_links_claim_id_evidence_claims"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["commercial_outcomes.id"],
            name=op.f(
                "fk_claim_commercial_outcome_links_outcome_id_"
                "commercial_outcomes"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_claim_commercial_outcome_links"),
        ),
        sa.UniqueConstraint(
            "claim_id",
            "outcome_id",
            "direction",
            name="claim_commercial_outcome_direction",
        ),
    )
    op.create_index(
        "ix_claim_commercial_outcome_claim_direction",
        "claim_commercial_outcome_links",
        ["claim_id", "direction"],
        unique=False,
    )
    op.create_table(
        "evidence_claim_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["evidence_claims.id"],
            name=op.f(
                "fk_evidence_claim_reviews_claim_id_evidence_claims"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_evidence_claim_reviews"),
        ),
        sa.UniqueConstraint(
            "claim_id",
            "version",
            name="evidence_claim_review_version",
        ),
    )
    op.create_index(
        "ix_evidence_claim_review_claim_time",
        "evidence_claim_reviews",
        ["claim_id", "reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_claim_review_claim_time",
        table_name="evidence_claim_reviews",
    )
    op.drop_table("evidence_claim_reviews")
    op.drop_index(
        "ix_claim_commercial_outcome_claim_direction",
        table_name="claim_commercial_outcome_links",
    )
    op.drop_table("claim_commercial_outcome_links")
    op.drop_column("evidence_claims", "created_by")
