# P4 Input Chain Closed-Loop Implementation Plan

> 2026-04-17 修订：本计划已按“推荐优先、逐项审定、批准后交付/研制”的口径收敛。`工具需求单` 视为 `P3 / P4 / P5` 的主干交付流对象。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4` 落地 `P3-sim -> P4 -> P5-sim` 的输入工序链闭环，支持模拟蓝军树型工具需求总单、叶子项推荐分析、人工逐项审定、批准后交付或研制，以及整单和叶子双查询。

**Architecture:** 后端在现有 `tool_hub` 子域上新增 `demand_sheets / demand_items / manufacture_plans` 三类事实对象和对应 API，统一继续投影到 `ToolHubStateSnapshot`。前端新增 `/xx-p3-sim` 与 `/xx-p5-sim` 两个独立模拟页，同时把 `/xx-p4` 的“输入工具链”升级为“工具需求列表 + 需求审批与处置面板”的审定工作区。当前阶段不做真实 `P3/P5`，未命中分支仅在人工批准后进入按查询自动推进的模拟制造。

**Tech Stack:** FastAPI, Pydantic, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

## File Structure

**Backend contracts and storage**
- Create: `apps/api/app/tool_hub/demand_fixtures.py`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Create: `apps/api/tests/test_tool_hub_demand_chain_api.py`

**Frontend contracts and routes**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/App.tsx`
- Create: `apps/web/src/pages/XXP3SimPage.tsx`
- Create: `apps/web/src/pages/XXP5SimPage.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`

**Frontend focused components**
- Create: `apps/web/src/components/p4/P4DemandSheetTree.tsx`
- Create: `apps/web/src/components/p4/P4DemandItemBoard.tsx`
- Create: `apps/web/src/components/p4/P4SupplyResultPreview.tsx`
- Create: `apps/web/src/components/p3/P3BlueForceGenerator.tsx`
- Create: `apps/web/src/components/p5/P5DemandQueryPanel.tsx`
- Modify: `apps/web/src/components/p4/P4InputChainWorkspace.tsx`

**Frontend tests**
- Create: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/AppRoutes.test.tsx`

**Docs / mirrors**
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

### Task 1: Lock Backend Demand-Chain Contract with Failing Tests

**Files:**
- Create: `apps/api/tests/test_tool_hub_demand_chain_api.py`
- Test: `apps/api/tests/test_tool_hub_demand_chain_api.py`

- [ ] **Step 1: Write the failing test for mock blue-force sheet creation**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.tool_hub import get_tool_hub_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app
from app.tool_hub.service import ToolHubService


def _write_archive(path: Path) -> None:
    path.write_text(
        """
{
  "summary": {
    "document_count": 1,
    "entity_count": 1,
    "event_count": 0,
    "process_count": 1
  },
  "documents": [],
  "entities": [],
  "events": [],
  "processes": [],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def _build_client(tmp_path: Path) -> TestClient:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")

    app = create_app()
    service = ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=False,
    )
    app.dependency_overrides[get_tool_hub_service] = lambda: service
    return TestClient(app)


def test_create_mock_blue_force_demand_sheet(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    response = client.post("/api/tool-hub/mock-generators/blue-force-demand-sheets")
    assert response.status_code == 201

    payload = response.json()
    assert payload["sheet_id"]
    assert payload["business_case"] == "simulated_blue_force"
    assert payload["lifecycle_status"] == "accepted"
    assert payload["review_status"] == "pending_review"
    assert payload["delivery_status"] == "not_delivered"
    assert payload["item_count"] >= 6
```

- [ ] **Step 2: Write the failing test for sheet, item, and progress queries**

```python
def test_query_demand_sheet_and_item_progress(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    created = client.post("/api/tool-hub/mock-generators/blue-force-demand-sheets")
    sheet_id = created.json()["sheet_id"]

    sheet_response = client.get(f"/api/tool-hub/demand-sheets/{sheet_id}")
    assert sheet_response.status_code == 200
    sheet_payload = sheet_response.json()
    assert sheet_payload["sheet_id"] == sheet_id
    assert sheet_payload["items"][0]["item_id"]

    item_id = sheet_payload["items"][0]["item_id"]
    item_response = client.get(f"/api/tool-hub/demand-items/{item_id}")
    assert item_response.status_code == 200
    assert item_response.json()["item_id"] == item_id

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["item_id"] == item_id
    assert progress_payload["status"] in {
        "matched_existing",
        "manufacturing_pending",
        "manufacturing_in_progress",
        "ready_for_fetch",
    }
```

