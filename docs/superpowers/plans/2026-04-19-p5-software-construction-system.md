# P5 Software Construction System Implementation Plan

> 正式归档说明：`P5` 当前正式详细设计入口为 `DOC/CODEX_DOC/02_设计说明/P5_软件构建系统/P5-软件构建系统设计.md`。本文件作为工作层实施计划保留；若其中的实施约束、范围或结构被确认并长期复用，必须同步回 `DOC/CODEX_DOC/03_研制计划/` 与相关正式设计文档。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable `P5` delivery loop that consumes frozen `P3` design data and readable `P4` supply data, generates a versioned delivery directory with manifest/report/gap files, and exposes a minimal `/build` workspace.

**Architecture:** Add a new `software_build` backend module that follows the existing `P3` repository/service/route pattern. `P5` assembles a delivery order from `P3` baseline modules, probes `P4` tool supply as auxiliary input, writes versioned export directories with explicit gap reporting, and exposes overview/order APIs consumed by a minimal build workspace page.

**Tech Stack:** FastAPI, Pydantic, file-based JSON repositories, React, Ant Design, Vitest, Pytest.

---

### Task 1: Create P5 backend API skeleton

**Files:**
- Create: `apps/api/tests/test_software_build_api.py`
- Create: `apps/api/app/software_build/__init__.py`
- Create: `apps/api/app/software_build/models.py`
- Create: `apps/api/app/software_build/repository.py`
- Create: `apps/api/app/software_build/service.py`
- Create: `apps/api/app/api/routes/software_build.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Write the failing API test for overview and order creation**

```python
def test_p5_delivery_order_can_be_created_from_frozen_p3_order(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _build_frozen_p3_order(tmp_path)

    created = client.post(
        "/api/software-build/orders",
        json={"p3_order_id": p3_order_id, "requested_by": "P5", "notes": "首轮组装"},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    overview = client.get("/api/software-build/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["order_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_delivery_order_can_be_created_from_frozen_p3_order -v`
Expected: FAIL because `/api/software-build/orders` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class P5DeliveryOrderCreate(BaseModel):
    p3_order_id: str
    requested_by: str
    notes: str = ""


class P5DeliveryOrder(BaseModel):
    delivery_order_id: str
    p3_order_id: str
    status: Literal["draft"] = "draft"
```

```python
@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_delivery_order(payload: P5DeliveryOrderCreate, service: SoftwareBuildService = Depends(get_software_build_service)):
    return service.create_delivery_order(payload)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_delivery_order_can_be_created_from_frozen_p3_order -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_software_build_api.py apps/api/app/software_build apps/api/app/api/routes/software_build.py apps/api/app/config.py apps/api/app/main.py
git commit -m "feat: add p5 delivery order api skeleton"
```

### Task 2: Build P5 assembly/export loop with gap reporting

**Files:**
- Modify: `apps/api/tests/test_software_build_api.py`
- Modify: `apps/api/app/software_build/models.py`
- Modify: `apps/api/app/software_build/repository.py`
- Modify: `apps/api/app/software_build/service.py`
- Modify: `apps/api/app/api/routes/software_build.py`

- [ ] **Step 1: Write the failing test for export attempt generation**

```python
def test_p5_attempt_exports_directory_and_gap_files(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _build_frozen_p3_order(tmp_path)
    delivery_order_id = client.post(
        "/api/software-build/orders",
        json={"p3_order_id": p3_order_id, "requested_by": "P5", "notes": "首轮组装"},
    ).json()["delivery_order_id"]

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={"export_root": str(tmp_path / "exports"), "build_profile": "baseline", "attempt_note": "attempt-1"},
    )

    assert attempt.status_code == 201
    payload = attempt.json()
    assert payload["validation_report"]["structure_status"] == "passed"
    assert (tmp_path / "exports").exists()
    assert Path(payload["export_directory"]).joinpath("docs", "delivery-report.md").exists()
    assert Path(payload["export_directory"]).joinpath("docs", "gap-list.md").exists()
    assert Path(payload["export_directory"]).joinpath("build-manifest.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_attempt_exports_directory_and_gap_files -v`
Expected: FAIL because attempt route and export generation are missing.

- [ ] **Step 3: Write minimal implementation**

```python
attempt_root = export_root / delivery_order.delivery_order_id / f"attempt-{sequence:03d}"
(attempt_root / "frontend").mkdir(parents=True, exist_ok=True)
(attempt_root / "backend").mkdir(parents=True, exist_ok=True)
(attempt_root / "deploy").mkdir(parents=True, exist_ok=True)
(attempt_root / "docs").mkdir(parents=True, exist_ok=True)
```

```python
manifest = {
    "delivery_order_id": delivery_order.delivery_order_id,
    "attempt_id": attempt.attempt_id,
    "gaps": [gap.model_dump(mode="json") for gap in attempt.gaps],
    "validation_report": attempt.validation_report.model_dump(mode="json"),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_attempt_exports_directory_and_gap_files -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_software_build_api.py apps/api/app/software_build
git commit -m "feat: add p5 assembly export loop"
```

### Task 3: Add supply binding heuristics and feedback task generation

**Files:**
- Modify: `apps/api/tests/test_software_build_api.py`
- Modify: `apps/api/app/software_build/service.py`
- Modify: `apps/api/app/software_build/models.py`

- [ ] **Step 1: Write the failing test for supply hit vs. gap classification**

```python
def test_p5_attempt_marks_supply_hits_and_pending_feedback(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _build_frozen_p3_order(tmp_path, recommended_tools=["workflow_engine"])
    _seed_tool_hub_tool(tmp_path, tool_id="tool-workflow-engine", slug="workflow-engine")
    delivery_order_id = client.post(
        "/api/software-build/orders",
        json={"p3_order_id": p3_order_id, "requested_by": "P5", "notes": "首轮组装"},
    ).json()["delivery_order_id"]

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={"export_root": str(tmp_path / "exports"), "build_profile": "baseline", "attempt_note": "attempt-1"},
    )

    payload = attempt.json()
    assert payload["assembly_plan"]["modules"][0]["binding_status"] == "bound"
    assert payload["feedback_tasks"][0]["status"] == "pending_confirmation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_attempt_marks_supply_hits_and_pending_feedback -v`
Expected: FAIL because supply matching and feedback generation are incomplete.

- [ ] **Step 3: Write minimal implementation**

```python
def _match_tool(self, module: DesignModule) -> ToolDefinition | None:
    normalized_targets = {item.replace("_", "-").lower() for item in module.recommended_tools}
    for tool in self.tool_hub_repository.list_tools():
        candidates = {tool.slug.lower(), tool.tool_id.lower(), *[keyword.lower() for keyword in tool.keywords]}
        if normalized_targets & candidates:
            return tool
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_software_build_api.py::test_p5_attempt_marks_supply_hits_and_pending_feedback -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_software_build_api.py apps/api/app/software_build/service.py apps/api/app/software_build/models.py
git commit -m "feat: classify p5 supply gaps and feedback tasks"
```

### Task 4: Add minimal P5 frontend workspace

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/softwareBuild.ts`
- Modify: `apps/web/src/pages/BuildWorkspacePage.tsx`
- Create: `apps/web/src/test/BuildWorkspacePage.test.tsx`

- [ ] **Step 1: Write the failing page test**

```tsx
test("renders P5 overview and latest attempt summary", async () => {
  render(
    <MemoryRouter initialEntries={["/build"]}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P5 交付主单")).toBeInTheDocument();
  expect(await screen.findByText("attempt-001")).toBeInTheDocument();
  expect(await screen.findByText("supply_gap")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- BuildWorkspacePage.test.tsx`
Expected: FAIL because the page is still placeholder-only.

- [ ] **Step 3: Write minimal implementation**

```tsx
const [overview, setOverview] = useState<P5Overview | null>(null);
const [orders, setOrders] = useState<P5DeliveryOrderSummary[]>([]);

useEffect(() => {
  void Promise.all([getSoftwareBuildOverview(), getSoftwareBuildOrders()]).then(([overviewRes, ordersRes]) => {
    setOverview(overviewRes.data.data);
    setOrders(ordersRes.data.data.items);
  });
}, []);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && npm test -- BuildWorkspacePage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/softwareBuild.ts apps/web/src/pages/BuildWorkspacePage.tsx apps/web/src/test/BuildWorkspacePage.test.tsx
git commit -m "feat: add p5 build workspace shell"
```

### Task 5: Verify P5 vertical slice and update docs

**Files:**
- Modify: `DOC/CODEX_DOC/05_测试文档/01_自测报告/...` (new record if needed)
- Modify: `DOC/CODEX_DOC/05_测试文档/02_验收清单/...` (new record if needed)
- Modify: `DOC/CODEX_DOC/06_过程文档/01_会话交接/...` (new record if needed)

- [ ] **Step 1: Run focused backend and frontend verification**

Run: `pytest apps/api/tests/test_software_build_api.py -v`
Expected: PASS

Run: `cd apps/web && npm test -- BuildWorkspacePage.test.tsx P3P4P5SimPages.test.tsx AppRoutes.test.tsx`
Expected: PASS

- [ ] **Step 2: Run broader smoke verification**

Run: `pytest apps/api/tests/test_software_design_api.py apps/api/tests/test_tool_hub_demand_chain_api.py -v`
Expected: PASS

- [ ] **Step 3: Record implemented scope and residual P5 backlog**

```markdown
- implemented: delivery order, assembly attempt, versioned export, gap report, feedback task, build workspace shell
- backlog: canvas editing, real local build executor, richer P3/P4 contract freeze
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-19-p5-software-construction-system.md DOC/CODEX_DOC
git commit -m "docs: record p5 implementation verification"
```
