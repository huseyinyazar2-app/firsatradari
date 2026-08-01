from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from firsat_radari.api.entity_links import (
    ReviewPackageRepositoryLinkRequest,
    review_package_repository_link,
)
from firsat_radari.config import Settings
from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    DataSource,
    Entity,
    IngestionRun,
    NormalizedDocument,
    Package,
    PackageRepositoryLink,
    PackageRepositoryLinkReview,
    PackageVersion,
    Repository,
    RepositoryObservation,
    RepositoryWorkItem,
)
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.normalization.github import GitHubRepositoryNormalizer
from firsat_radari.normalization.github_work_items import (
    GitHubWorkItemNormalizer,
)
from firsat_radari.normalization.npm import NpmPackageNormalizer
from firsat_radari.normalization.service import (
    NormalizationPolicyError,
    NormalizationService,
)
from firsat_radari.storage.filesystem import FileObjectStore


class SnapshotConnector(DataConnector):
    version = "normalization-test-1"
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

    def __init__(self, source_key: str, items: list[RawItem]) -> None:
        self.source_key = source_key
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
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_source(
    session: Session,
    key: str,
    *,
    derived_data_permission: str = "allowed",
) -> DataSource:
    source = DataSource(
        key=key,
        source_type="test",
        owner=key,
        base_url=f"https://{key}.example.test",
        policy_status="approved",
        policy_version="test-policy",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission=derived_data_permission,
        llm_processing_permission="prohibited",
        retention_days=30,
        enabled=True,
    )
    session.add(source)
    session.commit()
    return source


def github_payload(*, stars: int = 10, description: str = "A test repo") -> dict:
    return {
        "id": 123,
        "name": "radar",
        "full_name": "example/radar",
        "owner": {"login": "example"},
        "html_url": "https://github.com/example/radar",
        "description": description,
        "homepage": "https://example.test",
        "language": "Python",
        "license": {"spdx_id": "MIT"},
        "default_branch": "main",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "pushed_at": "2026-07-01T00:00:00Z",
        "archived": False,
        "disabled": False,
        "stargazers_count": stars,
        "forks_count": 2,
        "watchers_count": stars,
        "subscribers_count": 3,
        "open_issues_count": 4,
        "size": 120,
        "topics": ["testing", "quality"],
    }


