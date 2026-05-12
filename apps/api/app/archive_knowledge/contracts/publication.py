from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef
from app.archive_knowledge.contracts.quality_findings import QualityFindingReport


PublicationCandidateStatus = Literal[
    "machine_candidate_created",
    "governance_pending",
    "formalized",
    "blocked_by_quality",
    "stale_after_policy_change",
    "candidate",
    "draft",
    "published",
    "deprecated",
]


class PublicationCandidateSummary(BaseModel):
    publication_snapshot_id: str | None = None
    status_label: str = "待生成候选快照"
    source_scope: str = "post_quality_gate_publication_candidate"
    generated_from_runtime_snapshot_id: str | None = None
    candidate_count: int = 0
    candidate_knowledge_count: int = 0


class PublicationQualityDecisionSummary(BaseModel):
    decision: str = "pending"
    output_action: str = "delay_publication"
    score: float | None = None
    explanation: str = "等待质量门禁决策"
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)


class GovernanceStatusProjection(BaseModel):
    governance_confirmation_status: Literal["not_ready", "waiting_confirmation", "confirmed", "rejected"] = (
        "not_ready"
    )
    governance_confirmation_label: str = "未进入治理确认"
    formal_entry_status: Literal["not_admitted", "admitted"] = "not_admitted"
    formal_entry_label: str = "尚未正式入库"
    confirmation_required: bool = True


class ApiExposureScope(BaseModel):
    readonly_candidate_api_paths: list[str] = Field(default_factory=list)
    readonly_formal_api_paths: list[str] = Field(default_factory=list)
    index_names: list[str] = Field(default_factory=list)
    exposure_mode: Literal["candidate_preview_only", "formal_supply", "blocked"] = "candidate_preview_only"
    not_supply_reason: str | None = "候选快照尚未经过治理确认，禁止作为正式知识供应。"


class PublicationCandidateObject(BaseModel):
    object_id: str
    canonical_name: str
    object_type: str
    source_document_ids: list[str] = Field(default_factory=list)
    source_candidate_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality_status: Literal["passed", "warning", "blocked", "stale"] = "warning"
    governance_status: Literal["pending", "approved", "rejected", "superseded"] = "pending"
    version: str | None = None
    source_snapshot_id: str | None = None


class PublicationCandidateRelation(BaseModel):
    relation_id: str
    source_object_id: str
    target_object_id: str
    relation_type: str
    source_document_ids: list[str] = Field(default_factory=list)
    source_candidate_relation_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality_status: Literal["passed", "warning", "blocked", "stale"] = "warning"
    governance_status: Literal["pending", "approved", "rejected", "superseded"] = "pending"
    source_snapshot_id: str | None = None


class PublicationCandidateSnapshot(BaseModel):
    publication_candidate_snapshot_id: str
    archive_id: str
    run_id: str
    runtime_snapshot_id: str | None = None
    policy_package_version_id: str | None = None
    resolution_snapshot_id: str | None = None
    generated_at: str
    status: PublicationCandidateStatus
    governance_status: Literal["pending", "approved", "rejected", "superseded"]
    publication_snapshot_id: str | None = None
    candidate_summary: PublicationCandidateSummary = Field(default_factory=PublicationCandidateSummary)
    quality_decision_summary: PublicationQualityDecisionSummary = Field(
        default_factory=PublicationQualityDecisionSummary
    )
    quality_decision: PublicationQualityDecisionSummary = Field(default_factory=PublicationQualityDecisionSummary)
    quality_finding_report: QualityFindingReport | None = None
    governance_projection: GovernanceStatusProjection = Field(default_factory=GovernanceStatusProjection)
    candidate_objects: list[PublicationCandidateObject] = Field(default_factory=list)
    candidate_relations: list[PublicationCandidateRelation] = Field(default_factory=list)
    candidate_knowledge_refs: list[ArtifactRef] = Field(default_factory=list)
    api_exposure_scope: ApiExposureScope


class PublishedKnowledgeSnapshot(BaseModel):
    published_snapshot_id: str
    archive_id: str
    publication_candidate_snapshot_id: str
    formal_version: str
    published_at: str
    governed_by: str
    api_paths: list[str] = Field(default_factory=list)
