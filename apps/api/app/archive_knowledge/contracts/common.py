from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field


PayloadT = TypeVar("PayloadT")

P1SourceKind = Literal["live", "fixture", "mock_fallback"]
P1LifecycleStatus = Literal["draft", "published", "deprecated", "candidate", "governance_pending", "formalized"]
P1RunStatus = Literal["pending", "running", "completed", "warning", "blocked", "failed"]
P1StageStatus = Literal["not_started", "pending", "running", "completed", "warning", "blocked", "skipped"]
P1HealthLevel = Literal["good", "watch", "risk", "broken"]
P1RuleEffectKind = Literal["filter", "score", "normalize", "merge", "split", "block", "publish_candidate", "custom"]
P1MetricScope = Literal["document", "stage", "rule", "knowledge_item", "relation", "graph", "archive"]


class ArtifactRef(BaseModel):
    artifact_id: str
    artifact_type: str
    stage_id: str | None = None
    document_id: str | None = None
    uri: str | None = None
    hash: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceRef(BaseModel):
    trace_id: str
    source_kind: Literal["runtime", "policy", "quality", "publication", "governance", "external"]
    object_ids: list[str] = Field(default_factory=list)
    summary: str | None = None


class P1ResponseEnvelope(BaseModel, Generic[PayloadT]):
    contract_version: str
    source_kind: P1SourceKind = "fixture"
    generated_at: str
    data: PayloadT
    warnings: list[str] = Field(default_factory=list)
