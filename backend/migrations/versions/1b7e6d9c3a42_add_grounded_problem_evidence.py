"""add grounded problem evidence

Revision ID: 1b7e6d9c3a42
Revises: f4c9a1d2b807
Create Date: 2026-07-30 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1b7e6d9c3a42"
down_revision: str | Sequence[str] | None = "f4c9a1d2b807"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problem_extraction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("extractor_key", sa.String(length=80), nullable=False),
        sa.Column("extractor_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_problem_extraction_runs_source_id_data_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_extraction_runs")),
    )
    op.create_table(
        "problem_extraction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extractor_key", sa.String(length=80), nullable=False),
        sa.Column("extractor_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(length=80), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["normalized_documents.id"],
            name=op.f(
                "fk_problem_extraction_records_document_id_normalized_documents"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["problem_extraction_runs.id"],
            name=op.f(
                "fk_problem_extraction_records_run_id_problem_extraction_runs"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_extraction_records")),
        sa.UniqueConstraint(
            "document_id",
            "extractor_key",
            "extractor_version",
            name="problem_extraction_document_version",
        ),
    )
    op.create_table(
        "problem_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_record_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("source_field", sa.String(length=40), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["normalized_documents.id"],
            name=op.f("fk_problem_evidence_document_id_normalized_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_problem_evidence_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["extraction_record_id"],
            ["problem_extraction_records.id"],
            name=op.f(
                "fk_problem_evidence_extraction_record_id_problem_extraction_records"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_evidence")),
        sa.UniqueConstraint(
            "extraction_record_id",
            "evidence_hash",
            name="problem_evidence_record_hash",
        ),
    )
    op.create_index(
        "ix_problem_evidence_entity_type_created",
        "problem_evidence",
        ["entity_id", "evidence_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_problem_evidence_entity_type_created",
        table_name="problem_evidence",
    )
    op.drop_table("problem_evidence")
    op.drop_table("problem_extraction_records")
    op.drop_table("problem_extraction_runs")
