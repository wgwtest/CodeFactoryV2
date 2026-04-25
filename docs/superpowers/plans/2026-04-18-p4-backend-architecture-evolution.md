# P4 Backend Architecture Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 `P4` 的 `tool_hub` 单体验证实现演进为“独立 `P4 backend service` 的模块化单体内核”，补齐统一运行任务模型、分域服务边界、读写分离投影和后续服务化迁移骨架。

**Architecture:** 继续保留现有 `/api/tool-hub/*` 外部契约和 `XX-P4 / P3-sim / P5-sim` 页面行为，但把当前集中在 `ToolHubService` 中的职责拆成 `registry / demand / manufacture / evolution / runtime / query projection` 六个域。后台推进从“直接扫描业务对象的线程循环”演进为“标准 `RuntimeJob` + 协调器 + worker` 的任务驱动模型，并通过显式只读投影稳定前端和 `P5` 查询。

**Tech Stack:** FastAPI, Pydantic, Python, pytest, React 18, TypeScript, Vitest

---

## File Structure

- Create: `apps/api/app/tool_hub/runtime_models.py`
- Create: `apps/api/app/tool_hub/runtime_repository.py`
- Create: `apps/api/app/tool_hub/runtime_service.py`
- Create: `apps/api/app/tool_hub/registry_service.py`
- Create: `apps/api/app/tool_hub/demand_service.py`
- Create: `apps/api/app/tool_hub/manufacture_service.py`
- Create: `apps/api/app/tool_hub/evolution_service.py`
- Create: `apps/api/app/tool_hub/query_models.py`
- Create: `apps/api/app/tool_hub/query_service.py`
- Create: `apps/api/tests/test_tool_hub_runtime_repository.py`
- Create: `apps/api/tests/test_tool_hub_runtime_service.py`
- Create: `apps/api/tests/test_tool_hub_query_service.py`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/api/tests/test_tool_hub_evolution_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

### Task 1: Introduce explicit runtime job and lease models

**Files:**
- Create: `apps/api/tests/test_tool_hub_runtime_repository.py`
- Create: `apps/api/app/tool_hub/runtime_models.py`
- Create: `apps/api/app/tool_hub/runtime_repository.py`
- Modify: `apps/api/app/tool_hub/repository.py`

- [ ] **Step 1: Write the failing repository tests for runtime jobs**

```python
from pathlib import Path

from app.tool_hub.runtime_models import RuntimeJob, RuntimeLease
from app.tool_hub.runtime_repository import RuntimeRepository


def test_runtime_repository_can_save_list_and_lease_jobs(tmp_path: Path) -> None:
    repository = RuntimeRepository(tmp_path)
    job = RuntimeJob(
        job_id="job-001",
        job_type="manufacture_execution",
        queue_name="p4-manufacture",
        aggregate_type="tool_manufacture_plan",
        aggregate_id="plan-001",
        trigger_source="internal_command",
        trigger_actor_id="p4-system",
        payload_ref="plan-001",
    )

    repository.save_job(job)
    queued = repository.list_jobs(status="queued")

    assert [item.job_id for item in queued] == ["job-001"]

    leased = repository.acquire_job(
        queue_name="p4-manufacture",
        worker_id="worker-a",
        lease_seconds=30,
    )

    assert leased is not None
    assert leased.status == "leased"
    assert leased.leased_by == "worker-a"


def test_runtime_repository_records_execution_attempts(tmp_path: Path) -> None:
    repository = RuntimeRepository(tmp_path)
    repository.save_execution_record(
        job_id="job-001",
        attempt_number=1,
        worker_id="worker-a",
        status="failed",
        error_code="dependency_unavailable",
        error_message="queue timeout",
    )

    records = repository.list_execution_records("job-001")

    assert len(records) == 1
    assert records[0].error_code == "dependency_unavailable"
```

- [ ] **Step 2: Run the repository tests to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_runtime_repository.py -q`

Expected:
- import errors for `runtime_models` or `runtime_repository`
- or missing method failures such as `AttributeError: 'RuntimeRepository' object has no attribute 'acquire_job'`

- [ ] **Step 3: Implement the runtime models**

```python
from pydantic import BaseModel, Field

from app.tool_hub.models import now_iso


class RuntimeJob(BaseModel):
    job_id: str
    job_type: str
    queue_name: str
    aggregate_type: str
    aggregate_id: str
    trigger_source: str
    trigger_actor_id: str
    payload_ref: str
    status: str = "queued"
    attempt_count: int = 0
    max_attempts: int = 3
    priority: int = 100
    not_before: str | None = None
    leased_by: str | None = None
    leased_until: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class RuntimeExecutionRecord(BaseModel):
    record_id: str
    job_id: str
    attempt_number: int
    worker_id: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    started_at: str = Field(default_factory=now_iso)
    finished_at: str = Field(default_factory=now_iso)


class RuntimeLease(BaseModel):
    job_id: str
    worker_id: str
    leased_until: str
```

