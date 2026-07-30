"""add research and controlled exports

Revision ID: b8e1f4a6d235
Revises: a7d9e1b3c524
Create Date: 2026-07-30 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e1f4a6d235"
down_revision: str | None = "a7d9e1b3c524"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("research_tier", sa.String(length=30), nullable=False),
        sa.Column("focus_questions", sa.JSON(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_research_runs_opportunity_version_id_opportunity_versions"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_research_runs"),
        ),
        sa.UniqueConstraint(
            "opportunity_version_id",
            "input_fingerprint",
            name="opportunity_research_version_input",
        ),
    )
    op.create_index(
        "ix_opportunity_research_version_started",
        "opportunity_research_runs",
        ["opportunity_version_id", "started_at"],
    )

    op.create_table(
        "opportunity_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("destination", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_reference", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_exports_opportunity_version_id_opportunity_versions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["opportunity_research_runs.id"],
            name=op.f(
                "fk_opportunity_exports_research_run_id_opportunity_research_runs"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opportunity_exports")),
        sa.UniqueConstraint(
            "destination",
            "idempotency_key",
            name="opportunity_export_destination_key",
        ),
    )
    op.create_index(
        "ix_opportunity_export_version_created",
        "opportunity_exports",
        ["opportunity_version_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_export_version_created",
        table_name="opportunity_exports",
    )
    op.drop_table("opportunity_exports")
    op.drop_index(
        "ix_opportunity_research_version_started",
        table_name="opportunity_research_runs",
    )
    op.drop_table("opportunity_research_runs")
