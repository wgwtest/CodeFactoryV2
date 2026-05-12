from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef, P1LifecycleStatus


class KnowledgeIdentityKey(BaseModel):
    identity_key_id: str
    knowledge_type: str
    normalized_name: str
    business_scope: str
    key_fields: dict[str, str] = Field(default_factory=dict)
    alias_tokens: list[str] = Field(default_factory=list)
    definition_signature: str | None = None
    relation_neighborhood_hash: str | None = None
    policy_snapshot_id: str | None = None
    generated_by_rule_execution_id: str | None = None


class CrossDocumentMatchCandidate(BaseModel):
    candidate_id: str
    identity_key: KnowledgeIdentityKey
    source_candidate_item_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    similarity_score: float
    match_features: dict[str, float] = Field(default_factory=dict)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    suggested_action: Literal["merge", "keep_separate", "replace", "mark_conflict"]
    explanation: str | None = None
    generated_at: str | None = None


class KnowledgeMergeDecision(BaseModel):
    decision_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    source_candidate_item_ids: list[str] = Field(default_factory=list)
    decision: Literal["merged", "kept_separate", "replaced", "conflict_pending"]
    reason: str
    rule_execution_record_ids: list[str] = Field(default_factory=list)
    requires_governance_confirmation: bool = False
    generated_at: str | None = None


class CanonicalKnowledgeItem(BaseModel):
    knowledge_id: str
    identity_key: KnowledgeIdentityKey
    status: P1LifecycleStatus
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    source_candidate_item_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    relation_refs: list[str] = Field(default_factory=list)
    version: str
    quality_summary: dict[str, Any] = Field(default_factory=dict)


class ResolvedKnowledgeObject(BaseModel):
    object_id: str
    canonical_name: str
    object_type: str
    source_candidate_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    merge_decision: Literal["single_source", "merged", "kept_separate", "replaced", "conflict_pending"] = (
        "single_source"
    )
    conflict_status: Literal["clean", "conflict_pending", "low_confidence", "stale", "rule_conflict"] = "clean"
    identity_key: KnowledgeIdentityKey | None = None
    aliases: list[str] = Field(default_factory=list)
    resolution_trace_ids: list[str] = Field(default_factory=list)
    quality_summary: dict[str, Any] = Field(default_factory=dict)


class ResolvedKnowledgeRelation(BaseModel):
    relation_id: str
    source_object_id: str
    target_object_id: str
    relation_type: str
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    source_candidate_relation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    resolution_trace_ids: list[str] = Field(default_factory=list)


class KnowledgeResolutionTrace(BaseModel):
    trace_id: str
    trace_type: Literal[
        "object_resolution",
        "relation_resolution",
        "merge_decision",
        "conflict",
        "stale_update",
        "relation_skipped",
    ]
    object_ids: list[str] = Field(default_factory=list)
    relation_ids: list[str] = Field(default_factory=list)
    source_candidate_ids: list[str] = Field(default_factory=list)
    rule_execution_record_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeUpdatePlan(BaseModel):
    update_plan_id: str
    archive_id: str
    minimum_rebuild_stage_id: str
    stale_object_ids: list[str] = Field(default_factory=list)
    affected_knowledge_ids: list[str] = Field(default_factory=list)
    impacted_relation_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    requires_governance_confirmation: bool = False
    writes_official_knowledge: bool = False
    generated_at: str | None = None


class ArchiveKnowledgeResolutionSnapshot(BaseModel):
    snapshot_id: str
    archive_id: str
    run_id: str | None = None
    policy_snapshot_id: str | None = None
    runtime_snapshot_id: str | None = None
    policy_package_version_id: str | None = None
    input_document_ids: list[str] = Field(default_factory=list)
    generated_at: str
    match_candidates: list[CrossDocumentMatchCandidate] = Field(default_factory=list)
    merge_decisions: list[KnowledgeMergeDecision] = Field(default_factory=list)
    canonical_items: list[CanonicalKnowledgeItem] = Field(default_factory=list)
    resolved_objects: list[ResolvedKnowledgeObject] = Field(default_factory=list)
    resolved_relations: list[ResolvedKnowledgeRelation] = Field(default_factory=list)
    resolution_trace: list[KnowledgeResolutionTrace] = Field(default_factory=list)
    update_plan: KnowledgeUpdatePlan | None = None
    conflict_count: int = 0
    unsupported_count: int = 0
