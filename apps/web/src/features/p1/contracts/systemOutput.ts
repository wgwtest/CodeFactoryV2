import type { P1ArtifactRef } from "./common";
import type { PublishedKnowledgeSnapshot } from "./publication";

export interface DeprecatedOutputRoute {
  deprecated: true;
  replacement_path: string;
  removal_policy: string;
}

export interface P1KnowledgeSupplyExport {
  export_id: string;
  archive_id: string;
  contract_version: "P1KnowledgeSupplyExport.v1";
  published_snapshot_id: string;
  formal_version: string;
  governed_by: string;
  published_at: string;
  published_snapshot: PublishedKnowledgeSnapshot;
  formal_knowledge_refs: P1ArtifactRef[];
  quality_report_ref?: P1ArtifactRef | null;
  graph_quality_report_ref?: P1ArtifactRef | null;
  consumer_systems: string[];
  api_base_path: string;
  knowledge_read_path: string;
  graph_query_path: string;
  generated_at: string;
  deprecation?: DeprecatedOutputRoute | null;
}

export interface P6DisplayExportContractV2 {
  export_id: string;
  source_export_id: string;
  contract_version: "P6DisplayExportContract.v2";
  published_snapshot_id: string;
  formal_version: string;
  governed_by: string;
  published_at: string;
  graph_summary_path: string;
  entity_lookup_path: string;
  relation_lookup_path: string;
  source_trace: P1ArtifactRef[];
}

export interface FormalKnowledgeInterface {
  method: "GET" | "POST";
  path: string;
  purpose: string;
  source: "formal_publication_snapshot";
  requires_publication_snapshot_id: boolean;
}

export interface FormalKnowledgeVersionRule {
  rule_id: string;
  description: string;
  selected_publication_snapshot_id: string;
  selected_version_label: string;
  governance_boundary: "post_publication_confirmation";
}

export interface FormalApiExposureScope {
  exposure_mode: "formal_only" | "not_available";
  formal_api_paths: string[];
  candidate_api_paths: string[];
  blocked_candidate_sources: string[];
  not_supply_reason?: string | null;
}

export interface SystemReadableKnowledgeObject {
  object_id: string;
  name: string;
  item_type: string;
  category?: string | null;
  document_count: number;
  evidence_count: number;
  version_id?: string | null;
}

export interface SystemReadableKnowledgeRelation {
  relation_id: string;
  source_object_id: string;
  target_object_id: string;
  relation_type: string;
  version_id?: string | null;
}

export interface SystemReadableEvidence {
  evidence_id: string;
  object_id: string;
  document_id?: string | null;
  excerpt?: string | null;
  version_id?: string | null;
}

export interface SystemOutputAdapterContract {
  adapter_name: string;
  contract_version: string;
  input_keys: string[];
  output_keys: string[];
  allowed_backend_calls: string[];
  forbidden_sources: string[];
}

export interface DownstreamConsumptionGuide {
  consumer: "P2" | "P3";
  read_pattern: string;
  notes: string[];
}

export interface P1CleanSystemOutputContract {
  contract_version: "P1CleanSystemOutputContract.v1";
  archive_id: string;
  publication_snapshot_id: string | null;
  canonical_publication_snapshot_id: string | null;
  formal_version: string | null;
  formal_version_id?: string | null;
  governed_by: string | null;
  published_at: string | null;
  generated_at: string;
  source_kind: "governed_publication_snapshot";
  is_formalized: boolean;
  supply_available: boolean;
  unavailable_reason?: string | null;
  boundary: string;
  source_summary: {
    document_count: number;
    entity_count: number;
    event_count: number;
    process_count: number;
  };
  formal_interfaces: FormalKnowledgeInterface[];
  version_selection_rules: FormalKnowledgeVersionRule[];
  api_exposure_scope: FormalApiExposureScope;
  readable_objects: SystemReadableKnowledgeObject[];
  readable_relations: SystemReadableKnowledgeRelation[];
  readable_evidence: SystemReadableEvidence[];
  adapter_contract: SystemOutputAdapterContract;
  downstream_consumers: DownstreamConsumptionGuide[];
}