- [ ] **Step 3: Run the new backend tests to verify they fail**

Run: `uv run pytest apps/api/tests/test_tool_hub_demand_chain_api.py -q`
Expected: FAIL with `404 Not Found` or missing demand-chain models/routes.

- [ ] **Step 4: Commit the failing-test scaffold**

```bash
git add apps/api/tests/test_tool_hub_demand_chain_api.py
git commit -m "test: add failing demand chain API coverage"
```

### Task 2: Implement Demand-Sheet Models, Repository, Service, and Routes

**Files:**
- Create: `apps/api/app/tool_hub/demand_fixtures.py`
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/repository.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/tool_hub/snapshot.py`
- Modify: `apps/api/app/api/routes/tool_hub.py`
- Test: `apps/api/tests/test_tool_hub_demand_chain_api.py`

- [ ] **Step 1: Add backend contract models for sheet, node, item, progress, and fetch manifest**

```python
class ComponentSpec(BaseModel):
    component_name: str
    component_code: str
    problem_statement: str = ""
    required_input_types: list[str] = Field(default_factory=list)
    expected_output_types: list[str] = Field(default_factory=list)
    preferred_tool_forms: list[str] = Field(default_factory=list)
    preferred_runtime_platforms: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    acceptance_notes: str = ""


class ToolDemandNode(BaseModel):
    node_id: str
    node_type: Literal["system", "subsystem", "sub_subsystem", "module", "component"]
    node_name: str
    node_code: str
    description: str = ""
    business_domain_id: str = ""
    children: list["ToolDemandNode"] = Field(default_factory=list)
    component_spec: ComponentSpec | None = None


class ToolDemandSheetCreateRequest(BaseModel):
    sheet_name: str
    source: dict[str, str]
    requested_by: str
    root_node: ToolDemandNode
    notes: str = ""
