import type { P1ArtifactRef, P1LifecycleStatus } from "./common";
import type { QualityFindingReport } from "./quality";

export type PublicationCandidateStatus =
  | "machine_candidate_created"
  | "governance_pending"
  | "formalized"
  | "blocked_by_quality"
  | "stale_after_policy_change"
  | P1LifecycleStatus;

export interface PublicationCandidateSummary {
  publication_snapshot_id?: string | null;
  status_label: string;
  source_scope: string;
  generated_from_runtime_snapshot_id?: string | null;
  candidate_count: number;
  candidate_knowledge_count: number;
}

export interface PublicationQualityDecisionSummary {
  decision: string;
  output_action: string;
  score?: number | null;
  explanation: string;
  affected_object_ids: string[];
  affected_relation_ids: string[];
}

export interface GovernanceStatusProjection {
  governance_confirmation_status: "not_ready" | "waiting_confirmation" | "confirmed" | "rejected";
  governance_confirmation_label: string;
  formal_entry_status: "not_admitted" | "admitted";
  formal_entry_label: string;
  confirmation_required: boolean;
}

export interface PublicationCandidateObject {
  object_id: string;
  canonical_name: string;
  object_type: string;
  source_document_ids: string[];
  source_candidate_ids: string[];
  evidence_refs: P1ArtifactRef[];
  confidence?: number | null;
  quality_status: "passed" | "warning" | "blocked" | "stale";
  governance_status: "pending" | "approved" | "rejected" | "superseded";
  version?: string | null;
  source_snapshot_id?: string | null;
}

export interface PublicationCandidateRelation {
  relation_id: string;
  source_object_id: string;
  target_object_id: string;
  relation_type: string;
  source_document_ids: string[];
  source_candidate_relation_ids: string[];
  evidence_refs: P1ArtifactRef[];
  confidence?: number | null;
  quality_status: "passed" | "warning" | "blocked" | "stale";
  governance_status: "pending" | "approved" | "rejected" | "superseded";
  source_snapshot_id?: string | null;
}

export interface PublicationCandidateSnapshot {
  publication_candidate_snapshot_id: string;
  archive_id: string;
  run_id: string;
  runtime_snapshot_id?: string | null;
  policy_package_version_id?: string | null;
  resolution_snapshot_id?: string | null;
  generated_at: string;
  status: PublicationCandidateStatus;
  governance_status: "pending" | "approved" | "rejected" | "superseded";
  publication_snapshot_id?: string | null;
  candidate_summary?: PublicationCandidateSummary;
  quality_decision_summary?: PublicationQualityDecisionSummary;
  quality_decision?: PublicationQualityDecisionSummary;
  quality_finding_report?: QualityFindingReport | null;
  governance_projection?: GovernanceStatusProjection;
  candidate_objects?: PublicationCandidateObject[];
  candidate_relations?: PublicationCandidateRelation[];
  candidate_knowledge_refs: P1ArtifactRef[];
  api_exposure_scope: {
    readonly_candidate_api_paths: string[];
    readonly_formal_api_paths?: string[];
    index_names: string[];
    exposure_mode?: "candidate_preview_only" | "formal_supply" | "blocked";
    not_supply_reason?: string | null;
  };
}

export interface PublishedKnowledgeSnapshot {
  published_snapshot_id: string;
  archive_id: string;
  publication_candidate_snapshot_id: string;
  formal_version: string;
  published_at: string;
  governed_by: string;
  api_paths: string[];
}
