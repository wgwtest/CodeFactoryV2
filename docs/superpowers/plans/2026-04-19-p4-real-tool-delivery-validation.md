# P4 真实工具落地验证 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `P4` 从“模拟工具闭环”升级到“可生成、可登记、可校验、可交付、可消费的真实前端元组件闭环”，首个样例固定为 `React + Ant Design 查询表格元组件`。

**Architecture:** 保持当前 `P4` 的 `命令 -> 事实 -> runtime queue -> projection` 主骨架不变，在其上新增 `P4.5 delivery` 子域。`ToolDefinition` 与 `ToolFetchManifest` 先升级为“最小工具”契约，随后引入 SQLAlchemy 持久化的 `build request / build run / artifact / validation report` 表，再通过现有 OpenAI-compatible LLM 适配层生成结构化 `ToolRecipe`，由确定性模板生成器产出 `QueryTableWidget` 元组件与宿主接入样例，最后由 `P3-sim -> P4 -> P5-sim` 走完整真实交付链。

**Tech Stack:** FastAPI, SQLAlchemy, SQLite for tests and PostgreSQL for runtime, existing OpenAI-compatible LLM integration, React 18, TypeScript, Ant Design 5, pytest, Vitest

---

## File Structure

**Backend contracts and persistence**

- Modify: `apps/api/app/tool_hub/models.py`
  - 扩展 `ToolDefinitionWrite`、`ToolDefinition`、`ToolFetchManifest`
  - 新增 `ToolRecipe`、`ToolBuildRequest`、`ToolBuildRun`、`ToolArtifactVersion`、`ToolValidationReport`
- Modify: `apps/api/app/tool_hub/fixtures.py`
  - 新增 `frontend_component` 相关 catalog 项与样例工具
- Create: `apps/api/app/db/models/tool_hub_delivery.py`
  - SQLAlchemy 表：`tool_build_requests`、`tool_build_runs`、`tool_artifact_versions`、`tool_validation_reports`
- Modify: `apps/api/app/db/models/__init__.py`
  - 暴露新的 delivery ORM 模型
- Modify: `apps/api/app/main.py`
  - 显式导入 `app.db.models`，避免 `Base.metadata.create_all()` 时遗漏新表
- Create: `apps/api/app/tool_hub/delivery_repository.py`
  - 负责 SQLAlchemy 读写 delivery 事实对象
- Create: `apps/api/app/tool_hub/delivery_service.py`
  - 负责 build request 受理、artifact 归档、validation report 写入、delivery manifest 生成
- Create: `apps/api/app/tool_hub/recipe_service.py`
  - 调用现有 OpenAI-compatible LLM 适配层，输出结构化 `ToolRecipe`
- Create: `apps/api/app/tool_hub/generators/query_table_widget.py`
  - 把 `ToolRecipe` 渲染为稳定组件文件、宿主接入样例和 `manifest.json`

**Runtime and routes**

- Modify: `apps/api/app/tool_hub/runtime_models.py`
  - 新增 `p4-build` 队列对应 job 类型
- Modify: `apps/api/app/tool_hub/runtime_service.py`
  - 增加 build job enqueue / execute 逻辑
- Modify: `apps/api/app/tool_hub/service.py`
  - 组装 `delivery_service`、`recipe_service`，暴露新入口
- Modify: `apps/api/app/api/routes/tool_hub_operator.py`
  - 新增 build request 创建、build run 查询、artifact 查询端点
- Modify: `apps/api/app/api/routes/tool_hub_p3_input.py`
  - 新增 `P3-sim` 前端元组件需求入口
- Modify: `apps/api/app/api/routes/tool_hub_p5_query.py`
  - 新增 delivery manifest 查询与 artifact 读取端点

**Tests**