@pytest.mark.asyncio
async def test_github_normalization_is_idempotent_and_keeps_provenance(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "github")
    observed_at = datetime.now(UTC)
    item = RawItem(
        external_type="repository",
        external_id="123",
        payload=github_payload(),
        observed_at=observed_at,
        source_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        source_updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    store = FileObjectStore(tmp_path)
    ingestion = await IngestionService(session, store).discover(
        SnapshotConnector("github", [item]),
        {"q": "testing"},
    )

    service = NormalizationService(session, store)
    first = service.normalize_pending(GitHubRepositoryNormalizer())
    second = service.normalize_pending(GitHubRepositoryNormalizer())
    version_two = GitHubRepositoryNormalizer()
    version_two.version = "2.0.0"
    third = service.normalize_pending(version_two)

    assert first.status == "succeeded"
    assert first.success_count == 1
    assert second.input_count == 0
    assert third.success_count == 1
    assert session.scalar(select(func.count()).select_from(Entity)) == 1
    repository = session.scalar(select(Repository))
    observation = session.scalar(select(RepositoryObservation))
    document = session.scalar(select(NormalizedDocument))
    assert repository is not None
    assert repository.full_name == "example/radar"
    assert observation is not None
    assert observation.stars_count == 10
    assert document is not None
    assert document.snapshot_id == observation.snapshot_id
    run = session.get(IngestionRun, ingestion.run_id)
    assert run is not None
    assert run.normalized_item_count == 1
    assert session.scalar(select(func.count()).select_from(RepositoryObservation)) == 1
    assert session.scalar(select(func.count()).select_from(NormalizedDocument)) == 2


@pytest.mark.asyncio
async def test_npm_search_and_detail_snapshots_merge_by_registry_identity(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "npm")
    observed_at = datetime.now(UTC)
    search_payload = {
        "package": {
            "name": "@example/radar",
            "version": "1.0.0",
            "description": "Search description",
            "date": "2026-06-01T00:00:00Z",
            "links": {"npm": "https://www.npmjs.com/package/@example/radar"},
            "publisher": {"username": "example"},
        },
        "searchScore": 80.5,
    }
    detail_payload = {
        "_id": "@example/radar",
        "name": "@example/radar",
        "description": "Detailed package",
        "license": "MIT",
        "repository": {
            "type": "git",
            "url": "git+https://github.com/example/radar.git",
            "directory": "packages/radar",
        },
        "homepage": "https://example.test",
        "dist-tags": {"latest": "1.1.0"},
        "time": {
            "created": "2026-05-01T00:00:00Z",
            "modified": "2026-07-01T00:00:00Z",
            "1.0.0": "2026-06-01T00:00:00Z",
            "1.1.0": "2026-07-01T00:00:00Z",
        },
        "versions": {
            "1.0.0": {"name": "@example/radar", "version": "1.0.0"},
            "1.1.0": {
                "name": "@example/radar",
                "version": "1.1.0",
                "license": "MIT",
            },
        },
    }
    items = [
        RawItem(
            external_type="package_search_result",
            external_id="@example/radar",
            payload=search_payload,
            observed_at=observed_at,
        ),
        RawItem(
            external_type="package",
            external_id="@example/radar",
            payload=detail_payload,
            observed_at=observed_at,
        ),
    ]
    store = FileObjectStore(tmp_path)
    await IngestionService(session, store).discover(
        SnapshotConnector("npm", items),
        {"text": "radar"},
    )

    outcome = NormalizationService(session, store).normalize_pending(NpmPackageNormalizer())

    assert outcome.status == "succeeded"
    assert outcome.success_count == 2
    assert session.scalar(select(func.count()).select_from(Entity)) == 1
    package = session.scalar(select(Package))
    assert package is not None
    assert package.description == "Detailed package"
    assert package.repository_url_raw == "git+https://github.com/example/radar.git"
    assert package.repository_directory == "packages/radar"
    link = session.scalar(select(PackageRepositoryLink))
    assert link is not None
    assert link.repository_full_name == "example/radar"
    assert link.repository_id is None
    assert link.status == "candidate"
    assert link.confidence == Decimal("0.9000")
    assert session.scalar(select(func.count()).select_from(PackageVersion)) == 2
    assert session.scalar(select(func.count()).select_from(NormalizedDocument)) == 2

    newer_search_payload = {
        **search_payload,
        "package": {
            **search_payload["package"],
            "description": "Short search description",
            "date": "2026-08-01T00:00:00Z",
        },
    }
    await IngestionService(session, store).discover(
        SnapshotConnector(
            "npm",
            [
                RawItem(
                    external_type="package_search_result",
                    external_id="@example/radar",
                    payload=newer_search_payload,
                    observed_at=observed_at,
                )
            ],
        ),
        {"text": "radar"},
    )
    NormalizationService(session, store).normalize_pending(NpmPackageNormalizer())
    assert package.description == "Detailed package"
    assert package.repository_url_raw == "git+https://github.com/example/radar.git"
    assert package.repository_directory == "packages/radar"

    add_source(session, "github")
    await IngestionService(session, store).discover(
        SnapshotConnector(
            "github",
            [
                RawItem(
                    external_type="repository",
                    external_id="123",
                    payload=github_payload(),
                    observed_at=observed_at,
                )
            ],
        ),
        {"q": "radar"},
    )
    NormalizationService(session, store).normalize_pending(
        GitHubRepositoryNormalizer()
    )
    assert link.repository_id is not None
    assert link.evidence["repository_entity_found"] is True
    assert link.status == "candidate"
    reviewed = review_package_repository_link(
        link.id,
        ReviewPackageRepositoryLinkRequest(
            status="confirmed",
            reviewer="test-reviewer",
            notes="Exact npm-declared repository and matching package scope.",
        ),
        session,
        Settings(
            environment="test",
            database_url="sqlite://",
            entity_link_review_api_enabled=True,
        ),
    )
    assert reviewed.status == "confirmed"
    audit = session.scalar(select(PackageRepositoryLinkReview))
    assert audit is not None
    assert audit.previous_status == "candidate"
    assert audit.new_status == "confirmed"


@pytest.mark.asyncio
async def test_normalization_requires_derived_data_permission(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "github", derived_data_permission="prohibited")
    store = FileObjectStore(tmp_path)

    with pytest.raises(NormalizationPolicyError, match="not permitted"):
        NormalizationService(session, store).normalize_pending(GitHubRepositoryNormalizer())


@pytest.mark.asyncio
async def test_invalid_source_shape_is_recorded_without_partial_entity(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "github")
    payload = github_payload()
    payload.pop("owner")
    item = RawItem(
        external_type="repository",
        external_id="123",
        payload=payload,
        observed_at=datetime.now(UTC),
    )
    store = FileObjectStore(tmp_path)
    await IngestionService(session, store).discover(
        SnapshotConnector("github", [item]),
        {"q": "invalid"},
    )

    outcome = NormalizationService(session, store).normalize_pending(GitHubRepositoryNormalizer())

    assert outcome.status == "failed_permanent"
    assert outcome.error_count == 1
    document = session.scalar(select(NormalizedDocument))
    assert document is not None
    assert document.status == "failed"
    assert document.error_class == "missing_owner"
    assert session.scalar(select(func.count()).select_from(Entity)) == 0


@pytest.mark.asyncio
async def test_github_issue_and_pull_request_are_normalized_as_distinct_types(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "github")
    store = FileObjectStore(tmp_path)
    await IngestionService(session, store).discover(
        SnapshotConnector(
            "github",
            [
                RawItem(
                    external_type="repository",
                    external_id="123",
                    payload=github_payload(),
                    observed_at=datetime.now(UTC),
                )
            ],
        ),
        {"q": "repo"},
    )
    NormalizationService(session, store).normalize_pending(GitHubRepositoryNormalizer())

    base_payload = {
        "repository_url": "https://api.github.com/repos/example/radar",
        "state": "open",
        "body": "Repeated setup failure",
        "labels": [{"name": "bug"}],
        "comments": 3,
        "author_association": "CONTRIBUTOR",
        "user": {"login": "human", "type": "User"},
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
        "closed_at": None,
    }
    issue = {
        **base_payload,
        "id": 1001,
        "number": 11,
        "title": "Setup fails on Windows",
        "html_url": "https://github.com/example/radar/issues/11",
    }
    pull_request = {
        **base_payload,
        "id": 1002,
        "number": 12,
        "title": "Fix Windows setup",
        "html_url": "https://github.com/example/radar/pull/12",
        "pull_request": {"url": "https://api.github.com/repos/example/radar/pulls/12"},
    }
    work_item_connector = SnapshotConnector(
        "github",
        [
            RawItem(
                external_type="repository_work_item",
                external_id="1001",
                payload=issue,
                observed_at=datetime.now(UTC),
            ),
            RawItem(
                external_type="repository_work_item",
                external_id="1002",
                payload=pull_request,
                observed_at=datetime.now(UTC),
            ),
        ],
    )
    work_item_connector.job_type = "github_work_items"
    ingestion = await IngestionService(session, store).discover(
        work_item_connector,
        {"q": "work-items"},
    )
    ingestion_run = session.get(IngestionRun, ingestion.run_id)
    assert ingestion_run is not None
    assert ingestion_run.job_type == "github_work_items"

    outcome = NormalizationService(session, store).normalize_pending(GitHubWorkItemNormalizer())

    assert outcome.success_count == 2
    work_items = list(
        session.scalars(select(RepositoryWorkItem).order_by(RepositoryWorkItem.github_item_id))
    )
    assert [item.item_type for item in work_items] == ["issue", "pull_request"]
    assert work_items[0].labels == ["bug"]
    documents = list(
        session.scalars(
            select(NormalizedDocument).where(
                NormalizedDocument.normalizer_key == "github_work_item"
            )
        )
    )
    assert {document.document_type for document in documents} == {
        "issue",
        "pull_request",
    }


@pytest.mark.asyncio
async def test_normalization_can_be_scoped_to_the_current_ingestion_run(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, "github")
    store = FileObjectStore(tmp_path)
    item = RawItem(
        external_type="repository",
        external_id="123",
        payload=github_payload(),
        observed_at=datetime.now(UTC),
    )
    first = await IngestionService(session, store).discover(
        SnapshotConnector("github", [item]),
        {"q": "first"},
    )
    second = await IngestionService(session, store).discover(
        SnapshotConnector("github", [item]),
        {"q": "second"},
    )

    outcome = NormalizationService(session, store).normalize_pending(
        GitHubRepositoryNormalizer(),
        ingestion_run_id=second.run_id,
    )

    assert first.run_id != second.run_id
    assert outcome.input_count == 1
    assert outcome.success_count == 1
    assert len(list(session.scalars(select(NormalizedDocument)))) == 1
