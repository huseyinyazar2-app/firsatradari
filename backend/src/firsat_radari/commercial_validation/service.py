import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    CommercialContactPreference,
    CommercialOutcome,
    CommercialOutcomeReview,
    CommercialValidationExperiment,
    Opportunity,
    OpportunityVersion,
    ProblemCluster,
)

EXPERIMENT_TYPES = frozenset(
    {
        "customer_interview",
        "price_test",
        "pilot_offer",
        "pre_sale",
        "contract_negotiation",
        "landing_page",
    }
)
SUPPORTING_OUTCOMES = frozenset(
    {
        "qualified_interview",
        "price_acceptance",
        "pilot_commitment",
        "prepayment",
        "contract",
        "sale",
        "repeat_usage",
        "renewal",
        "landing_page_signup",
        "qualified_lead",
        "meeting_scheduled",
    }
)
REFUTING_OUTCOMES = frozenset({"rejection", "no_budget"})
DIRECT_PAYMENT_OUTCOMES = frozenset(
    {"prepayment", "contract", "sale", "renewal"}
)
_OPAQUE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
EXPERIMENT_COHORTS = frozenset({"radar", "control", "baseline"})
CONTACT_CHANNELS = frozenset({"email", "phone", "sms", "messaging", "all"})
CONTACT_STATUSES = frozenset({"opt_in", "opt_out"})


class CommercialValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExperimentInput:
    cluster_id: uuid.UUID
    opportunity_version_id: uuid.UUID | None
    external_key: str
    protocol_key: str
    cohort: str
    experiment_type: str
    target_segment: str
    hypothesis: str
    status: str
    started_at: datetime
    created_by: str


@dataclass(frozen=True)
class OutcomeInput:
    experiment_id: uuid.UUID
    idempotency_key: str
    participant_key: str
    outcome_type: str
    amount: Decimal | None
    currency: str | None
    evidence_reference: str | None
    notes: str | None
    occurred_at: datetime
    created_by: str


@dataclass(frozen=True)
class OutcomeReviewInput:
    outcome_id: uuid.UUID
    new_status: str
    reviewer: str
    notes: str


@dataclass(frozen=True)
class ContactPreferenceInput:
    participant_key: str
    channel: str
    scope: str
    status: str
    evidence_reference: str | None
    recorded_by: str


