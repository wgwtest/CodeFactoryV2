from __future__ import annotations

from app.tool_hub.fixtures import (
    DOMAIN_CATALOG,
    INPUT_TYPE_CATALOG,
    LIFECYCLE_STAGE_CATALOG,
    OUTPUT_TYPE_CATALOG,
    RUNTIME_PLATFORM_CATALOG,
    SUPPORTED_SOURCE_CATALOG,
    TAG_NAMESPACE_CATALOG,
    TOOL_FORM_CATALOG,
    VERIFICATION_STATUS_CATALOG,
)
from app.tool_hub.models import (
    ToolDefinition,
    ToolDemandItem,
    ToolDemandSheet,
    ToolDemandSheetDetail,
    ToolHubCatalogs,
    ToolHubStateSnapshot,
    ToolManufacturePlanView,
)
from app.tool_hub.projection_repository import ToolHubProjectionRepository
from app.tool_hub.query_models import (
    CoverageKnowledgeGraphProjection,
    DeliveredToolAttributeProjection,
    EvolutionConfigProjection,
    EvolutionLineageProjection,
    EvolutionWorkspaceProjection,
    OverviewProjection,
    P4ObjectWorkbenchProjection,
    P4ObjectWorkbenchReadEnvelope,
    P4ObjectViewTab,
    ProjectionRefreshResult,
    ToolBuildProjection,
    ToolListProjection,
    ToolResourcesProjection,
    UsageCockpitProjection,
    WorkorderPoolProjection,
    WorkorderProcessingProjection,
)
from app.tool_hub.repository import ToolHubRepository
from app.tool_hub.snapshot import build_tool_hub_snapshot, project_tool_hub_overview


