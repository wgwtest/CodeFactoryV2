from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RuntimeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"


class RuntimeOrigin(StrEnum):
    SOURCE = "source"
    DERIVED = "derived"
    UNAVAILABLE = "unavailable"


class RuntimeObserverMode(StrEnum):
    STAGE = "stage"
    NODE = "node"
    EDGE = "edge"


class RuntimeAction(BaseModel):
    action_id: str
    label: str
    target_kind: Literal["stage", "node", "edge", "document", "item", "evidence", "graph"]
    target_id: str | None = None


class RuntimeSummaryField(BaseModel):
    key: str
    label: str
    value: str
    tone: Literal["neutral", "success", "warning", "danger", "info"] = "neutral"


class RuntimeSummarySection(BaseModel):
    section_id: str
    title: str
    fields: list[RuntimeSummaryField] = Field(default_factory=list)


class RuntimeEvent(BaseModel):
    event_id: str
    kind: Literal["progress", "decision", "evidence", "rule", "warning", "block", "result", "info"]
    level: Literal["neutral", "success", "warning", "danger", "info"] = "neutral"
    message: str
    object_id: str | None = None
    object_kind: Literal["stage", "node", "edge", "document", "item", "evidence"] | None = None
    timestamp: str | None = None


class RuntimeGraphNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    stage_id: str
    status: RuntimeStatus
    origin: RuntimeOrigin = RuntimeOrigin.SOURCE
    is_primary: bool = False
    is_focus: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RuntimeGraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    relation: str
    stage_id: str
    status: RuntimeStatus
    origin: RuntimeOrigin = RuntimeOrigin.SOURCE
    is_primary: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class RuntimeObserverPayload(BaseModel):
    mode: RuntimeObserverMode
    title: str
    subtitle: str | None = None
    status: RuntimeStatus
    stream: list[RuntimeEvent] = Field(default_factory=list)
    sections: list[RuntimeSummarySection] = Field(default_factory=list)
    actions: list[RuntimeAction] = Field(default_factory=list)


class RuntimeStageGraph(BaseModel):
    nodes: list[RuntimeGraphNode] = Field(default_factory=list)
    edges: list[RuntimeGraphEdge] = Field(default_factory=list)
    primary_node_ids: list[str] = Field(default_factory=list)
    primary_edge_ids: list[str] = Field(default_factory=list)


class RuntimeStageSnapshot(BaseModel):
    stage_id: str
    label: str
    group: str
    order: int
    status: RuntimeStatus
    is_current: bool = False
    graph: RuntimeStageGraph
    stage_observer: RuntimeObserverPayload
    node_observers: dict[str, RuntimeObserverPayload] = Field(default_factory=dict)
    edge_observers: dict[str, RuntimeObserverPayload] = Field(default_factory=dict)


class RuntimePolicySnapshotRule(BaseModel):
    key: str
    name: str
    meaning: str = ""
    threshold: str = ""
    action: str


class RuntimePolicySnapshotStage(BaseModel):
    stage_id: str
    label: str
    enabled: bool
    ai_mode: str
    default_action: str
    rule_count: int = 0
    rules: list[RuntimePolicySnapshotRule] = Field(default_factory=list)


class RuntimePolicySnapshot(BaseModel):
    snapshot_id: str
    captured_at: str | None = None
    archive_id: str
    version_label: str
    scope_label: str
    ai_autoadapt_enabled: bool = True
    config_updated_at: str | None = None
    stage_order: list[str] = Field(default_factory=list)
    stages: list[RuntimePolicySnapshotStage] = Field(default_factory=list)


class DocumentRuntimeContract(BaseModel):
    archive_id: str
    document_id: str
    document_title: str
    current_stage_id: str
    current_stage_label: str
    status: RuntimeStatus
    runtime_mode: Literal["persisted", "hybrid", "derived", "legacy_fallback"] = "derived"
    persisted_stage_ids: list[str] = Field(default_factory=list)
    source_document: dict[str, Any] = Field(default_factory=dict)
    policy_snapshot: RuntimePolicySnapshot | None = None
    stages: list[RuntimeStageSnapshot] = Field(default_factory=list)


class RuntimeStageDefinition(BaseModel):
    stage_id: str
    label: str
    group: str
    order: int


STAGE_DEFINITIONS: tuple[RuntimeStageDefinition, ...] = (
    RuntimeStageDefinition(stage_id="asset_intake", label="Asset Intake", group="Asset Intake and Normalization", order=1),
    RuntimeStageDefinition(stage_id="parser_router", label="Parser Router", group="Asset Intake and Normalization", order=2),
    RuntimeStageDefinition(stage_id="parser_execution", label="Parser Execution", group="Asset Intake and Normalization", order=3),
    RuntimeStageDefinition(stage_id="unified_document_object", label="Unified Document Object", group="Asset Intake and Normalization", order=4),
    RuntimeStageDefinition(stage_id="evidence_constructor", label="Evidence Constructor", group="Evidence and Knowledge Generation", order=5),
    RuntimeStageDefinition(stage_id="evidence_graph_chunk_layer", label="Evidence Graph / Chunk Layer", group="Evidence and Knowledge Generation", order=6),
    RuntimeStageDefinition(stage_id="evidence_pack", label="Evidence Pack", group="Evidence and Knowledge Generation", order=7),
    RuntimeStageDefinition(stage_id="concept_candidate_review", label="Concept Candidate Review", group="Evidence and Knowledge Generation", order=8),
    RuntimeStageDefinition(
        stage_id="relation_review_family_normalization",
        label="Relation Review / Family Normalization",
        group="Evidence and Knowledge Generation",
        order=9,
    ),
    RuntimeStageDefinition(
        stage_id="definition_summary_conflict_consolidation",
        label="Definition / Summary / Conflict Consolidation",
        group="Evidence and Knowledge Generation",
        order=10,
    ),
    RuntimeStageDefinition(stage_id="canonical_knowledge", label="Canonical Knowledge", group="Canonicalization and Publication", order=11),
    RuntimeStageDefinition(
        stage_id="quality_policy_evaluation_governance_gate",
        label="Quality Policy Evaluation / Governance Gate",
        group="Canonicalization and Publication",
        order=12,
    ),
    RuntimeStageDefinition(stage_id="indexes_snapshots_apis", label="Indexes / Snapshots / APIs", group="Canonicalization and Publication", order=13),
)


STAGE_DEFINITION_MAP = {definition.stage_id: definition for definition in STAGE_DEFINITIONS}
