# Knowledge Warehouse Foundation

Minimal foundation for the Knowledge Warehouse workspace, featuring a FastAPI-powered health endpoint and the tooling needed to run the API and tests locally.

-## Local commands
- `uv run pytest apps/api/tests/test_health.py -q` – run the health-check test (TDD step).
- `uv run pytest apps/api/tests -q` – execute the API test suite.
- `just api-test` – runs the API tests via `just`.
- `just up` – `docker compose up -d` (starts Postgres 16 and MinIO with sensible defaults).

## Services
- Postgres 16 on `localhost:5432`
- MinIO console on `localhost:9001`, object storage on `localhost:9000`
