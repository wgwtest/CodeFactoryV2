# XX-P3 Software Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P3` 落地独立的 `XX-P3` 软件设计系统页面与 `design_system` 后端子域，形成“需求快照输入 -> 模块设计 -> 软件设计说明校核 -> 模块级工具化描述导出”的最小闭环。

**Architecture:** 后端新增 `design_system` 文件型版本化子域，对外暴露 `design-runs / reviews / exports / overview` 4 组接口；前端新增独立路由 `/xx-p3`，不并入当前主导航，采用独立页面壳层和页内工作区切换。页面默认展示设计总览，并在同页内切换到模块设计、设计说明和工具化描述工作区。

**Tech Stack:** FastAPI, Pydantic, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

### Task 1: 锁定 `design_system` 后端契约与最小行为

**Files:**
- Create: `apps/api/tests/test_design_system_api.py`

- [ ] **Step 1: 写失败测试，覆盖设计任务创建、评审冻结和导出接口**

```python
def test_design_system_run_review_and_export(tmp_path) -> None:
    app = create_app()
    service = DesignSystemService(root=tmp_path, seed_demo_data=False)
    app.dependency_overrides[get_design_system_service] = lambda: service
    client = TestClient(app)

    run_payload = {
        "requirement_snapshot_id": "arm_snapshot_demo",
        "application_name": "空域协同规划应用",
        "problem_statement": "提升规划任务的跨角色协同效率",
    }

    created = client.post("/api/design-system/design-runs", json=run_payload)
    assert created.status_code == 201
    design_id = created.json()["design_id"]

    overview = client.get("/api/design-system/overview")
    assert overview.status_code == 200
    assert overview.json()["metrics"]["design_count"] == 1

    frozen = client.post(f"/api/design-system/design-runs/{design_id}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"

    exported = client.post(f"/api/design-system/design-runs/{design_id}/exports")
    assert exported.status_code == 201
    assert exported.json()["design_id"] == design_id
```

- [ ] **Step 2: 跑后端单测确认先红**

Run: `uv run pytest apps/api/tests/test_design_system_api.py -q`
Expected: FAIL，提示 `design_system` 路由、依赖或模型不存在。

### Task 2: 实现 `design_system` 后端子域

**Files:**
- Create: `apps/api/app/design_system/__init__.py`
- Create: `apps/api/app/design_system/models.py`
- Create: `apps/api/app/design_system/fixtures.py`
- Create: `apps/api/app/design_system/repository.py`
- Create: `apps/api/app/design_system/service.py`
- Create: `apps/api/app/api/routes/design_system.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_design_system_api.py`

- [ ] **Step 1: 定义 `SoftwareDesignModel`、评审和导出对象**

```python
class SoftwareDesignRunCreate(BaseModel):
    requirement_snapshot_id: str
    application_name: str
    problem_statement: str = ""


class SoftwareDesignModel(BaseModel):
    design_id: str
    requirement_snapshot_id: str
    application_name: str
    status: Literal["draft", "in_review", "frozen"] = "draft"
    scenes: list[DesignScene] = Field(default_factory=list)
    modules: list[DesignModule] = Field(default_factory=list)
    review: DesignReview = Field(default_factory=DesignReview)
```

- [ ] **Step 2: 实现文件型仓储，保存设计任务、冻结快照和导出包**

```python
class DesignSystemRepository:
    def save_design(self, design: SoftwareDesignModel) -> SoftwareDesignModel:
        self._write_json(self.designs_dir / f"{design.design_id}.json", design.model_dump(mode="json"))
        return design

    def save_export_bundle(self, bundle: ModuleToolDescriptorBundle) -> ModuleToolDescriptorBundle:
        self._write_json(self.exports_dir / f"{bundle.bundle_id}.json", bundle.model_dump(mode="json"))
        return bundle
```

- [ ] **Step 3: 在服务层实现模块生成、冻结和导出**

```python
def create_design_run(self, payload: SoftwareDesignRunCreate) -> SoftwareDesignModel:
    design = self._build_design_from_requirement(payload)
    return self.repository.save_design(design)


def freeze_design(self, design_id: str) -> SoftwareDesignModel:
    design = self.repository.get_design(design_id)
    frozen = design.model_copy(update={"status": "frozen"})
    return self.repository.save_design(frozen)
```

