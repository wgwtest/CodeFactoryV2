#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env.local" ]]; then
  set -a
  source ".env.local"
  set +a
fi

WEB_HOST="${VITE_WEB_HOST:-127.0.0.1}"
WEB_PORT="${VITE_WEB_PORT:-5174}"

cd apps/web
exec npm run dev -- --host "${WEB_HOST}" --port "${WEB_PORT}"
