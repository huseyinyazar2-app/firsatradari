import asyncio
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from time import monotonic

from firsat_radari.config import get_settings
from firsat_radari.db.session import SessionLocal
from firsat_radari.scheduler.service import SchedulerService

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger("firsat_radari.scheduler_worker")


async def run() -> None:
    settings = get_settings()
    while True:
        started_at = monotonic()
        try:
            with SessionLocal() as session:
                outcome = await SchedulerService(
                    session,
                    settings,
                ).run_due(
                    as_of=datetime.now(UTC),
                    limit=25,
                )
            if outcome.considered_count:
                logger.info(
                    json.dumps(
                        asdict(outcome),
                        default=str,
                        sort_keys=True,
                    )
                )
        except Exception:
            logger.exception("Scheduled worker iteration failed")
        elapsed = monotonic() - started_at
        await asyncio.sleep(
            max(1, settings.scheduler_poll_seconds - elapsed)
        )


if __name__ == "__main__":
    asyncio.run(run())
