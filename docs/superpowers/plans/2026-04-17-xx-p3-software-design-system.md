# XX-P3 Order-Driven Software Design Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `P3` 落地面向软件级产物的订单驱动软件设计编制与模块工单下发能力，形成“`P2` 正式虚规 -> `P3` 订单审批 -> 软设草案生成/评审冻结 -> 批次模块工单包 -> 人工推送 `P4`”的最小闭环。

**Architecture:** 后端新增 `software_design` 文件型版本化子域，以 `P3Order / SoftwareDesignBaseline / ModuleWorkorderBatchPackage` 作为核心对象，并通过 `overview / orders / review-threads / workorder-batches` 暴露接口。前端新增独立路由 `/xx-p3`，页面采用和 `XX-P4` 相同的独立驾驶舱壳层，但工作流切换为“订单列表 + 设计编制 + 评审协作 + 模块工单包”，所有关键动作均由人工触发。

**Tech Stack:** FastAPI, Pydantic, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

## File Map

- Create: `apps/api/app/software_design/__init__.py`
  - 标记 `software_design` 子域
- Create: `apps/api/app/software_design/models.py`
  - 定义 `P3Order`、`SoftwareDesignBaseline`、`ReviewThread`、`ModuleWorkorderBatchPackage`、概览与读模型
- Create: `apps/api/app/software_design/repository.py`
  - 文件型仓储，保存订单、基线、评论线程、工单包、推送记录
- Create: `apps/api/app/software_design/snapshot.py`
  - 组装概览、列表和详情投影
- Create: `apps/api/app/software_design/service.py`
  - 订单生命周期、软设草案生成、评论追加、冻结、工单包生成、推送 `P4`
- Create: `apps/api/app/api/routes/software_design.py`
  - `software_design` API 路由与依赖装配
- Modify: `apps/api/app/config.py`
  - 增加 `software_design_root`
- Modify: `apps/api/app/main.py`
  - 注册 `software_design_router`
- Create: `apps/api/tests/test_software_design_api.py`
  - 后端端到端 API 契约测试
- Modify: `apps/web/src/lib/api.ts`
  - 增加 `software_design` 相关类型
- Create: `apps/web/src/lib/softwareDesign.ts`
  - 前端 API 封装
- Modify: `apps/web/src/App.tsx`
  - 增加 `/xx-p3` 独立壳层路由
- Create: `apps/web/src/pages/XXP3Page.tsx`
  - P3 驾驶舱主页面
- Create: `apps/web/src/components/p3/P3Hero.tsx`
  - 顶部总览区
- Create: `apps/web/src/components/p3/P3OrderQueue.tsx`
  - 订单列表、审批/驳回入口
- Create: `apps/web/src/components/p3/P3OrderContextPanel.tsx`
  - 当前订单上下文摘要
- Create: `apps/web/src/components/p3/P3DesignWorkspace.tsx`
  - 软件设计说明草案工作区
- Create: `apps/web/src/components/p3/P3ReviewWorkspace.tsx`
  - 评论线程、AI 修订建议、冻结入口
- Create: `apps/web/src/components/p3/P3WorkorderBatchWorkspace.tsx`
  - 批次模块工单包预览、生成、推送入口
- Create: `apps/web/src/components/p3/P3WorkspaceTabs.tsx`
  - 页内工作区切换
- Create: `apps/web/src/components/p3/p3-workspace-tabs.css`
  - P3 标签视觉样式
- Create: `apps/web/src/test/XXP3Page.test.tsx`
  - 前端独立路由与关键工作流测试
- Modify: `apps/web/src/test/AppRoutes.test.tsx`
  - 补充 `/xx-p3` 引入后主壳层路由不受影响的回归检查

### Task 1: 锁定 `software_design` 后端订单生命周期契约

**Files:**
- Create: `apps/api/tests/test_software_design_api.py`

- [ ] **Step 1: 写失败测试，覆盖 `P3` 订单从创建到推送 `P4` 的最小闭环**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.software_design import get_software_design_service
from app.main import create_app
from app.software_design.service import SoftwareDesignService


