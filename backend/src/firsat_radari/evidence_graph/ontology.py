import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.commercial_validation.service import (
    DIRECT_PAYMENT_OUTCOMES,
)
from firsat_radari.db.models import (
    ClaimCommercialOutcomeLink,
    ClaimEvidenceLink,
    CommercialOutcome,
    CommercialValidationExperiment,
    EvidenceClaim,
    EvidenceClaimReview,
    NormalizedDocument,
    ProblemCluster,
    ProblemClusterMembership,
    ProblemEvidence,
)
from firsat_radari.source_registry.independence import (
    EvidenceOrigin,
    assess_source_independence,
)

EXTRACTOR_KEY = "deterministic_ontology_drafts"
EXTRACTOR_VERSION = "1.0.0"
ALLOWED_CLAIM_TYPES = frozenset(
    {
        "customer_segment",
        "job_to_be_done",
        "problem_context",
        "current_alternative",
        "solution_gap",
        "payment_reason",
        "entry_product_hypothesis",
        "distribution_path",
        "expansion_path_hypothesis",
    }
)


class OntologyClaimError(ValueError):
    pass


@dataclass(frozen=True)
class OntologyClaimProposalInput:
    cluster_id: uuid.UUID
    claim_type: str
    statement: str
    supporting_problem_evidence_ids: tuple[uuid.UUID, ...] = ()
    refuting_problem_evidence_ids: tuple[uuid.UUID, ...] = ()
    commercial_outcome_ids: tuple[uuid.UUID, ...] = ()
    generator_key: str = EXTRACTOR_KEY
    generator_version: str = EXTRACTOR_VERSION
    created_by: str = "system:ontology-extractor"


@dataclass(frozen=True)
class EvidenceClaimReviewInput:
    claim_id: uuid.UUID
    version: str
    decision: str
    reviewer: str
    rationale: str


@dataclass(frozen=True)
class OntologyDraftOutcome:
    cluster_id: uuid.UUID
    claim_ids: dict[str, uuid.UUID]
    missing_claim_types: tuple[str, ...]


