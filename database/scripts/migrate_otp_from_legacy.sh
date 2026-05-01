#!/usr/bin/env bash
set -euo pipefail

LEGACY_CONTAINER=${LEGACY_CONTAINER:-otp_postgres}
LEGACY_DB=${LEGACY_DB:-otp_db}
LEGACY_USER=${LEGACY_USER:-app}

TARGET_CONTAINER=${TARGET_CONTAINER:-snaprise_postgres}
TARGET_DB=${TARGET_DB:-otp_db}
TARGET_USER=${TARGET_USER:-app}

DUMP_FILE=${DUMP_FILE:-/tmp/otp_db_legacy_dump.sql}

if ! docker ps --format '{{.Names}}' | grep -Fxq "$LEGACY_CONTAINER"; then
  echo "Legacy container '$LEGACY_CONTAINER' is not running."
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -Fxq "$TARGET_CONTAINER"; then
  echo "Target container '$TARGET_CONTAINER' is not running."
  exit 1
fi

echo "Creating dump from $LEGACY_CONTAINER ($LEGACY_DB)..."
docker exec "$LEGACY_CONTAINER" pg_dump -U "$LEGACY_USER" -d "$LEGACY_DB" -F p > "$DUMP_FILE"

echo "Restoring dump into $TARGET_CONTAINER ($TARGET_DB)..."
cat "$DUMP_FILE" | docker exec -i "$TARGET_CONTAINER" psql -U "$TARGET_USER" -d "$TARGET_DB"

rm -f "$DUMP_FILE"
echo "Migration complete."