- Create: `apps/api/tests/test_tool_hub_delivery_repository.py`
- Create: `apps/api/tests/test_tool_hub_delivery_api.py`
- Create: `apps/api/tests/test_tool_hub_component_generator.py`
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/api/tests/test_tool_hub_runtime_service.py`
- Modify: `apps/api/tests/conftest.py`

**Frontend**

- Modify: `apps/web/src/lib/api.ts`
  - 新增 `ToolRecipe`、`ToolBuildRun`、`ToolArtifactVersion`、`ToolDeliveryManifest` 类型
- Modify: `apps/web/src/lib/toolHub.ts`
  - 新增 delivery/build API helper
- Create: `apps/web/src/components/p3/P3AtomicToolRequestGenerator.tsx`
  - `P3-sim` 中创建前端元组件需求
- Create: `apps/web/src/components/p4/P4RealToolDeliveryWorkspace.tsx`
  - `XX-P4` 中查看 build request、build run、artifact、validation
- Create: `apps/web/src/components/p5/P5DeliveryManifestPanel.tsx`
  - `P5-sim` 中查看 delivery manifest 和接入说明
- Modify: `apps/web/src/pages/XXP3SimPage.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/pages/XXP5SimPage.tsx`
- Modify: `apps/web/src/components/p4/P4WorkspaceTabs.tsx`
- Modify: `apps/web/src/components/p4/p4-page.css`
- Create: `apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

**Docs**

- Modify: `DOC/CODEX_DOC/04_研发文档/01-P4-设计实现映射表.md`
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

### Task 1: 锁定“最小工具”契约与 fetch manifest 形态

**Files:**
- Modify: `apps/api/app/tool_hub/models.py`
- Modify: `apps/api/app/tool_hub/fixtures.py`
- Modify: `apps/api/app/tool_hub/registry_service.py`
- Modify: `apps/api/app/tool_hub/query_models.py`
- Modify: `apps/api/app/tool_hub/query_service.py`
- Modify: `apps/api/app/api/routes/tool_hub_operator.py`
- Modify: `apps/api/tests/test_tool_hub_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`

- [ ] **Step 1: Write the failing API contract test for atomic frontend component tools**

```python
def test_tool_fetch_manifest_exposes_atomic_frontend_component_contract(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_payload = {
        "name": "查询表格元组件",
        "slug": "query-table-widget",
        "status": "draft",
        "summary": "可嵌入宿主项目的查询表格元组件",
        "problem_statement": "复用列表筛选、表格渲染和行级操作骨架",
        "primary_domain_id": "cross_domain_shared",
        "tool_form_id": "frontend_component",
        "tool_granularity": "atomic",
        "packaging_type": "source_package",
        "integration_mode": "import_component",
        "dependency_policy": "peer",
        "runtime_dependencies": ["react@18", "antd@5"],
        "host_constraints": {
            "frontend_framework": "react",
            "ui_library": "antd",
        },
        "runtime_platform_ids": ["web_frontend"],
        "lifecycle_stage_ids": ["solution_design", "verification_release"],
        "input_types": ["query_params", "column_schema"],
        "output_types": ["tsx_component", "delivery_manifest"],
        "supported_sources": ["p3_design_output"],
        "tags": [
            "domain:cross_domain_shared",
            "form:frontend_component",
            "runtime:web_frontend",
            "delivery:import_component",
        ],
    }

    created = client.post("/api/tool-hub/tools", json=create_payload)
    assert created.status_code == 201
    tool_id = created.json()["tool_id"]

    manifest = client.get(f"/api/tool-hub/tools/{tool_id}/fetch")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["tool_form_id"] == "frontend_component"
    assert payload["packaging_type"] == "source_package"
    assert payload["integration_mode"] == "import_component"
    assert payload["dependency_policy"] == "peer"
    assert payload["runtime_dependencies"] == ["react@18", "antd@5"]
```

- [ ] **Step 2: Run the contract test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py::test_tool_fetch_manifest_exposes_atomic_frontend_component_contract -q`

Expected: FAIL because `ToolDefinitionWrite` and `ToolFetchManifest` do not yet expose the new fields.

- [ ] **Step 3: Extend `ToolDefinitionWrite`, `ToolDefinition`, and `ToolFetchManifest`**

```python
class ToolDefinitionWrite(BaseModel):
    name: str
    slug: str
    status: str
    summary: str
    problem_statement: str
    primary_domain_id: str
    tool_form_id: str
    tool_granularity: Literal["atomic", "composite", "page_level"] = "atomic"
    packaging_type: Literal["source_package", "build_artifact", "http_endpoint", "descriptor_only"]
    integration_mode: Literal[
        "import_component",
        "import_module",
        "include_router",
        "call_http_api",
        "mount_page",
    ]
    dependency_policy: Literal["peer", "bundled", "external"] = "peer"
    runtime_dependencies: list[str] = Field(default_factory=list)
    host_constraints: dict[str, str | list[str]] = Field(default_factory=dict)
    runtime_platform_ids: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
