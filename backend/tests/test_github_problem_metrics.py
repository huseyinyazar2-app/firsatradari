from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    ClaimEvidenceLink,
    DataSource,
    Entity,
    EvidenceClaim,
    IngestionRun,
    MetricDefinition,
    MetricObservation,
    NormalizedDocument,
    OpportunityEligibilityDecision,
    ProblemCluster,
    ProblemClusteringQualitySnapshot,
    ProblemClusterLineage,
    ProblemClusterMembership,
    ProblemClusterMetricObservation,
    ProblemEvidence,
    ProblemExtractionRecord,
    Repository,
    SignalValue,
)
from firsat_radari.evidence_graph.service import EvidenceGraphService
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.main import create_app
from firsat_radari.metrics.github_problem import (
    METRIC_SPECS,
    GitHubProblemMetricEngine,
    MetricEngineError,
)
from firsat_radari.metrics.problem_clusters import (
    CLUSTER_METRIC_SPECS,
    ProblemClusterMetricEngine,
)
from firsat_radari.normalization.github_work_items import GitHubWorkItemNormalizer
from firsat_radari.normalization.service import NormalizationService
from firsat_radari.opportunities.eligibility import OpportunityEligibilityService
from firsat_radari.problem_mining.clustering import (
    ProblemClusteringEngine,
    ProblemClusteringError,
)
from firsat_radari.problem_mining.github import GitHubProblemEvidenceExtractor
from firsat_radari.problem_mining.lineage import ProblemClusterLineageService
from firsat_radari.problem_mining.quality import (
    ClusterAuditInput,
    ProblemClusterQualityService,
)
from firsat_radari.source_registry.service import (
    SourceIndependenceDecision,
    SourceRegistryService,
)
from firsat_radari.storage.filesystem import FileObjectStore


class WorkItemConnector(DataConnector):
    source_key = "github"
    job_type = "github_work_items"
    version = "metrics-test-1"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=False,
        incremental=False,
        historical=False,
        deletions=False,
        conditional_requests=False,
        pagination="none",
        rate_limit_headers=False,
        source_timestamps=True,
    )

    def __init__(
        self,
        items: list[RawItem],
        *,
        is_complete: bool = True,
    ) -> None:
        self._items = items
        self._is_complete = is_complete

    async def discover(
        self,
        query: dict,
        checkpoint: dict | None = None,
    ) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=self._items,
            is_complete=self._is_complete,
            resume_available=False,
            completeness_reason=None if self._is_complete else "search_result_cap",
            expected_total=len(self._items),
        )

    async def fetch(self, external_id: str) -> CollectionResult:
        raise NotImplementedError


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_github_source_and_repository(session: Session) -> Repository:
    source = DataSource(
        key="github",
        source_type="api",
        evidence_family_key="developer_repository_activity",
        independence_group_key="github",
        independence_status="conditional",
        owner="GitHub",
        base_url="https://api.github.com",
        policy_status="approved",
        policy_version="test-policy",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission="allowed",
        llm_processing_permission="prohibited",
        retention_days=30,
        enabled=True,
    )
    entity = Entity(
        entity_type="repository",
        canonical_name="example/radar",
        canonical_url="https://github.com/example/radar",
        status="active",
    )
    session.add_all([source, entity])
    session.flush()
    repository = Repository(
        id=entity.id,
        github_repository_id=123,
        owner_login="example",
        repository_name="radar",
        full_name="example/radar",
        description="test",
        homepage=None,
        primary_language="Python",
        license_spdx="MIT",
        default_branch="main",
        created_at_source=datetime(2025, 1, 1, tzinfo=UTC),
        archived=False,
        disabled=False,
    )
    session.add(repository)
    session.commit()
    return repository


