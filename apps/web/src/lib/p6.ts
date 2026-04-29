import { api } from "./api";

export type P6SourceMode = "mock" | "live";
export type P6FreshnessState = "fresh" | "stale" | "unknown";
export type P6BadgeTone = "ready" | "warning" | "blocked" | "neutral";
export type P6ProjectionMode = "auto" | "manual";
export type P6NodeKind = "module" | "user";
export type P6RenderTone = "knowledge" | "analysis" | "design" | "tooling" | "delivery";
export type P6RenderStyle = "solid" | "dashed";
export type P6PinSide = "left" | "right" | "top" | "bottom";

export type P6DisplayBadge = {
  label: string;
  tone: P6BadgeTone;
  detail?: string | null;
};

export type P6StageMetricProjection = {
  metric_key: string;
  metric_label: string;
  metric_value: string;
  metric_trend?: string | null;
};

export type P6StageNodeStatusPayload = {
  stage_id: string;
  headline_value: string;
  summary_line: string;
  metric_items: P6StageMetricProjection[];
  entry_badge: P6DisplayBadge;
  health_badge: P6DisplayBadge;
  timestamp_label: string;
  degraded_hint?: string | null;
};

export type P6ParticipantNodePayload = {
  role_label: string;
  title: string;
  context_label: string;
  interaction_hints: string[];
  availability_hint: string;
};

export type P6PortalNode = {
  node_id: string;
  node_kind: P6NodeKind;
  title: string;
  stage_id?: string | null;
  route?: string | null;
  projection_mode: P6ProjectionMode;
  summary: string;
  primary_status?: string | null;
  freshness?: P6FreshnessState | null;
  description: string;
  stage_card?: P6StageNodeStatusPayload | null;
  participant_payload?: P6ParticipantNodePayload | null;
};

export type P6PortalFlow = {
  flow_id: string;
  from_node_id: string;
  to_node_id: string;
  semantic_type: string;
  direction: "forward";
  from_pin: P6PinSide;
  to_pin: P6PinSide;
  render_tone: P6RenderTone;
  render_style: P6RenderStyle;
  label: string;
};

export type P6PortalArtifact = {
  artifact_id: string;
  artifact_kind: string;
  title: string;
  summary: string;
  linked_node_ids: string[];
  source_mode: P6SourceMode;
  render_tone: "analysis" | "design" | "tooling";
  projection_mode: P6ProjectionMode;
};

export type P6PortalSummary = {
  headline: string;
  source_label: string;
  scenario_label: string;
  module_count: number;
  user_count: number;
  artifact_count: number;
  flow_count: number;
  focus_hint: string;
  alert_message: string;
};

export type P6KnowledgeContext = {
  current_knowledge_base_name: string;
  archive_label: string;
  context_hint: string;
};

export type P6PortalProjection = {
  node_list: P6PortalNode[];
  flow_list: P6PortalFlow[];
  artifact_list: P6PortalArtifact[];
  portal_summary: P6PortalSummary;
  knowledge_context: P6KnowledgeContext;
  freshness: P6FreshnessState;
  degraded_reason?: string | null;
};

export type P6ObservationStageCard = {
  stage_id: string;
  stage_name: string;
  headline_value: string;
  summary_line: string;
  primary_status: string;
  freshness: P6FreshnessState;
  entry_badge: P6DisplayBadge;
  health_badge: P6DisplayBadge;
  timestamp_label: string;
  degraded_hint?: string | null;
};

export type P6ObservationComparisonItem = {
  comparison_id: string;
  label: string;
  value: string;
  tone: P6BadgeTone;
};

export type P6ObservationAlertSummary = {
  total: number;
  warning_stage_ids: string[];
  blocked_stage_ids: string[];
  message: string;
};

export type P6ObservationRouteAction = {
  stage_id: string;
  label: string;
  route: string;
  route_available: boolean;
};

