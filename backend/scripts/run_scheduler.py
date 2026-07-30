import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime

from firsat_radari.config import get_settings
from firsat_radari.db.session import SessionLocal
from firsat_radari.scheduler.service import SchedulerService


async def run() -> None:
    settings = get_settings()
    with SessionLocal() as session:
        outcome = await SchedulerService(session, settings).run_due(
            as_of=datetime.now(UTC),
            limit=25,
        )
    print(json.dumps(asdict(outcome), default=str, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(run())
