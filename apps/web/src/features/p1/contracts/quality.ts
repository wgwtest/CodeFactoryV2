import type { P1ArtifactRef, P1HealthLevel, P1MetricScope } from "./common";

export interface QualityMetric {
  metric_id: string;
  metric_name: string;
  scope: P1MetricScope;
  actual: number;
  threshold: number;
  threshold_direction: "gte" | "lte";
  status: "pass" | "warning" | "fail";
  explanation: string;
  affected_object_ids: string[];
  affected_relation_ids: string[];
  rule_execution_record_ids: string[];
  input_artifact_ids: string[];
  output_artifact_ids: string[];
  evidence_anchor_ids: string[];
}

export interface RuleHitExplanation {
  hit_id: string;
  rule_id: string;
  rule_version: string;
  rule_hash: string;
  stage_id: string;
  decision: string;
  metric_ids: string[];
  input_artifact_refs: P1ArtifactRef[];
  output_artifact_refs: P1ArtifactRef[];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  evidence_anchor_ids: string[];
  explanation: string;
}

export interface MetricHitExplanation {
  hit_id: string;
  metric_id: string;
  actual: number;
  threshold: number;
  threshold_direction: "gte" | "lte";
  status: "pass" | "warning" | "fail";
  affected_object_ids: string[];
  affected_relation_ids: string[];
  rule_execution_record_ids: string[];
  evidence_anchor_ids: string[];
  explanation: string;
}

export type QualityFindingScope = "item" | "relation" | "publication" | "evidence" | "category" | "system_output";
export type QualityFindingSeverity = "info" | "warning" | "blocked";

export interface QualityFinding {
  finding_id: string;
  scope: QualityFindingScope;
  severity: QualityFindingSeverity;
  code: string;
  message: string;
  target_id?: string | null;
  target_type?: string | null;
  evidence_refs: P1ArtifactRef[];
  suggested_action: string;
  blocking_publish: boolean;
  metadata: Record<string, string | number | boolean | null>;
}

export interface QualityFindingReport {
  report_id: string;
  archive_id: string;
  generated_at: string;
  resolution_snapshot_id?: string | null;
  publication_snapshot_id?: string | null;
  findings: QualityFinding[];
  summary: {
    finding_count: number;
    blocked_count: number;
    warning_count: number;
    info_count: number;
    publish_blocked: boolean;
  };
}

export interface QualityGateDecision {
  decision: "auto_pass" | "warn_continue" | "block" | "defer";
  score: number;
  metric_results: QualityMetric[];
  rule_hits: RuleHitExplanation[];
  metric_hits: MetricHitExplanation[];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  output_action: "publish_candidate" | "publish_candidate_with_warning" | "return_for_rebuild" | "delay_publication";
  explanation: string;
  generated_at: string;
}

export interface KnowledgeQualityReport {
  report_id: string;
  archive_id: string;
  run_id: string;
  document_id?: string;
  policy_snapshot_id?: string;
  resolution_snapshot_id?: string;
  health_level: P1HealthLevel;
  concept_precision: number;
  evidence_coverage: number;
  conflict_rate: number;
  duplicate_rate: number;
  stale_object_count: number;
  metrics: QualityMetric[];
  gate_decision?: QualityGateDecision;
  recommended_actions: string[];
}

export interface GraphQualityReport {
  report_id: string;
  archive_id: string;
  run_id?: string;
  graph_projection_id: string;
  graph_scope: "runtime" | "published";
  health_level: P1HealthLevel;
  relation_confidence_avg: number;
  orphan_node_rate: number;
  duplicate_relation_rate: number;
  explainability_coverage: number;
  layout_readability: number;
  metrics: QualityMetric[];
}

export interface EvaluationRunReport {
  evaluation_id: string;
  archive_id: string;
  run_id: string;
  generated_at: string;
  knowledge_quality: KnowledgeQualityReport;
  graph_quality: GraphQualityReport;
  gate_decision: QualityGateDecision;
  rule_hits: RuleHitExplanation[];
  metric_hits: MetricHitExplanation[];
  quality_finding_report?: QualityFindingReport | null;
  data_lineage: P1ArtifactRef[];
}
