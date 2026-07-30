import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    NormalizedDocument,
    ProblemEvidence,
    ProblemExtractionRecord,
    ProblemExtractionRun,
    RawSnapshot,
)

EXTRACTOR_KEY = "github_problem_rules"
EXTRACTOR_VERSION = "1.1.2"
PERMITTED_DERIVED_DATA_STATUSES = frozenset({"allowed", "approved"})
PROBLEM_LABELS = frozenset(
    {
        "bug",
        "crash",
        "defect",
        "incident",
        "problem",
        "regression",
        "security",
    }
)
PROBLEM_REPORT_PATTERN = re.compile(
    r"\b("
    r"bug|broken|cannot|can't|crash(?:ed|es|ing)?|"
    r"error|fail(?:ed|ing|s|ure)?|incorrect|"
    r"not working|regression|unable|unexpected|unusable"
    r")\b",
    re.IGNORECASE,
)


class ProblemExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceRule:
    key: str
    evidence_type: str
    pattern: re.Pattern[str]
    confidence: Decimal


@dataclass(frozen=True)
class EvidenceCandidate:
    evidence_type: str
    rule_key: str
    source_field: str
    char_start: int
    char_end: int
    excerpt: str
    confidence: Decimal
    attributes: dict[str, Any]


@dataclass(frozen=True)
class ProblemExtractionOutcome:
    run_id: uuid.UUID
    status: str
    input_count: int
    success_count: int
    error_count: int
    evidence_count: int


RULES = (
    EvidenceRule(
        key="severity_blocker",
        evidence_type="severe_impact",
        pattern=re.compile(
            r"\b(blocker|blocking|critical|unusable|production down)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8500"),
    ),
    EvidenceRule(
        key="data_loss",
        evidence_type="severe_impact",
        pattern=re.compile(
            r"\b(data loss|los(?:e|ing|t) data|corrupt(?:ed|ion)?)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.9000"),
    ),
    EvidenceRule(
        key="frequency_repeated",
        evidence_type="frequency",
        pattern=re.compile(
            r"\b(every time|always|repeatedly|constantly|daily|each time)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8000"),
    ),
    EvidenceRule(
        key="manual_workaround",
        evidence_type="workaround",
        pattern=re.compile(
            r"\b(workaround|work around|temporary fix|manually|manual process|"
            r"copy[ -]?paste|spreadsheet)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8000"),
    ),
    EvidenceRule(
        key="missing_capability",
        evidence_type="missing_capability",
        pattern=re.compile(
            r"\b(feature request|missing feature|support for|ability to|"
            r"would be (?:great|useful|helpful)|wish (?:it|we|I) could)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.7500"),
    ),
    EvidenceRule(
        key="abandonment_intent",
        evidence_type="abandonment_intent",
        pattern=re.compile(
            r"\b(switch(?:ing)? (?:to|away)|migrat(?:e|ing) away|"
            r"stop(?:ped|ping)? using|looking for an alternative)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8500"),
    ),
    EvidenceRule(
        key="payment_intent",
        evidence_type="payment_intent",
        pattern=re.compile(
            r"\b(willing to pay|would pay|budget (?:for|available)|"
            r"paid plan|pay extra)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.9000"),
    ),
    EvidenceRule(
        key="time_impact",
        evidence_type="time_impact",
        pattern=re.compile(
            r"\b(time[- ]consuming|takes? (?:hours|days)|"
            r"hours? (?:of work|each|per)|days? (?:of work|each|per))\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8000"),
    ),
    EvidenceRule(
        key="money_impact",
        evidence_type="money_impact",
        pattern=re.compile(
            r"\b(costs? (?:us|me)|lost revenue|revenue loss|expensive|"
            r"financial impact)\b",
            re.IGNORECASE,
        ),
        confidence=Decimal("0.8000"),
    ),
)


