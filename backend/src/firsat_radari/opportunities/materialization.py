import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    ClaimCommercialOutcomeLink,
    ClaimEvidenceLink,
    EvidenceClaim,
    EvidenceClaimReview,
    Opportunity,
    OpportunityComponentClaimLink,
    OpportunityEligibilityDecision,
    OpportunityEligibilityRun,
    OpportunityVersion,
    ProblemCluster,
)

ONTOLOGY_SCHEMA_VERSION = "1.0.0"
REQUIRED_COMPONENT_CLAIM_TYPES = {
    "customer": "customer_segment",
    "job": "job_to_be_done",
    "problem": "recurring_problem",
    "context": "problem_context",
    "current_alternative": "current_alternative",
    "solution_gap": "solution_gap",
    "payment_reason": "payment_reason",
    "entry_product": "entry_product_hypothesis",
    "distribution_path": "distribution_path",
    "expansion_path": "expansion_path_hypothesis",
}


class OpportunityMaterializationError(ValueError):
    pass


@dataclass(frozen=True)
class GroundedOpportunityInput:
    eligibility_decision_id: uuid.UUID
    component_claim_ids: dict[str, uuid.UUID]
    created_by: str


@dataclass(frozen=True)
class OpportunityMaterializationOutcome:
    opportunity_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    created: bool


class OpportunityMaterializationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def materialize(
        self,
        candidate: GroundedOpportunityInput,
    ) -> OpportunityMaterializationOutcome:
        created_by = candidate.created_by.strip()
        if not created_by:
            raise OpportunityMaterializationError("Creator is required")
        component_keys = set(candidate.component_claim_ids)
        required_keys = set(REQUIRED_COMPONENT_CLAIM_TYPES)
        if component_keys != required_keys:
            missing = sorted(required_keys - component_keys)
            unexpected = sorted(component_keys - required_keys)
            raise OpportunityMaterializationError(
                f"Opportunity ontology is incomplete: missing={missing}, "
                f"unexpected={unexpected}"
            )

        decision = self._session.get(
            OpportunityEligibilityDecision,
            candidate.eligibility_decision_id,
        )
        if decision is None:
            raise OpportunityMaterializationError(
                "Opportunity eligibility decision not found"
            )
        cluster = self._session.get(ProblemCluster, decision.cluster_id)
        if cluster is None:
            raise OpportunityMaterializationError("Problem cluster not found")
        latest_run = self._session.scalar(
            select(OpportunityEligibilityRun)
            .where(
                OpportunityEligibilityRun.clustering_run_id == cluster.run_id,
                OpportunityEligibilityRun.status == "succeeded",
            )
            .order_by(
                OpportunityEligibilityRun.finished_at.desc(),
                OpportunityEligibilityRun.id.desc(),
            )
            .limit(1)
        )
        if latest_run is None or latest_run.id != decision.run_id:
            raise OpportunityMaterializationError(
                "Eligibility decision is not from the latest successful run"
            )
        if not decision.eligible or decision.evidence_level != "E2":
            raise OpportunityMaterializationError(
                "Opportunity requires an eligible E2 decision"
            )

        claims = self._load_and_validate_claims(
            cluster.id,
            candidate.component_claim_ids,
        )
        fingerprint = self._fingerprint(decision, claims)
        existing = self._session.scalar(
            select(OpportunityVersion).where(
                OpportunityVersion.input_fingerprint == fingerprint
            )
        )
        if existing is not None:
            return OpportunityMaterializationOutcome(
                opportunity_id=existing.opportunity_id,
                version_id=existing.id,
                version_number=existing.version_number,
                created=False,
            )

        opportunity = self._session.scalar(
            select(Opportunity).where(
                Opportunity.origin_cluster_id == cluster.id
            )
        )
        if opportunity is None:
            opportunity = Opportunity(
                origin_cluster_id=cluster.id,
                status="candidate",
                created_at=datetime.now(UTC),
            )
            self._session.add(opportunity)
            self._session.flush()
        previous = self._session.scalar(
            select(OpportunityVersion)
            .where(
                OpportunityVersion.opportunity_id == opportunity.id,
                OpportunityVersion.is_current.is_(True),
            )
            .order_by(OpportunityVersion.version_number.desc())
            .limit(1)
        )
        if previous is not None:
            previous.is_current = False
        ontology = {
            component_key: claims[component_key].statement
            for component_key in REQUIRED_COMPONENT_CLAIM_TYPES
        }
        title = f"{ontology['customer']} — {ontology['problem']}"[:500]
        version = OpportunityVersion(
            opportunity_id=opportunity.id,
            eligibility_decision_id=decision.id,
            supersedes_version_id=previous.id if previous else None,
            version_number=(previous.version_number + 1 if previous else 1),
            ontology_schema_version=ONTOLOGY_SCHEMA_VERSION,
            title=title,
            ontology=ontology,
            status="candidate",
            evidence_level=decision.evidence_level,
            input_fingerprint=fingerprint,
            is_current=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(version)
        self._session.flush()
        for component_key, claim in claims.items():
            self._session.add(
                OpportunityComponentClaimLink(
                    opportunity_version_id=version.id,
                    component_key=component_key,
                    claim_id=claim.id,
                    created_at=datetime.now(UTC),
                )
            )
        self._session.commit()
        return OpportunityMaterializationOutcome(
            opportunity_id=opportunity.id,
            version_id=version.id,
            version_number=version.version_number,
            created=True,
        )

    def _load_and_validate_claims(
        self,
        cluster_id: uuid.UUID,
        component_claim_ids: dict[str, uuid.UUID],
    ) -> dict[str, EvidenceClaim]:
        claims_by_id = {
            claim.id: claim
            for claim in self._session.scalars(
                select(EvidenceClaim).where(
                    EvidenceClaim.id.in_(set(component_claim_ids.values()))
                )
            )
        }
        if len(claims_by_id) != len(component_claim_ids):
            raise OpportunityMaterializationError(
                "One or more ontology claims were not found"
            )
        claims = {
            key: claims_by_id[claim_id]
            for key, claim_id in component_claim_ids.items()
        }
        claim_ids = set(claims_by_id)
        links_by_claim: dict[uuid.UUID, list[ClaimEvidenceLink]] = {
            claim_id: [] for claim_id in claim_ids
        }
        for link in self._session.scalars(
            select(ClaimEvidenceLink).where(
                ClaimEvidenceLink.claim_id.in_(claim_ids)
            )
        ):
            links_by_claim[link.claim_id].append(link)
        commercial_links_by_claim: dict[
            uuid.UUID,
            list[ClaimCommercialOutcomeLink],
        ] = {claim_id: [] for claim_id in claim_ids}
        for link in self._session.scalars(
            select(ClaimCommercialOutcomeLink).where(
                ClaimCommercialOutcomeLink.claim_id.in_(claim_ids)
            )
        ):
            commercial_links_by_claim[link.claim_id].append(link)
        for component_key, claim in claims.items():
            expected_type = REQUIRED_COMPONENT_CLAIM_TYPES[component_key]
            if claim.claim_type != expected_type:
                raise OpportunityMaterializationError(
                    f"{component_key} requires claim type {expected_type}"
                )
            if (
                claim.cluster_id != cluster_id
                or not claim.is_current
                or claim.status != "grounded"
                or not claim.statement.strip()
            ):
                raise OpportunityMaterializationError(
                    f"{component_key} claim is not current grounded evidence"
                )
            links = [
                *links_by_claim[claim.id],
                *commercial_links_by_claim[claim.id],
            ]
            if not any(link.direction == "supports" for link in links):
                raise OpportunityMaterializationError(
                    f"{component_key} claim has no supporting source evidence"
                )
            if any(link.direction == "refutes" for link in links):
                raise OpportunityMaterializationError(
                    f"{component_key} claim has unresolved counter-evidence"
                )
            if claim.generator_key != "deterministic_problem_cluster_claim":
                latest_review = self._session.scalar(
                    select(EvidenceClaimReview)
                    .where(EvidenceClaimReview.claim_id == claim.id)
                    .order_by(
                        EvidenceClaimReview.reviewed_at.desc(),
                        EvidenceClaimReview.id.desc(),
                    )
                    .limit(1)
                )
                if (
                    latest_review is None
                    or latest_review.decision != "approved"
                ):
                    raise OpportunityMaterializationError(
                        f"{component_key} claim lacks critic approval"
                    )
        if claims["problem"].evidence_level != "E2":
            raise OpportunityMaterializationError(
                "Recurring problem claim must have E2 evidence"
            )
        return claims

    @staticmethod
    def _fingerprint(
        decision: OpportunityEligibilityDecision,
        claims: dict[str, EvidenceClaim],
    ) -> str:
        payload = {
            "ontology_schema_version": ONTOLOGY_SCHEMA_VERSION,
            "eligibility_decision_id": str(decision.id),
            "claims": {
                key: {
                    "id": str(claim.id),
                    "input_fingerprint": claim.input_fingerprint,
                }
                for key, claim in sorted(claims.items())
            },
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
