"""expand validation protocol controls

Revision ID: c9f2a5b7e346
Revises: b8e1f4a6d235
Create Date: 2026-07-30 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9f2a5b7e346"
down_revision: str | None = "b8e1f4a6d235"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "commercial_validation_experiments",
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "commercial_validation_experiments",
        sa.Column(
            "protocol_key",
            sa.String(length=80),
            server_default="default-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "commercial_validation_experiments",
        sa.Column(
            "cohort",
            sa.String(length=30),
            server_default="radar",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f(
            "fk_commercial_validation_experiments_opportunity_version_id_opportunity_versions"
        ),
        "commercial_validation_experiments",
        "opportunity_versions",
        ["opportunity_version_id"],
        ["id"],
    )
    op.alter_column(
        "commercial_validation_experiments",
        "protocol_key",
        server_default=None,
    )
    op.alter_column(
        "commercial_validation_experiments",
        "cohort",
        server_default=None,
    )

    op.create_table(
        "commercial_contact_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_key_hash", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_reference", sa.String(length=800), nullable=True),
        sa.Column("recorded_by", sa.String(length=200), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_commercial_contact_preferences"),
        ),
    )
    op.create_index(
        "ix_commercial_contact_participant_scope",
        "commercial_contact_preferences",
        ["participant_key_hash", "channel", "scope"],
    )
    op.create_index(
        "ix_commercial_contact_status_recorded",
        "commercial_contact_preferences",
        ["status", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_contact_status_recorded",
        table_name="commercial_contact_preferences",
    )
    op.drop_index(
        "ix_commercial_contact_participant_scope",
        table_name="commercial_contact_preferences",
    )
    op.drop_table("commercial_contact_preferences")
    op.drop_constraint(
        op.f(
            "fk_commercial_validation_experiments_opportunity_version_id_opportunity_versions"
        ),
        "commercial_validation_experiments",
        type_="foreignkey",
    )
    op.drop_column("commercial_validation_experiments", "cohort")
    op.drop_column("commercial_validation_experiments", "protocol_key")
    op.drop_column(
        "commercial_validation_experiments",
        "opportunity_version_id",
    )
