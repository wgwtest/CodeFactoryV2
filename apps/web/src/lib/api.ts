import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export function resolveApiUrl(path: string): string {
  const normalizedBase = API_BASE_URL.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (/^https?:\/\//i.test(normalizedBase)) {
    return new URL(normalizedPath.replace(/^\//, ""), `${normalizedBase}/`).toString();
  }

  return `${normalizedBase}${normalizedPath}`;
}

export type ArchiveReviewStatus = "pending" | "approved" | "rejected";

export type DocumentParseRun = {
  id: string;
  status: string;
  parser_name: string;
  parser_version?: string;
  failure_reason?: string | null;
  segment_count?: number;
  created_at?: string;
};

export type DocumentSegmentPreview = {
  id: string;
  block_type: string;
  heading: string;
  content: string;
  anchor: Record<string, string | number>;
};

export type DocumentVersionDetail = {
  id: string;
  version_number: number;
  file_name: string;
  mime_type: string;
  status: string;
  created_at: string;
  latest_parse_run: DocumentParseRun | null;
  parse_runs: DocumentParseRun[];
  segments_preview: DocumentSegmentPreview[];
};

export type IntakeDocumentSummary = {
  id: string;
  title: string;
  source_name: string;
  document_key: string;
  version_count: number;
  latest_version: DocumentVersionDetail | null;
};

export type IntakeDocumentDetail = {
  id: string;
  title: string;
  source_name: string;
  document_key: string;
  latest_version: DocumentVersionDetail | null;
  versions: DocumentVersionDetail[];
};

export type ArchiveKnowledgeSummary = {
  archive_id: string;
  document_count: number;
  entity_count: number;
  event_count: number;
  process_count: number;
};

export type KnowledgeArchiveArtifacts = {
  base_exists: boolean;
  curated_exists: boolean;
  publication_exists: boolean;
};

export type KnowledgeArchiveBuildStateDocument = {
  document_id: string;
  path: string;
  title: string;
  file_type: string;
  source_archive: string;
  state: "pending" | "running" | "completed" | "failed" | "skipped";
};

export type KnowledgeArchiveBuildStateChunk = {
  chunk_id: string | null;
  position: number | null;
  total: number | null;
  heading: string | null;
  char_count: number | null;
  segment_count: number | null;
  retry_depth: number | null;
};

export type KnowledgeArchiveBuildWarning = {
  code: string;
  severity: "warning";
  file_path: string;
  file_type: string;
  message: string;
  reason?: string | null;
};

export type KnowledgeArchiveBuildState = {
  archive_id: string;
  archive_name: string;
  mode: string;
  status: string;
  started_at: string | null;
  updated_at: string | null;
  expected_document_count: number;
  completed_document_ids: string[];
  skipped_document_ids?: string[];
  pending_document_ids: string[];
  failed_document_id: string | null;
  failed_message: string | null;
  current_document_id: string | null;
  current_document_title: string | null;
  current_document_path: string | null;
  current_chunk: KnowledgeArchiveBuildStateChunk | null;
  current_stage_id?: string | null;
  current_stage_label?: string | null;
  current_stage_status?: string | null;
  current_stage_message?: string | null;
  policy_snapshot?: ArchivePolicyRuntimeSnapshot | null;
  warning_count?: number;
  warnings?: KnowledgeArchiveBuildWarning[];
  documents: KnowledgeArchiveBuildStateDocument[];
};

export type KnowledgeArchive = {
  archive_id: string;
  name: string;
  source_dir: string;
  extract_root: string;
  is_active: boolean;
  status: "empty" | "extracting" | "ready" | "error";
  last_built_at: string | null;
  last_error: string | null;
  summary: ArchiveKnowledgeSummary | null;
  build_state: KnowledgeArchiveBuildState | null;
  artifacts: KnowledgeArchiveArtifacts;
};

export type CreateKnowledgeArchiveInput = {
  archive_id: string;
  name: string;
  source_dir: string;
  extract_root?: string;
};

export type ArchivePolicyAction =
  | "auto_pass"
  | "warn_continue"
  | "manual_review"
  | "block_return"
  | "defer_publish";

/*

export type ArchivePolicyAction =
  | "自动放行"
  | "告警继续"
  | "转人工复核"
  | "阻断并回退"
  | "延迟发布";

*/
export type ArchivePolicyEffectKind =
  | "filter"
  | "score"
  | "normalize"
  | "merge"
  | "split"
  | "block"
  | "publish_candidate";

export type ArchiveRuleInputFieldContract = {
  field_name: string;
  source_artifact?: string;
  field_type: string;
  required?: boolean;
  include_in_input_hash?: boolean;
  validation?: string;
  example?: string;
  business_meaning?: string;
  missing_action?: ArchivePolicyAction | string;
};

export type ArchiveRuleOutputFieldContract = {
  field_name: string;
  target_artifact?: string;
  field_type: string;
  producer?: string;
  include_in_output_hash?: boolean;
  write_to_runtime?: boolean;
  write_to_audit?: boolean;
  used_for_impact?: boolean;
  example?: string;
  business_meaning?: string;
};

export type ArchiveStagePolicyRule = {
  key: string;
  name: string;
  meaning: string;
  threshold: string;
  action: ArchivePolicyAction;
  rule_id?: string | null;
  rule_version?: string | null;
  effect_kind?: ArchivePolicyEffectKind | string | null;
  scope_selector?: Record<string, unknown>;
  input_schema?: ArchiveRuleInputFieldContract[];
  output_schema?: ArchiveRuleOutputFieldContract[];
  parameters?: Record<string, unknown>;
  trace_fields?: string[];
  rule_hash?: string | null;
  contract_status?: "valid" | "invalid" | string | null;
  contract_errors?: string[];
};

export type ArchiveStagePolicyConfig = {
  stage_id: string;
  label: string;
  group: string;
  enabled: boolean;
  ai_mode: string;
  default_action: ArchivePolicyAction;
  objective: string;
  inputs: string[];
  ai_adaptation: string;
  rules: ArchiveStagePolicyRule[];
  branches: string[];
  outputs: string[];
  observability: string[];
};

export type ArchivePolicyPackageVersion = {
  version_id?: string | null;
  version_label?: string | null;
  version_hash?: string | null;
  status?: string | null;
  created_at?: string | null;
  archived_at?: string | null;
  previous_version_id?: string | null;
  structural_hash?: string | null;
};

export type ArchivePolicyRuleChange = {
  stage_id: string;
  rule_id: string;
  change_type: string;
  previous_rule_hash?: string | null;
  next_rule_hash?: string | null;
  previous_rule_version?: string | null;
  next_rule_version?: string | null;
};

export type ArchivePolicyImpactSet = {
  impact_id: string;
  archive_id: string;
  changed_rule_ids: string[];
  changed_stage_ids: string[];
  affected_docs?: string[];
  affected_document_ids: string[];
  affected_stages?: string[];
  affected_stage_ids: string[];
  affected_chunks?: string[];
  affected_chunk_ids: string[];
  affected_candidates?: string[];
  affected_candidate_ids: string[];
  affected_relations?: string[];
  affected_relation_ids: string[];
  affected_publication_snapshots?: string[];
  affected_publication_snapshot_ids: string[];
  minimum_rebuild_stage_id?: string | null;
  source_policy_snapshot_id?: string | null;
  target_policy_snapshot_id?: string | null;
  rule_changes: ArchivePolicyRuleChange[];
  generated_at: string;
};

export type ArchiveIncrementalRebuildTask = {
  task_id: string;
  archive_id: string;
  status: string;
  mode: string;
  minimum_rebuild_stage_id?: string | null;
  start_stage_id?: string | null;
  affected_document_ids: string[];
  affected_stage_ids: string[];
  impact_set: ArchivePolicyImpactSet;
  writes_official_knowledge: boolean;
  output_policy: string;
  allowed_outputs: string[];
  created_at: string;
  candidate_artifact_path?: string | null;
};

export type ArchivePolicyConfig = {
  archive_id: string;
  policy_package_id?: string | null;
  policy_package_name?: string | null;
  policy_package_version_id?: string | null;
  policy_package_version_status?: string | null;
  policy_package_version_hash?: string | null;
  policy_package_version_created_at?: string | null;
  previous_policy_package_version_id?: string | null;
  policy_package_versions?: ArchivePolicyPackageVersion[];
  policy_contract_status?: string | null;
  policy_contract_errors?: Record<string, unknown>[];
  impact_set?: ArchivePolicyImpactSet | null;
  incremental_rebuild_task?: ArchiveIncrementalRebuildTask | null;
  version_label: string;
  scope_label: string;
  ai_autoadapt_enabled: boolean;
  updated_at: string | null;
  stage_order: string[];
  stages: Record<string, ArchiveStagePolicyConfig>;
};

export type UpdateArchivePolicyConfigInput = {
  policy_package_id?: string | null;
  policy_package_name?: string | null;
  policy_package_version_id?: string | null;
  policy_package_version_status?: string | null;
  policy_package_version_hash?: string | null;
  policy_package_version_created_at?: string | null;
  previous_policy_package_version_id?: string | null;
  policy_package_versions?: ArchivePolicyPackageVersion[];
  version_label: string;
  scope_label: string;
  ai_autoadapt_enabled: boolean;
  stage_order: string[];
  stages: Record<string, ArchiveStagePolicyConfig>;
};

export type ArchivePolicyRuntimeSnapshotStage = {
  stage_id: string;
  label: string;
  enabled: boolean;
  ai_mode: string;
  default_action: ArchivePolicyAction;
  rule_count: number;
  rules?: ArchiveStagePolicyRule[];
};

export type ArchivePolicyRuntimeSnapshot = {
  snapshot_id: string;
  run_id?: string | null;
  captured_at: string | null;
  archive_id: string;
  policy_package_id?: string | null;
  policy_package_name?: string | null;
  policy_package_version_id?: string | null;
  policy_package_version_status?: string | null;
  policy_package_version_hash?: string | null;
  version_label: string;
  scope_label: string;
  ai_autoadapt_enabled: boolean;
  config_updated_at: string | null;
  stage_order: string[];
  stages: ArchivePolicyRuntimeSnapshotStage[];
};

export type ArchiveDocumentFormalizeResult = {
  archive_id: string;
  document_id: string;
  action: "include" | "remove";
  mode:
    | "incremental_merge"
    | "full_rebuild_bootstrap"
    | "incremental_remove"
    | "full_rebuild_bootstrap_remove";
  document_included: boolean;
  summary: ArchiveKnowledgeSummary;
  document: ArchiveKnowledgeDocument | null;
};

export type ArchiveDocumentImportResult = {
  archive_id: string;
  document_id: string;
  action: "include";
  mode: "single_document_import" | "full_rebuild_bootstrap_import";
  document_included: true;
  stored_path: string;
  summary: ArchiveKnowledgeSummary;
  document: ArchiveKnowledgeDocument | null;
};

export type ArchiveKnowledgeNode = {
  id: string;
  label: string;
  type: string;
  item_type: string;
  document_count: number;
};

export type ArchiveKnowledgeEdge = {
  source: string;
  target: string;
  label: string;
};

export type ArchiveKnowledgeGraph = {
  archive_id: string;
  nodes: ArchiveKnowledgeNode[];
  edges: ArchiveKnowledgeEdge[];
  summary: ArchiveKnowledgeSummary;
  publication?: ArchivePublicationVersion | null;
};

export type ArchiveKnowledgeInterpretation = {
  kind_label: string;
  family_code: string | null;
  family_label: string | null;
  display_name: string | null;
  standard_name: string | null;
  summary: string;
  producer_hint: string | null;
};

export type ArchiveKnowledgeEntity = {
  id: string;
  name: string;
  category: string;
  aliases: string[];
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
  language_projection?: ArchiveKnowledgeLanguageProjection;
};

export type ArchiveKnowledgeEvent = {
  id: string;
  item_type: "event";
  name: string;
  category: string;
  aliases: string[];
  document_ids: string[];
  evidence: Array<{ document_id: string; excerpt: string }>;
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
  language_projection?: ArchiveKnowledgeLanguageProjection;
};

export type ArchiveKnowledgeEvidence = {
  document_id: string | null;
  document_title: string | null;
  excerpt: string;
};

export type ArchiveKnowledgeLanguageProjection = {
  display_name_zh: string | null;
  display_name_en: string | null;
  acronym: string | null;
  aliases_zh: string[];
  aliases_en: string[];
  description_zh: string | null;
  evidence_summary_zh: string | null;
  translation_status: "none" | "derived" | "generated" | "curated";
  translation_confidence: number | null;
};

export type ArchiveKnowledgeItemDetail = {
  id: string;
  name: string;
  item_type: string;
  category: string;
  aliases: string[];
  review_status: ArchiveReviewStatus;
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
  language_projection: ArchiveKnowledgeLanguageProjection;
  documents: Array<{
    id: string;
    title: string;
    file_type: string;
    source_archive: string;
  }>;
  evidence: ArchiveKnowledgeEvidence[];
  related_items: Array<{
    id: string;
    name: string;
    item_type: string;
    relation_type: string;
  }>;
  relationship_sections: Array<{
    key: string;
    title: string;
    items: Array<{
      id: string;
      name: string;
      item_type: string;
      relation_type: string;
      relation_label: string;
      direction: string;
      evidence: string | null;
    }>;
  }>;
};

export type ArchiveKnowledgeItemGraph = {
  focus_item_id: string;
  nodes: Array<{
    id: string;
    label: string;
    item_type: string;
    category: string;
    is_focus: boolean;
  }>;
  edges: Array<{
    source: string;
    target: string;
    label: string;
  }>;
};

export type ArchiveKnowledgeProcess = {
  id: string;
  item_type: "process";
  name: string;
  category: string;
  aliases: string[];
  document_ids: string[];
  evidence: Array<{ document_id: string; excerpt: string }>;
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
  language_projection?: ArchiveKnowledgeLanguageProjection;
};

export type ArchiveKnowledgeDocument = {
  id: string;
  title: string;
  file_type: string;
  source_archive: string;
  character_count: number;
  included_in_archive: boolean;
  entity_count: number;
  event_count: number;
  process_count: number;
  knowledge_item_count: number;
};

export type ArchiveKnowledgeDocumentKnowledgeItem = {
  id: string;
  name: string;
  item_type: string;
  category: string;
  aliases: string[];
  review_status: ArchiveReviewStatus;
  interpretation: ArchiveKnowledgeInterpretation;
  evidence: ArchiveKnowledgeEvidence[];
};

export type ArchiveKnowledgeDocumentDetail = {
  document: ArchiveKnowledgeDocument;
  knowledge_items: ArchiveKnowledgeDocumentKnowledgeItem[];
};

export type ArchiveReviewCandidate = {
  id: string;
  item_type: string;
  canonical_name: string;
  category: string;
  document_count: number;
  confidence: number;
  review_status: ArchiveReviewStatus;
  evidence_excerpt: string;
  evidence_document_title: string | null;
  candidate_source?: string;
  source_scope?: string;
  governance_boundary?: string;
};

export type ArchiveKnowledgeItemUpdateInput = {
  name: string;
  category: string;
  aliases: string[];
};

export type ArchiveKnowledgeItemReviewInput = {
  review_status: ArchiveReviewStatus;
};

export type ArchiveKnowledgeBatchApproveInput = {
  item_ids: string[];
};

export type ArchiveKnowledgeMergeInput = {
  primary_item_id: string;
  secondary_item_id: string;
};

export type ArchivePublicationVersion = {
  version_label: string;
  publisher: string;
  published_at: string | null;
  summary: {
    document_count: number;
    entity_count: number;
    event_count: number;
    process_count: number;
  };
};

export type ArchivePublicationOverview = {
  archive_id: string;
  current_version: ArchivePublicationVersion | null;
  versions: ArchivePublicationVersion[];
  working_summary: {
    document_count: number;
    entity_count: number;
    event_count: number;
    process_count: number;
  };
  candidate_source?: string;
  candidate_scope?: string;
  machine_publication_status?: string;
  machine_publication_label?: string;
  governance_confirmation_status?: string;
  governance_confirmation_label?: string;
  formal_entry_status?: string;
  formal_entry_label?: string;
  review_summary?: {
    pending_count: number;
    approved_count: number;
    rejected_count: number;
  };
};

export type ArchiveDocumentRuntimeStatus =
  | "pending"
  | "running"
  | "completed"
  | "blocked"
  | "warning"
  | "unavailable";

export type ArchiveDocumentRuntimeOrigin = "source" | "derived" | "unavailable";
export type ArchiveDocumentRuntimeMode = "persisted" | "hybrid" | "derived" | "legacy_fallback";

export type ArchiveDocumentRuntimeObserverMode = "stage" | "node" | "edge";

export type ArchiveDocumentRuntimeAction = {
  action_id: string;
  label: string;
  target_kind: "stage" | "node" | "edge" | "document" | "item" | "evidence" | "graph";
  target_id?: string | null;
};

export type ArchiveDocumentRuntimeSummaryField = {
  key: string;
  label: string;
  value: string;
  tone: "neutral" | "success" | "warning" | "danger" | "info";
};

export type ArchiveDocumentRuntimeSummarySection = {
  section_id: string;
  title: string;
  fields: ArchiveDocumentRuntimeSummaryField[];
};

export type ArchiveDocumentRuntimeEvent = {
  event_id: string;
  kind: "progress" | "decision" | "evidence" | "rule" | "warning" | "block" | "result" | "info";
  level: "neutral" | "success" | "warning" | "danger" | "info";
  message: string;
  object_id?: string | null;
  object_kind?: "stage" | "node" | "edge" | "document" | "item" | "evidence" | null;
  timestamp?: string | null;
};

export type ArchiveDocumentRuntimeGraphNode = {
  node_id: string;
  label: string;
  node_type: string;
  stage_id: string;
  status: ArchiveDocumentRuntimeStatus;
  origin: ArchiveDocumentRuntimeOrigin;
  is_primary: boolean;
  is_focus: boolean;
  metrics: Record<string, unknown>;
  attributes: Record<string, unknown>;
};

export type ArchiveDocumentRuntimeGraphEdge = {
  edge_id: string;
  source: string;
  target: string;
  relation: string;
  stage_id: string;
  status: ArchiveDocumentRuntimeStatus;
  origin: ArchiveDocumentRuntimeOrigin;
  is_primary: boolean;
  attributes: Record<string, unknown>;
};

export type ArchiveDocumentRuntimeObserverPayload = {
  mode: ArchiveDocumentRuntimeObserverMode;
  title: string;
  subtitle?: string | null;
  status: ArchiveDocumentRuntimeStatus;
  stream: ArchiveDocumentRuntimeEvent[];
  sections: ArchiveDocumentRuntimeSummarySection[];
  actions: ArchiveDocumentRuntimeAction[];
};

export type ArchiveDocumentRuntimeStageGraph = {
  nodes: ArchiveDocumentRuntimeGraphNode[];
  edges: ArchiveDocumentRuntimeGraphEdge[];
  primary_node_ids: string[];
  primary_edge_ids: string[];
};

export type ArchiveDocumentRuntimeStageSnapshot = {
  stage_id: string;
  label: string;
  group: string;
  order: number;
  status: ArchiveDocumentRuntimeStatus;
  is_current: boolean;
  graph: ArchiveDocumentRuntimeStageGraph;
  stage_observer: ArchiveDocumentRuntimeObserverPayload;
  node_observers: Record<string, ArchiveDocumentRuntimeObserverPayload>;
  edge_observers: Record<string, ArchiveDocumentRuntimeObserverPayload>;
  rule_execution_records?: ArchiveRuleExecutionRecord[];
};

export type ArchiveRuleExecutionRecord = {
  execution_id: string;
  archive_id: string;
  document_id: string;
  stage_id: string;
  rule_id: string;
  rule_version: string;
  rule_hash?: string | null;
  snapshot_id?: string | null;
  input_artifact_refs: string[];
  input_hash?: string | null;
  output_artifact_refs: string[];
  output_hash?: string | null;
  affected_object_ids: string[];
  affected_relation_ids: string[];
  decision: string;
  metrics: Record<string, unknown>;
  executed_at?: string | null;
  source: "runtime_trace" | "policy_snapshot" | "derived";
};

export type ArchiveDocumentRuntimeContract = {
  archive_id: string;
  document_id: string;
  document_title: string;
  current_stage_id: string;
  current_stage_label: string;
  status: ArchiveDocumentRuntimeStatus;
  runtime_mode?: ArchiveDocumentRuntimeMode;
  persisted_stage_ids?: string[];
  source_document: Record<string, unknown>;
  policy_snapshot?: ArchivePolicyRuntimeSnapshot | null;
  policy_package_id?: string | null;
  policy_version?: string | null;
  policy_snapshot_id?: string | null;
  stages: ArchiveDocumentRuntimeStageSnapshot[];
  rule_execution_records?: ArchiveRuleExecutionRecord[];
};

export type RequirementFormalElement = {
  id: string;
  name: string;
  item_type: "entity" | "process";
  category: string | null;
  aliases: string[];
  document_count: number;
  summary: string;
  source_archive_id: string;
};

export type RequirementApplication = {
  name: string;
  domain: string;
  summary: string;
  target_users: string[];
};

export type RequirementObject = {
  id: string;
  name: string;
  object_kind: "business" | "supporting";
  source_kind: "formal" | "temporary";
  category: string | null;
  aliases: string[];
  summary: string | null;
  description: string | null;
  source_archive_id: string | null;
  source_item_type: "entity" | "process" | null;
  source_item_id: string | null;
};

export type RequirementProcess = {
  id: string;
  name: string;
  process_kind: "lifecycle" | "collaboration";
  source_kind: "formal" | "temporary";
  description: string | null;
  participant_object_ids: string[];
  source_archive_id: string | null;
  source_item_type: "process" | null;
  source_item_id: string | null;
};

export type RequirementRule = {
  id: string;
  name: string;
  description: string;
};

export type RequirementMetric = {
  id: string;
  name: string;
  description: string;
};

export type RequirementConstraint = {
  id: string;
  name: string;
  category: string;
  description: string;
};

export type RequirementSpecPayload = {
  application: RequirementApplication;
  objects: RequirementObject[];
  processes: RequirementProcess[];
  rules: RequirementRule[];
  metrics: RequirementMetric[];
  non_functional_constraints: RequirementConstraint[];
};

export type RequirementSpecSummary = {
  id: string;
  application_name: string;
  domain_name: string;
  status: string;
  archive_id: string;
  object_count: number;
  formal_object_count: number;
  temporary_object_count: number;
  process_count: number;
  updated_at: string;
};

export type RequirementSpecDetail = RequirementSpecSummary & {
  created_at: string;
  payload: RequirementSpecPayload;
};

export type RequirementSpecWriteInput = {
  archive_id?: string;
  status: "draft" | "reviewing" | "ready";
  payload: RequirementSpecPayload;
};

export type RequirementAuthoringTemplateStatus = "draft" | "active" | "disabled" | "archived";
export type RequirementAuthoringDocumentStatus =
  | "draft"
  | "checking"
  | "ready_to_freeze"
  | "frozen"
  | "submitted_to_p3"
  | "archived";
export type RequirementAuthoringLayoutRatio = "2:3" | "1:1";

export type RequirementAuthoringTemplateField = {
  field_key: string;
  label: string;
  required: boolean;
  clause_id: string;
};

export type RequirementAuthoringTemplateFormGroup = {
  group_id: string;
  title: string;
  fields: RequirementAuthoringTemplateField[];
};

export type RequirementAuthoringTemplate = {
  template_id: string;
  template_code: string;
  name: string;
  status: RequirementAuthoringTemplateStatus;
  description: string;
  sections: Array<Record<string, unknown>>;
  form_groups: RequirementAuthoringTemplateFormGroup[];
  field_mappings: Array<Record<string, unknown>>;
  questionnaire_policy: {
    quick_inputs?: string[];
    [key: string]: unknown;
  };
  gap_rules: Record<string, unknown>;
  knowledge_bindings: Array<{ archive_id: string; label: string; enabled?: boolean }>;
  created_at: string;
  updated_at: string;
};

export type RequirementAuthoringClause = {
  clause_id: string;
  title: string;
  content: string;
  status: "missing" | "synced" | "pending_mapping" | string;
};

export type RequirementAuthoringSection = {
  section_id: string;
  title: string;
  clauses: RequirementAuthoringClause[];
};

export type RequirementAuthoringStandardDocument = {
  title: string;
  sections: RequirementAuthoringSection[];
};

export type RequirementAuthoringConversationMessage = {
  id: string;
  role: "assistant" | "user" | string;
  content: string;
  created_at?: string;
};

export type RequirementAuthoringAnnotation = {
  clause_id: string;
  title: string;
  interpretation: string;
  source_refs: string[];
  semantic_mapping: Array<Record<string, unknown>>;
  p3_mapping: string[];
  gaps: string[];
  pending_confirmations: string[];
};

export type RequirementAuthoringCheckResult = {
  blocking_count: number;
  warning_count: number;
  passed_count: number;
  items: Array<Record<string, unknown>>;
};

export type RequirementAuthoringDocumentSummary = {
  document_id: string;
  title: string;
  template_id: string;
  status: RequirementAuthoringDocumentStatus;
  layout_ratio: RequirementAuthoringLayoutRatio;
  archive_ids: string[];
  updated_at: string;
};

export type RequirementAuthoringDocumentDetail = RequirementAuthoringDocumentSummary & {
  created_at: string;
  semantic_state: {
    fields: Record<string, string>;
    knowledge_binding?: RequirementAuthoringKnowledgeBinding | null;
    [key: string]: unknown;
  };
  document: RequirementAuthoringStandardDocument;
  conversation: RequirementAuthoringConversationMessage[];
  annotations: RequirementAuthoringAnnotation[];
  check_result: RequirementAuthoringCheckResult;
  frozen_package: { p3_consumable?: boolean; [key: string]: unknown } | null;
};

export type RequirementAuthoringTemplateWriteInput = {
  template_code: string;
  name: string;
  description?: string;
  status?: RequirementAuthoringTemplateStatus;
  sections?: Array<Record<string, unknown>>;
  form_groups?: RequirementAuthoringTemplateFormGroup[];
  field_mappings?: Array<Record<string, unknown>>;
  questionnaire_policy?: Record<string, unknown>;
  gap_rules?: Record<string, unknown>;
  knowledge_bindings?: Array<Record<string, unknown>>;
};

export type RequirementAuthoringDocumentCreateInput = {
  title: string;
  template_id: string;
  archive_ids?: string[];
  layout_ratio?: RequirementAuthoringLayoutRatio;
};

export type P1KnowledgeProviderRegistration = {
  provider_id: string;
  provider_name: string;
  provider_kind: "p1_knowledge_provider";
  status: "online" | "offline";
  capabilities: string[];
  version: string;
  seed: string;
};

export type P1DomainKnowledgeCatalogItem = {
  domain_id: string;
  domain_name: string;
  domain_summary: string;
  archive_version: string;
  concept_count: number;
  rule_count: number;
  process_count: number;
  evidence_count: number;
};

export type P1DomainKnowledgeCatalog = {
  provider: P1KnowledgeProviderRegistration;
  items: P1DomainKnowledgeCatalogItem[];
};

export type P1KnowledgeConcept = {
  concept_id: string;
  name: string;
  definition: string;
};

export type P1KnowledgeRule = {
  rule_id: string;
  name: string;
  description: string;
};

export type P1KnowledgeProcess = {
  process_id: string;
  name: string;
  steps: string[];
};

export type P1KnowledgeConstraint = {
  constraint_id: string;
  category: string;
  description: string;
};

export type P1KnowledgeEvidenceRef = {
  evidence_id: string;
  source: string;
  excerpt: string;
};

export type P1DomainKnowledgeArchive = {
  provider_id: string;
  domain_id: string;
  archive_id: string;
  archive_version: string;
  published_at: string;
  concepts: P1KnowledgeConcept[];
  entities: P1KnowledgeConcept[];
  rules: P1KnowledgeRule[];
  processes: P1KnowledgeProcess[];
  constraints: P1KnowledgeConstraint[];
  evidence_refs: P1KnowledgeEvidenceRef[];
};

export type P1SimCallLog = {
  call_id: string;
  called_at: string;
  method: string;
  path: string;
  domain_id?: string | null;
  status_code: number;
  archive_version: string;
};

export type P1SimCallLogEnvelope = {
  items: P1SimCallLog[];
};

export type RequirementAuthoringKnowledgeProvider = P1KnowledgeProviderRegistration & {
  domains: P1DomainKnowledgeCatalogItem[];
};

export type RequirementAuthoringKnowledgeProviderEnvelope = {
  items: RequirementAuthoringKnowledgeProvider[];
};

export type RequirementAuthoringKnowledgeBinding = {
  binding_id: string;
  provider: P1KnowledgeProviderRegistration;
  domain: P1DomainKnowledgeCatalogItem;
  knowledge_archive: Partial<P1DomainKnowledgeArchive>;
  editor_badge: string;
  created_document: null;
  frozen_package: null;
};

export type RequirementStep = "goal" | "audience" | "flow" | "object_event" | "structure";
export type RequirementDraftStatus = "draft" | "completed";
export type RequirementRecommendationSource = "recommended_common" | "recommended_domain" | "manual";

export type RequirementRecommendation = {
  id: string;
  name: string;
  description: string;
  source: RequirementRecommendationSource;
  tags: string[];
  related_knowledge_id?: string | null;
};

export type ApplicationRequirementGoal = {
  problem_statement: string;
  target_outcome: string;
  success_criteria: string[];
};

export type ApplicationRequirementAudience = {
  id: string;
  name: string;
  description: string;
};

export type ApplicationRequirementRole = {
  id: string;
  name: string;
  audience_id: string;
  responsibility_summary: string;
};

export type ApplicationRequirementBusinessFlow = {
  id: string;
  name: string;
  scope: string;
  priority: string;
  participants: string[];
};

export type ApplicationRequirementBusinessObject = {
  id: string;
  name: string;
  description: string;
};

export type ApplicationRequirementEvent = {
  id: string;
  name: string;
  description: string;
};

export type ApplicationRequirementWorkspace = {
  id: string;
  name: string;
};

export type ApplicationRequirementPage = {
  id: string;
  name: string;
  page_type: string;
};

export type ApplicationRequirementPermissionIntent = {
  role_id: string;
  access_scope: string;
};

export type ApplicationRequirementStructure = {
  workspaces: ApplicationRequirementWorkspace[];
  pages: ApplicationRequirementPage[];
  permission_intents: ApplicationRequirementPermissionIntent[];
};

export type ApplicationRequirementKnowledgeReference = {
  source_type: string;
  source_id: string;
  source_name: string;
};

export type ApplicationRequirementManualAddition = {
  target_type: string;
  name: string;
};

export type ApplicationRequirementModel = {
  archive_id: string;
  application_name: string;
  application_goal: ApplicationRequirementGoal;
  audiences: ApplicationRequirementAudience[];
  roles: ApplicationRequirementRole[];
  business_flows: ApplicationRequirementBusinessFlow[];
  business_objects: ApplicationRequirementBusinessObject[];
  key_events: ApplicationRequirementEvent[];
  application_structure: ApplicationRequirementStructure;
  knowledge_references: ApplicationRequirementKnowledgeReference[];
  manual_additions: ApplicationRequirementManualAddition[];
};

export type ApplicationRequirementDraft = ApplicationRequirementModel & {
  draft_id: string;
  status: RequirementDraftStatus;
  current_step: RequirementStep;
  created_at: string;
  updated_at: string;
};

export type ApplicationRequirementDraftEnvelope = {
  draft: ApplicationRequirementDraft;
  recommendations: Record<RequirementStep, RequirementRecommendation[]>;
};

export type ApplicationRequirementDraftCreateInput = {
  archive_id: string;
};

export type ApplicationRequirementDraftUpdateInput = Partial<
  Pick<
    ApplicationRequirementDraft,
    | "current_step"
    | "application_name"
    | "application_goal"
    | "audiences"
    | "roles"
    | "business_flows"
    | "business_objects"
    | "key_events"
    | "application_structure"
    | "knowledge_references"
    | "manual_additions"
  >
>;

export type ApplicationRequirementDraftExport = {
  draft_id: string;
  model: ApplicationRequirementModel;
  json_text: string;
  yaml_text: string;
  markdown: string;
};

export type ToolStatus = "draft" | "active" | "archived";
export type ToolVerificationStatus = "unverified" | "verified" | "warning" | "failed";
export type SupportedSource = "p1_readonly_api" | "frozen_snapshot" | "manual_input" | "tool_hub_snapshot";
export type ToolGranularity = "atomic" | "composite" | "page_level";
export type ToolPackagingType = "source_package" | "build_artifact" | "http_endpoint" | "descriptor_only";
export type ToolIntegrationMode =
  | "import_component"
  | "import_module"
  | "include_router"
  | "call_http_api"
  | "mount_page"
  | "manual";
export type ToolDependencyPolicy = "peer" | "bundled" | "external";
export type ToolBuildRunStatus = "queued" | "running" | "completed" | "failed";

export type ToolHubCatalogItem = {
  id: string;
  label: string;
  description: string;
};

export type ToolVerification = {
  status: ToolVerificationStatus;
  last_verified_at?: string | null;
  last_verified_result: string;
  sample_case_ids: string[];
};

export type ToolDefinition = {
  tool_id: string;
  name: string;
  slug: string;
  status: ToolStatus;
  summary: string;
  problem_statement: string;
  primary_domain_id: string;
  tool_form_id: string;
  tool_granularity?: ToolGranularity;
  packaging_type?: ToolPackagingType;
  integration_mode?: ToolIntegrationMode;
  dependency_policy?: ToolDependencyPolicy;
  runtime_dependencies?: string[];
  host_constraints?: Record<string, string | string[]>;
  runtime_platform_ids: string[];
  tags: string[];
  lifecycle_stage_ids: string[];
  input_types: string[];
  output_types: string[];
  supported_sources: SupportedSource[];
  usage_notes: string;
  keywords: string[];
  verification: ToolVerification;
  created_at: string;
  updated_at: string;
};

export type ToolDefinitionWriteInput = Omit<
  ToolDefinition,
  | "tool_id"
  | "created_at"
  | "updated_at"
  | "tool_granularity"
  | "packaging_type"
  | "integration_mode"
  | "dependency_policy"
  | "runtime_dependencies"
  | "host_constraints"
  | "supported_sources"
> & {
  tool_granularity?: ToolGranularity;
  packaging_type?: ToolPackagingType;
  integration_mode?: ToolIntegrationMode;
  dependency_policy?: ToolDependencyPolicy;
  runtime_dependencies?: string[];
  host_constraints?: Record<string, string | string[]>;
  supported_sources?: string[];
};

export type ToolListEnvelope = {
  items: ToolDefinition[];
};

export type ToolHubSnapshotMeta = {
  snapshot_id: string;
  generated_at: string;
  state_version: string;
  source_contract_version?: string;
};

export type ToolHubReadEnvelope<T> = {
  meta: ToolHubSnapshotMeta;
  data: T;
};

export type P4ObjectViewTabKey =
  | "pool"
  | "processing"
  | "build"
  | "usage"
  | "registry"
  | "graph"
  | "asset"
  | "config"
  | "lineage";

export type P4ObjectViewTab = {
  key: P4ObjectViewTabKey;
  title: string;
  caption: string;
};

export type ToolHubCatalogs = {
  domains: ToolHubCatalogItem[];
  lifecycle_stages: ToolHubCatalogItem[];
  tool_forms: ToolHubCatalogItem[];
  runtime_platforms: ToolHubCatalogItem[];
  input_types: ToolHubCatalogItem[];
  output_types: ToolHubCatalogItem[];
  supported_sources: ToolHubCatalogItem[];
  verification_statuses: ToolHubCatalogItem[];
  tag_namespaces: ToolHubCatalogItem[];
};

export type ToolHubOverviewMetrics = {
  tool_count: number;
  verified_tool_count: number;
  active_tool_count: number;
  draft_tool_count: number;
  archived_tool_count: number;
  match_run_count: number;
  evolution_run_count: number;
  active_chain_count: number;
  overlap_candidate_count: number;
  pending_suggestion_count: number;
  recent_success_rate: number;
};

export type ToolHubCoverageMatrix = {
  title: string;
  x_axis_label: string;
  y_axis_label: string;
  columns: ToolHubCatalogItem[];
  rows: Array<{
    row_id: string;
    row_label: string;
    cells: Array<{
      column_id: string;
      value: number;
    }>;
  }>;
};

export type ToolHubRiskSummaryItem = {
  kind: "missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap";
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
};

export type ToolHubRecentRunSummary = {
  run_id: string;
  run_type: "match" | "evolution";
  title: string;
  status: string;
  created_at: string;
  summary: string;
};

export type ToolHubRunMonitor = {
  active_match_run_count: number;
  active_evolution_run_count: number;
  latest_match_run: ToolHubRecentRunSummary | null;
  latest_evolution_run: ToolHubRecentRunSummary | null;
  failing_run_count: number;
  stale_run_count: number;
};

export type PendingSuggestionItem = {
  finding_id: string;
  source_run_id: string;
  kind: "missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap";
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  tool_ids: string[];
};

export type ToolMatchKnowledgeContext = {
  archive_id?: string | null;
  entity_ids: string[];
  process_ids: string[];
  snapshot_version?: string | null;
};

export type ToolMatchRequestInput = {
  scenario_text: string;
  target_domain_ids: string[];
  lifecycle_stage_ids: string[];
  required_input_types: string[];
  expected_output_types: string[];
  preferred_tool_forms: string[];
  preferred_runtime_platforms: string[];
  preferred_tags: string[];
  knowledge_context: ToolMatchKnowledgeContext;
};

export type ToolMatchCandidate = {
  tool_id: string;
  name: string;
  match_score: number;
  matched_dimensions: string[];
  reasons: string[];
  gaps: string[];
  verification_status: ToolVerificationStatus;
};

export type ToolMatchRun = {
  run_id: string;
  status: "completed";
  created_at: string;
  request: ToolMatchRequestInput;
  candidates: ToolMatchCandidate[];
  context_summary: string;
};

export type EvolutionFinding = {
  finding_id: string;
  run_id: string;
  kind: "missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap";
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  tool_ids: string[];
  evidence: Record<string, unknown>;
  decision_status: "pending" | "accepted_to_task" | "ignored";
  decision_by: string | null;
  decision_at: string | null;
  decision_note: string;
  linked_task_id: string | null;
  updated_at: string;
};

export type EvolutionRun = {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  trigger_type: "manual" | "scheduled";
  triggered_by: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  snapshot_id: string | null;
  error_message: string;
  summary: {
    tool_count: number;
    finding_count: number;
    missing_description_count: number;
    taxonomy_issue_count: number;
    overlap_risk_count: number;
    coverage_gap_count: number;
    accepted_count: number;
    ignored_count: number;
    generated_task_count: number;
  };
  findings: EvolutionFinding[];
};

export type EvolutionRunEnvelope = {
  items: EvolutionRun[];
};

export type EvolutionInspectionConfig = {
  config_id: string;
  enabled: boolean;
  schedule_mode: "manual_and_scheduled";
  interval_minutes: number;
  include_draft_tools: boolean;
  focus_rule_ids: Array<"missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap">;
  overlap_threshold: number;
  max_run_history: number;
  auto_apply_rule_ids: Array<"missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap">;
  updated_by: string;
  updated_at: string;
};

export type EvolutionConfigUpdateInput = Partial<
  Pick<
    EvolutionInspectionConfig,
    | "enabled"
    | "interval_minutes"
    | "include_draft_tools"
    | "focus_rule_ids"
    | "overlap_threshold"
    | "max_run_history"
    | "auto_apply_rule_ids"
  >
>;

export type EvolutionRunCreateInput = {
  actor_id: string;
};

export type EvolutionFindingDecisionInput = {
  actor_id: string;
  decision: "accept" | "ignore";
  note: string;
};

export type EvolutionTask = {
  task_id: string;
  source_run_id: string;
  source_finding_id: string;
  task_type: "auto_apply" | "manual_followup";
  task_status: "queued" | "running" | "completed" | "failed" | "rolled_back";
  priority: "low" | "medium" | "high";
  planned_action: string;
  target_tool_ids: string[];
  result_summary: string;
  change_count: number;
  rollback_available: boolean;
  created_by: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type EvolutionTaskEnvelope = {
  items: EvolutionTask[];
};

export type EvolutionTaskRollbackInput = {
  actor_id: string;
  note: string;
};

export type ToolHubOverview = {
  metrics: ToolHubOverviewMetrics;
  run_monitor: ToolHubRunMonitor;
  coverage_matrix: ToolHubCoverageMatrix;
  risk_summary: ToolHubRiskSummaryItem[];
  pending_suggestions: PendingSuggestionItem[];
  recent_demand_sheets?: ToolDemandSheet[];
  recent_match_runs: ToolHubRecentRunSummary[];
  recent_evolution_runs: ToolHubRecentRunSummary[];
  catalogs: ToolHubCatalogs;
};

export type P4ObjectWorkbenchProjection = {
  snapshot_id: string;
  meta: ToolHubSnapshotMeta;
  object_tabs: P4ObjectViewTab[];
  workorder_pool: {
    sheets: ToolDemandSheet[];
    active_sheet: ToolDemandSheet | null;
  };
  workorder_processing: {
    active_sheet: ToolDemandSheet | null;
    active_item: ToolDemandItem | null;
  };
  tool_build: {
    selected_tool: ToolDefinition | null;
    active_item: ToolDemandItem | null;
    manufacture_plan: ToolManufacturePlanView | null;
  };
  usage_cockpit: {
    active_items: ToolDemandItem[];
    hot_tools: ToolDefinition[];
    cold_tools: ToolDefinition[];
    hot_domains: ToolHubCatalogItem[];
    cold_domains: ToolHubCatalogItem[];
  };
  tool_resources: {
    tools: ToolDefinition[];
  };
  coverage_knowledge_graph: {
    matrix: ToolHubCoverageMatrix;
  };
  delivered_tool_attribute: {
    selected_tool: ToolDefinition | null;
    used_by_items: ToolDemandItem[];
    evolution_task_count: number;
    rollback_available_count: number;
  };
  evolution_config: {
    config: EvolutionInspectionConfig | null;
  };
  evolution_lineage: {
    runs: EvolutionRun[];
    tasks: EvolutionTask[];
  };
};

export type ToolDemandSheetLifecycleStatus = "submitted" | "accepted" | "rejected" | "withdrawn" | "closed";
export type ToolDemandSheetReviewStatus = "pending_review" | "reviewing" | "reviewed";
export type ToolDemandSheetDeliveryStatus = "not_delivered" | "delivering" | "delivered";
export type ToolDemandSheetProcessingStatus = "not_started" | "processing" | "partially_ready" | "ready" | "failed";
export type ToolDemandItemRecommendationType = "existing_tool" | "manufacture_candidate" | "insufficient_info";
export type ToolDemandItemReviewStatus = "pending_review" | "approved_delivery" | "approved_manufacture" | "rejected";
export type ToolDemandItemProcessingStatus =
  | "accepted"
  | "analyzing"
  | "checking"
  | "matched_existing"
  | "manufacturing_pending"
  | "manufacturing_in_progress"
  | "ready_for_fetch"
  | "failed";
export type ToolSupplyResultType = "existing_tool" | "pending_manufacture" | "manufactured_tool";
export type ToolManufacturePlanStatus = "manufacturing_pending" | "manufacturing_in_progress" | "ready_for_fetch" | "failed";
export type ToolManufactureSimulationProfile = "fast" | "normal" | "slow";
export type MockDemandScenarioId = "simulated_blue_force" | "navigation_planning" | "data_governance";

export type ToolDemandSource = {
  phase: string;
  producer: string;
  business_case: string;
  scenario_id: string;
  scenario_name: string;
};

export type ComponentSpec = {
  component_name: string;
  component_code: string;
  problem_statement: string;
  required_input_types: string[];
  expected_output_types: string[];
  preferred_tool_forms: string[];
  preferred_runtime_platforms: string[];
  lifecycle_stage_ids: string[];
  keywords: string[];
  acceptance_notes: string;
};

export type ToolDemandNode = {
  node_id: string;
  node_type: "system" | "subsystem" | "sub_subsystem" | "module" | "component";
  node_name: string;
  node_code: string;
  description?: string;
  business_domain_id: string;
  children: ToolDemandNode[];
  component_spec?: ComponentSpec | null;
};

export type ToolFetchManifest = {
  tool_id: string;
  tool_name: string;
  tool_version: string;
  tool_form_id: string;
  packaging_type?: ToolPackagingType;
  integration_mode?: ToolIntegrationMode;
  dependency_policy?: ToolDependencyPolicy;
  runtime_dependencies?: string[];
  runtime_platform_ids: string[];
  fetch_mode: "descriptor";
  entrypoint_type: "http" | "descriptor" | "artifact_ref" | "manual";
  entrypoint_locator: string;
  contract_version: string;
  updated_at: string;
};

export type ToolBuildRun = {
  build_run_id: string;
  build_request_id: string;
  tool_id: string;
  status: ToolBuildRunStatus;
  queue_name: string;
  payload: Record<string, unknown>;
  artifact_version_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ToolDeliveryManifest = {
  tool_id: string;
  tool_name: string;
  tool_form_id: string;
  packaging_type: ToolPackagingType;
  integration_mode: ToolIntegrationMode;
  dependency_policy: ToolDependencyPolicy;
  runtime_dependencies: string[];
  import_specifier: string;
  example_host_path: string;
  artifact_version_id?: string | null;
  manifest_path: string;
  contract_version: string;
  updated_at: string;
};

export type FrontendComponentBuildRequestInput = {
  requested_by: string;
  component_name: string;
  scenario_id: string;
  tool_definition: ToolDefinitionWriteInput;
};

export type ToolSupplyResult = {
  result_type: ToolSupplyResultType;
  item_id: string;
  tool_ref?: string | null;
  fetch_interface?: ToolFetchManifest | null;
  progress_query_interface?: string | null;
  estimated_ready_at?: string | null;
  suggested_poll_after_seconds?: number | null;
  available_at?: string | null;
  last_message: string;
};

export type ToolDemandLifecycleEvent = {
  event_id: string;
  event_type: ToolDemandSheetLifecycleStatus;
  actor_phase: string;
  actor_id: string;
  from_status?: ToolDemandSheetLifecycleStatus | null;
  to_status: ToolDemandSheetLifecycleStatus;
  reason_code: string;
  reason_message: string;
  occurred_at: string;
};

export type ToolDemandItem = {
  item_id: string;
  sheet_id: string;
  source_node_id: string;
  ancestry: string[];
  business_domain_id: string;
  component_name: string;
  component_code: string;
  problem_statement: string;
  required_input_types: string[];
  expected_output_types: string[];
  preferred_tool_forms: string[];
  preferred_runtime_platforms: string[];
  lifecycle_stage_ids: string[];
  keywords: string[];
  acceptance_notes: string;
  recommendation_type: ToolDemandItemRecommendationType;
  recommendation_summary: string;
  recommended_tool_id?: string | null;
  recommended_tool_name?: string | null;
  review_status: ToolDemandItemReviewStatus;
  importance_score?: number | null;
  urgency_score?: number | null;
  rationality_verdict: string;
  review_comment: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  processing_status: ToolDemandItemProcessingStatus;
  analysis_result: string;
  check_result: string;
  match_result: string;
  supply_result?: ToolSupplyResult | null;
  submitted_at: string;
  updated_at: string;
};

export type ToolDemandSheet = {
  sheet_id: string;
  sheet_name: string;
  lifecycle_status: ToolDemandSheetLifecycleStatus;
  review_status: ToolDemandSheetReviewStatus;
  delivery_status: ToolDemandSheetDeliveryStatus;
  processing_status: ToolDemandSheetProcessingStatus;
  source: ToolDemandSource;
  requested_by: string;
  business_case: string;
  root_node: ToolDemandNode;
  item_ids: string[];
  item_count: number;
  pending_review_count: number;
  approved_delivery_count: number;
  approved_manufacture_count: number;
  rejected_item_count: number;
  matched_existing_count: number;
  manufacturing_count: number;
  ready_for_fetch_count: number;
  failed_count: number;
  lifecycle_events: ToolDemandLifecycleEvent[];
  last_actor_phase?: string | null;
  last_actor_id?: string | null;
  terminal_reason_code?: string | null;
  terminal_reason_message?: string | null;
  items?: ToolDemandItem[];
  submitted_at: string;
  updated_at: string;
};

export type ToolDemandSheetCreateRequestInput = {
  sheet_name: string;
  source: ToolDemandSource;
  requested_by: string;
  root_node: ToolDemandNode;
  notes?: string;
};

export type ToolDemandSheetEnvelope = {
  items: ToolDemandSheet[];
};

export type ToolManufacturePlanView = {
  plan_id: string;
  item_id: string;
  sheet_id: string;
  component_name: string;
  planned_tool_name: string;
  status: ToolManufacturePlanStatus;
  progress_percent: number;
  simulation_profile: ToolManufactureSimulationProfile;
  target_duration_seconds: number;
  estimated_ready_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  last_progress_message: string;
  updated_at: string;
};

export type ToolManufacturePlanEnvelope = {
  items: ToolManufacturePlanView[];
};

export type ToolRegistryDeleteResult = {
  removed_tool_id: string;
  remaining_tool_count: number;
};

export type ToolRegistryTestingClearResult = {
  cleared_tool_count: number;
  cleared_match_run_count: number;
  cleared_evolution_run_count: number;
};

export type ToolDemandTestingClearResult = {
  cleared_sheet_count: number;
  cleared_item_count: number;
  cleared_manufacture_plan_count: number;
};

export type ToolDemandSheetActionInput = {
  actor_id: string;
  reason_code: string;
  reason_message: string;
  actor_phase?: string;
};

export type ToolDemandReviewDecisionInput = {
  decision: "approve_delivery" | "approve_manufacture" | "reject";
  importance_score?: number | null;
  urgency_score?: number | null;
  rationality_verdict: string;
  review_comment: string;
  reviewed_by: string;
};

export type ItemProgressView = {
  item_id: string;
  sheet_id: string;
  status: ToolDemandItemProcessingStatus;
  sheet_lifecycle_status: ToolDemandSheetLifecycleStatus;
  sheet_review_status: ToolDemandSheetReviewStatus;
  sheet_delivery_status: ToolDemandSheetDeliveryStatus;
  review_status: ToolDemandItemReviewStatus;
  result_type?: ToolSupplyResultType | null;
  progress_percent: number;
  estimated_ready_at?: string | null;
  suggested_poll_after_seconds?: number | null;
  fetch_interface?: ToolFetchManifest | null;
  last_message: string;
  updated_at: string;
};

export type P3OrderStatus =
  | "pending_approval"
  | "rejected"
  | "approved_for_generation"
  | "generating"
  | "draft_ready"
  | "in_revision"
  | "pending_review"
  | "changes_requested"
  | "frozen"
  | "package_ready"
  | "pushed_to_p4";

export type P3OrderSummary = {
  order_id: string;
  requirement_spec_id: string;
  application_name: string;
  status: P3OrderStatus;
  updated_at: string;
};

export type SoftwareDesignOverview = {
  metrics: {
    order_count: number;
    pending_approval_count: number;
    frozen_count: number;
    package_ready_count: number;
    pushed_count: number;
  };
  recent_orders: P3OrderSummary[];
  recent_packages: Array<{
    package_id: string;
    order_id: string;
    item_count: number;
    push_status: string;
  }>;
};

export type P3ReviewThread = {
  thread_id: string;
  topic: string;
  anchor: string;
  status: "open" | "resolved";
  messages: string[];
};

export type P3WorkorderBatch = {
  package_id?: string;
  package_overview: {
    architecture_recommendation: string;
    interaction_mode: string;
    deployment_hint?: string;
    tool_recommendations?: string[];
    design_notes?: string[];
  };
  items: Array<{ item_id: string; title: string }>;
  push_status?: string;
};

export type P3OrderDetail = {
  order_id: string;
  status: P3OrderStatus;
  requirement_spec_summary: {
    application_name: string;
    domain_name: string;
    status: string;
  };
  design_description: {
    sections: Array<{ id: string; title: string; summary: string; body?: string }>;
    modules?: Array<{ module_id: string; name: string; objective: string }>;
  } | null;
  review_threads: P3ReviewThread[];
  workorder_batch: P3WorkorderBatch | null;
};

export type P3ReferenceSection = {
  section_id: string;
  title: string;
  summary: string;
};

export type P3ReferenceTemplate = {
  template_id: string;
  title: string;
  source_doc_id: string;
  document_type: "software_design_description";
  version: string;
  format: "pdf";
  summary: string;
  recommendation: string;
  official_detail_url: string;
  pdf_asset_name: string;
  pdf_url: string | null;
  sections: P3ReferenceSection[];
};

export type P3StandardReference = {
  doc_id: string;
  title: string;
  category: string;
  scope: string;
  summary: string;
  official_detail_url: string;
  recommended_use: string;
  tags: string[];
  sections: P3ReferenceSection[];
};

export type P3TemplateStandardMapping = {
  template_id: string;
  doc_id: string;
  rationale: string;
  section_pairs: Array<{ template_section: string; standard_section: string }>;
};

export type P3ReferenceCenter = {
  templates: P3ReferenceTemplate[];
  standards: P3StandardReference[];
  mappings: P3TemplateStandardMapping[];
};

export type P3StandardSearchResult = {
  doc_id: string;
  title: string;
  matched_section: string;
  excerpt: string;
  official_detail_url: string;
};

export type P5DeliveryOrderStatus =
  | "draft"
  | "assembling"
  | "exported_with_gaps"
  | "completed_with_gaps"
  | "completed"
  | "failed";

export type P5BuildOverview = {
  metrics: {
    order_count: number;
    draft_count: number;
    exported_with_gaps_count: number;
    completed_count: number;
    failed_count: number;
  };
  recent_orders: P5DeliveryOrderSummary[];
};

export type P5DeliveryOrderSummary = {
  delivery_order_id: string;
  p3_order_id: string;
  application_name: string;
  status: P5DeliveryOrderStatus;
  current_attempt_count: number;
  updated_at: string;
};

export type P5DeliveryOrder = {
  delivery_order_id: string;
  p3_order_id: string;
  requirement_spec_id: string;
  application_name: string;
  requested_by: string;
  notes: string;
  status: P5DeliveryOrderStatus;
  current_attempt_count: number;
  formal_result_ready: boolean;
  active_input_binding: P5InputBinding;
  created_at: string;
  updated_at: string;
};

export type P5SupplyInputTool = {
  tool_id: string;
  tool_name: string;
  tool_slug: string;
  verification_status: string;
  keywords: string[];
};

export type P5DesignInputSource = {
  design_input_id: string;
  source_kind: "p3_baseline" | "xx_p3_doc_sim";
  source_ref_id: string;
  p3_order_id?: string | null;
  application_name: string;
  requirement_spec_id: string;
  baseline_id: string;
  notes: string;
  module_count: number;
  module_names: string[];
  created_at: string;
  updated_at: string;
};

export type P5SupplyInputSource = {
  supply_input_id: string;
  source_kind: "p4_supply" | "xx_p4_supply_sim";
  source_ref_id: string;
  snapshot_name: string;
  notes: string;
  tool_count: number;
  tool_names: string[];
  tools: P5SupplyInputTool[];
  created_at: string;
  updated_at: string;
};

export type P5ModuleBindingDecision = {
  module_id: string;
  tool_id: string;
  tool_name?: string | null;
  source: "manual";
  updated_by: string;
  updated_at: string;
};

export type P5InputBinding = {
  binding_id: string;
  delivery_order_id: string;
  design_input_id: string;
  supply_input_id?: string | null;
  supply_mode: "snapshot" | "empty";
  module_bindings: P5ModuleBindingDecision[];
  is_confirmed: boolean;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  updated_at: string;
};
export type P5ExportConfig = {
  export_root: string;
  build_profile: string;
  attempt_note: string;
};

export type P5AssemblyModule = {
  module_id: string;
  name: string;
  objective: string;
  target_directories: string[];
  binding_status: "bound" | "placeholder";
  binding_source: "heuristic" | "manual" | "empty";
  bound_tool_id?: string | null;
  bound_tool_name?: string | null;
  gap_reason?: string | null;
};

export type P5AssemblyPlan = {
  modules: P5AssemblyModule[];
};

export type P5GapRecord = {
  gap_id: string;
  kind: "design_gap" | "supply_gap" | "assembly_or_build_gap";
  module_id?: string | null;
  module_name?: string | null;
  summary: string;
  detail: string;
};

export type P5FeedbackTask = {
  task_id: string;
  gap_id: string;
  kind: "design_gap" | "supply_gap" | "assembly_or_build_gap";
  title: string;
  detail: string;
  status: "pending_confirmation" | "confirmed" | "dismissed";
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_note?: string | null;
};

export type P5ValidationReport = {
  module_closure_status: "passed" | "warning" | "failed" | "skipped";
  structure_status: "passed" | "warning" | "failed" | "skipped";
  build_status: "passed" | "warning" | "failed" | "skipped";
  summary: string;
};

export type P5InputSnapshot = {
  design_input: {
    source_kind: string;
    design_input_id: string;
    order_id: string;
    baseline_id: string;
    module_count: number;
    module_names: string[];
  };
  supply_input: {
    source_kind: string;
    supply_input_id?: string | null;
    tool_count: number;
    tool_names: string[];
    matched_tool_count: number;
  };
};

export type P5RuntimeSnapshot = {
  executor_name: string;
  executor_status: "idle" | "running" | "completed" | "blocked" | "failed";
  attempt_status: P5DeliveryOrderStatus;
  progress_percent: number;
  stages: Array<{
    stage_id: string;
    label: string;
    status: "pending" | "running" | "completed" | "warning" | "failed";
    detail: string;
  }>;
  recent_logs: Array<{
    timestamp: string;
    level: "info" | "warning" | "error";
    message: string;
  }>;
  block_reason?: string | null;
};

export type P5OutputPreview = {
  root_directory: string;
  directories: string[];
  key_files: Array<{
    path: string;
    kind: "file" | "directory";
    status: "generated" | "generated_with_gaps" | "placeholder";
    summary: string;
  }>;
};

export type P5AssemblyAttempt = {
  attempt_id: string;
  delivery_order_id: string;
  sequence: number;
  export_config: P5ExportConfig;
  input_snapshot: P5InputSnapshot;
  assembly_plan: P5AssemblyPlan;
  runtime_snapshot: P5RuntimeSnapshot;
  validation_report: P5ValidationReport;
  output_preview: P5OutputPreview;
  gaps: P5GapRecord[];
  feedback_tasks: P5FeedbackTask[];
  export_directory: string;
  created_at: string;
  updated_at: string;
};

export type P5DeliveryOrderDetail = {
  delivery_order_id: string;
  p3_order_id: string;
  requirement_spec_id: string;
  application_name: string;
  requested_by: string;
  notes: string;
  status: P5DeliveryOrderStatus;
  current_attempt_count: number;
  formal_result_ready: boolean;
  active_input_binding: P5InputBinding;
  created_at: string;
  updated_at: string;
  attempts: P5AssemblyAttempt[];
};

export type P5WorkspaceBootstrapResult = {
  delivery_order_id: string;
  attempt_id: string;
  created_demo_inputs: boolean;
};

export type P5DeliveryRuntimeClearResult = {
  cleared_order_count: number;
  cleared_attempt_count: number;
  cleared_export_directory_count: number;
};

export type P3DesignLabInputPackage = {
  input_package_id: string;
  source_document_id: string;
  source_title: string;
  standard_document: RequirementAuthoringStandardDocument;
  structured_spec: Record<string, unknown>;
  annotations: RequirementAuthoringAnnotation[];
  knowledge_binding?: RequirementAuthoringKnowledgeBinding | null;
  frozen_at?: string | null;
  p3_consumable: boolean;
  related_designs?: P3DesignLabRelatedDesign[];
};

export type P3DesignLabRelatedDesign = {
  software_design_id: string;
  title: string;
  version_label: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type P3DesignLabDocumentSection = {
  section_id: string;
  title: string;
  content: string;
  status?: string;
  source_refs?: string[];
  quality?: Record<string, unknown>;
  blocks?: P3DesignLabDocumentBlock[];
  children?: P3DesignLabDocumentSection[];
  subsections?: P3DesignLabDocumentSection[];
};

export type P3DesignLabDocumentBlock = {
  block_id?: string;
  blockId?: string;
  kind?: string;
  title?: string;
  content?: string;
  diagram_type?: string;
  diagramType?: string;
  columns?: string[];
  rows?: string[][];
  source_refs?: string[];
  sourceRefs?: string[];
  quality_refs?: string[];
  qualityRefs?: string[];
  anchor_id?: string;
  anchorId?: string;
};

export type P3DesignLabDesignDocument = {
  title: string;
  version_label?: string;
  sections: P3DesignLabDocumentSection[];
};

export type P3DesignLabFunctionTreeNode = {
  node_id?: string;
  nodeId?: string;
  id?: string;
  title?: string;
  name?: string;
  node_type?: string;
  nodeType?: string;
  type?: string;
  status?: string;
  module_id?: string;
  moduleId?: string;
  source_refs?: string[];
  sourceRefs?: string[];
  design_refs?: string[];
  designRefs?: string[];
  architecture_refs?: string[];
  architectureRefs?: string[];
  p4_refs?: string[];
  p4Refs?: string[];
  description?: string;
  children?: P3DesignLabFunctionTreeNode[];
};

export type P3DesignLabFunctionTree = {
  tree_id?: string;
  treeId?: string;
  title?: string;
  root?: P3DesignLabFunctionTreeNode | null;
};

export type P3DesignLabDesignBaseline = {
  baseline_id: string;
  application_name?: string;
  architecture_mode: string;
  modules: Array<{ module_id: string; name: string; source_refs?: string[] }>;
  function_tree?: P3DesignLabFunctionTree;
  functionTree?: P3DesignLabFunctionTree;
  traceability?: Array<Record<string, string>>;
  pending_confirmations?: string[];
};

export type P3DesignLabWorkorderProjection = {
  package_overview?: Record<string, unknown>;
  tree?: P3DesignLabProjectionTreeNode;
  items: Array<{ item_id: string; title: string; module_id?: string; description?: string; readiness?: string }>;
};

export type P3DesignLabProjectionTreeNode = {
  node_id: string;
  title: string;
  node_type: string;
  description?: string;
  readiness?: string;
  source_refs?: string[];
  depends_on?: string[];
  acceptance?: string;
  children?: P3DesignLabProjectionTreeNode[];
};

export type P3DesignLabFrozenPackage = {
  package_id: string;
  version_label: string;
  status: string;
  frozen_at: string;
  design_document?: P3DesignLabDesignDocument;
  design_baseline?: P3DesignLabDesignBaseline;
  workorder_projection?: P3DesignLabWorkorderProjection;
};

export type P3DesignLabRuntimeEvent = {
  event_id: string;
  event_type: string;
  message: string;
  created_at: string;
};

export type P3DesignLabConversionStep = {
  step_id: string;
  title: string;
  description: string;
  status: "pending" | "running" | "done" | "failed" | string;
};

export type P3DesignLabConversionState = {
  status: "conversion_pending" | "conversion_running" | "conversion_failed" | "draft_ready" | string;
  strategy: string;
  strategy_options: Array<{ value: string; label: string; description: string }>;
  steps: P3DesignLabConversionStep[];
  draft_preview?: {
    title: string;
    version_label?: string;
    sections: string[];
  } | null;
  traceability_summary?: {
    mapped_clause_count: number;
    target_count: number;
    pending_confirmation_count: number;
  } | null;
  process_output?: Record<string, unknown>;
};

export type P3DesignLabSession = {
  session_id: string;
  input_package: P3DesignLabInputPackage;
  design_title?: string;
  version_label?: string;
  generation_policy: Record<string, string>;
  status: string;
  conversion?: P3DesignLabConversionState | null;
  design_document: P3DesignLabDesignDocument | null;
  design_baseline: P3DesignLabDesignBaseline | null;
  workorder_projection: P3DesignLabWorkorderProjection | null;
  turns: Array<Record<string, unknown>>;
  check_result?: RequirementAuthoringCheckResult | null;
  frozen_package?: P3DesignLabFrozenPackage | null;
  runtime_events?: P3DesignLabRuntimeEvent[];
  created_at?: string;
  updated_at?: string;
};

export type RequirementAnalysisOrchestratorStatus = "active" | "available" | "disabled";

export type RequirementAnalysisOrchestrator = {
  plugin_id?: string;
  orchestrator_id: string;
  name: string;
  plugin_type?: "local_package" | "dify_workflow" | "remote_service";
  observability_level?: "full" | "limited" | "none";
  version?: string;
  stage?: string;
  document_type?: string;
  contract?: string;
  mode?: string;
  status: RequirementAnalysisOrchestratorStatus;
  description: string;
  entry?: string | null;
  capabilities?: readonly string[] | Record<string, boolean>;
  requires?: Record<string, unknown>;
  package_path?: string;
};

export type RequirementAnalysisProvider = {
  provider_id: string;
  name: string;
  status: "active" | "not_configured" | "disabled";
};

export type RequirementAnalysisStableContract = {
  formal_document: boolean;
  template_object: boolean;
  knowledge_binding: boolean;
  draft_persistence: boolean;
  check_and_freeze: boolean;
  p2_to_p3_output: boolean;
};

export type RequirementAnalysisOrchestratorEnvelope = {
  items: RequirementAnalysisOrchestrator[];
  stable_contract: RequirementAnalysisStableContract;
  output_protocol: string[];
};

export type RequirementAnalysisProviderEnvelope = {
  items: RequirementAnalysisProvider[];
};

export type RequirementAnalysisTemplateSummary = {
  template_id: string;
  template_code: string;
  base_template_id: string;
  base_template_name: string;
  name: string;
  description: string;
  status: "active" | "available" | "disabled" | string;
};

export type RequirementAnalysisTemplateEnvelope = {
  items: RequirementAnalysisTemplateSummary[];
};

export type RequirementAnalysisTemplateDetail = RequirementAnalysisTemplateSummary & {
  format: "markdown" | string;
  content: string;
};

export type RequirementSpecWorkItemStatus =
  | "draft"
  | "configured"
  | "revision_draft"
  | "published_to_p3"
  | "archived"
  | string;

export type RequirementSpecWorkItem = {
  spec_item_id: string;
  title: string;
  initial_description: string;
  status: RequirementSpecWorkItemStatus;
  template_id: string;
  knowledge_binding: Record<string, unknown> | null;
  authoring_document_id: string;
  analysis_session_id: string | null;
  published_requirement_spec_id: string | null;
  published_package_id: string | null;
  version: number;
  p3_consumable: boolean;
  next_action?: "enter_config" | "stay" | null;
  available_actions: string[];
  created_at: string;
  updated_at: string;
};

export type RequirementSpecWorkItemEnvelope = {
  items: RequirementSpecWorkItem[];
};

export type RequirementSpecWorkItemCreateInput = {
  title: string;
  initial_description?: string;
  template_id: string;
  knowledge_binding?: Record<string, unknown> | null;
  create_action?: "enter_config" | "stay";
};

export type RequirementSpecWorkItemSaveAsInput = {
  title: string;
  session_id?: string;
};

export type RequirementSpecWorkItemSaveSessionArtifactsInput = {
  session_id?: string;
};

export type RequirementSpecWorkItemConfigureInput = {
  topic: string;
  orchestrator_id?: string;
  provider_id?: string;
  model?: string;
  template_id?: string;
  knowledge_package_id?: string;
  write_policy?: string;
};

export type RequirementAnalysisPageMeta = {
  title: string;
  subtitle: string;
};

export type RequirementAnalysisLabDefaults = {
  topic: string;
  orchestrator_id: string;
  provider_id: string;
  model: string;
  template_id: string;
  knowledge_package_id: string;
  write_policy: string;
};

export type RequirementAnalysisStartupField = {
  field: string;
  label: string;
  control: string;
  required?: boolean;
  placeholder?: string;
};

export type RequirementAnalysisWritePolicyOption = {
  policy_id: string;
  label: string;
  description: string;
};

export type RequirementAnalysisFieldSchemaItem = {
  path: string;
  label: string;
  description: string;
  used_when?: string;
};

export type RequirementAnalysisFieldSchema = {
  fields: RequirementAnalysisFieldSchemaItem[];
};

export type RequirementAnalysisTurnAuditSchema = {
  protocol_version: string;
  required_fields: string[];
};

export type RequirementAnalysisLabConfig = {
  page: RequirementAnalysisPageMeta;
  defaults: RequirementAnalysisLabDefaults;
  startup_fields: RequirementAnalysisStartupField[];
  write_policies: RequirementAnalysisWritePolicyOption[];
  provider_log_schema: RequirementAnalysisFieldSchema;
  turn_audit_schema: RequirementAnalysisTurnAuditSchema;
};

export type RequirementAnalysisMessage = {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  turn_id?: string;
  created_at?: string;
};

export type RequirementAnalysisDocumentPatch = {
  plan_ref: string;
  operation: string;
  content: string;
  write_policy?: string;
};

export type RequirementAnalysisTemplateShapeAssessment = {
  shape_type: string;
  reason?: string;
  allowed_write_modes?: string[];
  forbidden_write_modes?: string[];
  template_revision_recommendations?: string[];
};

export type RequirementAnalysisTargetAnchorPlan = {
  plan_id: string;
  decision_type: string;
  template_clause_id: string;
  canonical_clause_heading?: string;
  subtopic_action?: string;
  subtopic_key?: string;
  subtopic_title?: string;
  display_heading?: string;
  template_shape_ref?: string;
  reason?: string;
  confidence?: string;
  anchor_path?: string;
};

export type RequirementAnalysisQuestionStatus = "open" | "confirmed" | "cancelled" | "superseded" | "review";

export type RequirementAnalysisQuestionItem = {
  question_id: string;
  content: string;
  status: RequirementAnalysisQuestionStatus | string;
  target_section?: string | null;
  source_turn_id: string | null;
  resolution_fact_ids: string[];
};

export type RequirementAnalysisConfirmedFactItem = {
  fact_id: string;
  content: string;
  source_turn_id: string;
  source_question_ids: string[];
  target_section?: string | null;
};

export type RequirementAnalysisPatchProposal = {
  patch_id: string;
  target_section: string;
  operation: string;
  content: string;
  write_policy?: string;
  status: "proposed" | "accepted" | "rejected" | string;
  source_fact_ids: string[];
  source_question_ids: string[];
};

export type RequirementAnalysisSpecTreeNode = {
  node_id: string;
  title: string;
  target_section: string;
  node_type?: string;
  question?: string;
  status: "open" | "partial" | "closed" | "skipped" | string;
  answer_summary: string;
  completion_reason: string;
  children: RequirementAnalysisSpecTreeNode[];
};

export type RequirementAnalysisTurnPathItem = {
  turn_id: string;
  node_id: string;
  question_id?: string | null;
  previous_interaction_id?: string | null;
  input_relation?: string;
  affected_node_ids?: string[];
  next_interaction_id?: string | null;
  closed_node_ids: string[];
  answer_summary: string;
};

export type RequirementAnalysisQuickOption = {
  key: string;
  label: string;
  recommended?: boolean;
};

export type RequirementAnalysisServiceStep = {
  step: number;
  title: string;
  status: string;
};

export type RequirementAnalysisInteraction = {
  interaction_id?: string | null;
  type: "none" | "open_question" | "choice_question" | "suggestion" | "free_continue" | string;
  prompt: string;
  options: RequirementAnalysisQuickOption[];
  target_spec_node_ids: string[];
  reason?: string;
};

export type RequirementAnalysisInputRelation = {
  relation: string;
  reason: string;
};

export type RequirementAnalysisOrganizerInterpretation = {
  summary: string;
  intent?: string;
  confidence?: string;
};

export type RequirementAnalysisAffectedSpecNode = {
  node_id: string | null;
  title?: string;
  target_section?: string;
  effect: string;
  reason: string;
};

export type RequirementAnalysisClosureAssessment = {
  status: string;
  reason: string;
  next_action: string;
};

export type RequirementAnalysisStateChanges = {
  closed_question_ids: string[];
  created_question_ids: string[];
  closed_spec_node_ids: string[];
  next_active_spec_node_id?: string | null;
};

export type RequirementAnalysisSpecExecution = {
  interpretation: RequirementAnalysisOrganizerInterpretation;
  assistant_message: string;
  confirmed_facts: string[];
  affected_spec_nodes: RequirementAnalysisAffectedSpecNode[];
  template_shape_assessment?: RequirementAnalysisTemplateShapeAssessment;
  target_anchor_plan?: RequirementAnalysisTargetAnchorPlan[];
  document_patch: RequirementAnalysisDocumentPatch[];
  working_document_update: {
    applied_block_ids: string[];
    applied_fragment_ids: string[];
    blocks: RequirementAnalysisWorkingDocumentBlock[];
    before_excerpt: string;
    after_excerpt: string;
  };
  state_changes: RequirementAnalysisStateChanges;
  annotations: string[];
  risks: string[];
};

export type RequirementAnalysisPostUpdateReview = {
  summary: string;
  target_review: {
    status: string;
    review_target: string[];
    reason: string;
    missing_aspects: string[];
  };
  global_review: {
    status: string;
    summary: string;
    remaining_gaps: string[];
  };
};

export type RequirementAnalysisWorkingDocumentBlock = {
  block_id: string;
  anchor_path: string;
  block_type: string;
  order_index?: number;
  display_heading?: string;
  text: string;
  last_turn_id: string | null;
  source_fragment_ids: string[];
};

export type RequirementAnalysisRevisionFragment = {
  fragment_id: string;
  turn_id: string;
  color_token: string;
  target_block_id: string;
  apply_mode: string;
  start_offset: number;
  end_offset: number;
  deleted_text?: string;
  user_input_summary?: string;
  supplement_reason?: string;
  hit_spec_nodes?: string[];
  source_patch_ids?: string[];
};

export type RequirementAnalysisWorkingDocument = {
  document_id: string;
  title: string;
  topic?: string;
  template_id?: string;
  blocks: RequirementAnalysisWorkingDocumentBlock[];
  revision_fragments: RequirementAnalysisRevisionFragment[];
};

export type RequirementAnalysisSessionPhase =
  | "configured"
  | "exploration_convergence"
  | "draft_entry_confirmation"
  | "draft_generation"
  | "draft_review"
  | string;

export type RequirementAnalysisDecisionStateItem = {
  item_id?: string;
  content: string;
  source_turn_id?: string | null;
  target_section?: string;
  status?: string;
};

export type RequirementAnalysisDecisionState = {
  topic?: string;
  confirmed_facts: RequirementAnalysisDecisionStateItem[];
  confirmed_decisions: RequirementAnalysisDecisionStateItem[];
  tentative_assumptions: RequirementAnalysisDecisionStateItem[];
  open_questions: RequirementAnalysisDecisionStateItem[];
  rejected_directions: RequirementAnalysisDecisionStateItem[];
  next_focus: string;
  chapter_projections: RequirementAnalysisDecisionStateItem[];
};

export type RequirementAnalysisDecisionStateDocumentSection = {
  section_id: string;
  heading: string;
  items: RequirementAnalysisDecisionStateItem[];
};

export type RequirementAnalysisDecisionStateDocument = {
  document_id: string;
  title: string;
  phase: RequirementAnalysisSessionPhase;
  sections: RequirementAnalysisDecisionStateDocumentSection[];
};

export type RequirementAnalysisWorkingDocumentSection = {
  section_id: string;
  target_section: string;
  content: string;
  source_patch_ids: string[];
  last_turn_id: string | null;
  review_status: string;
  review_reason: string;
};

export type RequirementAnalysisTurn = {
  turn_id: string;
  session_id: string;
  user_input: string;
  orchestrator_plugin?: {
    plugin_id: string;
    plugin_type?: "local_package" | "dify_workflow" | "remote_service";
    observability_level?: "full" | "limited" | "none";
  };
  previous_interaction: RequirementAnalysisInteraction;
  normalized_input: {
    input_type: string;
    matched_option: string | null;
    matched_option_label?: string | null;
    semantic: string;
  };
  input_relation: RequirementAnalysisInputRelation;
  spec_execution: RequirementAnalysisSpecExecution;
  post_update_review: RequirementAnalysisPostUpdateReview;
  decision_state_delta?: Partial<RequirementAnalysisDecisionState>;
  decision_state_change_summary?: {
    turn_id: string;
    added_counts: Record<string, number>;
    next_focus: string;
  } | Record<string, unknown>;
  decision_state_document?: RequirementAnalysisDecisionStateDocument;
  closure_decision: RequirementAnalysisClosureAssessment;
  next_interaction: RequirementAnalysisInteraction;
  stage_audits?: RequirementAnalysisTurnStageAudit[];
  decision_trace: string[];
  confidence: string;
  service_steps: RequirementAnalysisServiceStep[];
  raw_model_response: Record<string, unknown>;
  raw_plugin_response?: Record<string, unknown>;
  created_at: string;
};

export type RequirementAnalysisTurnStageAudit = {
  stage_id: string;
  stage_kind: string;
  stage_type: string;
  execution_mode: string;
  provider_call_log_id: string | null;
  validation_status: string;
  blocking_used?: boolean;
  adopted_fields: string[];
  summary: string;
};

export type RequirementAnalysisProviderLog = {
  call_id: string;
  turn_id?: string | null;
  stage_id?: string;
  stage_type?: string;
  provider_id: string;
  orchestrator_id?: string;
  orchestrator_mode?: string;
  model: string;
  status: string;
  audit?: {
    user_input?: string;
    normalized_input?: Record<string, unknown>;
    provider_request?: Record<string, unknown>;
    provider_response?: Record<string, unknown>;
    provider_normalized_output?: Record<string, unknown>;
    service_output?: Record<string, unknown>;
  };
  created_at: string;
};

export type RequirementAnalysisSession = {
  session_id: string;
  topic: string;
  status: "created" | "waiting_user" | "running" | "failed" | "completed";
  orchestrator: RequirementAnalysisOrchestrator;
  provider_id: string;
  model: string;
  template_id: string;
  knowledge_package_id: string;
  write_policy: string;
  session_phase: RequirementAnalysisSessionPhase;
  decision_state: RequirementAnalysisDecisionState;
  decision_state_document: RequirementAnalysisDecisionStateDocument;
  draft_snapshot?: Record<string, unknown> | null;
  stable_contract: RequirementAnalysisStableContract;
  messages: RequirementAnalysisMessage[];
  turns: RequirementAnalysisTurn[];
  confirmed_facts: string[];
  open_questions: string[];
  document_patch: RequirementAnalysisDocumentPatch[];
  working_document: RequirementAnalysisWorkingDocument;
  questions: RequirementAnalysisQuestionItem[];
  facts: RequirementAnalysisConfirmedFactItem[];
  patches: RequirementAnalysisPatchProposal[];
  spec_tree: RequirementAnalysisSpecTreeNode[];
  active_spec_node_id: string | null;
  turn_path: RequirementAnalysisTurnPathItem[];
  annotations: string[];
  risks: string[];
  provider_logs: RequirementAnalysisProviderLog[];
  next_interaction: RequirementAnalysisInteraction | null;
  created_at: string;
  updated_at: string;
};

export type RequirementAnalysisSessionCreateInput = {
  topic: string;
  orchestrator_id?: string;
  provider_id: string;
  model?: string;
  template_id?: string;
  knowledge_package_id?: string;
  write_policy?: string;
};

export type RequirementAnalysisTurnEnvelope = {
  session: RequirementAnalysisSession;
  turn: RequirementAnalysisTurn;
};

export type RequirementAuthoringWorkbenchDefaults = {
  document_title: string;
  layout_ratio: RequirementAuthoringLayoutRatio;
  allow_empty_knowledge_binding: boolean;
};

export type RequirementAuthoringLayoutOption = {
  ratio: RequirementAuthoringLayoutRatio;
  label: string;
};

export type RequirementAuthoringStatusDefinition = {
  status: RequirementAuthoringDocumentStatus | string;
  label: string;
  editable: boolean;
};

export type RequirementAuthoringActionDefinition = {
  action_id: "create_document" | "open_document" | "save_draft" | "delete_document" | "run_check" | "freeze" | string;
  label: string;
  style?: "primary" | string;
  requires_document?: boolean;
  disabled_when_frozen?: boolean;
  danger?: boolean;
};

export type RequirementAuthoringDocumentSurfaceConfig = {
  title: string;
  badges: string[];
  ribbon: string[];
};

export type RequirementAuthoringWorkbenchConfig = {
  page: RequirementAnalysisPageMeta;
  defaults: RequirementAuthoringWorkbenchDefaults;
  layout_options: RequirementAuthoringLayoutOption[];
  document_statuses: RequirementAuthoringStatusDefinition[];
  actions: RequirementAuthoringActionDefinition[];
  document_surface: RequirementAuthoringDocumentSurfaceConfig;
  empty_states: Record<string, string>;
};
