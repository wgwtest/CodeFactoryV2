api-test:
  .venv/bin/python -m pytest apps/api/tests -q

up:
  docker compose up -d