- [ ] **Step 4: Implement the runtime repository**

```python
class RuntimeRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.jobs_dir = self.root / "runtime_jobs"
        self.execution_records_dir = self.root / "runtime_execution_records"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.execution_records_dir.mkdir(parents=True, exist_ok=True)

    def save_job(self, job: RuntimeJob) -> RuntimeJob:
        self._write_json(self.jobs_dir / f"{job.job_id}.json", job.model_dump(mode="json"))
        return job

    def acquire_job(self, *, queue_name: str, worker_id: str, lease_seconds: int) -> RuntimeJob | None:
        for job in self.list_jobs(status="queued"):
            if job.queue_name != queue_name:
                continue
            leased = job.model_copy(
                update={
                    "status": "leased",
                    "leased_by": worker_id,
                    "leased_until": (datetime.now(tz=UTC) + timedelta(seconds=lease_seconds)).isoformat(),
                    "updated_at": now_iso(),
                }
            )
            return self.save_job(leased)
        return None
```

- [ ] **Step 5: Re-run the repository tests to verify GREEN**

Run: `uv run pytest apps/api/tests/test_tool_hub_runtime_repository.py -q`

Expected:
- all tests pass

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/tool_hub/runtime_models.py \
  apps/api/app/tool_hub/runtime_repository.py \
  apps/api/app/tool_hub/repository.py \
  apps/api/tests/test_tool_hub_runtime_repository.py
