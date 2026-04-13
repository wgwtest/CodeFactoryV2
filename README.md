# Knowledge Warehouse Foundation

First shippable vertical slice for the Software Factory knowledge warehouse. This workspace ingests `PDF/DOC/DOCX`, stores versioned source material, extracts candidate knowledge, supports review and publish workflows, and exposes graph and process exploration views.

## Development policy
- This project must not use `git worktree` as the default development mode.
- All daily development, verification, and service startup should run from the repository root workspace.
- If historical docs mention paths under `.worktrees/`, treat them as obsolete execution context rather than the current project rule.
- Local runtime data under `.data/` is part of the active root workspace context and must not be split across separate worktrees.

中文说明见：[docs/development-policy.md](docs/development-policy.md)

## First release capabilities
- Upload and version source documents.
- Parse structured evidence segments from uploaded files.
- Extract candidate entities, events, processes, rules, and metrics.
- Review and publish governed knowledge versions.
- Explore graph and process projections from published knowledge.
- Enforce publisher role checks and persist publish audit logs.

## Local development
1. `cp .env.example .env`
2. `docker compose up -d`
3. `uv sync`
4. `corepack pnpm install`
5. Do not create or use `.worktrees/*` for this project.
6. `uv run uvicorn app.main:app --reload --app-dir apps/api`
7. `corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5173`

## Verification commands
- `uv run pytest apps/api/tests -q`
- `corepack pnpm --dir apps/web test`
- `corepack pnpm --dir apps/web exec playwright test`
- `just api-test`

## Services
- PostgreSQL 16: `localhost:5432`
- MinIO API: `localhost:9000`
- MinIO console: `localhost:9001`
- Web console: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000/api`
