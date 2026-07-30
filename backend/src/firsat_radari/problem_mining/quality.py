import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    ProblemCluster,
    ProblemClusterAudit,
    ProblemClusteringQualitySnapshot,
    ProblemClusteringRun,
)

MINIMUM_AUDITED_CLUSTERS = 20
MINIMUM_AUDIT_COVERAGE = Decimal("0.200000")
MINIMUM_MEMBER_PURITY = Decimal("0.800000")
MINIMUM_CLUSTER_COHERENCE_RATE = Decimal("0.800000")
PRECISION = Decimal("0.000001")


class ProblemClusterQualityError(ValueError):
    pass


@dataclass(frozen=True)
class ClusterAuditInput:
    cluster_id: uuid.UUID
    reviewer: str
    verdict: str
    sampled_member_count: int
    coherent_member_count: int
    sample_method: str = "random_member_sample"
    notes: str | None = None


@dataclass(frozen=True)
class ProblemClusterQualityOutcome:
    snapshot_id: uuid.UUID
    status: str
    passes_quality_gate: bool
    eligible_cluster_count: int
    audited_cluster_count: int


class ProblemClusterQualityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_audit(self, audit_input: ClusterAuditInput) -> ProblemClusterAudit:
        cluster = self._session.get(ProblemCluster, audit_input.cluster_id)
        if cluster is None:
            raise ProblemClusterQualityError("Problem cluster not found")
        reviewer = audit_input.reviewer.strip()
        if len(reviewer) < 2:
            raise ProblemClusterQualityError("Reviewer is required")
        if audit_input.verdict not in {"coherent", "mixed", "incorrect"}:
            raise ProblemClusterQualityError("Unsupported cluster verdict")
        if audit_input.sample_method not in {
            "all_members",
            "random_member_sample",
            "stratified_entity_sample",
        }:
            raise ProblemClusterQualityError("Unsupported sample method")
        if not 1 <= audit_input.sampled_member_count <= cluster.document_count:
            raise ProblemClusterQualityError(
                "Sample count must fit the cluster document count"
            )
        if not 0 <= audit_input.coherent_member_count <= audit_input.sampled_member_count:
            raise ProblemClusterQualityError(
                "Coherent member count must fit the sample"
            )
        purity = (
            Decimal(audit_input.coherent_member_count)
            / Decimal(audit_input.sampled_member_count)
        ).quantize(Decimal("0.0001"))
        if audit_input.verdict == "coherent" and purity < Decimal("0.8000"):
            raise ProblemClusterQualityError(
                "Coherent verdict requires at least 80% sampled purity"
            )
        if audit_input.verdict == "incorrect" and purity > Decimal("0.2000"):
            raise ProblemClusterQualityError(
                "Incorrect verdict requires at most 20% sampled purity"
            )
        if audit_input.verdict == "mixed" and not (
            Decimal("0.2000") < purity < Decimal("0.8000")
        ):
            raise ProblemClusterQualityError(
                "Mixed verdict requires purity between 20% and 80%"
            )
        previous = self._session.scalar(
            select(ProblemClusterAudit)
            .where(ProblemClusterAudit.cluster_id == cluster.id)
            .order_by(
                ProblemClusterAudit.created_at.desc(),
                ProblemClusterAudit.id.desc(),
            )
            .limit(1)
        )
        audit = ProblemClusterAudit(
            clustering_run_id=cluster.run_id,
            cluster_id=cluster.id,
            supersedes_audit_id=previous.id if previous else None,
            reviewer=reviewer,
            verdict=audit_input.verdict,
            sample_method=audit_input.sample_method,
            sampled_member_count=audit_input.sampled_member_count,
            coherent_member_count=audit_input.coherent_member_count,
            purity=purity,
            notes=audit_input.notes,
            created_at=datetime.now(UTC),
        )
        self._session.add(audit)
        self._session.commit()
        return audit

    def calculate(
        self,
        clustering_run_id: uuid.UUID,
    ) -> ProblemClusterQualityOutcome:
        clustering_run = self._session.get(
            ProblemClusteringRun,
            clustering_run_id,
        )
        if clustering_run is None:
            raise ProblemClusterQualityError("Problem clustering run not found")
        if clustering_run.status != "succeeded":
            raise ProblemClusterQualityError(
                "Problem clustering run is not complete"
            )
        eligible_clusters = list(
            self._session.scalars(
                select(ProblemCluster).where(
                    ProblemCluster.run_id == clustering_run.id,
                    ProblemCluster.status == "cross_entity_candidate",
                )
            )
        )
        eligible_cluster_ids = {cluster.id for cluster in eligible_clusters}
        latest_audits: dict[uuid.UUID, ProblemClusterAudit] = {}
        if eligible_cluster_ids:
            audits = list(
                self._session.scalars(
                    select(ProblemClusterAudit)
                    .where(
                        ProblemClusterAudit.cluster_id.in_(
                            eligible_cluster_ids
                        )
                    )
                    .order_by(
                        ProblemClusterAudit.created_at,
                        ProblemClusterAudit.id,
                    )
                )
            )
            for audit in audits:
                latest_audits[audit.cluster_id] = audit
        input_fingerprint = hashlib.sha256(
            "|".join(
                (
                    str(clustering_run.id),
                    *sorted(str(audit.id) for audit in latest_audits.values()),
                )
            ).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(ProblemClusteringQualitySnapshot).where(
                ProblemClusteringQualitySnapshot.clustering_run_id
                == clustering_run.id,
                ProblemClusteringQualitySnapshot.input_fingerprint
                == input_fingerprint,
            )
        )
        if existing is not None:
            return _outcome(existing)

        eligible_count = len(eligible_clusters)
        audited_count = len(latest_audits)
        coherent_cluster_count = sum(
            audit.verdict == "coherent" for audit in latest_audits.values()
        )
        sampled_member_count = sum(
            audit.sampled_member_count for audit in latest_audits.values()
        )
        coherent_member_count = sum(
            audit.coherent_member_count for audit in latest_audits.values()
        )
        audit_coverage = _ratio(audited_count, eligible_count) or Decimal(0)
        cluster_coherence_rate = _ratio(
            coherent_cluster_count,
            audited_count,
        )
        member_purity = _ratio(
            coherent_member_count,
            sampled_member_count,
        )
        purity_lower, purity_upper = _wilson_interval(
            coherent_member_count,
            sampled_member_count,
        )
        status = _quality_status(
            eligible_count=eligible_count,
            audited_count=audited_count,
            audit_coverage=audit_coverage,
            cluster_coherence_rate=cluster_coherence_rate,
            member_purity=member_purity,
        )
        snapshot = ProblemClusteringQualitySnapshot(
            clustering_run_id=clustering_run.id,
            input_fingerprint=input_fingerprint,
            status=status,
            eligible_cluster_count=eligible_count,
            audited_cluster_count=audited_count,
            coherent_cluster_count=coherent_cluster_count,
            sampled_member_count=sampled_member_count,
            coherent_member_count=coherent_member_count,
            audit_coverage=audit_coverage,
            cluster_coherence_rate=cluster_coherence_rate,
            member_purity=member_purity,
            purity_confidence_lower=purity_lower,
            purity_confidence_upper=purity_upper,
            passes_quality_gate=status == "passed",
            calculation={
                "minimum_audited_clusters": MINIMUM_AUDITED_CLUSTERS,
                "minimum_audit_coverage": float(MINIMUM_AUDIT_COVERAGE),
                "minimum_member_purity": float(MINIMUM_MEMBER_PURITY),
                "minimum_cluster_coherence_rate": float(
                    MINIMUM_CLUSTER_COHERENCE_RATE
                ),
                "audit_selection": "latest_audit_per_cluster",
                "confidence_method": "wilson_95",
            },
            calculated_at=datetime.now(UTC),
        )
        self._session.add(snapshot)
        self._session.commit()
        return _outcome(snapshot)


