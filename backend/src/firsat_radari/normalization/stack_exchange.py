import re
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    Entity,
    RawSnapshot,
    StackExchangeQuestion,
)
from firsat_radari.normalization.base import (
    NormalizationValidationError,
    NormalizedRecord,
    SnapshotNormalizer,
)
from firsat_radari.normalization.utils import (
    is_at_least_as_new,
    nonnegative_int,
    required_text,
)


class StackExchangeQuestionNormalizer(SnapshotNormalizer):
    source_key = "stack_exchange"
    key = "stack_exchange_question"
    version = "1.0.0"
    supported_external_types = frozenset({"stack_exchange_question"})

    def normalize(
        self,
        session: Session,
        source: DataSource,
        snapshot: RawSnapshot,
        payload: dict[str, Any],
    ) -> NormalizedRecord:
        site = required_text(payload, "site", maximum=80).casefold()
        question_id = nonnegative_int(payload, "question_id")
        if question_id == 0:
            raise NormalizationValidationError("invalid_question_identity")
        title = _html_to_text(
            required_text(payload, "title", maximum=10_000)
        )
        body = _html_to_text(
            required_text(payload, "body", maximum=250_000)
        )
        if not title or not body:
            raise NormalizationValidationError("empty_question_text")
        canonical_url = _canonical_url(
            required_text(payload, "link", maximum=800)
        )
        tags = _tags(payload.get("tags"))
        created_at = _epoch_datetime(
            payload.get("creation_date"),
            "creation_date",
            required=True,
        )
        last_activity_at = _epoch_datetime(
            payload.get("last_activity_date"),
            "last_activity_date",
            required=True,
        )
        last_edit_at = _epoch_datetime(
            payload.get("last_edit_date"),
            "last_edit_date",
            required=False,
        )
        content_license = required_text(
            payload,
            "content_license",
            maximum=80,
        )
        answer_count = nonnegative_int(payload, "answer_count")
        view_count = nonnegative_int(payload, "view_count")
        score = _integer(payload.get("score"), "score")
        is_answered = _boolean(payload.get("is_answered"), "is_answered")
        accepted_answer_id = _optional_positive_int(
            payload.get("accepted_answer_id"),
            "accepted_answer_id",
        )
        bounty_amount = _optional_positive_int(
            payload.get("bounty_amount"),
            "bounty_amount",
        )
        question = session.scalar(
            select(StackExchangeQuestion).where(
                StackExchangeQuestion.site == site,
                StackExchangeQuestion.question_id == question_id,
            )
        )
        if question is None:
            entity = Entity(
                id=uuid.uuid4(),
                entity_type="stack_exchange_question",
                canonical_name=title[:300],
                canonical_url=canonical_url,
                status="active",
            )
            session.add(entity)
            question = StackExchangeQuestion(
                id=entity.id,
                site=site,
                question_id=question_id,
                title=title[:500],
                body=body,
                canonical_url=canonical_url,
                tags=tags,
                answer_count=answer_count,
                is_answered=is_answered,
                accepted_answer_id=accepted_answer_id,
                view_count=view_count,
                score=score,
                bounty_amount=bounty_amount,
                content_license=content_license,
                created_at_source=created_at,
                last_activity_at_source=last_activity_at,
                last_edit_at_source=last_edit_at,
                snapshot_id=snapshot.id,
            )
            session.add(question)
        elif is_at_least_as_new(
            last_activity_at,
            question.last_activity_at_source,
        ):
            question.title = title[:500]
            question.body = body
            question.canonical_url = canonical_url
            question.tags = tags
            question.answer_count = answer_count
            question.is_answered = is_answered
            question.accepted_answer_id = accepted_answer_id
            question.view_count = view_count
            question.score = score
            question.bounty_amount = bounty_amount
            question.content_license = content_license
            question.last_activity_at_source = last_activity_at
            question.last_edit_at_source = last_edit_at
            question.snapshot_id = snapshot.id
            entity = session.get(Entity, question.id)
            if entity is not None:
                entity.canonical_name = title[:300]
                entity.canonical_url = canonical_url

        return NormalizedRecord(
            entity_id=question.id,
            document_type="technical_question",
            title=title[:500],
            body=body,
            canonical_url=canonical_url,
            language=None,
            attributes={
                "accepted_answer_id": accepted_answer_id,
                "answer_count": answer_count,
                "attribution_required": True,
                "bounty_amount": bounty_amount,
                "bounty_unit": "reputation_points",
                "content_license": content_license,
                "is_answered": is_answered,
                "question_id": question_id,
                "score": score,
                "site": site,
                "state": "answered" if is_answered else "unresolved",
                "tags": tags,
                "view_count": view_count,
            },
            source_created_at=created_at,
            source_updated_at=last_activity_at,
        )


class _TextExtractor(HTMLParser):
    _BLOCK_TAGS = frozenset(
        {
            "blockquote",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "li",
            "ol",
            "p",
            "pre",
            "ul",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return re.sub(r"[ \t\r\f\v]+", " ", "".join(parser.parts)).strip()


def _canonical_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username:
        raise NormalizationValidationError("invalid_question_url")
    return value


def _tags(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise NormalizationValidationError("invalid_tags")
    tags: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise NormalizationValidationError("invalid_tags")
        tags.append(item.strip().casefold()[:35])
    return sorted(set(tags))


def _epoch_datetime(
    value: Any,
    field: str,
    *,
    required: bool,
) -> datetime | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NormalizationValidationError(f"invalid_{field}")
    return datetime.fromtimestamp(value, tz=UTC)


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NormalizationValidationError(f"invalid_{field}")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise NormalizationValidationError(f"invalid_{field}")
    return value


def _optional_positive_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise NormalizationValidationError(f"invalid_{field}")
    return value
