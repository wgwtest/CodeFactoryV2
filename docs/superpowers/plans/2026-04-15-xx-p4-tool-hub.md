# XX-P4 Tool Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P4` 落地独立的 `XX-P4` 驾驶舱页与 `tool_hub` 后端子域，形成工具仓库、输入工具链、自演进巡检和总览热力矩阵的最小闭环。

**Architecture:** 后端新增 `tool_hub` 文件型仓储子域，对外暴露 `overview / tools / match-runs / evolution-runs` 4 组 API；前端新增独立路由 `/xx-p4`，不混入当前主导航，采用独立页面壳层和页内工作区切换。页面默认展示驾驶舱总览，并在同页内切换到输入工具链、自演进巡检和工具仓库工作区。

**Tech Stack:** FastAPI, Pydantic, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

**2026-04-16 Correction:** 当前实现以更新后的 P4 设计为准，工具仓核心模型已从旧的 `category / stage / capability` 轴线纠偏为 `business domain / tool form / runtime platform / lifecycle stage`。

---

### Task 1: 锁定 `tool_hub` 后端契约与最小行为

**Files:**
- Create: `apps/api/tests/test_tool_hub_api.py`

- [ ] **Step 1: 写失败测试，覆盖工具仓库 CRUD 与总览接口**

```python
def test_tool_hub_overview_and_crud(tmp_path) -> None:
    app = create_app()
    service = ToolHubService(root=tmp_path, archive_service=ArchiveKnowledgeService(tmp_path), seed_demo_data=False)
    app.dependency_overrides[get_tool_hub_service] = lambda: service
    client = TestClient(app)

    create_payload = {
        "name": "流程验证器",
        "slug": "process-validator",
        "status": "active",
        "summary": "针对流程清单生成验证建议",
        "problem_statement": "降低流程建模前期人工比对成本",
        "primary_category_id": "application_modeling",
        "tags": ["stage:modeling", "capability:process-analysis", "input:process-list", "output:validation-report"],
        "applicable_stages": ["modeling"],
        "input_types": ["process_list"],
        "output_types": ["validation_report"],
        "supported_sources": ["manual_input"],
        "usage_notes": "用于流程梳理前的快速筛查",
        "keywords": ["流程", "验证"],
        "verification": {"status": "verified", "last_verified_result": "样例通过", "sample_case_ids": ["sample-1"]},
    }

    created = client.post("/api/tool-hub/tools", json=create_payload)
    assert created.status_code == 201
    tool_id = created.json()["tool_id"]

    overview = client.get("/api/tool-hub/overview")
    assert overview.status_code == 200
    assert overview.json()["metrics"]["tool_count"] == 1

    updated = client.put(
        f"/api/tool-hub/tools/{tool_id}",
        json={**create_payload, "summary": "针对流程清单输出结构化验证建议"},
    )
    assert updated.status_code == 200
    assert updated.json()["summary"] == "针对流程清单输出结构化验证建议"
```

- [ ] **Step 2: 跑后端单测确认先红**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
Expected: FAIL，提示 `tool_hub` 路由、依赖或模型不存在。

### Task 2: 实现 `tool_hub` 文件型仓储、匹配与巡检 API

**Files:**
- Create: `apps/api/app/tool_hub/models.py`
- Create: `apps/api/app/tool_hub/fixtures.py`
- Create: `apps/api/app/tool_hub/repository.py`
- Create: `apps/api/app/tool_hub/service.py`
- Create: `apps/api/app/api/routes/tool_hub.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_tool_hub_api.py`

- [ ] **Step 1: 定义 `tool_hub` 的 Pydantic 模型**

```python
class ToolDefinitionWrite(BaseModel):
    name: str
    slug: str
    status: Literal["draft", "active", "archived"] = "draft"
    summary: str = ""
    problem_statement: str = ""
    primary_category_id: str
    tags: list[str] = Field(default_factory=list)
    applicable_stages: list[str] = Field(default_factory=list)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    supported_sources: list[str] = Field(default_factory=list)
    usage_notes: str = ""
    keywords: list[str] = Field(default_factory=list)
    verification: ToolVerification = Field(default_factory=ToolVerification)
```

- [ ] **Step 2: 实现文件型仓储，按目录持久化工具与运行记录**

```python
class ToolHubRepository:
    def list_tools(self) -> list[ToolDefinition]:
        return sorted(self._read_models(self.tools_dir, ToolDefinition), key=lambda item: item.updated_at, reverse=True)

    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        self._write_json(self.tools_dir / f"{tool.tool_id}.json", tool.model_dump(mode="json"))
        return tool
```

- [ ] **Step 3: 在服务层实现总览、匹配与巡检**

