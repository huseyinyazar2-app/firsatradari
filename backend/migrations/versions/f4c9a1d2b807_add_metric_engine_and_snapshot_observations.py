"""add metric engine and snapshot observations

Revision ID: f4c9a1d2b807
Revises: e926f2f86872
Create Date: 2026-07-30 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c9a1d2b807"
down_revision: str | Sequence[str] | None = "e926f2f86872"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("numerator_description", sa.Text(), nullable=True),
        sa.Column("denominator_description", sa.Text(), nullable=True),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=True),
        sa.Column("comparison_group_description", sa.Text(), nullable=False),
        sa.Column("freshness_policy", sa.String(length=200), nullable=False),
        sa.Column("confidence_method", sa.String(length=80), nullable=False),
        sa.Column("missing_data_policy", sa.String(length=80), nullable=False),
        sa.Column("outlier_policy", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_definitions")),
        sa.UniqueConstraint("key", "version", name="metric_definition_version"),
    )
    op.create_table(
        "signal_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_definitions")),
        sa.UniqueConstraint("key", "version", name="signal_definition_version"),
    )
    op.create_table(
        "raw_snapshot_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["ingestion_collections.id"],
            name=op.f(
                "fk_raw_snapshot_observations_collection_id_ingestion_collections"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_raw_snapshot_observations_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f("fk_raw_snapshot_observations_snapshot_id_raw_snapshots"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_raw_snapshot_observations_source_id_data_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_snapshot_observations")),
        sa.UniqueConstraint(
            "collection_id",
            "snapshot_id",
            name="collection_snapshot_observation",
        ),
    )
    op.create_index(
        "ix_snapshot_observation_source_observed",
        "raw_snapshot_observations",
        ["source_id", "observed_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            INSERT INTO raw_snapshot_observations (
                id,
                snapshot_id,
                source_id,
                run_id,
                collection_id,
                observed_at,
                is_duplicate
            )
            SELECT
                id,
                id,
                source_id,
                run_id,
                collection_id,
                observed_at,
                false
            FROM raw_snapshots
            WHERE run_id IS NOT NULL AND collection_id IS NOT NULL
            """
        )
    )
    op.create_table(
        "metric_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("definition_set_version", sa.String(length=40), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_document_count", sa.Integer(), nullable=False),
        sa.Column("metric_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["ingestion_collections.id"],
            name=op.f("fk_metric_runs_collection_id_ingestion_collections"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_runs")),
        sa.UniqueConstraint(
            "collection_id",
            "definition_set_version",
            "as_of",
            name="metric_run_identity",
        ),
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("numerator", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("denominator", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "confidence_lower",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column(
            "confidence_upper",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column("calculation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["ingestion_collections.id"],
            name=op.f(
                "fk_metric_observations_collection_id_ingestion_collections"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_metric_observations_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["metric_definition_id"],
            ["metric_definitions.id"],
            name=op.f(
                "fk_metric_observations_metric_definition_id_metric_definitions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["metric_runs.id"],
            name=op.f("fk_metric_observations_run_id_metric_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_observations")),
        sa.UniqueConstraint(
            "run_id",
            "metric_definition_id",
            "entity_id",
            name="metric_observation_identity",
        ),
    )
    op.create_index(
        "ix_metric_observation_entity_definition_asof",
        "metric_observations",
        ["entity_id", "metric_definition_id", "as_of"],
        unique=False,
    )
    op.create_table(
        "signal_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("signal_definition_id", sa.Uuid(), nullable=False),
        sa.Column("metric_observation_id", sa.Uuid(), nullable=False),
        sa.Column("baseline_observation_id", sa.Uuid(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "absolute_change",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column(
            "relative_change",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
        ),
        sa.Column("direction", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["baseline_observation_id"],
            ["metric_observations.id"],
            name=op.f(
                "fk_signal_values_baseline_observation_id_metric_observations"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_signal_values_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["metric_observation_id"],
            ["metric_observations.id"],
            name=op.f(
                "fk_signal_values_metric_observation_id_metric_observations"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["signal_definition_id"],
            ["signal_definitions.id"],
            name=op.f(
                "fk_signal_values_signal_definition_id_signal_definitions"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_values")),
        sa.UniqueConstraint(
            "metric_observation_id",
            "signal_definition_id",
            name="metric_signal_value",
        ),
    )
    op.create_index(
        "ix_signal_value_entity_asof",
        "signal_values",
        ["entity_id", "as_of"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_signal_value_entity_asof", table_name="signal_values")
    op.drop_table("signal_values")
    op.drop_index(
        "ix_metric_observation_entity_definition_asof",
        table_name="metric_observations",
    )
    op.drop_table("metric_observations")
    op.drop_table("metric_runs")
    op.drop_index(
        "ix_snapshot_observation_source_observed",
        table_name="raw_snapshot_observations",
    )
    op.drop_table("raw_snapshot_observations")
    op.drop_table("signal_definitions")
    op.drop_table("metric_definitions")
