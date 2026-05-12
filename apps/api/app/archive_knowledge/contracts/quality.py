from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef, P1HealthLevel, P1MetricScope
from app.archive_knowledge.contracts.quality_findings import QualityFindingReport


class QualityMetric(BaseModel):
    metric_id: str
    metric_name: str
    scope: P1MetricScope
    actual: float
    threshold: float
    threshold_direction: Literal["gte", "lte"] = "gte"
    status: Literal["pass", "warning", "fail"]
    explanation: str
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    rule_execution_record_ids: list[str] = Field(default_factory=list)
    input_artifact_ids: list[str] = Field(default_factory=list)
    output_artifact_ids: list[str] = Field(default_factory=list)
    evidence_anchor_ids: list[str] = Field(default_factory=list)


class RuleHitExplanation(BaseModel):
    hit_id: str
    rule_id: str
    rule_version: str
    rule_hash: str
    stage_id: str
    decision: str
    metric_ids: list[str] = Field(default_factory=list)
    input_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    output_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    evidence_anchor_ids: list[str] = Field(default_factory=list)
    explanation: str


class MetricHitExplanation(BaseModel):
    hit_id: str
    metric_id: str
    actual: float
    threshold: float
    threshold_direction: Literal["gte", "lte"] = "gte"
    status: Literal["pass", "warning", "fail"]
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    rule_execution_record_ids: list[str] = Field(default_factory=list)
    evidence_anchor_ids: list[str] = Field(default_factory=list)
    explanation: str


class QualityGateDecision(BaseModel):
    decision: Literal["auto_pass", "warn_continue", "block", "defer"]
    score: float
    metric_results: list[QualityMetric] = Field(default_factory=list)
    rule_hits: list[RuleHitExplanation] = Field(default_factory=list)
    metric_hits: list[MetricHitExplanation] = Field(default_factory=list)
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    output_action: Literal["publish_candidate", "publish_candidate_with_warning", "return_for_rebuild", "delay_publication"]
    explanation: str
    generated_at: str


class KnowledgeQualityReport(BaseModel):
    report_id: str
    archive_id: str
    run_id: str
    document_id: str | None = None
    policy_snapshot_id: str | None = None
    resolution_snapshot_id: str | None = None
    health_level: P1HealthLevel
    concept_precision: float
    evidence_coverage: float
    conflict_rate: float
    duplicate_rate: float = 0
    stale_object_count: int
    metrics: list[QualityMetric] = Field(default_factory=list)
    gate_decision: QualityGateDecision | None = None
    recommended_actions: list[str] = Field(default_factory=list)


class GraphQualityReport(BaseModel):
    report_id: str
    archive_id: str
    run_id: str | None = None
    graph_projection_id: str
    graph_scope: Literal["runtime", "published"] = "runtime"
    health_level: P1HealthLevel
    relation_confidence_avg: float
    orphan_node_rate: float
    duplicate_relation_rate: float
    explainability_coverage: float
    layout_readability: float = 1
    metrics: list[QualityMetric] = Field(default_factory=list)


class EvaluationRunReport(BaseModel):
    evaluation_id: str
    archive_id: str
    run_id: str
    generated_at: str
    knowledge_quality: KnowledgeQualityReport
    graph_quality: GraphQualityReport
    gate_decision: QualityGateDecision
    rule_hits: list[RuleHitExplanation] = Field(default_factory=list)
    metric_hits: list[MetricHitExplanation] = Field(default_factory=list)
    quality_finding_report: QualityFindingReport | None = None
    data_lineage: list[ArtifactRef] = Field(default_factory=list)