```

- [ ] **Step 2: Extend the repository with demand-sheet, item, and manufacture-plan directories**

```python
class ToolHubRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.tools_dir = self.root / "tools"
        self.demand_sheets_dir = self.root / "demand_sheets"
        self.demand_items_dir = self.root / "demand_items"
        self.manufacture_plans_dir = self.root / "manufacture_plans"
        self.match_runs_dir = self.root / "runs" / "match"
        self.evolution_runs_dir = self.root / "runs" / "evolution"
        for directory in (
            self.tools_dir,
            self.demand_sheets_dir,
            self.demand_items_dir,
            self.manufacture_plans_dir,
            self.match_runs_dir,
            self.evolution_runs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: Add a blue-force demand fixture generator**

```python
def build_mock_blue_force_request() -> ToolDemandSheetCreateRequest:
    return ToolDemandSheetCreateRequest(
        sheet_name="模拟蓝军一期工具需求单",
        source={
            "phase": "p3_simulator",
            "producer": "mock_blue_force_generator",
            "business_case": "simulated_blue_force",
            "scenario_id": "blue-force-sim-001",
            "scenario_name": "模拟蓝军对抗推演一期",
        },
        requested_by="P3",
        root_node=ToolDemandNode(
            node_id="sys-blue-force",
            node_type="system",
            node_name="模拟蓝军系统",
            node_code="SYS-BLUE-FORCE",
            business_domain_id="simulated_blue_force",
            children=[
                ToolDemandNode(
                    node_id="subsys-battlefield-modeling",
                    node_type="subsystem",
                    node_name="战场建模",
                    node_code="SUBSYS-BATTLEFIELD-MODELING",
                    business_domain_id="simulated_blue_force",
                    children=[],
                ),
                ToolDemandNode(
                    node_id="subsys-blue-force-organization",
                    node_type="subsystem",
                    node_name="蓝军编组",
                    node_code="SUBSYS-BLUE-FORCE-ORGANIZATION",
                    business_domain_id="simulated_blue_force",
                    children=[],
                ),
                ToolDemandNode(
                    node_id="subsys-wargame",
                    node_type="subsystem",
                    node_name="对抗推演",
                    node_code="SUBSYS-WARGAME",
                    business_domain_id="simulated_blue_force",
                    children=[],
                ),
                ToolDemandNode(
                    node_id="subsys-action-control",
                    node_type="subsystem",
                    node_name="行动控制",
                    node_code="SUBSYS-ACTION-CONTROL",
                    business_domain_id="simulated_blue_force",
                    children=[],
                ),
                ToolDemandNode(
                    node_id="subsys-assessment-review",
                    node_type="subsystem",
                    node_name="评估复盘",
                    node_code="SUBSYS-ASSESSMENT-REVIEW",
                    business_domain_id="simulated_blue_force",
                    children=[],
                ),
            ],
        ),
    )
```

- [ ] **Step 4: Implement service methods for create, split, query, and progress**

```python
def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
    sheet_id = f"tds-{uuid4().hex[:12]}"
    items = self._build_demand_items(sheet_id, payload.root_node)
    sheet = ToolDemandSheet(
        sheet_id=sheet_id,
        sheet_name=payload.sheet_name,
        lifecycle_status="accepted",
        review_status="pending_review",
        delivery_status="not_delivered",
        source=payload.source,
        requested_by=payload.requested_by,
        business_case=payload.source["business_case"],
        root_node=payload.root_node,
        item_count=len(items),
    )
    self.repository.save_demand_sheet(sheet)
    for item in items:
        processed_item = self._process_demand_item(item)
        self.repository.save_demand_item(processed_item)
    return self.get_demand_sheet_detail(sheet_id)
```

- [ ] **Step 5: Add the new demand-chain routes**

```python
@router.post("/mock-generators/blue-force-demand-sheets", status_code=status.HTTP_201_CREATED)
def create_mock_blue_force_demand_sheet(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.create_mock_blue_force_demand_sheet()


@router.post("/demand-sheets", status_code=status.HTTP_201_CREATED)
def create_demand_sheet(
    payload: ToolDemandSheetCreateRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.create_demand_sheet(payload)


@router.get("/demand-items/{item_id}/progress")
def get_demand_item_progress(item_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    return service.get_demand_item_progress(item_id)
```

- [ ] **Step 6: Run the backend demand-chain tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_tool_hub_demand_chain_api.py -q`
Expected: PASS

- [ ] **Step 7: Run the existing tool-hub regression tests**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
Expected: PASS

- [ ] **Step 8: Commit the backend demand-chain implementation**

```bash
git add apps/api/app/tool_hub/demand_fixtures.py apps/api/app/tool_hub/models.py apps/api/app/tool_hub/repository.py apps/api/app/tool_hub/service.py apps/api/app/tool_hub/snapshot.py apps/api/app/api/routes/tool_hub.py apps/api/tests/test_tool_hub_demand_chain_api.py
git commit -m "feat: add tool hub demand chain backend"
```

### Task 3: Lock Frontend Routes and Demand-Chain UX with Failing Tests

**Files:**
- Create: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`
- Modify: `apps/web/src/test/AppRoutes.test.tsx`

- [ ] **Step 1: Write the failing route test for `/xx-p3-sim` and `/xx-p5-sim`**

```tsx
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

test("renders P3 and P5 simulator routes", async () => {
  getMock.mockResolvedValue({ data: { items: [] } });
  postMock.mockResolvedValue({ data: { sheet_id: "tds-001", item_count: 6 } });

  render(
    <MemoryRouter initialEntries={["/xx-p3-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 模拟发生器")).toBeInTheDocument();

  render(
    <MemoryRouter initialEntries={["/xx-p5-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P5 模拟消费器")).toBeInTheDocument();
});
```

- [ ] **Step 2: Extend the failing `XXP4Page` test for demand-sheet blocks**

```tsx
expect(await screen.findByText("工序单受理区")).toBeInTheDocument();
expect(await screen.findByText("工具需求列表")).toBeInTheDocument();
expect(await screen.findByText("需求审批与处置面板")).toBeInTheDocument();
expect(screen.queryByText("P3 模拟发生区")).not.toBeInTheDocument();
expect(screen.queryByText("P5 输出预览区")).not.toBeInTheDocument();
```

- [ ] **Step 3: Run the new frontend tests to verify they fail**

Run: `corepack pnpm --dir apps/web test -- P3P4P5SimPages.test.tsx XXP4Page.test.tsx AppRoutes.test.tsx`
Expected: FAIL because the new routes and demand-chain UI do not exist yet.

- [ ] **Step 4: Commit the failing frontend tests**

```bash
git add apps/web/src/test/P3P4P5SimPages.test.tsx apps/web/src/test/XXP4Page.test.tsx apps/web/src/test/AppRoutes.test.tsx
git commit -m "test: add failing P3 P4 P5 sim page coverage"
```

### Task 4: Implement Shared Frontend Contracts, Simulator Pages, and P4 Demand Workspace

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/App.tsx`
- Create: `apps/web/src/pages/XXP3SimPage.tsx`
- Create: `apps/web/src/pages/XXP5SimPage.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Create: `apps/web/src/components/p4/P4DemandSheetTree.tsx`
- Create: `apps/web/src/components/p4/P4DemandItemBoard.tsx`
- Create: `apps/web/src/components/p4/P4SupplyResultPreview.tsx`
- Create: `apps/web/src/components/p3/P3BlueForceGenerator.tsx`
- Create: `apps/web/src/components/p5/P5DemandQueryPanel.tsx`
- Modify: `apps/web/src/components/p4/P4InputChainWorkspace.tsx`
- Test: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Test: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: Add frontend mirror types and API helpers**

```ts
export type ToolDemandSheet = {
  sheet_id: string;
  sheet_name: string;
  lifecycle_status: "submitted" | "accepted" | "rejected" | "withdrawn" | "closed";
  review_status: "pending_review" | "reviewing" | "reviewed";
  delivery_status: "not_delivered" | "delivering" | "delivered";
  business_case: string;
  item_count: number;
  matched_existing_count: number;
  manufacturing_count: number;
  ready_for_fetch_count: number;
  failed_count: number;
};

export function createMockBlueForceDemandSheet() {
  return api.post<ToolDemandSheet>("/tool-hub/mock-generators/blue-force-demand-sheets");
}

export function getDemandItemProgress(itemId: string) {
  return api.get<ItemProgressView>(`/tool-hub/demand-items/${itemId}/progress`);
}
```

- [ ] **Step 2: Add dedicated routes for the simulator pages**

```tsx
if (location.pathname.startsWith("/xx-p4") || location.pathname.startsWith("/xx-p3-sim") || location.pathname.startsWith("/xx-p5-sim")) {
  return (
    <Routes>
      <Route path="/xx-p3-sim" element={<XXP3SimPage />} />
      <Route path="/xx-p4" element={<XXP4Page />} />
      <Route path="/xx-p5-sim" element={<XXP5SimPage />} />
    </Routes>
  );
}
```

- [ ] **Step 3: Build the P3 simulator page**

```tsx
export function XXP3SimPage() {
  const [sheet, setSheet] = useState<ToolDemandSheet | null>(null);

  async function handleGenerate() {
    const response = await createMockBlueForceDemandSheet();
    setSheet(response.data);
  }

  return (
    <Space direction="vertical" size={16} style={{ display: "flex", padding: 24 }}>
      <Typography.Title level={2}>P3 模拟发生器</Typography.Title>
      <P3BlueForceGenerator onGenerate={handleGenerate} sheet={sheet} />
    </Space>
  );
}
```

- [ ] **Step 4: Build the P5 simulator page**

```tsx
export function XXP5SimPage() {
  return (
    <Space direction="vertical" size={16} style={{ display: "flex", padding: 24 }}>
      <Typography.Title level={2}>P5 模拟消费器</Typography.Title>
      <P5DemandQueryPanel />
    </Space>
  );
}
```

- [ ] **Step 5: Replace the generic P4 input form with demand-sheet workspace blocks**

```tsx
<Space direction="vertical" size={16} style={{ display: "flex" }}>
  <Card title="工序单受理区">
    <Typography.Paragraph>新建总单请前往 /xx-p3-sim</Typography.Paragraph>
    <Typography.Paragraph>结果消费与进度决策请前往 /xx-p5-sim</Typography.Paragraph>
    <Select value={activeSheet?.sheet_id} onChange={(value) => void onSelectSheet(value)} />
  </Card>
  <Row gutter={[16, 16]}>
    <Col span={10}>
      <Card title="工具需求列表">
        <P4DemandItemBoard items={activeItems} selectedItemId={selectedItemId} onSelectItem={setSelectedItemId} />
      </Card>
    </Col>
    <Col span={14}>
      <Card title="需求审批与处置面板">
        <P4SupplyResultPreview item={selectedItem} />
        <P4DemandSheetTree sheet={activeSheet} selectedItemId={selectedItemId} onSelectItem={setSelectedItemId} />
      </Card>
    </Col>
  </Row>
</Space>
```

- [ ] **Step 6: Run the new frontend tests to verify they pass**

Run: `corepack pnpm --dir apps/web test -- P3P4P5SimPages.test.tsx XXP4Page.test.tsx AppRoutes.test.tsx`
Expected: PASS

- [ ] **Step 7: Commit the frontend demand-chain UI**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/toolHub.ts apps/web/src/App.tsx apps/web/src/pages/XXP3SimPage.tsx apps/web/src/pages/XXP5SimPage.tsx apps/web/src/pages/XXP4Page.tsx apps/web/src/components/p4/P4DemandSheetTree.tsx apps/web/src/components/p4/P4DemandItemBoard.tsx apps/web/src/components/p4/P4SupplyResultPreview.tsx apps/web/src/components/p3/P3BlueForceGenerator.tsx apps/web/src/components/p5/P5DemandQueryPanel.tsx apps/web/src/components/p4/P4InputChainWorkspace.tsx apps/web/src/test/P3P4P5SimPages.test.tsx apps/web/src/test/XXP4Page.test.tsx apps/web/src/test/AppRoutes.test.tsx
git commit -m "feat: add P3 P4 P5 demand chain simulator pages"
```

### Task 5: Run End-to-End Regression and Sync Mirrors

**Files:**
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- Verify: `apps/api/tests/test_tool_hub_api.py`
- Verify: `apps/api/tests/test_tool_hub_demand_chain_api.py`
- Verify: `apps/web/src/test/XXP4Page.test.tsx`
- Verify: `apps/web/src/test/P3P4P5SimPages.test.tsx`
- Verify: `apps/web/src/test/AppRoutes.test.tsx`

- [ ] **Step 1: Update the local issue mirror to include `P4.2`**

```md
- `P4` 工具仓库 / 工具中台 `[开发中]`
  - `P4.1` 第一批最小闭环 `[已完成]`
  - `P4.2` 输入工序链闭环探索 `[开发中]`
    - `P4.2.1` 协议与对象模型 `[开发中]`
    - `P4.2.2` `P3-sim` 模拟发生器页 `[开发中]`
    - `P4.2.3` `P4` 输入工序链处理闭环 `[开发中]`
    - `P4.2.4` `P5-sim` 模拟消费页 `[开发中]`
    - `P4.2.5` 三段联调与回归验证 `[待开发]`
```

- [ ] **Step 2: Run backend regression**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_demand_chain_api.py -q`
Expected: PASS

- [ ] **Step 3: Run frontend regression**

Run: `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx P3P4P5SimPages.test.tsx AppRoutes.test.tsx viteConfig.test.ts`
Expected: PASS

- [ ] **Step 4: Run production build**

Run: `corepack pnpm --dir apps/web build`
Expected: PASS

- [ ] **Step 5: Commit regression and mirror sync**

```bash
git add docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md
git commit -m "docs: sync P4.2 demand chain mirror state"
```

## Self-Review

**Spec coverage**
- `P3-sim` 独立页: Task 4
- `P4` 输入工序链闭环: Task 2 + Task 4
- `P5-sim` 独立页: Task 4
- 总单、叶子、进度、获取接口协议: Task 2
- 模拟蓝军默认树: Task 2
- 双查询与回归: Task 1 + Task 5

**Placeholder scan**
- No `TBD`, `TODO`, or deferred implementation placeholders remain in the task steps. Remaining `...args` uses are JavaScript spread syntax in test mocks, not unresolved plan placeholders.

**Type consistency**
- `ToolDemandSheetCreateRequest`, `ToolDemandNode`, `ToolDemandItem`, `ToolSupplyResult`, `ItemProgressView`, and `ToolFetchManifest` are introduced in Task 2 and mirrored in Task 4 with the same names.
