from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.requirements.service import RequirementSpecService
from app.software_design.models import (
    DesignModule,
    DesignSection,
    ModuleWorkorderBatchItem,
    ModuleWorkorderBatchOverview,
    ModuleWorkorderBatchPackage,
    P3Order,
    P3OrderCreate,
    P3OrderDetail,
    ReviewThread,
    ReviewThreadWrite,
    SoftwareDesignBaseline,
    now_iso,
)
from app.software_design.repository import SoftwareDesignRepository
from app.software_design.snapshot import project_order_detail, project_order_list, project_overview


class SoftwareDesignService:
    def __init__(self, root: str | Path) -> None:
        self.repository = SoftwareDesignRepository(root)

    def get_overview(self) -> dict[str, object]:
        return {"data": project_overview(self.repository.list_orders(), self.repository.list_packages())}

    def list_orders(self) -> dict[str, object]:
        return {"data": {"items": project_order_list(self.repository.list_orders())}}

    def get_order_detail(self, order_id: str) -> P3OrderDetail:
        order = self._get_order(order_id)
        return project_order_detail(
            order,
            self.repository.get_baseline(order_id),
            self.repository.list_review_threads(order_id),
            self.repository.get_package(order_id),
        )

    def create_order(self, payload: P3OrderCreate, requirement_service: RequirementSpecService) -> P3Order:
        spec = requirement_service.get_spec(payload.requirement_spec_id)
        if spec is None:
            raise ValueError("Requirement spec not found")
        timestamp = now_iso()
        order = P3Order(
            order_id=f"p3-order-{uuid4().hex[:12]}",
            requirement_spec_id=payload.requirement_spec_id,
            application_name=spec["application_name"],
            domain_name=spec["domain_name"],
            requirement_spec_status=spec["status"],
            requested_by=payload.requested_by,
            notes=payload.notes,
            status="pending_approval",
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_order(order)

    def approve_order(self, order_id: str) -> P3Order:
        order = self._get_order(order_id)
        return self.repository.save_order(order.model_copy(update={"status": "approved_for_generation", "updated_at": now_iso()}))

    def generate_draft(self, order_id: str, requirement_service: RequirementSpecService) -> P3OrderDetail:
        order = self._get_order(order_id)
        spec = requirement_service.get_spec(order.requirement_spec_id)
        if spec is None:
            raise ValueError("Requirement spec not found")
        generating = self.repository.save_order(order.model_copy(update={"status": "generating", "updated_at": now_iso()}))
        baseline = self._build_baseline_from_requirement(generating, spec)
        self.repository.save_baseline(baseline)
        draft_ready = self.repository.save_order(generating.model_copy(update={"status": "draft_ready", "updated_at": now_iso()}))
        return project_order_detail(draft_ready, baseline, self.repository.list_review_threads(order_id), self.repository.get_package(order_id))

    def add_review_thread(self, order_id: str, payload: ReviewThreadWrite) -> ReviewThread:
        thread = ReviewThread(
            thread_id=f"thread-{uuid4().hex[:12]}",
            order_id=order_id,
            topic=payload.topic,
            anchor=payload.anchor,
            messages=[payload.message],
        )
        order = self._get_order(order_id)
        self.repository.save_order(order.model_copy(update={"status": "in_revision", "updated_at": now_iso()}))
        return self.repository.save_review_thread(thread)

    def freeze_order(self, order_id: str) -> P3Order:
        order = self._get_order(order_id)
        return self.repository.save_order(order.model_copy(update={"status": "frozen", "updated_at": now_iso()}))

    def build_workorder_batch(self, order_id: str) -> ModuleWorkorderBatchPackage:
        order = self._get_order(order_id)
        baseline = self.repository.get_baseline(order_id)
        if baseline is None:
            raise ValueError("Software design baseline not found")
        package = self._build_batch_from_baseline(order_id, baseline)
        self.repository.save_order(order.model_copy(update={"status": "package_ready", "updated_at": now_iso()}))
        return self.repository.save_package(package)

    def push_to_p4(self, order_id: str) -> dict[str, str]:
        order = self._get_order(order_id)
        package = self.repository.get_package(order_id)
        if package is None:
            raise ValueError("Module workorder batch not found")
        updated_package = package.model_copy(update={"push_status": "pushed", "updated_at": now_iso()})
        self.repository.save_package(updated_package)
        self.repository.save_order(order.model_copy(update={"status": "pushed_to_p4", "updated_at": now_iso()}))
        self.repository.save_push_record(order_id, {"push_status": "pushed"})
        return {"push_status": "pushed"}

    def _build_baseline_from_requirement(self, order: P3Order, spec: dict) -> SoftwareDesignBaseline:
        payload = spec["payload"]
        application_summary = payload.get("application", {}).get("summary", "")
        object_items = payload.get("objects", [])
        constraints = [item.get("description", "") for item in payload.get("non_functional_constraints", []) if item.get("description")]
        module_source_name = object_items[0]["name"] if object_items else order.application_name
        module_name = "规划任务管理" if "规划任务" in module_source_name else f"{module_source_name}管理"
        module = DesignModule(
            module_id=f"module-{uuid4().hex[:8]}",
            name=module_name,
            objective=f"围绕{module_source_name}实现核心业务处理能力。",
            inputs=["planning_request"],
            outputs=["planning_task"],
            constraints=constraints or ["关键状态变更需留痕"],
            recommended_tools=["workflow_engine", "form_builder"],
        )
        sections = [
            DesignSection(
                id="goal",
                title="1. 设计目标与范围",
                summary="定义本次软件设计工作的范围和目标。",
                body=application_summary or f"本设计面向 {order.application_name} 的首版交付范围。",
            ),
            DesignSection(
                id="architecture",
                title="2. 总体架构与技术路线",
                summary="说明统一服务、交互模式和后续拆分建议。",
                body="首版建议采用 unified_service 架构与 BS 交互模式，后续根据负载与职责边界再评估微服务拆分。",
            ),
            DesignSection(
                id="modules",
                title="3. 模块划分与职责",
                summary="描述核心模块、输入输出与边界。",
                body=f"首版以 {module.name} 作为核心实现模块，承载主要业务流程与状态变更。",
            ),
            DesignSection(
                id="handoff",
                title="4. 模块工单下发建议",
                summary="面向 P4 给出模块实现建议。",
                body="模块工单包应保留统一服务实现建议，并为后续工具匹配提供推荐能力类型。",
            ),
        ]
        requirement_ids = [item.get("id") for item in object_items if item.get("id")]
        return SoftwareDesignBaseline(
            baseline_id=f"sdb-{uuid4().hex[:12]}",
            order_id=order.order_id,
            requirement_spec_id=order.requirement_spec_id,
            sections=sections,
            modules=[module],
            requirement_ids=requirement_ids,
        )

    def _build_batch_from_baseline(self, order_id: str, baseline: SoftwareDesignBaseline) -> ModuleWorkorderBatchPackage:
        items = [
            ModuleWorkorderBatchItem(
                item_id=f"workitem-{uuid4().hex[:12]}",
                module_id=module.module_id,
                title=f"{module.name}模块实现",
                objective=module.objective,
                inputs=module.inputs,
                outputs=module.outputs,
                constraints=module.constraints,
                acceptance=[
                    f"可完成{module.name}核心流程",
                    "关键状态历史可查询",
                ],
                recommended_tools=module.recommended_tools,
            )
            for module in baseline.modules
        ]
        return ModuleWorkorderBatchPackage(
            package_id=f"mwbp-{uuid4().hex[:12]}",
            order_id=order_id,
            design_description_id=f"sdd-{order_id}",
            package_overview=ModuleWorkorderBatchOverview(
                architecture_recommendation=baseline.architecture_mode,
                interaction_mode=baseline.interaction_mode,
                tool_recommendations=sorted({tool for module in baseline.modules for tool in module.recommended_tools}),
                design_notes=["先完成统一服务实现，再评估拆分时机。"],
            ),
            items=items,
        )

    def _get_order(self, order_id: str) -> P3Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise ValueError("P3 order not found")
        return order
