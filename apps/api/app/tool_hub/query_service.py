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
from app.tool_hub.query_models import EvolutionWorkspaceProjection, OverviewProjection, ToolListProjection
from app.tool_hub.repository import ToolHubRepository
from app.tool_hub.snapshot import build_tool_hub_snapshot, project_tool_hub_overview


class ToolHubQueryService:
    def __init__(self, repository: ToolHubRepository) -> None:
        self.repository = repository

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
        snapshot = self.get_state_snapshot()
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

    def get_tool_list_projection(self) -> ToolListProjection:
        snapshot = self.get_state_snapshot()
        return ToolListProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            items=snapshot.raw.tools,
        )

    def get_evolution_workspace_projection(self) -> EvolutionWorkspaceProjection:
        snapshot = self.get_state_snapshot()
        return EvolutionWorkspaceProjection(
            snapshot_id=snapshot.meta.snapshot_id,
            meta=snapshot.meta,
            config=snapshot.raw.evolution_config,
            runs=snapshot.raw.evolution_runs,
            tasks=snapshot.raw.evolution_tasks,
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
