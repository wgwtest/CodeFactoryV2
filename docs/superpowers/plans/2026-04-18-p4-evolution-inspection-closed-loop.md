# P4 Evolution Inspection Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4` 增加独立的自演进巡检闭环，包括巡检协议、前端卡片工作区、统一运行协调器、低风险自动改写与任务级回退。

**Architecture:** 后端继续沿用 `tool_hub` 子域，但把自演进从“单次报告”升级为 `config / run / finding / task / change_set / rollback` 六类对象，并通过统一的 `P4 runtime coordinator` 同时推进 `manufacture` 和 `evolution`。前端在 `XX-P4` 的“自演进巡检”标签页下拆分为独立卡片，分别展示配置、轮次、发现项、任务队列和已完成优化项，并通过显式 DOM id 保持可沟通性。

**Tech Stack:** FastAPI, Pydantic, Python threading, React 18, TypeScript, Ant Design 5, pytest, Vitest

---

## File Structure

- Create: `docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
- Create: `docs/superpowers/plans/2026-04-18-p4-evolution-inspection-closed-loop.md`
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Create: `apps/api/tests/test_tool_hub_evolution_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/components/p4/P4EvolutionWorkspace.tsx`
- Modify: `apps/web/src/components/p4/p4-page.css`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/AppRoutes.test.tsx`

### Task 1: Lock the P4.3 backend contract with failing tests

**Files:**
- Create: `apps/api/tests/test_tool_hub_evolution_api.py`

- [ ] **Step 1: Write the failing test for config, run, finding and task lifecycle**

```python
def test_evolution_run_decision_and_task_creation(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    run_response = client.post("/api/tool-hub/evolution/runs", json={"actor_id": "tester"})
    assert run_response.status_code == 201
    run_id = run_response.json()["run_id"]

    runs_response = client.get("/api/tool-hub/evolution/runs")
    finding_id = runs_response.json()["data"]["items"][0]["findings"][0]["finding_id"]

    decision_response = client.post(
        f"/api/tool-hub/evolution/findings/{finding_id}/decision",
        json={"actor_id": "tester", "decision": "accept", "note": "turn into task"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["decision_status"] == "accepted_to_task"
    assert decision_response.json()["linked_task_id"]

    tasks_response = client.get("/api/tool-hub/evolution/tasks")
    assert tasks_response.status_code == 200
    assert tasks_response.json()["data"]["items"][0]["source_run_id"] == run_id
```

- [ ] **Step 2: Write the failing test for auto-apply and rollback**

```python
def test_evolution_auto_apply_and_task_rollback(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    run_response = client.post("/api/tool-hub/evolution/runs", json={"actor_id": "tester"})
    finding_id = _find_first_decidable_finding(run_response.json())

    decision_response = client.post(
        f"/api/tool-hub/evolution/findings/{finding_id}/decision",
        json={"actor_id": "tester", "decision": "accept", "note": "auto apply"},
    )
    task_id = decision_response.json()["linked_task_id"]

    _wait_for_task_status(client, task_id, expected_status="completed")

    rollback_response = client.post(
        f"/api/tool-hub/evolution/tasks/{task_id}/rollback",
        json={"actor_id": "tester", "note": "revert auto change"},
    )
    assert rollback_response.status_code == 200
    assert rollback_response.json()["task_status"] == "rolled_back"
```

- [ ] **Step 3: Write the failing test for scheduled trigger**

```python
def test_evolution_scheduler_runs_when_dirty(tmp_path: Path) -> None:
    service = _build_service(tmp_path, evolution_interval_minutes=0.001, executor_tick_seconds=0.05)
    service.update_evolution_config(
        {"enabled": True, "interval_minutes": 1, "focus_rule_ids": ["missing_description"]},
        actor_id="tester",
    )
    service.mark_evolution_dirty()

    _wait_until(lambda: len(service.list_evolution_runs().data.items) >= 1)

    latest = service.list_evolution_runs().data.items[0]
    assert latest.trigger_type == "scheduled"
```

