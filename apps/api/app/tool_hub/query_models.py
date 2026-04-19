from __future__ import annotations

from pydantic import BaseModel, Field

from app.tool_hub.models import (
    EvolutionInspectionConfig,
    EvolutionRun,
    EvolutionTask,
    ToolDefinition,
    ToolHubOverview,
    ToolHubSnapshotMeta,
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


class ProjectionRefreshResult(BaseModel):
    snapshot_id: str
    generated_at: str = Field(default_factory=now_iso)
    refreshed_projection_names: list[str]
