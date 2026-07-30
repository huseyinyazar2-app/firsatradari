from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    RawSnapshot,
    Repository,
    RepositoryWorkItem,
)
from firsat_radari.normalization.base import (
    NormalizationValidationError,
    NormalizedRecord,
    SnapshotNormalizer,
)
from firsat_radari.normalization.utils import (
    is_at_least_as_new,
    nonnegative_int,
    optional_text,
    parse_datetime,
    required_text,
)


class GitHubWorkItemNormalizer(SnapshotNormalizer):
    source_key = "github"
    key = "github_work_item"
    version = "1.0.0"
    supported_external_types = frozenset({"repository_work_item"})

    def normalize(
        self,
        session: Session,
        source: DataSource,
        snapshot: RawSnapshot,
        payload: dict[str, Any],
    ) -> NormalizedRecord:
        github_item_id = nonnegative_int(payload, "id")
        number = nonnegative_int(payload, "number")
        if github_item_id == 0 or number == 0:
            raise NormalizationValidationError("invalid_work_item_identity")
        repository_full_name = _repository_full_name(payload.get("repository_url"))
        repository = session.scalar(
            select(Repository).where(
                func.lower(Repository.full_name) == repository_full_name.lower()
            )
        )
        if repository is None:
            raise NormalizationValidationError("repository_not_normalized")

        item_type = "pull_request" if "pull_request" in payload else "issue"
        title = required_text(payload, "title", maximum=10_000)
        canonical_url = required_text(payload, "html_url", maximum=800)
        state = required_text(payload, "state", maximum=20)
        created_at = parse_datetime(payload.get("created_at"), "created_at", required=True)
        updated_at = parse_datetime(payload.get("updated_at"), "updated_at", required=True)
        closed_at = parse_datetime(payload.get("closed_at"), "closed_at")
        labels = _labels(payload.get("labels"))
        author_association = optional_text(
            payload.get("author_association"),
            maximum=50,
        )
        is_bot_likely = _is_bot(payload.get("user"))

        work_item = session.scalar(
            select(RepositoryWorkItem).where(
                RepositoryWorkItem.repository_id == repository.id,
                RepositoryWorkItem.github_item_id == github_item_id,
            )
        )
        if work_item is None:
            work_item = RepositoryWorkItem(
                repository_id=repository.id,
                github_item_id=github_item_id,
                number=number,
                item_type=item_type,
                state=state,
                title=title,
                body=optional_text(payload.get("body"), maximum=100_000),
                labels=labels,
                comments_count=nonnegative_int(payload, "comments"),
                author_association=author_association,
                created_at_source=created_at,
                updated_at_source=updated_at,
                closed_at_source=closed_at,
                is_bot_likely=is_bot_likely,
                snapshot_id=snapshot.id,
            )
            session.add(work_item)
        elif is_at_least_as_new(updated_at, work_item.updated_at_source):
            work_item.number = number
            work_item.item_type = item_type
            work_item.state = state
            work_item.title = title
            work_item.body = optional_text(payload.get("body"), maximum=100_000)
            work_item.labels = labels
            work_item.comments_count = nonnegative_int(payload, "comments")
            work_item.author_association = author_association
            work_item.updated_at_source = updated_at
            work_item.closed_at_source = closed_at
            work_item.is_bot_likely = is_bot_likely
            work_item.snapshot_id = snapshot.id

        return NormalizedRecord(
            entity_id=repository.id,
            document_type=item_type,
            title=title[:500],
            body=work_item.body,
            canonical_url=canonical_url,
            language=None,
            attributes={
                "author_association": author_association,
                "comments_count": work_item.comments_count,
                "closed_at": closed_at.isoformat() if closed_at else None,
                "is_bot_likely": is_bot_likely,
                "item_type": item_type,
                "labels": labels,
                "number": number,
                "repository_full_name": repository.full_name,
                "state": state,
            },
            source_created_at=created_at,
            source_updated_at=updated_at,
        )


def _repository_full_name(value: Any) -> str:
    if not isinstance(value, str):
        raise NormalizationValidationError("missing_repository_url")
    parsed = urlparse(value)
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "api.github.com"
        or len(path_parts) != 3
        or path_parts[0] != "repos"
    ):
        raise NormalizationValidationError("invalid_repository_url")
    return f"{path_parts[1]}/{path_parts[2]}"


def _labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for label in value:
        name = label.get("name") if isinstance(label, dict) else label
        if isinstance(name, str) and name.strip():
            labels.append(name.strip()[:100])
    return labels


def _is_bot(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    login = value.get("login")
    return value.get("type") == "Bot" or (
        isinstance(login, str) and login.lower().endswith("[bot]")
    )