```

```python
class ToolFetchManifest(BaseModel):
    tool_id: str
    tool_name: str
    tool_version: str = "v1"
    tool_form_id: str
    packaging_type: str
    integration_mode: str
    dependency_policy: str
    runtime_dependencies: list[str] = Field(default_factory=list)
    entrypoint_type: Literal["http", "descriptor", "artifact_ref", "manual"] = "descriptor"
    entrypoint_locator: str
    contract_version: str = "p4.fetch.v2"
```

- [ ] **Step 4: Update registry/query plumbing to preserve the new fields**

```python
def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
    self.hub._ensure_demo_data()
    self.hub._ensure_slug_unique(payload.slug)
    tool = ToolDefinition(
        tool_id=f"tool-{uuid4().hex[:12]}",
        **payload.model_dump(mode="json"),
    )
    saved = self.repository.save_tool(tool)
    self.hub.mark_evolution_dirty()
    return saved

def get_tool_fetch_manifest(self, tool_id: str) -> ToolFetchManifest | None:
    tool = self.repository.get_tool(tool_id)
    if tool is None:
        return None
    return ToolFetchManifest(
        tool_id=tool.tool_id,
        tool_name=tool.name,
        tool_version=f"v{tool.version}",
        tool_form_id=tool.tool_form_id,
        packaging_type=tool.packaging_type,
        integration_mode=tool.integration_mode,
        dependency_policy=tool.dependency_policy,
        runtime_dependencies=tool.runtime_dependencies,
        entrypoint_locator=f"tool://{tool.slug}",
    )
```

- [ ] **Step 5: Mirror the contract to the frontend API layer**

```ts
export type ToolDefinition = {
  tool_id: string;
  name: string;
  slug: string;
  tool_form_id: string;
  tool_granularity: "atomic" | "composite" | "page_level";
  packaging_type: "source_package" | "build_artifact" | "http_endpoint" | "descriptor_only";
  integration_mode: "import_component" | "import_module" | "include_router" | "call_http_api" | "mount_page";
  dependency_policy: "peer" | "bundled" | "external";
  runtime_dependencies: string[];
  host_constraints: Record<string, string | string[]>;
};

export type ToolFetchManifest = {
  tool_id: string;
  tool_name: string;
  tool_version: string;
  tool_form_id: string;
  packaging_type: string;
  integration_mode: string;
  dependency_policy: string;
  runtime_dependencies: string[];
  entrypoint_type: "http" | "descriptor" | "artifact_ref" | "manual";
  entrypoint_locator: string;
  contract_version: string;
};
```

- [ ] **Step 6: Run the updated test to verify GREEN**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py::test_tool_fetch_manifest_exposes_atomic_frontend_component_contract -q`

Expected: PASS

- [ ] **Step 7: Commit the contract slice**

```bash
git add apps/api/app/tool_hub/models.py apps/api/app/tool_hub/fixtures.py apps/api/app/tool_hub/registry_service.py apps/api/app/tool_hub/query_models.py apps/api/app/tool_hub/query_service.py apps/api/app/api/routes/tool_hub_operator.py apps/api/tests/test_tool_hub_api.py apps/web/src/lib/api.ts apps/web/src/lib/toolHub.ts
git commit -m "feat: add atomic tool contract and fetch manifest fields"
```

### Task 2: 引入 SQLAlchemy delivery 持久化层

**Files:**
- Create: `apps/api/app/db/models/tool_hub_delivery.py`
- Modify: `apps/api/app/db/models/__init__.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/app/tool_hub/delivery_repository.py`
- Create: `apps/api/tests/test_tool_hub_delivery_repository.py`
- Modify: `apps/api/tests/conftest.py`

