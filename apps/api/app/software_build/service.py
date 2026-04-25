from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.software_build.models import (
    P5AssemblyAttempt,
    P5AssemblyAttemptCreate,
    P5AssemblyModule,
    P5AssemblyPlan,
    P5BuildMetrics,
    P5BuildOverview,
    P5DeliveryRuntimeClearResult,
    P5DeliveryOrder,
    P5DeliveryOrderCreate,
    P5DeliveryOrderDetail,
    P5DeliveryOrderSummary,
    P5DesignInputSimCreate,
    P5DesignInputSnapshot,
    P5DesignInputSource,
    P5ExportConfig,
    P5FeedbackTask,
    P5FeedbackTaskReview,
    P5GapRecord,
    P5InputBinding,
    P5InputBindingConfirmRequest,
    P5InputSnapshot,
    P5ModuleBindingDecision,
    P5ModuleBindingUpdate,
    P5OutputArtifact,
    P5OutputPreview,
    P5RuntimeLog,
    P5RuntimeSnapshot,
    P5RuntimeStage,
    P5SupplyInputSimCreate,
    P5SupplyInputSnapshot,
    P5SupplyInputSource,
    P5SupplyInputTool,
    P5ValidationReport,
    P5WorkspaceBootstrapRequest,
    P5WorkspaceBootstrapResult,
    now_iso,
)
from app.software_build.repository import SoftwareBuildRepository
from app.software_design.models import DesignModule
from app.software_design.repository import SoftwareDesignRepository
from app.tool_hub.repository import ToolHubRepository

DEMO_APPLICATION_NAME = "基于地理信息系统的通视分析软件"
DEMO_REQUIREMENT_SPEC_ID = "spec-gis-los-analysis-001"
DEMO_BASELINE_ID = "baseline-gis-los-analysis-001"
DEMO_DESIGN_INPUT_ID = "design-input-gis-los-analysis"
DEMO_SUPPLY_INPUT_ID = "supply-input-gis-los-analysis"
DEMO_P3_SOURCE_REF = "xx/P3/DOC/sim:gis-los-analysis"


