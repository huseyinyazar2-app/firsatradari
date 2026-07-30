import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    NormalizedDocument,
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterMembership,
    ProblemEvidence,
    ProblemExtractionRecord,
    RawSnapshot,
)

ALGORITHM_KEY = "lexical_problem_candidates"
ALGORITHM_VERSION = "1.1.1"
SIMILARITY_THRESHOLD = Decimal("0.600000")
MAX_CLUSTERING_INPUTS = 1_000
PERMITTED_DERIVED_DATA_STATUSES = frozenset({"allowed", "approved"})
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]*")
STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "because",
        "before",
        "being",
        "between",
        "could",
        "does",
        "doesnt",
        "during",
        "error",
        "feature",
        "from",
        "have",
        "into",
        "issue",
        "please",
        "problem",
        "request",
        "should",
        "that",
        "their",
        "there",
        "these",
        "this",
        "using",
        "when",
        "where",
        "which",
        "with",
        "would",
    }
)
TOKEN_ALIASES = {
    "crashed": "crash",
    "crashes": "crash",
    "crashing": "crash",
    "failed": "fail",
    "failing": "fail",
    "fails": "fail",
    "failure": "fail",
    "failures": "fail",
    "installing": "install",
    "installation": "install",
    "installed": "install",
}
ACTIVE_EXTRACTORS = {
    "github_problem_rules": "1.1.1",
    "stack_exchange_problem_rules": "1.0.0",
}


class ProblemClusteringError(ValueError):
    pass


@dataclass(frozen=True)
class ClusterInput:
    evidence_id: uuid.UUID
    document_id: uuid.UUID
    entity_id: uuid.UUID
    source_id: uuid.UUID
    evidence_hash: str
    text: str
    tokens: frozenset[str]
    source_created_at: datetime | None


@dataclass(frozen=True)
class CandidateGroup:
    representative: ClusterInput
    members: tuple[ClusterInput, ...]
    similarities: tuple[Decimal, ...]


@dataclass(frozen=True)
class ProblemClusteringOutcome:
    run_id: uuid.UUID
    status: str
    input_count: int
    eligible_count: int
    cluster_count: int
    singleton_count: int
    error_count: int


