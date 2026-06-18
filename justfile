api-test:
  uv run pytest apps/api/tests -q

api-dev:
  bash scripts/start_api_dev.sh

api-dev-ps:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_api_dev.ps1

web-dev:
  bash scripts/start_web_dev.sh

web-dev-ps:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_web_dev.ps1

web-test:
  corepack pnpm --dir apps/web test

web-e2e:
  corepack pnpm --dir apps/web exec playwright test

up:
  docker compose up -d
