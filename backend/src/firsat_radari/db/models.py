import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from firsat_radari.db.base import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(80), unique=True)
    source_type: Mapped[str] = mapped_column(String(50))
    evidence_family_key: Mapped[str] = mapped_column(
        String(80),
        default="unknown",
    )
    independence_group_key: Mapped[str] = mapped_column(
        String(80),
        default="unknown",
    )
    independence_status: Mapped[str] = mapped_column(
        String(30),
        default="unknown",
    )
    owner: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    policy_status: Mapped[str] = mapped_column(String(30), default="candidate")
    policy_version: Mapped[str | None] = mapped_column(String(80))
    commercial_use_status: Mapped[str] = mapped_column(String(30), default="unknown")
    storage_permission: Mapped[str] = mapped_column(String(30), default="unknown")
    derived_data_permission: Mapped[str] = mapped_column(String(30), default="unknown")
    llm_processing_permission: Mapped[str] = mapped_column(String(30), default="unknown")
    retention_days: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class SourceRelationship(Base):
    __tablename__ = "source_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "related_source_id",
            "relationship_type",
            "scope",
            name="source_relationship_identity",
        ),
        Index(
            "ix_source_relationship_sources_status",
            "source_id",
            "related_source_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    related_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id")
    )
    relationship_type: Mapped[str] = mapped_column(String(50))
    scope: Mapped[str] = mapped_column(String(50))
    independence_effect: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewer: Mapped[str] = mapped_column(String(200))


class SourcePolicy(Base):
    __tablename__ = "source_policies"
    __table_args__ = (UniqueConstraint("source_id", "version", name="source_policy_version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewer: Mapped[str] = mapped_column(String(200))
    commercial_use_status: Mapped[str] = mapped_column(String(30))
    storage_permission: Mapped[str] = mapped_column(String(30))
    derived_data_permission: Mapped[str] = mapped_column(String(30))
    llm_processing_permission: Mapped[str] = mapped_column(String(30))
    retention_days: Mapped[int | None] = mapped_column(Integer)
    terms_url: Mapped[str | None] = mapped_column(String(800))
    notes: Mapped[str | None] = mapped_column(Text)


class SourceIndependenceReview(Base):
    __tablename__ = "source_independence_reviews"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "version",
            name="source_independence_review_version",
        ),
        Index(
            "ix_source_independence_reviews_source_time",
            "source_id",
            "reviewed_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    version: Mapped[str] = mapped_column(String(80))
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(Text)
    evidence_references: Mapped[list[str]] = mapped_column(JSON)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IngestionCollection(Base):
    __tablename__ = "ingestion_collections"
    __table_args__ = (
        Index(
            "ix_collection_source_query_status",
            "source_id",
            "query_fingerprint",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    job_type: Mapped[str] = mapped_column(String(50))
    query_fingerprint: Mapped[str] = mapped_column(String(64))
    query_definition: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_total: Mapped[int | None] = mapped_column(Integer)
    collected_total: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    resume_available: Mapped[bool] = mapped_column(Boolean, default=True)
    completeness_reason: Mapped[str | None] = mapped_column(String(80))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    collection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_collections.id"))
    connector_version: Mapped[str] = mapped_column(String(80))
    job_type: Mapped[str] = mapped_column(String(50))
    query_definition: Mapped[dict] = mapped_column(JSON)
    query_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    checkpoint_before: Mapped[dict | None] = mapped_column(JSON)
    checkpoint_after: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_item_count: Mapped[int] = mapped_column(Integer, default=0)
    normalized_item_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_item_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))


class IngestionCheckpoint(Base):
    __tablename__ = "ingestion_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "job_type",
            "query_fingerprint",
            name="ingestion_checkpoint_query",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_collections.id"))
    last_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    job_type: Mapped[str] = mapped_column(String(50))
    query_fingerprint: Mapped[str] = mapped_column(String(64))
    connector_version: Mapped[str] = mapped_column(String(80))
    checkpoint: Mapped[dict | None] = mapped_column(JSON)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    resume_available: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CollectionPage(Base):
    __tablename__ = "collection_pages"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "page_number",
            name="collection_page_number",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_collections.id"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    cursor_in: Mapped[dict | None] = mapped_column(JSON)
    cursor_out: Mapped[dict | None] = mapped_column(JSON)
    items_returned: Mapped[int] = mapped_column(Integer)
    is_last_page: Mapped[bool] = mapped_column(Boolean)
    is_complete: Mapped[bool] = mapped_column(Boolean)
    resume_available: Mapped[bool] = mapped_column(Boolean)
    completeness_reason: Mapped[str | None] = mapped_column(String(80))
    expected_total: Mapped[int | None] = mapped_column(Integer)
    collected_total: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RequestRecord(Base):
    __tablename__ = "request_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    endpoint_key: Mapped[str] = mapped_column(String(100))
    request_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(String(300))
    rate_limit_limit: Mapped[int | None] = mapped_column(Integer)
    rate_limit_remaining: Mapped[int | None] = mapped_column(Integer)
    rate_limit_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    error_class: Mapped[str | None] = mapped_column(String(50))


class RawSnapshot(Base):
    __tablename__ = "raw_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "external_type",
            "external_id",
            "content_hash",
            name="raw_identity",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    collection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_collections.id"))
    external_type: Mapped[str] = mapped_column(String(80))
    external_id: Mapped[str] = mapped_column(String(300))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64))
    object_storage_key: Mapped[str] = mapped_column(String(800))
    media_type: Mapped[str] = mapped_column(String(100), default="application/json")
    schema_hint: Mapped[str | None] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(80))
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    is_deleted_at_source: Mapped[bool] = mapped_column(Boolean, default=False)


