#!/usr/bin/env bash
set -euo pipefail

source scripts/load_dev_ports.sh

WEB_HOST="${VITE_WEB_HOST:-127.0.0.1}"
WEB_PORT="${VITE_WEB_PORT:-5173}"
API_HOST="${CF_API_HOST:-127.0.0.1}"
API_PORT="${CF_API_PORT:-8020}"
export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-${VITE_DEV_API_PROXY_TARGET:-http://${API_HOST}:${API_PORT}}}"

cd apps/web
exec npm run dev -- --host "${WEB_HOST}" --port "${WEB_PORT}"
