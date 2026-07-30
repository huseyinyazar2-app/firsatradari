import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    SourceIndependenceReview,
    SourcePolicy,
    SourceRelationship,
)

_SOURCE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
_ALLOWED = frozenset({"allowed", "approved"})
_PERMISSION_STATUSES = frozenset({"allowed", "approved", "prohibited", "unknown", "not_applicable"})


class SourceRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class SourceCandidate:
    key: str
    source_type: str
    owner: str
    base_url: str
    evidence_family_key: str = "unknown"
    independence_group_key: str = "unknown"
    independence_status: str = "unknown"


@dataclass(frozen=True)
class SourceRelationshipDeclaration:
    source_key: str
    related_source_key: str
    relationship_type: str
    scope: str
    independence_effect: str
    reviewer: str
    rationale: str


@dataclass(frozen=True)
class SourceIndependenceDecision:
    version: str
    new_status: str
    reviewer: str
    rationale: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyApproval:
    version: str
    reviewer: str
    commercial_use_status: str
    storage_permission: str
    derived_data_permission: str
    llm_processing_permission: str
    retention_days: int
    terms_url: str | None = None
    notes: str | None = None


class SourceRegistryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def register_candidate(self, candidate: SourceCandidate) -> DataSource:
        self._validate_candidate(candidate)
        existing = self._session.scalar(select(DataSource).where(DataSource.key == candidate.key))
        if existing is not None:
            raise SourceRegistryError(f"Source already exists: {candidate.key}")

        source = DataSource(
            key=candidate.key,
            source_type=candidate.source_type.strip(),
            evidence_family_key=candidate.evidence_family_key.strip(),
            independence_group_key=candidate.independence_group_key.strip(),
            independence_status=candidate.independence_status,
            owner=candidate.owner.strip(),
            base_url=candidate.base_url,
            policy_status="candidate",
            policy_version=None,
            commercial_use_status="unknown",
            storage_permission="unknown",
            derived_data_permission="unknown",
            llm_processing_permission="unknown",
            retention_days=None,
            enabled=False,
        )
        self._session.add(source)
        self._session.commit()
        return source

    def declare_relationship(
        self,
        declaration: SourceRelationshipDeclaration,
    ) -> SourceRelationship:
        source = self._get_source(declaration.source_key)
        related_source = self._get_source(declaration.related_source_key)
        if source.id == related_source.id:
            raise SourceRegistryError("A source cannot depend on itself")
        if declaration.independence_effect not in {
            "none",
            "reduces",
            "invalidates",
        }:
            raise SourceRegistryError("Unsupported independence effect")
        if declaration.scope not in {
            "global",
            "same_entity",
            "same_content",
        }:
            raise SourceRegistryError("Unsupported relationship scope")
        if (
            not declaration.relationship_type.strip()
            or not declaration.reviewer.strip()
            or not declaration.rationale.strip()
        ):
            raise SourceRegistryError(
                "Relationship type, reviewer and rationale are required"
            )
        first_source, second_source = sorted(
            (source, related_source),
            key=lambda item: str(item.id),
        )
        existing = self._session.scalar(
            select(SourceRelationship).where(
                SourceRelationship.source_id == first_source.id,
                SourceRelationship.related_source_id == second_source.id,
                SourceRelationship.relationship_type
                == declaration.relationship_type,
                SourceRelationship.scope == declaration.scope,
            )
        )
        if existing is not None:
            raise SourceRegistryError("Source relationship already exists")
        relationship = SourceRelationship(
            source_id=first_source.id,
            related_source_id=second_source.id,
            relationship_type=declaration.relationship_type.strip(),
            scope=declaration.scope,
            independence_effect=declaration.independence_effect,
            status="approved",
            rationale=declaration.rationale.strip(),
            reviewed_at=datetime.now(UTC),
            reviewer=declaration.reviewer.strip(),
        )
        self._session.add(relationship)
        self._session.commit()
        return relationship

    def approve_policy(
        self,
        source_key: str,
        approval: PolicyApproval,
    ) -> SourcePolicy:
        source = self._get_source(source_key)
        self._validate_approval(approval)
        existing = self._session.scalar(
            select(SourcePolicy).where(
                SourcePolicy.source_id == source.id,
                SourcePolicy.version == approval.version,
            )
        )
        if existing is not None:
            raise SourceRegistryError(
                f"Policy version already exists: {source_key}/{approval.version}"
            )

        policy = SourcePolicy(
            source_id=source.id,
            version=approval.version.strip(),
            status="approved",
            reviewed_at=datetime.now(UTC),
            reviewer=approval.reviewer.strip(),
            commercial_use_status=approval.commercial_use_status,
            storage_permission=approval.storage_permission,
            derived_data_permission=approval.derived_data_permission,
            llm_processing_permission=approval.llm_processing_permission,
            retention_days=approval.retention_days,
            terms_url=approval.terms_url,
            notes=approval.notes,
        )
        source.policy_status = "approved"
        source.policy_version = policy.version
        source.commercial_use_status = policy.commercial_use_status
        source.storage_permission = policy.storage_permission
        source.derived_data_permission = policy.derived_data_permission
        source.llm_processing_permission = policy.llm_processing_permission
        source.retention_days = policy.retention_days
        self._session.add(policy)
        self._session.commit()
        return policy

    def review_independence(
        self,
        source_key: str,
        decision: SourceIndependenceDecision,
    ) -> SourceIndependenceReview:
        source = self._get_source(source_key)
        references = self._validate_independence_decision(source, decision)
        existing = self._session.scalar(
            select(SourceIndependenceReview).where(
                SourceIndependenceReview.source_id == source.id,
                SourceIndependenceReview.version == decision.version.strip(),
            )
        )
        if existing is not None:
            if (
                existing.new_status == decision.new_status
                and existing.reviewer == decision.reviewer.strip()
                and existing.rationale == decision.rationale.strip()
                and existing.evidence_references == references
            ):
                return existing
            raise SourceRegistryError(
                "Source independence review version already exists with "
                "different content"
            )

        review = SourceIndependenceReview(
            source_id=source.id,
            version=decision.version.strip(),
            previous_status=source.independence_status,
            new_status=decision.new_status,
            reviewer=decision.reviewer.strip(),
            rationale=decision.rationale.strip(),
            evidence_references=references,
            reviewed_at=datetime.now(UTC),
        )
        source.independence_status = decision.new_status
        self._session.add(review)
        self._session.commit()
        return review

    def set_enabled(self, source_key: str, *, enabled: bool) -> DataSource:
        source = self._get_source(source_key)
        if enabled and (
            source.policy_status != "approved"
            or not source.policy_version
            or source.storage_permission not in _ALLOWED
            or source.retention_days is None
            or source.retention_days < 1
        ):
            raise SourceRegistryError(
                f"Source cannot be enabled without an approved storage policy: {source_key}"
            )
        source.enabled = enabled
        self._session.commit()
        return source

    def _get_source(self, source_key: str) -> DataSource:
        source = self._session.scalar(select(DataSource).where(DataSource.key == source_key))
        if source is None:
            raise SourceRegistryError(f"Source not found: {source_key}")
        return source

    @staticmethod
    def _validate_candidate(candidate: SourceCandidate) -> None:
        if not _SOURCE_KEY_PATTERN.fullmatch(candidate.key):
            raise SourceRegistryError("Source key has an invalid format")
        if not candidate.source_type.strip() or not candidate.owner.strip():
            raise SourceRegistryError("Source type and owner are required")
        if (
            not candidate.evidence_family_key.strip()
            or not candidate.independence_group_key.strip()
            or candidate.independence_status
            not in {"independent", "conditional", "dependent", "unknown"}
        ):
            raise SourceRegistryError("Source independence classification is invalid")
        parsed_url = urlparse(candidate.base_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise SourceRegistryError("Source base URL must use HTTPS")
        if parsed_url.username or parsed_url.password:
            raise SourceRegistryError("Source base URL must not contain credentials")

    @staticmethod
    def _validate_approval(approval: PolicyApproval) -> None:
        if not approval.version.strip() or not approval.reviewer.strip():
            raise SourceRegistryError("Policy version and reviewer are required")
        if approval.commercial_use_status not in _ALLOWED:
            raise SourceRegistryError("Commercial use must be explicitly allowed")
        if approval.storage_permission not in _ALLOWED:
            raise SourceRegistryError("Raw storage must be explicitly allowed")
        permissions = {
            "derived data": approval.derived_data_permission,
            "LLM processing": approval.llm_processing_permission,
        }
        for permission_name, permission_status in permissions.items():
            if permission_status not in _PERMISSION_STATUSES:
                raise SourceRegistryError(f"Unsupported {permission_name} permission status")
        if not 1 <= approval.retention_days <= 3_650:
            raise SourceRegistryError("Retention must be between 1 and 3650 days")
        if approval.terms_url is not None:
            parsed_url = urlparse(approval.terms_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise SourceRegistryError("Terms URL must use HTTPS")

    @staticmethod
    def _validate_independence_decision(
        source: DataSource,
        decision: SourceIndependenceDecision,
    ) -> list[str]:
        if (
            not decision.version.strip()
            or not decision.reviewer.strip()
            or not decision.rationale.strip()
        ):
            raise SourceRegistryError(
                "Review version, reviewer and rationale are required"
            )
        if decision.new_status not in {
            "independent",
            "conditional",
            "dependent",
            "unknown",
        }:
            raise SourceRegistryError("Unsupported source independence status")
        references = list(
            dict.fromkeys(
                reference.strip()
                for reference in decision.evidence_references
            )
        )
        if any(not reference for reference in references):
            raise SourceRegistryError("Evidence references must not be empty")
        for reference in references:
            parsed_url = urlparse(reference)
            if (
                parsed_url.scheme != "https"
                or not parsed_url.netloc
                or parsed_url.username
                or parsed_url.password
            ):
                raise SourceRegistryError(
                    "Evidence references must be credential-free HTTPS URLs"
                )
        if decision.new_status == "independent":
            if source.independence_group_key == "unknown":
                raise SourceRegistryError(
                    "An independent source requires a known independence group"
                )
            if not references:
                raise SourceRegistryError(
                    "An independent decision requires evidence references"
                )
        return references