def _quality_status(
    *,
    eligible_count: int,
    audited_count: int,
    audit_coverage: Decimal,
    cluster_coherence_rate: Decimal | None,
    member_purity: Decimal | None,
) -> str:
    if eligible_count == 0:
        return "insufficient_clusters"
    if (
        audited_count < MINIMUM_AUDITED_CLUSTERS
        or audit_coverage < MINIMUM_AUDIT_COVERAGE
    ):
        return "insufficient_audits"
    if (
        member_purity is None
        or cluster_coherence_rate is None
        or member_purity < MINIMUM_MEMBER_PURITY
        or cluster_coherence_rate < MINIMUM_CLUSTER_COHERENCE_RATE
    ):
        return "below_quality_threshold"
    return "passed"


def _ratio(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return (
        Decimal(numerator) / Decimal(denominator)
    ).quantize(PRECISION)


def _wilson_interval(
    successes: int,
    sample_size: int,
) -> tuple[Decimal | None, Decimal | None]:
    if sample_size == 0:
        return None, None
    z = 1.959963984540054
    proportion = successes / sample_size
    denominator = 1 + z * z / sample_size
    centre = proportion + z * z / (2 * sample_size)
    spread = z * math.sqrt(
        proportion * (1 - proportion) / sample_size
        + z * z / (4 * sample_size * sample_size)
    )
    return (
        Decimal(str((centre - spread) / denominator)).quantize(PRECISION),
        Decimal(str((centre + spread) / denominator)).quantize(PRECISION),
    )


def _outcome(
    snapshot: ProblemClusteringQualitySnapshot,
) -> ProblemClusterQualityOutcome:
    return ProblemClusterQualityOutcome(
        snapshot_id=snapshot.id,
        status=snapshot.status,
        passes_quality_gate=snapshot.passes_quality_gate,
        eligible_cluster_count=snapshot.eligible_cluster_count,
        audited_cluster_count=snapshot.audited_cluster_count,
    )
