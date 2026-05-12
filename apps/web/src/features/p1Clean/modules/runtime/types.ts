import type {
  ArchiveDocumentRuntimeContract,
  ArchiveDocumentRuntimeEvent,
  ArchiveDocumentRuntimeGraphEdge,
  ArchiveDocumentRuntimeGraphNode,
  ArchiveDocumentRuntimeStageSnapshot,
  ArchiveDocumentRuntimeStatus,
  ArchiveKnowledgeDocument,
} from "../../../../lib/api";

export type RuntimeModuleInput = {
  archiveId: string;
  documentSetId: string;
  policyPackageVersionId: string;
  documentId: string;
};

export type RuntimeTransportStatus = "idle" | "connecting" | "streaming" | "polling" | "unavailable" | "error";

export type RuntimeEvent = ArchiveDocumentRuntimeEvent & {
  stage_id?: string;
  stage_label?: string;
};

export type RuntimeRealtimeEvent = {
  event_id: string;
  event_type:
    | "run_started"
    | "document_started"
    | "parse_snapshot_ready"
    | "rule_started"
    | "rule_hit"
    | "object_candidate_created"
    | "relation_candidate_created"
    | "merge_candidate_created"
    | "quality_metric_updated"
    | "run_completed"
    | "run_failed";
  level: "neutral" | "success" | "warning" | "danger" | "info";
  message: string;
  document_id?: string | null;
  stage_id?: string | null;
  rule_id?: string | null;
  object_id?: string | null;
  relation_id?: string | null;
  candidate_id?: string | null;
  timestamp?: string | null;
  payload: Record<string, unknown>;
};

export type RuntimeDocument = ArchiveKnowledgeDocument;

export type RuntimeStageSnapshot = ArchiveDocumentRuntimeStageSnapshot;

export type RuntimeGraphNode = ArchiveDocumentRuntimeGraphNode;

export type RuntimeGraphEdge = ArchiveDocumentRuntimeGraphEdge;

export type RuntimeGraphProjection = {
  nodes: RuntimeGraphNode[];
  edges: RuntimeGraphEdge[];
  node_count: number;
  edge_count: number;
  current_stage_id?: string | null;
  current_node_ids: string[];
  current_edge_ids: string[];
  changed_node_ids: string[];
  changed_edge_ids: string[];
  summary: Record<string, unknown>;
};

export type RuntimeGeneratedCandidate = {
  candidate_id: string;
  candidate_type: string;
  label: string;
  source_document_id: string;
  stage_id: string;
  status: ArchiveDocumentRuntimeStatus | string;
  evidence_count: number;
  relation_count: number;
  attributes: Record<string, unknown>;
};

export type RuntimeContract = ArchiveDocumentRuntimeContract & {
  runtime_snapshot_id?: string | null;
  stream_status?: "streaming" | "polling" | "unavailable" | "error";
  document_set_id?: string | null;
  policy_package_version_id?: string | null;
  current_document_id?: string | null;
  current_stage_or_rule_id?: string | null;
  current_stage_status?: ArchiveDocumentRuntimeStatus | null;
  current_stage_message?: string | null;
  runtime_status?: ArchiveDocumentRuntimeStatus | string | null;
  stage_statuses?: Record<string, ArchiveDocumentRuntimeStatus | string>;
  quality_gate?: Record<string, unknown>;
  publication_candidate_status?: Record<string, unknown>;
  runtime_events?: RuntimeRealtimeEvent[];
  graph_projection?: RuntimeGraphProjection;
  generated_candidates?: RuntimeGeneratedCandidate[];
};

export type RuntimeModuleOutput = {
  runtimeSnapshotId: string;
};
