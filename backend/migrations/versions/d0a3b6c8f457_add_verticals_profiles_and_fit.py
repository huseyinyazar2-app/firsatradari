"""add verticals profiles and fit

Revision ID: d0a3b6c8f457
Revises: c9f2a5b7e346
Create Date: 2026-07-30 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0a3b6c8f457"
down_revision: str | None = "c9f2a5b7e346"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vertical_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("selection_rationale", sa.Text(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vertical_definitions")),
        sa.UniqueConstraint(
            "key",
            "version",
            name="vertical_definition_version",
        ),
    )
    op.create_index(
        "ix_vertical_definition_current",
        "vertical_definitions",
        ["key", "is_current"],
    )

    op.create_table(
        "research_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vertical_definition_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("exclusions", sa.JSON(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["vertical_definition_id"],
            ["vertical_definitions.id"],
            name=op.f(
                "fk_research_profiles_vertical_definition_id_vertical_definitions"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_profiles")),
        sa.UniqueConstraint(
            "key",
            "version",
            name="research_profile_version",
        ),
    )
    op.create_index(
        "ix_research_profile_current",
        "research_profiles",
        ["key", "is_current"],
    )

    op.create_table(
        "opportunity_profile_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_version_id", sa.Uuid(), nullable=False),
        sa.Column("research_profile_id", sa.Uuid(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("observed_attributes", sa.JSON(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("blocker_codes", sa.JSON(), nullable=False),
        sa.Column("unknown_fields", sa.JSON(), nullable=False),
        sa.Column("fit_score", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column(
            "data_coverage",
            sa.Numeric(precision=7, scale=6),
            nullable=False,
        ),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("evaluated_by", sa.String(length=200), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_version_id"],
            ["opportunity_versions.id"],
            name=op.f(
                "fk_opportunity_profile_evaluations_opportunity_version_id_opportunity_versions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["research_profile_id"],
            ["research_profiles.id"],
            name=op.f(
                "fk_opportunity_profile_evaluations_research_profile_id_research_profiles"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_opportunity_profile_evaluations"),
        ),
        sa.UniqueConstraint(
            "opportunity_version_id",
            "research_profile_id",
            "input_fingerprint",
            name="opportunity_profile_evaluation_input",
        ),
    )
    op.create_index(
        "ix_opportunity_profile_version_evaluated",
        "opportunity_profile_evaluations",
        ["opportunity_version_id", "evaluated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_profile_version_evaluated",
        table_name="opportunity_profile_evaluations",
    )
    op.drop_table("opportunity_profile_evaluations")
    op.drop_index(
        "ix_research_profile_current",
        table_name="research_profiles",
    )
    op.drop_table("research_profiles")
    op.drop_index(
        "ix_vertical_definition_current",
        table_name="vertical_definitions",
    )
    op.drop_table("vertical_definitions")
