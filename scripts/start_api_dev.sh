#!/usr/bin/env bash
set -euo pipefail

source scripts/load_dev_ports.sh

API_HOST="${CF_API_HOST:-127.0.0.1}"
API_PORT="${CF_API_PORT:-8020}"

exec uv run uvicorn app.main:app --reload --app-dir apps/api --host "${API_HOST}" --port "${API_PORT}"
