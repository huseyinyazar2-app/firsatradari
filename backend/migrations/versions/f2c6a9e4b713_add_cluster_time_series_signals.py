"""add cluster time series signals

Revision ID: f2c6a9e4b713
Revises: e5b7c2d8a314
Create Date: 2026-07-31 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2c6a9e4b713"
down_revision: str | Sequence[str] | None = "e5b7c2d8a314"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_cluster_signal_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("cluster_count", sa.Integer(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_signal_runs_clustering_run_id_"
                "problem_clustering_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_signal_runs"),
        ),
        sa.UniqueConstraint(
            "clustering_run_id",
            "algorithm_version",
            "input_fingerprint",
            name="problem_cluster_signal_run_version",
        ),
    )
    op.create_table(
        "problem_cluster_signal_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("point_count", sa.Integer(), nullable=False),
        sa.Column("first_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slope_per_day", sa.Numeric(18, 9), nullable=True),
        sa.Column("relative_change_30d", sa.Numeric(18, 6), nullable=True),
        sa.Column("trend_direction", sa.String(length=20), nullable=True),
        sa.Column("anomaly_score", sa.Numeric(18, 6), nullable=True),
        sa.Column("anomaly_status", sa.String(length=40), nullable=False),
        sa.Column("seasonality_period_days", sa.Integer(), nullable=True),
        sa.Column(
            "seasonality_strength",
            sa.Numeric(18, 6),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("calculation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_signal_observations_cluster_id_"
                "problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["metric_definition_id"],
            ["metric_definitions.id"],
            name=op.f(
                "fk_problem_cluster_signal_observations_"
                "metric_definition_id_metric_definitions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["problem_cluster_signal_runs.id"],
            name=op.f(
                "fk_problem_cluster_signal_observations_run_id_"
                "problem_cluster_signal_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_signal_observations"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "cluster_id",
            "metric_definition_id",
            name="problem_cluster_signal_identity",
        ),
    )
    op.create_index(
        "ix_problem_cluster_signal_status",
        "problem_cluster_signal_observations",
        ["run_id", "status", "trend_direction"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_cluster_signal_status",
        table_name="problem_cluster_signal_observations",
    )
    op.drop_table("problem_cluster_signal_observations")
    op.drop_table("problem_cluster_signal_runs")