class ProblemClusteringEngine:
    def __init__(self, session: Session) -> None:
        self._session = session

    def cluster(
        self,
        *,
        as_of: datetime | None = None,
        source_created_from: datetime | None = None,
    ) -> ProblemClusteringOutcome:
        if as_of is not None and _as_utc(as_of) > datetime.now(UTC):
            raise ProblemClusteringError("as_of cannot be in the future")
        normalized_source_created_from = (
            _as_utc(source_created_from)
            if source_created_from is not None
            else None
        )

        query_cutoff = (
            _as_utc(as_of) if as_of is not None else datetime.now(UTC)
        )
        if (
            normalized_source_created_from is not None
            and normalized_source_created_from > query_cutoff
        ):
            raise ProblemClusteringError(
                "source_created_from cannot be after as_of"
            )
        statement = (
            select(
                ProblemEvidence,
                NormalizedDocument,
                RawSnapshot,
            )
            .join(
                NormalizedDocument,
                NormalizedDocument.id == ProblemEvidence.document_id,
            )
            .join(
                RawSnapshot,
                RawSnapshot.id == NormalizedDocument.snapshot_id,
            )
            .join(
                ProblemExtractionRecord,
                ProblemExtractionRecord.id
                == ProblemEvidence.extraction_record_id,
            )
            .where(
                ProblemEvidence.evidence_type == "problem_report",
                or_(
                    *(
                        and_(
                            ProblemExtractionRecord.extractor_key == key,
                            ProblemExtractionRecord.extractor_version
                            == version,
                        )
                        for key, version in ACTIVE_EXTRACTORS.items()
                    )
                ),
                ProblemEvidence.created_at <= query_cutoff,
                or_(
                    ProblemEvidence.retention_until.is_(None),
                    ProblemEvidence.retention_until >= query_cutoff,
                ),
                or_(
                    NormalizedDocument.source_created_at.is_(None),
                    NormalizedDocument.source_created_at <= query_cutoff,
                ),
            )
            .order_by(ProblemEvidence.created_at, ProblemEvidence.id)
        )
        if normalized_source_created_from is not None:
            statement = statement.where(
                NormalizedDocument.source_created_at
                >= normalized_source_created_from
            )
        rows = list(self._session.execute(statement))
        if not rows:
            raise ProblemClusteringError("No retained problem evidence is available")
        if len(rows) > MAX_CLUSTERING_INPUTS:
            raise ProblemClusteringError(
                "Problem evidence exceeds the 1000-item safety limit; "
                "partition the clustering input"
            )
        effective_as_of = (
            query_cutoff
            if as_of is not None
            else max(_as_utc(evidence.created_at) for evidence, _, _ in rows)
        )

        source_ids = {snapshot.source_id for _, _, snapshot in rows}
        self._enforce_policies(source_ids)
        input_fingerprint = hashlib.sha256(
            "|".join(sorted(evidence.evidence_hash for evidence, _, _ in rows)).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(ProblemClusteringRun).where(
                ProblemClusteringRun.algorithm_key == ALGORITHM_KEY,
                ProblemClusteringRun.algorithm_version == ALGORITHM_VERSION,
                ProblemClusteringRun.input_fingerprint == input_fingerprint,
            )
        )
        if existing is not None:
            return _outcome(existing)

        inputs = [
            ClusterInput(
                evidence_id=evidence.id,
                document_id=document.id,
                entity_id=evidence.entity_id,
                source_id=snapshot.source_id,
                evidence_hash=evidence.evidence_hash,
                text=evidence.excerpt,
                tokens=_tokens(evidence.excerpt),
                source_created_at=document.source_created_at,
            )
            for evidence, document, snapshot in rows
        ]
        eligible = [item for item in inputs if len(item.tokens) >= 3]
        groups = _candidate_groups(eligible)
        run = ProblemClusteringRun(
            algorithm_key=ALGORITHM_KEY,
            algorithm_version=ALGORITHM_VERSION,
            input_fingerprint=input_fingerprint,
            input_definition={
                "source_created_from": (
                    normalized_source_created_from.isoformat()
                    if normalized_source_created_from is not None
                    else None
                ),
                "as_of_requested": (
                    query_cutoff.isoformat() if as_of is not None else None
                ),
                "retention_enforced": True,
                "maximum_input_count": MAX_CLUSTERING_INPUTS,
            },
            as_of=effective_as_of,
            status="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            input_count=len(inputs),
            eligible_count=len(eligible),
            cluster_count=0,
            singleton_count=0,
            error_count=0,
        )
        self._session.add(run)
        self._session.flush()

        for group in groups:
            cluster_id = uuid.uuid4()
            member_hashes = sorted(member.evidence_hash for member in group.members)
            fingerprint = hashlib.sha256("|".join(member_hashes).encode()).hexdigest()
            entity_count = len({member.entity_id for member in group.members})
            source_count = len({member.source_id for member in group.members})
            if len(group.members) == 1:
                cluster_status = "insufficient_repetition"
                run.singleton_count += 1
            elif entity_count == 1:
                cluster_status = "within_entity_repeated"
            else:
                cluster_status = "cross_entity_candidate"
            source_dates = [
                _as_utc(member.source_created_at)
                for member in group.members
                if member.source_created_at is not None
            ]
            signature = sorted(
                set.intersection(
                    *(set(member.tokens) for member in group.members)
                )
            )
            self._session.add(
                ProblemCluster(
                    id=cluster_id,
                    run_id=run.id,
                    fingerprint=fingerprint,
                    signature=signature,
                    label=group.representative.text[:500],
                    status=cluster_status,
                    representative_evidence_id=group.representative.evidence_id,
                    document_count=len(group.members),
                    entity_count=entity_count,
                    source_count=source_count,
                    cohesion_min=min(group.similarities),
                    cohesion_mean=(
                        sum(group.similarities, Decimal(0))
                        / Decimal(len(group.similarities))
                    ).quantize(Decimal("0.000001")),
                    first_source_created_at=min(source_dates) if source_dates else None,
                    last_source_created_at=max(source_dates) if source_dates else None,
                    created_at=datetime.now(UTC),
                )
            )
            for member, similarity in zip(
                group.members,
                group.similarities,
                strict=True,
            ):
                self._session.add(
                    ProblemClusterMembership(
                        run_id=run.id,
                        cluster_id=cluster_id,
                        evidence_id=member.evidence_id,
                        document_id=member.document_id,
                        entity_id=member.entity_id,
                        source_id=member.source_id,
                        similarity_to_representative=similarity,
                        created_at=datetime.now(UTC),
                    )
                )
            run.cluster_count += 1

        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(run)

    def _enforce_policies(self, source_ids: set[uuid.UUID]) -> None:
        sources = {
            source.id: source
            for source in self._session.scalars(
                select(DataSource).where(DataSource.id.in_(source_ids))
            )
        }
        if len(sources) != len(source_ids):
            raise ProblemClusteringError("Problem evidence source is missing")
        for source in sources.values():
            if (
                not source.enabled
                or source.policy_status != "approved"
                or source.derived_data_permission
                not in PERMITTED_DERIVED_DATA_STATUSES
            ):
                raise ProblemClusteringError(
                    f"Source policy does not permit clustering: {source.key}"
                )


