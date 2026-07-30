"""add versioned problem candidate clusters

Revision ID: c8a4e1f6b239
Revises: 7d2f8a5c1e90
Create Date: 2026-07-30 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8a4e1f6b239"
down_revision: str | Sequence[str] | None = "7d2f8a5c1e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_clustering_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("algorithm_key", sa.String(length=80), nullable=False),
        sa.Column("algorithm_version", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("cluster_count", sa.Integer(), nullable=False),
        sa.Column("singleton_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_clustering_runs")),
        sa.UniqueConstraint(
            "algorithm_key",
            "algorithm_version",
            "input_fingerprint",
            name="problem_clustering_input_version",
        ),
    )
    op.create_table(
        "problem_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.JSON(), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("representative_evidence_id", sa.Uuid(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("cohesion_min", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("cohesion_mean", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column(
            "first_source_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_source_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["representative_evidence_id"],
            ["problem_evidence.id"],
            name=op.f(
                "fk_problem_clusters_representative_evidence_id_problem_evidence"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["problem_clustering_runs.id"],
            name=op.f("fk_problem_clusters_run_id_problem_clustering_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_clusters")),
        sa.UniqueConstraint(
            "run_id",
            "fingerprint",
            name="problem_cluster_run_fingerprint",
        ),
    )
    op.create_index(
        "ix_problem_cluster_status_spread",
        "problem_clusters",
        ["status", "entity_count", "document_count"],
        unique=False,
    )
    op.create_table(
        "problem_cluster_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "similarity_to_representative",
            sa.Numeric(precision=7, scale=6),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["problem_clusters.id"],
            name=op.f(
                "fk_problem_cluster_memberships_cluster_id_problem_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["normalized_documents.id"],
            name=op.f(
                "fk_problem_cluster_memberships_document_id_normalized_documents"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f(
                "fk_problem_cluster_memberships_entity_id_entities"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["problem_evidence.id"],
            name=op.f(
                "fk_problem_cluster_memberships_evidence_id_problem_evidence"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["problem_clustering_runs.id"],
            name=op.f(
                "fk_problem_cluster_memberships_run_id_problem_clustering_runs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f(
                "fk_problem_cluster_memberships_source_id_data_sources"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_problem_cluster_memberships"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "evidence_id",
            name="problem_cluster_run_evidence",
        ),
    )
    op.create_index(
        "ix_problem_cluster_membership_cluster_entity",
        "problem_cluster_memberships",
        ["cluster_id", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_cluster_membership_cluster_entity",
        table_name="problem_cluster_memberships",
    )
    op.drop_table("problem_cluster_memberships")
    op.drop_index(
        "ix_problem_cluster_status_spread",
        table_name="problem_clusters",
    )
    op.drop_table("problem_clusters")
    op.drop_table("problem_clustering_runs")