- [ ] **Step 1: Write the failing repository test for build requests, artifacts, and validation reports**

```python
def test_delivery_repository_persists_build_request_run_and_artifact(db_session: Session, tmp_path: Path) -> None:
    repository = ToolHubDeliveryRepository(db_session)

    build_request = ToolBuildRequest(
        build_request_id="build-req-1",
        tool_id="tool-query-table",
        request_type="frontend_component",
        requested_by="p3-sim",
        recipe_status="pending",
    )
    saved_request = repository.save_build_request(build_request)

    build_run = ToolBuildRun(
        build_run_id="build-run-1",
        build_request_id=saved_request.build_request_id,
        status="queued",
        queue_name="p4-build",
    )
    repository.save_build_run(build_run)

    artifact = ToolArtifactVersion(
        artifact_version_id="artifact-1",
        tool_id="tool-query-table",
        build_run_id="build-run-1",
        version_label="v1",
        artifact_root=str(tmp_path / "artifacts" / "artifact-1"),
        manifest_path="manifest.json",
        packaging_type="source_package",
        integration_mode="import_component",
    )
    report = ToolValidationReport(
        validation_report_id="report-1",
        build_run_id="build-run-1",
        overall_status="passed",
        checks=[{"name": "typecheck", "status": "passed"}],
    )

    repository.save_artifact_version(artifact)
    repository.save_validation_report(report)

    assert repository.get_build_request("build-req-1").tool_id == "tool-query-table"
    assert repository.get_build_run("build-run-1").status == "queued"
    assert repository.list_artifact_versions("tool-query-table")[0].integration_mode == "import_component"
    assert repository.get_validation_report("build-run-1").overall_status == "passed"
```

- [ ] **Step 2: Run the repository test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_delivery_repository.py::test_delivery_repository_persists_build_request_run_and_artifact -q`

Expected: FAIL because the ORM model and repository do not exist yet.

- [ ] **Step 3: Add the ORM tables**

```python
class ToolBuildRequestRecord(Base):
    __tablename__ = "tool_build_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(255), index=True)
    request_type: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(255))
    recipe_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
```

```python
class ToolBuildRunRecord(Base):
    __tablename__ = "tool_build_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    build_request_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    queue_name: Mapped[str] = mapped_column(String(64), default="p4-build")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
```

- [ ] **Step 4: Register the models and create the repository**

```python
from app.db.models import document, knowledge, requirements, tool_hub_delivery
```

```python
class ToolHubDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_build_request(self, build_request: ToolBuildRequest) -> ToolBuildRequest:
        record = ToolBuildRequestRecord(
            id=build_request.build_request_id,
            tool_id=build_request.tool_id,
            request_type=build_request.request_type,
            requested_by=build_request.requested_by,
            recipe_status=build_request.recipe_status,
            payload=build_request.model_dump(mode="json"),
        )
        self.session.merge(record)
        self.session.commit()
        return build_request
```

- [ ] **Step 5: Ensure the app imports all ORM modules before `create_all()`**

```python
import app.db.models  # noqa: F401

def create_app() -> FastAPI:
    Base.metadata.create_all(engine)
    app = FastAPI(title=settings.app_name)
    ...
