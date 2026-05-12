export interface ImpactSet {
  impact_set_id: string;
  archive_id: string;
  policy_package_version_id: string;
  previous_policy_package_version_id: string;
  changed_rule_ids: string[];
  affected_stage_ids: string[];
  affected_chunk_ids?: string[];
  affected_candidate_ids?: string[];
  minimum_rebuild_stage_id: string;
  affected_document_ids: string[];
  affected_object_ids: string[];
  affected_relation_ids: string[];
  affected_publication_snapshot_ids: string[];
  requires_governance_reconfirmation?: boolean;
  generated_at?: string;
  writes_official_knowledge: boolean;
}