class OntologyClaimService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def generate_observed_drafts(
        self,
        cluster_id: uuid.UUID,
    ) -> OntologyDraftOutcome:
        cluster = self._session.get(ProblemCluster, cluster_id)
        if cluster is None:
            raise OntologyClaimError("Problem cluster not found")
        memberships = list(
            self._session.scalars(
                select(ProblemClusterMembership).where(
                    ProblemClusterMembership.cluster_id == cluster.id
                )
            )
        )
        if not memberships:
            raise OntologyClaimError("Problem cluster has no evidence")
        evidence_by_id = {
            evidence.id: evidence
            for evidence in self._session.scalars(
                select(ProblemEvidence).where(
                    ProblemEvidence.document_id.in_(
                        {
                            membership.document_id
                            for membership in memberships
                        }
                    )
                )
            )
        }
        documents = {
            document.id: document
            for document in self._session.scalars(
                select(NormalizedDocument).where(
                    NormalizedDocument.id.in_(
                        {
                            membership.document_id
                            for membership in memberships
                        }
                    )
                )
            )
        }
        problem_ids = tuple(
            evidence.id
            for evidence in evidence_by_id.values()
            if evidence.evidence_type == "problem_report"
        )
        if not problem_ids:
            raise OntologyClaimError(
                "Problem cluster has no source-grounded problem reports"
            )
        contexts = _observed_contexts(documents.values())
        direct_rows = self._verified_direct_outcomes(cluster.id)
        proposals: dict[str, OntologyClaimProposalInput] = {}
        if direct_rows:
            segments = _unique_text(
                experiment.target_segment for _, experiment in direct_rows
            )
            customer_statement = (
                "Observed paying customer segment: "
                + "; ".join(segments)
            )
            customer_outcomes = tuple(
                outcome.id for outcome, _ in direct_rows
            )
        else:
            customer_statement = (
                "Observed customer segment: people reporting this problem"
                + (f" in {contexts}" if contexts else "")
                + "."
            )
            customer_outcomes = ()
        proposals["customer_segment"] = OntologyClaimProposalInput(
            cluster_id=cluster.id,
            claim_type="customer_segment",
            statement=customer_statement,
            supporting_problem_evidence_ids=problem_ids,
            commercial_outcome_ids=customer_outcomes,
        )
        proposals["job_to_be_done"] = OntologyClaimProposalInput(
            cluster_id=cluster.id,
            claim_type="job_to_be_done",
            statement=(
                "Observed job: complete work currently blocked by "
                f"“{cluster.label}”."
            ),
            supporting_problem_evidence_ids=problem_ids,
        )
        proposals["problem_context"] = OntologyClaimProposalInput(
            cluster_id=cluster.id,
            claim_type="problem_context",
            statement=(
                f"Observed context: {contexts}."
                if contexts
                else "Observed context: source reports in this cluster."
            ),
            supporting_problem_evidence_ids=problem_ids,
        )
        workaround_ids = tuple(
            evidence.id
            for evidence in evidence_by_id.values()
            if evidence.evidence_type == "workaround"
        )
        if workaround_ids:
            proposals["current_alternative"] = OntologyClaimProposalInput(
                cluster_id=cluster.id,
                claim_type="current_alternative",
                statement=(
                    "Observed current alternative: "
                    + _first_excerpt(evidence_by_id, workaround_ids)
                ),
                supporting_problem_evidence_ids=workaround_ids,
            )
        gap_ids = tuple(
            evidence.id
            for evidence in evidence_by_id.values()
            if evidence.evidence_type
            in {
                "missing_capability",
                "abandonment_intent",
                "severe_impact",
            }
        )
        if gap_ids:
            proposals["solution_gap"] = OntologyClaimProposalInput(
                cluster_id=cluster.id,
                claim_type="solution_gap",
                statement=(
                    "Observed solution gap: "
                    + _first_excerpt(evidence_by_id, gap_ids)
                ),
                supporting_problem_evidence_ids=gap_ids,
            )
        if direct_rows:
            outcome, experiment = direct_rows[0]
            money = (
                f"{outcome.amount} {outcome.currency}"
                if outcome.amount is not None and outcome.currency
                else outcome.outcome_type
            )
            proposals["payment_reason"] = OntologyClaimProposalInput(
                cluster_id=cluster.id,
                claim_type="payment_reason",
                statement=(
                    f"Verified payment reason: {experiment.target_segment} "
                    f"provided {money} for “{experiment.hypothesis}”."
                ),
                commercial_outcome_ids=tuple(
                    item.id for item, _ in direct_rows
                ),
            )
        claim_ids = {
            claim_type: self.propose(value).id
            for claim_type, value in proposals.items()
        }
        expected = {
            "customer_segment",
            "job_to_be_done",
            "problem_context",
            "current_alternative",
            "solution_gap",
            "payment_reason",
        }
        return OntologyDraftOutcome(
            cluster_id=cluster.id,
            claim_ids=claim_ids,
            missing_claim_types=tuple(sorted(expected - set(claim_ids))),
        )

    def propose(
        self,
        value: OntologyClaimProposalInput,
    ) -> EvidenceClaim:
        cluster = self._session.get(ProblemCluster, value.cluster_id)
        if cluster is None:
            raise OntologyClaimError("Problem cluster not found")
        if value.claim_type not in ALLOWED_CLAIM_TYPES:
            raise OntologyClaimError("Unsupported ontology claim type")
        statement = _required_text(value.statement, "statement", 4_000)
        generator_key = _required_text(
            value.generator_key,
            "generator_key",
            80,
        )
        generator_version = _required_text(
            value.generator_version,
            "generator_version",
            40,
        )
        created_by = _required_text(value.created_by, "created_by", 200)
        support_ids = set(value.supporting_problem_evidence_ids)
        refute_ids = set(value.refuting_problem_evidence_ids)
        if support_ids & refute_ids:
            raise OntologyClaimError(
                "The same evidence cannot support and refute a claim"
            )
        memberships = self._cluster_memberships(
            cluster.id,
            support_ids | refute_ids,
        )
        commercial_rows = self._commercial_outcomes(
            cluster.id,
            set(value.commercial_outcome_ids),
        )
        if not support_ids and not commercial_rows:
            raise OntologyClaimError(
                "Ontology claim requires source or commercial evidence"
            )
        if value.claim_type == "payment_reason" and not any(
            outcome.outcome_type in DIRECT_PAYMENT_OUTCOMES
            and outcome.direction == "supports"
            for outcome, _ in commercial_rows
        ):
            raise OntologyClaimError(
                "Payment reason requires verified direct payment evidence"
            )
        support_origins = [
            EvidenceOrigin(
                source_id=membership.source_id,
                entity_id=membership.entity_id,
                content_id=membership.document_id,
            )
            for evidence_id, membership in memberships.items()
            if evidence_id in support_ids
        ]
        assessment = (
            assess_source_independence(self._session, support_origins)
            if support_origins
            else None
        )
        fingerprint = _proposal_fingerprint(
            cluster.id,
            value.claim_type,
            statement,
            generator_key,
            generator_version,
            support_ids,
            refute_ids,
            {outcome.id for outcome, _ in commercial_rows},
        )
        existing = self._session.scalar(
            select(EvidenceClaim).where(
                EvidenceClaim.input_fingerprint == fingerprint
            )
        )
        if existing is not None:
            return existing
        supporting_commercial_count = sum(
            outcome.direction == "supports"
            for outcome, _ in commercial_rows
        )
        claim = EvidenceClaim(
            cluster_id=cluster.id,
            supersedes_claim_id=None,
            claim_type=value.claim_type,
            statement=statement,
            status="pending_review",
            generator_key=generator_key,
            generator_version=generator_version,
            input_fingerprint=fingerprint,
            evidence_level=(
                assessment.evidence_level
                if assessment is not None
                else "commercially_verified"
            ),
            source_count=assessment.source_count if assessment else 0,
            independence_group_count=(
                assessment.independence_group_count if assessment else 0
            ),
            supporting_evidence_count=(
                len(support_ids) + supporting_commercial_count
            ),
            independence_blockers=(
                list(assessment.blockers) if assessment else []
            ),
            is_current=False,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(claim)
        self._session.flush()
        for evidence_id in sorted(support_ids | refute_ids, key=str):
            self._session.add(
                ClaimEvidenceLink(
                    claim_id=claim.id,
                    problem_evidence_id=evidence_id,
                    source_id=memberships[evidence_id].source_id,
                    direction=(
                        "supports"
                        if evidence_id in support_ids
                        else "refutes"
                    ),
                    created_at=datetime.now(UTC),
                )
            )
        for outcome, _ in commercial_rows:
            self._session.add(
                ClaimCommercialOutcomeLink(
                    claim_id=claim.id,
                    outcome_id=outcome.id,
                    direction=outcome.direction,
                    created_at=datetime.now(UTC),
                )
            )
        self._session.commit()
        return claim

    def review(
        self,
        value: EvidenceClaimReviewInput,
    ) -> EvidenceClaimReview:
        claim = self._session.get(EvidenceClaim, value.claim_id)
        if claim is None:
            raise OntologyClaimError("Evidence claim not found")
        version = _required_text(value.version, "review version", 80)
        reviewer = _required_text(value.reviewer, "reviewer", 200)
        rationale = _required_text(value.rationale, "rationale", 4_000)
        if reviewer == claim.created_by:
            raise OntologyClaimError(
                "Claim creator cannot review the same claim"
            )
        if value.decision not in {"approved", "rejected"}:
            raise OntologyClaimError("Unsupported claim review decision")
        existing = self._session.scalar(
            select(EvidenceClaimReview).where(
                EvidenceClaimReview.claim_id == claim.id,
                EvidenceClaimReview.version == version,
            )
        )
        if existing is not None:
            if (
                existing.decision == value.decision
                and existing.reviewer == reviewer
                and existing.rationale == rationale
            ):
                return existing
            raise OntologyClaimError(
                "Claim review version already exists with different content"
            )
        if claim.status != "pending_review":
            raise OntologyClaimError("Only pending claims can be reviewed")
        if value.decision == "approved":
            self._validate_approval(claim)
            previous = self._session.scalar(
                select(EvidenceClaim)
                .where(
                    EvidenceClaim.cluster_id == claim.cluster_id,
                    EvidenceClaim.claim_type == claim.claim_type,
                    EvidenceClaim.is_current.is_(True),
                    EvidenceClaim.id != claim.id,
                )
                .order_by(
                    EvidenceClaim.created_at.desc(),
                    EvidenceClaim.id.desc(),
                )
                .limit(1)
            )
            if previous is not None:
                previous.is_current = False
                claim.supersedes_claim_id = previous.id
            claim.status = "grounded"
            claim.is_current = True
        else:
            claim.status = "rejected"
            claim.is_current = False
        review = EvidenceClaimReview(
            claim_id=claim.id,
            version=version,
            previous_status="pending_review",
            decision=value.decision,
            reviewer=reviewer,
            rationale=rationale,
            reviewed_at=datetime.now(UTC),
        )
        self._session.add(review)
        self._session.commit()
        return review

    def _validate_approval(self, claim: EvidenceClaim) -> None:
        problem_links = list(
            self._session.scalars(
                select(ClaimEvidenceLink).where(
                    ClaimEvidenceLink.claim_id == claim.id
                )
            )
        )
        commercial_links = list(
            self._session.scalars(
                select(ClaimCommercialOutcomeLink).where(
                    ClaimCommercialOutcomeLink.claim_id == claim.id
                )
            )
        )
        directions = {
            link.direction for link in [*problem_links, *commercial_links]
        }
        if "supports" not in directions:
            raise OntologyClaimError(
                "Claim has no supporting evidence"
            )
        if "refutes" in directions:
            raise OntologyClaimError(
                "Claim has unresolved counter-evidence"
            )
        if claim.claim_type == "payment_reason":
            outcome_ids = {link.outcome_id for link in commercial_links}
            rows = self._commercial_outcomes(claim.cluster_id, outcome_ids)
            if not any(
                outcome.outcome_type in DIRECT_PAYMENT_OUTCOMES
                and outcome.direction == "supports"
                for outcome, _ in rows
            ):
                raise OntologyClaimError(
                    "Payment reason lost direct payment verification"
                )

    def _cluster_memberships(
        self,
        cluster_id: uuid.UUID,
        evidence_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, ProblemClusterMembership]:
        if not evidence_ids:
            return {}
        memberships_by_document = {
            membership.document_id: membership
            for membership in self._session.scalars(
                select(ProblemClusterMembership).where(
                    ProblemClusterMembership.cluster_id == cluster_id,
                )
            )
        }
        evidence = list(
            self._session.scalars(
                select(ProblemEvidence).where(
                    ProblemEvidence.id.in_(evidence_ids)
                )
            )
        )
        if (
            {item.id for item in evidence} != evidence_ids
            or any(
                item.document_id not in memberships_by_document
                for item in evidence
            )
        ):
            raise OntologyClaimError(
                "Problem evidence does not belong to the cluster"
            )
        return {
            item.id: memberships_by_document[item.document_id]
            for item in evidence
        }

    def _verified_direct_outcomes(
        self,
        cluster_id: uuid.UUID,
    ) -> list[tuple[CommercialOutcome, CommercialValidationExperiment]]:
        return list(
            self._session.execute(
                select(
                    CommercialOutcome,
                    CommercialValidationExperiment,
                )
                .join(
                    CommercialValidationExperiment,
                    CommercialValidationExperiment.id
                    == CommercialOutcome.experiment_id,
                )
                .where(
                    CommercialValidationExperiment.cluster_id == cluster_id,
                    CommercialOutcome.verification_status == "verified",
                    CommercialOutcome.verified_at.is_not(None),
                    CommercialOutcome.direction == "supports",
                    CommercialOutcome.outcome_type.in_(
                        DIRECT_PAYMENT_OUTCOMES
                    ),
                )
                .order_by(
                    CommercialOutcome.occurred_at.desc(),
                    CommercialOutcome.id,
                )
            )
        )

    def _commercial_outcomes(
        self,
        cluster_id: uuid.UUID,
        outcome_ids: set[uuid.UUID],
    ) -> list[tuple[CommercialOutcome, CommercialValidationExperiment]]:
        if not outcome_ids:
            return []
        rows = list(
            self._session.execute(
                select(
                    CommercialOutcome,
                    CommercialValidationExperiment,
                )
                .join(
                    CommercialValidationExperiment,
                    CommercialValidationExperiment.id
                    == CommercialOutcome.experiment_id,
                )
                .where(
                    CommercialOutcome.id.in_(outcome_ids),
                    CommercialValidationExperiment.cluster_id == cluster_id,
                    CommercialOutcome.verification_status == "verified",
                    CommercialOutcome.verified_at.is_not(None),
                )
            )
        )
        if {outcome.id for outcome, _ in rows} != outcome_ids:
            raise OntologyClaimError(
                "Commercial evidence is missing, unverified or from "
                "another cluster"
            )
        return rows


def _observed_contexts(
    documents: Iterable[NormalizedDocument],
) -> str:
    tags: set[str] = set()
    repositories: set[str] = set()
    document_types: set[str] = set()
    for document in documents:
        document_types.add(document.document_type)
        tags.update(
            item
            for item in document.attributes.get("tags", [])
            if isinstance(item, str)
        )
        repository = document.attributes.get("repository_full_name")
        if isinstance(repository, str) and repository:
            repositories.add(repository)
    parts: list[str] = []
    if tags:
        parts.append("tags " + ", ".join(sorted(tags)[:5]))
    if repositories:
        parts.append(
            "repositories " + ", ".join(sorted(repositories)[:5])
        )
    if document_types:
        parts.append(
            "document types " + ", ".join(sorted(document_types)[:5])
        )
    return "; ".join(parts)


def _first_excerpt(
    evidence_by_id: dict[uuid.UUID, ProblemEvidence],
    evidence_ids: tuple[uuid.UUID, ...],
) -> str:
    return evidence_by_id[evidence_ids[0]].excerpt.strip()[:500]


def _unique_text(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values))[:5]


def _required_text(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise OntologyClaimError(f"{field} is required")
    if len(normalized) > maximum:
        raise OntologyClaimError(f"{field} exceeds {maximum} characters")
    return normalized


def _proposal_fingerprint(
    cluster_id: uuid.UUID,
    claim_type: str,
    statement: str,
    generator_key: str,
    generator_version: str,
    support_ids: set[uuid.UUID],
    refute_ids: set[uuid.UUID],
    commercial_ids: set[uuid.UUID],
) -> str:
    payload = {
        "cluster_id": str(cluster_id),
        "claim_type": claim_type,
        "statement": statement,
        "generator_key": generator_key,
        "generator_version": generator_version,
        "support_ids": sorted(str(item) for item in support_ids),
        "refute_ids": sorted(str(item) for item in refute_ids),
        "commercial_ids": sorted(str(item) for item in commercial_ids),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