class RawSnapshotObservation(Base):
    __tablename__ = "raw_snapshot_observations"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "snapshot_id",
            name="collection_snapshot_observation",
        ),
        Index(
            "ix_snapshot_observation_source_observed",
            "source_id",
            "observed_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_collections.id")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_duplicate: Mapped[bool] = mapped_column(Boolean)


class DataQualityEvent(Base):
    __tablename__ = "data_quality_events"
    __table_args__ = (
        Index("ix_quality_event_run_type", "run_id", "event_type"),
        Index("ix_quality_event_source_observed", "source_id", "observed_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("raw_snapshots.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))
    external_type: Mapped[str | None] = mapped_column(String(80))
    external_id: Mapped[str | None] = mapped_column(String(300))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceSchemaProfile(Base):
    __tablename__ = "source_schema_profiles"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "external_type",
            "fingerprint",
            name="source_schema_fingerprint",
        ),
        Index(
            "ix_schema_profile_source_type_seen",
            "source_id",
            "external_type",
            "last_seen_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    external_type: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(64))
    top_level_schema: Mapped[dict] = mapped_column(JSON)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(Integer, default=1)


class NormalizationRun(Base):
    __tablename__ = "normalization_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    normalizer_key: Mapped[str] = mapped_column(String(80))
    normalizer_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(50))
    canonical_name: Mapped[str] = mapped_column(String(300))
    canonical_url: Mapped[str | None] = mapped_column(String(800))
    status: Mapped[str] = mapped_column(String(30), default="active")


class NormalizedDocument(Base):
    __tablename__ = "normalized_documents"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "normalizer_key",
            "normalizer_version",
            name="normalized_snapshot_version",
        ),
        Index("ix_normalized_document_entity_type", "entity_id", "document_type"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    normalization_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalization_runs.id"))
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entities.id"))
    normalizer_key: Mapped[str] = mapped_column(String(80))
    normalizer_version: Mapped[str] = mapped_column(String(80))
    document_type: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(40))
    title: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(String(800))
    language: Mapped[str | None] = mapped_column(String(20))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    error_class: Mapped[str | None] = mapped_column(String(80))


class ProblemExtractionRun(Base):
    __tablename__ = "problem_extraction_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    extractor_key: Mapped[str] = mapped_column(String(80))
    extractor_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)


