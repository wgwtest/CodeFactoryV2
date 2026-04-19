from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import ClassVar
from uuid import uuid4

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.demand_fixtures import build_mock_blue_force_request, build_mock_demand_request
from app.tool_hub.demand_service import DemandService
from app.tool_hub.evolution_service import EvolutionService
from app.tool_hub.fixtures import (
    DOMAIN_CATALOG,
    INPUT_TYPE_CATALOG,
    OUTPUT_TYPE_CATALOG,
    LIFECYCLE_STAGE_CATALOG,
    SUPPORTED_SOURCE_CATALOG,
    TAG_NAMESPACE_CATALOG,
    TOOL_FORM_CATALOG,
    RUNTIME_PLATFORM_CATALOG,
    VERIFICATION_STATUS_CATALOG,
    demo_tools,
)
from app.tool_hub.manufacture_service import ManufactureService
from app.tool_hub.models import (
    EvolutionChangeSet,
    EvolutionConfigReadEnvelope,
    EvolutionConfigUpdateRequest,
    EvolutionFinding,
    EvolutionFindingDecisionRequest,
    EvolutionInspectionConfig,
    EvolutionRollbackRecord,
    EvolutionRunCreateRequest,
    EvolutionRun,
    EvolutionRunSummary,
    EvolutionRunReadEnvelope,
    EvolutionRuntimeState,
    EvolutionTask,
    EvolutionTaskEnvelope,
    EvolutionTaskReadEnvelope,
    EvolutionTaskRollbackRequest,
    ItemProgressView,
    ToolDefinition,
    ToolDefinitionWrite,
    ToolDemandItem,
    ToolDemandLifecycleEvent,
    ToolDemandNode,
    ToolDemandReviewDecisionRequest,
    ToolDemandSheet,
    ToolDemandSheetActionRequest,
    ToolDemandSheetCreateRequest,
    ToolDemandSheetDetail,
    ToolDemandSheetEnvelope,
    ToolDemandTestingClearResult,
    ToolFetchManifest,
    ToolHubCatalogs,
    ToolHubOverviewReadEnvelope,
    ToolHubStateSnapshot,
    ToolListEnvelope,
    ToolManufacturePlan,
    ToolManufacturePlanEnvelope,
    ToolManufacturePlanView,
    ToolRegistryDeleteResult,
    ToolRegistryTestingClearResult,
    ToolListReadEnvelope,
    ToolMatchCandidate,
    ToolMatchRequest,
    ToolMatchRun,
    ToolSupplyResult,
    ToolVerification,
    now_iso,
)
from app.tool_hub.repository import ToolHubRepository
from app.tool_hub.registry_service import RegistryService
from app.tool_hub.query_service import ToolHubQueryService
from app.tool_hub.runtime_repository import RuntimeRepository
from app.tool_hub.runtime_worker import ToolHubRuntimeCoordinator, ToolHubRuntimeWorker
from app.tool_hub.snapshot import (
    build_evolution_run,
    build_tool_hub_snapshot,
    project_evolution_runs,
    project_tool_hub_overview,
    project_tool_list,
)

TERMINAL_SHEET_LIFECYCLE_STATUSES = {"rejected", "withdrawn", "closed"}
DEFAULT_SIMULATION_PROFILE_WINDOWS = {
    "fast": (5, 300),
    "normal": (300, 3600),
    "slow": (3600, 7200),
}
MIN_SIMULATION_DURATION_SECONDS = 5
MAX_SIMULATION_DURATION_SECONDS = 2 * 60 * 60


