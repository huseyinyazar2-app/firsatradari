"""bind scores to research profiles

Revision ID: f3c5d8e0b679
Revises: e1b4c7d9a568
Create Date: 2026-07-30 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3c5d8e0b679"
down_revision: str | None = "e1b4c7d9a568"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunity_score_runs",
        sa.Column("research_profile_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f(
            "fk_opportunity_score_runs_research_profile_id_research_profiles"
        ),
        "opportunity_score_runs",
        "research_profiles",
        ["research_profile_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f(
            "fk_opportunity_score_runs_research_profile_id_research_profiles"
        ),
        "opportunity_score_runs",
        type_="foreignkey",
    )
    op.drop_column("opportunity_score_runs", "research_profile_id")
