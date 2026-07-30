#!/bin/sh
set -eu

backup_root="${1:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="${backup_root%/}/${timestamp}"

mkdir -p "$target"

docker compose \
  --env-file .env.production \
  -f compose.production.yaml \
  exec -T postgres \
  pg_dump -U firsat -d firsat_radari -Fc > "$target/database.dump"

docker compose \
  --env-file .env.production \
  -f compose.production.yaml \
  exec -T backend \
  tar -C /data/raw -czf - . > "$target/raw-data.tar.gz"

sha256sum "$target/database.dump" "$target/raw-data.tar.gz" \
  > "$target/SHA256SUMS"

printf '%s\n' "$target"
