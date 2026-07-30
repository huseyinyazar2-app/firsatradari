from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    NormalizedDocument,
    ProblemExtractionRecord,
    ProblemExtractionRun,
    RawSnapshot,
)
from firsat_radari.problem_mining.github import (
    PERMITTED_DERIVED_DATA_STATUSES,
    RULES,
    EvidenceCandidate,
    ProblemExtractionError,
    ProblemExtractionOutcome,
    _context_excerpt,
    _outcome,
    _to_evidence,
)

EXTRACTOR_KEY = "stack_exchange_problem_rules"
EXTRACTOR_VERSION = "1.0.0"


class StackExchangeProblemEvidenceExtractor:
    def __init__(self, session: Session) -> None:
        self._session = session

    def extract_pending(
        self,
        *,
        limit: int = 500,
    ) -> ProblemExtractionOutcome:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        source = self._session.scalar(
            select(DataSource).where(DataSource.key == "stack_exchange")
        )
        self._enforce_policy(source)
        run = ProblemExtractionRun(
            source_id=source.id,
            extractor_key=EXTRACTOR_KEY,
            extractor_version=EXTRACTOR_VERSION,
            status="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            input_count=0,
            success_count=0,
            error_count=0,
            evidence_count=0,
        )
        self._session.add(run)
        self._session.commit()

        processed = exists().where(
            ProblemExtractionRecord.document_id == NormalizedDocument.id,
            ProblemExtractionRecord.extractor_key == EXTRACTOR_KEY,
            ProblemExtractionRecord.extractor_version == EXTRACTOR_VERSION,
        )
        documents = list(
            self._session.execute(
                select(NormalizedDocument, RawSnapshot)
                .join(
                    RawSnapshot,
                    RawSnapshot.id == NormalizedDocument.snapshot_id,
                )
                .where(
                    NormalizedDocument.normalizer_key
                    == "stack_exchange_question",
                    NormalizedDocument.normalizer_version == "1.0.0",
                    NormalizedDocument.document_type
                    == "technical_question",
                    NormalizedDocument.status == "succeeded",
                    ~processed,
                )
                .order_by(
                    NormalizedDocument.normalized_at,
                    NormalizedDocument.id,
                )
                .limit(limit)
            )
        )
        for document, snapshot in documents:
            run.input_count += 1
            try:
                candidates = _extract_candidates(document)
                with self._session.begin_nested():
                    record = ProblemExtractionRecord(
                        run_id=run.id,
                        document_id=document.id,
                        extractor_key=EXTRACTOR_KEY,
                        extractor_version=EXTRACTOR_VERSION,
                        status="succeeded",
                        evidence_count=len(candidates),
                        error_class=None,
                        processed_at=datetime.now(UTC),
                    )
                    self._session.add(record)
                    self._session.flush()
                    for candidate in candidates:
                        self._session.add(
                            _to_evidence(
                                record,
                                document,
                                snapshot,
                                candidate,
                            )
                        )
                run.success_count += 1
                run.evidence_count += len(candidates)
            except Exception as exc:
                run.error_count += 1
                self._session.add(
                    ProblemExtractionRecord(
                        run_id=run.id,
                        document_id=document.id,
                        extractor_key=EXTRACTOR_KEY,
                        extractor_version=EXTRACTOR_VERSION,
                        status="failed",
                        evidence_count=0,
                        error_class=type(exc).__name__[:80],
                        processed_at=datetime.now(UTC),
                    )
                )
            self._session.commit()
        run.status = (
            "succeeded"
            if run.error_count == 0
            else "partial"
            if run.success_count > 0
            else "failed"
        )
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(run)

    @staticmethod
    def _enforce_policy(source: DataSource | None) -> None:
        if source is None:
            raise ProblemExtractionError(
                "Stack Exchange source is not registered"
            )
        if (
            not source.enabled
            or source.policy_status != "approved"
            or not source.policy_version
            or source.derived_data_permission
            not in PERMITTED_DERIVED_DATA_STATUSES
        ):
            raise ProblemExtractionError(
                "Stack Exchange source policy does not permit "
                "problem extraction"
            )


def _extract_candidates(
    document: NormalizedDocument,
) -> list[EvidenceCandidate]:
    if document.entity_id is None or not document.title:
        return []
    candidates = [
        EvidenceCandidate(
            evidence_type="problem_report",
            rule_key="stack_exchange_question_report",
            source_field="title",
            char_start=0,
            char_end=len(document.title),
            excerpt=document.title,
            confidence=Decimal("0.7000"),
            attributes={
                "answer_count": document.attributes.get("answer_count", 0),
                "content_license": document.attributes.get(
                    "content_license"
                ),
                "is_answered": document.attributes.get("is_answered"),
                "site": document.attributes.get("site"),
                "tags": document.attributes.get("tags", []),
                "text_representation": "normalized_plain_text_v1",
                "view_count": document.attributes.get("view_count", 0),
            },
        )
    ]
    for source_field, text in (
        ("title", document.title),
        ("body", document.body or ""),
    ):
        for rule in RULES:
            for match in rule.pattern.finditer(text):
                candidates.append(
                    EvidenceCandidate(
                        evidence_type=rule.evidence_type,
                        rule_key=rule.key,
                        source_field=source_field,
                        char_start=match.start(),
                        char_end=match.end(),
                        excerpt=_context_excerpt(
                            text,
                            match.start(),
                            match.end(),
                        ),
                        confidence=rule.confidence,
                        attributes={
                            "matched_text": match.group(0),
                            "text_representation": (
                                "normalized_plain_text_v1"
                            ),
                        },
                    )
                )
    return candidates
