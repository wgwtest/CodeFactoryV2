# P4 Simulated Manufacture Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4` 增加后台模拟研制执行器，使未命中后进入研制的需求项能够自动并行推进，并在工具仓库与 `P5` 查询页展示真实变化。

**Architecture:** 后端在 `tool_hub` 子域内引入一个单进程后台执行器，按周期扫描 `ToolManufacturePlan`，根据时间推进 `manufacturing_pending -> manufacturing_in_progress -> ready_for_fetch`。前端新增研制队列读取与展示，但仍保持 `P5` 只读查询、`P4` 内部自推进的边界。

**Tech Stack:** FastAPI, Pydantic, Python threading, React 18, TypeScript, Ant Design 5, pytest, Vitest

---

## File Structure

- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/api/tests/test_tool_hub_demand_chain_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- Modify: `apps/web/src/components/p5/P5DemandQueryPanel.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/P3P4P5SimPages.test.tsx`

### Task 1: Lock the executor contract with failing backend tests

**Files:**
- Modify: `apps/api/tests/test_tool_hub_demand_chain_api.py`

- [ ] Step 1: Add a failing test that approves a manufacture item, waits without calling `progress`, and expects the item to advance automatically.
- [ ] Step 2: Add a failing test that verifies `/api/tool-hub/manufacture-plans` returns queue data for `P4` consumption.
- [ ] Step 3: Run `uv run pytest apps/api/tests/test_tool_hub_demand_chain_api.py -q` and confirm the new assertions fail for the current query-driven implementation.

### Task 2: Implement backend simulated manufacture executor

**Files:**
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`

- [ ] Step 1: Extend `ToolManufacturePlan` with simulation timing and progress message fields, and add a read model for queue rows.
- [ ] Step 2: Make repository writes atomic and guarded by a shared lock so executor and requests can safely share JSON state.
- [ ] Step 3: Add a shared background executor keyed by repository root, with configurable tick interval and duration profiles for tests.
- [ ] Step 4: Move manufacture progression out of `get_demand_item_progress`, so the API becomes pure read.
- [ ] Step 5: Add `GET /api/tool-hub/manufacture-plans` and wire it to executor-refreshed queue projection.
- [ ] Step 6: Re-run `uv run pytest apps/api/tests/test_tool_hub_demand_chain_api.py -q` until green.

### Task 3: Expose queue state to P4 and keep P5 read-only

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- Modify: `apps/web/src/components/p5/P5DemandQueryPanel.tsx`

- [ ] Step 1: Add frontend types and API helpers for manufacture-plan queue reads.
- [ ] Step 2: Load queue data in `XXP4Page` and pass it into the registry workspace.
- [ ] Step 3: Add a stable-id queue card in the registry workspace that shows component, plan status, percent, profile, and ETA.
- [ ] Step 4: Keep `P5` progress UI on pure read semantics, but update wording to reflect executor-driven progress.

### Task 4: Lock behavior with frontend tests and run final verification

**Files:**
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/P3P4P5SimPages.test.tsx`

- [ ] Step 1: Add frontend assertions for the registry queue card and executor-driven progress wording.
- [ ] Step 2: Run `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx P3P4P5SimPages.test.tsx` and fix failures.
- [ ] Step 3: Run `corepack pnpm --dir apps/web test`.
- [ ] Step 4: Run `corepack pnpm --dir apps/web build`.
- [ ] Step 5: Run `uv run pytest apps/api/tests/test_tool_hub_demand_chain_api.py -q`.