def work_items(*, count: int = 30, start_id: int = 1) -> list[RawItem]:
    observed_at = datetime.now(UTC)
    items: list[RawItem] = []
    for offset in range(count):
        item_id = start_id + offset
        is_pull_request = offset >= 20
        is_closed_issue = not is_pull_request and offset >= 10
        created_at = observed_at - timedelta(days=20 - min(offset, 19))
        closed_at = created_at + timedelta(days=5) if is_closed_issue else None
        payload = {
            "id": item_id,
            "number": item_id,
            "repository_url": "https://api.github.com/repos/example/radar",
            "html_url": f"https://github.com/example/radar/issues/{item_id}",
            "title": f"Work item {item_id}",
            "body": "Reproducible problem",
            "state": "closed" if is_closed_issue else "open",
            "labels": [{"name": "bug"}] if offset < 10 else [],
            "comments": 2,
            "author_association": "NONE",
            "user": {"login": f"user-{item_id}", "type": "User"},
            "created_at": created_at.isoformat(),
            "updated_at": (closed_at or created_at).isoformat(),
            "closed_at": closed_at.isoformat() if closed_at else None,
        }
        if is_pull_request:
            payload["pull_request"] = {
                "url": f"https://api.github.com/repos/example/radar/pulls/{item_id}"
            }
        items.append(
            RawItem(
                external_type="repository_work_item",
                external_id=str(item_id),
                payload=payload,
                observed_at=observed_at,
                source_created_at=created_at,
                source_updated_at=closed_at or created_at,
            )
        )
    return items


async def ingest_and_normalize(
    session: Session,
    store: FileObjectStore,
    items: list[RawItem],
    *,
    is_complete: bool = True,
    extract_problem_evidence: bool = False,
) -> IngestionRun:
    outcome = await IngestionService(session, store).discover(
        WorkItemConnector(items, is_complete=is_complete),
        {"q": "repo:example/radar"},
    )
    NormalizationService(session, store).normalize_pending(
        GitHubWorkItemNormalizer(),
        limit=100,
    )
    if extract_problem_evidence:
        GitHubProblemEvidenceExtractor(session).extract_pending(limit=100)
    run = session.get(IngestionRun, outcome.run_id)
    assert run is not None
    return run


@pytest.mark.asyncio
async def test_complete_collection_produces_guarded_metrics_and_trends(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    store = FileObjectStore(tmp_path)
    items = work_items()
    items[0].payload["body"] = (
        "We manually copy-paste this every time and would pay for a workaround."
    )

    first_ingestion = await ingest_and_normalize(
        session,
        store,
        items,
        extract_problem_evidence=True,
    )
    assert first_ingestion.collection_id is not None
    first = GitHubProblemMetricEngine(session).calculate(
        first_ingestion.collection_id
    )

    observations = list(
        session.execute(
            select(MetricDefinition.key, MetricObservation)
            .join(
                MetricObservation,
                MetricObservation.metric_definition_id == MetricDefinition.id,
            )
            .where(MetricObservation.run_id == first.run_id)
        )
    )
    by_key = {key: observation for key, observation in observations}
    assert first.status == "succeeded"
    assert first.input_document_count == 30
    assert first.metric_count == len(METRIC_SPECS)
    assert set(by_key) == {spec.key for spec in METRIC_SPECS}
    assert all(observation.status == "measured" for observation in by_key.values())
    assert by_key["github.eligible_issue_count"].value == Decimal("20")
    assert by_key["github.pull_request_share"].value == Decimal("0.333333")
    assert by_key["github.bug_label_ratio"].value == Decimal("0.500000")
    assert by_key["github.open_issue_ratio"].value == Decimal("0.500000")
    assert by_key["github.mean_issue_comments"].value == Decimal("2")
    assert by_key["github.median_resolution_days"].value == Decimal("5")
    assert by_key["github.payment_intent_issue_ratio"].value == Decimal("0.05")
    assert by_key["github.workaround_issue_ratio"].value == Decimal("0.05")
    assert by_key["github.bug_label_ratio"].confidence_lower is not None
    assert first_ingestion.collection_id is not None
    assert first_ingestion.finished_at is not None
    with pytest.raises(MetricEngineError, match="must match"):
        GitHubProblemMetricEngine(session).calculate(
            first_ingestion.collection_id,
            as_of=first_ingestion.finished_at + timedelta(seconds=1),
        )

    second_ingestion = await ingest_and_normalize(
        session,
        store,
        items,
        extract_problem_evidence=True,
    )
    assert second_ingestion.raw_item_count == 0
    assert second_ingestion.duplicate_item_count == 30
    assert second_ingestion.collection_id is not None
    second = GitHubProblemMetricEngine(session).calculate(
        second_ingestion.collection_id
    )
    repeated = GitHubProblemMetricEngine(session).calculate(
        second_ingestion.collection_id
    )

    assert second.input_document_count == 30
    assert repeated.run_id == second.run_id
    trend_values = list(
        session.scalars(
            select(SignalValue).where(
                SignalValue.metric_observation_id.in_(
                    select(MetricObservation.id).where(
                        MetricObservation.run_id == second.run_id
                    )
                )
            )
        )
    )
    assert len(trend_values) == len(METRIC_SPECS)
    assert all(value.status == "measured" for value in trend_values)
    assert all(value.direction == "flat" for value in trend_values)

    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        metrics_api_enabled=True,
    )
    with TestClient(app) as client:
        response = client.post(
            "/metric-runs",
            json={"collection_id": str(second_ingestion.collection_id)},
        )
        assert response.status_code == 201
        assert response.json()["id"] == str(second.run_id)
        assert len(client.get("/metric-definitions").json()) == len(METRIC_SPECS)
        assert len(
            client.get(f"/metric-runs/{second.run_id}/observations").json()
        ) == len(METRIC_SPECS)
        signal_response = client.get(
            "/signals",
            params={"metric_key": "github.bug_label_ratio"},
        )
        assert signal_response.status_code == 200
        assert len(signal_response.json()) == 2


