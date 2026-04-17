#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env.local" ]]; then
  set -a
  source ".env.local"
  set +a
fi

API_HOST="${CF_API_HOST:-127.0.0.1}"
API_PORT="${CF_API_PORT:-8020}"

exec uv run uvicorn app.main:app --reload --app-dir apps/api --host "${API_HOST}" --port "${API_PORT}"
