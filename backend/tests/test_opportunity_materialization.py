import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    ClaimEvidenceLink,
    CommercialOutcome,
    CommercialValidationExperiment,
    DataSource,
    EvidenceClaim,
    EvidenceClaimReview,
    MetricDefinition,
    Opportunity,
    OpportunityComponentClaimLink,
    OpportunityEligibilityDecision,
    OpportunityEligibilityRun,
    OpportunityVersion,
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
)
from firsat_radari.main import create_app
from firsat_radari.opportunities.materialization import (
    REQUIRED_COMPONENT_CLAIM_TYPES,
    GroundedOpportunityInput,
    OpportunityMaterializationError,
    OpportunityMaterializationService,
)
from firsat_radari.opportunities.scoring import OpportunityScoringService
from firsat_radari.profiles.service import (
    ProfileEvaluationInput,
    ProfileInput,
    ResearchProfileService,
    VerticalInput,
)


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


def test_only_complete_grounded_ontology_creates_a_version(
    session: Session,
) -> None:
    now = datetime.now(UTC)
    clustering_run = ProblemClusteringRun(
        algorithm_key="test",
        algorithm_version="1",
        input_fingerprint="a" * 64,
        input_definition={},
        as_of=now,
        status="succeeded",
        started_at=now,
        finished_at=now,
        input_count=10,
        eligible_count=10,
        cluster_count=1,
        singleton_count=0,
        error_count=0,
    )
    session.add(clustering_run)
    session.flush()
    cluster = ProblemCluster(
        run_id=clustering_run.id,
        fingerprint="b" * 64,
        signature=["database", "lock"],
        label="database lock",
        status="cross_entity_candidate",
        representative_evidence_id=uuid.uuid4(),
        document_count=10,
        entity_count=5,
        source_count=2,
        cohesion_min=Decimal("0.8"),
        cohesion_mean=Decimal("0.9"),
        first_source_created_at=now,
        last_source_created_at=now,
        created_at=now,
    )
    source = DataSource(
        key="test-source",
        source_type="test",
        evidence_family_key="demand",
        independence_group_key="test-source",
        independence_status="independent",
        owner="Test",
        base_url="https://example.test",
        policy_status="approved",
        policy_version="1",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission="allowed",
        llm_processing_permission="prohibited",
        retention_days=30,
        enabled=True,
    )
    session.add_all([cluster, source])
    session.flush()
    eligibility_run = OpportunityEligibilityRun(
        clustering_run_id=clustering_run.id,
        gate_version="1",
        input_fingerprint="c" * 64,
        status="succeeded",
        evaluated_cluster_count=1,
        eligible_cluster_count=1,
        excluded_cluster_count=0,
        started_at=now,
        finished_at=now,
    )
    session.add(eligibility_run)
    session.flush()
    decision = OpportunityEligibilityDecision(
        run_id=eligibility_run.id,
        cluster_id=cluster.id,
        eligible=True,
        evidence_level="E2",
        blocker_codes=[],
        details={},
        decided_at=now,
    )
    session.add(decision)
    session.flush()
    claim_ids: dict[str, uuid.UUID] = {}
    for index, (component_key, claim_type) in enumerate(
        REQUIRED_COMPONENT_CLAIM_TYPES.items(),
        start=1,
    ):
        claim = EvidenceClaim(
            cluster_id=cluster.id,
            supersedes_claim_id=None,
            claim_type=claim_type,
            statement=f"Grounded {component_key} statement",
            status="grounded",
            generator_key="test",
            generator_version="1",
            input_fingerprint=f"{index:064x}",
            evidence_level="E2" if component_key == "problem" else "E1",
            source_count=2,
            independence_group_count=2,
            supporting_evidence_count=1,
            independence_blockers=[],
            is_current=True,
            created_by="claim-generator",
            created_at=now,
        )
        session.add(claim)
        session.flush()
        session.add(
            ClaimEvidenceLink(
                claim_id=claim.id,
                problem_evidence_id=uuid.uuid4(),
                source_id=source.id,
                direction="supports",
                created_at=now,
            )
        )
        if component_key != "expansion_path":
            session.add(
                EvidenceClaimReview(
                    claim_id=claim.id,
                    version="review-v1",
                    previous_status="pending_review",
                    decision="approved",
                    reviewer="claim-critic",
                    rationale="Source link and statement were checked.",
                    reviewed_at=now,
                )
            )
        claim_ids[component_key] = claim.id
    session.commit()
    service = OpportunityMaterializationService(session)

    with pytest.raises(
        OpportunityMaterializationError,
        match="ontology is incomplete",
    ):
        service.materialize(
            GroundedOpportunityInput(
                eligibility_decision_id=decision.id,
                component_claim_ids={"problem": claim_ids["problem"]},
                created_by="test",
            )
        )
    assert session.scalar(select(func.count()).select_from(Opportunity)) == 0

    candidate = GroundedOpportunityInput(
        eligibility_decision_id=decision.id,
        component_claim_ids=claim_ids,
        created_by="research-pipeline",
    )
    with pytest.raises(
        OpportunityMaterializationError,
        match="lacks critic approval",
    ):
        service.materialize(candidate)
    session.add(
        EvidenceClaimReview(
            claim_id=claim_ids["expansion_path"],
            version="review-v1",
            previous_status="pending_review",
            decision="approved",
            reviewer="claim-critic",
            rationale="Source link and statement were checked.",
            reviewed_at=now,
        )
    )
    session.commit()
    created = service.materialize(candidate)
    repeated = service.materialize(candidate)

    assert created.created is True
    assert repeated.created is False
    assert repeated.version_id == created.version_id
    version = session.get(OpportunityVersion, created.version_id)
    assert version is not None
    assert version.version_number == 1
    assert version.status == "candidate"
    assert version.evidence_level == "E2"
    assert set(version.ontology) == set(REQUIRED_COMPONENT_CLAIM_TYPES)
    assert (
        session.scalar(
            select(func.count()).select_from(
                OpportunityComponentClaimLink
            )
        )
        == len(REQUIRED_COMPONENT_CLAIM_TYPES)
    )
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
    )
    payload = {
        "eligibility_decision_id": str(decision.id),
        "component_claim_ids": {
            key: str(claim_id) for key, claim_id in claim_ids.items()
        },
        "created_by": "research-pipeline",
    }
    with TestClient(app) as client:
        disabled = client.post("/opportunity-versions", json=payload)
        assert disabled.status_code == 503
        app.dependency_overrides[get_settings] = lambda: Settings(
            environment="test",
            opportunity_materialization_api_enabled=True,
        )
        api_result = client.post("/opportunity-versions", json=payload)
        listed = client.get("/opportunities")
        versions = client.get(
            f"/opportunities/{created.opportunity_id}/versions"
        )

    assert api_result.status_code == 201
    assert api_result.json()["id"] == str(created.version_id)
    assert len(listed.json()) == 1
    assert len(versions.json()) == 1

    historical_cutoff = datetime.now(UTC) - timedelta(days=60)
    version.created_at = historical_cutoff - timedelta(days=1)
    decision.decided_at = historical_cutoff - timedelta(days=1)
    metric_run = ProblemClusterMetricRun(
        clustering_run_id=clustering_run.id,
        definition_set_version="test-score-v1",
        input_fingerprint="d" * 64,
        as_of=historical_cutoff - timedelta(days=1),
        status="succeeded",
        started_at=historical_cutoff - timedelta(days=2),
        finished_at=historical_cutoff - timedelta(days=1),
        cluster_count=1,
        metric_count=5,
        error_count=0,
    )
    session.add(metric_run)
    session.flush()
    metric_values = {
        "cluster.independent_demand_signal_rate": "0.70",
        "cluster.direct_payment_evidence_rate": "0.60",
        "cluster.economic_impact_rate": "0.80",
        "cluster.problem_mention_rate": "0.50",
        "cluster.problem_entity_spread": "0.40",
    }
    for metric_key, metric_value in metric_values.items():
        definition = MetricDefinition(
            key=metric_key,
            version="score-test",
            name=metric_key,
            description="test",
            unit="ratio",
            numerator_description="test",
            denominator_description="test",
            minimum_sample_size=5,
            window_days=None,
            comparison_group_description="test",
            freshness_policy="test",
            confidence_method="wilson_95",
            missing_data_policy="no_value",
            outlier_policy="none",
            active=True,
        )
        session.add(definition)
        session.flush()
        session.add(
            ProblemClusterMetricObservation(
                run_id=metric_run.id,
                metric_definition_id=definition.id,
                cluster_id=cluster.id,
                as_of=metric_run.as_of,
                numerator=Decimal("14"),
                denominator=Decimal("20"),
                value=Decimal(metric_value),
                unit="ratio",
                sample_size=30,
                status="measured",
                confidence_lower=Decimal(metric_value) - Decimal("0.05"),
                confidence_upper=Decimal(metric_value) + Decimal("0.05"),
                calculation={"evidence_level": "E2"},
                created_at=metric_run.as_of,
            )
        )
    decision.details = {
        "cluster_metric_run_id": str(metric_run.id),
    }
    session.commit()

    profile_service = ResearchProfileService(session)
    vertical = profile_service.create_vertical(
        VerticalInput(
            key="software",
            version="1.0.0",
            name="Software",
            status="active",
            config={},
            selection_rationale="Test vertical",
            created_by="test",
        )
    )
    research_profile = profile_service.create_profile(
        ProfileInput(
            vertical_definition_id=vertical.id,
            key="solo-founder",
            version="1.0.0",
            name="Solo founder",
            status="active",
            constraints={},
            exclusions={"categories": ["game"]},
            preferences={},
            created_by="test",
        )
    )
    profile_evaluation = profile_service.evaluate(
        ProfileEvaluationInput(
            opportunity_version_id=version.id,
            research_profile_id=research_profile.id,
            observed_attributes={"category": "saas"},
            evaluated_by="test",
        )
    )
    profile_evaluation.evaluated_at = historical_cutoff - timedelta(days=1)
    session.commit()

    scoring = OpportunityScoringService(session)
    score_outcome = scoring.score(
        as_of=historical_cutoff,
        research_profile_id=research_profile.id,
    )
    repeated_score = scoring.score(
        as_of=historical_cutoff,
        research_profile_id=research_profile.id,
    )
    assert repeated_score.run_id == score_outcome.run_id
    assert score_outcome.rankable_count == 1
    ranking = scoring.rank(score_outcome.run_id)
    assert ranking.ranked_count == 1
    backtest = scoring.backtest(
        score_outcome.run_id,
        outcome_window_days=30,
    )
    assert backtest.status == "insufficient_sample"
    assert backtest.evaluated_count == 1

    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        scoring_api_enabled=True,
    )
    with TestClient(app) as client:
        score_response = client.post(
            "/opportunity-score-runs",
            json={
                "as_of": historical_cutoff.isoformat(),
                "research_profile_id": str(research_profile.id),
            },
        )
        assert score_response.status_code == 201
        assert score_response.json()["rankable_count"] == 1
        snapshots_response = client.get(
            f"/opportunity-score-runs/{score_outcome.run_id}/snapshots"
        )
        assert snapshots_response.status_code == 200
        assert snapshots_response.json()[0]["status"] == "rankable"
        ranking_response = client.post(
            f"/opportunity-score-runs/{score_outcome.run_id}/ranking"
        )
        assert ranking_response.status_code == 201
        backtest_response = client.post(
            "/backtest-runs",
            json={
                "score_run_id": str(score_outcome.run_id),
                "outcome_window_days": 30,
            },
        )
        assert backtest_response.status_code == 201
        assert backtest_response.json()["status"] == "insufficient_sample"

        app.dependency_overrides[get_settings] = lambda: Settings(
            environment="test",
            research_review_api_enabled=True,
            research_api_enabled=True,
            sales_export_api_enabled=True,
        )
        review_response = client.post(
            f"/opportunity-versions/{version.id}/reviews",
            json={
                "decision": "validate",
                "reviewer": "research-owner",
                "notes": "Kanıt paketi saha doğrulamasına hazır.",
            },
        )
        assert review_response.status_code == 201
        research_response = client.post(
            f"/opportunity-versions/{version.id}/research-runs",
            json={
                "research_tier": "validation_ready",
                "focus_questions": [
                    "Hangi en ucuz test belirsizliği en hızlı azaltır?"
                ],
                "requested_by": "research-owner",
            },
        )
        assert research_response.status_code == 201
        assert research_response.json()["status"] == "succeeded"
        assert research_response.json()["findings"][
            "recommended_next_test"
        ] == "price_test"
        research_id = research_response.json()["id"]
        export_response = client.post(
            "/opportunity-exports",
            json={
                "opportunity_version_id": str(version.id),
                "research_run_id": research_id,
                "destination": "sales-partner",
                "idempotency_key": "sales-partner:test:001",
                "created_by": "research-owner",
            },
        )
        assert export_response.status_code == 201
        export_payload = export_response.json()
        assert export_payload["status"] == "prepared"
        assert "participant_key_hash" not in str(export_payload["payload"])
        acknowledged = client.patch(
            f"/opportunity-exports/{export_payload['id']}/acknowledge",
            json={"external_reference": "sales-partner:lead:001"},
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["status"] == "exported"

        refuting_link = session.scalar(
            select(ClaimEvidenceLink).where(
                ClaimEvidenceLink.claim_id == claim_ids["problem"]
            )
        )
        assert refuting_link is not None
        refuting_link.direction = "refutes"
        legacy_experiment = CommercialValidationExperiment(
            cluster_id=cluster.id,
            opportunity_version_id=None,
            external_key="legacy-cluster-experiment",
            protocol_key="legacy-v1",
            cohort="radar",
            experiment_type="customer_interview",
            target_segment="Legacy cluster segment",
            hypothesis="Must not leak into a versioned research run",
            status="completed",
            started_at=historical_cutoff + timedelta(days=1),
            ended_at=historical_cutoff + timedelta(days=3),
            created_by="test",
            created_at=historical_cutoff + timedelta(days=1),
        )
        session.add(legacy_experiment)
        session.flush()
        session.add(
            CommercialOutcome(
                experiment_id=legacy_experiment.id,
                idempotency_key="legacy-outcome",
                participant_key_hash="f" * 64,
                outcome_type="sale",
                direction="supports",
                amount=Decimal("100"),
                currency="USD",
                evidence_reference="crm:legacy",
                notes="Legacy cluster outcome",
                verification_status="verified",
                occurred_at=historical_cutoff + timedelta(days=2),
                created_by="test",
                created_at=historical_cutoff + timedelta(days=2),
                verified_at=historical_cutoff + timedelta(days=3),
                verifier="test",
                verification_notes="verified",
            )
        )
        session.commit()
        assert (
            scoring._future_outcome_count(
                version.id,
                historical_cutoff,
                historical_cutoff + timedelta(days=30),
            )
            == 0
        )
        risk_research = client.post(
            f"/opportunity-versions/{version.id}/research-runs",
            json={
                "research_tier": "validation_ready",
                "focus_questions": ["Karşı kanıt ne söylüyor?"],
                "requested_by": "research-owner",
            },
        )
        assert risk_research.status_code == 201
        assert risk_research.json()["status"] == "succeeded"
        assert risk_research.json()["findings"]["risk_flags"]
        assert (
            risk_research.json()["evidence_snapshot"]["validation"][
                "experiment_count"
            ]
            == 0
        )
