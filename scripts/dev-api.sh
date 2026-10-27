#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR/apps/api"
exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "${API_PORT:-8000}"
