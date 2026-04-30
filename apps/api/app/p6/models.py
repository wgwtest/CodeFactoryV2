from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceMode = Literal["mock", "live"]
FreshnessState = Literal["fresh", "stale", "unknown"]
HealthLevel = Literal["healthy", "warning", "blocked", "unknown"]
BadgeTone = Literal["ready", "warning", "blocked", "neutral"]
NodeKind = Literal["module", "user"]
ProjectionMode = Literal["auto", "manual"]
PinSide = Literal["left", "right", "top", "bottom"]
RenderTone = Literal["knowledge", "analysis", "design", "tooling", "delivery"]
RenderStyle = Literal["solid", "dashed"]
FlowDirection = Literal["input", "output", "process"]


class DisplayBadge(BaseModel):
    label: str
    tone: BadgeTone
    detail: str | None = None


class StageMetricProjection(BaseModel):
    metric_key: str
    metric_label: str
    metric_value: str
    metric_trend: str | None = None


class StageOverview(BaseModel):
    stage_id: str
    stage_name: str
    stage_display_name: str
    primary_status: str
    summary: str
    updated_at: str
    freshness: FreshnessState


class StageEntryProjection(BaseModel):
    entry_route: str
    entry_available: bool
    entry_reason: str


class StageHealthProjection(BaseModel):
    health_level: HealthLevel
    health_message: str
    health_source: str
    captured_at: str


class StageOverallMetricProjection(BaseModel):
    key: str
    label: str
    value: int | float | str
    unit: str
    basis: str


class StageLiveCounterProjection(BaseModel):
    key: str
    label: str
    value: int | float | str
    unit: str
    window: str
    direction: FlowDirection


class StageFlowPortProjection(BaseModel):
    port_id: str
    side: Literal["left", "right"]
    direction: Literal["input", "output"]
    label: str
    connected_target: str
    current_rate: str
    terminal: bool = False


class StageConnectedUserProjection(BaseModel):
    user_ref: str
    display_label: str
    role_label: str
    activity_state: str
    connected_at: str


class StageQueueItemProjection(BaseModel):
    item_id: str
    label: str
    state: str
    order_index: int


class StageQueueProjection(BaseModel):
    queue_id: str
    label: str
    items: list[StageQueueItemProjection] = Field(default_factory=list)
    active_index: int
    advance_rule: str


class StageDisplayBinding(BaseModel):
    prototype_refs: list[str] = Field(default_factory=list)
    regions: dict[str, str]


class StageSourceTrace(BaseModel):
    field: str
    source_doc: str
    source_object: str
    calculation_basis: str
    freshness_policy: str | None = None
    display_reason: str


class StageNodeStatusPayload(BaseModel):
    contract_version: str = "P6DisplayExportContract.v2"
    stage_id: str
    headline_value: str
    summary_line: str
    metric_items: list[StageMetricProjection] = Field(default_factory=list)
    system_overall_metric_items: list[StageOverallMetricProjection] = Field(default_factory=list)
    live_counter_items: list[StageLiveCounterProjection] = Field(default_factory=list)
    flow_port_items: list[StageFlowPortProjection] = Field(default_factory=list)
    connected_user_items: list[StageConnectedUserProjection] = Field(default_factory=list)
    queue_projection: StageQueueProjection | None = None
    display_binding: StageDisplayBinding | None = None
    source_trace: list[StageSourceTrace] = Field(default_factory=list)
    entry_badge: DisplayBadge
    health_badge: DisplayBadge
    timestamp_label: str
    degraded_hint: str | None = None


class P6DisplayExportContract(BaseModel):
    contract_version: Literal["P6DisplayExportContract.v2"]
    stage_overview: StageOverview
    entry_projection: StageEntryProjection
    system_overall_metrics: list[StageOverallMetricProjection] = Field(default_factory=list)
    live_counters: list[StageLiveCounterProjection] = Field(default_factory=list)
    flow_ports: list[StageFlowPortProjection] = Field(default_factory=list)
    connected_users: list[StageConnectedUserProjection] = Field(default_factory=list)
    queue_projection: StageQueueProjection
    display_binding: StageDisplayBinding
    health_projection: StageHealthProjection
    source_trace: list[StageSourceTrace] = Field(default_factory=list)
    stage_specific: dict[str, Any] = Field(default_factory=dict)


class StageSnapshot(BaseModel):
    snapshot_id: str
    stage_id: str
    stage_name: str
    primary_status: str
    summary: str
    entry_projection: StageEntryProjection
    metric_list: list[StageMetricProjection] = Field(default_factory=list)
    health_projection: StageHealthProjection
    captured_at: str
    projection_at: str
    freshness: FreshnessState
    degraded_reason: str | None = None
    node_status_payload: StageNodeStatusPayload
    display_contract: P6DisplayExportContract | None = None


class ParticipantNodePayload(BaseModel):
    role_label: str
    title: str
    context_label: str
    interaction_hints: list[str] = Field(default_factory=list)
    availability_hint: str


