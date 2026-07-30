"""add scheduler and audit events

Revision ID: e1b4c7d9a568
Revises: d0a3b6c8f457
Create Date: 2026-07-30 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1b4c7d9a568"
down_revision: str | None = "d0a3b6c8f457"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consecutive_failure_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_jobs")),
        sa.UniqueConstraint("key", name="scheduled_job_key"),
    )
    op.create_index(
        "ix_scheduled_job_due",
        "scheduled_jobs",
        ["status", "next_run_at"],
    )

    op.create_table(
        "scheduled_job_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_job_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error_class", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["scheduled_job_id"],
            ["scheduled_jobs.id"],
            name=op.f(
                "fk_scheduled_job_runs_scheduled_job_id_scheduled_jobs"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_job_runs")),
    )
    op.create_index(
        "ix_scheduled_job_run_job_started",
        "scheduled_job_runs",
        ["scheduled_job_id", "started_at"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_event_occurred",
        "audit_events",
        ["occurred_at"],
    )
    op.create_index(
        "ix_audit_event_request",
        "audit_events",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_event_request", table_name="audit_events")
    op.drop_index("ix_audit_event_occurred", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(
        "ix_scheduled_job_run_job_started",
        table_name="scheduled_job_runs",
    )
    op.drop_table("scheduled_job_runs")
    op.drop_index("ix_scheduled_job_due", table_name="scheduled_jobs")
    op.drop_table("scheduled_jobs")
