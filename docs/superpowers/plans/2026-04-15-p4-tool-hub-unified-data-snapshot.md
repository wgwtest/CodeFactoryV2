# P4 Tool Hub Unified Data Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4.1.6` 建立统一数据层 `ToolHubStateSnapshot`，并通过 `snapshot_id` 证明总览、输入工具链、自演进巡检和工具仓库消费的是同一份状态快照投影。

**Architecture:** 后端保持现有文件型事实仓储不变，在 `tool_hub` 子域内部新增统一快照构建层，把 `tools / match_runs / evolution_runs / catalogs` 统一构造成 `raw + derived` 状态快照；对外仍保留按页面职责拆分的读接口，但统一返回 `meta + data`。前端继续并发读取 `overview / tools / evolution-runs`，同时校验 `snapshot_id` 一致性，并在异常时显示显式警告。

**Tech Stack:** FastAPI, Pydantic, Python 3.12, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

### Task 1: 回写 WBS 节点与本地 issue 树承载

**Files:**
- Modify: `docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md`
- Create: `docs/superpowers/specs/2026-04-15-p4-tool-hub-unified-data-snapshot-design.md`
- Create: `docs/superpowers/plans/2026-04-15-p4-tool-hub-unified-data-snapshot.md`
- Create: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- Create: `docs/superpowers/issues/P4.1.6-tool-hub-unified-data-snapshot-execution.md`

- [ ] **Step 1: 在 `P4.1` 下补充 `P4.1.6` 子节点，明确主题为“统一数据层与同源快照验证”**
- [ ] **Step 2: 写清统一数据层边界、快照模型、派生层和同源验证要求**
- [ ] **Step 3: 在本地 issue 树镜像中挂接 `P4.1.6`，并为该节点写执行契约**

### Task 2: 先锁定统一快照契约与同源验证测试

**Files:**
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: 先写失败测试，要求 `overview / tools / evolution-runs` 读接口统一返回 `meta.snapshot_id`**
- [ ] **Step 2: 先写失败测试，要求创建或更新工具后，多路读接口返回同一个 `snapshot_id`，且 `tool_count` 与工具列表长度一致**
- [ ] **Step 3: 先写失败测试，要求前端在三路数据 `snapshot_id` 不一致时显示显式警告**
- [ ] **Step 4: 跑定向测试，确认当前实现先红**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx`

### Task 3: 定义统一快照模型与读接口包络

**Files:**
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: 在后端模型中新增 `ToolHubSnapshotMeta / ToolHubRawState / ToolHubDerivedState / ToolHubStateSnapshot`**
- [ ] **Step 2: 补齐 `ToolHubRunMonitor` 与 `PendingSuggestionItem`，把 `metrics / run_monitor / risk_summary / coverage_matrix / pending_suggestions` 明确为派生层**
- [ ] **Step 3: 为读接口新增统一包络模型 `meta + data`**
- [ ] **Step 4: 在前端类型中新增 `ToolHubSnapshotMeta` 和 `ToolHubReadEnvelope<T>`**

### Task 4: 新增统一快照构建层并迁移派生逻辑

**Files:**
- Create: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/tool_hub/repository.py`

- [ ] **Step 1: 新增 `build_tool_hub_snapshot()`，统一读取 `tools / match_runs / evolution_runs / catalogs`**
- [ ] **Step 2: 把当前 `service.py` 中的 `metrics / coverage_matrix / risk_summary / recent runs` 组装逻辑迁移到 `snapshot.py`**
- [ ] **Step 3: 补齐 `run_monitor` 和 `pending_suggestions` 的派生逻辑**
- [ ] **Step 4: 保持 `repository.py` 只负责事实读写，不承担状态拼装**

### Task 5: 统一读接口返回快照投影

**Files:**
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/api/app/tool_hub/service.py`

- [ ] **Step 1: 让 `overview / tools / evolution-runs` 都从同一个 snapshot 投影返回**
- [ ] **Step 2: 三个读接口统一返回 `meta + data`**
- [ ] **Step 3: Mutation 接口保持最小改动，继续通过重新拉取读接口获得最新快照**

### Task 6: 前端接入快照一致性校验

**Files:**
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`

- [ ] **Step 1: 让前端读接口消费 `ToolHubReadEnvelope<T>`**
- [ ] **Step 2: 在 `XXP4Page` 中并发获取 `overview / tools / evolution-runs` 后，校验三路 `snapshot_id` 是否一致**
- [ ] **Step 3: 新增轻量的一致性警告显示，不改变现有四个一级工作区结构**

### Task 7: 回归验证并形成编码前闭环

**Files:**
- Verify: `apps/api/tests/test_tool_hub_api.py`
- Verify: `apps/web/src/test/XXP4Page.test.tsx`
- Verify: `apps/web/src/lib/api.ts`
- Verify: `apps/api/app/tool_hub/snapshot.py`

- [ ] **Step 1: 跑后端定向测试**
- [ ] **Step 2: 跑前端定向测试**
- [ ] **Step 3: 跑前端构建验证类型和包络变更**
- [ ] **Step 4: 记录 `P4.1.6` 已具备编码前条件**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx`
- `corepack pnpm --dir apps/web build`
