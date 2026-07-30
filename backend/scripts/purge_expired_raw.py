import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime

from firsat_radari.config import get_settings
from firsat_radari.db.session import SessionLocal
from firsat_radari.operations.retention import RetentionService
from firsat_radari.storage.filesystem import FileObjectStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    arguments = parser.parse_args()
    settings = get_settings()
    with SessionLocal() as session:
        outcome = RetentionService(
            session,
            FileObjectStore(settings.raw_storage_path),
        ).purge_expired(
            as_of=datetime.now(UTC),
            limit=arguments.limit,
            apply=arguments.apply,
        )
    print(json.dumps(asdict(outcome), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
