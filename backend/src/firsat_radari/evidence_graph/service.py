import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    ClaimEvidenceLink,
    EvidenceClaim,
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterMembership,
    ProblemEvidence,
)
from firsat_radari.source_registry.independence import (
    EvidenceOrigin,
    assess_source_independence,
)

GENERATOR_KEY = "deterministic_problem_cluster_claim"
GENERATOR_VERSION = "1.0.0"


class EvidenceGraphError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceGraphOutcome:
    clustering_run_id: uuid.UUID
    claim_count: int
    created_count: int
    reused_count: int


class EvidenceGraphService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def materialize_problem_claims(
        self,
        clustering_run_id: uuid.UUID,
    ) -> EvidenceGraphOutcome:
        clustering_run = self._session.get(
            ProblemClusteringRun,
            clustering_run_id,
        )
        if clustering_run is None:
            raise EvidenceGraphError("Problem clustering run not found")
        if clustering_run.status != "succeeded":
            raise EvidenceGraphError("Problem clustering run is not complete")
        clusters = list(
            self._session.scalars(
                select(ProblemCluster)
                .where(
                    ProblemCluster.run_id == clustering_run.id,
                    ProblemCluster.status == "cross_entity_candidate",
                )
                .order_by(ProblemCluster.id)
            )
        )
        created_count = 0
        reused_count = 0
        for cluster in clusters:
            memberships = list(
                self._session.scalars(
                    select(ProblemClusterMembership)
                    .where(
                        ProblemClusterMembership.cluster_id == cluster.id
                    )
                    .order_by(ProblemClusterMembership.evidence_id)
                )
            )
            evidence = {
                item.id: item
                for item in self._session.scalars(
                    select(ProblemEvidence).where(
                        ProblemEvidence.id.in_(
                            {
                                membership.evidence_id
                                for membership in memberships
                            }
                        )
                    )
                )
            }
            if len(evidence) != len(memberships):
                raise EvidenceGraphError(
                    "Problem cluster evidence is incomplete"
                )
            assessment = assess_source_independence(
                self._session,
                [
                    EvidenceOrigin(
                        source_id=membership.source_id,
                        entity_id=membership.entity_id,
                        content_id=membership.document_id,
                    )
                    for membership in memberships
                ],
            )
            input_fingerprint = hashlib.sha256(
                "|".join(
                    (
                        GENERATOR_VERSION,
                        str(cluster.id),
                        cluster.fingerprint,
                        assessment.evidence_level,
                        str(assessment.source_count),
                        str(assessment.independence_group_count),
                        *assessment.blockers,
                        *sorted(
                            item.evidence_hash for item in evidence.values()
                        ),
                    )
                ).encode()
            ).hexdigest()
            existing = self._session.scalar(
                select(EvidenceClaim).where(
                    EvidenceClaim.input_fingerprint == input_fingerprint,
                    EvidenceClaim.is_current.is_(True),
                )
            )
            if existing is not None:
                reused_count += 1
                continue
            previous = self._session.scalar(
                select(EvidenceClaim)
                .where(
                    EvidenceClaim.cluster_id == cluster.id,
                    EvidenceClaim.claim_type == "recurring_problem",
                    EvidenceClaim.is_current.is_(True),
                )
                .order_by(
                    EvidenceClaim.created_at.desc(),
                    EvidenceClaim.id.desc(),
                )
                .limit(1)
            )
            if previous is not None:
                previous.is_current = False
            claim = EvidenceClaim(
                cluster_id=cluster.id,
                supersedes_claim_id=previous.id if previous else None,
                claim_type="recurring_problem",
                statement=f"Repeated problem cluster: {cluster.label}",
                status="grounded",
                generator_key=GENERATOR_KEY,
                generator_version=GENERATOR_VERSION,
                input_fingerprint=input_fingerprint,
                evidence_level=assessment.evidence_level,
                source_count=assessment.source_count,
                independence_group_count=(
                    assessment.independence_group_count
                ),
                supporting_evidence_count=len(memberships),
                independence_blockers=list(assessment.blockers),
                is_current=True,
                created_by="system:evidence-graph",
                created_at=datetime.now(UTC),
            )
            self._session.add(claim)
            self._session.flush()
            for membership in memberships:
                self._session.add(
                    ClaimEvidenceLink(
                        claim_id=claim.id,
                        problem_evidence_id=membership.evidence_id,
                        source_id=membership.source_id,
                        direction="supports",
                        created_at=datetime.now(UTC),
                    )
                )
            created_count += 1
        self._session.commit()
        return EvidenceGraphOutcome(
            clustering_run_id=clustering_run.id,
            claim_count=len(clusters),
            created_count=created_count,
            reused_count=reused_count,
        )