export type P6ObservationProjection = {
  stage_cards: P6ObservationStageCard[];
  comparison_items: P6ObservationComparisonItem[];
  alert_summary: P6ObservationAlertSummary;
  route_actions: P6ObservationRouteAction[];
  focus_stage_id: string;
  freshness: P6FreshnessState;
  degraded_reason?: string | null;
};

export type P6MockScenarioSummary = {
  scenario_id: string;
  label: string;
  description: string;
  source_mode: P6SourceMode;
  recommended_focus_stage: string;
};

export type P6MockScenarioCatalog = {
  source_mode: P6SourceMode;
  default_scenario_id: string;
  items: P6MockScenarioSummary[];
};

export type P6PortalProjectionReadEnvelope = {
  source_mode: P6SourceMode;
  scenario: P6MockScenarioSummary;
  projection: P6PortalProjection;
};

export type P6ObservationProjectionReadEnvelope = {
  source_mode: P6SourceMode;
  scenario: P6MockScenarioSummary;
  projection: P6ObservationProjection;
};

export type P6DesignTokenSet = {
  token_set_id: string;
  color_tokens: Record<string, string>;
  spacing_tokens: Record<string, string>;
  radius_tokens: Record<string, string>;
  shadow_tokens: Record<string, string>;
  typography_tokens: Record<string, string>;
  version: string;
};

export type P6StageNamingBaseline = {
  baseline_id: string;
  stage_name_map: Record<string, string>;
  forbidden_aliases: string[];
  notes: string[];
  version: string;
};

export type P6StatusCopyBaseline = {
  baseline_id: string;
  platform_status_map: Record<string, string>;
  state_color_map: Record<string, string>;
  feedback_copy_map: Record<string, string>;
  version: string;
};

export type P6SharedDisplayPrimitive = {
  primitive_id: string;
  primitive_kind: string;
  supported_states: string[];
  layout_rules: string[];
  interaction_rules: string[];
  example_refs: string[];
};

export type P6NodeVisualBaseline = {
  baseline_id: string;
  system_stage_card_rules: Record<string, unknown>;
  participant_user_node_rules: Record<string, unknown>;
  artifact_node_rules: Record<string, unknown>;
  status_annotation_node_rules: Record<string, unknown>;
  state_transition_rules: Record<string, unknown>;
  size_tiers: Record<string, unknown>;
};

export type P6UpgradeRule = {
  rule_id: string;
  applies_to_scope: string;
  required_primitives: string[];
  allowed_exceptions: string[];
  validation_points: string[];
  priority: number;
};

export type P6PlatformDisplayBaselinePackage = {
  version: string;
  token_set: P6DesignTokenSet;
  stage_naming_baseline: P6StageNamingBaseline;
  status_copy_baseline: P6StatusCopyBaseline;
  shared_display_primitives: P6SharedDisplayPrimitive[];
  node_visual_baseline: P6NodeVisualBaseline;
  upgrade_rules: P6UpgradeRule[];
  exception_rules: Array<Record<string, unknown>>;
};

export type P6PlatformRouteItem = {
  route_id: string;
  label: string;
  path: string;
  description: string;
  entry_available: boolean;
};

export type P6PlatformRoutes = {
  portal_route: P6PlatformRouteItem;
  observation_route: P6PlatformRouteItem;
  stage_routes: Record<string, P6PlatformRouteItem>;
};

export type P6PlatformLegendSignalItem = {
  tone: string;
  label: string;
  detail: string;
};

export type P6PlatformLegendRoadmapItem = {
  item_id: string;
  label: string;
  status: string;
};

export type P6PlatformLegend = {
  summary_copy: string;
  interaction_facts: string[];
  element_language_copy: string;
  signal_items: P6PlatformLegendSignalItem[];
  roadmap_items: P6PlatformLegendRoadmapItem[];
};

export type P6DisplayWidgetTemplate = {
  template_id: string;
  template_name: string;
  template_kind: string;
  slot_schema: string[];
  supported_field_map: Record<string, string>;
  supported_states: string[];
  style_profile_ref: string;
};

