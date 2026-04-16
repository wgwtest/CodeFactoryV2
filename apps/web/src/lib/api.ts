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
  artifacts: KnowledgeArchiveArtifacts;
};

export type CreateKnowledgeArchiveInput = {
  archive_id: string;
  name: string;
  source_dir: string;
  extract_root?: string;
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
};

export type ArchiveKnowledgeEvidence = {
  document_id: string | null;
  document_title: string | null;
  excerpt: string;
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
};

export type ArchiveKnowledgeDocument = {
  id: string;
  title: string;
  file_type: string;
  source_archive: string;
  character_count: number;
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
  primary_category_id: string;
  tags: string[];
  applicable_stages: string[];
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
  categories: ToolHubCatalogItem[];
  stages: ToolHubCatalogItem[];
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
  stages: ToolHubCatalogItem[];
  rows: Array<{
    category_id: string;
    category_label: string;
    cells: Array<{
      stage_id: string;
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
  target_stage: string;
  required_input_types: string[];
  expected_output_types: string[];
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
  kind: "missing_description" | "taxonomy_issue" | "overlap_risk" | "coverage_gap";
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  tool_ids: string[];
};

export type EvolutionRun = {
  run_id: string;
  status: "completed";
  created_at: string;
  summary: {
    tool_count: number;
    finding_count: number;
    missing_description_count: number;
    taxonomy_issue_count: number;
    overlap_risk_count: number;
    coverage_gap_count: number;
  };
  findings: EvolutionFinding[];
};

export type EvolutionRunEnvelope = {
  items: EvolutionRun[];
};

export type ToolHubOverview = {
  metrics: ToolHubOverviewMetrics;
  run_monitor: ToolHubRunMonitor;
  coverage_matrix: ToolHubCoverageMatrix;
  risk_summary: ToolHubRiskSummaryItem[];
  pending_suggestions: PendingSuggestionItem[];
  recent_match_runs: ToolHubRecentRunSummary[];
  recent_evolution_runs: ToolHubRecentRunSummary[];
  catalogs: ToolHubCatalogs;
};