```python
def run_match(self, request: ToolMatchRequest) -> ToolMatchRun:
    candidates = [self._score_tool(tool, request) for tool in self.list_tools() if tool.status == "active"]
    run = ToolMatchRun(run_id=f"match-{uuid4().hex[:12]}", request=request, candidates=sorted_candidates, ...)
    self.repository.save_match_run(run)
    return run
```

- [ ] **Step 4: 将 `tool_hub` 路由挂到 FastAPI 应用**

```python
app.include_router(tool_hub_router, prefix=settings.api_prefix)
```

- [ ] **Step 5: 重新运行后端单测确认转绿**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
Expected: PASS

### Task 3: 锁定 `/xx-p4` 独立页面路由与驾驶舱骨架

**Files:**
- Create: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: 写失败测试，覆盖独立路由与页内工作区切换**

```tsx
render(
  <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
    <App />
  </MemoryRouter>,
);

expect(await screen.findByText("XX-P4")).toBeInTheDocument();
expect(screen.getByText("工具中台 / Tool Hub")).toBeInTheDocument();
expect(screen.getByRole("tab", { name: "总览" })).toBeInTheDocument();

fireEvent.click(screen.getByRole("tab", { name: "输入工具链" }));
expect(await screen.findByText("输入场景")).toBeInTheDocument();
```

- [ ] **Step 2: 跑前端单测确认先红**

Run: `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx`
Expected: FAIL，提示 `/xx-p4` 路由或页面元素不存在。

### Task 4: 实现独立驾驶舱页面与 4 个工作区

**Files:**
- Create: `apps/web/src/pages/XXP4Page.tsx`
- Create: `apps/web/src/components/p4/P4Hero.tsx`
- Create: `apps/web/src/components/p4/P4MetricsPanel.tsx`
- Create: `apps/web/src/components/p4/P4CoverageMatrix.tsx`
- Create: `apps/web/src/components/p4/P4RunList.tsx`
- Create: `apps/web/src/components/p4/P4RiskSummary.tsx`
- Create: `apps/web/src/components/p4/P4InputChainWorkspace.tsx`
- Create: `apps/web/src/components/p4/P4EvolutionWorkspace.tsx`
- Create: `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- Create: `apps/web/src/components/p4/P4WorkspaceTabs.tsx`
- Create: `apps/web/src/lib/toolHub.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/App.tsx`
- Test: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: 在 `App.tsx` 中为 `/xx-p4` 提供独立壳层路由**

```tsx
if (location.pathname.startsWith("/xx-p4")) {
  return (
    <Routes>
      <Route path="/xx-p4" element={<XXP4Page />} />
    </Routes>
  );
}
```

- [ ] **Step 2: 实现深色英雄区、指标卡和热力矩阵组件**

```tsx
<section style={{ background: "linear-gradient(135deg, #081225 0%, #12356b 58%, #0f766e 100%)" }}>
  <P4Hero overview={overview} archiveName={activeArchive?.name} />
  <P4MetricsPanel metrics={overview.metrics} />
</section>
<P4CoverageMatrix matrix={overview.coverage_matrix} />
```

- [ ] **Step 3: 用页内标签承载 4 个工作区**

```tsx
<Tabs
  items={[
    { key: "overview", label: "总览", children: <OverviewPanels ... /> },
    { key: "input-chain", label: "输入工具链", children: <P4InputChainWorkspace ... /> },
    { key: "evolution", label: "自演进巡检", children: <P4EvolutionWorkspace ... /> },
    { key: "registry", label: "工具仓库", children: <P4RegistryWorkspace ... /> },
  ]}
/>
```

- [ ] **Step 4: 接入工具仓库 CRUD、匹配运行和巡检运行**

```tsx
const overviewQuery = useQuery({ queryKey: ["tool-hub", "overview"], queryFn: getToolHubOverview });
const [matchRun, setMatchRun] = useState<ToolMatchRun | null>(null);
const [evolutionRun, setEvolutionRun] = useState<EvolutionRun | null>(null);
```

- [ ] **Step 5: 重新运行前端单测确认转绿**

Run: `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx`
Expected: PASS

### Task 5: 跑面向 P4 的回归验证

**Files:**
- Verify: `apps/api/tests/test_tool_hub_api.py`
- Verify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: 跑后端工具中台单测**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py -q`
Expected: PASS

- [ ] **Step 2: 跑前端独立页面单测**

Run: `corepack pnpm --dir apps/web test -- XXP4Page.test.tsx`
Expected: PASS

- [ ] **Step 3: 跑相关前端路由回归**

Run: `corepack pnpm --dir apps/web test -- AppRoutes.test.tsx`
Expected: PASS，证明新增独立路由没有破坏现有主壳层路由。