class SoftwareBuildService:
    def __init__(self, root: str | Path, software_design_root: str | Path, tool_hub_root: str | Path) -> None:
        self.repository = SoftwareBuildRepository(root)
        self.software_design_repository = SoftwareDesignRepository(software_design_root)
        self.tool_hub_repository = ToolHubRepository(tool_hub_root)

    def get_overview(self) -> dict[str, object]:
        orders = self.repository.list_orders()
        return {
            "data": P5BuildOverview(
                metrics=P5BuildMetrics(
                    order_count=len(orders),
                    draft_count=sum(1 for order in orders if order.status == "draft"),
                    exported_with_gaps_count=sum(1 for order in orders if order.status == "exported_with_gaps"),
                    completed_count=sum(1 for order in orders if order.status == "completed"),
                    failed_count=sum(1 for order in orders if order.status == "failed"),
                ),
                recent_orders=[
                    P5DeliveryOrderSummary(
                        delivery_order_id=order.delivery_order_id,
                        p3_order_id=order.p3_order_id,
                        application_name=order.application_name,
                        status=order.status,
                        current_attempt_count=order.current_attempt_count,
                        updated_at=order.updated_at,
                    )
                    for order in orders[:5]
                ],
            )
        }

    def list_orders(self) -> dict[str, object]:
        return {
            "data": {
                "items": [
                    P5DeliveryOrderSummary(
                        delivery_order_id=order.delivery_order_id,
                        p3_order_id=order.p3_order_id,
                        application_name=order.application_name,
                        status=order.status,
                        current_attempt_count=order.current_attempt_count,
                        updated_at=order.updated_at,
                    )
                    for order in self.repository.list_orders()
                ]
            }
        }

    def list_design_inputs(self) -> dict[str, object]:
        return {"data": {"items": self.repository.list_design_inputs()}}

    def list_supply_inputs(self) -> dict[str, object]:
        return {"data": {"items": self.repository.list_supply_inputs()}}

    def get_order_detail(self, delivery_order_id: str) -> P5DeliveryOrderDetail:
        order = self.repository.get_order(delivery_order_id)
        if order is None:
            raise ValueError("P5 delivery order not found")
        return P5DeliveryOrderDetail(**order.model_dump(mode="json"), attempts=self.repository.list_attempts(delivery_order_id))

    def create_simulated_design_input(self, payload: P5DesignInputSimCreate) -> P5DesignInputSource:
        timestamp = now_iso()
        design_input_id = f"design-input-{uuid4().hex[:12]}"
        source = P5DesignInputSource(
            design_input_id=design_input_id,
            source_kind="xx_p3_doc_sim",
            source_ref_id=f"xx/P3/DOC/sim:{design_input_id}",
            application_name=payload.application_name,
            requirement_spec_id=payload.requirement_spec_id,
            baseline_id=payload.baseline_id,
            notes=payload.notes,
            module_count=len(payload.module_specs),
            module_names=[module.name for module in payload.module_specs],
            modules=payload.module_specs,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_design_input(source)

    def create_simulated_supply_input(self, payload: P5SupplyInputSimCreate) -> P5SupplyInputSource:
        timestamp = now_iso()
        supply_input_id = f"supply-input-{uuid4().hex[:12]}"
        source = P5SupplyInputSource(
            supply_input_id=supply_input_id,
            source_kind="xx_p4_supply_sim",
            source_ref_id=f"xx/P4/sim:{supply_input_id}",
            snapshot_name=payload.snapshot_name,
            notes=payload.notes,
            tool_count=len(payload.tools),
            tool_names=[tool.tool_name for tool in payload.tools],
            tools=payload.tools,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_supply_input(source)

    def create_delivery_order(self, payload: P5DeliveryOrderCreate) -> P5DeliveryOrder:
        design_input = self._resolve_design_input_for_order(payload)
        if payload.p3_order_id:
            existing = self.repository.get_order_by_p3_order_id(payload.p3_order_id)
            if existing is not None:
                raise ValueError(f"P5 delivery order already exists for P3 order {payload.p3_order_id}")
        elif self.repository.get_order_by_design_input_id(design_input.design_input_id) is not None:
            raise ValueError(f"P5 delivery order already exists for design input {design_input.design_input_id}")

        timestamp = now_iso()
        delivery_order_id = f"p5-order-{uuid4().hex[:12]}"
        order = P5DeliveryOrder(
            delivery_order_id=delivery_order_id,
            p3_order_id=design_input.p3_order_id or f"xx/P3/DOC/sim:{design_input.design_input_id}",
            requirement_spec_id=design_input.requirement_spec_id,
            application_name=design_input.application_name,
            requested_by=payload.requested_by,
            notes=payload.notes,
            status="draft",
            current_attempt_count=0,
            formal_result_ready=False,
            active_input_binding=self._build_initial_binding(delivery_order_id, design_input.design_input_id),
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_order(order)

    def confirm_input_binding(
        self,
        delivery_order_id: str,
        payload: P5InputBindingConfirmRequest,
    ) -> P5InputBinding:
        order = self._require_order(delivery_order_id)
        if order.active_input_binding.design_input_id != payload.design_input_id:
            raise ValueError("Design input does not match delivery order")

        if payload.supply_mode == "snapshot":
            if not payload.supply_input_id:
                raise ValueError("P5 supply input is required for snapshot mode")
            if self.repository.get_supply_input(payload.supply_input_id) is None:
                raise ValueError("P5 supply input not found")
        else:
            payload = payload.model_copy(update={"supply_input_id": None})

        binding = order.active_input_binding.model_copy(
            update={
                "supply_input_id": payload.supply_input_id,
                "supply_mode": payload.supply_mode,
                "is_confirmed": True,
                "confirmed_by": payload.confirmed_by,
                "confirmed_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        order = order.model_copy(update={"active_input_binding": binding, "updated_at": now_iso()})
        self.repository.save_order(order)
        return binding

    def update_module_binding(
        self,
        delivery_order_id: str,
        module_id: str,
        payload: P5ModuleBindingUpdate,
    ) -> P5InputBinding:
        order = self._require_order(delivery_order_id)
        binding = order.active_input_binding
        design_input = self._require_design_input(binding.design_input_id)
        if not any(module.module_id == module_id for module in design_input.modules):
            raise ValueError("P5 design module not found")
        if binding.supply_mode != "snapshot" or not binding.supply_input_id:
            raise ValueError("P5 supply input snapshot is not active")
        supply_input = self._require_supply_input(binding.supply_input_id)
        tool = self._find_supply_tool(supply_input, payload.tool_id)
        if tool is None:
            raise ValueError("P5 supply tool not found")

        current_bindings = {item.module_id: item for item in binding.module_bindings}
        current_bindings[module_id] = P5ModuleBindingDecision(
            module_id=module_id,
            tool_id=tool.tool_id,
            tool_name=tool.tool_name,
            updated_by=payload.updated_by,
        )
        updated_binding = binding.model_copy(
            update={
                "module_bindings": list(current_bindings.values()),
                "updated_at": now_iso(),
            }
        )
        updated_order = order.model_copy(update={"active_input_binding": updated_binding, "updated_at": now_iso()})
        self.repository.save_order(updated_order)
        return updated_binding

    def create_attempt(self, delivery_order_id: str, payload: P5AssemblyAttemptCreate) -> P5AssemblyAttempt:
        order = self._require_order(delivery_order_id)
        binding = order.active_input_binding
        if not binding.is_confirmed:
            raise ValueError("P5 input binding is not confirmed")

        design_input = self._require_design_input(binding.design_input_id)
        supply_input = self._load_bound_supply_input(binding)
        sequence = len(self.repository.list_attempts(delivery_order_id)) + 1
        assembly_modules = self._build_assembly_modules(design_input, supply_input, binding)
        assembly_plan = P5AssemblyPlan(modules=assembly_modules)
        input_snapshot = self._build_input_snapshot(design_input, supply_input, assembly_modules)
        gaps = self._build_gap_records(assembly_modules)
        feedback_tasks = self._build_feedback_tasks(gaps)
        final_status = "exported_with_gaps" if gaps else "completed"
        validation_report = P5ValidationReport(
            module_closure_status="warning" if gaps else "passed",
            structure_status="passed",
            build_status="warning" if gaps else "passed",
            summary="存在缺口，占位导出已完成。" if gaps else "模块绑定与目录导出通过。",
        )
        runtime_snapshot = self._build_runtime_snapshot(order, final_status, assembly_plan, gaps)
        export_config = P5ExportConfig(
            export_root=payload.export_root,
            build_profile=payload.build_profile,
            attempt_note=payload.attempt_note,
        )
        export_directory = Path(export_config.export_root) / order.delivery_order_id / f"attempt-{sequence:03d}"
        output_preview = self._build_output_preview(export_directory, gaps)
        self._export_attempt_directory(
            export_directory=export_directory,
            order=order,
            sequence=sequence,
            binding=binding,
            input_snapshot=input_snapshot,
            assembly_plan=assembly_plan,
            runtime_snapshot=runtime_snapshot,
            validation_report=validation_report,
            output_preview=output_preview,
            gaps=gaps,
            feedback_tasks=feedback_tasks,
        )

        timestamp = now_iso()
        attempt = P5AssemblyAttempt(
            attempt_id=f"attempt-{uuid4().hex[:12]}",
            delivery_order_id=delivery_order_id,
            sequence=sequence,
            export_config=export_config,
            input_snapshot=input_snapshot,
            assembly_plan=assembly_plan,
            runtime_snapshot=runtime_snapshot,
            validation_report=validation_report,
            output_preview=output_preview,
            gaps=gaps,
            feedback_tasks=feedback_tasks,
            export_directory=str(export_directory),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.repository.save_attempt(attempt)
        self.repository.save_order(
            order.model_copy(
                update={
                    "status": final_status,
                    "current_attempt_count": sequence,
                    "formal_result_ready": not gaps,
                    "updated_at": now_iso(),
                }
            )
        )
        return attempt

    def review_feedback_task(
        self,
        delivery_order_id: str,
        attempt_id: str,
        task_id: str,
        payload: P5FeedbackTaskReview,
    ) -> P5FeedbackTask:
        self._require_order(delivery_order_id)
        attempt = self.repository.get_attempt(attempt_id)
        if attempt is None or attempt.delivery_order_id != delivery_order_id:
            raise ValueError("P5 assembly attempt not found")

        updated_task: P5FeedbackTask | None = None
        next_tasks: list[P5FeedbackTask] = []
        for task in attempt.feedback_tasks:
            if task.task_id != task_id:
                next_tasks.append(task)
                continue
            updated_task = task.model_copy(
                update={
                    "status": payload.decision,
                    "reviewed_by": payload.reviewed_by,
                    "reviewed_at": now_iso(),
                    "review_note": payload.review_note,
                }
            )
            next_tasks.append(updated_task)

        if updated_task is None:
            raise ValueError("P5 feedback task not found")

        self.repository.save_attempt(attempt.model_copy(update={"feedback_tasks": next_tasks, "updated_at": now_iso()}))
        return updated_task

    def clear_delivery_runtime_for_testing(self) -> P5DeliveryRuntimeClearResult:
        export_directories = {
            Path(attempt.export_directory)
            for attempt in self.repository.list_attempts()
            if attempt.export_directory
        }
        default_export_root = self.repository.root.parent / "software_build_exports"
        if default_export_root.exists():
            export_directories.update(
                path
                for path in default_export_root.rglob("*")
                if path.is_dir() and path.name.startswith("attempt-")
            )

        cleared_order_count, cleared_attempt_count = self.repository.clear_delivery_runtime()
        cleared_export_directory_count = 0
        for export_directory in sorted(export_directories, key=lambda path: len(path.parts), reverse=True):
            if not export_directory.exists():
                continue
            shutil.rmtree(export_directory, ignore_errors=True)
            cleared_export_directory_count += 1
            parent_directory = export_directory.parent
            while parent_directory.exists() and parent_directory != parent_directory.parent:
                try:
                    parent_directory.rmdir()
                except OSError:
                    break
                if parent_directory.name == "software_build_exports":
                    break
                parent_directory = parent_directory.parent

        return P5DeliveryRuntimeClearResult(
            cleared_order_count=cleared_order_count,
            cleared_attempt_count=cleared_attempt_count,
            cleared_export_directory_count=cleared_export_directory_count,
        )

    def bootstrap_demo(self, payload: P5WorkspaceBootstrapRequest) -> P5WorkspaceBootstrapResult:
        created_demo_inputs = self._ensure_demo_inputs()
        order = self.repository.get_order_by_design_input_id(DEMO_DESIGN_INPUT_ID)
        if order is None:
            order = self.create_delivery_order(
                P5DeliveryOrderCreate(
                    design_input_id=DEMO_DESIGN_INPUT_ID,
                    requested_by="P5-bootstrap",
                    notes="基于地理信息系统的通视分析软件样例主单",
                )
            )

        self.confirm_input_binding(
            order.delivery_order_id,
            P5InputBindingConfirmRequest(
                design_input_id=DEMO_DESIGN_INPUT_ID,
                supply_input_id=DEMO_SUPPLY_INPUT_ID,
                supply_mode="snapshot",
                confirmed_by="P5-bootstrap",
            ),
        )
        attempt = self.create_attempt(
            order.delivery_order_id,
            P5AssemblyAttemptCreate(
                export_root=payload.export_root,
                build_profile=payload.build_profile,
                attempt_note=payload.attempt_note,
            ),
        )
        return P5WorkspaceBootstrapResult(
            delivery_order_id=order.delivery_order_id,
            attempt_id=attempt.attempt_id,
            created_demo_inputs=created_demo_inputs,
        )

    def _resolve_design_input_for_order(self, payload: P5DeliveryOrderCreate) -> P5DesignInputSource:
        if bool(payload.p3_order_id) == bool(payload.design_input_id):
            raise ValueError("Provide exactly one of p3_order_id or design_input_id")
        if payload.design_input_id:
            return self._require_design_input(payload.design_input_id)
        return self._register_p3_design_input(payload.p3_order_id or "")

    def _register_p3_design_input(self, p3_order_id: str) -> P5DesignInputSource:
        design_input_id = f"design-input-p3-{p3_order_id}"
        existing = self.repository.get_design_input(design_input_id)
        if existing is not None:
            return existing

        design_order = self.software_design_repository.get_order(p3_order_id)
        if design_order is None:
            raise ValueError("P3 order not found")
        if design_order.status not in {"frozen", "package_ready", "pushed_to_p4"}:
            raise ValueError("P3 order is not frozen for delivery")
        baseline = self.software_design_repository.get_baseline(p3_order_id)
        if baseline is None:
            raise ValueError("Software design baseline not found")

        timestamp = now_iso()
        design_input = P5DesignInputSource(
            design_input_id=design_input_id,
            source_kind="p3_baseline",
            source_ref_id=design_order.order_id,
            p3_order_id=design_order.order_id,
            application_name=design_order.application_name,
            requirement_spec_id=design_order.requirement_spec_id,
            baseline_id=baseline.baseline_id,
            module_count=len(baseline.modules),
            module_names=[module.name for module in baseline.modules],
            modules=baseline.modules,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_design_input(design_input)

    def _build_initial_binding(self, delivery_order_id: str, design_input_id: str) -> P5InputBinding:
        return P5InputBinding(
            binding_id=f"binding-{uuid4().hex[:12]}",
            delivery_order_id=delivery_order_id,
            design_input_id=design_input_id,
            supply_mode="empty",
            is_confirmed=False,
        )

    def _build_assembly_modules(
        self,
        design_input: P5DesignInputSource,
        supply_input: P5SupplyInputSource | None,
        binding: P5InputBinding,
    ) -> list[P5AssemblyModule]:
        manual_bindings = {item.module_id: item for item in binding.module_bindings}
        modules: list[P5AssemblyModule] = []
        for module in design_input.modules:
            target_directories = self._infer_target_directories(module)
            manual_binding = manual_bindings.get(module.module_id)
            if manual_binding and supply_input:
                tool = self._find_supply_tool(supply_input, manual_binding.tool_id)
                if tool is not None:
                    modules.append(
                        P5AssemblyModule(
                            module_id=module.module_id,
                            name=module.name,
                            objective=module.objective,
                            target_directories=target_directories,
                            binding_status="bound",
                            binding_source="manual",
                            bound_tool_id=tool.tool_id,
                            bound_tool_name=tool.tool_name,
                        )
                    )
                    continue

            matched_tool = self._match_tool(module.recommended_tools, supply_input)
            if matched_tool is not None:
                modules.append(
                    P5AssemblyModule(
                        module_id=module.module_id,
                        name=module.name,
                        objective=module.objective,
                        target_directories=target_directories,
                        binding_status="bound",
                        binding_source="heuristic",
                        bound_tool_id=matched_tool.tool_id,
                        bound_tool_name=matched_tool.tool_name,
                    )
                )
                continue

            gap_reason = (
                "当前供给输入为空，当前按缺口占位继续导出。"
                if binding.supply_mode == "empty"
                else "未命中当前供给快照资产，当前按缺口占位继续导出。"
            )
            modules.append(
                P5AssemblyModule(
                    module_id=module.module_id,
                    name=module.name,
                    objective=module.objective,
                    target_directories=target_directories,
                    binding_status="placeholder",
                    binding_source="empty",
                    gap_reason=gap_reason,
                )
            )
        return modules

    def _build_gap_records(self, assembly_modules: list[P5AssemblyModule]) -> list[P5GapRecord]:
        return [
            P5GapRecord(
                gap_id=f"gap-{uuid4().hex[:12]}",
                kind="supply_gap",
                module_id=module.module_id,
                module_name=module.name,
                summary=f"{module.name} 未命中已供给资产",
                detail=module.gap_reason or "当前模块没有绑定到 P4 已审定 / 已供给资产。",
            )
            for module in assembly_modules
            if module.binding_status == "placeholder"
        ]

    def _build_feedback_tasks(self, gaps: list[P5GapRecord]) -> list[P5FeedbackTask]:
        return [
            P5FeedbackTask(
                task_id=f"feedback-{uuid4().hex[:12]}",
                gap_id=gap.gap_id,
                kind=gap.kind,
                title=f"回流确认：{gap.summary}",
                detail=f"{gap.detail}。默认回流到 P3 仲裁。",
            )
            for gap in gaps
        ]

    def _build_input_snapshot(
        self,
        design_input: P5DesignInputSource,
        supply_input: P5SupplyInputSource | None,
        assembly_modules: list[P5AssemblyModule],
    ) -> P5InputSnapshot:
        return P5InputSnapshot(
            design_input=P5DesignInputSnapshot(
                source_kind=design_input.source_kind,
                design_input_id=design_input.design_input_id,
                order_id=design_input.p3_order_id or design_input.source_ref_id,
                baseline_id=design_input.baseline_id,
                module_count=design_input.module_count,
                module_names=design_input.module_names,
            ),
            supply_input=P5SupplyInputSnapshot(
                source_kind=supply_input.source_kind if supply_input else "empty_supply",
                supply_input_id=supply_input.supply_input_id if supply_input else None,
                tool_count=supply_input.tool_count if supply_input else 0,
                tool_names=supply_input.tool_names if supply_input else [],
                matched_tool_count=sum(1 for module in assembly_modules if module.binding_status == "bound"),
            ),
        )

    def _build_runtime_snapshot(
        self,
        order: P5DeliveryOrder,
        final_status: str,
        assembly_plan: P5AssemblyPlan,
        gaps: list[P5GapRecord],
    ) -> P5RuntimeSnapshot:
        bound_count = sum(1 for module in assembly_plan.modules if module.binding_status == "bound")
        placeholder_count = len(assembly_plan.modules) - bound_count
        recent_logs = [
            P5RuntimeLog(message=f"{order.delivery_order_id} 已接收当前输入绑定快照。"),
            P5RuntimeLog(message=f"完成模块投影，共 {len(assembly_plan.modules)} 个模块。"),
        ]
        if gaps:
            recent_logs.append(
                P5RuntimeLog(
                    level="warning",
                    message=f"发现 {len(gaps)} 个供给缺口，已按占位目录继续导出。",
                )
            )
        else:
            recent_logs.append(P5RuntimeLog(message="全部模块已命中供给资产，导出完成。"))

        return P5RuntimeSnapshot(
            executor_name="p5-mvp-executor",
            executor_status="completed",
            attempt_status=final_status,
            progress_percent=100,
            stages=[
                P5RuntimeStage(
                    stage_id="intake",
                    label="接收输入",
                    status="completed",
                    detail="已冻结当前设计输入与供给输入快照。",
                ),
                P5RuntimeStage(
                    stage_id="projection",
                    label="装配投影",
                    status="warning" if gaps else "completed",
                    detail=f"已绑定 {bound_count} 个模块，保留 {placeholder_count} 个占位模块。",
                ),
                P5RuntimeStage(
                    stage_id="export",
                    label="导出目录",
                    status="completed",
                    detail="已生成 frontend/backend/deploy/docs 目录结构。",
                ),
                P5RuntimeStage(
                    stage_id="feedback",
                    label="缺口回流",
                    status="warning" if gaps else "completed",
                    detail="已生成 gap-list 与反馈任务留痕。",
                ),
            ],
            recent_logs=recent_logs,
            block_reason=gaps[0].summary if gaps else None,
        )

    def _build_output_preview(self, export_directory: Path, gaps: list[P5GapRecord]) -> P5OutputPreview:
        gap_status = "generated_with_gaps" if gaps else "generated"
        return P5OutputPreview(
            root_directory=str(export_directory),
            directories=["frontend", "backend", "deploy", "docs"],
            key_files=[
                P5OutputArtifact(
                    path="build-manifest.json",
                    kind="file",
                    status="generated",
                    summary="导出目录元数据与 attempt 快照。",
                ),
                P5OutputArtifact(
                    path="docs/delivery-report.md",
                    kind="file",
                    status="generated",
                    summary="说明本次交付模块投影与构建结论。",
                ),
                P5OutputArtifact(
                    path="docs/gap-list.md",
                    kind="file",
                    status=gap_status,
                    summary="说明当前缺口、占位模块和回流建议。",
                ),
            ],
        )

    def _export_attempt_directory(
        self,
        export_directory: Path,
        order: P5DeliveryOrder,
        sequence: int,
        binding: P5InputBinding,
        input_snapshot: P5InputSnapshot,
        assembly_plan: P5AssemblyPlan,
        runtime_snapshot: P5RuntimeSnapshot,
        validation_report: P5ValidationReport,
        output_preview: P5OutputPreview,
        gaps: list[P5GapRecord],
        feedback_tasks: list[P5FeedbackTask],
    ) -> None:
        for directory_name in ("frontend", "backend", "deploy", "docs"):
            (export_directory / directory_name).mkdir(parents=True, exist_ok=True)

        (export_directory / "frontend" / "README.md").write_text(
            "# Frontend\n\n当前为 P5 首版导出占位目录。\n",
            encoding="utf-8",
        )
        (export_directory / "backend" / "README.md").write_text(
            "# Backend\n\n当前为 P5 首版导出占位目录。\n",
            encoding="utf-8",
        )
        (export_directory / "deploy" / "README.md").write_text(
            "# Deploy\n\n当前为 P5 首版部署占位目录。\n",
            encoding="utf-8",
        )
        (export_directory / "docs" / "delivery-report.md").write_text(
            self._build_delivery_report(order, sequence, input_snapshot, assembly_plan, validation_report),
            encoding="utf-8",
        )
        (export_directory / "docs" / "gap-list.md").write_text(self._build_gap_report(gaps, feedback_tasks), encoding="utf-8")
        manifest = {
            "delivery_order_id": order.delivery_order_id,
            "p3_order_id": order.p3_order_id,
            "sequence": sequence,
            "application_name": order.application_name,
            "active_input_binding": binding.model_dump(mode="json"),
            "input_snapshot": input_snapshot.model_dump(mode="json"),
            "directories": output_preview.directories,
            "modules": [module.model_dump(mode="json") for module in assembly_plan.modules],
            "runtime_snapshot": runtime_snapshot.model_dump(mode="json"),
            "validation_report": validation_report.model_dump(mode="json"),
            "output_preview": output_preview.model_dump(mode="json"),
            "gaps": [gap.model_dump(mode="json") for gap in gaps],
            "feedback_tasks": [task.model_dump(mode="json") for task in feedback_tasks],
        }
        (export_directory / "build-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_delivery_report(
        self,
        order: P5DeliveryOrder,
        sequence: int,
        input_snapshot: P5InputSnapshot,
        assembly_plan: P5AssemblyPlan,
        validation_report: P5ValidationReport,
    ) -> str:
        module_lines = "\n".join(
            [
                f"- {module.name}: {module.binding_status}/{module.binding_source} -> {', '.join(module.target_directories)}"
                for module in assembly_plan.modules
            ]
        )
        return (
            f"# Delivery Report\n\n"
            f"- delivery_order_id: {order.delivery_order_id}\n"
            f"- p3_order_id: {order.p3_order_id}\n"
            f"- sequence: {sequence}\n"
            f"- design_module_count: {input_snapshot.design_input.module_count}\n"
            f"- supply_tool_count: {input_snapshot.supply_input.tool_count}\n"
            f"- module_closure_status: {validation_report.module_closure_status}\n"
            f"- structure_status: {validation_report.structure_status}\n"
            f"- build_status: {validation_report.build_status}\n\n"
            f"## Modules\n{module_lines}\n"
        )

    def _build_gap_report(self, gaps: list[P5GapRecord], feedback_tasks: list[P5FeedbackTask]) -> str:
        if not gaps:
            return "# Gap List\n\nNo gaps.\n"
        gap_lines = "\n".join([f"- {gap.kind} | {gap.module_name}: {gap.summary}" for gap in gaps])
        task_lines = "\n".join([f"- {task.status} | {task.title}" for task in feedback_tasks])
        return f"# Gap List\n\n## Gaps\n{gap_lines}\n\n## Feedback Tasks\n{task_lines}\n"

    def _infer_target_directories(self, module) -> list[str]:
        directories = ["frontend", "backend", "docs"]
        normalized_tokens = " ".join([module.name, module.objective, *module.outputs, *module.constraints]).lower()
        if any(token in normalized_tokens for token in ("deploy", "部署", "runtime", "运行")):
            directories.append("deploy")
        return list(dict.fromkeys(directories))

    def _match_tool(self, recommended_tools: list[str], supply_input: P5SupplyInputSource | None) -> P5SupplyInputTool | None:
        if supply_input is None:
            return None
        normalized_targets = {item.replace("_", "-").lower() for item in recommended_tools}
        normalized_targets.update({item.lower() for item in recommended_tools})
        for tool in supply_input.tools:
            candidates = {
                tool.tool_id.lower(),
                tool.tool_slug.lower(),
                tool.tool_name.lower(),
                *[keyword.lower() for keyword in tool.keywords],
            }
            if normalized_targets & candidates and tool.verification_status == "verified":
                return tool
        return None

    def _find_supply_tool(self, supply_input: P5SupplyInputSource, tool_id: str) -> P5SupplyInputTool | None:
        for tool in supply_input.tools:
            if tool.tool_id == tool_id and tool.verification_status == "verified":
                return tool
        return None

    def _load_bound_supply_input(self, binding: P5InputBinding) -> P5SupplyInputSource | None:
        if binding.supply_mode == "empty":
            return None
        if not binding.supply_input_id:
            raise ValueError("P5 supply input not found")
        return self._require_supply_input(binding.supply_input_id)

    def _require_order(self, delivery_order_id: str) -> P5DeliveryOrder:
        order = self.repository.get_order(delivery_order_id)
        if order is None:
            raise ValueError("P5 delivery order not found")
        return order

    def _require_design_input(self, design_input_id: str) -> P5DesignInputSource:
        design_input = self.repository.get_design_input(design_input_id)
        if design_input is None:
            raise ValueError("P5 design input not found")
        return design_input

    def _require_supply_input(self, supply_input_id: str) -> P5SupplyInputSource:
        supply_input = self.repository.get_supply_input(supply_input_id)
        if supply_input is None:
            raise ValueError("P5 supply input not found")
        return supply_input

    def _ensure_demo_inputs(self) -> bool:
        created = False
        timestamp = now_iso()
        if self.repository.get_design_input(DEMO_DESIGN_INPUT_ID) is None:
            self.repository.save_design_input(
                P5DesignInputSource(
                    design_input_id=DEMO_DESIGN_INPUT_ID,
                    source_kind="xx_p3_doc_sim",
                    source_ref_id=DEMO_P3_SOURCE_REF,
                    application_name=DEMO_APPLICATION_NAME,
                    requirement_spec_id=DEMO_REQUIREMENT_SPEC_ID,
                    baseline_id=DEMO_BASELINE_ID,
                    notes="基于地理信息系统的通视分析软件冻结设计样例",
                    module_count=2,
                    module_names=["构建任务编排", "构建缺口回流"],
                    modules=[
                        self._demo_module(
                            module_id="module-assembly-board",
                            name="构建任务编排",
                            objective="驱动主单到 attempt 的最小装配与执行流。",
                            recommended_tools=["ui_shell"],
                            outputs=["attempt_manifest"],
                            constraints=["关键阶段需可回看"],
                        ),
                        self._demo_module(
                            module_id="module-gap-feedback",
                            name="构建缺口回流",
                            objective="沉淀缺口、反馈任务和回流建议。",
                            recommended_tools=["gap_reporter"],
                            outputs=["gap_feedback"],
                            constraints=["回流说明需结构化输出"],
                        ),
                    ],
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            created = True

        if self.repository.get_supply_input(DEMO_SUPPLY_INPUT_ID) is None:
            self.repository.save_supply_input(
                P5SupplyInputSource(
                    supply_input_id=DEMO_SUPPLY_INPUT_ID,
                    source_kind="xx_p4_supply_sim",
                    source_ref_id="xx/P4/sim:demo",
                    snapshot_name="通视分析软件供给样例快照",
                    notes="供通视分析软件样例命中使用",
                    tool_count=1,
                    tool_names=["UI Shell"],
                    tools=[
                        P5SupplyInputTool(
                            tool_id="tool-ui-shell",
                            tool_name="UI Shell",
                            tool_slug="ui-shell",
                            verification_status="verified",
                            keywords=["ui_shell", "编排", "attempt"],
                        )
                    ],
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            created = True

        return created

    def _demo_module(
        self,
        module_id: str,
        name: str,
        objective: str,
        recommended_tools: list[str],
        outputs: list[str],
        constraints: list[str],
    ) -> DesignModule:
        return DesignModule(
            module_id=module_id,
            name=name,
            objective=objective,
            inputs=["delivery_order"],
            outputs=outputs,
            constraints=constraints,
            recommended_tools=recommended_tools,
        )