class ProblemExtractionRecord(Base):
    __tablename__ = "problem_extraction_records"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "extractor_key",
            "extractor_version",
            name="problem_extraction_document_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_extraction_runs.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_documents.id"))
    extractor_key: Mapped[str] = mapped_column(String(80))
    extractor_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    error_class: Mapped[str | None] = mapped_column(String(80))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemEvidence(Base):
    __tablename__ = "problem_evidence"
    __table_args__ = (
        UniqueConstraint(
            "extraction_record_id",
            "evidence_hash",
            name="problem_evidence_record_hash",
        ),
        Index(
            "ix_problem_evidence_entity_type_created",
            "entity_id",
            "evidence_type",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    extraction_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_extraction_records.id")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_documents.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    evidence_type: Mapped[str] = mapped_column(String(50))
    rule_key: Mapped[str] = mapped_column(String(80))
    source_field: Mapped[str] = mapped_column(String(40))
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(String(500))
    evidence_hash: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_version: Mapped[str] = mapped_column(String(80))
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusteringRun(Base):
    __tablename__ = "problem_clustering_runs"
    __table_args__ = (
        UniqueConstraint(
            "algorithm_key",
            "algorithm_version",
            "input_fingerprint",
            name="problem_clustering_input_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    algorithm_key: Mapped[str] = mapped_column(String(80))
    algorithm_version: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    input_definition: Mapped[dict] = mapped_column(JSON)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_count: Mapped[int] = mapped_column(Integer, default=0)
    eligible_count: Mapped[int] = mapped_column(Integer, default=0)
    cluster_count: Mapped[int] = mapped_column(Integer, default=0)
    singleton_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)


class ProblemCluster(Base):
    __tablename__ = "problem_clusters"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "fingerprint",
            name="problem_cluster_run_fingerprint",
        ),
        Index(
            "ix_problem_cluster_status_spread",
            "status",
            "entity_count",
            "document_count",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    signature: Mapped[list] = mapped_column(JSON)
    label: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40))
    representative_evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_evidence.id")
    )
    document_count: Mapped[int] = mapped_column(Integer)
    entity_count: Mapped[int] = mapped_column(Integer)
    source_count: Mapped[int] = mapped_column(Integer)
    cohesion_min: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    cohesion_mean: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    first_source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusterMembership(Base):
    __tablename__ = "problem_cluster_memberships"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "evidence_id",
            name="problem_cluster_run_evidence",
        ),
        Index(
            "ix_problem_cluster_membership_cluster_entity",
            "cluster_id",
            "entity_id",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_evidence.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normalized_documents.id")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    similarity_to_representative: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusterMetricRun(Base):
    __tablename__ = "problem_cluster_metric_runs"
    __table_args__ = (
        UniqueConstraint(
            "clustering_run_id",
            "definition_set_version",
            "input_fingerprint",
            name="problem_cluster_metric_run_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    definition_set_version: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cluster_count: Mapped[int] = mapped_column(Integer, default=0)
    metric_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)


class ProblemClusterMetricObservation(Base):
    __tablename__ = "problem_cluster_metric_observations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "metric_definition_id",
            "cluster_id",
            name="problem_cluster_metric_observation_identity",
        ),
        Index(
            "ix_problem_cluster_metric_cluster_definition_asof",
            "cluster_id",
            "metric_definition_id",
            "as_of",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_cluster_metric_runs.id")
    )
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("metric_definitions.id")
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    numerator: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(50))
    sample_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40))
    confidence_lower: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    confidence_upper: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    calculation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusterSignalRun(Base):
    __tablename__ = "problem_cluster_signal_runs"
    __table_args__ = (
        UniqueConstraint(
            "clustering_run_id",
            "algorithm_version",
            "input_fingerprint",
            name="problem_cluster_signal_run_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    algorithm_version: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    cluster_count: Mapped[int] = mapped_column(Integer)
    observation_count: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class ProblemClusterSignalObservation(Base):
    __tablename__ = "problem_cluster_signal_observations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "cluster_id",
            "metric_definition_id",
            name="problem_cluster_signal_identity",
        ),
        Index(
            "ix_problem_cluster_signal_status",
            "run_id",
            "status",
            "trend_direction",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_cluster_signal_runs.id")
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clusters.id")
    )
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("metric_definitions.id")
    )
    point_count: Mapped[int] = mapped_column(Integer)
    first_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    slope_per_day: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    relative_change_30d: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    trend_direction: Mapped[str | None] = mapped_column(String(20))
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    anomaly_status: Mapped[str] = mapped_column(String(40))
    seasonality_period_days: Mapped[int | None] = mapped_column(Integer)
    seasonality_strength: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6)
    )
    status: Mapped[str] = mapped_column(String(40))
    calculation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusterAudit(Base):
    __tablename__ = "problem_cluster_audits"
    __table_args__ = (
        Index(
            "ix_problem_cluster_audit_cluster_created",
            "cluster_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    supersedes_audit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("problem_cluster_audits.id")
    )
    reviewer: Mapped[str] = mapped_column(String(200))
    verdict: Mapped[str] = mapped_column(String(30))
    sample_method: Mapped[str] = mapped_column(String(50))
    sampled_member_count: Mapped[int] = mapped_column(Integer)
    coherent_member_count: Mapped[int] = mapped_column(Integer)
    purity: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusteringQualitySnapshot(Base):
    __tablename__ = "problem_clustering_quality_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "clustering_run_id",
            "input_fingerprint",
            name="problem_clustering_quality_input",
        ),
        Index(
            "ix_problem_clustering_quality_run_calculated",
            "clustering_run_id",
            "calculated_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40))
    eligible_cluster_count: Mapped[int] = mapped_column(Integer)
    audited_cluster_count: Mapped[int] = mapped_column(Integer)
    coherent_cluster_count: Mapped[int] = mapped_column(Integer)
    sampled_member_count: Mapped[int] = mapped_column(Integer)
    coherent_member_count: Mapped[int] = mapped_column(Integer)
    audit_coverage: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    cluster_coherence_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    member_purity: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    purity_confidence_lower: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    purity_confidence_upper: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    passes_quality_gate: Mapped[bool] = mapped_column(Boolean)
    calculation: Mapped[dict] = mapped_column(JSON)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemClusterLineageRun(Base):
    __tablename__ = "problem_cluster_lineage_runs"
    __table_args__ = (
        UniqueConstraint(
            "previous_clustering_run_id",
            "current_clustering_run_id",
            "algorithm_version",
            name="problem_cluster_lineage_run_identity",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    previous_clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    current_clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    algorithm_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    previous_cluster_count: Mapped[int] = mapped_column(Integer)
    current_cluster_count: Mapped[int] = mapped_column(Integer)
    matched_cluster_count: Mapped[int] = mapped_column(Integer)
    stable_cluster_count: Mapped[int] = mapped_column(Integer)
    split_relation_count: Mapped[int] = mapped_column(Integer)
    merge_relation_count: Mapped[int] = mapped_column(Integer)
    new_cluster_count: Mapped[int] = mapped_column(Integer)
    disappeared_cluster_count: Mapped[int] = mapped_column(Integer)
    stability_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    mean_best_member_jaccard: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 6)
    )
    passes_stability_gate: Mapped[bool] = mapped_column(Boolean)
    calculation: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProblemClusterLineage(Base):
    __tablename__ = "problem_cluster_lineage"
    __table_args__ = (
        UniqueConstraint(
            "lineage_run_id",
            "previous_cluster_id",
            "current_cluster_id",
            name="problem_cluster_lineage_pair",
        ),
        Index(
            "ix_problem_cluster_lineage_run_relation",
            "lineage_run_id",
            "relation_type",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    lineage_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_cluster_lineage_runs.id")
    )
    previous_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("problem_clusters.id")
    )
    current_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("problem_clusters.id")
    )
    relation_type: Mapped[str] = mapped_column(String(30))
    member_jaccard: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    signature_jaccard: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityEligibilityRun(Base):
    __tablename__ = "opportunity_eligibility_runs"
    __table_args__ = (
        UniqueConstraint(
            "clustering_run_id",
            "gate_version",
            "input_fingerprint",
            name="opportunity_eligibility_run_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clustering_runs.id")
    )
    gate_version: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    evaluated_cluster_count: Mapped[int] = mapped_column(Integer)
    eligible_cluster_count: Mapped[int] = mapped_column(Integer)
    excluded_cluster_count: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpportunityEligibilityDecision(Base):
    __tablename__ = "opportunity_eligibility_decisions"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "cluster_id",
            name="opportunity_eligibility_run_cluster",
        ),
        Index(
            "ix_opportunity_eligibility_decision_eligible",
            "run_id",
            "eligible",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_eligibility_runs.id")
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    eligible: Mapped[bool] = mapped_column(Boolean)
    evidence_level: Mapped[str] = mapped_column(String(40))
    blocker_codes: Mapped[list] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceClaim(Base):
    __tablename__ = "evidence_claims"
    __table_args__ = (
        Index(
            "ix_evidence_claim_cluster_current",
            "cluster_id",
            "is_current",
        ),
        Index(
            "ix_evidence_claim_input_current",
            "input_fingerprint",
            "is_current",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    supersedes_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_claims.id")
    )
    claim_type: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    generator_key: Mapped[str] = mapped_column(String(80))
    generator_version: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    evidence_level: Mapped[str] = mapped_column(String(40))
    source_count: Mapped[int] = mapped_column(Integer)
    independence_group_count: Mapped[int] = mapped_column(Integer)
    supporting_evidence_count: Mapped[int] = mapped_column(Integer)
    independence_blockers: Mapped[list] = mapped_column(JSON)
    is_current: Mapped[bool] = mapped_column(Boolean)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "problem_evidence_id",
            "direction",
            name="claim_problem_evidence_direction",
        ),
        Index(
            "ix_claim_evidence_link_claim_direction",
            "claim_id",
            "direction",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_claims.id")
    )
    problem_evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_evidence.id")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    direction: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClaimCommercialOutcomeLink(Base):
    __tablename__ = "claim_commercial_outcome_links"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "outcome_id",
            "direction",
            name="claim_commercial_outcome_direction",
        ),
        Index(
            "ix_claim_commercial_outcome_claim_direction",
            "claim_id",
            "direction",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_claims.id")
    )
    outcome_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commercial_outcomes.id")
    )
    direction: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceClaimReview(Base):
    __tablename__ = "evidence_claim_reviews"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "version",
            name="evidence_claim_review_version",
        ),
        Index(
            "ix_evidence_claim_review_claim_time",
            "claim_id",
            "reviewed_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_claims.id")
    )
    version: Mapped[str] = mapped_column(String(80))
    previous_status: Mapped[str] = mapped_column(String(30))
    decision: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = uuid_pk()
    origin_cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_clusters.id"),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityVersion(Base):
    __tablename__ = "opportunity_versions"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "version_number",
            name="opportunity_version_number",
        ),
        Index(
            "ix_opportunity_versions_current",
            "opportunity_id",
            "is_current",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunities.id")
    )
    eligibility_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_eligibility_decisions.id")
    )
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    ontology_schema_version: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(500))
    ontology: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30))
    evidence_level: Mapped[str] = mapped_column(String(40))
    input_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    is_current: Mapped[bool] = mapped_column(Boolean)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityComponentClaimLink(Base):
    __tablename__ = "opportunity_component_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_version_id",
            "component_key",
            name="opportunity_version_component",
        ),
        Index(
            "ix_opportunity_component_claim",
            "claim_id",
            "component_key",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    component_key: Mapped[str] = mapped_column(String(50))
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_claims.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScoringProfile(Base):
    __tablename__ = "scoring_profiles"
    __table_args__ = (
        UniqueConstraint(
            "key",
            "version",
            name="scoring_profile_version",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    weights: Mapped[dict] = mapped_column(JSON)
    minimum_confidence: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityScoreRun(Base):
    __tablename__ = "opportunity_score_runs"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "as_of",
            "input_fingerprint",
            name="opportunity_score_run_identity",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scoring_profiles.id")
    )
    research_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_profiles.id")
    )
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    opportunity_count: Mapped[int] = mapped_column(Integer)
    rankable_count: Mapped[int] = mapped_column(Integer)
    excluded_count: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class OpportunityScoreSnapshot(Base):
    __tablename__ = "opportunity_score_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "opportunity_version_id",
            name="opportunity_score_run_version",
        ),
        Index(
            "ix_opportunity_score_status_total",
            "run_id",
            "status",
            "total_score",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_score_runs.id")
    )
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    potential_score: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    actionability_score: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    uncertainty: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    status: Mapped[str] = mapped_column(String(40))
    components: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityRankingRun(Base):
    __tablename__ = "opportunity_ranking_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    score_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_score_runs.id"),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    candidate_count: Mapped[int] = mapped_column(Integer)
    ranked_count: Mapped[int] = mapped_column(Integer)
    excluded_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityRankingEntry(Base):
    __tablename__ = "opportunity_ranking_entries"
    __table_args__ = (
        UniqueConstraint(
            "ranking_run_id",
            "score_snapshot_id",
            name="opportunity_ranking_snapshot",
        ),
        UniqueConstraint(
            "ranking_run_id",
            "rank",
            name="opportunity_ranking_position",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    ranking_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_ranking_runs.id")
    )
    score_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_score_snapshots.id")
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    eligible: Mapped[bool] = mapped_column(Boolean)
    exclusion_reasons: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        UniqueConstraint(
            "score_run_id",
            "outcome_window_days",
            name="backtest_score_window",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    score_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_score_runs.id")
    )
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome_window_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40))
    prediction_count: Mapped[int] = mapped_column(Integer)
    evaluated_count: Mapped[int] = mapped_column(Integer)
    positive_count: Mapped[int] = mapped_column(Integer)
    brier_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    baseline_brier_score: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 6)
    )
    improvement: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class BacktestPrediction(Base):
    __tablename__ = "backtest_predictions"
    __table_args__ = (
        UniqueConstraint(
            "backtest_run_id",
            "score_snapshot_id",
            name="backtest_run_score_snapshot",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backtest_runs.id")
    )
    score_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_score_snapshots.id")
    )
    predicted_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 6)
    )
    outcome_observed: Mapped[bool | None] = mapped_column(Boolean)
    outcome_count: Mapped[int] = mapped_column(Integer)
    evaluation_status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CommercialValidationExperiment(Base):
    __tablename__ = "commercial_validation_experiments"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "external_key",
            name="commercial_experiment_cluster_external_key",
        ),
        Index(
            "ix_commercial_experiment_cluster_status",
            "cluster_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problem_clusters.id"))
    opportunity_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    external_key: Mapped[str] = mapped_column(String(80))
    protocol_key: Mapped[str] = mapped_column(String(80), default="default-v1")
    cohort: Mapped[str] = mapped_column(String(30), default="radar")
    experiment_type: Mapped[str] = mapped_column(String(40))
    target_segment: Mapped[str] = mapped_column(Text)
    hypothesis: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CommercialOutcome(Base):
    __tablename__ = "commercial_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "idempotency_key",
            name="commercial_outcome_experiment_idempotency",
        ),
        Index(
            "ix_commercial_outcome_experiment_verification",
            "experiment_id",
            "verification_status",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commercial_validation_experiments.id")
    )
    idempotency_key: Mapped[str] = mapped_column(String(80))
    participant_key_hash: Mapped[str] = mapped_column(String(64))
    outcome_type: Mapped[str] = mapped_column(String(40))
    direction: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    evidence_reference: Mapped[str | None] = mapped_column(String(800))
    notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verifier: Mapped[str | None] = mapped_column(String(200))
    verification_notes: Mapped[str | None] = mapped_column(Text)


