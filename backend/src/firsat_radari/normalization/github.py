from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    Entity,
    PackageRepositoryLink,
    RawSnapshot,
    Repository,
    RepositoryObservation,
)
from firsat_radari.normalization.base import (
    NormalizationValidationError,
    NormalizedRecord,
    SnapshotNormalizer,
)
from firsat_radari.normalization.entities import get_or_create_entity
from firsat_radari.normalization.utils import (
    is_at_least_as_new,
    nonnegative_int,
    optional_text,
    parse_datetime,
    required_text,
)


class GitHubRepositoryNormalizer(SnapshotNormalizer):
    source_key = "github"
    key = "github_repository"
    version = "1.0.0"
    supported_external_types = frozenset({"repository"})

    def normalize(
        self,
        session: Session,
        source: DataSource,
        snapshot: RawSnapshot,
        payload: dict[str, Any],
    ) -> NormalizedRecord:
        repository_id = nonnegative_int(payload, "id")
        if repository_id == 0:
            raise NormalizationValidationError("invalid_id")
        full_name = required_text(payload, "full_name", maximum=500)
        repository_name = required_text(payload, "name", maximum=300)
        owner = payload.get("owner")
        if not isinstance(owner, dict):
            raise NormalizationValidationError("missing_owner")
        owner_login = required_text(owner, "login", maximum=200)
        canonical_url = required_text(payload, "html_url", maximum=800)
        created_at = parse_datetime(payload.get("created_at"), "created_at", required=True)
        updated_at = parse_datetime(payload.get("updated_at"), "updated_at")
        pushed_at = parse_datetime(payload.get("pushed_at"), "pushed_at")
        license_data = payload.get("license")
        license_spdx = (
            optional_text(license_data.get("spdx_id"), maximum=100)
            if isinstance(license_data, dict)
            else None
        )
        topics_value = payload.get("topics", [])
        topics = (
            [topic[:100] for topic in topics_value if isinstance(topic, str)]
            if isinstance(topics_value, list)
            else []
        )

        repository = session.scalar(
            select(Repository).where(Repository.github_repository_id == repository_id)
        )
        existing_entity = session.get(Entity, repository.id) if repository is not None else None
        if repository is not None and existing_entity is None:
            raise NormalizationValidationError("repository_entity_missing")
        entity = get_or_create_entity(
            session,
            source,
            entity_type="repository",
            external_type="repository",
            external_id=str(repository_id),
            canonical_name=full_name,
            canonical_url=canonical_url,
            observed_at=snapshot.observed_at,
            existing_entity=existing_entity,
        )
        entity.canonical_name = full_name
        entity.canonical_url = canonical_url

        latest_source_update = None
        if repository is None:
            repository = Repository(
                id=entity.id,
                github_repository_id=repository_id,
                owner_login=owner_login,
                repository_name=repository_name,
                full_name=full_name,
                description=optional_text(payload.get("description"), maximum=20_000),
                homepage=optional_text(payload.get("homepage"), maximum=800),
                primary_language=optional_text(payload.get("language"), maximum=100),
                license_spdx=license_spdx,
                default_branch=optional_text(
                    payload.get("default_branch"),
                    maximum=300,
                )
                or "main",
                created_at_source=created_at,
                archived=bool(payload.get("archived", False)),
                disabled=bool(payload.get("disabled", False)),
            )
            session.add(repository)
        else:
            latest_source_update = session.scalar(
                select(func.max(RepositoryObservation.updated_at_source)).where(
                    RepositoryObservation.repository_id == repository.id
                )
            )
        if is_at_least_as_new(updated_at, latest_source_update):
            repository.owner_login = owner_login
            repository.repository_name = repository_name
            repository.full_name = full_name
            repository.description = optional_text(
                payload.get("description"),
                maximum=20_000,
            )
            repository.homepage = optional_text(payload.get("homepage"), maximum=800)
            repository.primary_language = optional_text(
                payload.get("language"),
                maximum=100,
            )
            repository.license_spdx = license_spdx
            repository.default_branch = (
                optional_text(payload.get("default_branch"), maximum=300)
                or repository.default_branch
            )
            repository.archived = bool(payload.get("archived", False))
            repository.disabled = bool(payload.get("disabled", False))

        for package_link in session.scalars(
            select(PackageRepositoryLink).where(
                func.lower(PackageRepositoryLink.repository_full_name)
                == full_name.lower(),
                PackageRepositoryLink.repository_id.is_(None),
                PackageRepositoryLink.status == "candidate",
            )
        ):
            package_link.repository_id = repository.id
            package_link.evidence = {
                **package_link.evidence,
                "repository_entity_found": True,
            }
            package_link.updated_at = snapshot.observed_at

        existing_observation = session.scalar(
            select(RepositoryObservation.id).where(RepositoryObservation.snapshot_id == snapshot.id)
        )
        if existing_observation is None:
            session.add(
                RepositoryObservation(
                    repository_id=entity.id,
                    observed_at=snapshot.observed_at,
                    stars_count=nonnegative_int(
                        payload,
                        "stargazers_count",
                    ),
                    forks_count=nonnegative_int(payload, "forks_count"),
                    watchers_count=nonnegative_int(payload, "watchers_count"),
                    subscribers_count=_optional_nonnegative_int(payload.get("subscribers_count")),
                    open_items_count=nonnegative_int(
                        payload,
                        "open_issues_count",
                    ),
                    size=nonnegative_int(payload, "size"),
                    pushed_at=pushed_at,
                    updated_at_source=updated_at,
                    topics=topics,
                    snapshot_id=snapshot.id,
                )
            )
        return NormalizedRecord(
            entity_id=entity.id,
            document_type="repository",
            title=full_name,
            body=repository.description,
            canonical_url=canonical_url,
            language=None,
            attributes={
                "archived": repository.archived,
                "default_branch": repository.default_branch,
                "forks_count": nonnegative_int(payload, "forks_count"),
                "license_spdx": license_spdx,
                "open_items_count": nonnegative_int(payload, "open_issues_count"),
                "primary_language": repository.primary_language,
                "stars_count": nonnegative_int(payload, "stargazers_count"),
                "topics": topics,
            },
            source_created_at=created_at,
            source_updated_at=updated_at,
        )


def _optional_nonnegative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NormalizationValidationError("invalid_subscribers_count")
    return value
