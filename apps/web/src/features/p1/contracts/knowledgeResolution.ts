import type { P1ArtifactRef, P1LifecycleStatus } from "./common";

export interface KnowledgeIdentityKey {
  identity_key_id: string;
  knowledge_type: string;
  normalized_name: string;
  business_scope: string;
  key_fields: Record<string, string>;
  alias_tokens?: string[];
  definition_signature?: string;
  relation_neighborhood_hash?: string;
  policy_snapshot_id?: string;
  generated_by_rule_execution_id?: string;
}

export interface CrossDocumentMatchCandidate {
  candidate_id: string;
  identity_key: KnowledgeIdentityKey;
  source_candidate_item_ids?: string[];
  source_document_ids: string[];
  similarity_score: number;
  match_features?: Record<string, number>;
  evidence_refs: P1ArtifactRef[];
  suggested_action: "merge" | "keep_separate" | "replace" | "mark_conflict";
  explanation?: string;
  generated_at?: string;
}

export interface KnowledgeMergeDecision {
  decision_id: string;
  candidate_ids: string[];
  source_candidate_item_ids?: string[];
  decision: "merged" | "kept_separate" | "replaced" | "conflict_pending";
  reason: string;
  rule_execution_record_ids: string[];
  requires_governance_confirmation?: boolean;
  generated_at?: string;
}

export interface CanonicalKnowledgeItem {
  knowledge_id: string;
  identity_key: KnowledgeIdentityKey;
  status: P1LifecycleStatus;
  display_name: string;
  aliases?: string[];
  source_document_ids: string[];
  source_candidate_item_ids?: string[];
  evidence_refs: P1ArtifactRef[];
  relation_refs?: string[];
  version: string;
  quality_summary?: Record<string, unknown>;
}

export interface KnowledgeUpdatePlan {
  update_plan_id: string;
  archive_id: string;
  minimum_rebuild_stage_id: string;
  stale_object_ids: string[];
  affected_knowledge_ids: string[];
  impacted_relation_ids?: string[];
  recommended_actions: string[];
  requires_governance_confirmation?: boolean;
  writes_official_knowledge?: boolean;
  generated_at?: string;
}

export interface ArchiveKnowledgeResolutionSnapshot {
  snapshot_id: string;
  archive_id: string;
  run_id?: string;
  policy_snapshot_id?: string;
  input_document_ids?: string[];
  generated_at: string;
  match_candidates: CrossDocumentMatchCandidate[];
  merge_decisions: KnowledgeMergeDecision[];
  canonical_items: CanonicalKnowledgeItem[];
  update_plan?: KnowledgeUpdatePlan;
  conflict_count?: number;
  unsupported_count?: number;
}