class GitHubProblemEvidenceExtractor:
    def __init__(self, session: Session) -> None:
        self._session = session

    def extract_pending(self, *, limit: int = 500) -> ProblemExtractionOutcome:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        source = self._session.scalar(
            select(DataSource).where(DataSource.key == "github")
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
                    NormalizedDocument.normalizer_key == "github_work_item",
                    NormalizedDocument.normalizer_version == "1.0.0",
                    NormalizedDocument.document_type == "issue",
                    NormalizedDocument.status == "succeeded",
                    ~processed,
                )
                .order_by(NormalizedDocument.normalized_at, NormalizedDocument.id)
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
            raise ProblemExtractionError("GitHub source is not registered")
        if (
            not source.enabled
            or source.policy_status != "approved"
            or not source.policy_version
            or source.derived_data_permission not in PERMITTED_DERIVED_DATA_STATUSES
        ):
            raise ProblemExtractionError(
                "GitHub source policy does not permit problem extraction"
            )


def _extract_candidates(document: NormalizedDocument) -> list[EvidenceCandidate]:
    if document.entity_id is None or not document.title:
        return []
    if bool(document.attributes.get("is_bot_likely", False)):
        return []

    candidates: list[EvidenceCandidate] = []
    if _is_problem_report(document):
        candidates.append(
            EvidenceCandidate(
                evidence_type="problem_report",
                rule_key="github_issue_report",
                source_field="title",
                char_start=0,
                char_end=len(document.title),
                excerpt=document.title,
                confidence=Decimal("0.7000"),
                attributes={
                    "comments_count": document.attributes.get(
                        "comments_count",
                        0,
                    ),
                    "labels": document.attributes.get("labels", []),
                    "state": document.attributes.get("state"),
                },
            )
        )
    for source_field, text in (("title", document.title), ("body", document.body or "")):
        for rule in RULES:
            for match in rule.pattern.finditer(text):
                candidates.append(
                    EvidenceCandidate(
                        evidence_type=rule.evidence_type,
                        rule_key=rule.key,
                        source_field=source_field,
                        char_start=match.start(),
                        char_end=match.end(),
                        excerpt=_context_excerpt(text, match.start(), match.end()),
                        confidence=rule.confidence,
                        attributes={"matched_text": match.group(0)},
                    )
                )
    return candidates


def _is_problem_report(document: NormalizedDocument) -> bool:
    labels = {
        str(label).strip().casefold()
        for label in document.attributes.get("labels", [])
        if str(label).strip()
    }
    if any(
        known_label == label or known_label in label.split()
        for label in labels
        for known_label in PROBLEM_LABELS
    ):
        return True
    return PROBLEM_REPORT_PATTERN.search(document.title) is not None


def _context_excerpt(text: str, start: int, end: int) -> str:
    excerpt_start = max(0, start - 120)
    excerpt_end = min(len(text), end + 120)
    return text[excerpt_start:excerpt_end].strip()[:500]


def _to_evidence(
    record: ProblemExtractionRecord,
    document: NormalizedDocument,
    snapshot: RawSnapshot,
    candidate: EvidenceCandidate,
) -> ProblemEvidence:
    identity = "|".join(
        (
            str(document.id),
            candidate.rule_key,
            candidate.source_field,
            str(candidate.char_start),
            str(candidate.char_end),
            candidate.excerpt,
        )
    )
    return ProblemEvidence(
        extraction_record_id=record.id,
        document_id=document.id,
        entity_id=document.entity_id,
        evidence_type=candidate.evidence_type,
        rule_key=candidate.rule_key,
        source_field=candidate.source_field,
        char_start=candidate.char_start,
        char_end=candidate.char_end,
        excerpt=candidate.excerpt,
        evidence_hash=hashlib.sha256(identity.encode()).hexdigest(),
        confidence=candidate.confidence,
        attributes=candidate.attributes,
        policy_version=snapshot.policy_version,
        retention_until=snapshot.retention_until,
        created_at=datetime.now(UTC),
    )


def _outcome(run: ProblemExtractionRun) -> ProblemExtractionOutcome:
    return ProblemExtractionOutcome(
        run_id=run.id,
        status=run.status,
        input_count=run.input_count,
        success_count=run.success_count,
        error_count=run.error_count,
        evidence_count=run.evidence_count,
    )
