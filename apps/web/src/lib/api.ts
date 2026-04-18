import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
});

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
  state: "pending" | "running" | "completed" | "failed";
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

export type KnowledgeArchiveBuildState = {
  archive_id: string;
  archive_name: string;
  mode: string;
  status: string;
  started_at: string | null;
  updated_at: string | null;
  expected_document_count: number;
  completed_document_ids: string[];
  pending_document_ids: string[];
  failed_document_id: string | null;
  failed_message: string | null;
  current_document_id: string | null;
  current_document_title: string | null;
  current_document_path: string | null;
  current_chunk: KnowledgeArchiveBuildStateChunk | null;
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
  runtime_platform_ids: string[];
  tags: string[];
  lifecycle_stage_ids: string[];
  input_types: string[];
  output_types: string[];
  supported_sources: string[];
  usage_notes: string;
  keywords: string[];
  verification: ToolVerification;
  created_at: string;
  updated_at: string;
};

export type ToolDefinitionWriteInput = Omit<ToolDefinition, "tool_id" | "created_at" | "updated_at">;

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
  runtime_platform_ids: string[];
  fetch_mode: "descriptor";
  entrypoint_type: "http" | "descriptor" | "artifact_ref" | "manual";
  entrypoint_locator: string;
  contract_version: string;
  updated_at: string;
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
