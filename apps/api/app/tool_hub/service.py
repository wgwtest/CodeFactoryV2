from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock, Thread
from typing import ClassVar
from uuid import uuid4

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.demand_fixtures import build_mock_blue_force_request, build_mock_demand_request
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
from app.tool_hub.models import (
    EvolutionRun,
    EvolutionRunReadEnvelope,
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


class _ToolManufactureExecutor:
    def __init__(self, service_factory: Callable[[], "ToolHubService"], interval_seconds: float) -> None:
        self.service_factory = service_factory
        self.interval_seconds = interval_seconds
        self._stop_event = Event()
        self._thread = Thread(target=self._run, name="tool-hub-manufacture-executor", daemon=True)

    def start(self) -> None:
        if self._thread.is_alive():
            return
        self._thread.start()

    def _run(self) -> None:
        service = self.service_factory()
        while not self._stop_event.is_set():
            try:
                service.run_manufacture_executor_cycle()
            except Exception:
                pass
            self._stop_event.wait(self.interval_seconds)


class ToolHubService:
    _executor_registry: ClassVar[dict[str, _ToolManufactureExecutor]] = {}
    _executor_registry_lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        root: str | Path,
        archive_service: ArchiveKnowledgeService,
        seed_demo_data: bool = True,
        enable_background_executor: bool = True,
        executor_tick_seconds: float = 0.1,
        simulation_profile_durations: dict[str, int | tuple[int, int]] | None = None,
    ) -> None:
        self.root = Path(root)
        self.repository = ToolHubRepository(self.root)
        self.archive_service = archive_service
        self.seed_demo_data = seed_demo_data
        self.executor_tick_seconds = executor_tick_seconds
        self.simulation_profile_durations = simulation_profile_durations or DEFAULT_SIMULATION_PROFILE_WINDOWS
        self._ensure_demo_data()
        if enable_background_executor:
            self._ensure_background_executor()

    def _ensure_background_executor(self) -> None:
        root_key = str(self.root.resolve())
        with self._executor_registry_lock:
            if root_key in self._executor_registry:
                return
            executor = _ToolManufactureExecutor(
                service_factory=lambda: ToolHubService(
                    root=self.root,
                    archive_service=self.archive_service,
                    seed_demo_data=self.seed_demo_data,
                    enable_background_executor=False,
                    executor_tick_seconds=self.executor_tick_seconds,
                    simulation_profile_durations=self.simulation_profile_durations,
                ),
                interval_seconds=self.executor_tick_seconds,
            )
            self._executor_registry[root_key] = executor
            executor.start()

    def get_snapshot(self) -> ToolHubStateSnapshot:
        self._ensure_demo_data()
        return build_tool_hub_snapshot(
            catalogs=self.get_catalogs(),
            tools=self.repository.list_tools(),
            demand_sheets=self.repository.list_demand_sheets(),
            match_runs=self.repository.list_match_runs(),
            evolution_runs=self.repository.list_evolution_runs(),
        )

    def get_overview(self) -> ToolHubOverviewReadEnvelope:
        snapshot = self.get_snapshot()
        return ToolHubOverviewReadEnvelope(
            meta=snapshot.meta,
            data=project_tool_hub_overview(snapshot),
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
        snapshot = self.get_snapshot()
        return ToolListReadEnvelope(
            meta=snapshot.meta,
            data=project_tool_list(snapshot),
        )

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        self._ensure_demo_data()
        return self.repository.get_tool(tool_id)

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        self._ensure_demo_data()
        self._ensure_slug_unique(payload.slug)
        tool = ToolDefinition(
            tool_id=f"tool-{uuid4().hex[:12]}",
            **payload.model_dump(mode="json"),
        )
        return self.repository.save_tool(tool)

    def update_tool(self, tool_id: str, payload: ToolDefinitionWrite) -> ToolDefinition | None:
        existing = self.repository.get_tool(tool_id)
        if existing is None:
            return None
        self._ensure_slug_unique(payload.slug, ignore_tool_id=tool_id)
        updated = ToolDefinition.model_validate(
            {
                **existing.model_dump(mode="json"),
                **payload.model_dump(mode="json"),
                "tool_id": tool_id,
                "created_at": existing.created_at,
                "updated_at": now_iso(),
            }
        )
        return self.repository.save_tool(updated)

    def delete_tool(self, tool_id: str) -> ToolRegistryDeleteResult | None:
        self._ensure_demo_data()
        tool = self.repository.get_tool(tool_id)
        if tool is None:
            return None
        self._ensure_tool_is_not_referenced(tool_id)
        self.repository.delete_tool(tool_id)
        return ToolRegistryDeleteResult(
            removed_tool_id=tool_id,
            remaining_tool_count=len(self.repository.list_tools()),
        )

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
        return self.repository.save_match_run(run)

    def list_evolution_runs(self) -> EvolutionRunReadEnvelope:
        snapshot = self.get_snapshot()
        return EvolutionRunReadEnvelope(
            meta=snapshot.meta,
            data=project_evolution_runs(snapshot),
        )

    def run_evolution(self) -> EvolutionRun:
        self._ensure_demo_data()
        run = build_evolution_run(self.repository.list_tools())
        return self.repository.save_evolution_run(run)

    def create_mock_blue_force_demand_sheet(self) -> ToolDemandSheetDetail:
        return self.create_demand_sheet(build_mock_blue_force_request())

    def create_mock_demand_sheet(self, scenario_id: str) -> ToolDemandSheetDetail:
        return self.create_demand_sheet(build_mock_demand_request(scenario_id))

    def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
        sheet_id = f"tds-{uuid4().hex[:12]}"
        items = [self._process_demand_item(item) for item in self._build_demand_items(sheet_id, payload.root_node)]
        for item in items:
            self.repository.save_demand_item(item)

        submitted_event = self._build_lifecycle_event(
            event_type="submitted",
            actor_phase=payload.requested_by,
            actor_id=payload.source.producer,
            from_status=None,
            to_status="submitted",
            reason_code="sheet_submitted",
            reason_message="需求方已提交工具需求单。",
        )
        accepted_event = self._build_lifecycle_event(
            event_type="accepted",
            actor_phase="P4",
            actor_id="p4-system",
            from_status="submitted",
            to_status="accepted",
            reason_code="sheet_accepted",
            reason_message="P4 已受理当前工具需求单。",
        )
        sheet = ToolDemandSheet(
            sheet_id=sheet_id,
            sheet_name=payload.sheet_name,
            lifecycle_status="accepted",
            review_status="pending_review",
            delivery_status="not_delivered",
            processing_status="not_started",
            source=payload.source,
            requested_by=payload.requested_by,
            business_case=payload.source.business_case,
            root_node=payload.root_node,
            item_ids=[item.item_id for item in items],
            item_count=len(items),
            lifecycle_events=[submitted_event, accepted_event],
            last_actor_phase="P4",
            last_actor_id="p4-system",
        )
        refreshed = self._refresh_sheet(sheet, items)
        self.repository.save_demand_sheet(refreshed)
        return ToolDemandSheetDetail(**refreshed.model_dump(mode="json"), items=items)

    def list_demand_sheets(self) -> ToolDemandSheetEnvelope:
        sheets = [self._refresh_sheet(sheet) for sheet in self.repository.list_demand_sheets()]
        return ToolDemandSheetEnvelope(items=sheets)

    def list_manufacture_plans(self) -> ToolManufacturePlanEnvelope:
        items: list[ToolManufacturePlanView] = []
        for plan in self.repository.list_manufacture_plans():
            item = self.repository.get_demand_item(plan.item_id)
            if item is None:
                continue
            items.append(self._build_manufacture_plan_view(plan, item))
        return ToolManufacturePlanEnvelope(items=items)

    def get_demand_sheet(self, sheet_id: str) -> ToolDemandSheetDetail | None:
        sheet = self.repository.get_demand_sheet(sheet_id)
        if sheet is None:
            return None
        items = self._get_sheet_items(sheet)
        refreshed = self._refresh_sheet(sheet, items)
        if refreshed.model_dump(mode="json") != sheet.model_dump(mode="json"):
            self.repository.save_demand_sheet(refreshed)
        return ToolDemandSheetDetail(**refreshed.model_dump(mode="json"), items=items)

    def get_demand_item(self, item_id: str) -> ToolDemandItem | None:
        return self.repository.get_demand_item(item_id)

    def review_demand_item(
        self,
        item_id: str,
        payload: ToolDemandReviewDecisionRequest,
    ) -> ToolDemandItem | None:
        item = self.repository.get_demand_item(item_id)
        if item is None:
            return None

        sheet = self.repository.get_demand_sheet(item.sheet_id)
        if sheet is None:
            return None
        if sheet.lifecycle_status in TERMINAL_SHEET_LIFECYCLE_STATUSES:
            raise ValueError("Demand sheet is already in terminal status")
        if item.review_status != "pending_review":
            raise ValueError("Demand item is already reviewed")

        review_update = {
            "importance_score": payload.importance_score,
            "urgency_score": payload.urgency_score,
            "rationality_verdict": payload.rationality_verdict,
            "review_comment": payload.review_comment,
            "reviewed_by": payload.reviewed_by,
            "reviewed_at": now_iso(),
            "updated_at": now_iso(),
        }

        if payload.decision == "approve_delivery":
            if item.recommendation_type != "existing_tool" or not item.recommended_tool_id:
                raise ValueError("Current demand item is not eligible for direct delivery")
            tool = self.repository.get_tool(item.recommended_tool_id)
            if tool is None:
                raise ValueError("Recommended tool is no longer available")
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "approved_delivery",
                    "processing_status": "matched_existing",
                    "supply_result": self._build_existing_tool_supply_result(item, tool),
                }
            )
        elif payload.decision == "approve_manufacture":
            if item.recommendation_type != "manufacture_candidate":
                raise ValueError("Current demand item is not eligible for manufacture approval")
            plan = self.repository.get_manufacture_plan(item.item_id)
            if plan is None:
                plan = self._build_manufacture_plan(item)
                self.repository.save_manufacture_plan(plan)
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "approved_manufacture",
                    "processing_status": "manufacturing_pending",
                    "supply_result": self._build_pending_manufacture_supply_result(item, plan),
                }
            )
        else:
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "rejected",
                    "supply_result": None,
                }
            )

        self.repository.save_demand_item(updated_item)
        self._refresh_sheet_for_item(updated_item)
        return self.repository.get_demand_item(item_id)

    def withdraw_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        return self._transition_demand_sheet(
            sheet_id=sheet_id,
            event_type="withdrawn",
            actor_phase=payload.actor_phase or "P3",
            actor_id=payload.actor_id,
            reason_code=payload.reason_code,
            reason_message=payload.reason_message,
        )

    def reject_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        return self._transition_demand_sheet(
            sheet_id=sheet_id,
            event_type="rejected",
            actor_phase=payload.actor_phase or "P4",
            actor_id=payload.actor_id,
            reason_code=payload.reason_code,
            reason_message=payload.reason_message,
        )

    def clear_demand_chain_for_testing(self) -> ToolDemandTestingClearResult:
        cleared_sheet_count, cleared_item_count, cleared_manufacture_plan_count = (
            self.repository.clear_demand_chain_runtime()
        )
        return ToolDemandTestingClearResult(
            cleared_sheet_count=cleared_sheet_count,
            cleared_item_count=cleared_item_count,
            cleared_manufacture_plan_count=cleared_manufacture_plan_count,
        )

    def clear_tool_registry_for_testing(self) -> ToolRegistryTestingClearResult:
        self._mark_demo_seed_initialized()
        cleared_tool_count, cleared_match_run_count, cleared_evolution_run_count = (
            self.repository.clear_tool_runtime()
        )
        return ToolRegistryTestingClearResult(
            cleared_tool_count=cleared_tool_count,
            cleared_match_run_count=cleared_match_run_count,
            cleared_evolution_run_count=cleared_evolution_run_count,
        )

    def run_manufacture_executor_cycle(self) -> None:
        for plan in self.repository.list_manufacture_plans():
            if plan.status not in {"manufacturing_pending", "manufacturing_in_progress"}:
                continue
            item = self.repository.get_demand_item(plan.item_id)
            if item is None:
                continue
            sheet = self.repository.get_demand_sheet(item.sheet_id)
            if sheet is not None and sheet.lifecycle_status in TERMINAL_SHEET_LIFECYCLE_STATUSES:
                continue
            self._advance_manufacture_plan(plan, item)

    def get_demand_item_progress(self, item_id: str) -> ItemProgressView | None:
        item = self.repository.get_demand_item(item_id)
        if item is None:
            return None

        sheet = self.repository.get_demand_sheet(item.sheet_id)
        return self._build_progress_view(item, sheet)

    def get_tool_fetch_manifest(self, tool_id: str) -> ToolFetchManifest | None:
        tool = self.repository.get_tool(tool_id)
        if tool is None:
            return None
        return self._build_tool_fetch_manifest_response(tool)

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

        if plan.started_at is None:
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

        started_at = datetime.fromisoformat(plan.started_at)
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

    def _refresh_sheet_for_item(self, item: ToolDemandItem) -> None:
        sheet = self.repository.get_demand_sheet(item.sheet_id)
        if sheet is None:
            return
        refreshed = self._refresh_sheet(sheet)
        self.repository.save_demand_sheet(refreshed)

    def _build_tool_slug(self, component_code: str) -> str:
        base_slug = component_code.lower().replace("_", "-")
        return f"{base_slug}-{uuid4().hex[:6]}"