class PortalNode(BaseModel):
    node_id: str
    node_kind: NodeKind
    title: str
    stage_id: str | None = None
    route: str | None = None
    projection_mode: ProjectionMode
    summary: str
    primary_status: str | None = None
    freshness: FreshnessState | None = None
    description: str
    stage_card: StageNodeStatusPayload | None = None
    participant_payload: ParticipantNodePayload | None = None


class PortalFlow(BaseModel):
    flow_id: str
    from_node_id: str
    to_node_id: str
    semantic_type: str
    direction: Literal["forward"]
    from_pin: PinSide
    to_pin: PinSide
    render_tone: RenderTone
    render_style: RenderStyle
    label: str


class PortalArtifact(BaseModel):
    artifact_id: str
    artifact_kind: str
    title: str
    summary: str
    linked_node_ids: list[str] = Field(default_factory=list)
    source_mode: SourceMode
    render_tone: Literal["analysis", "design", "tooling"]
    projection_mode: ProjectionMode


class PortalSummary(BaseModel):
    headline: str
    source_label: str
    scenario_label: str
    module_count: int
    user_count: int
    artifact_count: int
    flow_count: int
    focus_hint: str
    alert_message: str


class KnowledgeContext(BaseModel):
    current_knowledge_base_name: str
    archive_label: str
    context_hint: str


class PortalProjection(BaseModel):
    node_list: list[PortalNode] = Field(default_factory=list)
    flow_list: list[PortalFlow] = Field(default_factory=list)
    artifact_list: list[PortalArtifact] = Field(default_factory=list)
    portal_summary: PortalSummary
    knowledge_context: KnowledgeContext
    freshness: FreshnessState
    degraded_reason: str | None = None


class ObservationStageCard(BaseModel):
    stage_id: str
    stage_name: str
    headline_value: str
    summary_line: str
    primary_status: str
    freshness: FreshnessState
    entry_badge: DisplayBadge
    health_badge: DisplayBadge
    timestamp_label: str
    degraded_hint: str | None = None


class ObservationComparisonItem(BaseModel):
    comparison_id: str
    label: str
    value: str
    tone: BadgeTone


class ObservationAlertSummary(BaseModel):
    total: int
    warning_stage_ids: list[str] = Field(default_factory=list)
    blocked_stage_ids: list[str] = Field(default_factory=list)
    message: str


class ObservationRouteAction(BaseModel):
    stage_id: str
    label: str
    route: str
    route_available: bool


class ObservationProjection(BaseModel):
    stage_cards: list[ObservationStageCard] = Field(default_factory=list)
    comparison_items: list[ObservationComparisonItem] = Field(default_factory=list)
    alert_summary: ObservationAlertSummary
    route_actions: list[ObservationRouteAction] = Field(default_factory=list)
    focus_stage_id: str
    freshness: FreshnessState
    degraded_reason: str | None = None


class MockScenarioSummary(BaseModel):
    scenario_id: str
    label: str
    description: str
    source_mode: SourceMode
    recommended_focus_stage: str


class MockScenarioCatalog(BaseModel):
    source_mode: SourceMode
    default_scenario_id: str
    items: list[MockScenarioSummary] = Field(default_factory=list)


class StageSnapshotReadEnvelope(BaseModel):
    source_mode: SourceMode
    scenario: MockScenarioSummary
    items: list[StageSnapshot] = Field(default_factory=list)
    projection_at: str
    freshness: FreshnessState
    degraded_reason: str | None = None


class PortalProjectionReadEnvelope(BaseModel):
    source_mode: SourceMode
    scenario: MockScenarioSummary
    projection: PortalProjection


class ObservationProjectionReadEnvelope(BaseModel):
    source_mode: SourceMode
    scenario: MockScenarioSummary
    projection: ObservationProjection


class P6SimulatorContractSubmission(BaseModel):
    scenario_id: str = "simulator-latest"
    label: str
    description: str
    recommended_focus_stage: str = "P3"
    contracts: list[P6DisplayExportContract]


class P6SimulatorSubmissionResponse(BaseModel):
    scenario: MockScenarioSummary
    accepted_contract_count: int
    portal_projection_path: str


class DesignTokenSet(BaseModel):
    token_set_id: str
    color_tokens: dict[str, str]
    spacing_tokens: dict[str, str]
    radius_tokens: dict[str, str]
    shadow_tokens: dict[str, str]
    typography_tokens: dict[str, str]
    version: str


class StageNamingBaseline(BaseModel):
    baseline_id: str
    stage_name_map: dict[str, str]
    forbidden_aliases: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    version: str


class StatusCopyBaseline(BaseModel):
    baseline_id: str
    platform_status_map: dict[str, str]
    state_color_map: dict[str, str]
    feedback_copy_map: dict[str, str]
    version: str


class SharedDisplayPrimitive(BaseModel):
    primitive_id: str
    primitive_kind: str
    supported_states: list[str] = Field(default_factory=list)
    layout_rules: list[str] = Field(default_factory=list)
    interaction_rules: list[str] = Field(default_factory=list)
    example_refs: list[str] = Field(default_factory=list)


