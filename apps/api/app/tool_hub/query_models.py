from __future__ import annotations

from pydantic import BaseModel

from app.tool_hub.models import (
    EvolutionInspectionConfig,
    EvolutionRun,
    EvolutionTask,
    ToolDefinition,
    ToolHubOverview,
    ToolHubSnapshotMeta,
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
