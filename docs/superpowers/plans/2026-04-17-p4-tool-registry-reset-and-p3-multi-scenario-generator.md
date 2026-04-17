# P4 Tool Registry Reset And P3 Multi-Scenario Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4` 增加工具删除与测试清空能力，并把 `P3-sim` 升级为可切换 `模拟蓝军 / 导航规划 / 数据治理` 的典型工单发生器。

**Architecture:** 后端在 `tool_hub` 子域内补齐删除/清空接口与多场景 mock 生成入口；前端在 `XX-P4` 的工具仓库页增加删除操作，在 `XX-P3-sim` 增加场景选择与通用生成按钮。删除采用安全检查，测试清空保持临时接口语义。

**Tech Stack:** FastAPI, Pydantic, React 18, TypeScript, Ant Design 5, pytest, Vitest

---

## File Structure

- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- Create: `docs/superpowers/specs/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator-design.md`
- Create: `docs/superpowers/plans/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator.md`
- Modify: `apps/api/app/tool_hub/demand_fixtures.py`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/api/tests/test_tool_hub_demand_chain_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/components/p3/P3BlueForceGenerator.tsx`
- Modify: `apps/web/src/pages/XXP3SimPage.tsx`
- Modify: `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

### Task 1: Lock backend behavior with failing tests

**Files:**
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/api/tests/test_tool_hub_demand_chain_api.py`

- [ ] Step 1: Add a failing API test for deleting an unreferenced tool and clearing all tools.
- [ ] Step 2: Add a failing API test for refusing deletion when a tool is still referenced by demand-chain objects.
- [ ] Step 3: Add a failing API test for generating multiple mock demand-sheet scenarios.
- [ ] Step 4: Run `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_demand_chain_api.py -q` and confirm failures.

### Task 2: Implement backend delete/reset/multi-scenario support

**Files:**
- Modify: `apps/api/app/tool_hub/demand_fixtures.py`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`

- [ ] Step 1: Add tool-registry testing clear result types and repository helpers for deleting one tool and clearing tool-related runtime state.
- [ ] Step 2: Add multi-scenario mock demand builders for `simulated_blue_force`, `navigation_planning`, and `data_governance`.
- [ ] Step 3: Add service-layer safe-delete checks and temporary clear-tools behavior.
- [ ] Step 4: Add the new tool delete, clear-tools, and generic mock-generator routes while keeping the existing blue-force alias.
- [ ] Step 5: Re-run `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_demand_chain_api.py -q` until green.

### Task 3: Expose the new operations in P3 and P4 UI

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/components/p3/P3BlueForceGenerator.tsx`
- Modify: `apps/web/src/pages/XXP3SimPage.tsx`
- Modify: `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`

- [ ] Step 1: Add frontend types and request helpers for delete-tool, clear-tools, and scenario-based mock generation.
- [ ] Step 2: Add scenario selection and generic generate action to `XXP3SimPage`.
- [ ] Step 3: Add per-tool delete buttons and a top-level clear-tools button to the registry workspace, with stable ids.
- [ ] Step 4: Keep existing sheet withdrawal, tool creation, and queue display behavior intact.

### Task 4: Lock UI behavior with tests and verify

**Files:**
- Modify: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] Step 1: Add frontend assertions for scenario switching and generation in `P3-sim`.
- [ ] Step 2: Add frontend assertions for single delete and clear-all-tools in `XX-P4`.
- [ ] Step 3: Run `corepack pnpm --dir apps/web test -- P3P4P5SimPages.test.tsx XXP4Page.test.tsx` and fix failures.
- [ ] Step 4: Run `corepack pnpm --dir apps/web test`.
- [ ] Step 5: Run `corepack pnpm --dir apps/web build`.
- [ ] Step 6: Run `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_demand_chain_api.py -q`.

