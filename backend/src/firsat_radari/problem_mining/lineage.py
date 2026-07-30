import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterLineage,
    ProblemClusterLineageRun,
    ProblemClusterMembership,
)

LINEAGE_ALGORITHM_VERSION = "1.0.0"
MINIMUM_COMPARABLE_CLUSTERS = 20
MINIMUM_STABILITY_RATE = Decimal("0.800000")
PAIR_THRESHOLD = Decimal("0.600000")
STABLE_MEMBER_THRESHOLD = Decimal("0.800000")
PRECISION = Decimal("0.000001")


class ProblemClusterLineageError(ValueError):
    pass


@dataclass(frozen=True)
class ClusterState:
    cluster: ProblemCluster
    evidence_ids: frozenset[uuid.UUID]
    signature: frozenset[str]


@dataclass(frozen=True)
class CandidateRelation:
    previous: ClusterState
    current: ClusterState
    member_jaccard: Decimal
    signature_jaccard: Decimal


@dataclass(frozen=True)
class ProblemClusterLineageOutcome:
    run_id: uuid.UUID
    status: str
    matched_cluster_count: int
    stable_cluster_count: int
    new_cluster_count: int
    disappeared_cluster_count: int
    passes_stability_gate: bool


class ProblemClusterLineageService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def compare(
        self,
        previous_clustering_run_id: uuid.UUID,
        current_clustering_run_id: uuid.UUID,
    ) -> ProblemClusterLineageOutcome:
        previous_run = self._session.get(
            ProblemClusteringRun,
            previous_clustering_run_id,
        )
        current_run = self._session.get(
            ProblemClusteringRun,
            current_clustering_run_id,
        )
        if previous_run is None or current_run is None:
            raise ProblemClusterLineageError("Problem clustering run not found")
        if previous_run.id == current_run.id:
            raise ProblemClusterLineageError(
                "Lineage requires two different clustering runs"
            )
        if previous_run.status != "succeeded" or current_run.status != "succeeded":
            raise ProblemClusterLineageError(
                "Both clustering runs must be complete"
            )
        if previous_run.algorithm_key != current_run.algorithm_key:
            raise ProblemClusterLineageError(
                "Clustering algorithms are not comparable"
            )
        if _as_utc(previous_run.as_of) >= _as_utc(current_run.as_of):
            raise ProblemClusterLineageError(
                "Current clustering run must be newer than previous run"
            )
        existing = self._session.scalar(
            select(ProblemClusterLineageRun).where(
                ProblemClusterLineageRun.previous_clustering_run_id
                == previous_run.id,
                ProblemClusterLineageRun.current_clustering_run_id
                == current_run.id,
                ProblemClusterLineageRun.algorithm_version
                == LINEAGE_ALGORITHM_VERSION,
            )
        )
        if existing is not None:
            return _outcome(existing)

        previous_states = self._states(previous_run.id)
        current_states = self._states(current_run.id)
        candidates = _candidate_relations(previous_states, current_states)
        previous_degrees = Counter(
            relation.previous.cluster.id for relation in candidates
        )
        current_degrees = Counter(
            relation.current.cluster.id for relation in candidates
        )
        matched_previous_ids = set(previous_degrees)
        matched_current_ids = set(current_degrees)
        stable_current_ids = {
            relation.current.cluster.id
            for relation in candidates
            if previous_degrees[relation.previous.cluster.id] == 1
            and current_degrees[relation.current.cluster.id] == 1
            and relation.member_jaccard >= STABLE_MEMBER_THRESHOLD
        }
        new_states = [
            state
            for state in current_states
            if state.cluster.id not in matched_current_ids
        ]
        disappeared_states = [
            state
            for state in previous_states
            if state.cluster.id not in matched_previous_ids
        ]
        current_count = len(current_states)
        stability_rate = _ratio(len(stable_current_ids), current_count)
        best_jaccard_by_current: dict[uuid.UUID, Decimal] = defaultdict(
            lambda: Decimal(0)
        )
        for relation in candidates:
            current_id = relation.current.cluster.id
            best_jaccard_by_current[current_id] = max(
                best_jaccard_by_current[current_id],
                relation.member_jaccard,
            )
        mean_best_jaccard = (
            (
                sum(
                    (
                        best_jaccard_by_current.get(
                            state.cluster.id,
                            Decimal(0),
                        )
                        for state in current_states
                    ),
                    Decimal(0),
                )
                / Decimal(current_count)
            ).quantize(PRECISION)
            if current_count
            else None
        )
        status = _stability_status(
            previous_count=len(previous_states),
            current_count=current_count,
            stability_rate=stability_rate,
        )
        lineage_run = ProblemClusterLineageRun(
            previous_clustering_run_id=previous_run.id,
            current_clustering_run_id=current_run.id,
            algorithm_version=LINEAGE_ALGORITHM_VERSION,
            status=status,
            previous_cluster_count=len(previous_states),
            current_cluster_count=current_count,
            matched_cluster_count=len(matched_current_ids),
            stable_cluster_count=len(stable_current_ids),
            split_relation_count=sum(
                degree for degree in previous_degrees.values() if degree > 1
            ),
            merge_relation_count=sum(
                degree for degree in current_degrees.values() if degree > 1
            ),
            new_cluster_count=len(new_states),
            disappeared_cluster_count=len(disappeared_states),
            stability_rate=stability_rate,
            mean_best_member_jaccard=mean_best_jaccard,
            passes_stability_gate=status == "passed",
            calculation={
                "minimum_comparable_clusters": MINIMUM_COMPARABLE_CLUSTERS,
                "minimum_stability_rate": float(MINIMUM_STABILITY_RATE),
                "pair_threshold": float(PAIR_THRESHOLD),
                "stable_member_threshold": float(
                    STABLE_MEMBER_THRESHOLD
                ),
                "cluster_scope": "cross_entity_candidate",
            },
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        self._session.add(lineage_run)
        self._session.flush()
        for relation in candidates:
            relation_type = _relation_type(
                relation,
                previous_degrees,
                current_degrees,
            )
            self._session.add(
                ProblemClusterLineage(
                    lineage_run_id=lineage_run.id,
                    previous_cluster_id=relation.previous.cluster.id,
                    current_cluster_id=relation.current.cluster.id,
                    relation_type=relation_type,
                    member_jaccard=relation.member_jaccard,
                    signature_jaccard=relation.signature_jaccard,
                    created_at=datetime.now(UTC),
                )
            )
        for state in new_states:
            self._session.add(
                ProblemClusterLineage(
                    lineage_run_id=lineage_run.id,
                    previous_cluster_id=None,
                    current_cluster_id=state.cluster.id,
                    relation_type="new",
                    member_jaccard=None,
                    signature_jaccard=None,
                    created_at=datetime.now(UTC),
                )
            )
        for state in disappeared_states:
            self._session.add(
                ProblemClusterLineage(
                    lineage_run_id=lineage_run.id,
                    previous_cluster_id=state.cluster.id,
                    current_cluster_id=None,
                    relation_type="disappeared",
                    member_jaccard=None,
                    signature_jaccard=None,
                    created_at=datetime.now(UTC),
                )
            )
        lineage_run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(lineage_run)

    def _states(self, clustering_run_id: uuid.UUID) -> list[ClusterState]:
        clusters = list(
            self._session.scalars(
                select(ProblemCluster).where(
                    ProblemCluster.run_id == clustering_run_id,
                    ProblemCluster.status == "cross_entity_candidate",
                )
            )
        )
        memberships = list(
            self._session.scalars(
                select(ProblemClusterMembership).where(
                    ProblemClusterMembership.run_id == clustering_run_id
                )
            )
        )
        evidence_ids_by_cluster: dict[
            uuid.UUID,
            set[uuid.UUID],
        ] = defaultdict(set)
        for membership in memberships:
            evidence_ids_by_cluster[membership.cluster_id].add(
                membership.evidence_id
            )
        return [
            ClusterState(
                cluster=cluster,
                evidence_ids=frozenset(
                    evidence_ids_by_cluster.get(cluster.id, set())
                ),
                signature=frozenset(str(token) for token in cluster.signature),
            )
            for cluster in clusters
        ]


def _candidate_relations(
    previous_states: list[ClusterState],
    current_states: list[ClusterState],
) -> list[CandidateRelation]:
    candidates: list[CandidateRelation] = []
    for previous in previous_states:
        for current in current_states:
            member_jaccard = _jaccard(
                previous.evidence_ids,
                current.evidence_ids,
            )
            signature_jaccard = _jaccard(
                previous.signature,
                current.signature,
            )
            if (
                member_jaccard >= PAIR_THRESHOLD
                or signature_jaccard >= PAIR_THRESHOLD
            ):
                candidates.append(
                    CandidateRelation(
                        previous=previous,
                        current=current,
                        member_jaccard=member_jaccard,
                        signature_jaccard=signature_jaccard,
                    )
                )
    return candidates


def _relation_type(
    relation: CandidateRelation,
    previous_degrees: Counter,
    current_degrees: Counter,
) -> str:
    if previous_degrees[relation.previous.cluster.id] > 1:
        return "split"
    if current_degrees[relation.current.cluster.id] > 1:
        return "merged"
    if relation.member_jaccard >= STABLE_MEMBER_THRESHOLD:
        return "stable"
    return "evolved"


def _stability_status(
    *,
    previous_count: int,
    current_count: int,
    stability_rate: Decimal | None,
) -> str:
    if min(previous_count, current_count) < MINIMUM_COMPARABLE_CLUSTERS:
        return "insufficient_history"
    if stability_rate is None or stability_rate < MINIMUM_STABILITY_RATE:
        return "below_stability_threshold"
    return "passed"


def _jaccard(left: frozenset, right: frozenset) -> Decimal:
    if not left and not right:
        return Decimal("1.000000")
    if not left or not right:
        return Decimal("0.000000")
    return (
        Decimal(len(left & right)) / Decimal(len(left | right))
    ).quantize(PRECISION)


def _ratio(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return (
        Decimal(numerator) / Decimal(denominator)
    ).quantize(PRECISION)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _outcome(
    run: ProblemClusterLineageRun,
) -> ProblemClusterLineageOutcome:
    return ProblemClusterLineageOutcome(
        run_id=run.id,
        status=run.status,
        matched_cluster_count=run.matched_cluster_count,
        stable_cluster_count=run.stable_cluster_count,
        new_cluster_count=run.new_cluster_count,
        disappeared_cluster_count=run.disappeared_cluster_count,
        passes_stability_gate=run.passes_stability_gate,
    )
