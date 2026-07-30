"""add grounded opportunity versions

Revision ID: c4e8a1d7f209
Revises: b7d4e2a9c681
Create Date: 2026-07-31 01:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1d7f209"
down_revision: str | Sequence[str] | None = "b7d4e2a9c681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("origin_cluster_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["origin_cluster_id"],
            ["problem_clusters.id"],
            name=op.f("fk_opportunities_origin_cluster_id_problem_clusters"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opportunities")),
        sa.UniqueConstraint(
            "origin_cluster_id",
            name=op.f("uq_opportunities_origin_cluster_id"),
        ),
    )
    op.create_table(
        "opportunity_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("eligibility_decision_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "ontology_schema_version",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("ontology", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_level", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["eligibility_decision_id"],
            ["opportunity_eligibility_decisions.id"],
            name=op.f(
                "fk_opportunity_versions_eligibility_decision_id_"
                "opportunity_eligibility_decisions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name=op.f(
                "fk_opportunity_versions_opportunity_id_opportunities"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_versions_supersedes_version_id_"
                "opportunity_versions"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_versions"),
        ),
        sa.UniqueConstraint(
            "input_fingerprint",
            name=op.f("uq_opportunity_versions_input_fingerprint"),
        ),
        sa.UniqueConstraint(
            "opportunity_id",
            "version_number",
            name="opportunity_version_number",
        ),
    )
    op.create_index(
        "ix_opportunity_versions_current",
        "opportunity_versions",
        ["opportunity_id", "is_current"],
        unique=False,
    )
    op.create_table(
        "opportunity_component_claim_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("component_key", sa.String(length=50), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["evidence_claims.id"],
            name=op.f(
                "fk_opportunity_component_claim_links_claim_id_"
                "evidence_claims"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_component_claim_links_"
                "opportunity_version_id_opportunity_versions"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_component_claim_links"),
        ),
        sa.UniqueConstraint(
            "opportunity_version_id",
            "component_key",
            name="opportunity_version_component",
        ),
    )
    op.create_index(
        "ix_opportunity_component_claim",
        "opportunity_component_claim_links",
        ["claim_id", "component_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_component_claim",
        table_name="opportunity_component_claim_links",
    )
    op.drop_table("opportunity_component_claim_links")
    op.drop_index(
        "ix_opportunity_versions_current",
        table_name="opportunity_versions",
    )
    op.drop_table("opportunity_versions")
    op.drop_table("opportunities")
