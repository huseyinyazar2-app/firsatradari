import json
from dataclasses import asdict
from datetime import UTC, datetime

from firsat_radari.config import get_settings
from firsat_radari.db.session import SessionLocal
from firsat_radari.operations.service import OperationsService


def main() -> None:
    settings = get_settings()
    with SessionLocal() as session:
        outcome = OperationsService(session).evaluate(
            as_of=datetime.now(UTC),
            freshness_hours=settings.source_freshness_hours,
            daily_budget_usd=settings.daily_cost_budget_usd,
            monthly_budget_usd=settings.monthly_cost_budget_usd,
        )
    print(json.dumps(asdict(outcome), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