def _create_requirement_spec(client: TestClient) -> str:
    response = client.post(
        "/api/requirements/specs",
        json={
            "archive_id": "20161116-nas",
            "status": "ready",
            "payload": {
                "application": {
                    "name": "空域协同规划软件",
                    "domain": "国家空域管理",
                    "summary": "围绕规划任务和审批流形成协同规划能力。",
                    "target_users": ["规划员", "审核员"],
                },
                "objects": [
                    {
                        "id": "planning-task",
                        "name": "规划任务",
                        "object_kind": "business",
                        "source_kind": "temporary",
                        "category": "domain_object",
                        "aliases": [],
                        "summary": "描述一次规划活动。",
                        "description": "用于承载规划状态、审批记录和输出。",
                        "source_archive_id": None,
                        "source_item_type": None,
                        "source_item_id": None,
                    }
                ],
                "processes": [],
                "rules": [],
                "metrics": [],
                "non_functional_constraints": [
                    {
                        "id": "constraint-audit",
                        "name": "全链路留痕",
                        "category": "audit",
                        "description": "关键审批和状态变更必须可追溯。",
                    }
                ],
            },
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _build_client(tmp_path: Path) -> TestClient:
    app = create_app()
    service = SoftwareDesignService(root=tmp_path / "software-design")
    app.dependency_overrides[get_software_design_service] = lambda: service
    return TestClient(app)


def test_software_design_order_lifecycle(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    spec_id = _create_requirement_spec(client)

    created = client.post(
        "/api/software-design/orders",
        json={
            "requirement_spec_id": spec_id,
            "requested_by": "架构组",
            "notes": "请先生成统一服务版本的软设草案。",
        },
    )
    assert created.status_code == 201
    order_id = created.json()["order_id"]
    assert created.json()["status"] == "pending_approval"

    overview = client.get("/api/software-design/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["pending_approval_count"] == 1

    approved = client.post(f"/api/software-design/orders/{order_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved_for_generation"

    generated = client.post(f"/api/software-design/orders/{order_id}/generate-draft")
    assert generated.status_code == 200
    assert generated.json()["status"] == "draft_ready"
    assert generated.json()["design_description"]["sections"][0]["title"] == "1. 设计目标与范围"

    thread = client.post(
        f"/api/software-design/orders/{order_id}/review-threads",
        json={
            "topic": "统一服务是否满足首版性能要求",
            "anchor": "section:architecture",
            "message": "请保留统一服务建议，但补充后续微服务拆分条件。",
        },
    )
    assert thread.status_code == 201
    assert thread.json()["status"] == "open"

    frozen = client.post(f"/api/software-design/orders/{order_id}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"

    batch = client.post(f"/api/software-design/orders/{order_id}/workorder-batch")
    assert batch.status_code == 201
    assert batch.json()["package_overview"]["architecture_recommendation"] == "unified_service"
    assert len(batch.json()["items"]) >= 1

    pushed = client.post(f"/api/software-design/orders/{order_id}/push-to-p4")
    assert pushed.status_code == 200
    assert pushed.json()["push_status"] == "pushed"
```

- [ ] **Step 2: 跑后端单测确认先红**

Run: `uv run pytest apps/api/tests/test_software_design_api.py -q`
Expected: FAIL，提示 `software_design` 路由、依赖或模型不存在。

### Task 2: 定义 `software_design` 子域的数据模型与文件仓储

**Files:**
- Modify: `apps/api/app/config.py`
- Create: `apps/api/app/software_design/__init__.py`
- Create: `apps/api/app/software_design/models.py`
- Create: `apps/api/app/software_design/repository.py`
- Create: `apps/api/app/software_design/snapshot.py`

- [ ] **Step 1: 在配置中新增 `software_design_root`，与 `tool_hub_root` 保持相同的仓储模式**

```python
class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///:memory:"
    storage_bucket: str = "knowledge-warehouse"
    storage_root: str = ".data/storage"
    knowledge_output_root: str = ".data/knowledge_output"
    application_modeling_root: str = ".data/application_modeling"
    tool_hub_root: str = ".data/tool_hub"
    software_design_root: str = ".data/software_design"
    default_archive_id: str = "20161116-nas"

    @model_validator(mode="after")
    def resolve_repository_relative_paths(self) -> "Settings":
        self.storage_root = _resolve_repo_path(self.storage_root)
        self.knowledge_output_root = _resolve_repo_path(self.knowledge_output_root)
        self.application_modeling_root = _resolve_repo_path(self.application_modeling_root)
        self.tool_hub_root = _resolve_repo_path(self.tool_hub_root)
        self.software_design_root = _resolve_repo_path(self.software_design_root)
        return self
```

- [ ] **Step 2: 在 `models.py` 中定义订单、基线、评论线程、软设投影和工单包对象**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OrderStatus = Literal[
    "pending_approval",
    "rejected",
    "approved_for_generation",
    "generating",
    "draft_ready",
    "in_revision",
    "pending_review",
    "changes_requested",
    "frozen",
    "package_ready",
    "pushed_to_p4",
]


class P3OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_spec_id: str
    requested_by: str
    notes: str = ""


class DesignSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    summary: str
    body: str


class DesignModule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    name: str
    objective: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)


class SoftwareDesignBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: str
    order_id: str
    requirement_spec_id: str
    architecture_mode: Literal["unified_service", "microservice"] = "unified_service"
    interaction_mode: Literal["bs", "cs"] = "bs"
    sections: list[DesignSection] = Field(default_factory=list)
    modules: list[DesignModule] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)


class ReviewThreadWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    anchor: str
    message: str


class ReviewThread(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    order_id: str
    topic: str
    anchor: str
    status: Literal["open", "resolved"] = "open"
    messages: list[str] = Field(default_factory=list)


class ModuleWorkorderBatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    module_id: str
    title: str
    objective: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: 在 `repository.py` 中实现文件型持久化，并在 `snapshot.py` 中提供列表/概览投影**

```python
class SoftwareDesignRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.orders_dir = self.root / "orders"
        self.baselines_dir = self.root / "baselines"
        self.review_threads_dir = self.root / "review_threads"
        self.packages_dir = self.root / "packages"
        self.pushes_dir = self.root / "pushes"
        for path in [
            self.orders_dir,
            self.baselines_dir,
            self.review_threads_dir,
            self.packages_dir,
            self.pushes_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def save_order(self, order: P3Order) -> P3Order:
        self._write_json(self.orders_dir / f"{order.order_id}.json", order.model_dump(mode="json"))
        return order

    def list_orders(self) -> list[P3Order]:
        return [P3Order.model_validate(self._read_json(path)) for path in sorted(self.orders_dir.glob("*.json"))]

    def save_baseline(self, baseline: SoftwareDesignBaseline) -> SoftwareDesignBaseline:
        self._write_json(self.baselines_dir / f"{baseline.order_id}.json", baseline.model_dump(mode="json"))
        return baseline


def project_overview(orders: list[P3Order], packages: list[ModuleWorkorderBatchPackage]) -> SoftwareDesignOverview:
    return SoftwareDesignOverview(
        metrics=SoftwareDesignMetrics(
            order_count=len(orders),
            pending_approval_count=sum(1 for order in orders if order.status == "pending_approval"),
            frozen_count=sum(1 for order in orders if order.status == "frozen"),
            package_ready_count=sum(1 for order in orders if order.status == "package_ready"),
            pushed_count=sum(1 for order in orders if order.status == "pushed_to_p4"),
        ),
        recent_orders=[project_order_summary(order) for order in orders[:5]],
        recent_packages=[project_package_summary(package) for package in packages[:5]],
    )
```

- [ ] **Step 4: 运行单测确认错误从“模块不存在”收敛到“服务/路由未实现”**

Run: `uv run pytest apps/api/tests/test_software_design_api.py -q`
Expected: FAIL，但报错应聚焦到 `get_software_design_service`、路由或生命周期方法缺失，而不是模型导入失败。

### Task 3: 实现 `software_design` 服务层与 API 路由

**Files:**
- Create: `apps/api/app/software_design/service.py`
- Create: `apps/api/app/api/routes/software_design.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_software_design_api.py`

- [ ] **Step 1: 在服务层实现订单受理、审批、软设生成、评论追加、冻结、工单包生成与推送**

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.requirements.service import RequirementSpecService
from app.software_design.models import (
    ModuleWorkorderBatchPackage,
    P3Order,
    P3OrderCreate,
    P3OrderDetail,
    ReviewThread,
    ReviewThreadWrite,
    SoftwareDesignBaseline,
)
from app.software_design.repository import SoftwareDesignRepository
from app.software_design.snapshot import project_order_detail, project_order_list, project_overview


class SoftwareDesignService:
    def __init__(self, root: str | Path) -> None:
        self.repository = SoftwareDesignRepository(root)

    def get_overview(self):
        return {"data": project_overview(self.repository.list_orders(), self.repository.list_packages())}

    def list_orders(self):
        return {"data": {"items": project_order_list(self.repository.list_orders())}}

    def get_order_detail(self, order_id: str) -> P3OrderDetail:
        order = self.repository.get_order(order_id)
        baseline = self.repository.get_baseline(order_id)
        package = self.repository.get_package(order_id)
        threads = self.repository.list_review_threads(order_id)
        return project_order_detail(order, baseline, threads, package)

    def create_order(self, payload: P3OrderCreate, requirement_service: RequirementSpecService) -> P3Order:
        spec = requirement_service.get_spec(payload.requirement_spec_id)
        if spec is None:
            raise ValueError("Requirement spec not found")
        order = P3Order(
            order_id=f"p3-order-{uuid4().hex[:12]}",
            requirement_spec_id=payload.requirement_spec_id,
            application_name=spec["application_name"],
            requested_by=payload.requested_by,
            notes=payload.notes,
            status="pending_approval",
        )
        return self.repository.save_order(order)

    def approve_order(self, order_id: str) -> P3Order:
        order = self.repository.get_order(order_id)
        approved = order.model_copy(update={"status": "approved_for_generation"})
        return self.repository.save_order(approved)

    def generate_draft(self, order_id: str, requirement_service: RequirementSpecService) -> P3OrderDetail:
        order = self.repository.get_order(order_id)
        spec = requirement_service.get_spec(order.requirement_spec_id)
        baseline = self._build_baseline_from_requirement(order, spec)
        self.repository.save_baseline(baseline)
        updated = self.repository.save_order(order.model_copy(update={"status": "draft_ready"}))
        return project_order_detail(updated, baseline, self.repository.list_review_threads(order_id), None)

    def add_review_thread(self, order_id: str, payload: ReviewThreadWrite) -> ReviewThread:
        thread = ReviewThread(
            thread_id=f"thread-{uuid4().hex[:12]}",
            order_id=order_id,
            topic=payload.topic,
            anchor=payload.anchor,
            messages=[payload.message],
        )
        self.repository.save_order(self.repository.get_order(order_id).model_copy(update={"status": "in_revision"}))
        return self.repository.save_review_thread(thread)

    def freeze_order(self, order_id: str) -> P3Order:
        order = self.repository.get_order(order_id)
        return self.repository.save_order(order.model_copy(update={"status": "frozen"}))

    def build_workorder_batch(self, order_id: str) -> ModuleWorkorderBatchPackage:
        baseline = self.repository.get_baseline(order_id)
        package = self._build_batch_from_baseline(order_id, baseline)
        self.repository.save_order(self.repository.get_order(order_id).model_copy(update={"status": "package_ready"}))
        return self.repository.save_package(package)

    def push_to_p4(self, order_id: str) -> dict[str, str]:
        self.repository.save_push_record(order_id, {"push_status": "pushed"})
        self.repository.save_order(self.repository.get_order(order_id).model_copy(update={"status": "pushed_to_p4"}))
        return {"push_status": "pushed"}
```

- [ ] **Step 2: 在路由层对接 `requirements` 服务和 `software_design` 服务，并暴露完整生命周期 API**

```python
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.db.session import get_session
from app.requirements.service import RequirementSpecService
from app.software_design.models import P3OrderCreate, ReviewThreadWrite
from app.software_design.service import SoftwareDesignService

router = APIRouter(prefix="/software-design", tags=["software-design"])


def get_requirement_spec_service(session=Depends(get_session)) -> RequirementSpecService:
    return RequirementSpecService(session)


def get_software_design_service() -> SoftwareDesignService:
    return SoftwareDesignService(root=settings.software_design_root)


@router.get("/overview")
def get_software_design_overview(service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.get_overview()


@router.get("/orders")
def list_software_design_orders(service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.list_orders()


@router.get("/orders/{order_id}")
def get_software_design_order_detail(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.get_order_detail(order_id)


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_software_design_order(
    payload: P3OrderCreate,
    service: SoftwareDesignService = Depends(get_software_design_service),
    requirement_service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    try:
        return service.create_order(payload, requirement_service)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/{order_id}/approve")
def approve_software_design_order(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.approve_order(order_id)


@router.post("/orders/{order_id}/generate-draft")
def generate_software_design_draft(
    order_id: str,
    service: SoftwareDesignService = Depends(get_software_design_service),
    requirement_service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    return service.generate_draft(order_id, requirement_service)


@router.post("/orders/{order_id}/review-threads", status_code=status.HTTP_201_CREATED)
def create_review_thread(
    order_id: str,
    payload: ReviewThreadWrite,
    service: SoftwareDesignService = Depends(get_software_design_service),
):
    return service.add_review_thread(order_id, payload)


@router.post("/orders/{order_id}/freeze")
def freeze_software_design(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.freeze_order(order_id)


@router.post("/orders/{order_id}/workorder-batch", status_code=status.HTTP_201_CREATED)
def build_workorder_batch(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.build_workorder_batch(order_id)


@router.post("/orders/{order_id}/push-to-p4")
def push_workorder_batch_to_p4(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.push_to_p4(order_id)
```

- [ ] **Step 3: 在应用入口注册 `software_design_router`**

```python
from app.api.routes.software_design import router as software_design_router


def create_app() -> FastAPI:
    Base.metadata.create_all(engine)
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(archives_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(governance_router, prefix=settings.api_prefix)
    app.include_router(knowledge_router, prefix=settings.api_prefix)
    app.include_router(modeling_router, prefix=settings.api_prefix)
    app.include_router(requirements_router, prefix=settings.api_prefix)
    app.include_router(tool_hub_router, prefix=settings.api_prefix)
    app.include_router(software_design_router, prefix=settings.api_prefix)
    return app
```

- [ ] **Step 4: 重新运行后端契约测试确认转绿**

Run: `uv run pytest apps/api/tests/test_software_design_api.py -q`
Expected: PASS

- [ ] **Step 5: 提交后端生命周期实现**

```bash
git add apps/api/app/config.py apps/api/app/main.py apps/api/app/api/routes/software_design.py apps/api/app/software_design apps/api/tests/test_software_design_api.py
git commit -m "feat: add software design order lifecycle api"
```

### Task 4: 锁定 `/xx-p3` 独立驾驶舱路由与核心交互测试

**Files:**
- Create: `apps/web/src/test/XXP3Page.test.tsx`

- [ ] **Step 1: 写失败测试，覆盖订单队列、审批、软设草案、冻结和工单包推送**

```tsx
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
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

test("renders XX-P3 cockpit route and drives order review workflow", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/software-design/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 1,
              pending_approval_count: 1,
              frozen_count: 0,
              package_ready_count: 0,
              pushed_count: 0,
            },
            recent_orders: [],
            recent_packages: [],
          },
        },
      });
    }
    if (url === "/software-design/orders") {
      return Promise.resolve({
        data: {
          data: {
            items: [
              {
                order_id: "p3-order-1",
                application_name: "空域协同规划软件",
                requirement_spec_id: "spec-1",
                status: "pending_approval",
                updated_at: "2026-04-17T10:00:00Z",
              },
            ],
          },
        },
      });
    }
    if (url === "/software-design/orders/p3-order-1") {
      return Promise.resolve({
        data: {
          order_id: "p3-order-1",
          requirement_spec_summary: {
            application_name: "空域协同规划软件",
            domain_name: "国家空域管理",
            status: "ready",
          },
          status: "draft_ready",
          design_description: {
            sections: [{ id: "goal", title: "1. 设计目标与范围", summary: "..." }],
          },
          review_threads: [],
          workorder_batch: null,
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url.endsWith("/approve")) {
      return Promise.resolve({ data: { status: "approved_for_generation" } });
    }
    if (url.endsWith("/generate-draft")) {
      return Promise.resolve({ data: { status: "draft_ready" } });
    }
    if (url.endsWith("/freeze")) {
      return Promise.resolve({ data: { status: "frozen" } });
    }
    if (url.endsWith("/workorder-batch")) {
      return Promise.resolve({
        data: {
          package_overview: {
            architecture_recommendation: "unified_service",
            interaction_mode: "bs",
          },
          items: [{ item_id: "item-1", title: "规划任务管理模块实现" }],
        },
      });
    }
    if (url.endsWith("/push-to-p4")) {
      return Promise.resolve({ data: { push_status: "pushed" } });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("XX-P3")).toBeInTheDocument();
  expect(screen.getByText("软件设计编制与模块工单下发系统")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "审批通过" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "设计编制" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "审批通过" }));
  fireEvent.click(screen.getByRole("button", { name: "生成软设草案" }));
  fireEvent.click(screen.getByRole("tab", { name: "模块工单包" }));
  fireEvent.click(screen.getByRole("button", { name: "生成批次工单包" }));

  expect(await screen.findByText("规划任务管理模块实现")).toBeInTheDocument();
  expect(screen.getByText("unified_service")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "推送到 P4" }));
  expect(postMock).toHaveBeenCalledWith("/software-design/orders/p3-order-1/push-to-p4");
});
```

- [ ] **Step 2: 跑前端测试确认先红**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: FAIL，提示 `/xx-p3` 路由、`P3` 组件或 `software_design` API 封装不存在。

### Task 5: 补齐前端 `software_design` API 类型与 `/xx-p3` 独立路由壳层

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/softwareDesign.ts`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: 在 `api.ts` 中新增 `software_design` 相关类型**

```ts
export type P3OrderStatus =
  | "pending_approval"
  | "rejected"
  | "approved_for_generation"
  | "generating"
  | "draft_ready"
  | "in_revision"
  | "pending_review"
  | "changes_requested"
  | "frozen"
  | "package_ready"
  | "pushed_to_p4";

export type P3OrderSummary = {
  order_id: string;
  requirement_spec_id: string;
  application_name: string;
  status: P3OrderStatus;
  updated_at: string;
};

export type SoftwareDesignOverview = {
  metrics: {
    order_count: number;
    pending_approval_count: number;
    frozen_count: number;
    package_ready_count: number;
    pushed_count: number;
  };
  recent_orders: P3OrderSummary[];
  recent_packages: Array<{
    package_id: string;
    order_id: string;
    item_count: number;
    push_status: string;
  }>;
};

export type P3OrderDetail = {
  order_id: string;
  status: P3OrderStatus;
  requirement_spec_summary: {
    application_name: string;
    domain_name: string;
    status: string;
  };
  design_description: {
    sections: Array<{ id: string; title: string; summary: string; body?: string }>;
    modules?: Array<{ module_id: string; name: string; objective: string }>;
  } | null;
  review_threads: Array<{
    thread_id: string;
    topic: string;
    anchor: string;
    status: "open" | "resolved";
    messages: string[];
  }>;
  workorder_batch: {
    package_overview: {
      architecture_recommendation: string;
      interaction_mode: string;
    };
    items: Array<{ item_id: string; title: string }>;
  } | null;
};
```

- [ ] **Step 2: 新建 `softwareDesign.ts`，封装 `overview / orders / lifecycle action` 调用**

```ts
import { api } from "./api";
import type { P3OrderDetail, P3OrderSummary, SoftwareDesignOverview } from "./api";

export function getSoftwareDesignOverview() {
  return api.get<{ data: SoftwareDesignOverview }>("/software-design/overview");
}

export function getSoftwareDesignOrders() {
  return api.get<{ data: { items: P3OrderSummary[] } }>("/software-design/orders");
}

export function getSoftwareDesignOrderDetail(orderId: string) {
  return api.get<P3OrderDetail>(`/software-design/orders/${orderId}`);
}

export function approveSoftwareDesignOrder(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/approve`);
}

export function generateSoftwareDesignDraft(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/generate-draft`);
}

export function freezeSoftwareDesign(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/freeze`);
}

export function createReviewThread(
  orderId: string,
  payload: { topic: string; anchor: string; message: string },
) {
  return api.post(`/software-design/orders/${orderId}/review-threads`, payload);
}

export function generateWorkorderBatch(orderId: string) {
  return api.post<P3OrderDetail["workorder_batch"]>(`/software-design/orders/${orderId}/workorder-batch`);
}

export function pushWorkorderBatchToP4(orderId: string) {
  return api.post<{ push_status: string }>(`/software-design/orders/${orderId}/push-to-p4`);
}
```

- [ ] **Step 3: 在 `App.tsx` 中增加 `/xx-p3` 独立壳层路由**

```tsx
import { XXP3Page } from "./pages/XXP3Page";


export default function App() {
  const location = useLocation();

  if (location.pathname.startsWith("/xx-p3")) {
    return (
      <Routes>
        <Route path="/xx-p3" element={<XXP3Page />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/xx-p4")) {
    return (
      <Routes>
        <Route path="/xx-p4" element={<XXP4Page />} />
      </Routes>
    );
  }

  return <MainShell />;
}
```

- [ ] **Step 4: 跑前端测试确认错误收敛到页面组件未实现**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: FAIL，但报错应集中在 `XXP3Page` 或 `P3` 子组件不存在，而不是类型或 API 封装缺失。

### Task 6: 实现 `XX-P3` 驾驶舱页面与订单驱动工作区

**Files:**
- Create: `apps/web/src/pages/XXP3Page.tsx`
- Create: `apps/web/src/components/p3/P3Hero.tsx`
- Create: `apps/web/src/components/p3/P3OrderQueue.tsx`
- Create: `apps/web/src/components/p3/P3OrderContextPanel.tsx`
- Create: `apps/web/src/components/p3/P3DesignWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3ReviewWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3WorkorderBatchWorkspace.tsx`
- Create: `apps/web/src/components/p3/P3WorkspaceTabs.tsx`
- Create: `apps/web/src/components/p3/p3-workspace-tabs.css`
- Test: `apps/web/src/test/XXP3Page.test.tsx`

- [ ] **Step 1: 在 `XXP3Page.tsx` 中搭建与 `XXP4Page` 风格一致的页面壳层和数据加载入口**

```tsx
import { startTransition, useEffect, useState } from "react";
import { Alert, Card, Space, Spin } from "antd";

import { P3Hero } from "../components/p3/P3Hero";
import { P3OrderQueue } from "../components/p3/P3OrderQueue";
import { P3OrderContextPanel } from "../components/p3/P3OrderContextPanel";
import { P3WorkspaceTabs } from "../components/p3/P3WorkspaceTabs";
import {
  approveSoftwareDesignOrder,
  createReviewThread,
  freezeSoftwareDesign,
  generateSoftwareDesignDraft,
  generateWorkorderBatch,
  getSoftwareDesignOrderDetail,
  getSoftwareDesignOrders,
  getSoftwareDesignOverview,
  pushWorkorderBatchToP4,
} from "../lib/softwareDesign";

export function XXP3Page() {
  const [overview, setOverview] = useState<SoftwareDesignOverview | null>(null);
  const [orders, setOrders] = useState<P3OrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<P3OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadPage(showLoading = false) {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const [overviewResponse, ordersResponse] = await Promise.all([
        getSoftwareDesignOverview(),
        getSoftwareDesignOrders(),
      ]);
      const orderItems = ordersResponse.data.data.items;
      const initialOrderId = selectedOrderId ?? orderItems[0]?.order_id ?? null;
      const detailResponse = initialOrderId ? await getSoftwareDesignOrderDetail(initialOrderId) : null;
      startTransition(() => {
        setOverview(overviewResponse.data.data);
        setOrders(orderItems);
        setSelectedOrderId(initialOrderId);
        setSelectedOrder(detailResponse?.data ?? null);
        setError(null);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载 XX-P3 数据失败");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadPage(true);
  }, []);
```

- [ ] **Step 2: 实现订单列表和上下文面板，让审批、草案生成动作在列表页即可触发**

```tsx
<P3OrderQueue
  orders={orders}
  selectedOrderId={selectedOrderId}
  onSelectOrder={async (orderId) => {
    setSelectedOrderId(orderId);
    const detail = await getSoftwareDesignOrderDetail(orderId);
    setSelectedOrder(detail.data);
  }}
  onApprove={async (orderId) => {
    await approveSoftwareDesignOrder(orderId);
    await loadPage();
  }}
  onGenerateDraft={async (orderId) => {
    await generateSoftwareDesignDraft(orderId);
    await loadPage();
  }}
/>

<P3OrderContextPanel order={selectedOrder} />
```

- [ ] **Step 3: 实现“设计编制”和“评审协作”工作区，至少展示章节、评论线程和冻结入口**

```tsx
<P3WorkspaceTabs
  items={[
    {
      key: "overview",
      label: "总览",
      children: <P3OrderContextPanel order={selectedOrder} />,
    },
    {
      key: "design",
      label: "设计编制",
      children: <P3DesignWorkspace order={selectedOrder} />,
    },
    {
      key: "review",
      label: "评审协作",
      children: (
        <P3ReviewWorkspace
          order={selectedOrder}
          onCreateThread={async (payload) => {
            if (!selectedOrder) return;
            await createReviewThread(selectedOrder.order_id, payload);
            await loadPage();
          }}
          onFreeze={async () => {
            if (!selectedOrder) return;
            await freezeSoftwareDesign(selectedOrder.order_id);
            await loadPage();
          }}
        />
      ),
    },
    {
      key: "workorders",
      label: "模块工单包",
      children: (
        <P3WorkorderBatchWorkspace
          order={selectedOrder}
          onGenerateBatch={async () => {
            if (!selectedOrder) return;
            await generateWorkorderBatch(selectedOrder.order_id);
            await loadPage();
          }}
          onPushToP4={async () => {
            if (!selectedOrder) return;
            await pushWorkorderBatchToP4(selectedOrder.order_id);
            await loadPage();
          }}
        />
      ),
    },
  ]}
/>

export function P3ReviewWorkspace({
  order,
  onCreateThread,
  onFreeze,
}: {
  order: P3OrderDetail | null;
  onCreateThread: (payload: { topic: string; anchor: string; message: string }) => Promise<void>;
  onFreeze: () => Promise<void>;
}) {
  if (!order) {
    return <Empty description="请选择订单" />;
  }

  return (
    <Space direction="vertical" size={16} style={{ display: "flex" }}>
      <Button
        onClick={() =>
          void onCreateThread({
            topic: "统一服务补充说明",
            anchor: "section:architecture",
            message: "补充后续微服务拆分条件。",
          })
        }
      >
        新增评论线程
      </Button>
      <List
        dataSource={order.review_threads}
        renderItem={(thread) => (
          <List.Item key={thread.thread_id}>
            <Typography.Text>{thread.topic}</Typography.Text>
          </List.Item>
        )}
      />
      <Button type="primary" onClick={() => void onFreeze()}>
        冻结软件设计说明
      </Button>
    </Space>
  );
}
```

- [ ] **Step 4: 在模块工单包工作区展示包级推荐与条目列表，并接通推送按钮**

```tsx
export function P3WorkorderBatchWorkspace({
  order,
  onGenerateBatch,
  onPushToP4,
}: {
  order: P3OrderDetail | null;
  onGenerateBatch: () => Promise<void>;
  onPushToP4: () => Promise<void>;
}) {
  if (!order) {
    return <Empty description="请选择订单" />;
  }

  return (
    <Space direction="vertical" size={16} style={{ display: "flex" }}>
      <Card>
        <Typography.Title level={4}>批次模块工单包</Typography.Title>
        {order.workorder_batch ? (
          <>
            <Typography.Text>{order.workorder_batch.package_overview.architecture_recommendation}</Typography.Text>
            <List
              dataSource={order.workorder_batch.items}
              renderItem={(item) => (
                <List.Item key={item.item_id}>
                  <Typography.Text>{item.title}</Typography.Text>
                </List.Item>
              )}
            />
            <Button type="primary" onClick={() => void onPushToP4()}>
              推送到 P4
            </Button>
          </>
        ) : (
          <Button type="primary" onClick={() => void onGenerateBatch()}>
            生成批次工单包
          </Button>
        )}
      </Card>
    </Space>
  );
}
```

- [ ] **Step 5: 跑前端页面测试确认转绿**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: PASS

- [ ] **Step 6: 提交前端订单驾驶舱实现**

```bash
git add apps/web/src/App.tsx apps/web/src/lib/api.ts apps/web/src/lib/softwareDesign.ts apps/web/src/pages/XXP3Page.tsx apps/web/src/components/p3 apps/web/src/test/XXP3Page.test.tsx
git commit -m "feat: add xx-p3 order driven cockpit"
```

### Task 7: 跑 `P3` 回归验证并补主壳层路由回归

**Files:**
- Modify: `apps/web/src/test/AppRoutes.test.tsx`
- Verify: `apps/api/tests/test_software_design_api.py`
- Verify: `apps/web/src/test/XXP3Page.test.tsx`
- Verify: `apps/web/src/test/AppRoutes.test.tsx`

- [ ] **Step 1: 在 `AppRoutes.test.tsx` 中补充独立壳层共存的基础回归**

```tsx
test("keeps main shell routes working after xx-p3 route registration", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/documents") {
      return Promise.resolve({ data: [] });
    }

    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 66,
          entity_count: 751,
          event_count: 4,
          process_count: 6,
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "10002024_NAS-EA-OV-2-As-Is-V1.0-091311",
            file_type: "docx",
            source_archive: "20161116-chinese",
            character_count: 23271,
            entity_count: 52,
            event_count: 1,
            process_count: 0,
            knowledge_item_count: 53,
          },
        ],
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/documents"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("已建库档案文档")).toBeInTheDocument();
});
```

- [ ] **Step 2: 跑后端 `P3` 生命周期测试**

Run: `uv run pytest apps/api/tests/test_software_design_api.py -q`
Expected: PASS

- [ ] **Step 3: 跑前端 `XX-P3` 驾驶舱测试**

Run: `corepack pnpm --dir apps/web test -- XXP3Page.test.tsx`
Expected: PASS

- [ ] **Step 4: 跑主壳层路由回归**

Run: `corepack pnpm --dir apps/web test -- AppRoutes.test.tsx`
Expected: PASS，证明新增 `/xx-p3` 独立壳层没有破坏现有主应用路由。

- [ ] **Step 5: 提交回归测试补强**

```bash
git add apps/web/src/test/AppRoutes.test.tsx
git commit -m "test: cover xx-p3 route coexistence"
```
