"""add problem cluster quality gate

Revision ID: 2c7f1a9e5d83
Revises: 0a5d9e7c2b64
Create Date: 2026-07-31 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c7f1a9e5d83"
down_revision: str | Sequence[str] | None = "0a5d9e7c2b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_cluster_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_audit_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("verdict", sa.String(length=30), nullable=False),
        sa.Column("sample_method", sa.String(length=50), nullable=False),
        sa.Column("sampled_member_count", sa.Integer(), nullable=False),
        sa.Column("coherent_member_count", sa.Integer(), nullable=False),
        sa.Column("purity", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_audits_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_audits_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_audit_id"],
            ["problem_cluster_audits.id"],
            name=op.f(
                "fk_problem_cluster_audits_supersedes_audit_id_problem_cluster_audits"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_audits"),
        ),
    )
    op.create_index(
        "ix_problem_cluster_audit_cluster_created",
        "problem_cluster_audits",
        ["cluster_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "problem_clustering_quality_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clustering_run_id", sa.Uuid(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("eligible_cluster_count", sa.Integer(), nullable=False),
        sa.Column("audited_cluster_count", sa.Integer(), nullable=False),
        sa.Column("coherent_cluster_count", sa.Integer(), nullable=False),
        sa.Column("sampled_member_count", sa.Integer(), nullable=False),
        sa.Column("coherent_member_count", sa.Integer(), nullable=False),
        sa.Column(
            "audit_coverage",
            sa.Numeric(precision=7, scale=6),
            nullable=False,
        ),
        sa.Column(
            "cluster_coherence_rate",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "member_purity",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "purity_confidence_lower",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "purity_confidence_upper",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column("passes_quality_gate", sa.Boolean(), nullable=False),
        sa.Column("calculation", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_clustering_quality_snapshots_clustering_run_id_problem_clustering_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_clustering_quality_snapshots"),
        ),
        sa.UniqueConstraint(
            "clustering_run_id",
            "input_fingerprint",
            name="problem_clustering_quality_input",
        ),
    )
    op.create_index(
        "ix_problem_clustering_quality_run_calculated",
        "problem_clustering_quality_snapshots",
        ["clustering_run_id", "calculated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_clustering_quality_run_calculated",
        table_name="problem_clustering_quality_snapshots",
    )
    op.drop_table("problem_clustering_quality_snapshots")
    op.drop_index(
        "ix_problem_cluster_audit_cluster_created",
        table_name="problem_cluster_audits",
    )
    op.drop_table("problem_cluster_audits")