git commit -m "feat: add p4 runtime job repository"
```

### Task 2: Split the current ToolHubService into explicit domain services

**Files:**
- Create: `apps/api/app/tool_hub/registry_service.py`
- Create: `apps/api/app/tool_hub/demand_service.py`
- Create: `apps/api/app/tool_hub/manufacture_service.py`
- Create: `apps/api/app/tool_hub/evolution_service.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/api/tests/test_tool_hub_evolution_api.py`

- [ ] **Step 1: Write the failing domain-service extraction test**

```python
def test_tool_hub_service_delegates_to_domain_services(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    detail = service.create_mock_blue_force_demand_sheet()
    assert detail.sheet_id.startswith("tds-")

    run = service.run_evolution(actor_id="tester", trigger_type="manual")
    assert run.run_id.startswith("evolution-run-")
```

- [ ] **Step 2: Run the existing API tests to verify RED after introducing empty domain modules**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_evolution_api.py -q`

Expected:
- import errors or delegation failures while services are being extracted

- [ ] **Step 3: Implement registry, demand, manufacture and evolution services**

```python
class RegistryService:
    def __init__(self, repository: ToolHubRepository) -> None:
        self.repository = repository

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        tool = ToolDefinition(tool_id=f"tool-{uuid4().hex[:12]}", **payload.model_dump(mode="json"))
        return self.repository.save_tool(tool)


class DemandService:
    def __init__(self, repository: ToolHubRepository, registry_service: RegistryService) -> None:
        self.repository = repository
        self.registry_service = registry_service

    def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
        ...
```

- [ ] **Step 4: Turn `ToolHubService` into a façade that wires domain services**

```python
class ToolHubService:
    def __init__(...):
        self.repository = ToolHubRepository(self.root)
        self.registry_service = RegistryService(self.repository)
        self.demand_service = DemandService(self.repository, self.registry_service)
        self.manufacture_service = ManufactureService(self.repository, self.registry_service)
        self.evolution_service = EvolutionService(self.repository, self.registry_service)

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        saved = self.registry_service.create_tool(payload)
        self.mark_evolution_dirty()
        return saved
```

- [ ] **Step 5: Re-run the API tests to verify GREEN**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_evolution_api.py -q`

Expected:
- all tests pass with unchanged external API behavior

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/tool_hub/registry_service.py \
  apps/api/app/tool_hub/demand_service.py \
  apps/api/app/tool_hub/manufacture_service.py \
  apps/api/app/tool_hub/evolution_service.py \
  apps/api/app/tool_hub/service.py \
  apps/api/tests/test_tool_hub_api.py \
  apps/api/tests/test_tool_hub_evolution_api.py
git commit -m "refactor: split p4 tool hub domain services"
```

### Task 3: Replace the scan-everything loop with a job-driven runtime coordinator

**Files:**
- Create: `apps/api/app/tool_hub/runtime_service.py`
- Create: `apps/api/tests/test_tool_hub_runtime_service.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/tool_hub/repository.py`

- [ ] **Step 1: Write the failing runtime coordinator test**

```python
def test_runtime_coordinator_processes_manufacture_and_evolution_jobs(tmp_path: Path) -> None:
    service = _build_service(tmp_path, enable_background_executor=False)
    detail = service.create_mock_blue_force_demand_sheet()
    target_item = next(item for item in detail.items if item.recommendation_type == "manufacture_candidate")

    service.review_demand_item(
        target_item.item_id,
        ToolDemandReviewDecisionRequest(
            decision="approve_manufacture",
            reviewed_by="tester",
            review_comment="enqueue manufacture",
            importance_score=85,
            urgency_score=70,
            rationality_verdict="approved",
        ),
    )

    runtime = ToolHubRuntimeService(service)
    runtime.run_once()

    progress = service.get_demand_item_progress(target_item.item_id)
    assert progress is not None
    assert progress.processing_status in {"manufacturing_in_progress", "ready_for_fetch"}
```

- [ ] **Step 2: Run the runtime test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_runtime_service.py -q`

Expected:
- missing `ToolHubRuntimeService`
- or no job was created for manufacture approval

- [ ] **Step 3: Enqueue standard runtime jobs from demand and evolution flows**

```python
def enqueue_manufacture_job(self, plan: ToolManufacturePlan, actor_id: str) -> RuntimeJob:
    return self.runtime_repository.save_job(
        RuntimeJob(
            job_id=f"job-{uuid4().hex[:12]}",
            job_type="manufacture_execution",
            queue_name="p4-manufacture",
            aggregate_type="tool_manufacture_plan",
            aggregate_id=plan.item_id,
            trigger_source="internal_command",
            trigger_actor_id=actor_id,
            payload_ref=plan.item_id,
        )
    )
```

- [ ] **Step 4: Implement a job-driven runtime service**

```python
class ToolHubRuntimeService:
    def __init__(self, tool_hub_service: ToolHubService) -> None:
        self.tool_hub_service = tool_hub_service
        self.runtime_repository = RuntimeRepository(tool_hub_service.root)

    def run_once(self) -> None:
        self._run_due_evolution_scan()
        self._run_queue("p4-evolution", self._execute_evolution_job)
        self._run_queue("p4-manufacture", self._execute_manufacture_job)
        self._run_queue("p4-projection", self._execute_projection_job)
```

- [ ] **Step 5: Replace the thread loop to call the runtime service instead of scanning aggregates**

```python
def run_runtime_cycle(self) -> None:
    runtime_service = ToolHubRuntimeService(self)
    runtime_service.run_once()
```

- [ ] **Step 6: Re-run the runtime and API tests to verify GREEN**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_runtime_service.py -q`
- `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_evolution_api.py -q`

Expected:
- runtime tests pass
- existing API behavior remains green

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/tool_hub/runtime_service.py \
  apps/api/app/tool_hub/service.py \
  apps/api/app/tool_hub/repository.py \
  apps/api/tests/test_tool_hub_runtime_service.py
git commit -m "refactor: drive p4 runtime by jobs and workers"
```

### Task 4: Introduce explicit query projections and move reads off the raw snapshot

**Files:**
- Create: `apps/api/app/tool_hub/query_models.py`
- Create: `apps/api/app/tool_hub/query_service.py`
- Create: `apps/api/tests/test_tool_hub_query_service.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/tool_hub/service.py`

- [ ] **Step 1: Write the failing query projection test**

```python
def test_query_service_builds_projection_for_overview_and_evolution(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    query_service = ToolHubQueryService(service.repository)

    overview = query_service.get_overview_projection()
    evolution = query_service.get_evolution_workspace_projection()

    assert overview.metric_total_tools >= 0
    assert evolution.config.config_id == "default"
```

- [ ] **Step 2: Run the projection test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_query_service.py -q`

Expected:
- missing `ToolHubQueryService`
- or missing projection model types

- [ ] **Step 3: Define projection models**

```python
class OverviewProjection(BaseModel):
    snapshot_id: str
    metric_total_tools: int
    metric_verified_tools: int
    metric_pending_manufacture: int
    metric_pending_evolution_tasks: int


class EvolutionWorkspaceProjection(BaseModel):
    snapshot_id: str
    config: EvolutionInspectionConfig
    runs: list[EvolutionRun]
    tasks: list[EvolutionTask]
```

- [ ] **Step 4: Implement a query service over repository reads**

```python
class ToolHubQueryService:
    def __init__(self, repository: ToolHubRepository) -> None:
        self.repository = repository

    def get_overview_projection(self) -> OverviewProjection:
        snapshot = build_tool_hub_snapshot(
            catalogs=ToolHubCatalogs(...),
            tools=self.repository.list_tools(),
            demand_sheets=self.repository.list_demand_sheets(),
            match_runs=self.repository.list_match_runs(),
            evolution_config=self.repository.get_evolution_config(),
            evolution_runs=self.repository.list_evolution_runs(),
            evolution_tasks=self.repository.list_evolution_tasks(),
            runtime_state=self.repository.get_runtime_state(),
        )
        return OverviewProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            metric_total_tools=snapshot.overview.total_tools,
            metric_verified_tools=snapshot.overview.verified_tools,
            metric_pending_manufacture=snapshot.overview.manufacturing_count,
            metric_pending_evolution_tasks=snapshot.overview.pending_suggestions,
        )
```

- [ ] **Step 5: Route `get_overview`, `list_evolution_runs`, `list_tools` and related reads through the query service**

```python
def get_overview(self) -> ToolHubOverviewReadEnvelope:
    projection = self.query_service.get_overview_projection()
    return ToolHubOverviewReadEnvelope(meta=ToolHubMeta(snapshot_id=projection.snapshot_id), data=projection)
```

- [ ] **Step 6: Re-run the query and regression tests to verify GREEN**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_query_service.py -q`
- `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_evolution_api.py -q`

Expected:
- projection tests pass
- external read APIs still pass

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/tool_hub/query_models.py \
  apps/api/app/tool_hub/query_service.py \
  apps/api/app/tool_hub/snapshot.py \
  apps/api/app/tool_hub/service.py \
  apps/api/tests/test_tool_hub_query_service.py
git commit -m "refactor: add p4 query projections"
```

### Task 5: Preserve route contracts, refresh frontend compatibility, and complete regression verification

**Files:**
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: Write or update the failing contract regression tests**

```tsx
it("keeps XX-P4 evolution and demand workspaces working after backend refactor", async () => {
  render(<XXP4Page />);

  await user.click(screen.getByRole("tab", { name: /输入工序链/i }));
  expect(document.querySelector("#xx-p4-demand-item-list")).toBeTruthy();

  await user.click(screen.getByRole("tab", { name: /自演进巡检/i }));
  expect(document.querySelector("#xx-p4-evolution-config-card")).toBeTruthy();
});
```

- [ ] **Step 2: Run the frontend compatibility tests to verify RED**

Run: `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx AppRoutes.test.tsx`

Expected:
- route or payload shape failures if backend response envelopes drifted

- [ ] **Step 3: Keep route payloads and frontend client types backward-compatible**

```python
@router.get("/evolution/tasks", response_model=EvolutionTaskReadEnvelope)
def get_evolution_tasks(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_evolution_tasks()
```

```ts
export async function getEvolutionTasks(): Promise<EvolutionTaskEnvelope> {
  const response = await api.get<EvolutionTaskReadEnvelope>("/tool-hub/evolution/tasks");
  return response.data.data;
}
```

- [ ] **Step 4: Run the full verification suite**

Run:
- `uv run pytest apps/api/tests/test_tool_hub_runtime_repository.py apps/api/tests/test_tool_hub_runtime_service.py apps/api/tests/test_tool_hub_query_service.py apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_evolution_api.py -q`
- `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx AppRoutes.test.tsx`
- `corepack pnpm --dir apps/web build`

Expected:
- all backend tests pass
- frontend contract tests pass
- production build succeeds

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/api/routes/tool_hub.py \
  apps/web/src/lib/api.ts \
  apps/web/src/lib/toolHub.ts \
  apps/web/src/pages/XXP4Page.tsx \
  apps/web/src/test/XXP4Page.test.tsx
git commit -m "test: lock p4 backend refactor compatibility"
```

## Spec Coverage Check

- `2026-04-18-p4-core-business-cycle-design.md`
  - covered by Tasks 2, 3, 4, 5
- `2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
  - covered by Tasks 1 and 3
- `2026-04-18-p4-backend-service-boundary-design.md`
  - covered by Task 2 and Task 5
- `2026-04-18-p4-data-and-projection-model-design.md`
  - covered by Tasks 1 and 4

No uncovered spec sections remain for the first implementation batch. Database migration and external queue products are intentionally deferred because the current batch only establishes the code skeleton and contract-preserving runtime model inside the existing FastAPI service.

