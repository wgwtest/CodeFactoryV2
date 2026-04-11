api-test:
  uv run pytest apps/api/tests -q

web-test:
  corepack pnpm --dir apps/web test

web-e2e:
  corepack pnpm --dir apps/web exec playwright test

up:
  docker compose up -d