- [ ] **Step 4: 将 `design_system` 路由挂到 FastAPI 应用**

```python
app.include_router(design_system_router, prefix=settings.api_prefix)
```

- [ ] **Step 5: 重新运行后端单测确认转绿**

Run: `uv run pytest apps/api/tests/test_design_system_api.py -q`
Expected: PASS

### Task 3: 锁定 `/xx-p3` 独立页面路由与驾驶舱骨架

**Files:**
- Create: `apps/web/src/test/XXP3Page.test.tsx`

- [ ] **Step 1: 写失败测试，覆盖独立路由与页内工作区切换**

```tsx
render(
  <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
    <App />
  </MemoryRouter>,
);

expect(await screen.findByText("XX-P3")).toBeInTheDocument();
expect(screen.getByText("软件设计系统 / Software Design System")).toBeInTheDocument();
expect(screen.getByRole("tab", { name: "模块设计" })).toBeInTheDocument();

fireEvent.click(screen.getByRole("tab", { name: "工具化描述" }));
expect(await screen.findByText("导出描述包")).toBeInTheDocument();
```

- [ ] **Step 2: 跑前端单测确认先红**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: FAIL，提示 `/xx-p3` 路由或页面元素不存在。

### Task 4: 实现独立驾驶舱页面与 4 个工作区

**Files:**
- Create: `apps/web/src/pages/XXP3Page.tsx`
- Create: `apps/web/src/components/p3/P3Hero.tsx`
- Create: `apps/web/src/components/p3/P3MetricsPanel.tsx`
- Create: `apps/web/src/components/p3/P3ModuleWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3SpecificationWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3DescriptorWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3RiskSummary.tsx`
- Create: `apps/web/src/components/p3/P3WorkspaceTabs.tsx`
- Create: `apps/web/src/lib/designSystem.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/App.tsx`
- Test: `apps/web/src/test/XXP3Page.test.tsx`

- [ ] **Step 1: 在 `App.tsx` 中为 `/xx-p3` 提供独立壳层路由**

```tsx
if (location.pathname.startsWith("/xx-p3")) {
  return (
    <Routes>
      <Route path="/xx-p3" element={<XXP3Page />} />
    </Routes>
  );
}
```

- [ ] **Step 2: 实现英雄区、指标卡和风险摘要组件**

```tsx
<section style={{ background: "linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0f766e 100%)" }}>
  <P3Hero overview={overview} />
  <P3MetricsPanel metrics={overview.metrics} />
</section>
<P3RiskSummary risks={overview.risks} />
```

- [ ] **Step 3: 用页内标签承载 4 个工作区**

```tsx
<Tabs
  items={[
    { key: "overview", label: "总览", children: <OverviewPanels overview={overview} /> },
    { key: "modules", label: "模块设计", children: <P3ModuleWorkspace design={selectedDesign} /> },
    { key: "specification", label: "设计说明", children: <P3SpecificationWorkspace design={selectedDesign} /> },
    { key: "descriptors", label: "工具化描述", children: <P3DescriptorWorkspace design={selectedDesign} /> },
  ]}
/>
```

- [ ] **Step 4: 接入设计任务、冻结和导出 API**

```tsx
const overviewQuery = useQuery({ queryKey: ["design-system", "overview"], queryFn: getDesignSystemOverview });
const [selectedDesignId, setSelectedDesignId] = useState<string | null>(null);
const freezeMutation = useMutation({ mutationFn: freezeDesignRun });
const exportMutation = useMutation({ mutationFn: exportDescriptorBundle });
```

- [ ] **Step 5: 重新运行前端单测确认转绿**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: PASS

### Task 5: 跑面向 P3 的回归验证

**Files:**
- Verify: `apps/api/tests/test_design_system_api.py`
- Verify: `apps/web/src/test/XXP3Page.test.tsx`

- [ ] **Step 1: 跑后端软件设计系统单测**

Run: `uv run pytest apps/api/tests/test_design_system_api.py -q`
Expected: PASS

- [ ] **Step 2: 跑前端独立页面单测**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: PASS

- [ ] **Step 3: 跑相关前端路由回归**

Run: `corepack pnpm --dir apps/web test -- AppRoutes.test.tsx`
Expected: PASS，证明新增独立路由没有破坏现有主壳层路由。