class NodeVisualBaseline(BaseModel):
    baseline_id: str
    system_stage_card_rules: dict[str, Any]
    participant_user_node_rules: dict[str, Any]
    artifact_node_rules: dict[str, Any]
    status_annotation_node_rules: dict[str, Any]
    state_transition_rules: dict[str, Any]
    size_tiers: dict[str, Any]


class UpgradeRule(BaseModel):
    rule_id: str
    applies_to_scope: str
    required_primitives: list[str] = Field(default_factory=list)
    allowed_exceptions: list[str] = Field(default_factory=list)
    validation_points: list[str] = Field(default_factory=list)
    priority: int


class PlatformDisplayBaselinePackage(BaseModel):
    version: str
    token_set: DesignTokenSet
    stage_naming_baseline: StageNamingBaseline
    status_copy_baseline: StatusCopyBaseline
    shared_display_primitives: list[SharedDisplayPrimitive] = Field(default_factory=list)
    node_visual_baseline: NodeVisualBaseline
    upgrade_rules: list[UpgradeRule] = Field(default_factory=list)
    exception_rules: list[dict[str, Any]] = Field(default_factory=list)


class PlatformRouteItem(BaseModel):
    route_id: str
    label: str
    path: str
    description: str
    entry_available: bool = True


class PlatformRoutes(BaseModel):
    portal_route: PlatformRouteItem
    observation_route: PlatformRouteItem
    stage_routes: dict[str, PlatformRouteItem]


class PlatformLegendSignalItem(BaseModel):
    tone: str
    label: str
    detail: str


class PlatformLegendRoadmapItem(BaseModel):
    item_id: str
    label: str
    status: str


class PlatformLegend(BaseModel):
    summary_copy: str
    interaction_facts: list[str] = Field(default_factory=list)
    element_language_copy: str
    signal_items: list[PlatformLegendSignalItem] = Field(default_factory=list)
    roadmap_items: list[PlatformLegendRoadmapItem] = Field(default_factory=list)


class DisplayWidgetTemplate(BaseModel):
    template_id: str
    template_name: str
    template_kind: str
    slot_schema: list[str] = Field(default_factory=list)
    supported_field_map: dict[str, str]
    supported_states: list[str] = Field(default_factory=list)
    style_profile_ref: str


class DisplayWidgetBinding(BaseModel):
    binding_id: str
    source_projection_kind: str
    source_stage_scope: str
    field_map: dict[str, str]
    transform_rules: list[str] = Field(default_factory=list)
    fallback_rules: list[str] = Field(default_factory=list)


class DisplayWidgetLayout(BaseModel):
    layout_id: str
    layout_name: str
    region_schema: list[str] = Field(default_factory=list)
    ordering_rules: list[str] = Field(default_factory=list)
    size_rules: list[str] = Field(default_factory=list)
    responsive_rules: list[str] = Field(default_factory=list)


class DisplayWidgetPreset(BaseModel):
    preset_id: str
    preset_name: str
    applicable_scenarios: list[str] = Field(default_factory=list)
    template_refs: list[str] = Field(default_factory=list)
    binding_refs: list[str] = Field(default_factory=list)
    layout_refs: list[str] = Field(default_factory=list)
    status: str


class DisplayExperimentRecord(BaseModel):
    experiment_id: str
    goal: str
    projection_scope: str
    template_refs: list[str] = Field(default_factory=list)
    binding_refs: list[str] = Field(default_factory=list)
    layout_refs: list[str] = Field(default_factory=list)
    preset_refs: list[str] = Field(default_factory=list)
    result_summary: str
    issues: list[str] = Field(default_factory=list)
    promotion_recommendation: str
    target_stage_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str


class DisplayExperimentCreateRequest(BaseModel):
    goal: str
    projection_scope: str
    template_refs: list[str] = Field(default_factory=list)
    binding_refs: list[str] = Field(default_factory=list)
    layout_refs: list[str] = Field(default_factory=list)
    preset_refs: list[str] = Field(default_factory=list)
    result_summary: str
    issues: list[str] = Field(default_factory=list)
    promotion_recommendation: str
    target_stage_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class DisplayPromotionCandidate(BaseModel):
    promotion_candidate_id: str
    source_experiment_id: str
    candidate_kind: str
    target_stage_ids: list[str] = Field(default_factory=list)
    adoption_reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    status: str


class DisplayExperimentList(BaseModel):
    items: list[DisplayExperimentRecord] = Field(default_factory=list)


class DisplayPromotionCandidateList(BaseModel):
    items: list[DisplayPromotionCandidate] = Field(default_factory=list)


class DisplayWorkbenchBootstrap(BaseModel):
    version: str
    templates: list[DisplayWidgetTemplate] = Field(default_factory=list)
    bindings: list[DisplayWidgetBinding] = Field(default_factory=list)
    layouts: list[DisplayWidgetLayout] = Field(default_factory=list)
    presets: list[DisplayWidgetPreset] = Field(default_factory=list)
    experiments: list[DisplayExperimentRecord] = Field(default_factory=list)
    promotion_candidates: list[DisplayPromotionCandidate] = Field(default_factory=list)
