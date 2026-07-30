from typing import Any

from firsat_radari.config import Settings
from firsat_radari.connectors.base import DataConnector
from firsat_radari.connectors.github import GitHubConnector
from firsat_radari.connectors.github_work_items import GitHubWorkItemConnector
from firsat_radari.connectors.npm import NpmConnector
from firsat_radari.connectors.stack_exchange import StackExchangeConnector


class ConnectorRegistryError(ValueError):
    pass


def create_connector(connector_key: str, settings: Settings) -> DataConnector:
    if connector_key == "github":
        token = settings.github_token.get_secret_value() if settings.github_token else None
        return GitHubConnector(token=token)
    if connector_key == "github_work_items":
        token = settings.github_token.get_secret_value() if settings.github_token else None
        return GitHubWorkItemConnector(token=token)
    if connector_key == "npm":
        return NpmConnector()
    if connector_key == "stack_exchange_questions":
        key = (
            settings.stack_exchange_key.get_secret_value()
            if settings.stack_exchange_key
            else None
        )
        return StackExchangeConnector(key=key)
    raise ConnectorRegistryError(f"Unsupported connector: {connector_key}")


def validate_discovery_query(connector_key: str, query: dict[str, Any]) -> dict[str, Any]:
    if connector_key == "github":
        return _validate_github_query(query)
    if connector_key == "github_work_items":
        return _validate_github_work_item_query(query)
    if connector_key == "npm":
        return _validate_npm_query(query)
    if connector_key == "stack_exchange_questions":
        return _validate_stack_exchange_query(query)
    raise ConnectorRegistryError(f"Unsupported connector: {connector_key}")


def validate_discovery_checkpoint(
    connector_key: str,
    checkpoint: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    if connector_key in {"github", "github_work_items"}:
        _reject_unknown_keys(checkpoint, {"page"})
        page = _bounded_integer(
            checkpoint,
            "page",
            default=1,
            minimum=1,
            maximum=100,
        )
        return {"page": page}
    if connector_key == "npm":
        _reject_unknown_keys(checkpoint, {"offset"})
        offset = _bounded_integer(
            checkpoint,
            "offset",
            default=0,
            minimum=0,
            maximum=10_000_000,
        )
        return {"offset": offset}
    if connector_key == "stack_exchange_questions":
        _reject_unknown_keys(checkpoint, {"page"})
        page = _bounded_integer(
            checkpoint,
            "page",
            default=1,
            minimum=1,
            maximum=10_000,
        )
        return {"page": page}
    raise ConnectorRegistryError(f"Unsupported connector: {connector_key}")


def _validate_github_query(query: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"q", "sort", "order", "per_page"}
    _reject_unknown_keys(query, allowed_keys)
    search_query = _required_text(query, "q")
    if len(search_query) > 256:
        raise ConnectorRegistryError("GitHub query exceeds 256 characters")

    sort = query.get("sort", "updated")
    if sort not in {"stars", "forks", "help-wanted-issues", "updated"}:
        raise ConnectorRegistryError("Unsupported GitHub sort")
    order = query.get("order", "desc")
    if order not in {"asc", "desc"}:
        raise ConnectorRegistryError("Unsupported GitHub order")
    per_page = _bounded_integer(query, "per_page", default=100, minimum=1, maximum=100)
    return {"q": search_query, "sort": sort, "order": order, "per_page": per_page}


def _validate_github_work_item_query(query: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"q", "sort", "order", "per_page"}
    _reject_unknown_keys(query, allowed_keys)
    search_query = _required_text(query, "q")
    if len(search_query) > 256:
        raise ConnectorRegistryError("GitHub query exceeds 256 characters")
    sort = query.get("sort", "updated")
    if sort not in {"comments", "created", "updated"}:
        raise ConnectorRegistryError("Unsupported GitHub work item sort")
    order = query.get("order", "desc")
    if order not in {"asc", "desc"}:
        raise ConnectorRegistryError("Unsupported GitHub order")
    per_page = _bounded_integer(query, "per_page", default=100, minimum=1, maximum=100)
    return {"q": search_query, "sort": sort, "order": order, "per_page": per_page}


def _validate_npm_query(query: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"text", "size"}
    _reject_unknown_keys(query, allowed_keys)
    search_text = _required_text(query, "text")
    if len(search_text) > 256:
        raise ConnectorRegistryError("npm query exceeds 256 characters")
    size = _bounded_integer(query, "size", default=100, minimum=1, maximum=250)
    return {"text": search_text, "size": size}


def _validate_stack_exchange_query(
    query: dict[str, Any],
) -> dict[str, Any]:
    allowed_keys = {
        "site",
        "tags",
        "from_date",
        "to_date",
        "sort",
        "order",
        "page_size",
    }
    _reject_unknown_keys(query, allowed_keys)
    site = _required_text(query, "site").casefold()
    if (
        len(site) > 80
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for character in site)
    ):
        raise ConnectorRegistryError("Invalid Stack Exchange site")
    raw_tags = query.get("tags")
    if not isinstance(raw_tags, list) or not 1 <= len(raw_tags) <= 5:
        raise ConnectorRegistryError(
            "Stack Exchange tags must contain between 1 and 5 items"
        )
    tags: list[str] = []
    for raw_tag in raw_tags:
        if not isinstance(raw_tag, str) or not raw_tag.strip():
            raise ConnectorRegistryError("Invalid Stack Exchange tag")
        tag = raw_tag.strip().casefold()
        if len(tag) > 35 or ";" in tag:
            raise ConnectorRegistryError("Invalid Stack Exchange tag")
        tags.append(tag)
    from_date = _iso_date(query, "from_date")
    to_date = _iso_date(query, "to_date")
    if from_date > to_date:
        raise ConnectorRegistryError(
            "Stack Exchange from_date cannot be after to_date"
        )
    if (to_date - from_date).days > 30:
        raise ConnectorRegistryError(
            "Stack Exchange date window cannot exceed 31 days"
        )
    sort = query.get("sort", "creation")
    if sort not in {"activity", "creation", "votes"}:
        raise ConnectorRegistryError("Unsupported Stack Exchange sort")
    order = query.get("order", "asc")
    if order not in {"asc", "desc"}:
        raise ConnectorRegistryError("Unsupported Stack Exchange order")
    page_size = _bounded_integer(
        query,
        "page_size",
        default=100,
        minimum=1,
        maximum=100,
    )
    return {
        "site": site,
        "tags": sorted(set(tags)),
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "sort": sort,
        "order": order,
        "page_size": page_size,
    }


def _reject_unknown_keys(query: dict[str, Any], allowed_keys: set[str]) -> None:
    unknown = sorted(set(query) - allowed_keys)
    if unknown:
        raise ConnectorRegistryError(f"Unsupported query fields: {', '.join(unknown)}")


def _required_text(query: dict[str, Any], key: str) -> str:
    value = query.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConnectorRegistryError(f"Query field is required: {key}")
    return value.strip()


def _bounded_integer(
    query: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = query.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConnectorRegistryError(f"Query field must be an integer: {key}")
    if not minimum <= value <= maximum:
        raise ConnectorRegistryError(f"Query field {key} must be between {minimum} and {maximum}")
    return value


def _iso_date(query: dict[str, Any], key: str):
    from datetime import date

    value = query.get(key)
    if not isinstance(value, str):
        raise ConnectorRegistryError(f"Query field is required: {key}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConnectorRegistryError(
            f"Query field must be an ISO date: {key}"
        ) from exc
