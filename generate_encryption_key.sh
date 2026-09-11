#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/board_service/.env"
EXAMPLE_FILE="$ROOT_DIR/board_service/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f "$EXAMPLE_FILE" ]]; then
    echo "Error: $EXAMPLE_FILE was not found." >&2
    exit 1
  fi
  cp "$EXAMPLE_FILE" "$ENV_FILE"
  echo "Created $ENV_FILE from .env.example"
fi

NEW_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

python3 - "$ENV_FILE" "$NEW_KEY" <<'PY'
from pathlib import Path
import sys

env_file = Path(sys.argv[1])
new_key = sys.argv[2]
lines = env_file.read_text().splitlines()
replaced = False
output = []

for line in lines:
    if line.startswith("ENCRYPTION_KEY="):
        output.append(f"ENCRYPTION_KEY={new_key}")
        replaced = True
    else:
        output.append(line)

if not replaced:
    output.append(f"ENCRYPTION_KEY={new_key}")

env_file.write_text("\n".join(output) + "\n")
PY

echo "Generated a new ENCRYPTION_KEY in $ENV_FILE"
echo "Recreating board_api..."
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d --no-build board_api

echo "Done. Check status with: docker compose ps board_api"
