from __future__ import annotations

from pydantic import BaseModel, Field

from app.tool_hub.models import (
    CatalogItem,
    CoverageMatrix,
    EvolutionInspectionConfig,
    EvolutionRun,
    EvolutionTask,
    ToolDefinition,
    ToolDemandItem,
    ToolDemandSheet,
    ToolDemandSheetDetail,
    ToolHubOverview,
    ToolHubSnapshotMeta,
    ToolManufacturePlanView,
    now_iso,
)


class OverviewProjection(BaseModel):
    snapshot_id: str
    meta: ToolHubSnapshotMeta
    overview: ToolHubOverview
    metric_total_tools: int
    metric_verified_tools: int
    metric_pending_manufacture: int
    metric_pending_evolution_tasks: int


class ToolListProjection(BaseModel):
    snapshot_id: str
    meta: ToolHubSnapshotMeta
    items: list[ToolDefinition]


class EvolutionWorkspaceProjection(BaseModel):
    snapshot_id: str
    meta: ToolHubSnapshotMeta
    config: EvolutionInspectionConfig
    runs: list[EvolutionRun]
    tasks: list[EvolutionTask]


class P4ObjectViewTab(BaseModel):
    key: str
    title: str
    caption: str


class WorkorderPoolProjection(BaseModel):
    sheets: list[ToolDemandSheet]
    active_sheet: ToolDemandSheetDetail | None = None


class WorkorderProcessingProjection(BaseModel):
    active_sheet: ToolDemandSheetDetail | None = None
    active_item: ToolDemandItem | None = None


class ToolBuildProjection(BaseModel):
    selected_tool: ToolDefinition | None = None
    active_item: ToolDemandItem | None = None
    manufacture_plan: ToolManufacturePlanView | None = None


class UsageCockpitProjection(BaseModel):
    active_items: list[ToolDemandItem]
    hot_tools: list[ToolDefinition]
    cold_tools: list[ToolDefinition]
    hot_domains: list[CatalogItem]
    cold_domains: list[CatalogItem]


class ToolResourcesProjection(BaseModel):
    tools: list[ToolDefinition]


class CoverageKnowledgeGraphProjection(BaseModel):
    matrix: CoverageMatrix


class DeliveredToolAttributeProjection(BaseModel):
    selected_tool: ToolDefinition | None = None
    used_by_items: list[ToolDemandItem]
    evolution_task_count: int = 0
    rollback_available_count: int = 0


class EvolutionConfigProjection(BaseModel):
    config: EvolutionInspectionConfig


class EvolutionLineageProjection(BaseModel):
    runs: list[EvolutionRun]
    tasks: list[EvolutionTask]


class P4ObjectWorkbenchProjection(BaseModel):
    snapshot_id: str
    meta: ToolHubSnapshotMeta
    object_tabs: list[P4ObjectViewTab]
    workorder_pool: WorkorderPoolProjection
    workorder_processing: WorkorderProcessingProjection
    tool_build: ToolBuildProjection
    usage_cockpit: UsageCockpitProjection
    tool_resources: ToolResourcesProjection
    coverage_knowledge_graph: CoverageKnowledgeGraphProjection
    delivered_tool_attribute: DeliveredToolAttributeProjection
    evolution_config: EvolutionConfigProjection
    evolution_lineage: EvolutionLineageProjection


class P4ObjectWorkbenchReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: P4ObjectWorkbenchProjection


class ProjectionRefreshResult(BaseModel):
    snapshot_id: str
    generated_at: str = Field(default_factory=now_iso)
    refreshed_projection_names: list[str]
