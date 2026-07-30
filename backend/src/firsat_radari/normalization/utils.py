from datetime import UTC, datetime
from typing import Any

from firsat_radari.normalization.base import NormalizationValidationError


def parse_datetime(value: Any, field: str, *, required: bool = False) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise NormalizationValidationError(f"invalid_{field}")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NormalizationValidationError(f"invalid_{field}") from exc


def required_text(
    payload: dict,
    field: str,
    *,
    maximum: int | None = None,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise NormalizationValidationError(f"missing_{field}")
    normalized = value.strip()
    if maximum is not None and len(normalized) > maximum:
        raise NormalizationValidationError(f"{field}_too_long")
    return normalized


def optional_text(value: Any, *, maximum: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:maximum]


def nonnegative_int(payload: dict, field: str, *, default: int = 0) -> int:
    value = payload.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NormalizationValidationError(f"invalid_{field}")
    return value


def is_at_least_as_new(
    incoming: datetime | None,
    existing: datetime | None,
) -> bool:
    if existing is None:
        return True
    if incoming is None:
        return False
    return _as_utc(incoming) >= _as_utc(existing)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
