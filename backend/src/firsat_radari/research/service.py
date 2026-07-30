import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    ClaimCommercialOutcomeLink,
    ClaimEvidenceLink,
    CommercialOutcome,
    CommercialValidationExperiment,
    DataSource,
    EvidenceClaim,
    EvidenceClaimReview,
    NormalizedDocument,
    Opportunity,
    OpportunityComponentClaimLink,
    OpportunityExport,
    OpportunityResearchRun,
    OpportunityReview,
    OpportunityScoreRun,
    OpportunityScoreSnapshot,
    OpportunityVersion,
    ProblemEvidence,
)
from firsat_radari.opportunities.materialization import (
    REQUIRED_COMPONENT_CLAIM_TYPES,
)

_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")
RESEARCH_TIERS = frozenset({"evidence_review", "validation_ready"})


class ResearchError(ValueError):
    pass


@dataclass(frozen=True)
class ResearchRequest:
    opportunity_version_id: uuid.UUID
    research_tier: str
    focus_questions: tuple[str, ...]
    requested_by: str


@dataclass(frozen=True)
class ExportRequest:
    opportunity_version_id: uuid.UUID
    research_run_id: uuid.UUID
    destination: str
    idempotency_key: str
    created_by: str


class OpportunityResearchService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def research(self, request: ResearchRequest) -> OpportunityResearchRun:
        version = self._session.get(
            OpportunityVersion,
            request.opportunity_version_id,
        )
        if version is None:
            raise ResearchError("Opportunity version not found")
        if request.research_tier not in RESEARCH_TIERS:
            raise ResearchError("Unsupported research tier")
        questions = _questions(request.focus_questions)
        requested_by = _required_text(request.requested_by, "requested_by", 200)
        started_at = datetime.now(UTC)

        component_links = list(
            self._session.scalars(
                select(OpportunityComponentClaimLink)
                .where(
                    OpportunityComponentClaimLink.opportunity_version_id
                    == version.id
                )
                .order_by(OpportunityComponentClaimLink.component_key)
            )
        )
        components: list[dict] = []
        fingerprint_parts = [
            str(version.id),
            version.input_fingerprint,
            request.research_tier,
            *questions,
        ]
        blockers: list[str] = []
        risk_flags: list[str] = []
        present_components = {link.component_key for link in component_links}
        missing_components = sorted(
            set(REQUIRED_COMPONENT_CLAIM_TYPES) - present_components
        )
        blockers.extend(f"missing_component:{key}" for key in missing_components)

        for component_link in component_links:
            claim = self._session.get(EvidenceClaim, component_link.claim_id)
            if claim is None:
                blockers.append(
                    f"missing_claim:{component_link.component_key}"
                )
                continue
            fingerprint_parts.append(str(claim.id))
            evidence_links = list(
                self._session.scalars(
                    select(ClaimEvidenceLink)
                    .where(ClaimEvidenceLink.claim_id == claim.id)
                    .order_by(ClaimEvidenceLink.id)
                )
            )
            commercial_links = list(
                self._session.scalars(
                    select(ClaimCommercialOutcomeLink)
                    .where(ClaimCommercialOutcomeLink.claim_id == claim.id)
                    .order_by(ClaimCommercialOutcomeLink.id)
                )
            )
            latest_claim_review = self._session.scalar(
                select(EvidenceClaimReview)
                .where(EvidenceClaimReview.claim_id == claim.id)
                .order_by(EvidenceClaimReview.reviewed_at.desc())
                .limit(1)
            )
            if latest_claim_review is not None:
                fingerprint_parts.append(str(latest_claim_review.id))
            review_approved = (
                latest_claim_review is not None
                and latest_claim_review.decision == "approved"
            )
            evidence: list[dict] = []
            for link in evidence_links:
                fingerprint_parts.extend((str(link.id), link.direction))
                if link.direction == "refutes":
                    risk_flags.append(
                        f"counterevidence:{component_link.component_key}"
                    )
                item = self._session.get(
                    ProblemEvidence,
                    link.problem_evidence_id,
                )
                if item is None:
                    continue
                document = self._session.get(
                    NormalizedDocument,
                    item.document_id,
                )
                source = self._session.get(DataSource, link.source_id)
                attributes = document.attributes if document is not None else {}
                evidence.append(
                    {
                        "evidence_id": str(item.id),
                        "source_id": str(link.source_id),
                        "source_name": source.owner if source is not None else None,
                        "source_url": (
                            document.canonical_url
                            if document is not None
                            else None
                        ),
                        "source_license": attributes.get("content_license"),
                        "attribution_required": bool(
                            attributes.get("attribution_required", False)
                        ),
                        "direction": link.direction,
                        "excerpt": item.excerpt,
                        "confidence": str(item.confidence),
                        "document_id": str(item.document_id),
                    }
                )
            commercial_evidence: list[dict] = []
            for link in commercial_links:
                fingerprint_parts.extend((str(link.id), link.direction))
                if link.direction == "refutes":
                    risk_flags.append(
                        f"commercial_counterevidence:{component_link.component_key}"
                    )
                outcome = self._session.get(CommercialOutcome, link.outcome_id)
                if outcome is None:
                    continue
                commercial_evidence.append(
                    {
                        "outcome_id": str(outcome.id),
                        "direction": link.direction,
                        "outcome_type": outcome.outcome_type,
                        "amount": (
                            str(outcome.amount)
                            if outcome.amount is not None
                            else None
                        ),
                        "currency": outcome.currency,
                        "verification_status": outcome.verification_status,
                        "occurred_at": outcome.occurred_at.isoformat(),
                    }
                )
            components.append(
                {
                    "component_key": component_link.component_key,
                    "claim_id": str(claim.id),
                    "statement": claim.statement,
                    "status": (
                        "approved" if review_approved else claim.status
                    ),
                    "evidence_level": claim.evidence_level,
                    "source_count": claim.source_count,
                    "independence_group_count": claim.independence_group_count,
                    "evidence": evidence,
                    "commercial_evidence": commercial_evidence,
                }
            )
            if not review_approved:
                blockers.append(
                    f"claim_not_approved:{component_link.component_key}"
                )

        score = self._latest_score(version.id)
        if score is None:
            blockers.append("missing_score")
            score_snapshot = None
        else:
            fingerprint_parts.append(str(score.id))
            score_snapshot = {
                "score_snapshot_id": str(score.id),
                "potential_score": str(score.potential_score),
                "actionability_score": str(score.actionability_score),
                "confidence_score": str(score.confidence_score),
                "uncertainty": str(score.uncertainty),
                "total_score": (
                    str(score.total_score)
                    if score.total_score is not None
                    else None
                ),
                "status": score.status,
                "components": score.components,
            }
            if score.status != "rankable":
                blockers.append(f"score_status:{score.status}")

        opportunity = self._session.get(Opportunity, version.opportunity_id)
        validation = self._validation_snapshot(
            version.id,
            opportunity.origin_cluster_id if opportunity else None
        )
        fingerprint_parts.extend(validation["fingerprint_parts"])
        input_fingerprint = hashlib.sha256(
            "\n".join(fingerprint_parts).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(OpportunityResearchRun).where(
                OpportunityResearchRun.opportunity_version_id == version.id,
                OpportunityResearchRun.input_fingerprint == input_fingerprint,
            )
        )
        if existing is not None:
            return existing

        unique_blockers = sorted(set(blockers))
        evidence_snapshot = {
            "opportunity_version_id": str(version.id),
            "ontology_schema_version": version.ontology_schema_version,
            "evidence_level": version.evidence_level,
            "components": components,
            "score": score_snapshot,
            "validation": validation["summary"],
            "risk_flags": sorted(set(risk_flags)),
            "future_data_used": False,
        }
        findings = {
            "title": version.title,
            "ontology": version.ontology,
            "focus_questions": list(questions),
            "knowns": [
                {
                    "component_key": item["component_key"],
                    "statement": item["statement"],
                    "evidence_level": item["evidence_level"],
                }
                for item in components
            ],
            "unknowns": unique_blockers,
            "risk_flags": sorted(set(risk_flags)),
            "question_assessments": [
                {
                    "question": question,
                    "status": (
                        "evidence_available"
                        if components
                        else "insufficient_evidence"
                    ),
                    "supporting_components": [
                        item["component_key"] for item in components
                    ],
                    "caveat": (
                        "Assessment is limited to the versioned evidence "
                        "snapshot; no unsupported answer was generated."
                    ),
                }
                for question in questions
            ],
            "recommended_next_test": _recommended_test(
                score,
                validation["summary"]["verified_outcomes"],
            ),
        }
        run = OpportunityResearchRun(
            opportunity_version_id=version.id,
            research_tier=request.research_tier,
            focus_questions=list(questions),
            input_fingerprint=input_fingerprint,
            status="blocked" if unique_blockers else "succeeded",
            evidence_snapshot=evidence_snapshot,
            findings=findings,
            blockers=unique_blockers,
            requested_by=requested_by,
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )
        self._session.add(run)
        self._session.commit()
        return run

    def prepare_export(self, request: ExportRequest) -> OpportunityExport:
        version = self._session.get(
            OpportunityVersion,
            request.opportunity_version_id,
        )
        run = self._session.get(OpportunityResearchRun, request.research_run_id)
        if version is None or run is None:
            raise ResearchError("Opportunity version or research run not found")
        if run.opportunity_version_id != version.id:
            raise ResearchError("Research run belongs to another opportunity version")
        if run.status != "succeeded":
            raise ResearchError("Blocked research cannot be exported")
        latest_review = self._session.scalar(
            select(OpportunityReview)
            .where(OpportunityReview.opportunity_version_id == version.id)
            .order_by(OpportunityReview.created_at.desc())
            .limit(1)
        )
        if latest_review is None or latest_review.decision != "validate":
            raise ResearchError(
                "Latest manual decision must be validate before export"
            )
        destination = _required_text(request.destination, "destination", 80)
        idempotency_key = request.idempotency_key.strip()
        if not _KEY.fullmatch(idempotency_key):
            raise ResearchError("Invalid export idempotency key")
        created_by = _required_text(request.created_by, "created_by", 200)
        existing = self._session.scalar(
            select(OpportunityExport).where(
                OpportunityExport.destination == destination,
                OpportunityExport.idempotency_key == idempotency_key,
            )
        )
        payload = {
            "schema_version": "opportunity-export-v1",
            "opportunity_version_id": str(version.id),
            "title": version.title,
            "ontology": version.ontology,
            "evidence_level": version.evidence_level,
            "research_run_id": str(run.id),
            "research_findings": run.findings,
            "evidence_summary": {
                "component_count": len(
                    run.evidence_snapshot.get("components", [])
                ),
                "score": run.evidence_snapshot.get("score"),
                "validation": run.evidence_snapshot.get("validation"),
            },
            "manual_decision": {
                "decision": latest_review.decision,
                "reviewer": latest_review.reviewer,
                "notes": latest_review.notes,
                "created_at": latest_review.created_at.isoformat(),
            },
        }
        payload_hash = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ).encode()
        ).hexdigest()
        if existing is not None:
            if (
                existing.opportunity_version_id != version.id
                or existing.research_run_id != run.id
                or existing.payload_hash != payload_hash
            ):
                raise ResearchError(
                    "Export idempotency key was used with different data"
                )
            return existing
        result = OpportunityExport(
            opportunity_version_id=version.id,
            research_run_id=run.id,
            destination=destination,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            payload=payload,
            status="prepared",
            created_by=created_by,
            created_at=datetime.now(UTC),
            exported_at=None,
            external_reference=None,
        )
        self._session.add(result)
        self._session.commit()
        return result

    def acknowledge_export(
        self,
        export_id: uuid.UUID,
        external_reference: str,
    ) -> OpportunityExport:
        result = self._session.get(OpportunityExport, export_id)
        if result is None:
            raise ResearchError("Opportunity export not found")
        reference = _required_text(
            external_reference,
            "external_reference",
            300,
        )
        if result.status == "exported":
            if result.external_reference != reference:
                raise ResearchError(
                    "Export was acknowledged with another reference"
                )
            return result
        if result.status != "prepared":
            raise ResearchError("Opportunity export is not prepared")
        result.status = "exported"
        result.external_reference = reference
        result.exported_at = datetime.now(UTC)
        self._session.commit()
        return result

    def _latest_score(
        self,
        version_id: uuid.UUID,
    ) -> OpportunityScoreSnapshot | None:
        return self._session.scalar(
            select(OpportunityScoreSnapshot)
            .join(
                OpportunityScoreRun,
                OpportunityScoreRun.id == OpportunityScoreSnapshot.run_id,
            )
            .where(
                OpportunityScoreSnapshot.opportunity_version_id == version_id,
                OpportunityScoreRun.status == "succeeded",
            )
            .order_by(OpportunityScoreRun.as_of.desc())
            .limit(1)
        )

    def _validation_snapshot(
        self,
        opportunity_version_id: uuid.UUID,
        cluster_id: uuid.UUID | None,
    ) -> dict:
        if cluster_id is None:
            return {
                "fingerprint_parts": [],
                "summary": {
                    "experiment_count": 0,
                    "verified_outcomes": [],
                },
            }
        experiments = list(
            self._session.scalars(
                select(CommercialValidationExperiment)
                .where(
                    CommercialValidationExperiment.cluster_id == cluster_id,
                    CommercialValidationExperiment.opportunity_version_id
                    == opportunity_version_id,
                )
                .order_by(CommercialValidationExperiment.created_at)
            )
        )
        outcomes: list[dict] = []
        fingerprint_parts: list[str] = []
        for experiment in experiments:
            fingerprint_parts.append(str(experiment.id))
            for outcome in self._session.scalars(
                select(CommercialOutcome)
                .where(
                    CommercialOutcome.experiment_id == experiment.id,
                    CommercialOutcome.verification_status == "verified",
                )
                .order_by(CommercialOutcome.occurred_at)
            ):
                fingerprint_parts.append(str(outcome.id))
                outcomes.append(
                    {
                        "outcome_id": str(outcome.id),
                        "experiment_id": str(experiment.id),
                        "experiment_type": experiment.experiment_type,
                        "outcome_type": outcome.outcome_type,
                        "direction": outcome.direction,
                        "amount": (
                            str(outcome.amount)
                            if outcome.amount is not None
                            else None
                        ),
                        "currency": outcome.currency,
                        "occurred_at": outcome.occurred_at.isoformat(),
                    }
                )
        return {
            "fingerprint_parts": fingerprint_parts,
            "summary": {
                "experiment_count": len(experiments),
                "verified_outcomes": outcomes,
            },
        }


def _recommended_test(
    score: OpportunityScoreSnapshot | None,
    verified_outcomes: list[dict],
) -> str:
    direct = {
        "prepayment",
        "contract",
        "sale",
        "renewal",
    }
    if any(item["outcome_type"] in direct for item in verified_outcomes):
        return "pilot_offer"
    if score is None or score.confidence_score < Decimal("0.60"):
        return "customer_interview"
    return "price_test"


def _questions(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        if len(item) > 500:
            raise ResearchError("Focus question is too long")
        if item not in normalized:
            normalized.append(item)
    if len(normalized) > 20:
        raise ResearchError("At most 20 focus questions are allowed")
    return tuple(normalized)


def _required_text(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ResearchError(f"{field} is required")
    if len(normalized) > maximum:
        raise ResearchError(f"{field} is too long")
    return normalized
