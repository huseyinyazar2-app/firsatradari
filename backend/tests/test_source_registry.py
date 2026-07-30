import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    SourceIndependenceReview,
    SourcePolicy,
    SourceRelationship,
)
from firsat_radari.main import create_app
from firsat_radari.source_registry.independence import (
    EvidenceOrigin,
    assess_source_independence,
)
from firsat_radari.source_registry.service import (
    PolicyApproval,
    SourceCandidate,
    SourceIndependenceDecision,
    SourceRegistryError,
    SourceRegistryService,
    SourceRelationshipDeclaration,
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


def valid_approval(version: str = "2026-07-29") -> PolicyApproval:
    return PolicyApproval(
        version=version,
        reviewer="data-governance",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission="allowed",
        llm_processing_permission="prohibited",
        retention_days=90,
        terms_url="https://example.test/terms",
    )


def test_candidate_requires_safe_https_source(session: Session) -> None:
    registry = SourceRegistryService(session)

    with pytest.raises(SourceRegistryError, match="HTTPS"):
        registry.register_candidate(
            SourceCandidate(
                key="unsafe",
                source_type="registry",
                owner="owner",
                base_url="http://example.test",
            )
        )


def test_policy_approval_is_versioned_before_source_can_be_enabled(
    session: Session,
) -> None:
    registry = SourceRegistryService(session)
    source = registry.register_candidate(
        SourceCandidate(
            key="example",
            source_type="registry",
            owner="Example",
            base_url="https://example.test",
        )
    )

    with pytest.raises(SourceRegistryError, match="cannot be enabled"):
        registry.set_enabled(source.key, enabled=True)

    policy = registry.approve_policy(source.key, valid_approval())
    enabled_source = registry.set_enabled(source.key, enabled=True)

    assert policy.version == "2026-07-29"
    assert enabled_source.enabled is True
    assert enabled_source.policy_version == policy.version
    assert session.scalar(select(func.count()).select_from(SourcePolicy)) == 1


def test_policy_version_cannot_be_overwritten(session: Session) -> None:
    registry = SourceRegistryService(session)
    registry.register_candidate(
        SourceCandidate(
            key="example",
            source_type="registry",
            owner="Example",
            base_url="https://example.test",
        )
    )
    registry.approve_policy("example", valid_approval())

    with pytest.raises(SourceRegistryError, match="already exists"):
        registry.approve_policy("example", valid_approval())


def test_source_policy_and_enabled_state_are_managed_through_api(
    session: Session,
) -> None:
    source = SourceRegistryService(session).register_candidate(
        SourceCandidate(
            key="example",
            source_type="registry",
            owner="Example",
            base_url="https://example.test",
        )
    )
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        source_governance_api_enabled=True,
    )

    with TestClient(app) as client:
        approved = client.post(
            "/sources/example/policies",
            json={
                "version": "2026-07-30",
                "reviewer": "data-governance",
                "commercial_use_status": "allowed",
                "storage_permission": "allowed",
                "derived_data_permission": "allowed",
                "llm_processing_permission": "prohibited",
                "retention_days": 90,
                "terms_url": "https://example.test/terms",
            },
        )
        enabled = client.patch(
            "/sources/example/enabled",
            json={"enabled": True},
        )

    assert approved.status_code == 201
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True
    session.refresh(source)
    assert source.policy_status == "approved"
    assert source.enabled is True


