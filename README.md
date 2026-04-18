# CodeFactoryV2

`CodeFactoryV2` 是一个知识驱动的软件工厂项目。当前仓库已经落地 `P1` 业务知识库的首个可运行闭环，并在此基础上继续推进 `P2` 需求分析系统、`P3` 软件设计系统、`P4` 工具仓库、`P5` 软件构建系统和 `P6` 门户入口层的正式规划与实施。

## Formal docs

- 正式文档根：`DOC/CODEX_DOC/`
- 正式阅读入口：`DOC/CODEX_DOC/README.md`
- 本地工程策略映射：`DOC/CODEX_DOC/00-本地工程策略映射.md`
- `docs/superpowers/` 为工作文档层，不再单独承担正式权威文档根职责

## Development policy
- This project must not use `git worktree` as the default development mode.
- All daily development, verification, and service startup should run from the repository root workspace.
- If historical docs mention paths under `.worktrees/`, treat them as obsolete execution context rather than the current project rule.
- Local runtime data under `.data/` is part of the active root workspace context and must not be split across separate worktrees.

中文说明见：[docs/development-policy.md](docs/development-policy.md)

## Reading order

1. `DOC/CODEX_DOC/README.md`
2. `DOC/CODEX_DOC/00-本地工程策略映射.md`
3. `DOC/CODEX_DOC/01_需求分析/00-工程总体分析.md`
4. `DOC/CODEX_DOC/02_设计说明/00-软件工厂平台总体设计.md`
5. `DOC/CODEX_DOC/03_研制计划/00-WBS-0-CodeFactoryV2-研发总纲-研制计划.md`

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
