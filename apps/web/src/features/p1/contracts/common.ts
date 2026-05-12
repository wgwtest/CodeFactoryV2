export type P1SourceKind = "live" | "fixture" | "mock_fallback";

export type P1LifecycleStatus =
  | "draft"
  | "published"
  | "deprecated"
  | "candidate"
  | "governance_pending"
  | "formalized";

export type P1RunStatus = "pending" | "running" | "completed" | "warning" | "blocked" | "failed";

export type P1StageStatus = "not_started" | "pending" | "running" | "completed" | "warning" | "blocked" | "skipped";

export type P1HealthLevel = "good" | "watch" | "risk" | "broken";

export type P1RuleEffectKind =
  | "filter"
  | "score"
  | "normalize"
  | "merge"
  | "split"
  | "block"
  | "publish_candidate"
  | "custom";

export type P1MetricScope = "document" | "stage" | "rule" | "knowledge_item" | "relation" | "graph" | "archive";

export interface P1ArtifactRef {
  artifact_id: string;
  artifact_type: string;
  stage_id?: string;
  document_id?: string;
  uri?: string;
  hash?: string;
  summary?: string;
  metadata?: Record<string, unknown>;
}

export interface P1TraceRef {
  trace_id: string;
  source_kind: "runtime" | "policy" | "quality" | "publication" | "governance" | "external";
  object_ids: string[];
  summary?: string;
}

export interface P1ResponseEnvelope<TPayload> {
  contract_version: string;
  source_kind: P1SourceKind;
  generated_at: string;
  data: TPayload;
  warnings?: string[];
}
