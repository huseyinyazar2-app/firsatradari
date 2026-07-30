import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    Entity,
    Package,
    PackageRepositoryLink,
    PackageVersion,
    RawSnapshot,
    Repository,
)
from firsat_radari.normalization.base import (
    NormalizationValidationError,
    NormalizedRecord,
    SnapshotNormalizer,
)
from firsat_radari.normalization.entities import get_or_create_entity
from firsat_radari.normalization.utils import (
    is_at_least_as_new,
    optional_text,
    parse_datetime,
)


class NpmPackageNormalizer(SnapshotNormalizer):
    source_key = "npm"
    key = "npm_package"
    version = "1.0.0"
    supported_external_types = frozenset({"package", "package_search_result"})

    def normalize(
        self,
        session: Session,
        source: DataSource,
        snapshot: RawSnapshot,
        payload: dict[str, Any],
    ) -> NormalizedRecord:
        package_data, time_data = _package_and_time(snapshot, payload)
        package_name = _package_name(package_data)
        canonical_url = f"https://www.npmjs.com/package/{quote(package_name, safe='@/')}"
        created_at = parse_datetime(time_data.get("created"), "created_at")
        modified_at = parse_datetime(time_data.get("modified"), "modified_at")
        if snapshot.external_type == "package_search_result":
            modified_at = parse_datetime(package_data.get("date"), "modified_at")

        existing_package = session.scalar(
            select(Package).where(
                Package.registry == "npm",
                Package.package_name == package_name,
            )
        )
        existing_entity = (
            session.get(Entity, existing_package.id) if existing_package is not None else None
        )
        if existing_package is not None and existing_entity is None:
            raise NormalizationValidationError("package_entity_missing")
        entity = get_or_create_entity(
            session,
            source,
            entity_type="package",
            external_type="package",
            external_id=package_name,
            canonical_name=package_name,
            canonical_url=canonical_url,
            observed_at=snapshot.observed_at,
            existing_entity=existing_entity,
        )
        entity.canonical_name = package_name
        entity.canonical_url = canonical_url

        repository_url = _repository_url(package_data.get("repository"))
        repository_directory = _repository_directory(
            package_data.get("repository")
        )
        license_expression = optional_text(package_data.get("license"), maximum=300)
        homepage_url = optional_text(package_data.get("homepage"), maximum=800)
        deprecated = bool(package_data.get("deprecated"))
        package = existing_package
        if package is None:
            package = Package(
                id=entity.id,
                registry="npm",
                package_name=package_name,
                description=optional_text(
                    package_data.get("description"),
                    maximum=20_000,
                ),
                license_expression=license_expression,
                repository_url_raw=repository_url,
                repository_directory=repository_directory,
                homepage_url=homepage_url,
                created_at_source=created_at,
                modified_at_source=modified_at,
                deprecated=deprecated,
            )
            session.add(package)
        elif snapshot.external_type == "package":
            if is_at_least_as_new(modified_at, package.modified_at_source):
                package.description = optional_text(
                    package_data.get("description"),
                    maximum=20_000,
                )
                package.license_expression = license_expression
                package.repository_url_raw = repository_url
                package.repository_directory = repository_directory
                package.homepage_url = homepage_url
                package.created_at_source = created_at or package.created_at_source
                package.modified_at_source = modified_at or package.modified_at_source
                package.deprecated = deprecated
            else:
                package.license_expression = (
                    package.license_expression or license_expression
                )
                package.repository_url_raw = (
                    package.repository_url_raw or repository_url
                )
                package.repository_directory = (
                    package.repository_directory or repository_directory
                )
                package.homepage_url = package.homepage_url or homepage_url
                package.created_at_source = (
                    package.created_at_source or created_at
                )
        elif is_at_least_as_new(modified_at, package.modified_at_source):
            if package.description is None:
                package.description = optional_text(
                    package_data.get("description"),
                    maximum=20_000,
                )
            package.modified_at_source = modified_at or package.modified_at_source
        if snapshot.external_type == "package":
            _reconcile_repository_link(
                session,
                package,
                repository_url,
                repository_directory,
                snapshot.observed_at,
            )

        versions_written = _normalize_versions(
            session,
            package,
            snapshot,
            package_data,
            time_data,
        )
        keywords_value = package_data.get("keywords", [])
        keywords = (
            [keyword[:100] for keyword in keywords_value if isinstance(keyword, str)]
            if isinstance(keywords_value, list)
            else []
        )
        return NormalizedRecord(
            entity_id=entity.id,
            document_type="package",
            title=package_name,
            body=package.description,
            canonical_url=canonical_url,
            language=None,
            attributes={
                "deprecated": package.deprecated,
                "keywords": keywords,
                "latest_version": _latest_version(package_data),
                "license_expression": package.license_expression,
                "repository_url_raw": package.repository_url_raw,
                "search_score": _search_score(payload),
                "versions_written": versions_written,
            },
            source_created_at=created_at,
            source_updated_at=modified_at,
        )


