from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import P1StageStatus


class RuntimeGraphNode(BaseModel):
    node_id: str
    label: str
    node_type: Literal["input_object", "rule", "action", "output_object", "quality_metric", "publication", "collection"]
    stage_id: str
    status: P1StageStatus
    semantic_role: Literal["input", "basis", "action", "output", "context"]
    object_count: int | None = None
    payload_ref: str | None = None


class RuntimeGraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    relation: str
    stage_id: str
    evidence: str | None = None


class RuntimeGraphProjection(BaseModel):
    graph_projection_id: str
    archive_id: str
    document_id: str
    view_mode: Literal["semantic_aggregate", "detail"] = "semantic_aggregate"
    layout_strategy: Literal["layered_dag", "force_assist", "manual_adjusted"] = "layered_dag"
    nodes: list[RuntimeGraphNode] = Field(default_factory=list)
    edges: list[RuntimeGraphEdge] = Field(default_factory=list)
    highlighted_node_ids: list[str] = Field(default_factory=list)
    highlighted_edge_ids: list[str] = Field(default_factory=list)
