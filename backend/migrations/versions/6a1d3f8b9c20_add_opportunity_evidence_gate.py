"""add opportunity evidence gate

Revision ID: 6a1d3f8b9c20
Revises: 4e8b2c6d1a75
Create Date: 2026-07-31 01:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6a1d3f8b9c20"
down_revision: str | Sequence[str] | None = "4e8b2c6d1a75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_eligibility_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("gate_version", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evaluated_cluster_count", sa.Integer(), nullable=False),
        sa.Column("eligible_cluster_count", sa.Integer(), nullable=False),
        sa.Column("excluded_cluster_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_opportunity_eligibility_runs_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_eligibility_runs"),
        ),
        sa.UniqueConstraint(
            "clustering_run_id",
            "gate_version",
            "input_fingerprint",
            name="opportunity_eligibility_run_version",
        ),
    )
    op.create_table(
        "opportunity_eligibility_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("evidence_level", sa.String(length=40), nullable=False),
        sa.Column("blocker_codes", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_opportunity_eligibility_decisions_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["opportunity_eligibility_runs.id"],
            name=op.f(
                "fk_opportunity_eligibility_decisions_run_id_opportunity_eligibility_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_eligibility_decisions"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "cluster_id",
            name="opportunity_eligibility_run_cluster",
        ),
    )
    op.create_index(
        "ix_opportunity_eligibility_decision_eligible",
        "opportunity_eligibility_decisions",
        ["run_id", "eligible"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_eligibility_decision_eligible",
        table_name="opportunity_eligibility_decisions",
    )
    op.drop_table("opportunity_eligibility_decisions")
    op.drop_table("opportunity_eligibility_runs")