class ToolHubQueryService:
    def __init__(self, repository: ToolHubRepository) -> None:
        self.repository = repository
        self.projection_repository = ToolHubProjectionRepository(repository.root)

    def get_state_snapshot(self) -> ToolHubStateSnapshot:
        return build_tool_hub_snapshot(
            catalogs=self._build_catalogs(),
            tools=self.repository.list_tools(),
            demand_sheets=self.repository.list_demand_sheets(),
            match_runs=self.repository.list_match_runs(),
            evolution_config=self.repository.get_evolution_config(),
            evolution_runs=self.repository.list_evolution_runs(),
            evolution_tasks=self.repository.list_evolution_tasks(),
            runtime_state=self.repository.get_runtime_state(),
        )

    def get_overview_projection(self) -> OverviewProjection:
        self._ensure_core_projections()
        projection = self.projection_repository.get_overview_projection()
        if projection is None:
            self.refresh_core_projections()
            projection = self.projection_repository.get_overview_projection()
        if projection is None:
            raise RuntimeError("Overview projection refresh failed")
        return projection

    def get_tool_list_projection(self) -> ToolListProjection:
        self._ensure_core_projections()
        projection = self.projection_repository.get_tool_list_projection()
        if projection is None:
            self.refresh_core_projections()
            projection = self.projection_repository.get_tool_list_projection()
        if projection is None:
            raise RuntimeError("Tool list projection refresh failed")
        return projection

    def get_evolution_workspace_projection(self) -> EvolutionWorkspaceProjection:
        self._ensure_core_projections()
        projection = self.projection_repository.get_evolution_workspace_projection()
        if projection is None:
            self.refresh_core_projections()
            projection = self.projection_repository.get_evolution_workspace_projection()
        if projection is None:
            raise RuntimeError("Evolution workspace projection refresh failed")
        return projection

    def get_object_workbench_projection(
        self,
        *,
        sheet_id: str | None = None,
        item_id: str | None = None,
        tool_id: str | None = None,
    ) -> P4ObjectWorkbenchReadEnvelope:
        if sheet_id is None and item_id is None and tool_id is None:
            self._ensure_core_projections()
            projection = self.projection_repository.get_object_workbench_projection()
            if projection is None:
                self.refresh_core_projections()
                projection = self.projection_repository.get_object_workbench_projection()
            if projection is None:
                raise RuntimeError("Object workbench projection refresh failed")
            return P4ObjectWorkbenchReadEnvelope(meta=projection.meta, data=projection)

        snapshot = self.get_state_snapshot()
        projection = self._build_object_workbench_projection(
            snapshot,
            sheet_id=sheet_id,
            item_id=item_id,
            tool_id=tool_id,
        )
        return P4ObjectWorkbenchReadEnvelope(meta=snapshot.meta, data=projection)

    def refresh_core_projections(self) -> ProjectionRefreshResult:
        snapshot = self.get_state_snapshot()
        overview = self._build_overview_projection(snapshot)
        tool_list = self._build_tool_list_projection(snapshot)
        evolution = self._build_evolution_workspace_projection(snapshot)
        object_workbench = self._build_object_workbench_projection(snapshot)
        self.projection_repository.save_overview_projection(overview)
        self.projection_repository.save_tool_list_projection(tool_list)
        self.projection_repository.save_evolution_workspace_projection(evolution)
        self.projection_repository.save_object_workbench_projection(object_workbench)
        return ProjectionRefreshResult(
            snapshot_id=snapshot.meta.snapshot_id,
            generated_at=snapshot.meta.generated_at,
            refreshed_projection_names=["overview", "tool_list", "evolution_workspace", "object_workbench"],
        )

    def _build_catalogs(self) -> ToolHubCatalogs:
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

    def _ensure_core_projections(self) -> None:
        if self.projection_repository.has_core_projections():
            return
        self.refresh_core_projections()

    def _build_overview_projection(self, snapshot: ToolHubStateSnapshot) -> OverviewProjection:
        overview = project_tool_hub_overview(snapshot)
        return OverviewProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            overview=overview,
            metric_total_tools=overview.metrics.tool_count,
            metric_verified_tools=overview.metrics.verified_tool_count,
            metric_pending_manufacture=sum(item.manufacturing_count for item in snapshot.raw.demand_sheets),
            metric_pending_evolution_tasks=len(
                [item for item in snapshot.raw.evolution_tasks if item.task_status in {"queued", "running"}]
            ),
        )

    def _build_tool_list_projection(self, snapshot: ToolHubStateSnapshot) -> ToolListProjection:
        return ToolListProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            items=snapshot.raw.tools,
        )

    def _build_evolution_workspace_projection(self, snapshot: ToolHubStateSnapshot) -> EvolutionWorkspaceProjection:
        return EvolutionWorkspaceProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            config=snapshot.raw.evolution_config,
            runs=snapshot.raw.evolution_runs,
            tasks=snapshot.raw.evolution_tasks,
        )

    def _build_object_workbench_projection(
        self,
        snapshot: ToolHubStateSnapshot,
        *,
        sheet_id: str | None = None,
        item_id: str | None = None,
        tool_id: str | None = None,
    ) -> P4ObjectWorkbenchProjection:
        sheets = snapshot.raw.demand_sheets
        active_sheet = self._hydrate_sheet(
            self._resolve_active_sheet(sheets, sheet_id),
        )
        active_item = self._resolve_active_item(active_sheet, item_id)
        selected_tool = self._resolve_selected_tool(snapshot.raw.tools, active_item, tool_id)
        manufacture_plan = self._resolve_manufacture_plan(active_item)
        active_items = self._resolve_active_items()
        hot_tools = [*snapshot.raw.tools]
        hot_tools.sort(key=lambda tool: tool.updated_at, reverse=True)
        hot_tools = hot_tools[:3]
        cold_tools = [tool for tool in snapshot.raw.tools if tool.status != "active"][:3]
        hot_domains = snapshot.raw.catalogs.domains[:3]
        cold_domains = snapshot.raw.catalogs.domains[-3:]
        used_by_items = self._resolve_used_by_items(selected_tool, active_sheet)
        return P4ObjectWorkbenchProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            object_tabs=[
                P4ObjectViewTab(key="pool", title="工单池与工单", caption="池 / 单 / 工具"),
                P4ObjectViewTab(key="processing", title="工单处理", caption="生命周期与进展"),
                P4ObjectViewTab(key="build", title="工具构建", caption="匹配 / 生产 / 过程值"),
                P4ObjectViewTab(key="usage", title="取用驾驶舱", caption="热点 / 冷门 / 使用热度"),
                P4ObjectViewTab(key="registry", title="工具资源列表", caption="资产大页"),
                P4ObjectViewTab(key="graph", title="覆盖知识图谱", caption="业务变化 / 时序变化"),
                P4ObjectViewTab(key="asset", title="成品工具属性", caption="使用工程与演进关系"),
                P4ObjectViewTab(key="config", title="演进配置", caption="巡检 / 触发 / 编辑"),
                P4ObjectViewTab(key="lineage", title="演进轨迹", caption="主干 / 分支 / 回退"),
            ],
            workorder_pool=WorkorderPoolProjection(
                sheets=sheets,
                active_sheet=active_sheet,
            ),
            workorder_processing=WorkorderProcessingProjection(
                active_sheet=active_sheet,
                active_item=active_item,
            ),
            tool_build=ToolBuildProjection(
                selected_tool=selected_tool,
                active_item=active_item,
                manufacture_plan=manufacture_plan,
            ),
            usage_cockpit=UsageCockpitProjection(
                active_items=active_items,
                hot_tools=hot_tools,
                cold_tools=cold_tools,
                hot_domains=hot_domains,
                cold_domains=cold_domains,
            ),
            tool_resources=ToolResourcesProjection(
                tools=snapshot.raw.tools,
            ),
            coverage_knowledge_graph=CoverageKnowledgeGraphProjection(
                matrix=snapshot.derived.coverage_matrix,
            ),
            delivered_tool_attribute=DeliveredToolAttributeProjection(
                selected_tool=selected_tool,
                used_by_items=used_by_items,
                evolution_task_count=len(snapshot.raw.evolution_tasks),
                rollback_available_count=len([task for task in snapshot.raw.evolution_tasks if task.rollback_available]),
            ),
            evolution_config=EvolutionConfigProjection(
                config=snapshot.raw.evolution_config,
            ),
            evolution_lineage=EvolutionLineageProjection(
                runs=snapshot.raw.evolution_runs,
                tasks=snapshot.raw.evolution_tasks,
            ),
        )

    def _resolve_active_sheet(self, sheets: list[ToolDemandSheet], sheet_id: str | None) -> ToolDemandSheet | None:
        if sheet_id is not None:
            for sheet in sheets:
                if sheet.sheet_id == sheet_id:
                    return sheet
        return sheets[0] if sheets else None

    def _hydrate_sheet(self, sheet: ToolDemandSheet | None) -> ToolDemandSheetDetail | None:
        if sheet is None:
            return None
        items = self.repository.list_demand_items(sheet.sheet_id)
        ordered_items = [item for item_id in sheet.item_ids for item in items if item.item_id == item_id]
        if not ordered_items:
            ordered_items = items
        return ToolDemandSheetDetail(**sheet.model_dump(mode="json"), items=ordered_items)

    def _resolve_active_item(
        self,
        active_sheet: ToolDemandSheetDetail | None,
        item_id: str | None,
    ) -> ToolDemandItem | None:
        if active_sheet is None or not active_sheet.items:
            return None
        if item_id is not None:
            for item in active_sheet.items:
                if item.item_id == item_id:
                    return item
        return active_sheet.items[0]

    def _resolve_selected_tool(
        self,
        tools: list[ToolDefinition],
        active_item: ToolDemandItem | None,
        tool_id: str | None,
    ) -> ToolDefinition | None:
        if tool_id is not None:
            for tool in tools:
                if tool.tool_id == tool_id:
                    return tool
        if active_item is not None and active_item.recommended_tool_id is not None:
            for tool in tools:
                if tool.tool_id == active_item.recommended_tool_id:
                    return tool
        return tools[0] if tools else None

    def _resolve_manufacture_plan(self, active_item: ToolDemandItem | None) -> ToolManufacturePlanView | None:
        if active_item is None:
            return None
        plan = self.repository.get_manufacture_plan(active_item.item_id)
        if plan is None:
            return None
        return ToolManufacturePlanView(
            plan_id=plan.plan_id,
            item_id=plan.item_id,
            sheet_id=active_item.sheet_id,
            component_name=active_item.component_name,
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

    def _resolve_active_items(self) -> list[ToolDemandItem]:
        return [
            item
            for item in self.repository.list_demand_items()
            if item.supply_result is not None and item.supply_result.result_type in {"existing_tool", "manufactured_tool"}
        ]

    def _resolve_used_by_items(
        self,
        selected_tool: ToolDefinition | None,
        active_sheet: ToolDemandSheetDetail | None,
    ) -> list[ToolDemandItem]:
        if selected_tool is None:
            return []
        candidates = self.repository.list_demand_items()
        if active_sheet is not None:
            candidates = [*active_sheet.items, *[item for item in candidates if item.sheet_id != active_sheet.sheet_id]]
        used_by_items = [
            item
            for item in candidates
            if item.recommended_tool_id == selected_tool.tool_id
            or (item.supply_result is not None and item.supply_result.tool_ref == selected_tool.tool_id)
        ]
        seen: set[str] = set()
        ordered_items: list[ToolDemandItem] = []
        for item in used_by_items:
            if item.item_id in seen:
                continue
            seen.add(item.item_id)
            ordered_items.append(item)
        return ordered_items