class ToolHubService:
    _executor_registry: ClassVar[dict[str, ToolHubRuntimeCoordinator]] = {}
    _executor_registry_lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        root: str | Path,
        archive_service: ArchiveKnowledgeService,
        seed_demo_data: bool = True,
        enable_background_executor: bool = True,
        executor_tick_seconds: float = 0.1,
        simulation_profile_durations: dict[str, int | tuple[int, int]] | None = None,
        runtime_worker_id: str = "p4-runtime-worker",
    ) -> None:
        self.root = Path(root)
        self.repository = ToolHubRepository(self.root)
        self.runtime_repository = RuntimeRepository(self.root)
        self.archive_service = archive_service
        self.seed_demo_data = seed_demo_data
        self.executor_tick_seconds = executor_tick_seconds
        self.simulation_profile_durations = simulation_profile_durations or DEFAULT_SIMULATION_PROFILE_WINDOWS
        self.runtime_worker_id = runtime_worker_id
        self.query_service = ToolHubQueryService(self.repository)
        self.registry_service = RegistryService(self)
        self.demand_service = DemandService(self)
        self.manufacture_service = ManufactureService(self)
        self.evolution_service = EvolutionService(self)
        from app.tool_hub.runtime_service import ToolHubRuntimeService

        self.runtime_service = ToolHubRuntimeService(self, worker_id=runtime_worker_id)
        self._ensure_demo_data()
        if enable_background_executor:
            self._ensure_background_executor()

    def _ensure_background_executor(self) -> None:
        root_key = str(self.root.resolve())
        with self._executor_registry_lock:
            if root_key in self._executor_registry:
                return
            executor = ToolHubRuntimeCoordinator(
                worker_factory=lambda: ToolHubRuntimeWorker(
                    root=self.root,
                    archive_service=self.archive_service,
                    seed_demo_data=self.seed_demo_data,
                    worker_id=f"{self.runtime_worker_id}-background",
                    executor_tick_seconds=self.executor_tick_seconds,
                    simulation_profile_durations=self.simulation_profile_durations,
                ),
                interval_seconds=self.executor_tick_seconds,
            )
            self._executor_registry[root_key] = executor
            executor.start()

    def get_snapshot(self) -> ToolHubStateSnapshot:
        self._ensure_demo_data()
        return self.query_service.get_state_snapshot()

    def refresh_query_projections(self):
        self._ensure_demo_data()
        return self.query_service.refresh_core_projections()

    def get_overview(self) -> ToolHubOverviewReadEnvelope:
        projection = self.query_service.get_overview_projection()
        return ToolHubOverviewReadEnvelope(
            meta=projection.meta,
            data=projection.overview,
        )

    def get_catalogs(self) -> ToolHubCatalogs:
        return ToolHubCatalogs(
            domains=DOMAIN_CATALOG,
            lifecycle_stages=LIFECYCLE_STAGE_CATALOG,
            tool_forms=TOOL_FORM_CATALOG,
            runtime_platforms=RUNTIME_PLATFORM_CATALOG,
            input_types=INPUT_TYPE_CATALOG,
            output_types=OUTPUT_TYPE_CATALOG,
            supported_sources=SUPPORTED_SOURCE_CATALOG,
            verification_statuses=VERIFICATION_STATUS_CATALOG,
            tag_namespaces=TAG_NAMESPACE_CATALOG,
        )

    def list_tools(self) -> ToolListReadEnvelope:
        projection = self.query_service.get_tool_list_projection()
        return ToolListReadEnvelope(
            meta=projection.meta,
            data=ToolListEnvelope(items=projection.items),
        )

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        return self.registry_service.get_tool(tool_id)

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        return self.registry_service.create_tool(payload)

    def update_tool(self, tool_id: str, payload: ToolDefinitionWrite) -> ToolDefinition | None:
        return self.registry_service.update_tool(tool_id, payload)

    def delete_tool(self, tool_id: str) -> ToolRegistryDeleteResult | None:
        return self.registry_service.delete_tool(tool_id)

    def run_match(self, request: ToolMatchRequest) -> ToolMatchRun:
        self._ensure_demo_data()
        candidates = [
            self._score_tool(tool, request)
            for tool in self.repository.list_tools()
            if tool.status == "active"
        ]
        sorted_candidates = sorted(
            candidates,
            key=lambda item: (item.match_score, item.verification_status == "verified"),
            reverse=True,
        )
        run = ToolMatchRun(
            run_id=f"match-{uuid4().hex[:12]}",
            request=request,
            candidates=sorted_candidates,
            context_summary=self._build_context_summary(request),
        )
        saved = self.repository.save_match_run(run)
        self.refresh_query_projections()
        return saved

    def list_evolution_runs(self) -> EvolutionRunReadEnvelope:
        return self.evolution_service.list_evolution_runs()

    def get_evolution_run(self, run_id: str) -> EvolutionRun | None:
        return self.evolution_service.get_evolution_run(run_id)

    def get_evolution_config(self) -> EvolutionConfigReadEnvelope:
        return self.evolution_service.get_evolution_config()

    def update_evolution_config(
        self,
        payload: EvolutionConfigUpdateRequest | dict,
        *,
        actor_id: str,
    ) -> EvolutionInspectionConfig:
        updated = self.evolution_service.update_evolution_config(payload, actor_id=actor_id)
        self.refresh_query_projections()
        return updated

    def list_evolution_tasks(self) -> EvolutionTaskReadEnvelope:
        return self.evolution_service.list_evolution_tasks()

    def get_evolution_task(self, task_id: str) -> EvolutionTask | None:
        return self.evolution_service.get_evolution_task(task_id)

    def run_evolution(
        self,
        *,
        actor_id: str = "p4-system",
        trigger_type: str = "manual",
    ) -> EvolutionRun:
        run = self.evolution_service.run_evolution(actor_id=actor_id, trigger_type=trigger_type)
        self.refresh_query_projections()
        return run

    def decide_evolution_finding(
        self,
        finding_id: str,
        payload: EvolutionFindingDecisionRequest,
    ) -> EvolutionFinding | None:
        finding = self.evolution_service.decide_evolution_finding(finding_id, payload)
        self.refresh_query_projections()
        return finding

    def rollback_evolution_task(
        self,
        task_id: str,
        payload: EvolutionTaskRollbackRequest,
    ) -> EvolutionTask | None:
        task = self.evolution_service.rollback_evolution_task(task_id, payload)
        self.refresh_query_projections()
        return task

    def mark_evolution_dirty(self) -> EvolutionRuntimeState:
        state = self.evolution_service.mark_dirty()
        self.refresh_query_projections()
        return state

    def create_mock_blue_force_demand_sheet(self) -> ToolDemandSheetDetail:
        detail = self.demand_service.create_mock_blue_force_demand_sheet()
        self.refresh_query_projections()
        return detail

    def create_mock_demand_sheet(self, scenario_id: str) -> ToolDemandSheetDetail:
        detail = self.demand_service.create_mock_demand_sheet(scenario_id)
        self.refresh_query_projections()
        return detail

    def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
        detail = self.demand_service.create_demand_sheet(payload)
        self.refresh_query_projections()
        return detail

    def list_demand_sheets(self) -> ToolDemandSheetEnvelope:
        return self.demand_service.list_demand_sheets()

    def list_manufacture_plans(self) -> ToolManufacturePlanEnvelope:
        return self.manufacture_service.list_manufacture_plans()

    def get_demand_sheet(self, sheet_id: str) -> ToolDemandSheetDetail | None:
        return self.demand_service.get_demand_sheet(sheet_id)

    def get_demand_item(self, item_id: str) -> ToolDemandItem | None:
        return self.demand_service.get_demand_item(item_id)

    def review_demand_item(
        self,
        item_id: str,
        payload: ToolDemandReviewDecisionRequest,
    ) -> ToolDemandItem | None:
        item = self.demand_service.review_demand_item(item_id, payload)
        self.refresh_query_projections()
        return item

    def withdraw_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        detail = self.demand_service.withdraw_demand_sheet(sheet_id, payload)
        self.refresh_query_projections()
        return detail

    def reject_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        detail = self.demand_service.reject_demand_sheet(sheet_id, payload)
        self.refresh_query_projections()
        return detail

    def clear_demand_chain_for_testing(self) -> ToolDemandTestingClearResult:
        result = self.demand_service.clear_demand_chain_for_testing()
        self.refresh_query_projections()
        return result

    def clear_tool_registry_for_testing(self) -> ToolRegistryTestingClearResult:
        result = self.registry_service.clear_tool_registry_for_testing()
        self.refresh_query_projections()
        return result

    def run_runtime_cycle(self):
        return self.runtime_service.run_once()

    def run_scheduled_evolution_cycle(self) -> None:
        self.runtime_service._run_due_evolution_scan()

    def run_evolution_task_cycle(self) -> None:
        self.runtime_service._run_queue("p4-evolution", self.runtime_service._execute_evolution_job)

    def run_manufacture_executor_cycle(self) -> None:
        self.runtime_service._run_queue("p4-manufacture", self.runtime_service._execute_manufacture_job)

    def get_demand_item_progress(self, item_id: str) -> ItemProgressView | None:
        return self.demand_service.get_demand_item_progress(item_id)

    def get_tool_fetch_manifest(self, tool_id: str) -> ToolFetchManifest | None:
        return self.manufacture_service.get_tool_fetch_manifest(tool_id)

    def _transition_demand_sheet(
        self,
        *,
        sheet_id: str,
        event_type: str,
        actor_phase: str,
        actor_id: str,
        reason_code: str,
        reason_message: str,
    ) -> ToolDemandSheetDetail | None:
        sheet = self.repository.get_demand_sheet(sheet_id)
        if sheet is None:
            return None
        if sheet.lifecycle_status in TERMINAL_SHEET_LIFECYCLE_STATUSES:
            raise ValueError("Demand sheet is already in terminal status")
        if sheet.lifecycle_status not in {"submitted", "accepted"}:
            raise ValueError("Demand sheet cannot transition from current lifecycle status")

        updated = sheet.model_copy(
            update={
                "lifecycle_status": event_type,
                "lifecycle_events": [
                    *sheet.lifecycle_events,
                    self._build_lifecycle_event(
                        event_type=event_type,
                        actor_phase=actor_phase,
                        actor_id=actor_id,
                        from_status=sheet.lifecycle_status,
                        to_status=event_type,
                        reason_code=reason_code,
                        reason_message=reason_message,
                    ),
                ],
                "last_actor_phase": actor_phase,
                "last_actor_id": actor_id,
                "terminal_reason_code": reason_code,
                "terminal_reason_message": reason_message,
                "updated_at": now_iso(),
            }
        )
        self.repository.save_demand_sheet(updated)
        return self.get_demand_sheet(sheet_id)

    def _build_lifecycle_event(
        self,
        *,
        event_type: str,
        actor_phase: str,
        actor_id: str,
        from_status: str | None,
        to_status: str,
        reason_code: str,
        reason_message: str,
    ) -> ToolDemandLifecycleEvent:
        return ToolDemandLifecycleEvent(
            event_id=f"tle-{uuid4().hex[:12]}",
            event_type=event_type,
            actor_phase=actor_phase,
            actor_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            reason_code=reason_code,
            reason_message=reason_message,
        )

    def _build_context_summary(self, request: ToolMatchRequest) -> str:
        archive_id = request.knowledge_context.archive_id
        if not archive_id:
            return "未关联知识库上下文，按人工输入进行匹配。"
        summary = self.archive_service.get_summary(archive_id)
        return (
            f"关联知识库 {archive_id}，当前发布态包含 "
            f"{summary['entity_count']} 个实体、{summary['process_count']} 个流程。"
        )

    def _score_tool(self, tool: ToolDefinition, request: ToolMatchRequest) -> ToolMatchCandidate:
        score = 0
        matched_dimensions: list[str] = []
        reasons: list[str] = []
        gaps: list[str] = []

        domain_hits = sorted(set(request.target_domain_ids).intersection([tool.primary_domain_id]))
        if request.target_domain_ids:
            if domain_hits:
                score += round(25 * len(domain_hits) / len(request.target_domain_ids))
                matched_dimensions.append("domain")
                reasons.append(f"命中业务域：{', '.join(domain_hits)}")
            else:
                gaps.append("未命中目标业务域")

        lifecycle_hits = sorted(set(request.lifecycle_stage_ids).intersection(tool.lifecycle_stage_ids))
        if request.lifecycle_stage_ids:
            if lifecycle_hits:
                score += round(20 * len(lifecycle_hits) / len(request.lifecycle_stage_ids))
                matched_dimensions.append("lifecycle")
                reasons.append(f"覆盖生命周期环节：{', '.join(lifecycle_hits)}")
            else:
                gaps.append("未覆盖目标生命周期环节")

        input_hits = sorted(set(request.required_input_types).intersection(tool.input_types))
        if request.required_input_types:
            if input_hits:
                score += round(15 * len(input_hits) / len(request.required_input_types))
                matched_dimensions.append("input_type")
                reasons.append(f"命中输入类型：{', '.join(input_hits)}")
            else:
                gaps.append("未命中输入类型要求")

        output_hits = sorted(set(request.expected_output_types).intersection(tool.output_types))
        if request.expected_output_types:
            if output_hits:
                score += round(10 * len(output_hits) / len(request.expected_output_types))
                matched_dimensions.append("output_type")
                reasons.append(f"命中输出类型：{', '.join(output_hits)}")
            else:
                gaps.append("未命中输出类型要求")

        form_hits = sorted(set(request.preferred_tool_forms).intersection([tool.tool_form_id]))
        if request.preferred_tool_forms:
            if form_hits:
                score += round(10 * len(form_hits) / len(request.preferred_tool_forms))
                matched_dimensions.append("tool_form")
                reasons.append(f"命中工具形态：{', '.join(form_hits)}")
            else:
                gaps.append("未命中期望工具形态")

        runtime_hits = sorted(set(request.preferred_runtime_platforms).intersection(tool.runtime_platform_ids))
        if request.preferred_runtime_platforms:
            if runtime_hits:
                score += round(10 * len(runtime_hits) / len(request.preferred_runtime_platforms))
                matched_dimensions.append("runtime")
                reasons.append(f"命中运行平台：{', '.join(runtime_hits)}")
            else:
                gaps.append("未命中期望运行平台")

        tag_hits = sorted(set(request.preferred_tags).intersection(tool.tags))
        if request.preferred_tags:
            if tag_hits:
                score += round(5 * len(tag_hits) / len(request.preferred_tags))
                matched_dimensions.append("tags")
                reasons.append(f"命中偏好标签：{', '.join(tag_hits)}")
            else:
                gaps.append("未命中偏好标签")

        keyword_hits = [keyword for keyword in tool.keywords if keyword and keyword in request.scenario_text]
        if request.scenario_text:
            if keyword_hits:
                score += min(5, len(keyword_hits) * 5)
                matched_dimensions.append("keywords")
                reasons.append(f"命中场景关键词：{', '.join(keyword_hits)}")
            else:
                gaps.append("场景文本未命中工具关键词")

        if tool.verification.status == "verified":
            reasons.append("工具已完成基线验证")
        elif tool.verification.status == "warning":
            gaps.append("工具仍需人工复核")
        elif tool.verification.status == "failed":
            gaps.append("工具最近一次验证失败")

        return ToolMatchCandidate(
            tool_id=tool.tool_id,
            name=tool.name,
            match_score=min(score, 100),
            matched_dimensions=matched_dimensions,
            reasons=reasons,
            gaps=gaps,
            verification_status=tool.verification.status,
        )

    def _ensure_demo_data(self) -> None:
        if not self.seed_demo_data:
            return
        if self._demo_seed_marker_path().exists():
            return
        if self.repository.list_tools():
            self._mark_demo_seed_initialized()
            return
        for tool in demo_tools():
            self.repository.save_tool(tool)
        self._mark_demo_seed_initialized()

    def _demo_seed_marker_path(self) -> Path:
        return self.repository.catalogs_dir / ".demo-seed-initialized"

    def _mark_demo_seed_initialized(self) -> None:
        marker_path = self._demo_seed_marker_path()
        marker_path.write_text(now_iso(), encoding="utf-8")

    def _ensure_slug_unique(self, slug: str, ignore_tool_id: str | None = None) -> None:
        for tool in self.repository.list_tools():
            if tool.slug == slug and tool.tool_id != ignore_tool_id:
                raise ValueError("Tool slug already exists")

    def _ensure_tool_is_not_referenced(self, tool_id: str) -> None:
        references: list[str] = []

        for item in self.repository.list_demand_items():
            if item.recommended_tool_id == tool_id:
                references.append(f"demand item {item.item_id}")
                continue
            if item.supply_result is not None and item.supply_result.tool_ref == tool_id:
                references.append(f"demand item {item.item_id}")

        for plan in self.repository.list_manufacture_plans():
            if plan.manufactured_tool_id == tool_id:
                references.append(f"manufacture plan {plan.plan_id}")

        if references:
            raise ValueError(f"Tool is still referenced by {', '.join(references)}")

    def _build_demand_items(self, sheet_id: str, root_node: ToolDemandNode) -> list[ToolDemandItem]:
        items: list[ToolDemandItem] = []
        for node, ancestry in self._iter_component_nodes(root_node, []):
            spec = node.component_spec
            if spec is None:
                continue
            items.append(
                ToolDemandItem(
                    item_id=f"tdi-{uuid4().hex[:12]}",
                    sheet_id=sheet_id,
                    source_node_id=node.node_id,
                    ancestry=ancestry,
                    business_domain_id=node.business_domain_id or root_node.business_domain_id,
                    component_name=spec.component_name,
                    component_code=spec.component_code,
                    problem_statement=spec.problem_statement,
                    required_input_types=spec.required_input_types,
                    expected_output_types=spec.expected_output_types,
                    preferred_tool_forms=spec.preferred_tool_forms,
                    preferred_runtime_platforms=spec.preferred_runtime_platforms,
                    lifecycle_stage_ids=spec.lifecycle_stage_ids,
                    keywords=spec.keywords,
                    acceptance_notes=spec.acceptance_notes,
                    recommendation_type="insufficient_info",
                    recommendation_summary="待完成工具匹配分析。",
                    review_status="pending_review",
                    processing_status="accepted",
                    analysis_result=f"已受理组件需求：{' / '.join(ancestry)}",
                    check_result="树型层级校验通过，组件叶子项结构完整。",
                    match_result="待执行工具匹配分析。",
                    supply_result=None,
                )
            )
        return items

    def _iter_component_nodes(
        self,
        node: ToolDemandNode,
        ancestry: list[str],
    ) -> list[tuple[ToolDemandNode, list[str]]]:
        current_path = [*ancestry, node.node_name]
        if node.node_type == "component":
            return [(node, current_path)]

        items: list[tuple[ToolDemandNode, list[str]]] = []
        for child in node.children:
            items.extend(self._iter_component_nodes(child, current_path))
        return items

    def _process_demand_item(self, item: ToolDemandItem) -> ToolDemandItem:
        if not item.required_input_types or not item.expected_output_types:
            return item.model_copy(
                update={
                    "processing_status": "checking",
                    "recommendation_type": "insufficient_info",
                    "recommendation_summary": "输入/输出约束不足，当前不能直接批准，需补充后再审定。",
                    "match_result": "当前需求项约束不足，待补充后再审定。",
                    "updated_at": now_iso(),
                }
            )

        match_request = self._build_item_match_request(item)
        candidates = [
            self._score_tool(tool, match_request)
            for tool in self.repository.list_tools()
            if tool.status == "active"
        ]
        candidates = sorted(candidates, key=lambda candidate: candidate.match_score, reverse=True)
        best_candidate = candidates[0] if candidates else None
        if best_candidate is not None and best_candidate.match_score >= 60:
            tool = self.repository.get_tool(best_candidate.tool_id)
            if tool is not None:
                return item.model_copy(
                    update={
                        "processing_status": "matched_existing",
                        "recommendation_type": "existing_tool",
                        "recommendation_summary": f"建议直接交付现有工具：{tool.name}（匹配得分 {best_candidate.match_score}）。",
                        "recommended_tool_id": tool.tool_id,
                        "recommended_tool_name": tool.name,
                        "match_result": f"命中现有工具：{tool.name}（得分 {best_candidate.match_score}），待人工审定。",
                        "updated_at": now_iso(),
                    }
                )

        return item.model_copy(
            update={
                "processing_status": "checking",
                "recommendation_type": "manufacture_candidate",
                "recommendation_summary": "当前未命中现有工具，建议审定通过后进入研制名单。",
                "match_result": "未命中现有工具，当前仅生成进入研制的推荐结论，待人工审定。",
                "updated_at": now_iso(),
            }
        )

    def _build_item_match_request(self, item: ToolDemandItem) -> ToolMatchRequest:
        scenario_text = " ".join(
            [item.component_name, item.problem_statement, *item.keywords, *item.ancestry]
        ).strip()
        return ToolMatchRequest(
            scenario_text=scenario_text,
            target_domain_ids=[item.business_domain_id] if item.business_domain_id else [],
            lifecycle_stage_ids=item.lifecycle_stage_ids,
            required_input_types=item.required_input_types,
            expected_output_types=item.expected_output_types,
            preferred_tool_forms=item.preferred_tool_forms,
            preferred_runtime_platforms=item.preferred_runtime_platforms,
            preferred_tags=[f"domain:{item.business_domain_id}"] if item.business_domain_id else [],
        )

    def _build_manufacture_plan(self, item: ToolDemandItem) -> ToolManufacturePlan:
        simulation_profile, target_duration_seconds = self._resolve_simulation_profile(item)
        suggested_poll_after_seconds = self._resolve_suggested_poll_after_seconds(target_duration_seconds)
        estimated_ready_at = (datetime.now(tz=UTC) + timedelta(seconds=target_duration_seconds)).isoformat()
        return ToolManufacturePlan(
            plan_id=f"tmp-{uuid4().hex[:12]}",
            item_id=item.item_id,
            status="manufacturing_pending",
            simulation_profile=simulation_profile,
            target_duration_seconds=target_duration_seconds,
            estimated_ready_at=estimated_ready_at,
            estimated_ready_in_hours=(target_duration_seconds + 3599) // 3600 if target_duration_seconds >= 3600 else None,
            suggested_poll_after_seconds=suggested_poll_after_seconds,
            planned_tool_name=item.component_name,
            planned_tool_form_id=item.preferred_tool_forms[0] if item.preferred_tool_forms else "skill",
            planned_runtime_platform_ids=item.preferred_runtime_platforms or ["agent_runtime"],
            last_progress_message="已批准进入研制，等待模拟执行器接管。",
        )

    def _resolve_simulation_profile(self, item: ToolDemandItem) -> tuple[str, int]:
        profiles = [
            ("fast", self._resolve_simulation_duration_window("fast")),
            ("normal", self._resolve_simulation_duration_window("normal")),
            ("slow", self._resolve_simulation_duration_window("slow")),
        ]
        profile_seed = self._build_simulation_seed(item)
        profile_index = profile_seed % len(profiles)
        profile_name, duration_window = profiles[profile_index]
        min_duration, max_duration = duration_window
        if min_duration >= max_duration:
            return profile_name, min_duration

        duration_seed = self._build_simulation_seed(item, salt=profile_name)
        duration_seconds = min_duration + (duration_seed % ((max_duration - min_duration) + 1))
        return profile_name, duration_seconds

    def _resolve_simulation_duration_window(self, profile_name: str) -> tuple[int, int]:
        configured = self.simulation_profile_durations.get(
            profile_name,
            DEFAULT_SIMULATION_PROFILE_WINDOWS[profile_name],
        )
        if isinstance(configured, int):
            duration = max(MIN_SIMULATION_DURATION_SECONDS, min(configured, MAX_SIMULATION_DURATION_SECONDS))
            return duration, duration
        if isinstance(configured, tuple) and len(configured) == 2:
            raw_min, raw_max = configured
        else:
            raw_min, raw_max = DEFAULT_SIMULATION_PROFILE_WINDOWS[profile_name]

        min_duration = max(int(raw_min), MIN_SIMULATION_DURATION_SECONDS)
        max_duration = min(int(raw_max), MAX_SIMULATION_DURATION_SECONDS)
        if max_duration < min_duration:
            max_duration = min_duration
        return min_duration, max_duration

    def _build_simulation_seed(self, item: ToolDemandItem, *, salt: str = "") -> int:
        seed_source = f"{item.component_code}:{item.item_id}:{salt}"
        return sum((index + 1) * ord(char) for index, char in enumerate(seed_source))

    def _resolve_suggested_poll_after_seconds(self, target_duration_seconds: int) -> int:
        if target_duration_seconds <= 60:
            return 5
        if target_duration_seconds <= 300:
            return 15
        if target_duration_seconds <= 1800:
            return 60
        if target_duration_seconds <= 3600:
            return 120
        return 300

    def _build_supply_fetch_manifest(self, tool: ToolDefinition) -> ToolFetchManifest:
        return ToolFetchManifest(
            tool_id=tool.tool_id,
            tool_name=tool.name,
            tool_form_id=tool.tool_form_id,
            runtime_platform_ids=tool.runtime_platform_ids,
            entrypoint_type="http",
            entrypoint_locator=f"/api/tool-hub/tools/{tool.tool_id}/fetch",
            updated_at=tool.updated_at,
        )

    def _build_tool_fetch_manifest_response(self, tool: ToolDefinition) -> ToolFetchManifest:
        return ToolFetchManifest(
            tool_id=tool.tool_id,
            tool_name=tool.name,
            tool_form_id=tool.tool_form_id,
            runtime_platform_ids=tool.runtime_platform_ids,
            entrypoint_type="http",
            entrypoint_locator=f"/api/tool-hub/tools/{tool.tool_id}",
            updated_at=tool.updated_at,
        )

    def _get_sheet_items(self, sheet: ToolDemandSheet) -> list[ToolDemandItem]:
        items: list[ToolDemandItem] = []
        for item_id in sheet.item_ids:
            item = self.repository.get_demand_item(item_id)
            if item is not None:
                items.append(item)
        return items

    def _refresh_sheet(
        self,
        sheet: ToolDemandSheet,
        items: list[ToolDemandItem] | None = None,
    ) -> ToolDemandSheet:
        current_items = items if items is not None else self._get_sheet_items(sheet)
        pending_review_count = len([item for item in current_items if item.review_status == "pending_review"])
        approved_delivery_count = len([item for item in current_items if item.review_status == "approved_delivery"])
        approved_manufacture_count = len(
            [item for item in current_items if item.review_status == "approved_manufacture"]
        )
        rejected_item_count = len([item for item in current_items if item.review_status == "rejected"])
        matched_existing_count = len([item for item in current_items if item.recommendation_type == "existing_tool"])
        manufacturing_count = len(
            [
                item
                for item in current_items
                if item.review_status == "approved_manufacture"
                and item.processing_status in {"manufacturing_pending", "manufacturing_in_progress"}
            ]
        )
        ready_for_fetch_count = len(
            [
                item
                for item in current_items
                if item.supply_result is not None and item.supply_result.fetch_interface is not None
            ]
        )
        failed_count = len([item for item in current_items if item.processing_status == "failed"])
        approved_item_count = approved_delivery_count + approved_manufacture_count

        if not current_items:
            review_status = "pending_review"
        elif pending_review_count == len(current_items):
            review_status = "pending_review"
        elif pending_review_count > 0:
            review_status = "reviewing"
        else:
            review_status = "reviewed"

        if approved_item_count == 0 or ready_for_fetch_count == 0:
            delivery_status = "not_delivered"
        elif ready_for_fetch_count >= approved_item_count:
            delivery_status = "delivered"
        else:
            delivery_status = "delivering"

        processing_status = sheet.processing_status
        if sheet.lifecycle_status not in TERMINAL_SHEET_LIFECYCLE_STATUSES:
            processing_status = "not_started"
            if current_items and failed_count == len(current_items):
                processing_status = "failed"
            elif approved_item_count > 0 and ready_for_fetch_count == approved_item_count and pending_review_count == 0:
                processing_status = "ready"
            elif ready_for_fetch_count > 0:
                processing_status = "partially_ready"
            elif current_items:
                processing_status = "processing"

        return sheet.model_copy(
            update={
                "processing_status": processing_status,
                "review_status": review_status,
                "delivery_status": delivery_status,
                "item_count": len(current_items),
                "pending_review_count": pending_review_count,
                "approved_delivery_count": approved_delivery_count,
                "approved_manufacture_count": approved_manufacture_count,
                "rejected_item_count": rejected_item_count,
                "matched_existing_count": matched_existing_count,
                "manufacturing_count": manufacturing_count,
                "ready_for_fetch_count": ready_for_fetch_count,
                "failed_count": failed_count,
                "updated_at": now_iso(),
            }
        )

    def _build_progress_view(
        self,
        item: ToolDemandItem,
        sheet: ToolDemandSheet | None,
    ) -> ItemProgressView:
        sheet_lifecycle_status = sheet.lifecycle_status if sheet is not None else "accepted"
        sheet_review_status = sheet.review_status if sheet is not None else "pending_review"
        sheet_delivery_status = sheet.delivery_status if sheet is not None else "not_delivered"
        progress_percent = 0
        result_type = item.supply_result.result_type if item.supply_result is not None else None
        estimated_ready_at = item.supply_result.estimated_ready_at if item.supply_result is not None else None
        suggested_poll_after_seconds = (
            item.supply_result.suggested_poll_after_seconds if item.supply_result is not None else None
        )
        fetch_interface = item.supply_result.fetch_interface if item.supply_result is not None else None
        last_message = item.supply_result.last_message if item.supply_result is not None else item.recommendation_summary

        if item.review_status == "approved_delivery":
            progress_percent = 100
        elif item.review_status == "approved_manufacture":
            plan = self.repository.get_manufacture_plan(item.item_id)
            if plan is not None:
                progress_percent = plan.progress_percent
                estimated_ready_at = plan.estimated_ready_at
                suggested_poll_after_seconds = plan.suggested_poll_after_seconds
        elif item.recommendation_type == "existing_tool":
            progress_percent = 60
        elif item.recommendation_type == "manufacture_candidate":
            progress_percent = 35

        return ItemProgressView(
            item_id=item.item_id,
            sheet_id=item.sheet_id,
            status=item.processing_status,
            sheet_lifecycle_status=sheet_lifecycle_status,
            sheet_review_status=sheet_review_status,
            sheet_delivery_status=sheet_delivery_status,
            review_status=item.review_status,
            result_type=result_type,
            progress_percent=progress_percent,
            estimated_ready_at=estimated_ready_at,
            suggested_poll_after_seconds=suggested_poll_after_seconds,
            fetch_interface=fetch_interface,
            last_message=last_message,
            updated_at=item.updated_at,
        )

    def _advance_manufacture_plan(self, plan: ToolManufacturePlan, item: ToolDemandItem) -> None:
        if item.review_status != "approved_manufacture":
            return

        current_time = datetime.now(tz=UTC)
        timestamp = now_iso()
        ready_at = datetime.fromisoformat(plan.estimated_ready_at)

        if plan.started_at is None and current_time < ready_at:
            updated_plan = plan.model_copy(
                update={
                    "status": "manufacturing_in_progress",
                    "started_at": timestamp,
                    "query_count": plan.query_count + 1,
                    "progress_percent": max(plan.progress_percent, 18),
                    "last_progress_message": "模拟研制已启动，正在持续推进。",
                    "updated_at": timestamp,
                }
            )
            updated_item = item.model_copy(
                update={
                    "processing_status": "manufacturing_in_progress",
                    "supply_result": self._build_pending_manufacture_supply_result(item, updated_plan),
                    "updated_at": timestamp,
                }
            )
            self.repository.save_manufacture_plan(updated_plan)
            self.repository.save_demand_item(updated_item)
            self._refresh_sheet_for_item(updated_item)
            return

        started_at = current_time if plan.started_at is None else datetime.fromisoformat(plan.started_at)
        if current_time < ready_at:
            elapsed_seconds = max((current_time - started_at).total_seconds(), 0)
            progress_ratio = min(elapsed_seconds / max(plan.target_duration_seconds, 1), 0.99)
            progress_percent = max(plan.progress_percent, min(95, 20 + int(progress_ratio * 75)))
            updated_plan = plan.model_copy(
                update={
                    "status": "manufacturing_in_progress",
                    "query_count": plan.query_count + 1,
                    "progress_percent": progress_percent,
                    "last_progress_message": f"模拟研制进行中，已完成 {progress_percent}%。",
                    "updated_at": timestamp,
                }
            )
            updated_item = item.model_copy(
                update={
                    "processing_status": "manufacturing_in_progress",
                    "supply_result": self._build_pending_manufacture_supply_result(item, updated_plan),
                    "updated_at": timestamp,
                }
            )
            self.repository.save_manufacture_plan(updated_plan)
            self.repository.save_demand_item(updated_item)
            self._refresh_sheet_for_item(updated_item)
            return

        manufactured_tool = self._ensure_manufactured_tool(item, plan)
        completed_plan = plan.model_copy(
            update={
                "status": "ready_for_fetch",
                "manufactured_tool_id": manufactured_tool.tool_id,
                "query_count": plan.query_count + 1,
                "progress_percent": 100,
                "started_at": plan.started_at or timestamp,
                "completed_at": timestamp,
                "last_progress_message": f"模拟研制完成，当前可获取工具：{manufactured_tool.name}",
                "updated_at": timestamp,
            }
        )
        updated_item = item.model_copy(
            update={
                "processing_status": "ready_for_fetch",
                "supply_result": self._build_manufactured_tool_supply_result(item, completed_plan, manufactured_tool),
                "updated_at": timestamp,
            }
        )
        self.repository.save_manufacture_plan(completed_plan)
        self.repository.save_demand_item(updated_item)
        self._refresh_sheet_for_item(updated_item)

    def _ensure_manufactured_tool(
        self,
        item: ToolDemandItem,
        plan: ToolManufacturePlan,
    ) -> ToolDefinition:
        if plan.manufactured_tool_id is not None:
            existing_tool = self.repository.get_tool(plan.manufactured_tool_id)
            if existing_tool is not None:
                return existing_tool

        tool = ToolDefinition(
            tool_id=f"tool-{uuid4().hex[:12]}",
            name=plan.planned_tool_name,
            slug=self._build_tool_slug(item.component_code),
            status="active",
            summary=f"模拟制造产物：{item.component_name}",
            problem_statement=item.problem_statement or f"支撑 {item.component_name} 的模拟制造产物。",
            primary_domain_id=item.business_domain_id or "cross_domain_shared",
            tool_form_id=plan.planned_tool_form_id,
            runtime_platform_ids=plan.planned_runtime_platform_ids or ["agent_runtime"],
            tags=[
                f"domain:{item.business_domain_id or 'cross_domain_shared'}",
                f"form:{plan.planned_tool_form_id}",
                *[f"runtime:{runtime}" for runtime in (plan.planned_runtime_platform_ids or ["agent_runtime"])],
                *[f"lifecycle:{stage}" for stage in (item.lifecycle_stage_ids or ["build_integration"])],
                *[f"input:{input_type}" for input_type in item.required_input_types],
                *[f"output:{output_type}" for output_type in item.expected_output_types],
                "risk:simulated-manufacture",
            ],
            lifecycle_stage_ids=item.lifecycle_stage_ids or ["build_integration"],
            input_types=item.required_input_types,
            output_types=item.expected_output_types,
            supported_sources=["manual_input"],
            usage_notes="当前阶段为 P4 未命中分支的模拟制造产物。",
            keywords=item.keywords,
            verification=ToolVerification(
                status="warning",
                last_verified_result="模拟制造产物，待后续正式验证。",
                sample_case_ids=[],
            ),
        )
        return self.repository.save_tool(tool)

    def _build_existing_tool_supply_result(self, item: ToolDemandItem, tool: ToolDefinition) -> ToolSupplyResult:
        return ToolSupplyResult(
            result_type="existing_tool",
            item_id=item.item_id,
            tool_ref=tool.tool_id,
            fetch_interface=self._build_supply_fetch_manifest(tool),
            available_at=now_iso(),
            last_message=f"已批准直接交付现有工具：{tool.name}",
        )

    def _build_pending_manufacture_supply_result(
        self,
        item: ToolDemandItem,
        plan: ToolManufacturePlan,
    ) -> ToolSupplyResult:
        return ToolSupplyResult(
            result_type="pending_manufacture",
            item_id=item.item_id,
            progress_query_interface=f"/api/tool-hub/demand-items/{item.item_id}/progress",
            estimated_ready_at=plan.estimated_ready_at,
            suggested_poll_after_seconds=plan.suggested_poll_after_seconds,
            last_message=plan.last_progress_message or "已批准进入研制，等待 P4 生成可取工具。",
        )

    def _build_manufactured_tool_supply_result(
        self,
        item: ToolDemandItem,
        plan: ToolManufacturePlan,
        tool: ToolDefinition,
    ) -> ToolSupplyResult:
        return ToolSupplyResult(
            result_type="manufactured_tool",
            item_id=item.item_id,
            tool_ref=tool.tool_id,
            fetch_interface=self._build_supply_fetch_manifest(tool),
            progress_query_interface=f"/api/tool-hub/demand-items/{item.item_id}/progress",
            estimated_ready_at=plan.estimated_ready_at,
            suggested_poll_after_seconds=plan.suggested_poll_after_seconds,
            available_at=now_iso(),
            last_message=plan.last_progress_message or f"模拟制造完成，当前可获取工具：{tool.name}",
        )

    def _build_manufacture_plan_view(
        self,
        plan: ToolManufacturePlan,
        item: ToolDemandItem,
    ) -> ToolManufacturePlanView:
        return ToolManufacturePlanView(
            plan_id=plan.plan_id,
            item_id=plan.item_id,
            sheet_id=item.sheet_id,
            component_name=item.component_name,
            planned_tool_name=plan.planned_tool_name,
            status=plan.status,
            progress_percent=plan.progress_percent,
            simulation_profile=plan.simulation_profile,
            target_duration_seconds=plan.target_duration_seconds,
            estimated_ready_at=plan.estimated_ready_at,
            started_at=plan.started_at,
            completed_at=plan.completed_at,
            last_progress_message=plan.last_progress_message,
            updated_at=plan.updated_at,
        )

    def _build_evolution_task(self, finding: EvolutionFinding, actor_id: str) -> EvolutionTask:
        config = self.repository.get_evolution_config()
        task_type = "auto_apply" if finding.kind in set(config.auto_apply_rule_ids) else "manual_followup"
        planned_action_by_kind = {
            "missing_description": "enrich_description",
            "taxonomy_issue": "normalize_metadata",
            "overlap_risk": "manual_overlap_review",
            "coverage_gap": "manual_coverage_followup",
        }
        priority_by_severity = {
            "info": "low",
            "warning": "medium",
            "critical": "high",
        }
        return EvolutionTask(
            task_id=f"evolution-task-{uuid4().hex[:12]}",
            source_run_id=finding.run_id,
            source_finding_id=finding.finding_id,
            task_type=task_type,
            priority=priority_by_severity[finding.severity],
            planned_action=planned_action_by_kind[finding.kind],
            target_tool_ids=finding.tool_ids,
            created_by=actor_id,
            result_summary="等待 P4 runtime coordinator 处理。",
        )

    def _build_evolution_run_summary(self, findings: list[EvolutionFinding], tool_count: int) -> EvolutionRunSummary:
        return EvolutionRunSummary(
            tool_count=tool_count,
            finding_count=len(findings),
            missing_description_count=len([item for item in findings if item.kind == "missing_description"]),
            taxonomy_issue_count=len([item for item in findings if item.kind == "taxonomy_issue"]),
            overlap_risk_count=len([item for item in findings if item.kind == "overlap_risk"]),
            coverage_gap_count=len([item for item in findings if item.kind == "coverage_gap"]),
            accepted_count=len([item for item in findings if item.decision_status == "accepted_to_task"]),
            ignored_count=len([item for item in findings if item.decision_status == "ignored"]),
            generated_task_count=len([item for item in findings if item.linked_task_id]),
        )

    def _advance_evolution_task(self, task: EvolutionTask) -> None:
        timestamp = now_iso()
        running_task = task if task.task_status == "running" else task.model_copy(
            update={"task_status": "running", "started_at": timestamp, "updated_at": timestamp}
        )
        self.repository.save_evolution_task(running_task)

        if running_task.task_type != "auto_apply":
            return

        change_sets = self._apply_evolution_auto_changes(running_task)
        completed_task = running_task.model_copy(
            update={
                "task_status": "completed",
                "completed_at": now_iso(),
                "updated_at": now_iso(),
                "change_count": len(change_sets),
                "rollback_available": len(change_sets) > 0,
                "result_summary": f"已自动改写 {len(change_sets)} 个工具定义。",
            }
        )
        self.repository.save_evolution_task(completed_task)
        if change_sets:
            self.mark_evolution_dirty()

    def _apply_evolution_auto_changes(self, task: EvolutionTask) -> list[EvolutionChangeSet]:
        change_sets: list[EvolutionChangeSet] = []
        located = self.repository.get_evolution_finding(task.source_finding_id)
        if located is None:
            return change_sets
        run, finding_index = located
        finding = run.findings[finding_index]

        for tool_id in task.target_tool_ids:
            tool = self.repository.get_tool(tool_id)
            if tool is None:
                continue
            updated_tool, change_kind = self._build_auto_updated_tool(tool, finding)
            if updated_tool.model_dump(mode="json") == tool.model_dump(mode="json"):
                continue
            self.repository.save_tool(updated_tool)
            change_set = EvolutionChangeSet(
                change_set_id=f"ecs-{uuid4().hex[:12]}",
                task_id=task.task_id,
                tool_id=tool.tool_id,
                change_kind=change_kind,
                before_snapshot=tool.model_dump(mode="json"),
                after_snapshot=updated_tool.model_dump(mode="json"),
            )
            self.repository.save_evolution_change_set(change_set)
            change_sets.append(change_set)

        return change_sets

    def _build_auto_updated_tool(self, tool: ToolDefinition, finding: EvolutionFinding) -> tuple[ToolDefinition, str]:
        if finding.kind == "missing_description":
            summary = tool.summary.strip() or f"{tool.name} 的基础能力摘要已由自演进巡检补充。"
            problem_statement = tool.problem_statement.strip() or f"补充 {tool.name} 的问题定义，便于后续匹配与验证。"
            verification = tool.verification.model_copy(
                update={
                    "last_verified_result": tool.verification.last_verified_result
                    or "P4 自演进巡检已自动补充基础描述字段。"
                }
            )
            return (
                tool.model_copy(
                    update={
                        "summary": summary,
                        "problem_statement": problem_statement,
                        "verification": verification,
                        "updated_at": now_iso(),
                    }
                ),
                "description_enrichment",
            )

        normalized_domain_id = tool.primary_domain_id if tool.primary_domain_id in {item.id for item in DOMAIN_CATALOG} else "cross_domain_shared"
        normalized_tool_form_id = tool.tool_form_id if tool.tool_form_id in {item.id for item in TOOL_FORM_CATALOG} else "skill"
        runtime_platform_ids = tool.runtime_platform_ids or ["agent_runtime"]
        lifecycle_stage_ids = tool.lifecycle_stage_ids or ["solution_design"]
        normalized_tool = ToolDefinition.model_validate(
            {
                **tool.model_dump(mode="json"),
                "primary_domain_id": normalized_domain_id,
                "tool_form_id": normalized_tool_form_id,
                "runtime_platform_ids": runtime_platform_ids,
                "lifecycle_stage_ids": lifecycle_stage_ids,
                "tags": self._build_normalized_tool_tags(
                    tool=tool,
                    primary_domain_id=normalized_domain_id,
                    tool_form_id=normalized_tool_form_id,
                    runtime_platform_ids=runtime_platform_ids,
                    lifecycle_stage_ids=lifecycle_stage_ids,
                ),
                "updated_at": now_iso(),
            }
        )
        return normalized_tool, "metadata_normalization"

    def _build_normalized_tool_tags(
        self,
        *,
        tool: ToolDefinition,
        primary_domain_id: str,
        tool_form_id: str,
        runtime_platform_ids: list[str],
        lifecycle_stage_ids: list[str],
    ) -> list[str]:
        preserved = [
            tag
            for tag in tool.tags
            if tag.startswith("risk:")
            or not any(
                tag.startswith(prefix)
                for prefix in ("domain:", "form:", "runtime:", "lifecycle:", "input:", "output:")
            )
        ]
        return sorted(
            dict.fromkeys(
                [
                    f"domain:{primary_domain_id}",
                    f"form:{tool_form_id}",
                    *[f"runtime:{item}" for item in runtime_platform_ids],
                    *[f"lifecycle:{item}" for item in lifecycle_stage_ids],
                    *[f"input:{item}" for item in tool.input_types],
                    *[f"output:{item}" for item in tool.output_types],
                    *preserved,
                ]
            )
        )

    def _trim_evolution_run_history(self, max_run_history: int) -> None:
        runs = self.repository.list_evolution_runs()
        for stale_run in runs[max_run_history:]:
            stale_path = self.repository.evolution_runs_dir / f"{stale_run.run_id}.json"
            stale_path.unlink(missing_ok=True)

    def _refresh_sheet_for_item(self, item: ToolDemandItem) -> None:
        sheet = self.repository.get_demand_sheet(item.sheet_id)
        if sheet is None:
            return
        refreshed = self._refresh_sheet(sheet)
        self.repository.save_demand_sheet(refreshed)

    def _build_tool_slug(self, component_code: str) -> str:
        base_slug = component_code.lower().replace("_", "-")
        return f"{base_slug}-{uuid4().hex[:6]}"
