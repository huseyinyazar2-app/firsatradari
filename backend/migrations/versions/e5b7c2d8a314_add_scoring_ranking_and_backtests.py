"""add scoring ranking and backtests

Revision ID: e5b7c2d8a314
Revises: d9a3f6b1c472
Create Date: 2026-07-31 03:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5b7c2d8a314"
down_revision: str | Sequence[str] | None = "d9a3f6b1c472"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("minimum_confidence", sa.Numeric(7, 6), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scoring_profiles")),
        sa.UniqueConstraint(
            "key",
            "version",
            name="scoring_profile_version",
        ),
    )
    op.create_table(
        "opportunity_score_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("opportunity_count", sa.Integer(), nullable=False),
        sa.Column("rankable_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["scoring_profiles.id"],
            name=op.f(
                "fk_opportunity_score_runs_profile_id_scoring_profiles"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_score_runs"),
        ),
        sa.UniqueConstraint(
            "profile_id",
            "as_of",
            "input_fingerprint",
            name="opportunity_score_run_identity",
        ),
    )
    op.create_table(
        "opportunity_score_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("potential_score", sa.Numeric(7, 6), nullable=False),
        sa.Column("actionability_score", sa.Numeric(7, 6), nullable=False),
        sa.Column("confidence_score", sa.Numeric(7, 6), nullable=False),
        sa.Column("uncertainty", sa.Numeric(7, 6), nullable=False),
        sa.Column("total_score", sa.Numeric(7, 6), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_score_snapshots_opportunity_version_id_"
                "opportunity_versions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["opportunity_score_runs.id"],
            name=op.f(
                "fk_opportunity_score_snapshots_run_id_"
                "opportunity_score_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_score_snapshots"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "opportunity_version_id",
            name="opportunity_score_run_version",
        ),
    )
    op.create_index(
        "ix_opportunity_score_status_total",
        "opportunity_score_snapshots",
        ["run_id", "status", "total_score"],
        unique=False,
    )
    op.create_table(
        "opportunity_ranking_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("score_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("ranked_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["score_run_id"],
            ["opportunity_score_runs.id"],
            name=op.f(
                "fk_opportunity_ranking_runs_score_run_id_"
                "opportunity_score_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_ranking_runs"),
        ),
        sa.UniqueConstraint(
            "score_run_id",
            name=op.f("uq_opportunity_ranking_runs_score_run_id"),
        ),
    )
    op.create_table(
        "opportunity_ranking_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ranking_run_id", sa.Uuid(), nullable=False),
        sa.Column("score_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ranking_run_id"],
            ["opportunity_ranking_runs.id"],
            name=op.f(
                "fk_opportunity_ranking_entries_ranking_run_id_"
                "opportunity_ranking_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["score_snapshot_id"],
            ["opportunity_score_snapshots.id"],
            name=op.f(
                "fk_opportunity_ranking_entries_score_snapshot_id_"
                "opportunity_score_snapshots"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_ranking_entries"),
        ),
        sa.UniqueConstraint(
            "ranking_run_id",
            "rank",
            name="opportunity_ranking_position",
        ),
        sa.UniqueConstraint(
            "ranking_run_id",
            "score_snapshot_id",
            name="opportunity_ranking_snapshot",
        ),
    )
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("score_run_id", sa.Uuid(), nullable=False),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome_window_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prediction_count", sa.Integer(), nullable=False),
        sa.Column("evaluated_count", sa.Integer(), nullable=False),
        sa.Column("positive_count", sa.Integer(), nullable=False),
        sa.Column("brier_score", sa.Numeric(7, 6), nullable=True),
        sa.Column(
            "baseline_brier_score",
            sa.Numeric(7, 6),
            nullable=True,
        ),
        sa.Column("improvement", sa.Numeric(7, 6), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["score_run_id"],
            ["opportunity_score_runs.id"],
            name=op.f("fk_backtest_runs_score_run_id_opportunity_score_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_runs")),
        sa.UniqueConstraint(
            "score_run_id",
            "outcome_window_days",
            name="backtest_score_window",
        ),
    )
    op.create_table(
        "backtest_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("backtest_run_id", sa.Uuid(), nullable=False),
        sa.Column("score_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column(
            "predicted_probability",
            sa.Numeric(7, 6),
            nullable=True,
        ),
        sa.Column("outcome_observed", sa.Boolean(), nullable=True),
        sa.Column("outcome_count", sa.Integer(), nullable=False),
        sa.Column("evaluation_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["backtest_run_id"],
            ["backtest_runs.id"],
            name=op.f(
                "fk_backtest_predictions_backtest_run_id_backtest_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["score_snapshot_id"],
            ["opportunity_score_snapshots.id"],
            name=op.f(
                "fk_backtest_predictions_score_snapshot_id_"
                "opportunity_score_snapshots"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_backtest_predictions"),
        ),
        sa.UniqueConstraint(
            "backtest_run_id",
            "score_snapshot_id",
            name="backtest_run_score_snapshot",
        ),
    )


def downgrade() -> None:
    op.drop_table("backtest_predictions")
    op.drop_table("backtest_runs")
    op.drop_table("opportunity_ranking_entries")
    op.drop_table("opportunity_ranking_runs")
    op.drop_index(
        "ix_opportunity_score_status_total",
        table_name="opportunity_score_snapshots",
    )
    op.drop_table("opportunity_score_snapshots")
    op.drop_table("opportunity_score_runs")
    op.drop_table("scoring_profiles")
