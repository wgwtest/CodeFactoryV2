from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.software_build.models import (
    P5AssemblyAttempt,
    P5AssemblyAttemptCreate,
    P5AssemblyModule,
    P5AssemblyPlan,
    P5BuildMetrics,
    P5BuildOverview,
    P5DeliveryOrder,
    P5DeliveryOrderCreate,
    P5DeliveryOrderDetail,
    P5DeliveryOrderSummary,
    P5DesignInputSnapshot,
    P5ExportConfig,
    P5FeedbackTask,
    P5GapRecord,
    P5InputSnapshot,
    P5OutputArtifact,
    P5OutputPreview,
    P5RuntimeLog,
    P5RuntimeSnapshot,
    P5RuntimeStage,
    P5SupplyInputSnapshot,
    P5ValidationReport,
    P5WorkspaceBootstrapRequest,
    P5WorkspaceBootstrapResult,
    now_iso,
)
from app.software_build.repository import SoftwareBuildRepository
from app.software_design.models import DesignModule, DesignSection, P3Order, SoftwareDesignBaseline
from app.software_design.repository import SoftwareDesignRepository
from app.tool_hub.models import ToolDefinition, ToolVerification
from app.tool_hub.repository import ToolHubRepository

DEMO_P3_ORDER_ID = "p3-order-demo-001"
DEMO_REQUIREMENT_SPEC_ID = "spec-p5-demo-001"
DEMO_BASELINE_ID = "baseline-p5-demo-001"
DEMO_TOOL_ID = "tool-workflow-engine"


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

    def get_order_detail(self, delivery_order_id: str) -> P5DeliveryOrderDetail:
        order = self.repository.get_order(delivery_order_id)
        if order is None:
            raise ValueError("P5 delivery order not found")
        return P5DeliveryOrderDetail(**order.model_dump(mode="json"), attempts=self.repository.list_attempts(delivery_order_id))

    def create_delivery_order(self, payload: P5DeliveryOrderCreate) -> P5DeliveryOrder:
        design_order = self.software_design_repository.get_order(payload.p3_order_id)
        if design_order is None:
            raise ValueError("P3 order not found")
        if design_order.status not in {"frozen", "package_ready", "pushed_to_p4"}:
            raise ValueError("P3 order is not frozen for delivery")
        if self.software_design_repository.get_baseline(payload.p3_order_id) is None:
            raise ValueError("Software design baseline not found")
        existing = self.repository.get_order_by_p3_order_id(payload.p3_order_id)
        if existing is not None:
            raise ValueError(f"P5 delivery order already exists for P3 order {payload.p3_order_id}")

        timestamp = now_iso()
        order = P5DeliveryOrder(
            delivery_order_id=f"p5-order-{uuid4().hex[:12]}",
            p3_order_id=design_order.order_id,
            requirement_spec_id=design_order.requirement_spec_id,
            application_name=design_order.application_name,
            requested_by=payload.requested_by,
            notes=payload.notes,
            status="draft",
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_order(order)

    def bootstrap_demo(self, payload: P5WorkspaceBootstrapRequest) -> P5WorkspaceBootstrapResult:
        created_demo_inputs = self._ensure_demo_inputs()
        order = self.repository.get_order_by_p3_order_id(DEMO_P3_ORDER_ID)
        if order is None:
            order = self.create_delivery_order(
                P5DeliveryOrderCreate(
                    p3_order_id=DEMO_P3_ORDER_ID,
                    requested_by="P5-bootstrap",
                    notes="P5.1 最小闭环演示主单",
                )
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

    def create_attempt(self, delivery_order_id: str, payload: P5AssemblyAttemptCreate) -> P5AssemblyAttempt:
        order = self.repository.get_order(delivery_order_id)
        if order is None:
            raise ValueError("P5 delivery order not found")
        baseline = self.software_design_repository.get_baseline(order.p3_order_id)
        if baseline is None:
            raise ValueError("Software design baseline not found")

        available_tools = self.tool_hub_repository.list_tools()
        sequence = len(self.repository.list_attempts(delivery_order_id)) + 1
        assembly_modules: list[P5AssemblyModule] = []
        for module in baseline.modules:
            matched_tool = self._match_tool(module.recommended_tools)
            target_directories = self._infer_target_directories(module)
            if matched_tool is not None:
                assembly_modules.append(
                    P5AssemblyModule(
                        module_id=module.module_id,
                        name=module.name,
                        objective=module.objective,
                        target_directories=target_directories,
                        binding_status="bound",
                        bound_tool_id=matched_tool.tool_id,
                        bound_tool_name=matched_tool.name,
                    )
                )
                continue

            assembly_modules.append(
                P5AssemblyModule(
                    module_id=module.module_id,
                    name=module.name,
                    objective=module.objective,
                    target_directories=target_directories,
                    binding_status="placeholder",
                    gap_reason="未命中 P4 已供给资产，当前按缺口占位继续导出。",
                )
            )

        assembly_plan = P5AssemblyPlan(modules=assembly_modules)
        input_snapshot = self._build_input_snapshot(order, baseline, available_tools, assembly_modules)
        gaps = [
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
        feedback_tasks = [
            P5FeedbackTask(
                task_id=f"feedback-{uuid4().hex[:12]}",
                gap_id=gap.gap_id,
                kind=gap.kind,
                title=f"回流确认：{gap.summary}",
                detail=f"{gap.detail}。默认回流到 P3 仲裁。",
            )
            for gap in gaps
        ]
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
            export_directory,
            order,
            sequence,
            input_snapshot,
            assembly_plan,
            runtime_snapshot,
            validation_report,
            output_preview,
            gaps,
            feedback_tasks,
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
        updated_order = order.model_copy(
            update={
                "current_attempt_count": sequence,
                "formal_result_ready": not gaps,
                "status": final_status,
                "updated_at": now_iso(),
            }
        )
        self.repository.save_order(updated_order)
        return attempt

    def _export_attempt_directory(
        self,
        export_directory: Path,
        order: P5DeliveryOrder,
        sequence: int,
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
                f"- {module.name}: {module.binding_status} -> {', '.join(module.target_directories)}"
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

    def _build_input_snapshot(
        self,
        order: P5DeliveryOrder,
        baseline: SoftwareDesignBaseline,
        available_tools: list[ToolDefinition],
        assembly_modules: list[P5AssemblyModule],
    ) -> P5InputSnapshot:
        is_demo_input = order.p3_order_id == DEMO_P3_ORDER_ID
        return P5InputSnapshot(
            design_input=P5DesignInputSnapshot(
                source_kind="demo_p3_baseline" if is_demo_input else "p3_baseline",
                order_id=order.p3_order_id,
                baseline_id=baseline.baseline_id,
                module_count=len(baseline.modules),
                module_names=[module.name for module in baseline.modules],
            ),
            supply_input=P5SupplyInputSnapshot(
                source_kind="demo_p4_supply" if is_demo_input else "p4_supply",
                tool_count=len(available_tools),
                tool_names=[tool.name for tool in available_tools[:6]],
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
            P5RuntimeLog(message=f"{order.delivery_order_id} 已接收 P3/P4 输入快照。"),
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
                    detail="已装载冻结 P3 基线与 P4 供给快照。",
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

    def _infer_target_directories(self, module: DesignModule) -> list[str]:
        directories = ["backend", "docs"]
        normalized_tokens = " ".join([module.name, module.objective, *module.outputs, *module.constraints]).lower()
        if any(token in normalized_tokens for token in ("ui", "页面", "前端", "展示", "portal")):
            directories.insert(0, "frontend")
        else:
            directories.insert(0, "frontend")
        if any(token in normalized_tokens for token in ("deploy", "部署", "runtime", "运行")):
            directories.append("deploy")
        return list(dict.fromkeys(directories))

    def _match_tool(self, recommended_tools: list[str]) -> ToolDefinition | None:
        normalized_targets = {item.replace("_", "-").lower() for item in recommended_tools}
        normalized_targets.update({item.lower() for item in recommended_tools})
        for tool in self.tool_hub_repository.list_tools():
            candidates = {
                tool.tool_id.lower(),
                tool.slug.lower(),
                tool.name.lower(),
                *[keyword.lower() for keyword in tool.keywords],
            }
            if normalized_targets & candidates:
                return tool
        return None

    def _ensure_demo_inputs(self) -> bool:
        created = False
        timestamp = now_iso()
        if self.software_design_repository.get_order(DEMO_P3_ORDER_ID) is None:
            self.software_design_repository.save_order(
                P3Order(
                    order_id=DEMO_P3_ORDER_ID,
                    requirement_spec_id=DEMO_REQUIREMENT_SPEC_ID,
                    application_name="P5 最小闭环演示系统",
                    domain_name="软件构建系统",
                    requirement_spec_status="ready",
                    requested_by="P5",
                    notes="P5.1 演示冻结设计",
                    status="frozen",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            created = True

        if self.software_design_repository.get_baseline(DEMO_P3_ORDER_ID) is None:
            self.software_design_repository.save_baseline(
                SoftwareDesignBaseline(
                    baseline_id=DEMO_BASELINE_ID,
                    order_id=DEMO_P3_ORDER_ID,
                    requirement_spec_id=DEMO_REQUIREMENT_SPEC_ID,
                    sections=[
                        DesignSection(
                            id="modules",
                            title="3. 模块划分与职责",
                            summary="P5.1 演示模块集合。",
                            body="包含一个已命中模块和一个缺口占位模块。",
                        )
                    ],
                    modules=[
                        DesignModule(
                            module_id="module-assembly-board",
                            name="构建任务编排",
                            objective="驱动主单到 attempt 的最小装配与执行流。",
                            inputs=["delivery_order"],
                            outputs=["attempt_manifest"],
                            constraints=["关键阶段需可回看"],
                            recommended_tools=["workflow_engine"],
                        ),
                        DesignModule(
                            module_id="module-gap-feedback",
                            name="构建缺口回流",
                            objective="沉淀缺口、反馈任务和回流建议。",
                            inputs=["attempt_manifest"],
                            outputs=["gap_feedback"],
                            constraints=["回流说明需结构化输出"],
                            recommended_tools=["gap_reporter"],
                        ),
                    ],
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            created = True

        if self.tool_hub_repository.get_tool(DEMO_TOOL_ID) is None:
            self.tool_hub_repository.save_tool(
                ToolDefinition(
                    tool_id=DEMO_TOOL_ID,
                    name="工作流引擎",
                    slug="workflow-engine",
                    status="active",
                    summary="承载主单装配与 attempt 推进。",
                    problem_statement="为 P5 最小闭环提供已供给的执行编排工具。",
                    primary_domain_id="workflow_approval",
                    tool_form_id="service_endpoint",
                    runtime_platform_ids=["agent_runtime"],
                    tags=["domain:workflow_approval", "form:service_endpoint"],
                    lifecycle_stage_ids=["solution_design"],
                    input_types=["structured_json"],
                    output_types=["structured_json"],
                    supported_sources=["tool_hub_snapshot"],
                    usage_notes="供 P5.1 演示工作台绑定命中使用。",
                    keywords=["workflow_engine", "编排", "attempt"],
                    verification=ToolVerification(status="verified"),
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            created = True

        return created
