import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    OpportunityProfileEvaluation,
    OpportunityVersion,
    ResearchProfile,
    VerticalDefinition,
)

_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class VerticalInput:
    key: str
    version: str
    name: str
    status: str
    config: dict
    selection_rationale: str
    created_by: str


@dataclass(frozen=True)
class ProfileInput:
    vertical_definition_id: uuid.UUID
    key: str
    version: str
    name: str
    status: str
    constraints: dict
    exclusions: dict
    preferences: dict
    created_by: str


@dataclass(frozen=True)
class ProfileEvaluationInput:
    opportunity_version_id: uuid.UUID
    research_profile_id: uuid.UUID
    observed_attributes: dict
    evaluated_by: str


class ResearchProfileService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_vertical(self, value: VerticalInput) -> VerticalDefinition:
        key = _key(value.key)
        version = _version(value.version)
        name = _text(value.name, "name", 200)
        rationale = _text(
            value.selection_rationale,
            "selection_rationale",
            4_000,
        )
        created_by = _text(value.created_by, "created_by", 200)
        if value.status not in {"draft", "active", "paused", "retired"}:
            raise ProfileError("Unsupported vertical status")
        config = _json_object(value.config, "config")
        existing = self._session.scalar(
            select(VerticalDefinition).where(
                VerticalDefinition.key == key,
                VerticalDefinition.version == version,
            )
        )
        if existing is not None:
            expected = (
                name,
                value.status,
                config,
                rationale,
            )
            actual = (
                existing.name,
                existing.status,
                existing.config,
                existing.selection_rationale,
            )
            if actual != expected:
                raise ProfileError(
                    "Vertical version already exists with different data"
                )
            return existing
        for current in self._session.scalars(
            select(VerticalDefinition).where(
                VerticalDefinition.key == key,
                VerticalDefinition.is_current.is_(True),
            )
        ):
            current.is_current = False
        result = VerticalDefinition(
            key=key,
            version=version,
            name=name,
            status=value.status,
            config=config,
            selection_rationale=rationale,
            is_current=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(result)
        self._session.commit()
        return result

    def create_profile(self, value: ProfileInput) -> ResearchProfile:
        vertical = self._session.get(
            VerticalDefinition,
            value.vertical_definition_id,
        )
        if vertical is None:
            raise ProfileError("Vertical definition not found")
        key = _key(value.key)
        version = _version(value.version)
        name = _text(value.name, "name", 200)
        created_by = _text(value.created_by, "created_by", 200)
        if value.status not in {"draft", "active", "paused", "retired"}:
            raise ProfileError("Unsupported research profile status")
        constraints = _json_object(value.constraints, "constraints")
        exclusions = _json_object(value.exclusions, "exclusions")
        preferences = _json_object(value.preferences, "preferences")
        _validate_profile_rules(constraints, exclusions)
        existing = self._session.scalar(
            select(ResearchProfile).where(
                ResearchProfile.key == key,
                ResearchProfile.version == version,
            )
        )
        if existing is not None:
            expected = (
                vertical.id,
                name,
                value.status,
                constraints,
                exclusions,
                preferences,
            )
            actual = (
                existing.vertical_definition_id,
                existing.name,
                existing.status,
                existing.constraints,
                existing.exclusions,
                existing.preferences,
            )
            if actual != expected:
                raise ProfileError(
                    "Research profile version exists with different data"
                )
            return existing
        for current in self._session.scalars(
            select(ResearchProfile).where(
                ResearchProfile.key == key,
                ResearchProfile.is_current.is_(True),
            )
        ):
            current.is_current = False
        result = ResearchProfile(
            vertical_definition_id=vertical.id,
            key=key,
            version=version,
            name=name,
            status=value.status,
            constraints=constraints,
            exclusions=exclusions,
            preferences=preferences,
            is_current=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(result)
        self._session.commit()
        return result

    def evaluate(
        self,
        value: ProfileEvaluationInput,
    ) -> OpportunityProfileEvaluation:
        version = self._session.get(
            OpportunityVersion,
            value.opportunity_version_id,
        )
        profile = self._session.get(
            ResearchProfile,
            value.research_profile_id,
        )
        if version is None or profile is None:
            raise ProfileError("Opportunity version or research profile not found")
        observed = _json_object(
            value.observed_attributes,
            "observed_attributes",
        )
        evaluated_by = _text(value.evaluated_by, "evaluated_by", 200)
        blockers: list[str] = []
        unknowns: list[str] = []
        components: dict[str, str] = {}
        expected = 1
        known = 1

        searchable = " ".join(
            [version.title, *[str(item) for item in version.ontology.values()]]
        ).casefold()
        for term in _string_list(profile.exclusions.get("terms")):
            if term.casefold() in searchable:
                blockers.append(f"excluded_term:{term}")
        components["excluded_terms"] = "clear" if not blockers else "blocked"

        category = _optional_string(observed.get("category"))
        expected += 1
        if category is None:
            unknowns.append("category")
        else:
            known += 1
            if category in _string_list(
                profile.exclusions.get("categories")
            ):
                blockers.append(f"excluded_category:{category}")
                components["category"] = "blocked"
            else:
                components["category"] = "compatible"

        known, expected = self._constraint_checks(
            profile,
            observed,
            blockers,
            unknowns,
            components,
            known,
            expected,
        )
        coverage = (
            Decimal(known) / Decimal(expected)
            if expected
            else Decimal("1")
        ).quantize(Decimal("0.000001"))
        if blockers:
            fit_score: Decimal | None = Decimal("0.000000")
        elif coverage < Decimal("0.500000"):
            fit_score = None
        else:
            compatible = sum(
                state in {"compatible", "clear", "preferred"}
                for state in components.values()
            )
            measured = sum(state != "unknown" for state in components.values())
            fit_score = (
                Decimal(compatible) / Decimal(measured)
                if measured
                else None
            )
            if fit_score is not None:
                fit_score = fit_score.quantize(Decimal("0.000001"))

        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "version": version.input_fingerprint,
                    "profile": f"{profile.key}:{profile.version}",
                    "observed": observed,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(OpportunityProfileEvaluation).where(
                OpportunityProfileEvaluation.opportunity_version_id
                == version.id,
                OpportunityProfileEvaluation.research_profile_id == profile.id,
                OpportunityProfileEvaluation.input_fingerprint == fingerprint,
            )
        )
        if existing is not None:
            return existing
        result = OpportunityProfileEvaluation(
            opportunity_version_id=version.id,
            research_profile_id=profile.id,
            input_fingerprint=fingerprint,
            observed_attributes=observed,
            eligible=not blockers,
            blocker_codes=sorted(set(blockers)),
            unknown_fields=sorted(set(unknowns)),
            fit_score=fit_score,
            data_coverage=coverage,
            components=components,
            evaluated_by=evaluated_by,
            evaluated_at=datetime.now(UTC),
        )
        self._session.add(result)
        self._session.commit()
        return result

    def _constraint_checks(
        self,
        profile: ResearchProfile,
        observed: dict,
        blockers: list[str],
        unknowns: list[str],
        components: dict[str, str],
        known: int,
        expected: int,
    ) -> tuple[int, int]:
        checks = (
            (
                "estimated_initial_cost",
                "capital_budget",
                "capital_budget_exceeded",
            ),
            (
                "estimated_build_weeks",
                "max_build_weeks",
                "build_time_exceeded",
            ),
            (
                "required_team_size",
                "max_team_size",
                "team_size_exceeded",
            ),
        )
        for observed_key, constraint_key, blocker in checks:
            if constraint_key not in profile.constraints:
                continue
            expected += 1
            actual = _decimal(observed.get(observed_key))
            maximum = _decimal(profile.constraints.get(constraint_key))
            if actual is None:
                unknowns.append(observed_key)
                components[observed_key] = "unknown"
                continue
            known += 1
            if maximum is not None and actual > maximum:
                blockers.append(blocker)
                components[observed_key] = "blocked"
            else:
                components[observed_key] = "compatible"

        sales_motion = _optional_string(observed.get("sales_motion"))
        excluded_sales = _string_list(
            profile.exclusions.get("sales_motions")
        )
        if excluded_sales:
            expected += 1
            if sales_motion is None:
                unknowns.append("sales_motion")
                components["sales_motion"] = "unknown"
            else:
                known += 1
                if sales_motion in excluded_sales:
                    blockers.append(f"excluded_sales_motion:{sales_motion}")
                    components["sales_motion"] = "blocked"
                elif sales_motion in _string_list(
                    profile.preferences.get("sales_motions")
                ):
                    components["sales_motion"] = "preferred"
                else:
                    components["sales_motion"] = "compatible"
        return known, expected


def _validate_profile_rules(constraints: dict, exclusions: dict) -> None:
    for key in ("capital_budget", "max_build_weeks", "max_team_size"):
        if key in constraints:
            value = _decimal(constraints[key])
            if value is None or value < 0:
                raise ProfileError(f"{key} must be a non-negative number")
    for key in ("categories", "terms", "sales_motions"):
        if key in exclusions:
            _string_list(exclusions[key], required=True)


def _json_object(value: dict, field: str) -> dict:
    if not isinstance(value, dict):
        raise ProfileError(f"{field} must be an object")
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError) as exc:
        raise ProfileError(f"{field} is not JSON serializable") from exc


def _key(value: str) -> str:
    normalized = value.strip().lower()
    if not _KEY.fullmatch(normalized):
        raise ProfileError("Invalid key")
    return normalized


def _version(value: str) -> str:
    normalized = value.strip()
    if not _VERSION.fullmatch(normalized):
        raise ProfileError("Invalid version")
    return normalized


def _text(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ProfileError(f"{field} is required")
    if len(normalized) > maximum:
        raise ProfileError(f"{field} is too long")
    return normalized


def _string_list(value, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProfileError("Profile list values must be non-empty strings")
    return [item.strip() for item in value]


def _optional_string(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProfileError("Profile numeric value is invalid") from exc
