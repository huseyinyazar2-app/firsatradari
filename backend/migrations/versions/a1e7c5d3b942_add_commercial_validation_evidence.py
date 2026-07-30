"""add commercial validation evidence

Revision ID: a1e7c5d3b942
Revises: 9d2f6a4c1b80
Create Date: 2026-07-31 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1e7c5d3b942"
down_revision: str | Sequence[str] | None = "9d2f6a4c1b80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "problem_cluster_metric_runs",
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE problem_cluster_metric_runs "
        "SET input_fingerprint = 'legacy-' || CAST(id AS VARCHAR)"
    )
    op.alter_column(
        "problem_cluster_metric_runs",
        "input_fingerprint",
        nullable=False,
    )
    op.drop_constraint(
        "problem_cluster_metric_run_version",
        "problem_cluster_metric_runs",
        type_="unique",
    )
    op.create_unique_constraint(
        "problem_cluster_metric_run_version",
        "problem_cluster_metric_runs",
        [
            "clustering_run_id",
            "definition_set_version",
            "input_fingerprint",
        ],
    )
    op.create_table(
        "commercial_validation_experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=80), nullable=False),
        sa.Column("experiment_type", sa.String(length=40), nullable=False),
        sa.Column("target_segment", sa.Text(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_commercial_validation_experiments_cluster_id_problem_clusters"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_commercial_validation_experiments"),
        ),
        sa.UniqueConstraint(
            "cluster_id",
            "external_key",
            name="commercial_experiment_cluster_external_key",
        ),
    )
    op.create_index(
        "ix_commercial_experiment_cluster_status",
        "commercial_validation_experiments",
        ["cluster_id", "status"],
        unique=False,
    )
    op.create_table(
        "commercial_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("participant_key_hash", sa.String(length=64), nullable=False),
        sa.Column("outcome_type", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column(
            "evidence_reference",
            sa.String(length=800),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verifier", sa.String(length=200), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["commercial_validation_experiments.id"],
            name=op.f(
                "fk_commercial_outcomes_experiment_id_commercial_validation_experiments"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_commercial_outcomes"),
        ),
        sa.UniqueConstraint(
            "experiment_id",
            "idempotency_key",
            name="commercial_outcome_experiment_idempotency",
        ),
    )
    op.create_index(
        "ix_commercial_outcome_experiment_verification",
        "commercial_outcomes",
        ["experiment_id", "verification_status"],
        unique=False,
    )
    op.create_table(
        "commercial_outcome_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["commercial_outcomes.id"],
            name=op.f(
                "fk_commercial_outcome_reviews_outcome_id_commercial_outcomes"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_commercial_outcome_reviews"),
        ),
    )
    op.create_index(
        "ix_commercial_outcome_review_outcome_time",
        "commercial_outcome_reviews",
        ["outcome_id", "reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_outcome_review_outcome_time",
        table_name="commercial_outcome_reviews",
    )
    op.drop_table("commercial_outcome_reviews")
    op.drop_index(
        "ix_commercial_outcome_experiment_verification",
        table_name="commercial_outcomes",
    )
    op.drop_table("commercial_outcomes")
    op.drop_index(
        "ix_commercial_experiment_cluster_status",
        table_name="commercial_validation_experiments",
    )
    op.drop_table("commercial_validation_experiments")
    op.drop_constraint(
        "problem_cluster_metric_run_version",
        "problem_cluster_metric_runs",
        type_="unique",
    )
    op.create_unique_constraint(
        "problem_cluster_metric_run_version",
        "problem_cluster_metric_runs",
        ["clustering_run_id", "definition_set_version"],
    )
    op.drop_column(
        "problem_cluster_metric_runs",
        "input_fingerprint",
    )
