import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.base import Base
from firsat_radari.db.models import OpportunityVersion
from firsat_radari.main import create_app


def test_versioned_profile_preserves_unknowns_and_applies_hard_exclusions() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        version = OpportunityVersion(
            opportunity_id=uuid.uuid4(),
            eligibility_decision_id=uuid.uuid4(),
            supersedes_version_id=None,
            version_number=1,
            ontology_schema_version="1",
            title="Database workflow assistant",
            ontology={"problem": "Teams lose time during database migrations."},
            status="candidate",
            evidence_level="E2",
            input_fingerprint="f" * 64,
            is_current=True,
            created_by="test",
            created_at=datetime.now(UTC),
        )
        session.add(version)
        session.commit()

    settings = Settings(
        environment="test",
        database_url="sqlite://",
        research_settings_api_enabled=True,
    )

    def override_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        vertical = client.post(
            "/verticals",
            json={
                "key": "software",
                "version": "1",
                "name": "Yazılım",
                "status": "active",
                "config": {
                    "included_categories": ["b2b_saas", "developer_tool"],
                    "regions": ["TR", "US"],
                },
                "selection_rationale": "Ölçülebilir ve kaynak kapsamı yeterli.",
                "created_by": "research-owner",
            },
        )
        assert vertical.status_code == 201
        profile = client.post(
            "/research-profiles",
            json={
                "vertical_definition_id": vertical.json()["id"],
                "key": "founder-default",
                "version": "1",
                "name": "Kurucu varsayılanı",
                "status": "active",
                "constraints": {
                    "capital_budget": 1000,
                    "max_build_weeks": 6,
                },
                "exclusions": {
                    "categories": ["game"],
                    "terms": ["gambling"],
                    "sales_motions": ["high_touch_enterprise"],
                },
                "preferences": {"sales_motions": ["self_serve"]},
                "created_by": "research-owner",
            },
        )
        assert profile.status_code == 201
        evaluation = client.post(
            f"/opportunity-versions/{version.id}/profile-evaluations",
            json={
                "research_profile_id": profile.json()["id"],
                "observed_attributes": {
                    "category": "b2b_saas",
                    "estimated_initial_cost": 800,
                    "sales_motion": "self_serve",
                },
                "evaluated_by": "research-owner",
            },
        )
        assert evaluation.status_code == 201
        result = evaluation.json()
        assert result["eligible"] is True
        assert result["unknown_fields"] == ["estimated_build_weeks"]
        assert result["fit_score"] is not None

        excluded = client.post(
            f"/opportunity-versions/{version.id}/profile-evaluations",
            json={
                "research_profile_id": profile.json()["id"],
                "observed_attributes": {
                    "category": "game",
                    "estimated_initial_cost": 800,
                    "estimated_build_weeks": 4,
                    "sales_motion": "self_serve",
                },
                "evaluated_by": "research-owner",
            },
        )
        assert excluded.status_code == 201
        assert excluded.json()["eligible"] is False
        assert excluded.json()["fit_score"] == "0.000000"
        assert "excluded_category:game" in excluded.json()["blocker_codes"]

    Base.metadata.drop_all(engine)
    engine.dispose()
