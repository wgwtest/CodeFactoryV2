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
from app.tool_hub.models import ToolHubCatalogs, ToolHubStateSnapshot
from app.tool_hub.projection_repository import ToolHubProjectionRepository
from app.tool_hub.query_models import (
    EvolutionWorkspaceProjection,
    OverviewProjection,
    ProjectionRefreshResult,
    ToolListProjection,
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

    def refresh_core_projections(self) -> ProjectionRefreshResult:
        snapshot = self.get_state_snapshot()
        overview = self._build_overview_projection(snapshot)
        tool_list = self._build_tool_list_projection(snapshot)
        evolution = self._build_evolution_workspace_projection(snapshot)
        self.projection_repository.save_overview_projection(overview)
        self.projection_repository.save_tool_list_projection(tool_list)
        self.projection_repository.save_evolution_workspace_projection(evolution)
        return ProjectionRefreshResult(
            snapshot_id=snapshot.meta.snapshot_id,
            generated_at=snapshot.meta.generated_at,
            refreshed_projection_names=["overview", "tool_list", "evolution_workspace"],
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
