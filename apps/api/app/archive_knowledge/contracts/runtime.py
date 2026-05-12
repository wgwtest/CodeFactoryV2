from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import P1RunStatus, P1StageStatus, TraceRef
from app.archive_knowledge.contracts.graph import RuntimeGraphProjection
from app.archive_knowledge.contracts.policy import PolicyRuntimeSnapshot
from app.archive_knowledge.contracts.rule import RuleExecutionRecord


class StageSnapshot(BaseModel):
    stage_id: str
    stage_name: str
    status: P1StageStatus
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
    input_object_count: int = 0
    output_object_count: int = 0
    rule_execution_record_ids: list[str] = Field(default_factory=list)
    graph_projection_id: str | None = None


class DocumentRuntimeSnapshot(BaseModel):
    archive_id: str
    document_id: str
    run_id: str
    status: P1RunStatus
    current_stage_id: str | None = None
    current_stage_message: str | None = None
    stream_status: Literal["connected", "fallback_polling", "disconnected", "not_started"] = "not_started"
    policy_snapshot: PolicyRuntimeSnapshot
    stage_snapshots: list[StageSnapshot] = Field(default_factory=list)
    graph_projection: RuntimeGraphProjection
    rule_execution_records: list[RuleExecutionRecord] = Field(default_factory=list)
    event_trace: list[TraceRef] = Field(default_factory=list)
