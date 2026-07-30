"""add problem cluster metric observations

Revision ID: e3b9d7a2c541
Revises: c8a4e1f6b239
Create Date: 2026-07-30 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3b9d7a2c541"
down_revision: str | Sequence[str] | None = "c8a4e1f6b239"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_cluster_metric_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("definition_set_version", sa.String(length=40), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cluster_count", sa.Integer(), nullable=False),
        sa.Column("metric_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_metric_runs_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_metric_runs"),
        ),
        sa.UniqueConstraint(
            "clustering_run_id",
            "definition_set_version",
            name="problem_cluster_metric_run_version",
        ),
    )
    op.create_table(
        "problem_cluster_metric_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("numerator", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("denominator", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "confidence_lower",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column(
            "confidence_upper",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column("calculation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_metric_observations_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["metric_definition_id"],
            ["metric_definitions.id"],
            name=op.f(
                "fk_problem_cluster_metric_observations_metric_definition_id_metric_definitions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["problem_cluster_metric_runs.id"],
            name=op.f(
                "fk_problem_cluster_metric_observations_run_id_problem_cluster_metric_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_metric_observations"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "metric_definition_id",
            "cluster_id",
            name="problem_cluster_metric_observation_identity",
        ),
    )
    op.create_index(
        "ix_problem_cluster_metric_cluster_definition_asof",
        "problem_cluster_metric_observations",
        ["cluster_id", "metric_definition_id", "as_of"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_cluster_metric_cluster_definition_asof",
        table_name="problem_cluster_metric_observations",
    )
    op.drop_table("problem_cluster_metric_observations")
    op.drop_table("problem_cluster_metric_runs")