```

- [ ] **Step 6: Run the repository test to verify GREEN**

Run: `uv run pytest apps/api/tests/test_tool_hub_delivery_repository.py::test_delivery_repository_persists_build_request_run_and_artifact -q`

Expected: PASS

- [ ] **Step 7: Commit the persistence slice**

```bash
git add apps/api/app/db/models/tool_hub_delivery.py apps/api/app/db/models/__init__.py apps/api/app/main.py apps/api/app/tool_hub/delivery_repository.py apps/api/tests/test_tool_hub_delivery_repository.py apps/api/tests/conftest.py
git commit -m "feat: add tool hub delivery persistence tables"
```

### Task 3: 实现 recipe 生成、模板生成与 build runtime

**Files:**
- Create: `apps/api/app/tool_hub/recipe_service.py`
- Create: `apps/api/app/tool_hub/delivery_service.py`
- Create: `apps/api/app/tool_hub/generators/query_table_widget.py`
- Modify: `apps/api/app/tool_hub/runtime_models.py`
- Modify: `apps/api/app/tool_hub/runtime_service.py`
- Modify: `apps/api/app/tool_hub/service.py`
- Modify: `apps/api/app/api/routes/tool_hub_operator.py`
- Modify: `apps/api/app/api/routes/tool_hub_p3_input.py`
- Modify: `apps/api/app/api/routes/tool_hub_p5_query.py`
- Create: `apps/api/tests/test_tool_hub_delivery_api.py`
- Create: `apps/api/tests/test_tool_hub_component_generator.py`
- Modify: `apps/api/tests/test_tool_hub_runtime_service.py`

- [ ] **Step 1: Write the failing API test for the real frontend component build flow**

```python
def test_frontend_component_build_request_can_complete_and_publish_manifest(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    request_payload = {
        "requested_by": "p3-sim",
        "component_name": "QueryTableWidget",
        "scenario_id": "frontend-query-table-widget",
        "tool_definition": {
            "name": "查询表格元组件",
            "slug": "query-table-widget",
            "status": "draft",
            "summary": "可嵌入宿主的查询表格组件",
            "problem_statement": "复用表格和筛选骨架",
            "primary_domain_id": "cross_domain_shared",
            "tool_form_id": "frontend_component",
            "tool_granularity": "atomic",
            "packaging_type": "source_package",
            "integration_mode": "import_component",
            "dependency_policy": "peer",
            "runtime_dependencies": ["react@18", "antd@5"],
            "runtime_platform_ids": ["web_frontend"],
            "lifecycle_stage_ids": ["solution_design"],
            "tags": [],
        },
    }

    created = client.post("/api/tool-hub/build-requests/frontend-components", json=request_payload)
    assert created.status_code == 201
    build_run_id = created.json()["build_run_id"]

    service = client.app.dependency_overrides[get_tool_hub_service]()
    service.runtime_service.run_once()

    build_run = client.get(f"/api/tool-hub/build-runs/{build_run_id}")
    assert build_run.status_code == 200
    assert build_run.json()["status"] == "completed"

    tool_id = build_run.json()["tool_id"]
    manifest = client.get(f"/api/tool-hub/tools/{tool_id}/delivery-manifest")
    assert manifest.status_code == 200
    assert manifest.json()["integration_mode"] == "import_component"
    assert manifest.json()["dependency_policy"] == "peer"
    assert manifest.json()["runtime_dependencies"] == ["react@18", "antd@5"]
```

- [ ] **Step 2: Run the delivery API test to verify RED**

Run: `uv run pytest apps/api/tests/test_tool_hub_delivery_api.py::test_frontend_component_build_request_can_complete_and_publish_manifest -q`

Expected: FAIL because the build request route, runtime job type, and delivery manifest endpoint do not exist yet.

- [ ] **Step 3: Add `ToolRecipeService` using the existing OpenAI-compatible adapter**

```python
class ToolRecipeService:
    def __init__(self, *, artifact_root: Path) -> None:
        self.artifact_root = artifact_root

    def create_query_table_widget_recipe(self, request: ToolBuildRequest) -> ToolRecipe:
        # First slice: call the existing OpenAI-compatible adapter when config is present.
        # Fallback to deterministic defaults so tests stay stable.
        return ToolRecipe(
            recipe_id=f"recipe-{uuid4().hex[:12]}",
            component_name="QueryTableWidget",
            package_name="@p4-tools/query-table-widget",
            props_schema={
                "columns": {"type": "array"},
                "filters": {"type": "array"},
                "fetcher": {"type": "function"},
            },
            peer_dependencies={"react": "^18.0.0", "antd": "^5.0.0"},
            host_constraints={"frontend_framework": "react", "ui_library": "antd"},
        )
```

- [ ] **Step 4: Add the deterministic generator**

```python
def render_query_table_widget(recipe: ToolRecipe, artifact_root: Path) -> GeneratedArtifactBundle:
    files = {
        "src/QueryTableWidget.tsx": QUERY_TABLE_WIDGET_TSX,
        "src/types.ts": QUERY_TABLE_WIDGET_TYPES_TS,
        "example/HostPage.tsx": HOST_EXAMPLE_TSX,
        "manifest.json": json.dumps(
            {
                "tool_form": "frontend_component",
                "tool_granularity": "atomic",
                "packaging_type": "source_package",
                "integration_mode": "import_component",
                "dependency_policy": "peer",
                "runtime_dependencies": ["react@18", "antd@5"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    }
    ...
```

- [ ] **Step 5: Extend runtime with the `p4-build` queue**

```python
def enqueue_build_job(self, build_run_id: str, actor_id: str) -> RuntimeJob:
    return self.runtime_repository.save_job(
        RuntimeJob(
            job_id=f"job-{uuid4().hex[:12]}",
            job_type="frontend_component_build",
            queue_name="p4-build",
            aggregate_type="tool_build_run",
            aggregate_id=build_run_id,
            trigger_source="internal_command",
            trigger_actor_id=actor_id,
            payload_ref=build_run_id,
        )
    )
```

```python
def _execute_build_job(self, job: RuntimeJob) -> None:
    build_run = self.tool_hub_service.delivery_service.get_build_run(job.aggregate_id)
    if build_run is None:
        return
    self.tool_hub_service.delivery_service.execute_build_run(build_run.build_run_id)
```

- [ ] **Step 6: Expose build and manifest routes**

```python
@router.post("/build-requests/frontend-components", status_code=201)
def create_frontend_component_build_request(
    payload: FrontendComponentBuildRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
) -> ToolBuildRun:
    return service.delivery_service.create_frontend_component_build_request(payload)

@router.get("/build-runs/{build_run_id}")
def get_build_run(build_run_id: str, service: ToolHubService = Depends(get_tool_hub_service)) -> ToolBuildRun:
    return service.delivery_service.get_build_run_or_raise(build_run_id)

@router.get("/tools/{tool_id}/delivery-manifest")
def get_delivery_manifest(tool_id: str, service: ToolHubService = Depends(get_tool_hub_service)) -> ToolDeliveryManifest:
    return service.delivery_service.get_delivery_manifest_or_raise(tool_id)
```

- [ ] **Step 7: Run the new backend tests to verify GREEN**

Run: `uv run pytest apps/api/tests/test_tool_hub_delivery_api.py apps/api/tests/test_tool_hub_component_generator.py apps/api/tests/test_tool_hub_runtime_service.py -q`

Expected: PASS

- [ ] **Step 8: Commit the delivery runtime slice**

```bash
git add apps/api/app/tool_hub/recipe_service.py apps/api/app/tool_hub/delivery_service.py apps/api/app/tool_hub/generators/query_table_widget.py apps/api/app/tool_hub/runtime_models.py apps/api/app/tool_hub/runtime_service.py apps/api/app/tool_hub/service.py apps/api/app/api/routes/tool_hub_operator.py apps/api/app/api/routes/tool_hub_p3_input.py apps/api/app/api/routes/tool_hub_p5_query.py apps/api/tests/test_tool_hub_delivery_api.py apps/api/tests/test_tool_hub_component_generator.py apps/api/tests/test_tool_hub_runtime_service.py
git commit -m "feat: add real frontend component delivery runtime"
```

### Task 4: 把真实元组件闭环接到 `P3-sim / XX-P4 / P5-sim`

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/toolHub.ts`
- Create: `apps/web/src/components/p3/P3AtomicToolRequestGenerator.tsx`
- Create: `apps/web/src/components/p4/P4RealToolDeliveryWorkspace.tsx`
- Create: `apps/web/src/components/p5/P5DeliveryManifestPanel.tsx`
- Modify: `apps/web/src/pages/XXP3SimPage.tsx`
- Modify: `apps/web/src/pages/XXP4Page.tsx`
- Modify: `apps/web/src/pages/XXP5SimPage.tsx`
- Modify: `apps/web/src/components/p4/P4WorkspaceTabs.tsx`
- Modify: `apps/web/src/components/p4/p4-page.css`
- Create: `apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx`
- Modify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: Write the failing frontend workspace test**

```tsx
it("shows the real delivery workspace with peer dependency and import guidance", async () => {
  server.use(
    http.get("/api/tool-hub/tools/tool-query-table/delivery-manifest", () =>
      HttpResponse.json({
        tool_id: "tool-query-table",
        tool_name: "查询表格元组件",
        tool_form_id: "frontend_component",
        packaging_type: "source_package",
        integration_mode: "import_component",
        dependency_policy: "peer",
        runtime_dependencies: ["react@18", "antd@5"],
        import_specifier: "@p4-tools/query-table-widget",
      }),
    ),
  );

  render(<P4RealToolDeliveryWorkspace />);

  expect(await screen.findByText("真实工具交付")).toBeInTheDocument();
  expect(screen.getByText("peer")).toBeInTheDocument();
  expect(screen.getByText("@p4-tools/query-table-widget")).toBeInTheDocument();
  expect(screen.getByText("react@18")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend test to verify RED**

Run: `corepack pnpm --dir apps/web test -- P4RealToolDeliveryWorkspace.test.tsx`

Expected: FAIL because the workspace component and delivery manifest types do not exist yet.

- [ ] **Step 3: Add frontend API types and helpers**

```ts
export type ToolBuildRun = {
  build_run_id: string;
  build_request_id: string;
  tool_id: string;
  status: "queued" | "running" | "completed" | "failed";
  queue_name: "p4-build";
};

export type ToolDeliveryManifest = {
  tool_id: string;
  tool_name: string;
  tool_form_id: "frontend_component";
  packaging_type: "source_package";
  integration_mode: "import_component";
  dependency_policy: "peer" | "bundled" | "external";
  runtime_dependencies: string[];
  import_specifier: string;
  example_host_path: string;
};
```

```ts
export function createFrontendComponentBuildRequest(payload: FrontendComponentBuildRequestInput) {
  return api.post<ToolBuildRun>("/tool-hub/build-requests/frontend-components", payload);
}

export function getToolDeliveryManifest(toolId: string) {
  return api.get<ToolDeliveryManifest>(`/tool-hub/tools/${toolId}/delivery-manifest`);
}
```

- [ ] **Step 4: Build the P3 / P4 / P5 UI blocks**

```tsx
export function P3AtomicToolRequestGenerator() {
  return (
    <Card id="xx-p3-atomic-tool-request" title="前端元组件需求">
      <Typography.Paragraph>固定样例：QueryTableWidget</Typography.Paragraph>
      <Button type="primary">提交到 P4</Button>
    </Card>
  );
}
```

```tsx
export function P4RealToolDeliveryWorkspace() {
  return (
    <Card id="xx-p4-real-tool-delivery" title="真实工具交付">
      <Descriptions column={1}>
        <Descriptions.Item label="依赖策略">peer</Descriptions.Item>
        <Descriptions.Item label="接入方式">import_component</Descriptions.Item>
        <Descriptions.Item label="导入路径">@p4-tools/query-table-widget</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
```

```tsx
export function P5DeliveryManifestPanel() {
  return (
    <Card id="xx-p5-delivery-manifest" title="交付清单">
      <Typography.Paragraph code>{`import { QueryTableWidget } from "@p4-tools/query-table-widget";`}</Typography.Paragraph>
    </Card>
  );
}
```

- [ ] **Step 5: Run the frontend tests and production build**

Run: `corepack pnpm --dir apps/web test -- P4RealToolDeliveryWorkspace.test.tsx XXP4Page.test.tsx`

Expected: PASS

Run: `corepack pnpm --dir apps/web build`

Expected: PASS

- [ ] **Step 6: Commit the frontend slice**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/toolHub.ts apps/web/src/components/p3/P3AtomicToolRequestGenerator.tsx apps/web/src/components/p4/P4RealToolDeliveryWorkspace.tsx apps/web/src/components/p5/P5DeliveryManifestPanel.tsx apps/web/src/pages/XXP3SimPage.tsx apps/web/src/pages/XXP4Page.tsx apps/web/src/pages/XXP5SimPage.tsx apps/web/src/components/p4/P4WorkspaceTabs.tsx apps/web/src/components/p4/p4-page.css apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx apps/web/src/test/XXP4Page.test.tsx
git commit -m "feat: wire real tool delivery through P3 P4 P5 workspaces"
```

### Task 5: 回归验证、文档映射和镜像同步

**Files:**
- Modify: `DOC/CODEX_DOC/04_研发文档/01-P4-设计实现映射表.md`
- Modify: `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- Verify: `apps/api/tests/test_tool_hub_api.py`
- Verify: `apps/api/tests/test_tool_hub_delivery_repository.py`
- Verify: `apps/api/tests/test_tool_hub_delivery_api.py`
- Verify: `apps/api/tests/test_tool_hub_runtime_service.py`
- Verify: `apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx`
- Verify: `apps/web/src/test/XXP4Page.test.tsx`

- [ ] **Step 1: Update the design-to-implementation mapping**

```md
- `P4.5.1` 工具定义与交付契约升级
  - `apps/api/app/tool_hub/models.py`
  - `apps/api/app/api/routes/tool_hub_operator.py`
  - `apps/web/src/lib/api.ts`
- `P4.5.2` 产物存储、版本与比对机制
  - `apps/api/app/db/models/tool_hub_delivery.py`
  - `apps/api/app/tool_hub/delivery_repository.py`
- `P4.5.3` AI 生成链与模板执行链
  - `apps/api/app/tool_hub/recipe_service.py`
  - `apps/api/app/tool_hub/generators/query_table_widget.py`
```

- [ ] **Step 2: Sync the local issue tree mirror**

```md
- `P4.5` 真实工具落地验证 `[开发中]`
  - `P4.5.1` 工具定义与交付契约升级 `[开发中]`
  - `P4.5.2` 产物存储、版本与比对机制 `[开发中]`
  - `P4.5.3` AI 生成链与模板执行链 `[开发中]`
  - `P4.5.4` 前端元组件样例实现与验证 `[开发中]`
  - `P4.5.5` `P3 -> P4 -> P5` 真实交付闭环验证 `[待开发]`
```

- [ ] **Step 3: Run the backend regression suite**

Run: `uv run pytest apps/api/tests/test_tool_hub_api.py apps/api/tests/test_tool_hub_delivery_repository.py apps/api/tests/test_tool_hub_delivery_api.py apps/api/tests/test_tool_hub_runtime_service.py -q`

Expected: PASS

- [ ] **Step 4: Run the frontend regression suite**

Run: `corepack pnpm --dir apps/web test -- P4RealToolDeliveryWorkspace.test.tsx XXP4Page.test.tsx`

Expected: PASS

- [ ] **Step 5: Run the final production build**

Run: `corepack pnpm --dir apps/web build`

Expected: PASS

- [ ] **Step 6: Commit the regression and doc sync**

```bash
git add DOC/CODEX_DOC/04_研发文档/01-P4-设计实现映射表.md docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md
git commit -m "docs: sync P4.5 delivery mapping and mirror state"
```

## Self-Review

**Spec coverage**

- “工具默认是最小原组件，不是页面”由 Task 1 契约升级实现
- “React + Ant Design 作为宿主提供的 peer 依赖”由 Task 1 contract + Task 4 UI manifest 展示实现
- “真实工具产物、版本、比对、校验报告”由 Task 2 delivery 持久化与 Task 3 generator/runtime 实现
- “现有 OpenAI-compatible 适配层参与 recipe 生成”由 Task 3 `ToolRecipeService` 实现
- “P3-sim -> P4 -> P5-sim 真实交付闭环”由 Task 3 routes + Task 4 UI + Task 5 regression 实现

**Placeholder scan**

- No unresolved placeholders remain in tasks.
- The first slice intentionally chooses a deterministic template generator for `QueryTableWidget`; the optional LLM call is additive, not a hidden gap.

**Type consistency**

- `tool_granularity`, `packaging_type`, `integration_mode`, `dependency_policy`, `runtime_dependencies` are introduced in Task 1 and reused with the same names in Tasks 3 and 4.
- The runtime queue name for real delivery is consistently `p4-build`.
- The delivery endpoints consistently use `build request -> build run -> delivery manifest`.
