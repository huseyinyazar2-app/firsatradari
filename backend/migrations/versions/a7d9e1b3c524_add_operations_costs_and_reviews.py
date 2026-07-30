"""add operations costs and reviews

Revision ID: a7d9e1b3c524
Revises: f2c6a9e4b713
Create Date: 2026-07-30 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7d9e1b3c524"
down_revision: str | None = "f2c6a9e4b713"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cost_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=120), nullable=False),
        sa.Column("operation_type", sa.String(length=60), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("experiment_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("units", sa.Numeric(precision=16, scale=4), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["commercial_validation_experiments.id"],
            name=op.f(
                "fk_cost_entries_experiment_id_commercial_validation_experiments"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name=op.f("fk_cost_entries_opportunity_id_opportunities"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_cost_entries_source_id_data_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_entries")),
        sa.UniqueConstraint(
            "external_key",
            name="cost_entry_external_key",
        ),
    )
    op.create_index(
        "ix_cost_entry_occurred_currency",
        "cost_entries",
        ["occurred_at", "currency"],
    )
    op.create_index(
        "ix_cost_entry_opportunity_occurred",
        "cost_entries",
        ["opportunity_id", "occurred_at"],
    )
    op.create_index(
        "ix_cost_entry_source_occurred",
        "cost_entries",
        ["source_id", "occurred_at"],
    )

    op.create_table(
        "operational_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_key", sa.String(length=180), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_operational_alerts_source_id_data_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operational_alerts")),
        sa.UniqueConstraint("alert_key", name="operational_alert_key"),
    )
    op.create_index(
        "ix_operational_alert_source_status",
        "operational_alerts",
        ["source_id", "status"],
    )
    op.create_index(
        "ix_operational_alert_status_severity",
        "operational_alerts",
        ["status", "severity"],
    )

    op.create_table(
        "opportunity_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_reviews_opportunity_version_id_opportunity_versions"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opportunity_reviews")),
    )
    op.create_index(
        "ix_opportunity_review_version_created",
        "opportunity_reviews",
        ["opportunity_version_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_review_version_created",
        table_name="opportunity_reviews",
    )
    op.drop_table("opportunity_reviews")
    op.drop_index(
        "ix_operational_alert_status_severity",
        table_name="operational_alerts",
    )
    op.drop_index(
        "ix_operational_alert_source_status",
        table_name="operational_alerts",
    )
    op.drop_table("operational_alerts")
    op.drop_index(
        "ix_cost_entry_source_occurred",
        table_name="cost_entries",
    )
    op.drop_index(
        "ix_cost_entry_opportunity_occurred",
        table_name="cost_entries",
    )
    op.drop_index(
        "ix_cost_entry_occurred_currency",
        table_name="cost_entries",
    )
    op.drop_table("cost_entries")
