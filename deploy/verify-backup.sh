#!/bin/sh
set -eu

backup_dir="${1:?usage: deploy/verify-backup.sh BACKUP_DIRECTORY}"
database_dump="$backup_dir/database.dump"
raw_archive="$backup_dir/raw-data.tar.gz"
verify_db="firsat_restore_verify_$(date -u +%Y%m%d%H%M%S)"

test -f "$database_dump"
test -f "$raw_archive"
(cd "$backup_dir" && sha256sum -c SHA256SUMS)
tar -tzf "$raw_archive" >/dev/null

compose() {
  docker compose \
    --env-file .env.production \
    -f compose.production.yaml \
    "$@"
}

cleanup() {
  compose exec -T postgres \
    dropdb -U firsat --if-exists "$verify_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT

compose exec -T postgres createdb -U firsat "$verify_db"
compose exec -T postgres pg_restore \
  -U firsat -d "$verify_db" --exit-on-error < "$database_dump"

migration_version="$(
  compose exec -T postgres \
    psql -U firsat -d "$verify_db" -Atc \
    "SELECT version_num FROM alembic_version"
)"
table_count="$(
  compose exec -T postgres \
    psql -U firsat -d "$verify_db" -Atc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
)"

test -n "$migration_version"
test "$table_count" -gt 0

printf 'migration=%s tables=%s\n' "$migration_version" "$table_count"
