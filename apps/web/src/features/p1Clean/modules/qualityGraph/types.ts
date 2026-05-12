export type QualityMetric = {
  metric_id: string;
  metric_name: string;
  scope: "document" | "stage" | "rule" | "knowledge_item" | "relation" | "graph" | "archive";
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
};

export type QualityArtifactRef = {
  artifact_id: string;
  artifact_type: string;
  stage_id?: string | null;
  document_id?: string | null;
  uri?: string | null;
  hash?: string | null;
  summary?: string | null;
  metadata: Record<string, unknown>;
};

export type QualityRuleHitExplanation = {
  hit_id: string;
  rule_id: string;
  rule_version: string;
  rule_hash: string;
  stage_id: string;
  decision: string;
  metric_ids: string[];
  input_artifact_refs: QualityArtifactRef[];
  output_artifact_refs: QualityArtifactRef[];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  evidence_anchor_ids: string[];
  explanation: string;
};

export type QualityMetricHitExplanation = {
  hit_id: string;
  metric_id: string;
  actual: number;
  threshold: number;
  threshold_direction: "gte" | "lte";
  status: QualityMetric["status"];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  rule_execution_record_ids: string[];
  evidence_anchor_ids: string[];
  explanation: string;
};

export type QualityFinding = {
  finding_id: string;
  scope: "item" | "relation" | "publication" | "evidence" | "category" | "system_output";
  severity: "info" | "warning" | "blocked";
  code: string;
  message: string;
  target_id?: string | null;
  target_type?: string | null;
  evidence_refs: QualityArtifactRef[];
  suggested_action: string;
  blocking_publish: boolean;
  metadata: Record<string, string | number | boolean | null>;
};

export type QualityFindingReport = {
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
};

export type QualityGateDecision = {
  decision: "auto_pass" | "warn_continue" | "block" | "defer";
  score: number;
  metric_results: QualityMetric[];
  rule_hits: QualityRuleHitExplanation[];
  metric_hits: QualityMetricHitExplanation[];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  output_action: "publish_candidate" | "publish_candidate_with_warning" | "return_for_rebuild" | "delay_publication";
  explanation: string;
  generated_at: string;
};

export type KnowledgeQualityReport = {
  report_id: string;
  archive_id: string;
  run_id: string;
  document_id: string | null;
  policy_snapshot_id: string | null;
  resolution_snapshot_id: string | null;
  health_level: "good" | "watch" | "risk" | "broken";
  concept_precision: number;
  evidence_coverage: number;
  conflict_rate: number;
  duplicate_rate: number;
  stale_object_count: number;
  metrics: QualityMetric[];
  gate_decision: QualityGateDecision | null;
  recommended_actions: string[];
};

export type GraphQualityReport = {
  report_id: string;
  archive_id: string;
  run_id: string | null;
  graph_projection_id: string;
  graph_scope: "runtime" | "published";
  health_level: "good" | "watch" | "risk" | "broken";
  relation_confidence_avg: number;
  orphan_node_rate: number;
  duplicate_relation_rate: number;
  explainability_coverage: number;
  layout_readability: number;
  metrics: QualityMetric[];
};

export type QualityEvaluationReport = {
  evaluation_id: string;
  archive_id: string;
  run_id: string;
  generated_at: string;
  knowledge_quality: KnowledgeQualityReport;
  graph_quality: GraphQualityReport;
  gate_decision: QualityGateDecision;
  rule_hits: QualityRuleHitExplanation[];
  metric_hits: QualityMetricHitExplanation[];
  quality_finding_report?: QualityFindingReport | null;
  data_lineage: QualityArtifactRef[];
};

export type QualityGraphReportEnvelope = {
  contract_version: string;
  source_kind: "live" | "fixture" | "mock_fallback";
  generated_at: string;
  data: QualityEvaluationReport;
  warnings: string[];
};

export type QualityMetricSummary = {
  evidenceCoverage: number;
  relationCompleteness: number;
  orphanNodeRate: number;
  crossDocumentVerificationCount: number;
  mergedObjectCount: number;
  conflictObjectCount: number;
  lowConfidenceObjectCount: number;
  ruleHitCount: number;
};

export type QualityGraphModuleOutput = {
  qualityDecisionId: string;
};
