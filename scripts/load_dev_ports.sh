#!/usr/bin/env bash
set -euo pipefail

PORT_CONFIG="config/dev-ports.env"
if [[ -f "${PORT_CONFIG}" ]]; then
  set -a
  source "${PORT_CONFIG}"
  set +a
fi

LOCAL_DIFY_ENV="${CODEFACTORY_LOCAL_DIFY_ENV:-${HOME}/.codefactory/dify.local.env}"
if [[ -f "${LOCAL_DIFY_ENV}" ]]; then
  set -a
  source "${LOCAL_DIFY_ENV}"
  set +a
fi

if [[ -f ".env.local" ]]; then
  set -a
  source ".env.local"
  set +a
fi

branch_name="${CF_DEV_BRANCH_OVERRIDE:-$(git branch --show-current 2>/dev/null || true)}"
if [[ -z "${branch_name}" ]]; then
  branch_name="main"
fi

branch_key="$(printf '%s' "${branch_name}" | tr '[:lower:]' '[:upper:]' | sed -E 's/[^A-Z0-9]+/_/g; s/^_+//; s/_+$//')"

api_port_var="${branch_key}_API_PORT"
web_port_var="${branch_key}_WEB_PORT"
default_route_var="${branch_key}_DEFAULT_ROUTE"

export CF_API_HOST="${CF_API_HOST:-127.0.0.1}"
export VITE_WEB_HOST="${VITE_WEB_HOST:-127.0.0.1}"
export CF_API_PORT="${CF_API_PORT:-${!api_port_var:-${MAIN_API_PORT:-8020}}}"
export VITE_WEB_PORT="${VITE_WEB_PORT:-${!web_port_var:-${MAIN_WEB_PORT:-5173}}}"
export VITE_DEFAULT_ROUTE="${VITE_DEFAULT_ROUTE:-${!default_route_var:-${MAIN_DEFAULT_ROUTE:-/documents}}}"
export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-${VITE_DEV_API_PROXY_TARGET:-http://${CF_API_HOST}:${CF_API_PORT}}}"
