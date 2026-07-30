from firsat_radari.db import models  # noqa: F401
from firsat_radari.db.base import Base


def test_initial_tables_are_registered() -> None:
    expected = {
        "data_sources",
        "source_policies",
        "ingestion_collections",
        "ingestion_runs",
        "ingestion_checkpoints",
        "collection_pages",
        "request_records",
        "raw_snapshots",
        "data_quality_events",
        "source_schema_profiles",
        "normalization_runs",
        "normalized_documents",
        "entities",
        "entity_external_ids",
        "repositories",
        "repository_observations",
        "repository_work_items",
        "packages",
        "package_versions",
    }

    assert expected <= set(Base.metadata.tables)
