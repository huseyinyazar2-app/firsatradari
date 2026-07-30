"""add source independence governance

Revision ID: f6c2a8d4b193
Revises: e3b9d7a2c541
Create Date: 2026-07-30 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6c2a8d4b193"
down_revision: str | Sequence[str] | None = "e3b9d7a2c541"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column_name, length in (
        ("evidence_family_key", 80),
        ("independence_group_key", 80),
        ("independence_status", 30),
    ):
        op.add_column(
            "data_sources",
            sa.Column(
                column_name,
                sa.String(length=length),
                nullable=False,
                server_default="unknown",
            ),
        )
    op.execute(
        sa.text(
            """
            UPDATE data_sources
            SET
                evidence_family_key = 'developer_repository_activity',
                independence_group_key = 'github',
                independence_status = 'conditional'
            WHERE key = 'github'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE data_sources
            SET
                evidence_family_key = 'package_distribution',
                independence_group_key = 'npm',
                independence_status = 'conditional'
            WHERE key = 'npm'
            """
        )
    )
    for column_name in (
        "evidence_family_key",
        "independence_group_key",
        "independence_status",
    ):
        op.alter_column(
            "data_sources",
            column_name,
            server_default=None,
        )
    op.create_table(
        "source_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("related_source_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("independence_effect", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["related_source_id"],
            ["data_sources.id"],
            name=op.f(
                "fk_source_relationships_related_source_id_data_sources"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_source_relationships_source_id_data_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_relationships")),
        sa.UniqueConstraint(
            "source_id",
            "related_source_id",
            "relationship_type",
            "scope",
            name="source_relationship_identity",
        ),
    )
    op.create_index(
        "ix_source_relationship_sources_status",
        "source_relationships",
        ["source_id", "related_source_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_relationship_sources_status",
        table_name="source_relationships",
    )
    op.drop_table("source_relationships")
    op.drop_column("data_sources", "independence_status")
    op.drop_column("data_sources", "independence_group_key")
    op.drop_column("data_sources", "evidence_family_key")