class CommercialOutcomeReview(Base):
    __tablename__ = "commercial_outcome_reviews"
    __table_args__ = (
        Index(
            "ix_commercial_outcome_review_outcome_time",
            "outcome_id",
            "reviewed_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    outcome_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commercial_outcomes.id")
    )
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CommercialContactPreference(Base):
    __tablename__ = "commercial_contact_preferences"
    __table_args__ = (
        Index(
            "ix_commercial_contact_participant_scope",
            "participant_key_hash",
            "channel",
            "scope",
        ),
        Index(
            "ix_commercial_contact_status_recorded",
            "status",
            "recorded_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    participant_key_hash: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(30))
    scope: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))
    evidence_reference: Mapped[str | None] = mapped_column(String(800))
    recorded_by: Mapped[str] = mapped_column(String(200))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EntityExternalId(Base):
    __tablename__ = "entity_external_ids"
    __table_args__ = (
        UniqueConstraint("source_id", "external_type", "external_id", name="external_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    external_type: Mapped[str] = mapped_column(String(80))
    external_id: Mapped[str] = mapped_column(String(300))
    external_url: Mapped[str | None] = mapped_column(String(800))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    github_repository_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner_login: Mapped[str] = mapped_column(String(200))
    repository_name: Mapped[str] = mapped_column(String(300))
    full_name: Mapped[str] = mapped_column(String(500), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    homepage: Mapped[str | None] = mapped_column(String(800))
    primary_language: Mapped[str | None] = mapped_column(String(100))
    license_spdx: Mapped[str | None] = mapped_column(String(100))
    default_branch: Mapped[str] = mapped_column(String(300))
    created_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class RepositoryObservation(Base):
    __tablename__ = "repository_observations"
    __table_args__ = (
        UniqueConstraint("repository_id", "observed_at", name="repository_observed_at"),
        UniqueConstraint("snapshot_id", name="repository_observation_snapshot"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stars_count: Mapped[int] = mapped_column(Integer)
    forks_count: Mapped[int] = mapped_column(Integer)
    watchers_count: Mapped[int] = mapped_column(Integer)
    subscribers_count: Mapped[int | None] = mapped_column(Integer)
    open_items_count: Mapped[int] = mapped_column(Integer)
    size: Mapped[int] = mapped_column(Integer)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    topics: Mapped[list] = mapped_column(JSON, default=list)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))


class RepositoryWorkItem(Base):
    __tablename__ = "repository_work_items"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_item_id", name="repository_work_item"),
        Index("ix_work_item_repository_type_state", "repository_id", "item_type", "state"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"))
    github_item_id: Mapped[int] = mapped_column(BigInteger)
    number: Mapped[int] = mapped_column(Integer)
    item_type: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    labels: Mapped[list] = mapped_column(JSON, default=list)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    author_association: Mapped[str | None] = mapped_column(String(50))
    created_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_bot_likely: Mapped[bool] = mapped_column(Boolean, default=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))


class StackExchangeQuestion(Base):
    __tablename__ = "stack_exchange_questions"
    __table_args__ = (
        UniqueConstraint(
            "site",
            "question_id",
            name="stack_exchange_site_question",
        ),
        Index(
            "ix_stack_exchange_question_site_activity",
            "site",
            "last_activity_at_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id"),
        primary_key=True,
    )
    site: Mapped[str] = mapped_column(String(80))
    question_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(String(800))
    tags: Mapped[list] = mapped_column(JSON)
    answer_count: Mapped[int] = mapped_column(Integer)
    is_answered: Mapped[bool] = mapped_column(Boolean)
    accepted_answer_id: Mapped[int | None] = mapped_column(BigInteger)
    view_count: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    bounty_amount: Mapped[int | None] = mapped_column(Integer)
    content_license: Mapped[str] = mapped_column(String(80))
    created_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity_at_source: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    last_edit_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))


class CostEntry(Base):
    __tablename__ = "cost_entries"
    __table_args__ = (
        UniqueConstraint("external_key", name="cost_entry_external_key"),
        Index("ix_cost_entry_occurred_currency", "occurred_at", "currency"),
        Index("ix_cost_entry_source_occurred", "source_id", "occurred_at"),
        Index(
            "ix_cost_entry_opportunity_occurred",
            "opportunity_id",
            "occurred_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    external_key: Mapped[str] = mapped_column(String(120))
    operation_type: Mapped[str] = mapped_column(String(60))
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id")
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opportunities.id")
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commercial_validation_experiments.id")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    currency: Mapped[str] = mapped_column(String(3))
    units: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OperationalAlert(Base):
    __tablename__ = "operational_alerts"
    __table_args__ = (
        UniqueConstraint("alert_key", name="operational_alert_key"),
        Index(
            "ix_operational_alert_status_severity",
            "status",
            "severity",
        ),
        Index("ix_operational_alert_source_status", "source_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    alert_key: Mapped[str] = mapped_column(String(180))
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id")
    )
    category: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpportunityReview(Base):
    __tablename__ = "opportunity_reviews"
    __table_args__ = (
        Index(
            "ix_opportunity_review_version_created",
            "opportunity_version_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    decision: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityResearchRun(Base):
    __tablename__ = "opportunity_research_runs"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_version_id",
            "input_fingerprint",
            name="opportunity_research_version_input",
        ),
        Index(
            "ix_opportunity_research_version_started",
            "opportunity_version_id",
            "started_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    research_tier: Mapped[str] = mapped_column(String(30))
    focus_questions: Mapped[list] = mapped_column(JSON)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    evidence_snapshot: Mapped[dict] = mapped_column(JSON)
    findings: Mapped[dict] = mapped_column(JSON)
    blockers: Mapped[list] = mapped_column(JSON)
    requested_by: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class OpportunityExport(Base):
    __tablename__ = "opportunity_exports"
    __table_args__ = (
        UniqueConstraint(
            "destination",
            "idempotency_key",
            name="opportunity_export_destination_key",
        ),
        Index(
            "ix_opportunity_export_version_created",
            "opportunity_version_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_research_runs.id")
    )
    destination: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    external_reference: Mapped[str | None] = mapped_column(String(300))


class VerticalDefinition(Base):
    __tablename__ = "vertical_definitions"
    __table_args__ = (
        UniqueConstraint("key", "version", name="vertical_definition_version"),
        Index("ix_vertical_definition_current", "key", "is_current"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    config: Mapped[dict] = mapped_column(JSON)
    selection_rationale: Mapped[str] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchProfile(Base):
    __tablename__ = "research_profiles"
    __table_args__ = (
        UniqueConstraint("key", "version", name="research_profile_version"),
        Index("ix_research_profile_current", "key", "is_current"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    vertical_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vertical_definitions.id")
    )
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    constraints: Mapped[dict] = mapped_column(JSON)
    exclusions: Mapped[dict] = mapped_column(JSON)
    preferences: Mapped[dict] = mapped_column(JSON)
    is_current: Mapped[bool] = mapped_column(Boolean)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityProfileEvaluation(Base):
    __tablename__ = "opportunity_profile_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_version_id",
            "research_profile_id",
            "input_fingerprint",
            name="opportunity_profile_evaluation_input",
        ),
        Index(
            "ix_opportunity_profile_version_evaluated",
            "opportunity_version_id",
            "evaluated_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    opportunity_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_versions.id")
    )
    research_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_profiles.id")
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    observed_attributes: Mapped[dict] = mapped_column(JSON)
    eligible: Mapped[bool] = mapped_column(Boolean)
    blocker_codes: Mapped[list] = mapped_column(JSON)
    unknown_fields: Mapped[list] = mapped_column(JSON)
    fit_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    data_coverage: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    components: Mapped[dict] = mapped_column(JSON)
    evaluated_by: Mapped[str] = mapped_column(String(200))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        UniqueConstraint("key", name="scheduled_job_key"),
        Index("ix_scheduled_job_due", "status", "next_run_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(100))
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    interval_minutes: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    consecutive_failure_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScheduledJobRun(Base):
    __tablename__ = "scheduled_job_runs"
    __table_args__ = (
        Index(
            "ix_scheduled_job_run_job_started",
            "scheduled_job_id",
            "started_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scheduled_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheduled_jobs.id")
    )
    status: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSON)
    error_class: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_event_occurred", "occurred_at"),
        Index("ix_audit_event_request", "request_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(30))
    duration_ms: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (
        UniqueConstraint("key", "version", name="metric_definition_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(50))
    numerator_description: Mapped[str | None] = mapped_column(Text)
    denominator_description: Mapped[str | None] = mapped_column(Text)
    minimum_sample_size: Mapped[int] = mapped_column(Integer)
    window_days: Mapped[int | None] = mapped_column(Integer)
    comparison_group_description: Mapped[str] = mapped_column(Text)
    freshness_policy: Mapped[str] = mapped_column(String(200))
    confidence_method: Mapped[str] = mapped_column(String(80))
    missing_data_policy: Mapped[str] = mapped_column(String(80))
    outlier_policy: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MetricRun(Base):
    __tablename__ = "metric_runs"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "definition_set_version",
            "as_of",
            name="metric_run_identity",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_collections.id")
    )
    definition_set_version: Mapped[str] = mapped_column(String(40))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_document_count: Mapped[int] = mapped_column(Integer, default=0)
    metric_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "metric_definition_id",
            "entity_id",
            name="metric_observation_identity",
        ),
        Index(
            "ix_metric_observation_entity_definition_asof",
            "entity_id",
            "metric_definition_id",
            "as_of",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("metric_runs.id"))
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("metric_definitions.id")
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_collections.id")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    numerator: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(50))
    sample_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40))
    confidence_lower: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    confidence_upper: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    calculation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignalDefinition(Base):
    __tablename__ = "signal_definitions"
    __table_args__ = (
        UniqueConstraint("key", "version", name="signal_definition_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SignalValue(Base):
    __tablename__ = "signal_values"
    __table_args__ = (
        UniqueConstraint(
            "metric_observation_id",
            "signal_definition_id",
            name="metric_signal_value",
        ),
        Index(
            "ix_signal_value_entity_asof",
            "entity_id",
            "as_of",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    signal_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_definitions.id")
    )
    metric_observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("metric_observations.id")
    )
    baseline_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("metric_observations.id")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_change: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    relative_change: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    direction: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (UniqueConstraint("registry", "package_name", name="registry_package"),)

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    registry: Mapped[str] = mapped_column(String(50))
    package_name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    license_expression: Mapped[str | None] = mapped_column(String(300))
    repository_url_raw: Mapped[str | None] = mapped_column(String(800))
    repository_directory: Mapped[str | None] = mapped_column(String(500))
    homepage_url: Mapped[str | None] = mapped_column(String(800))
    created_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False)


class PackageRepositoryLink(Base):
    __tablename__ = "package_repository_links"
    __table_args__ = (
        UniqueConstraint(
            "package_id",
            "repository_full_name",
            name="package_repository_link_target",
        ),
        Index(
            "ix_package_repository_link_status_target",
            "status",
            "repository_full_name",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("packages.id"))
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("repositories.id")
    )
    repository_full_name: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(800))
    repository_directory: Mapped[str | None] = mapped_column(String(500))
    match_method: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(30), default="candidate")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer: Mapped[str | None] = mapped_column(String(200))
    review_notes: Mapped[str | None] = mapped_column(Text)


class PackageRepositoryLinkReview(Base):
    __tablename__ = "package_repository_link_reviews"
    __table_args__ = (
        Index(
            "ix_package_repository_link_review_link_time",
            "link_id",
            "reviewed_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_repository_links.id")
    )
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PackageVersion(Base):
    __tablename__ = "package_versions"
    __table_args__ = (UniqueConstraint("package_id", "version", name="package_version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("packages.id"))
    version: Mapped[str] = mapped_column(String(100))
    published_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    license_expression: Mapped[str | None] = mapped_column(String(300))
    repository_url_raw: Mapped[str | None] = mapped_column(String(800))
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_snapshots.id"))