- [ ] **Step 4: Run test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_evolution_api.py -q`

Expected:
- `404` on `/api/tool-hub/evolution/*` subroutes that do not exist yet
- or schema assertion failures because config/task/rollback objects are missing

### Task 2: Implement backend P4.3 models, storage and runtime coordinator

**Files:**
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`

- [ ] **Step 1: Add the new P4.3 models**

```python
class EvolutionInspectionConfig(BaseModel):
    config_id: str = "default"
    enabled: bool = True
    schedule_mode: Literal["manual_and_scheduled"] = "manual_and_scheduled"
    interval_minutes: float = 60
    include_draft_tools: bool = True
    focus_rule_ids: list[RiskKind] = Field(default_factory=lambda: [...])
    overlap_threshold: int = 3
    max_run_history: int = 50
    auto_apply_rule_ids: list[RiskKind] = Field(default_factory=lambda: [...])
    updated_by: str = "p4-system"
    updated_at: str = Field(default_factory=now_iso)

class EvolutionTask(BaseModel):
    task_id: str
    source_run_id: str
    source_finding_id: str
    task_type: Literal["auto_apply", "manual_followup"]
    task_status: Literal["queued", "running", "completed", "failed", "rolled_back"]
    ...
```

- [ ] **Step 2: Extend repository storage for config, findings, tasks, change sets, rollbacks and runtime state**

```python
self.evolution_root_dir = self.root / "evolution"
self.evolution_config_dir = self.evolution_root_dir / "config"
self.evolution_findings_dir = self.evolution_root_dir / "findings"
self.evolution_tasks_dir = self.evolution_root_dir / "tasks"
self.evolution_change_sets_dir = self.evolution_root_dir / "change_sets"
self.evolution_rollbacks_dir = self.evolution_root_dir / "rollbacks"
self.runtime_dir = self.root / "runtime"
```

- [ ] **Step 3: Replace the manufacture-only thread with a unified runtime coordinator**

```python
class _ToolHubRuntimeCoordinator:
    def _run(self) -> None:
        service = self.service_factory()
        while not self._stop_event.is_set():
            service.run_runtime_cycle()
            self._stop_event.wait(self.interval_seconds)

def run_runtime_cycle(self) -> None:
    self.run_scheduled_evolution_cycle()
    self.run_evolution_task_cycle()
    self.run_manufacture_executor_cycle()
```

- [ ] **Step 4: Implement run generation, finding decisions, task creation, auto-apply and rollback**

```python
def decide_evolution_finding(self, finding_id: str, payload: EvolutionFindingDecisionRequest) -> EvolutionFinding:
    finding = self.repository.get_evolution_finding(finding_id)
    if payload.decision == "accept":
        task = self._build_evolution_task(finding, payload.actor_id)
        self.repository.save_evolution_task(task)
        finding.decision_status = "accepted_to_task"
        finding.linked_task_id = task.task_id
    else:
        finding.decision_status = "ignored"
    return self.repository.save_evolution_finding(finding)
```

- [ ] **Step 5: Add new routes without breaking legacy `/tool-hub/evolution-runs`**

```python
@router.get("/evolution/config", response_model=EvolutionConfigReadEnvelope)
def get_evolution_config(...): ...

@router.post("/evolution/runs", response_model=EvolutionInspectionRun)
def create_evolution_run(...): ...

@router.post("/evolution/tasks/{task_id}/rollback", response_model=EvolutionTask)
def rollback_evolution_task(...): ...
```

- [ ] **Step 6: Re-run backend tests to GREEN**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_evolution_api.py -q`
- `uv run pytest apps/api/tests/test_tool_hub_api.py -q`

Expected:
- all new P4.3 tests pass
- existing tool hub regression tests remain green

### Task 3: Extend frontend API types and page state with failing tests first

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/AppRoutes.test.tsx`

- [ ] **Step 1: Write a failing page test for the six-card evolution workspace**

```tsx
it("renders evolution config, run list, findings, queue and completed cards", async () => {
  render(<XXP4Page />);

  await user.click(screen.getByRole("tab", { name: /自演进巡检/i }));

  expect(document.querySelector("#xx-p4-evolution-config-card")).toBeTruthy();
  expect(document.querySelector("#xx-p4-evolution-run-list-card")).toBeTruthy();
  expect(document.querySelector("#xx-p4-evolution-findings-card")).toBeTruthy();
  expect(document.querySelector("#xx-p4-evolution-task-queue-card")).toBeTruthy();
  expect(document.querySelector("#xx-p4-evolution-completed-card")).toBeTruthy();
});
```

- [ ] **Step 2: Write a failing page test for decision and rollback actions**

```tsx
it("accepts a finding and rolls back a completed auto-apply task", async () => {
  render(<XXP4Page />);

  await user.click(screen.getByRole("tab", { name: /自演进巡检/i }));
  await user.click(screen.getByRole("button", { name: /采纳/i }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/evolution/findings/"),
    expect.objectContaining({ decision: "accept" }),
  ));
});
```

- [ ] **Step 3: Run the frontend tests to verify RED**

Run:
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx AppRoutes.test.tsx`

Expected:
- mocks fail because `/tool-hub/evolution/*` APIs and new cards are not implemented yet

### Task 4: Implement the P4.3 card workspace and frontend interactions

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/components/p4/P4EvolutionWorkspace.tsx`
- Modify: `apps/web/src/components/p4/p4-page.css`

- [ ] **Step 1: Add frontend types and API helpers**

```ts
export type EvolutionInspectionConfig = {
  config_id: string;
  enabled: boolean;
  interval_minutes: number;
  focus_rule_ids: RiskKind[];
  auto_apply_rule_ids: RiskKind[];
};

export function getEvolutionConfig() {
  return api.get<ToolHubReadEnvelope<EvolutionConfigEnvelope>>("/tool-hub/evolution/config");
}
```

- [ ] **Step 2: Load config, runs and tasks in `XXP4Page`**

```ts
const [evolutionConfig, setEvolutionConfig] = useState<EvolutionInspectionConfig | null>(null);
const [evolutionTasks, setEvolutionTasks] = useState<EvolutionTask[]>([]);

const [overviewResponse, toolsResponse, evolutionConfigResponse, evolutionRunsResponse, evolutionTasksResponse] =
  await Promise.all([ ... ]);
```

- [ ] **Step 3: Replace the single-card evolution panel with six explicit cards**

```tsx
<div id="xx-p4-evolution-config-card"><Card ... /></div>
<div id="xx-p4-evolution-run-list-card"><Card ... /></div>
<div id="xx-p4-evolution-summary-card"><Card ... /></div>
<div id="xx-p4-evolution-findings-card"><Card ... /></div>
<div id="xx-p4-evolution-task-queue-card"><Card ... /></div>
<div id="xx-p4-evolution-completed-card"><Card ... /></div>
```

- [ ] **Step 4: Wire decision, config save, manual trigger and rollback actions**

```tsx
async function handleDecision(findingId: string, decision: "accept" | "ignore") {
  await decideEvolutionFinding(findingId, { actor_id: "p4-workspace", decision, note: "" });
  await loadPage(false, activeSheet?.sheet_id, selectedItemId);
}

async function handleRollback(taskId: string) {
  await rollbackEvolutionTask(taskId, { actor_id: "p4-workspace", note: "manual rollback" });
  await loadPage(false, activeSheet?.sheet_id, selectedItemId);
}
```

- [ ] **Step 5: Re-run frontend tests to GREEN**

Run:
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx AppRoutes.test.tsx`

Expected:
- new P4.3 card and action tests pass

### Task 5: Full regression, build and sync checks

**Files:**
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

- [ ] **Step 1: Run focused backend regression**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_evolution_api.py apps/api/tests/test_tool_hub_api.py -q`

Expected:
- both files pass

- [ ] **Step 2: Run focused frontend regression**

Run:
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx AppRoutes.test.tsx`

Expected:
- pass with no snapshot mismatch failures

- [ ] **Step 3: Run frontend build**

Run:
- `corepack pnpm --dir apps/web build`

Expected:
- Vite build succeeds

- [ ] **Step 4: Run the complete tool hub verification path**

Run:
- `curl -s http://127.0.0.1:8010/api/tool-hub/evolution/config | jq '.data.config_id'`
- `curl -s -X POST http://127.0.0.1:8010/api/tool-hub/evolution/runs -H 'content-type: application/json' -d '{"actor_id":"manual-check"}' | jq '.status'`

Expected:
- first command returns `"default"`
- second command returns `"completed"` or `"running"` and the run can then be seen in `/xx-p4`

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md \
        docs/superpowers/plans/2026-04-18-p4-evolution-inspection-closed-loop.md \
        docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md \
        apps/api/app/tool_hub/models.py apps/api/app/tool_hub/repository.py \
        apps/api/app/tool_hub/snapshot.py apps/api/app/tool_hub/service.py \
        apps/api/app/api/routes/tool_hub.py apps/api/tests/test_tool_hub_evolution_api.py \
        apps/web/src/lib/api.ts apps/web/src/lib/toolHub.ts apps/web/src/pages/XXP4Page.tsx \
        apps/web/src/components/p4/P4EvolutionWorkspace.tsx apps/web/src/components/p4/p4-page.css \
        apps/web/src/test/XXP4Page.test.tsx apps/web/src/test/AppRoutes.test.tsx
git commit -m "feat: add p4 evolution inspection closed loop"
```