def test_source_relationship_prevents_naive_independence(
    session: Session,
) -> None:
    registry = SourceRegistryService(session)
    github = registry.register_candidate(
        SourceCandidate(
            key="github",
            source_type="code_host",
            owner="GitHub",
            base_url="https://api.github.com",
            evidence_family_key="developer_repository_activity",
            independence_group_key="github",
            independence_status="conditional",
        )
    )
    npm = registry.register_candidate(
        SourceCandidate(
            key="npm",
            source_type="package_registry",
            owner="npm",
            base_url="https://registry.npmjs.org",
            evidence_family_key="package_distribution",
            independence_group_key="npm",
            independence_status="conditional",
        )
    )

    relationship = registry.declare_relationship(
        SourceRelationshipDeclaration(
            source_key="github",
            related_source_key="npm",
            relationship_type="shared_product_identity",
            scope="same_entity",
            independence_effect="invalidates",
            reviewer="data-governance",
            rationale=(
                "A package and its declared repository can describe the same "
                "underlying product."
            ),
        )
    )

    assert relationship.status == "approved"
    assert relationship.independence_effect == "invalidates"
    assert {relationship.source_id, relationship.related_source_id} == {
        github.id,
        npm.id,
    }
    assert session.scalar(select(func.count()).select_from(SourceRelationship)) == 1
    with pytest.raises(SourceRegistryError, match="already exists"):
        registry.declare_relationship(
            SourceRelationshipDeclaration(
                source_key="npm",
                related_source_key="github",
                relationship_type="shared_product_identity",
                scope="same_entity",
                independence_effect="invalidates",
                reviewer="data-governance",
                rationale="Reverse duplicate must not be accepted.",
            )
        )

    shared_entity_id = uuid.uuid4()
    same_entity = assess_source_independence(
        session,
        [
            EvidenceOrigin(github.id, shared_entity_id, uuid.uuid4()),
            EvidenceOrigin(npm.id, shared_entity_id, uuid.uuid4()),
        ],
    )
    assert same_entity.evidence_level == "unverified_cross_source"
    assert "relationship:shared_product_identity:invalidates" in same_entity.blockers

    with pytest.raises(SourceRegistryError, match="evidence references"):
        registry.review_independence(
            "github",
            SourceIndependenceDecision(
                version="2026-07-31",
                new_status="independent",
                reviewer="data-governance",
                rationale="Ownership and collection paths were reviewed.",
            ),
        )
    registry.review_independence(
        "github",
        SourceIndependenceDecision(
            version="2026-07-31",
            new_status="independent",
            reviewer="data-governance",
            rationale="Ownership and collection paths were reviewed.",
            evidence_references=("https://example.test/reviews/github",),
        ),
    )
    registry.review_independence(
        "npm",
        SourceIndependenceDecision(
            version="2026-07-31",
            new_status="independent",
            reviewer="data-governance",
            rationale="Ownership and collection paths were reviewed.",
            evidence_references=("https://example.test/reviews/npm",),
        ),
    )
    different_entities = assess_source_independence(
        session,
        [
            EvidenceOrigin(github.id, uuid.uuid4(), uuid.uuid4()),
            EvidenceOrigin(npm.id, uuid.uuid4(), uuid.uuid4()),
        ],
    )
    assert different_entities.evidence_level == "E2"
    assert different_entities.verified_independent is True
    assert (
        session.scalar(
            select(func.count()).select_from(SourceIndependenceReview)
        )
        == 2
    )


def test_source_independence_review_api_is_disabled_and_audited(
    session: Session,
) -> None:
    registry = SourceRegistryService(session)
    source = registry.register_candidate(
        SourceCandidate(
            key="example",
            source_type="registry",
            owner="Example",
            base_url="https://example.test",
            evidence_family_key="demand",
            independence_group_key="example",
            independence_status="conditional",
        )
    )
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
    )
    request = {
        "version": "review-v1",
        "new_status": "independent",
        "reviewer": "governance-reviewer",
        "rationale": "Collection ownership and entity overlap were checked.",
        "evidence_references": [
            "https://example.test/governance/review-v1"
        ],
    }

    with TestClient(app) as client:
        disabled = client.post(
            "/sources/example/independence-reviews",
            json=request,
        )
        assert disabled.status_code == 503

        app.dependency_overrides[get_settings] = lambda: Settings(
            environment="test",
            source_governance_api_enabled=True,
        )
        created = client.post(
            "/sources/example/independence-reviews",
            json=request,
        )
        history = client.get("/sources/example/independence-reviews")

    assert created.status_code == 201
    assert created.json()["previous_status"] == "conditional"
    assert created.json()["new_status"] == "independent"
    assert history.status_code == 200
    assert len(history.json()) == 1
    session.refresh(source)
    assert source.independence_status == "independent"