class CommercialValidationService:
    def __init__(self, session: Session, hash_secret: str) -> None:
        if len(hash_secret) < 16:
            raise CommercialValidationError(
                "Validation hash secret must contain at least 16 characters"
            )
        self._session = session
        self._hash_secret = hash_secret.encode()

    def create_experiment(
        self,
        value: ExperimentInput,
    ) -> CommercialValidationExperiment:
        cluster = self._session.get(ProblemCluster, value.cluster_id)
        if cluster is None:
            raise CommercialValidationError("Problem cluster not found")
        if cluster.status != "cross_entity_candidate":
            raise CommercialValidationError(
                "Commercial validation requires a cross-entity candidate"
            )
        opportunity_version = None
        if value.opportunity_version_id is not None:
            opportunity_version = self._session.get(
                OpportunityVersion,
                value.opportunity_version_id,
            )
            opportunity = (
                self._session.get(
                    Opportunity,
                    opportunity_version.opportunity_id,
                )
                if opportunity_version is not None
                else None
            )
            if (
                opportunity_version is None
                or opportunity is None
                or opportunity.origin_cluster_id != cluster.id
            ):
                raise CommercialValidationError(
                    "Opportunity version does not belong to the experiment cluster"
                )
        external_key = _limited_opaque_key(
            value.external_key,
            "external_key",
            80,
        )
        protocol_key = _limited_opaque_key(
            value.protocol_key,
            "protocol_key",
            80,
        )
        if value.cohort not in EXPERIMENT_COHORTS:
            raise CommercialValidationError("Unsupported experiment cohort")
        if value.experiment_type not in EXPERIMENT_TYPES:
            raise CommercialValidationError("Unsupported experiment type")
        if value.status not in {"planned", "running"}:
            raise CommercialValidationError(
                "New experiment status must be planned or running"
            )
        target_segment = _required_text(
            value.target_segment,
            "target_segment",
            maximum=2_000,
        )
        hypothesis = _required_text(
            value.hypothesis,
            "hypothesis",
            maximum=4_000,
        )
        created_by = _required_text(
            value.created_by,
            "created_by",
            maximum=200,
        )
        existing = self._session.scalar(
            select(CommercialValidationExperiment).where(
                CommercialValidationExperiment.cluster_id == cluster.id,
                CommercialValidationExperiment.external_key == external_key,
            )
        )
        if existing is not None:
            if (
                existing.experiment_type != value.experiment_type
                or existing.opportunity_version_id
                != value.opportunity_version_id
                or existing.protocol_key != protocol_key
                or existing.cohort != value.cohort
                or existing.target_segment != target_segment
                or existing.hypothesis != hypothesis
                or existing.status != value.status
                or _as_utc(existing.started_at)
                != _as_utc(value.started_at)
            ):
                raise CommercialValidationError(
                    "Experiment external key was already used with "
                    "different data"
                )
            return existing
        experiment = CommercialValidationExperiment(
            cluster_id=cluster.id,
            opportunity_version_id=value.opportunity_version_id,
            external_key=external_key,
            protocol_key=protocol_key,
            cohort=value.cohort,
            experiment_type=value.experiment_type,
            target_segment=target_segment,
            hypothesis=hypothesis,
            status=value.status,
            started_at=_as_utc(value.started_at),
            ended_at=None,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(experiment)
        self._session.commit()
        return experiment

    def add_outcome(self, value: OutcomeInput) -> CommercialOutcome:
        experiment = self._session.get(
            CommercialValidationExperiment,
            value.experiment_id,
        )
        if experiment is None:
            raise CommercialValidationError(
                "Commercial validation experiment not found"
            )
        if experiment.status not in {"planned", "running"}:
            raise CommercialValidationError(
                "Commercial validation experiment is not active"
            )
        idempotency_key = _opaque_key(
            value.idempotency_key,
            "idempotency_key",
        )
        participant_key = _opaque_key(
            value.participant_key,
            "participant_key",
        )
        participant_hash = hmac.new(
            self._hash_secret,
            participant_key.encode(),
            hashlib.sha256,
        ).hexdigest()
        if value.outcome_type in SUPPORTING_OUTCOMES:
            direction = "supports"
        elif value.outcome_type in REFUTING_OUTCOMES:
            direction = "refutes"
        else:
            raise CommercialValidationError("Unsupported outcome type")
        amount, currency = _money(
            value.amount,
            value.currency,
            required=value.outcome_type in DIRECT_PAYMENT_OUTCOMES,
        )
        evidence_reference = _optional_text(
            value.evidence_reference,
            maximum=800,
        )
        if (
            value.outcome_type in DIRECT_PAYMENT_OUTCOMES
            and evidence_reference is None
        ):
            raise CommercialValidationError(
                "Direct payment outcome requires an evidence reference"
            )
        notes = _optional_text(value.notes, maximum=2_000)
        occurred_at = _as_utc(value.occurred_at)
        if occurred_at > datetime.now(UTC):
            raise CommercialValidationError(
                "Commercial outcome cannot occur in the future"
            )
        created_by = _required_text(
            value.created_by,
            "created_by",
            maximum=200,
        )
        existing = self._session.scalar(
            select(CommercialOutcome).where(
                CommercialOutcome.experiment_id == experiment.id,
                CommercialOutcome.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.participant_key_hash != participant_hash
                or existing.outcome_type != value.outcome_type
                or existing.amount != amount
                or existing.currency != currency
                or existing.evidence_reference != evidence_reference
                or existing.notes != notes
                or _as_utc(existing.occurred_at) != occurred_at
            ):
                raise CommercialValidationError(
                    "Idempotency key was already used with different data"
                )
            return existing
        outcome = CommercialOutcome(
            experiment_id=experiment.id,
            idempotency_key=idempotency_key,
            participant_key_hash=participant_hash,
            outcome_type=value.outcome_type,
            direction=direction,
            amount=amount,
            currency=currency,
            evidence_reference=evidence_reference,
            notes=notes,
            verification_status="pending",
            occurred_at=occurred_at,
            created_by=created_by,
            created_at=datetime.now(UTC),
            verified_at=None,
            verifier=None,
            verification_notes=None,
        )
        self._session.add(outcome)
        self._session.commit()
        return outcome

    def close_experiment(
        self,
        experiment_id: uuid.UUID,
        *,
        new_status: str,
        ended_at: datetime,
    ) -> CommercialValidationExperiment:
        experiment = self._session.get(
            CommercialValidationExperiment,
            experiment_id,
        )
        if experiment is None:
            raise CommercialValidationError(
                "Commercial validation experiment not found"
            )
        if new_status not in {"completed", "cancelled"}:
            raise CommercialValidationError(
                "Experiment can only be completed or cancelled"
            )
        normalized_end = _as_utc(ended_at)
        if normalized_end < _as_utc(experiment.started_at):
            raise CommercialValidationError(
                "Experiment cannot end before it started"
            )
        if normalized_end > datetime.now(UTC) + timedelta(minutes=5):
            raise CommercialValidationError(
                "Experiment cannot end in the future"
            )
        if experiment.status in {"completed", "cancelled"}:
            if (
                experiment.status != new_status
                or experiment.ended_at is None
                or _as_utc(experiment.ended_at) != normalized_end
            ):
                raise CommercialValidationError(
                    "Experiment is already closed with another result"
                )
            return experiment
        experiment.status = new_status
        experiment.ended_at = normalized_end
        self._session.commit()
        return experiment

    def record_contact_preference(
        self,
        value: ContactPreferenceInput,
    ) -> CommercialContactPreference:
        participant_key = _opaque_key(
            value.participant_key,
            "participant_key",
        )
        if value.channel not in CONTACT_CHANNELS:
            raise CommercialValidationError("Unsupported contact channel")
        if value.status not in CONTACT_STATUSES:
            raise CommercialValidationError("Unsupported contact preference")
        scope = _limited_opaque_key(value.scope, "scope", 80)
        recorded_by = _required_text(
            value.recorded_by,
            "recorded_by",
            maximum=200,
        )
        evidence_reference = _optional_text(
            value.evidence_reference,
            maximum=800,
        )
        participant_hash = hmac.new(
            self._hash_secret,
            participant_key.encode(),
            hashlib.sha256,
        ).hexdigest()
        previous = self._session.scalar(
            select(CommercialContactPreference)
            .where(
                CommercialContactPreference.participant_key_hash
                == participant_hash,
                CommercialContactPreference.channel == value.channel,
                CommercialContactPreference.scope == scope,
            )
            .order_by(CommercialContactPreference.recorded_at.desc())
            .limit(1)
        )
        if (
            previous is not None
            and previous.status == value.status
            and previous.evidence_reference == evidence_reference
        ):
            return previous
        result = CommercialContactPreference(
            participant_key_hash=participant_hash,
            channel=value.channel,
            scope=scope,
            status=value.status,
            evidence_reference=evidence_reference,
            recorded_by=recorded_by,
            recorded_at=datetime.now(UTC),
        )
        self._session.add(result)
        self._session.commit()
        return result

    def review_outcome(
        self,
        value: OutcomeReviewInput,
    ) -> CommercialOutcome:
        outcome = self._session.get(CommercialOutcome, value.outcome_id)
        if outcome is None:
            raise CommercialValidationError(
                "Commercial outcome not found"
            )
        if value.new_status not in {"verified", "rejected"}:
            raise CommercialValidationError(
                "Review status must be verified or rejected"
            )
        reviewer = _required_text(
            value.reviewer,
            "reviewer",
            maximum=200,
        )
        notes = _required_text(
            value.notes,
            "review_notes",
            maximum=2_000,
        )
        if reviewer.casefold() == outcome.created_by.casefold():
            raise CommercialValidationError(
                "Commercial outcome reviewer must differ from its creator"
            )
        if outcome.verification_status == value.new_status:
            return outcome
        if outcome.verification_status != "pending":
            raise CommercialValidationError(
                "Commercial outcome review is already final"
            )
        previous_status = outcome.verification_status
        reviewed_at = datetime.now(UTC)
        outcome.verification_status = value.new_status
        outcome.verified_at = reviewed_at
        outcome.verifier = reviewer
        outcome.verification_notes = notes
        self._session.add(
            CommercialOutcomeReview(
                outcome_id=outcome.id,
                previous_status=previous_status,
                new_status=value.new_status,
                reviewer=reviewer,
                notes=notes,
                reviewed_at=reviewed_at,
            )
        )
        self._session.commit()
        return outcome


def _money(
    amount: Decimal | None,
    currency: str | None,
    *,
    required: bool,
) -> tuple[Decimal | None, str | None]:
    if amount is None and currency is None and not required:
        return None, None
    if amount is None or amount <= 0:
        raise CommercialValidationError(
            "Monetary amount must be greater than zero"
        )
    normalized_currency = currency.strip().upper() if currency else ""
    if not _CURRENCY.fullmatch(normalized_currency):
        raise CommercialValidationError(
            "Currency must be a three-letter ISO code"
        )
    return amount.quantize(Decimal("0.01")), normalized_currency


def _opaque_key(value: str, field: str) -> str:
    normalized = value.strip()
    if not _OPAQUE_KEY.fullmatch(normalized):
        raise CommercialValidationError(
            f"{field} must be an opaque non-personal identifier"
        )
    return normalized


def _limited_opaque_key(
    value: str,
    field: str,
    maximum: int,
) -> str:
    normalized = _opaque_key(value, field)
    if len(normalized) > maximum:
        raise CommercialValidationError(f"{field} is too long")
    return normalized


def _required_text(value: str, field: str, *, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise CommercialValidationError(f"{field} is required")
    if len(normalized) > maximum:
        raise CommercialValidationError(f"{field} is too long")
    return normalized


def _optional_text(value: str | None, *, maximum: int) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()[:maximum]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
