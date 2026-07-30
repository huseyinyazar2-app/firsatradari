"""add evidence claim graph

Revision ID: 8c4e1b7d2a63
Revises: 6a1d3f8b9c20
Create Date: 2026-07-31 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c4e1b7d2a63"
down_revision: str | Sequence[str] | None = "6a1d3f8b9c20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_claim_id", sa.Uuid(), nullable=True),
        sa.Column("claim_type", sa.String(length=50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("generator_key", sa.String(length=80), nullable=False),
        sa.Column("generator_version", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evidence_level", sa.String(length=40), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("independence_group_count", sa.Integer(), nullable=False),
        sa.Column("supporting_evidence_count", sa.Integer(), nullable=False),
        sa.Column("independence_blockers", sa.JSON(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_evidence_claims_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_claim_id"],
            ["evidence_claims.id"],
            name=op.f(
                "fk_evidence_claims_supersedes_claim_id_evidence_claims"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_evidence_claims"),
        ),
    )
    op.create_index(
        "ix_evidence_claim_cluster_current",
        "evidence_claims",
        ["cluster_id", "is_current"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_claim_input_current",
        "evidence_claims",
        ["input_fingerprint", "is_current"],
        unique=False,
    )
    op.create_table(
        "claim_evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("problem_evidence_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["evidence_claims.id"],
            name=op.f(
                "fk_claim_evidence_links_claim_id_evidence_claims"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["problem_evidence_id"],
            ["problem_evidence.id"],
            name=op.f(
                "fk_claim_evidence_links_problem_evidence_id_problem_evidence"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f(
                "fk_claim_evidence_links_source_id_data_sources"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_claim_evidence_links"),
        ),
        sa.UniqueConstraint(
            "claim_id",
            "problem_evidence_id",
            "direction",
            name="claim_problem_evidence_direction",
        ),
    )
    op.create_index(
        "ix_claim_evidence_link_claim_direction",
        "claim_evidence_links",
        ["claim_id", "direction"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_evidence_link_claim_direction",
        table_name="claim_evidence_links",
    )
    op.drop_table("claim_evidence_links")
    op.drop_index(
        "ix_evidence_claim_input_current",
        table_name="evidence_claims",
    )
    op.drop_index(
        "ix_evidence_claim_cluster_current",
        table_name="evidence_claims",
    )
    op.drop_table("evidence_claims")
