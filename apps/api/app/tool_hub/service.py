from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.demand_fixtures import build_mock_blue_force_request
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
    ToolDemandNode,
    ToolDemandSheet,
    ToolDemandSheetCreateRequest,
    ToolDemandSheetDetail,
    ToolDemandSheetEnvelope,
    ToolFetchManifest,
    ToolHubCatalogs,
    ToolHubOverviewReadEnvelope,
    ToolHubStateSnapshot,
    ToolManufacturePlan,
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


class ToolHubService:
    def __init__(
        self,
        root: str | Path,
        archive_service: ArchiveKnowledgeService,
        seed_demo_data: bool = True,
    ) -> None:
        self.repository = ToolHubRepository(root)
        self.archive_service = archive_service
        self.seed_demo_data = seed_demo_data
        self._ensure_demo_data()

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

    def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
        sheet_id = f"tds-{uuid4().hex[:12]}"
        items = [self._process_demand_item(item) for item in self._build_demand_items(sheet_id, payload.root_node)]
        for item in items:
            self.repository.save_demand_item(item)

        sheet = ToolDemandSheet(
            sheet_id=sheet_id,
            sheet_name=payload.sheet_name,
            status="accepted",
            source=payload.source,
            requested_by=payload.requested_by,
            business_case=payload.source.business_case,
            root_node=payload.root_node,
            item_ids=[item.item_id for item in items],
            item_count=len(items),
        )
        refreshed = self._refresh_sheet(sheet, items)
        self.repository.save_demand_sheet(refreshed)
        return ToolDemandSheetDetail(**refreshed.model_dump(mode="json"), items=items)

    def list_demand_sheets(self) -> ToolDemandSheetEnvelope:
        sheets = [self._refresh_sheet(sheet) for sheet in self.repository.list_demand_sheets()]
        return ToolDemandSheetEnvelope(items=sheets)

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

    def get_demand_item_progress(self, item_id: str) -> ItemProgressView | None:
        item = self.repository.get_demand_item(item_id)
        if item is None:
            return None

        progress_view = self._build_progress_view(item)
        self._advance_pending_manufacture(item)
        return progress_view

    def get_tool_fetch_manifest(self, tool_id: str) -> ToolFetchManifest | None:
        tool = self.repository.get_tool(tool_id)
        if tool is None:
            return None
        return self._build_tool_fetch_manifest_response(tool)

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
        if self.repository.list_tools():
            return
        for tool in demo_tools():
            self.repository.save_tool(tool)

    def _ensure_slug_unique(self, slug: str, ignore_tool_id: str | None = None) -> None:
        for tool in self.repository.list_tools():
            if tool.slug == slug and tool.tool_id != ignore_tool_id:
                raise ValueError("Tool slug already exists")

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
                    status="manufacturing_pending",
                    analysis_result=f"已受理组件需求：{' / '.join(ancestry)}",
                    check_result="树型层级校验通过，组件叶子项结构完整。",
                    match_result="待执行工具匹配分析。",
                    supply_result=ToolSupplyResult(
                        result_type="pending_manufacture",
                        summary="待进入模拟制造流程。",
                    ),
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
                fetch_manifest = self._build_supply_fetch_manifest(tool)
                return item.model_copy(
                    update={
                        "status": "matched_existing",
                        "match_result": f"命中现有工具：{tool.name}（得分 {best_candidate.match_score}）",
                        "supply_result": ToolSupplyResult(
                            result_type="existing_tool",
                            summary=f"已命中现有工具：{tool.name}",
                            tool_id=tool.tool_id,
                            tool_name=tool.name,
                            fetch_manifest=fetch_manifest,
                            progress_query_path=f"/api/tool-hub/demand-items/{item.item_id}/progress",
                        ),
                        "updated_at": now_iso(),
                    }
                )

        plan = self._build_manufacture_plan(item)
        self.repository.save_manufacture_plan(plan)
        return item.model_copy(
            update={
                "status": "manufacturing_pending",
                "match_result": "未命中现有工具，已进入模拟制造排期。",
                "supply_result": ToolSupplyResult(
                    result_type="pending_manufacture",
                    summary="未命中现有工具，等待模拟制造。",
                    progress_query_path=f"/api/tool-hub/demand-items/{item.item_id}/progress",
                    estimated_ready_at=plan.estimated_ready_at,
                    estimated_ready_in_hours=plan.estimated_ready_in_hours,
                ),
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
        estimated_ready_in_hours = max(6, 4 + len(item.component_name) // 2)
        estimated_ready_at = (
            datetime.now(tz=UTC) + timedelta(hours=estimated_ready_in_hours)
        ).isoformat()
        return ToolManufacturePlan(
            plan_id=f"tmp-{uuid4().hex[:12]}",
            item_id=item.item_id,
            status="manufacturing_pending",
            estimated_ready_at=estimated_ready_at,
            estimated_ready_in_hours=estimated_ready_in_hours,
            planned_tool_name=item.component_name,
            planned_tool_form_id=item.preferred_tool_forms[0] if item.preferred_tool_forms else "skill",
            planned_runtime_platform_ids=item.preferred_runtime_platforms or ["agent_runtime"],
        )

    def _build_fetch_manifest(self, tool: ToolDefinition) -> ToolFetchManifest:
        return self._build_supply_fetch_manifest(tool)

    def _build_supply_fetch_manifest(self, tool: ToolDefinition) -> ToolFetchManifest:
        return ToolFetchManifest(
            tool_id=tool.tool_id,
            tool_name=tool.name,
            fetch_path=f"/api/tool-hub/tools/{tool.tool_id}/fetch",
            note="P5 可先读取该 manifest，再继续获取工具定义。",
        )

    def _build_tool_fetch_manifest_response(self, tool: ToolDefinition) -> ToolFetchManifest:
        return ToolFetchManifest(
            tool_id=tool.tool_id,
            tool_name=tool.name,
            fetch_path=f"/api/tool-hub/tools/{tool.tool_id}",
            note="返回实际工具定义读取地址。",
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
        matched_existing_count = len([item for item in current_items if item.status == "matched_existing"])
        manufacturing_count = len(
            [
                item
                for item in current_items
                if item.status in {"manufacturing_pending", "manufacturing_in_progress"}
            ]
        )
        ready_for_fetch_count = len(
            [item for item in current_items if item.status in {"matched_existing", "ready_for_fetch"}]
        )
        failed_count = len([item for item in current_items if item.status == "failed"])

        status: str = "accepted"
        if current_items and ready_for_fetch_count == len(current_items) and failed_count == 0:
            status = "ready"
        elif current_items and failed_count == len(current_items):
            status = "failed"
        elif any(item.status == "manufacturing_in_progress" for item in current_items):
            status = "processing"
        elif ready_for_fetch_count > 0:
            status = "partially_ready"

        return sheet.model_copy(
            update={
                "status": status,
                "item_count": len(current_items),
                "matched_existing_count": matched_existing_count,
                "manufacturing_count": manufacturing_count,
                "ready_for_fetch_count": ready_for_fetch_count,
                "failed_count": failed_count,
                "updated_at": now_iso(),
            }
        )

    def _build_progress_view(self, item: ToolDemandItem) -> ItemProgressView:
        if item.supply_result.result_type == "existing_tool":
            return ItemProgressView(
                item_id=item.item_id,
                sheet_id=item.sheet_id,
                status=item.status,
                result_type="existing_tool",
                progress_percent=100,
                summary=item.supply_result.summary,
                progress_query_path=item.supply_result.progress_query_path,
                fetch_manifest=item.supply_result.fetch_manifest,
            )

        plan = self.repository.get_manufacture_plan(item.item_id)
        if plan is None:
            return ItemProgressView(
                item_id=item.item_id,
                sheet_id=item.sheet_id,
                status=item.status,
                result_type=item.supply_result.result_type,
                progress_percent=0,
                summary=item.supply_result.summary,
                progress_query_path=item.supply_result.progress_query_path,
            )

        fetch_manifest = item.supply_result.fetch_manifest
        result_type = item.supply_result.result_type
        if plan.status == "ready_for_fetch":
            result_type = "manufactured_tool"
        return ItemProgressView(
            item_id=item.item_id,
            sheet_id=item.sheet_id,
            status=item.status,
            result_type=result_type,
            progress_percent=plan.progress_percent,
            summary=item.supply_result.summary,
            estimated_ready_at=plan.estimated_ready_at,
            estimated_ready_in_hours=plan.estimated_ready_in_hours,
            progress_query_path=item.supply_result.progress_query_path,
            fetch_manifest=fetch_manifest,
        )

    def _advance_pending_manufacture(self, item: ToolDemandItem) -> None:
        plan = self.repository.get_manufacture_plan(item.item_id)
        if plan is None or item.supply_result.result_type == "existing_tool":
            return

        if plan.status == "manufacturing_pending":
            updated_plan = plan.model_copy(
                update={
                    "status": "manufacturing_in_progress",
                    "query_count": plan.query_count + 1,
                    "progress_percent": 55,
                    "updated_at": now_iso(),
                }
            )
            updated_item = item.model_copy(
                update={
                    "status": "manufacturing_in_progress",
                    "supply_result": item.supply_result.model_copy(
                        update={"summary": "模拟制造已启动，等待后续查询确认完成。"}
                    ),
                    "updated_at": now_iso(),
                }
            )
            self.repository.save_manufacture_plan(updated_plan)
            self.repository.save_demand_item(updated_item)
            self._refresh_sheet_for_item(updated_item)
            return

        if plan.status == "manufacturing_in_progress":
            manufactured_tool = self._ensure_manufactured_tool(item, plan)
            fetch_manifest = self._build_supply_fetch_manifest(manufactured_tool)
            updated_plan = plan.model_copy(
                update={
                    "status": "ready_for_fetch",
                    "manufactured_tool_id": manufactured_tool.tool_id,
                    "query_count": plan.query_count + 1,
                    "progress_percent": 100,
                    "updated_at": now_iso(),
                }
            )
            updated_item = item.model_copy(
                update={
                    "status": "ready_for_fetch",
                    "supply_result": ToolSupplyResult(
                        result_type="manufactured_tool",
                        summary=f"模拟制造完成：{manufactured_tool.name}",
                        tool_id=manufactured_tool.tool_id,
                        tool_name=manufactured_tool.name,
                        fetch_manifest=fetch_manifest,
                        progress_query_path=f"/api/tool-hub/demand-items/{item.item_id}/progress",
                        estimated_ready_at=plan.estimated_ready_at,
                        estimated_ready_in_hours=0,
                    ),
                    "updated_at": now_iso(),
                }
            )
            self.repository.save_manufacture_plan(updated_plan)
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

    def _refresh_sheet_for_item(self, item: ToolDemandItem) -> None:
        sheet = self.repository.get_demand_sheet(item.sheet_id)
        if sheet is None:
            return
        refreshed = self._refresh_sheet(sheet)
        self.repository.save_demand_sheet(refreshed)

    def _build_tool_slug(self, component_code: str) -> str:
        base_slug = component_code.lower().replace("_", "-")
        return f"{base_slug}-{uuid4().hex[:6]}"
