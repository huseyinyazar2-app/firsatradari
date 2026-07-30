"""add problem cluster lineage

Revision ID: 4e8b2c6d1a75
Revises: 2c7f1a9e5d83
Create Date: 2026-07-31 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4e8b2c6d1a75"
down_revision: str | Sequence[str] | None = "2c7f1a9e5d83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_cluster_lineage_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("previous_clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("current_clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("previous_cluster_count", sa.Integer(), nullable=False),
        sa.Column("current_cluster_count", sa.Integer(), nullable=False),
        sa.Column("matched_cluster_count", sa.Integer(), nullable=False),
        sa.Column("stable_cluster_count", sa.Integer(), nullable=False),
        sa.Column("split_relation_count", sa.Integer(), nullable=False),
        sa.Column("merge_relation_count", sa.Integer(), nullable=False),
        sa.Column("new_cluster_count", sa.Integer(), nullable=False),
        sa.Column("disappeared_cluster_count", sa.Integer(), nullable=False),
        sa.Column(
            "stability_rate",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "mean_best_member_jaccard",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column("passes_stability_gate", sa.Boolean(), nullable=False),
        sa.Column("calculation", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["current_clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_lineage_runs_current_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["previous_clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_lineage_runs_previous_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_lineage_runs"),
        ),
        sa.UniqueConstraint(
            "previous_clustering_run_id",
            "current_clustering_run_id",
            "algorithm_version",
            name="problem_cluster_lineage_run_identity",
        ),
    )
    op.create_table(
        "problem_cluster_lineage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lineage_run_id", sa.Uuid(), nullable=False),
        sa.Column("previous_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("current_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("relation_type", sa.String(length=30), nullable=False),
        sa.Column(
            "member_jaccard",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "signature_jaccard",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["current_cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_lineage_current_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["lineage_run_id"],
            ["problem_cluster_lineage_runs.id"],
            name=op.f(
                "fk_problem_cluster_lineage_lineage_run_id_problem_cluster_lineage_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["previous_cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_lineage_previous_cluster_id_problem_clusters"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_lineage"),
        ),
        sa.UniqueConstraint(
            "lineage_run_id",
            "previous_cluster_id",
            "current_cluster_id",
            name="problem_cluster_lineage_pair",
        ),
    )
    op.create_index(
        "ix_problem_cluster_lineage_run_relation",
        "problem_cluster_lineage",
        ["lineage_run_id", "relation_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_cluster_lineage_run_relation",
        table_name="problem_cluster_lineage",
    )
    op.drop_table("problem_cluster_lineage")
    op.drop_table("problem_cluster_lineage_runs")