def _package_and_time(
    snapshot: RawSnapshot,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if snapshot.external_type == "package_search_result":
        package_data = payload.get("package")
        if not isinstance(package_data, dict):
            raise NormalizationValidationError("missing_package")
        return package_data, {}
    time_data = payload.get("time", {})
    if not isinstance(time_data, dict):
        raise NormalizationValidationError("invalid_time")
    return payload, time_data


def _package_name(package_data: dict[str, Any]) -> str:
    value = package_data.get("name", package_data.get("_id"))
    if not isinstance(value, str) or not value.strip():
        raise NormalizationValidationError("missing_package_name")
    normalized = value.strip()
    if len(normalized) > 300:
        raise NormalizationValidationError("package_name_too_long")
    return normalized


def _repository_url(value: Any) -> str | None:
    if isinstance(value, str):
        return optional_text(value, maximum=800)
    if isinstance(value, dict):
        return optional_text(value.get("url"), maximum=800)
    return None


def _repository_directory(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return optional_text(value.get("directory"), maximum=500)


def _reconcile_repository_link(
    session: Session,
    package: Package,
    source_url: str | None,
    repository_directory: str | None,
    observed_at: datetime,
) -> None:
    reference = _github_repository_reference(source_url)
    if reference is None:
        return
    repository_full_name, match_method = reference
    for previous in session.scalars(
        select(PackageRepositoryLink).where(
            PackageRepositoryLink.package_id == package.id,
            PackageRepositoryLink.status == "candidate",
            PackageRepositoryLink.repository_full_name != repository_full_name,
        )
    ):
        previous.status = "superseded"
        previous.updated_at = observed_at

    repository = session.scalar(
        select(Repository).where(
            func.lower(Repository.full_name) == repository_full_name
        )
    )
    link = session.scalar(
        select(PackageRepositoryLink).where(
            PackageRepositoryLink.package_id == package.id,
            PackageRepositoryLink.repository_full_name == repository_full_name,
        )
    )
    evidence = {
        "declared_by": "npm_package_repository",
        "repository_entity_found": repository is not None,
    }
    if link is None:
        session.add(
            PackageRepositoryLink(
                package_id=package.id,
                repository_id=repository.id if repository else None,
                repository_full_name=repository_full_name,
                source_url=source_url or "",
                repository_directory=repository_directory,
                match_method=match_method,
                confidence=Decimal("0.9000"),
                status="candidate",
                evidence=evidence,
                created_at=observed_at,
                updated_at=observed_at,
                reviewed_at=None,
                reviewer=None,
                review_notes=None,
            )
        )
        return
    link.repository_id = repository.id if repository else link.repository_id
    link.source_url = source_url or link.source_url
    link.repository_directory = repository_directory
    link.match_method = match_method
    link.evidence = evidence
    link.updated_at = observed_at


def _github_repository_reference(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None
    candidate = value.strip()
    match_method = "github_https_url"
    ssh_match = re.fullmatch(
        r"git@github\.com:([^/\s]+)/([^/\s]+)",
        candidate,
        flags=re.IGNORECASE,
    )
    if ssh_match:
        owner, repository = ssh_match.groups()
        match_method = "github_scp_url"
    elif candidate.lower().startswith("github:"):
        parts = candidate[7:].split("/")
        if len(parts) != 2:
            return None
        owner, repository = parts
        match_method = "github_shorthand"
    else:
        normalized = candidate
        if normalized.lower().startswith("git+"):
            normalized = normalized[4:]
        parsed = urlparse(normalized)
        if parsed.hostname is None or parsed.hostname.lower() != "github.com":
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            return None
        owner, repository = parts
        match_method = (
            "github_ssh_url"
            if parsed.scheme.lower() == "ssh"
            else "github_git_url"
            if parsed.scheme.lower() == "git"
            else "github_https_url"
        )
    repository = repository.removesuffix(".git")
    if not owner or not repository:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+",
        repository,
    ):
        return None
    return f"{owner}/{repository}".lower(), match_method


def _normalize_versions(
    session: Session,
    package: Package,
    snapshot: RawSnapshot,
    package_data: dict[str, Any],
    time_data: dict[str, Any],
) -> int:
    candidates: list[tuple[str, dict[str, Any], datetime | None]] = []
    if snapshot.external_type == "package_search_result":
        version = package_data.get("version")
        if isinstance(version, str) and version:
            candidates.append(
                (
                    version,
                    package_data,
                    parse_datetime(package_data.get("date"), "published_at"),
                )
            )
    else:
        versions = package_data.get("versions", {})
        if not isinstance(versions, dict):
            raise NormalizationValidationError("invalid_versions")
        for version, version_data in versions.items():
            if not isinstance(version, str) or not isinstance(version_data, dict):
                continue
            candidates.append(
                (
                    version,
                    version_data,
                    parse_datetime(time_data.get(version), "published_at"),
                )
            )

    written = 0
    for version, version_data, published_at in candidates:
        if published_at is None:
            continue
        normalized_version = version[:100]
        existing = session.scalar(
            select(PackageVersion.id).where(
                PackageVersion.package_id == package.id,
                PackageVersion.version == normalized_version,
            )
        )
        if existing is not None:
            continue
        session.add(
            PackageVersion(
                package_id=package.id,
                version=normalized_version,
                published_at_source=published_at,
                deprecated=bool(version_data.get("deprecated")),
                license_expression=optional_text(
                    version_data.get("license"),
                    maximum=300,
                ),
                repository_url_raw=_repository_url(version_data.get("repository")),
                snapshot_id=snapshot.id,
            )
        )
        written += 1
    return written


def _latest_version(package_data: dict[str, Any]) -> str | None:
    dist_tags = package_data.get("dist-tags")
    if isinstance(dist_tags, dict):
        return optional_text(dist_tags.get("latest"), maximum=100)
    return optional_text(package_data.get("version"), maximum=100)


def _search_score(payload: dict[str, Any]) -> float | None:
    value = payload.get("searchScore")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)