def _tokens(text: str) -> frozenset[str]:
    tokens: set[str] = set()
    for match in TOKEN_PATTERN.finditer(text.casefold()):
        token = match.group(0).strip("._+-")
        token = token.replace("'", "")
        token = TOKEN_ALIASES.get(token, token)
        if len(token) < 3 or token.isdigit() or token in STOP_WORDS:
            continue
        tokens.add(token)
    return frozenset(tokens)


def _candidate_groups(inputs: list[ClusterInput]) -> list[CandidateGroup]:
    remaining = sorted(inputs, key=lambda item: item.evidence_hash)
    groups: list[CandidateGroup] = []
    while remaining:
        representative = max(
            remaining,
            key=lambda candidate: _representative_rank(candidate, remaining),
        )
        members_with_similarity = [
            (candidate, _similarity(representative.tokens, candidate.tokens))
            for candidate in remaining
        ]
        selected = [
            (candidate, similarity)
            for candidate, similarity in members_with_similarity
            if candidate == representative or similarity >= SIMILARITY_THRESHOLD
        ]
        selected.sort(key=lambda item: item[0].evidence_hash)
        selected_ids = {candidate.evidence_id for candidate, _ in selected}
        remaining = [
            candidate
            for candidate in remaining
            if candidate.evidence_id not in selected_ids
        ]
        groups.append(
            CandidateGroup(
                representative=representative,
                members=tuple(candidate for candidate, _ in selected),
                similarities=tuple(similarity for _, similarity in selected),
            )
        )
    return groups


def _representative_rank(
    candidate: ClusterInput,
    inputs: list[ClusterInput],
) -> tuple[int, Decimal, str]:
    similarities = [
        _similarity(candidate.tokens, other.tokens)
        for other in inputs
    ]
    neighbors = sum(
        similarity >= SIMILARITY_THRESHOLD for similarity in similarities
    )
    total = sum(similarities, Decimal(0))
    return neighbors, total, candidate.evidence_hash


def _similarity(left: frozenset[str], right: frozenset[str]) -> Decimal:
    if left == right:
        return Decimal("1.000000")
    intersection_count = len(left & right)
    if intersection_count < 2:
        return Decimal("0.000000")
    union_count = len(left | right)
    return (
        Decimal(intersection_count) / Decimal(union_count)
    ).quantize(Decimal("0.000001"))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _outcome(run: ProblemClusteringRun) -> ProblemClusteringOutcome:
    return ProblemClusteringOutcome(
        run_id=run.id,
        status=run.status,
        input_count=run.input_count,
        eligible_count=run.eligible_count,
        cluster_count=run.cluster_count,
        singleton_count=run.singleton_count,
        error_count=run.error_count,
    )