@pytest.mark.asyncio
async def test_incomplete_collection_never_emits_measured_values(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    run = await ingest_and_normalize(
        session,
        FileObjectStore(tmp_path),
        work_items(),
        is_complete=False,
        extract_problem_evidence=True,
    )
    assert run.collection_id is not None

    outcome = GitHubProblemMetricEngine(session).calculate(run.collection_id)
    observations = list(
        session.scalars(
            select(MetricObservation).where(
                MetricObservation.run_id == outcome.run_id
            )
        )
    )

    assert len(observations) == len(METRIC_SPECS)
    assert all(observation.status == "incomplete_collection" for observation in observations)
    assert all(observation.value is None for observation in observations)


@pytest.mark.asyncio
async def test_small_sample_is_unknown_instead_of_zero(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    run = await ingest_and_normalize(
        session,
        FileObjectStore(tmp_path),
        work_items(count=5),
        extract_problem_evidence=True,
    )
    assert run.collection_id is not None

    outcome = GitHubProblemMetricEngine(session).calculate(run.collection_id)
    bug_ratio = session.scalar(
        select(MetricObservation)
        .join(
            MetricDefinition,
            MetricDefinition.id == MetricObservation.metric_definition_id,
        )
        .where(
            MetricObservation.run_id == outcome.run_id,
            MetricDefinition.key == "github.bug_label_ratio",
        )
    )

    assert bug_ratio is not None
    assert bug_ratio.status == "insufficient_sample"
    assert bug_ratio.value is None
    assert bug_ratio.numerator == Decimal("5")
    assert bug_ratio.denominator == Decimal("5")


@pytest.mark.asyncio
async def test_missing_problem_extraction_blocks_measurement(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    run = await ingest_and_normalize(
        session,
        FileObjectStore(tmp_path),
        work_items(),
    )
    assert run.collection_id is not None

    outcome = GitHubProblemMetricEngine(session).calculate(run.collection_id)
    observations = list(
        session.scalars(
            select(MetricObservation).where(
                MetricObservation.run_id == outcome.run_id
            )
        )
    )

    assert len(observations) == len(METRIC_SPECS)
    assert all(
        observation.status == "incomplete_problem_extraction"
        for observation in observations
    )
    assert all(observation.value is None for observation in observations)


@pytest.mark.asyncio
async def test_problem_evidence_is_grounded_versioned_and_idempotent(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    items = work_items(count=3)
    items[0].payload["body"] = (
        "Every time this happens we manually copy-paste data. "
        "We would pay for a reliable workaround."
    )
    items[1].payload["body"] = (
        "This is a critical blocker and takes hours of work each time."
    )
    items[2].payload["user"] = {"login": "robot[bot]", "type": "Bot"}
    await ingest_and_normalize(session, FileObjectStore(tmp_path), items)

    first = GitHubProblemEvidenceExtractor(session).extract_pending()
    second = GitHubProblemEvidenceExtractor(session).extract_pending()

    assert first.status == "succeeded"
    assert first.input_count == 3
    assert first.success_count == 3
    assert first.evidence_count >= 8
    assert second.input_count == 0
    assert (
        len(
            list(
                session.scalars(
                    select(ProblemExtractionRecord).where(
                        ProblemExtractionRecord.status == "succeeded"
                    )
                )
            )
        )
        == 3
    )
    evidence = list(session.scalars(select(ProblemEvidence)))
    evidence_types = {item.evidence_type for item in evidence}
    assert {
        "problem_report",
        "frequency",
        "workaround",
        "payment_intent",
        "severe_impact",
        "time_impact",
    } <= evidence_types
    assert all(item.policy_version == "test-policy" for item in evidence)
    assert all(item.retention_until is not None for item in evidence)

    payment = next(
        item for item in evidence if item.evidence_type == "payment_intent"
    )
    document = session.get(NormalizedDocument, payment.document_id)
    assert document is not None
    source_text = document.title if payment.source_field == "title" else document.body
    assert source_text is not None
    assert payment.char_start is not None
    assert payment.char_end is not None
    assert (
        source_text[payment.char_start : payment.char_end]
        == payment.attributes["matched_text"]
    )

    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        problem_extraction_api_enabled=True,
    )
    with TestClient(app) as client:
        run_response = client.post("/problem-extraction-runs", json={})
        assert run_response.status_code == 201
        assert run_response.json()["input_count"] == 0
        evidence_response = client.get(
            "/problem-evidence",
            params={
                "evidence_type": "payment_intent",
                "minimum_confidence": "0.8",
            },
        )
        assert evidence_response.status_code == 200
        assert len(evidence_response.json()) == 1


@pytest.mark.asyncio
async def test_feature_request_is_not_assumed_to_be_a_problem_report(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    items = work_items(count=1)
    items[0].payload["title"] = "Add CSV export support"
    items[0].payload["body"] = (
        "Feature request: scheduled exports are currently not working "
        "for our workflow."
    )
    items[0].payload["labels"] = [{"name": "enhancement"}]
    await ingest_and_normalize(session, FileObjectStore(tmp_path), items)

    outcome = GitHubProblemEvidenceExtractor(session).extract_pending()
    evidence = list(session.scalars(select(ProblemEvidence)))

    assert outcome.status == "succeeded"
    assert {item.evidence_type for item in evidence} == {
        "missing_capability"
    }
    assert all(item.rule_key != "github_issue_report" for item in evidence)


@pytest.mark.asyncio
async def test_problem_clustering_requires_cross_project_repetition(
    session: Session,
    tmp_path: Path,
) -> None:
    add_github_source_and_repository(session)
    second_entity = Entity(
        entity_type="repository",
        canonical_name="another/radar",
        canonical_url="https://github.com/another/radar",
        status="active",
    )
    session.add(second_entity)
    session.flush()
    session.add(
        Repository(
            id=second_entity.id,
            github_repository_id=456,
            owner_login="another",
            repository_name="radar",
            full_name="another/radar",
            description="second test repository",
            homepage=None,
            primary_language="Python",
            license_spdx="MIT",
            default_branch="main",
            created_at_source=datetime(2025, 1, 1, tzinfo=UTC),
            archived=False,
            disabled=False,
        )
    )
    session.commit()

    items = work_items(count=3)
    items[0].payload["title"] = (
        "Windows setup fails during package installation"
    )
    items[1].payload["title"] = (
        "Package installation on Windows fails in setup"
    )
    items[1].payload["repository_url"] = (
        "https://api.github.com/repos/another/radar"
    )
    items[2].payload["title"] = "OAuth token refresh crashes after login"
    items[2].payload["repository_url"] = (
        "https://api.github.com/repos/another/radar"
    )
    await ingest_and_normalize(session, FileObjectStore(tmp_path), items)
    GitHubProblemEvidenceExtractor(session).extract_pending()

    first = ProblemClusteringEngine(session).cluster()
    repeated = ProblemClusteringEngine(session).cluster()

    assert first.status == "succeeded"
    assert first.input_count == 3
    assert first.eligible_count == 3
    assert first.cluster_count == 2
    assert first.singleton_count == 1
    assert repeated.run_id == first.run_id
    clusters = list(
        session.scalars(
            select(ProblemCluster).where(ProblemCluster.run_id == first.run_id)
        )
    )
    cross_project = next(
        cluster
        for cluster in clusters
        if cluster.status == "cross_entity_candidate"
    )
    assert cross_project.document_count == 2
    assert cross_project.entity_count == 2
    assert cross_project.source_count == 1
    assert {"fail", "install", "package", "setup", "windows"} == set(
        cross_project.signature
    )
    memberships = list(
        session.scalars(
            select(ProblemClusterMembership).where(
                ProblemClusterMembership.cluster_id == cross_project.id
            )
        )
    )
    assert len(memberships) == 2
    assert all(
        membership.similarity_to_representative == Decimal("1.000000")
        for membership in memberships
    )
    claim_graph = EvidenceGraphService(session).materialize_problem_claims(
        first.run_id
    )
    repeated_claim_graph = EvidenceGraphService(
        session
    ).materialize_problem_claims(first.run_id)
    assert claim_graph.claim_count == 1
    assert claim_graph.created_count == 1
    assert claim_graph.reused_count == 0
    assert repeated_claim_graph.created_count == 0
    assert repeated_claim_graph.reused_count == 1
    claim = session.scalar(
        select(EvidenceClaim).where(
            EvidenceClaim.cluster_id == cross_project.id,
            EvidenceClaim.is_current.is_(True),
        )
    )
    assert claim is not None
    assert claim.claim_type == "recurring_problem"
    assert claim.status == "grounded"
    assert claim.evidence_level == "E1"
    assert claim.source_count == 1
    assert claim.supporting_evidence_count == 2
    assert claim.independence_blockers == ["single_source"]
    claim_links = list(
        session.scalars(
            select(ClaimEvidenceLink).where(
                ClaimEvidenceLink.claim_id == claim.id
            )
        )
    )
    assert len(claim_links) == 2
    assert all(link.direction == "supports" for link in claim_links)
    metric_run = ProblemClusterMetricEngine(session).calculate(first.run_id)
    repeated_metric_run = ProblemClusterMetricEngine(session).calculate(
        first.run_id
    )
    assert metric_run.status == "succeeded"
    assert metric_run.cluster_count == 2
    assert metric_run.metric_count == 2 * len(CLUSTER_METRIC_SPECS)
    assert repeated_metric_run.run_id == metric_run.run_id
    SourceRegistryService(session).review_independence(
        "github",
        SourceIndependenceDecision(
            version="test-review-v1",
            new_status="independent",
            reviewer="data-governance",
            rationale="Source ownership and collection path were reviewed.",
            evidence_references=(
                "https://example.test/governance/github-review",
            ),
        ),
    )
    previous_metric_run_id = metric_run.run_id
    governance_metric_run = ProblemClusterMetricEngine(session).calculate(
        first.run_id
    )
    assert governance_metric_run.run_id != previous_metric_run_id
    metric_run = governance_metric_run
    cross_metrics = list(
        session.scalars(
            select(ProblemClusterMetricObservation).where(
                ProblemClusterMetricObservation.run_id == metric_run.run_id,
                ProblemClusterMetricObservation.cluster_id == cross_project.id,
            )
        )
    )
    assert len(cross_metrics) == len(CLUSTER_METRIC_SPECS)
    assert all(metric.status == "insufficient_sample" for metric in cross_metrics)
    assert all(metric.value is None for metric in cross_metrics)
    assert all(
        metric.calculation["ranking_eligible"] is False
        for metric in cross_metrics
    )
    quality_service = ProblemClusterQualityService(session)
    before_audit = quality_service.calculate(first.run_id)
    audit = quality_service.add_audit(
        ClusterAuditInput(
            cluster_id=cross_project.id,
            reviewer="quality-reviewer",
            verdict="coherent",
            sample_method="all_members",
            sampled_member_count=2,
            coherent_member_count=2,
            notes="Both issue titles describe the same setup failure.",
        )
    )
    after_audit = quality_service.calculate(first.run_id)
    repeated_quality = quality_service.calculate(first.run_id)
    assert before_audit.status == "insufficient_audits"
    assert before_audit.audited_cluster_count == 0
    assert after_audit.status == "insufficient_audits"
    assert after_audit.audited_cluster_count == 1
    assert after_audit.passes_quality_gate is False
    assert repeated_quality.snapshot_id == after_audit.snapshot_id
    quality_snapshot = session.get(
        ProblemClusteringQualitySnapshot,
        after_audit.snapshot_id,
    )
    assert quality_snapshot is not None
    assert quality_snapshot.member_purity == Decimal("1.000000")
    assert quality_snapshot.purity_confidence_lower is not None
    with pytest.raises(ProblemClusteringError, match="future"):
        ProblemClusteringEngine(session).cluster(
            as_of=datetime.now(UTC) + timedelta(days=1)
        )

    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        problem_clustering_api_enabled=True,
        problem_cluster_review_api_enabled=True,
        metrics_api_enabled=True,
    )
    with TestClient(app) as client:
        run_response = client.post("/problem-clustering-runs", json={})
        assert run_response.status_code == 201
        assert run_response.json()["id"] == str(first.run_id)
        cluster_response = client.get(
            "/problem-clusters",
            params={
                "run_id": str(first.run_id),
                "status": "cross_entity_candidate",
            },
        )
        assert cluster_response.status_code == 200
        assert len(cluster_response.json()) == 1
        member_response = client.get(
            f"/problem-clusters/{cross_project.id}/members"
        )
        assert member_response.status_code == 200
        assert len(member_response.json()) == 2
        claim_run_response = client.post(
            f"/problem-clustering-runs/{first.run_id}/claims"
        )
        assert claim_run_response.status_code == 201
        assert claim_run_response.json()["reused_count"] == 1
        claim_response = client.get(
            "/evidence-claims",
            params={"cluster_id": str(cross_project.id)},
        )
        assert claim_response.status_code == 200
        assert len(claim_response.json()) == 1
        assert claim_response.json()[0]["id"] == str(claim.id)
        claim_evidence_response = client.get(
            f"/evidence-claims/{claim.id}/evidence"
        )
        assert claim_evidence_response.status_code == 200
        assert len(claim_evidence_response.json()) == 2
        metric_run_response = client.post(
            "/problem-cluster-metric-runs",
            json={"clustering_run_id": str(first.run_id)},
        )
        assert metric_run_response.status_code == 201
        assert metric_run_response.json()["id"] == str(metric_run.run_id)
        metric_response = client.get(
            f"/problem-cluster-metric-runs/{metric_run.run_id}/observations",
            params={"cluster_id": str(cross_project.id)},
        )
        assert metric_response.status_code == 200
        assert len(metric_response.json()) == len(CLUSTER_METRIC_SPECS)
        audit_response = client.post(
            f"/problem-clusters/{cross_project.id}/audits",
            json={
                "reviewer": "second-reviewer",
                "verdict": "mixed",
                "sample_method": "all_members",
                "sampled_member_count": 2,
                "coherent_member_count": 1,
                "notes": "Second pass found one ambiguous member.",
            },
        )
        assert audit_response.status_code == 201
        assert audit_response.json()["supersedes_audit_id"] == str(audit.id)
        quality_response = client.post(
            f"/problem-clustering-runs/{first.run_id}/quality-snapshots"
        )
        assert quality_response.status_code == 201
        assert quality_response.json()["status"] == "insufficient_audits"
        assert quality_response.json()["member_purity"] == "0.500000"

    new_item = work_items(count=1, start_id=99)
    new_item[0].payload["title"] = "Database migration lock waits forever"
    new_item[0].payload["repository_url"] = (
        "https://api.github.com/repos/another/radar"
    )
    await ingest_and_normalize(
        session,
        FileObjectStore(tmp_path),
        new_item,
    )
    GitHubProblemEvidenceExtractor(session).extract_pending()
    current = ProblemClusteringEngine(session).cluster()
    lineage = ProblemClusterLineageService(session).compare(
        first.run_id,
        current.run_id,
    )
    repeated_lineage = ProblemClusterLineageService(session).compare(
        first.run_id,
        current.run_id,
    )

    assert current.run_id != first.run_id
    assert lineage.status == "insufficient_history"
    assert lineage.matched_cluster_count == 1
    assert lineage.stable_cluster_count == 1
    assert lineage.new_cluster_count == 0
    assert lineage.disappeared_cluster_count == 0
    assert lineage.passes_stability_gate is False
    assert repeated_lineage.run_id == lineage.run_id
    relation = session.scalar(
        select(ProblemClusterLineage).where(
            ProblemClusterLineage.lineage_run_id == lineage.run_id
        )
    )
    assert relation is not None
    assert relation.relation_type == "stable"
    assert relation.member_jaccard == Decimal("1.000000")

    eligibility = OpportunityEligibilityService(session).evaluate(
        current.run_id
    )
    repeated_eligibility = OpportunityEligibilityService(session).evaluate(
        current.run_id
    )
    assert eligibility.status == "succeeded"
    assert eligibility.evaluated_cluster_count == 1
    assert eligibility.eligible_cluster_count == 0
    assert eligibility.excluded_cluster_count == 1
    assert repeated_eligibility.run_id == eligibility.run_id
    decision = session.scalar(
        select(OpportunityEligibilityDecision).where(
            OpportunityEligibilityDecision.run_id == eligibility.run_id
        )
    )
    assert decision is not None
    assert decision.eligible is False
    assert "missing_cluster_quality_snapshot" in decision.blocker_codes
    assert "cluster_stability:insufficient_history" in decision.blocker_codes
    assert "missing_cluster_audit" in decision.blocker_codes
    assert "base_metrics_not_measured" in decision.blocker_codes
    assert "independent_source_evidence_required" in decision.blocker_codes
    assert "independent_demand_evidence_required" in decision.blocker_codes
    assert "direct_payment_evidence_required" in decision.blocker_codes

    lineage_app = create_app()
    lineage_app.dependency_overrides[get_db_session] = lambda: session
    lineage_app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        metrics_api_enabled=True,
    )
    with TestClient(lineage_app) as client:
        lineage_response = client.post(
            "/problem-cluster-lineage-runs",
            json={
                "previous_clustering_run_id": str(first.run_id),
                "current_clustering_run_id": str(current.run_id),
            },
        )
        assert lineage_response.status_code == 201
        assert lineage_response.json()["id"] == str(lineage.run_id)
        relations_response = client.get(
            f"/problem-cluster-lineage-runs/{lineage.run_id}/relations"
        )
        assert relations_response.status_code == 200
        assert len(relations_response.json()) == 1
        eligibility_response = client.post(
            "/opportunity-eligibility-runs",
            json={"clustering_run_id": str(current.run_id)},
        )
        assert eligibility_response.status_code == 201
        assert eligibility_response.json()["id"] == str(eligibility.run_id)
        decisions_response = client.get(
            f"/opportunity-eligibility-runs/{eligibility.run_id}/decisions",
            params={"eligible": False},
        )
        assert decisions_response.status_code == 200
        assert len(decisions_response.json()) == 1
        assert decisions_response.json()[0]["eligible"] is False
