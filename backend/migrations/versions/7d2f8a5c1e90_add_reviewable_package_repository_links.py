"""add reviewable package repository links

Revision ID: 7d2f8a5c1e90
Revises: 1b7e6d9c3a42
Create Date: 2026-07-30 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d2f8a5c1e90"
down_revision: str | Sequence[str] | None = "1b7e6d9c3a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "packages",
        sa.Column("repository_directory", sa.String(length=500), nullable=True),
    )
    op.create_table(
        "package_repository_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=True),
        sa.Column("repository_full_name", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=800), nullable=False),
        sa.Column("repository_directory", sa.String(length=500), nullable=True),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer", sa.String(length=200), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_package_repository_links_package_id_packages"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f(
                "fk_package_repository_links_repository_id_repositories"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_package_repository_links")),
        sa.UniqueConstraint(
            "package_id",
            "repository_full_name",
            name="package_repository_link_target",
        ),
    )
    op.create_index(
        "ix_package_repository_link_status_target",
        "package_repository_links",
        ["status", "repository_full_name"],
        unique=False,
    )
    op.create_table(
        "package_repository_link_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("link_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["link_id"],
            ["package_repository_links.id"],
            name=op.f(
                "fk_package_repository_link_reviews_link_id_package_repository_links"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_package_repository_link_reviews"),
        ),
    )
    op.create_index(
        "ix_package_repository_link_review_link_time",
        "package_repository_link_reviews",
        ["link_id", "reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_package_repository_link_review_link_time",
        table_name="package_repository_link_reviews",
    )
    op.drop_table("package_repository_link_reviews")
    op.drop_index(
        "ix_package_repository_link_status_target",
        table_name="package_repository_links",
    )
    op.drop_table("package_repository_links")
    op.drop_column("packages", "repository_directory")