export type P6DisplayWidgetBinding = {
  binding_id: string;
  source_projection_kind: string;
  source_stage_scope: string;
  field_map: Record<string, string>;
  transform_rules: string[];
  fallback_rules: string[];
};

export type P6DisplayWidgetLayout = {
  layout_id: string;
  layout_name: string;
  region_schema: string[];
  ordering_rules: string[];
  size_rules: string[];
  responsive_rules: string[];
};

export type P6DisplayWidgetPreset = {
  preset_id: string;
  preset_name: string;
  applicable_scenarios: string[];
  template_refs: string[];
  binding_refs: string[];
  layout_refs: string[];
  status: string;
};

export type P6DisplayExperimentRecord = {
  experiment_id: string;
  goal: string;
  projection_scope: string;
  template_refs: string[];
  binding_refs: string[];
  layout_refs: string[];
  preset_refs: string[];
  result_summary: string;
  issues: string[];
  promotion_recommendation: string;
  target_stage_ids: string[];
  evidence_refs: string[];
  created_at: string;
};

export type P6DisplayPromotionCandidate = {
  promotion_candidate_id: string;
  source_experiment_id: string;
  candidate_kind: string;
  target_stage_ids: string[];
  adoption_reason: string;
  evidence_refs: string[];
  status: string;
};

export type P6DisplayExperimentRecordList = {
  items: P6DisplayExperimentRecord[];
};

export type P6DisplayPromotionCandidateList = {
  items: P6DisplayPromotionCandidate[];
};

export type P6DisplayWorkbenchBootstrap = {
  version: string;
  templates: P6DisplayWidgetTemplate[];
  bindings: P6DisplayWidgetBinding[];
  layouts: P6DisplayWidgetLayout[];
  presets: P6DisplayWidgetPreset[];
  experiments: P6DisplayExperimentRecord[];
  promotion_candidates: P6DisplayPromotionCandidate[];
};

export type P6DisplayExperimentCreateRequest = {
  goal: string;
  projection_scope: string;
  template_refs: string[];
  binding_refs: string[];
  layout_refs: string[];
  preset_refs: string[];
  result_summary: string;
  issues: string[];
  promotion_recommendation: string;
  target_stage_ids: string[];
  evidence_refs: string[];
};

type P6ProjectionParams = {
  source: P6SourceMode;
  scenario: string;
};

export function listP6MockScenarios() {
  return api.get<P6MockScenarioCatalog>("/p6/mock-scenarios");
}

export function getP6PortalProjection(params: P6ProjectionParams) {
  return api.get<P6PortalProjectionReadEnvelope>("/p6/portal-projection", {
    params,
  });
}

export function getP6ObservationProjection(params: P6ProjectionParams) {
  return api.get<P6ObservationProjectionReadEnvelope>("/p6/observation-projection", {
    params,
  });
}

export function getP6DisplayBaseline() {
  return api.get<P6PlatformDisplayBaselinePackage>("/platform-config/display-baseline");
}

export function getP6PlatformRoutes() {
  return api.get<P6PlatformRoutes>("/platform-config/routes");
}

export function getP6PlatformLegend() {
  return api.get<P6PlatformLegend>("/platform-config/legend");
}

export function getP6DisplayWorkbench() {
  return api.get<P6DisplayWorkbenchBootstrap>("/platform-display/workbench");
}

export function listP6DisplayExperiments() {
  return api.get<P6DisplayExperimentRecordList>("/platform-display/experiments");
}

export function createP6DisplayExperiment(payload: P6DisplayExperimentCreateRequest) {
  return api.post<P6DisplayExperimentRecord>("/platform-display/experiments", payload);
}

export function listP6DisplayPromotionCandidates() {
  return api.get<P6DisplayPromotionCandidateList>("/platform-display/promotion-candidates");
}
