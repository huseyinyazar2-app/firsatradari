import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
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
from firsat_radari.connectors.registry import (
    ConnectorRegistryError,
    validate_discovery_query,
)
from firsat_radari.connectors.stack_exchange import StackExchangeConnector
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    ClaimCommercialOutcomeLink,
    CommercialOutcome,
    CommercialOutcomeReview,
    DataSource,
    Entity,
    EvidenceClaim,
    EvidenceClaimReview,
    MetricDefinition,
    OpportunityEligibilityDecision,
    ProblemCluster,
    ProblemClusterMetricObservation,
    Repository,
    StackExchangeQuestion,
)
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.main import create_app
from firsat_radari.metrics.problem_clusters import ProblemClusterMetricEngine
from firsat_radari.normalization.github_work_items import (
    GitHubWorkItemNormalizer,
)
from firsat_radari.normalization.service import NormalizationService
from firsat_radari.normalization.stack_exchange import (
    StackExchangeQuestionNormalizer,
)
from firsat_radari.opportunities.eligibility import (
    OpportunityEligibilityService,
)
from firsat_radari.problem_mining.clustering import ProblemClusteringEngine
from firsat_radari.problem_mining.github import (
    GitHubProblemEvidenceExtractor,
)
from firsat_radari.problem_mining.stack_exchange import (
    StackExchangeProblemEvidenceExtractor,
)
from firsat_radari.storage.filesystem import FileObjectStore


class SnapshotConnector(DataConnector):
    version = "stack-exchange-test-1"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=False,
        incremental=False,
        historical=True,
        deletions=False,
        conditional_requests=False,
        pagination="none",
        rate_limit_headers=False,
        source_timestamps=True,
    )

    def __init__(
        self,
        source_key: str,
        job_type: str,
        items: list[RawItem],
    ) -> None:
        self.source_key = source_key
        self.job_type = job_type
        self._items = items

    async def discover(
        self,
        query: dict,
        checkpoint: dict | None = None,
    ) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=self._items,
            is_complete=True,
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
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with session_factory() as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.asyncio
async def test_stack_exchange_connector_pages_and_minimizes_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/2.3/questions"
        assert request.url.params["site"] == "stackoverflow"
        assert request.url.params["tagged"] == "postgresql;sqlalchemy"
        assert request.url.params["page"] == "2"
        assert request.url.params["pagesize"] == "50"
        assert request.url.params["filter"] == "withbody"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "question_id": 42,
                        "title": "Migration lock waits forever",
                        "body": "<p>How can I avoid this?</p>",
                        "link": "https://stackoverflow.com/questions/42",
                        "tags": ["postgresql"],
                        "owner": {
                            "user_id": 99,
                            "display_name": "not-retained",
                        },
                        "creation_date": 1_700_000_000,
                        "last_activity_date": 1_700_000_100,
                    }
                ],
                "has_more": True,
                "quota_remaining": 9_999,
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.stackexchange.test",
    )
    result = await StackExchangeConnector(client=client).discover(
        {
            "site": "stackoverflow",
            "tags": ["postgresql", "sqlalchemy"],
            "from_date": "2026-07-01",
            "to_date": "2026-07-31",
            "sort": "creation",
            "order": "asc",
            "page_size": 50,
        },
        checkpoint={"page": 2},
    )

    assert result.status is CollectionStatus.SUCCEEDED
    assert result.checkpoint == {"page": 3}
    assert result.is_complete is False
    assert result.rate_limit_remaining == 9_999
    assert result.items[0].external_id == "stackoverflow:42"
    assert "owner" not in result.items[0].payload
    await client.aclose()


@pytest.mark.asyncio
async def test_stack_exchange_connector_honors_api_backoff() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "items": [],
                    "has_more": True,
                    "backoff": 12,
                    "quota_remaining": 50,
                },
            )
        ),
        base_url="https://api.stackexchange.test",
    )
    result = await StackExchangeConnector(client=client).discover(
        {
            "site": "stackoverflow",
            "tags": ["python"],
            "from_date": "2026-07-01",
            "to_date": "2026-07-02",
        }
    )

    assert result.status is CollectionStatus.RATE_LIMITED
    assert result.errors == ["api_backoff"]
    assert result.checkpoint == {"page": 2}
    assert result.rate_limit_reset_at is not None
    await client.aclose()


def test_stack_exchange_query_requires_bounded_date_window() -> None:
    with pytest.raises(ConnectorRegistryError, match="31 days"):
        validate_discovery_query(
            "stack_exchange_questions",
            {
                "site": "stackoverflow",
                "tags": ["python"],
                "from_date": "2026-01-01",
                "to_date": "2026-07-01",
            },
        )


@pytest.mark.asyncio
async def test_stack_exchange_adds_measured_independent_demand_signal(
    session: Session,
    tmp_path: Path,
) -> None:
    github = _source(
        key="github",
        family="developer_repository_activity",
    )
    stack_exchange = _source(
        key="stack_exchange",
        family="technical_q_and_a",
    )
    repository_entity = Entity(
        entity_type="repository",
        canonical_name="example/radar",
        canonical_url="https://github.com/example/radar",
        status="active",
    )
    session.add_all([github, stack_exchange, repository_entity])
    session.flush()
    session.add(
        Repository(
            id=repository_entity.id,
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
    )
    session.commit()
    store = FileObjectStore(tmp_path)
    observed_at = datetime.now(UTC)
    title = "Database migration lock waits forever"
    github_items = [
        RawItem(
            external_type="repository_work_item",
            external_id=str(item_id),
            payload={
                "id": item_id,
                "number": item_id,
                "repository_url": (
                    "https://api.github.com/repos/example/radar"
                ),
                "html_url": (
                    f"https://github.com/example/radar/issues/{item_id}"
                ),
                "title": title,
                "body": "This blocker takes hours of work every time.",
                "state": "open",
                "labels": [{"name": "bug"}],
                "comments": 2,
                "author_association": "NONE",
                "user": {"login": f"user-{item_id}", "type": "User"},
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-02T00:00:00Z",
                "closed_at": None,
            },
            observed_at=observed_at,
            source_created_at=datetime(2026, 7, 1, tzinfo=UTC),
            source_updated_at=datetime(2026, 7, 2, tzinfo=UTC),
        )
        for item_id in range(1, 5)
    ]
    await IngestionService(session, store).discover(
        SnapshotConnector(
            "github",
            "github_work_items",
            github_items,
        ),
        {"q": "repo:example/radar"},
    )
    NormalizationService(session, store).normalize_pending(
        GitHubWorkItemNormalizer()
    )
    GitHubProblemEvidenceExtractor(session).extract_pending()

    stack_item = RawItem(
        external_type="stack_exchange_question",
        external_id="stackoverflow:9001",
        payload={
            "site": "stackoverflow",
            "question_id": 9001,
            "title": title,
            "body": (
                "<p>This blocker takes hours of work every time. "
                "We need a reliable workaround.</p>"
            ),
            "link": "https://stackoverflow.com/questions/9001/example",
            "tags": ["postgresql", "database"],
            "creation_date": 1_751_328_000,
            "last_activity_date": 1_751_414_400,
            "answer_count": 0,
            "is_answered": False,
            "view_count": 800,
            "score": 12,
            "content_license": "CC BY-SA 4.0",
        },
        observed_at=observed_at,
        source_created_at=datetime(2025, 7, 1, tzinfo=UTC),
        source_updated_at=datetime(2025, 7, 2, tzinfo=UTC),
    )
    await IngestionService(session, store).discover(
        SnapshotConnector(
            "stack_exchange",
            "stack_exchange_questions",
            [stack_item],
        ),
        {
            "site": "stackoverflow",
            "tags": ["postgresql"],
            "from_date": "2025-07-01",
            "to_date": "2025-07-02",
        },
    )
    normalized = NormalizationService(
        session,
        store,
    ).normalize_pending(StackExchangeQuestionNormalizer())
    extracted = StackExchangeProblemEvidenceExtractor(
        session
    ).extract_pending()

    assert normalized.success_count == 1
    assert extracted.success_count == 1
    question = session.scalar(select(StackExchangeQuestion))
    assert question is not None
    assert "<p>" not in question.body
    assert question.content_license == "CC BY-SA 4.0"
    assert question.bounty_amount is None

    clustering = ProblemClusteringEngine(session).cluster()
    cluster = session.scalar(
        select(ProblemCluster).where(
            ProblemCluster.run_id == clustering.run_id,
            ProblemCluster.status == "cross_entity_candidate",
        )
    )
    assert cluster is not None
    assert cluster.document_count == 5
    assert cluster.entity_count == 2
    assert cluster.source_count == 2

    metric_run = ProblemClusterMetricEngine(session).calculate(
        clustering.run_id
    )
    demand_observation = session.scalar(
        select(ProblemClusterMetricObservation)
        .join(
            MetricDefinition,
            MetricDefinition.id
            == ProblemClusterMetricObservation.metric_definition_id,
        )
        .where(
            ProblemClusterMetricObservation.run_id == metric_run.run_id,
            ProblemClusterMetricObservation.cluster_id == cluster.id,
            MetricDefinition.key
            == "cluster.independent_demand_signal_rate",
        )
    )
    assert demand_observation is not None
    assert demand_observation.status == "measured"
    assert demand_observation.numerator == 1
    assert demand_observation.denominator == 5
    assert demand_observation.value == Decimal("0.200000")
    assert demand_observation.calculation["evidence_level"] == "E2"

    eligibility = OpportunityEligibilityService(session).evaluate(
        clustering.run_id
    )
    decision = session.scalar(
        select(OpportunityEligibilityDecision).where(
            OpportunityEligibilityDecision.run_id == eligibility.run_id
        )
    )
    assert decision is not None
    assert "independent_demand_evidence_required" not in decision.blocker_codes
    assert "independent_demand_signal_absent" not in decision.blocker_codes
    assert "direct_payment_evidence_required" in decision.blocker_codes

    validation_app = create_app()
    validation_app.dependency_overrides[get_db_session] = lambda: session
    validation_app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        commercial_validation_api_enabled=True,
        validation_hash_secret="test-validation-secret-32-chars",
    )
    experiment_payload = {
        "cluster_id": str(cluster.id),
        "external_key": "validation:database-lock:001",
        "experiment_type": "pre_sale",
        "target_segment": "Teams operating PostgreSQL migrations",
        "hypothesis": "Teams will prepay for reliable lock diagnostics.",
        "status": "running",
        "started_at": observed_at.isoformat(),
        "created_by": "validation-owner",
    }
    outcome_payload = {
        "idempotency_key": "prepayment:001",
        "participant_key": "crm:account:1001",
        "outcome_type": "prepayment",
        "amount": "250.00",
        "currency": "USD",
        "evidence_reference": "invoice:demo:001",
        "notes": "Pre-sale validation payment.",
        "occurred_at": observed_at.isoformat(),
        "created_by": "validation-owner",
    }
    with TestClient(validation_app) as client:
        experiment_response = client.post(
            "/commercial-validation-experiments",
            json=experiment_payload,
        )
        assert experiment_response.status_code == 201
        experiment_id = experiment_response.json()["id"]
        outcome_response = client.post(
            f"/commercial-validation-experiments/{experiment_id}/outcomes",
            json=outcome_payload,
        )
        assert outcome_response.status_code == 201
        outcome_id = outcome_response.json()["id"]
        assert "participant_key_hash" not in outcome_response.json()
        repeated_outcome = client.post(
            f"/commercial-validation-experiments/{experiment_id}/outcomes",
            json=outcome_payload,
        )
        assert repeated_outcome.status_code == 201
        assert repeated_outcome.json()["id"] == outcome_id
        review_response = client.patch(
            f"/commercial-outcomes/{outcome_id}/review",
            json={
                "new_status": "verified",
                "reviewer": "commercial-auditor",
                "notes": "Invoice reference checked.",
            },
        )
        assert review_response.status_code == 200
        assert review_response.json()["verification_status"] == "verified"
        reviews_response = client.get(
            f"/commercial-outcomes/{outcome_id}/reviews"
        )
        assert reviews_response.status_code == 200
        assert len(reviews_response.json()) == 1
        preference_response = client.post(
            "/commercial-contact-preferences",
            json={
                "participant_key": "crm:account:1001",
                "channel": "email",
                "scope": "validation:database-lock",
                "status": "opt_out",
                "evidence_reference": "crm:preference:001",
                "recorded_by": "validation-owner",
            },
        )
        assert preference_response.status_code == 201
        assert "participant_key_hash" not in preference_response.json()
        close_response = client.patch(
            f"/commercial-validation-experiments/{experiment_id}",
            json={
                "status": "completed",
                "ended_at": observed_at.isoformat(),
            },
        )
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "completed"

    stored_outcome = session.get(CommercialOutcome, uuid.UUID(outcome_id))
    assert stored_outcome is not None
    assert stored_outcome.participant_key_hash != "crm:account:1001"
    assert len(stored_outcome.participant_key_hash) == 64
    assert (
        len(list(session.scalars(select(CommercialOutcomeReview)))) == 1
    )

    paid_metric_run = ProblemClusterMetricEngine(session).calculate(
        clustering.run_id
    )
    assert paid_metric_run.run_id != metric_run.run_id
    direct_payment = session.scalar(
        select(ProblemClusterMetricObservation)
        .join(
            MetricDefinition,
            MetricDefinition.id
            == ProblemClusterMetricObservation.metric_definition_id,
        )
        .where(
            ProblemClusterMetricObservation.run_id
            == paid_metric_run.run_id,
            ProblemClusterMetricObservation.cluster_id == cluster.id,
            MetricDefinition.key
            == "cluster.direct_payment_evidence_rate",
        )
    )
    assert direct_payment is not None
    assert direct_payment.status == "measured"
    assert direct_payment.numerator == Decimal("1.000000")
    assert direct_payment.denominator == Decimal("1.000000")
    assert direct_payment.value == Decimal("1.000000")
    assert (
        direct_payment.calculation["commercial_evidence_level"] == "E5"
    )

    paid_eligibility = OpportunityEligibilityService(session).evaluate(
        clustering.run_id
    )
    assert paid_eligibility.run_id != eligibility.run_id
    paid_decision = session.scalar(
        select(OpportunityEligibilityDecision).where(
            OpportunityEligibilityDecision.run_id
            == paid_eligibility.run_id
        )
    )
    assert paid_decision is not None
    assert "direct_payment_evidence_required" not in (
        paid_decision.blocker_codes
    )
    assert "direct_payment_signal_absent" not in paid_decision.blocker_codes

    validation_app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        ontology_claim_api_enabled=True,
    )
    with TestClient(validation_app) as client:
        draft_response = client.post(
            f"/problem-clusters/{cluster.id}/ontology-drafts"
        )
        assert draft_response.status_code == 201
        draft_payload = draft_response.json()
        assert draft_payload["missing_claim_types"] == []
        expected_types = {
            "customer_segment",
            "job_to_be_done",
            "problem_context",
            "current_alternative",
            "solution_gap",
            "payment_reason",
        }
        assert set(draft_payload["claim_ids"]) == expected_types
        first_claim_id = next(iter(draft_payload["claim_ids"].values()))
        self_review = client.post(
            f"/evidence-claims/{first_claim_id}/reviews",
            json={
                "version": "critic-v1",
                "decision": "approved",
                "reviewer": "system:ontology-extractor",
                "rationale": "Self review must be rejected.",
            },
        )
        assert self_review.status_code == 409
        for claim_type, claim_id in draft_payload["claim_ids"].items():
            reviewed = client.post(
                f"/evidence-claims/{claim_id}/reviews",
                json={
                    "version": "critic-v1",
                    "decision": "approved",
                    "reviewer": "ontology-critic",
                    "rationale": (
                        f"Source links for {claim_type} were checked."
                    ),
                },
            )
            assert reviewed.status_code == 201
        payment_claim_id = draft_payload["claim_ids"]["payment_reason"]
        commercial_links = client.get(
            f"/evidence-claims/{payment_claim_id}/commercial-evidence"
        )
        assert commercial_links.status_code == 200
        assert len(commercial_links.json()) == 1
        customer_claim_id = draft_payload["claim_ids"]["customer_segment"]
        customer_evidence = client.get(
            f"/evidence-claims/{customer_claim_id}/evidence"
        ).json()
        counter_claim = client.post(
            "/ontology-claims",
            json={
                "cluster_id": str(cluster.id),
                "claim_type": "distribution_path",
                "statement": "A disputed distribution-path hypothesis.",
                "supporting_problem_evidence_ids": [
                    customer_evidence[0]["problem_evidence_id"]
                ],
                "refuting_problem_evidence_ids": [
                    customer_evidence[1]["problem_evidence_id"]
                ],
                "commercial_outcome_ids": [],
                "generator_key": "test-hypothesis-generator",
                "generator_version": "1",
                "created_by": "hypothesis-generator",
            },
        )
        assert counter_claim.status_code == 201
        blocked_review = client.post(
            f"/evidence-claims/{counter_claim.json()['id']}/reviews",
            json={
                "version": "critic-v1",
                "decision": "approved",
                "reviewer": "ontology-critic",
                "rationale": "Counter-evidence must block approval.",
            },
        )
        assert blocked_review.status_code == 409

    reviewed_claims = list(
        session.scalars(
            select(EvidenceClaim).where(
                EvidenceClaim.cluster_id == cluster.id,
                EvidenceClaim.claim_type.in_(expected_types),
            )
        )
    )
    assert len(reviewed_claims) == 6
    assert all(claim.status == "grounded" for claim in reviewed_claims)
    assert all(claim.is_current for claim in reviewed_claims)
    assert len(list(session.scalars(select(EvidenceClaimReview)))) == 6
    assert (
        len(
            list(
                session.scalars(
                    select(ClaimCommercialOutcomeLink).where(
                        ClaimCommercialOutcomeLink.claim_id
                        == uuid.UUID(payment_claim_id)
                    )
                )
            )
        )
        == 1
    )


def _source(*, key: str, family: str) -> DataSource:
    return DataSource(
        key=key,
        source_type="test",
        evidence_family_key=family,
        independence_group_key=key,
        independence_status="independent",
        owner=key,
        base_url=f"https://{key}.example.test",
        policy_status="approved",
        policy_version="test-policy",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission="allowed",
        llm_processing_permission="prohibited",
        retention_days=30,
        enabled=True,
    )
