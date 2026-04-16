from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


ToolStatus = Literal["draft", "active", "archived"]
ToolVerificationStatus = Literal["unverified", "verified", "warning", "failed"]
SupportedSource = Literal["p1_readonly_api", "frozen_snapshot", "manual_input", "tool_hub_snapshot"]
RiskKind = Literal["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"]
RiskSeverity = Literal["info", "warning", "critical"]
ToolDemandSheetStatus = Literal["accepted", "processing", "partially_ready", "ready", "failed"]
ToolDemandNodeType = Literal["system", "subsystem", "sub_subsystem", "module", "component"]
ToolDemandItemStatus = Literal[
    "matched_existing",
    "manufacturing_pending",
    "manufacturing_in_progress",
    "ready_for_fetch",
    "failed",
]
ToolSupplyResultType = Literal["existing_tool", "pending_manufacture", "manufactured_tool"]
ToolManufacturePlanStatus = Literal["manufacturing_pending", "manufacturing_in_progress", "ready_for_fetch", "failed"]

LEGACY_CATEGORY_TO_DOMAIN = {
    "knowledge_ingestion": "cross_domain_shared",
    "knowledge_processing": "cross_domain_shared",
    "knowledge_governance": "master_data",
    "knowledge_query": "reporting_audit",
    "application_modeling": "workflow_approval",
    "validation_support": "cross_domain_shared",
}

LEGACY_STAGE_TO_LIFECYCLE = {
    "archive_intake": "domain_discovery",
    "parsing": "domain_discovery",
    "extraction": "solution_design",
    "governance": "build_integration",
    "query": "operation_optimization",
    "modeling": "solution_design",
    "validation": "verification_release",
}

LEGACY_CAPABILITY_TO_DOMAIN = {
    "entity-normalization": "master_data",
    "process-analysis": "workflow_approval",
    "coverage-analysis": "cross_domain_shared",
}


def _infer_domain_from_legacy_payload(payload: dict[str, Any]) -> str:
    capability_tags = payload.get("tags", []) or []
    for tag in capability_tags:
        if not isinstance(tag, str) or not tag.startswith("capability:"):
            continue
        legacy_capability = tag.split(":", 1)[1]
        if legacy_capability in LEGACY_CAPABILITY_TO_DOMAIN:
            return LEGACY_CAPABILITY_TO_DOMAIN[legacy_capability]

    primary_category_id = payload.get("primary_category_id")
    if isinstance(primary_category_id, str) and primary_category_id in LEGACY_CATEGORY_TO_DOMAIN:
        return LEGACY_CATEGORY_TO_DOMAIN[primary_category_id]

    return "cross_domain_shared"


def _infer_tool_form(payload: dict[str, Any]) -> str:
    slug = str(payload.get("slug", "")).lower()
    name = str(payload.get("name", "")).lower()
    summary = str(payload.get("summary", "")).lower()
    if "template" in slug or "模板" in name or "模板" in summary:
        return "template"
    if "library" in slug or "库" in name:
        return "static_library"
    if "service" in slug or "服务" in name:
        return "service_endpoint"
    if "package" in slug or "bundle" in slug or "包" in name:
        return "package_bundle"
    return "skill"


def _normalize_lifecycle_stage_ids(payload: dict[str, Any]) -> list[str]:
    lifecycle_stage_ids = payload.get("lifecycle_stage_ids")
    if isinstance(lifecycle_stage_ids, list) and lifecycle_stage_ids:
        return [str(item) for item in lifecycle_stage_ids]

    legacy_stage_ids = payload.get("applicable_stages")
    if not isinstance(legacy_stage_ids, list):
        legacy_stage_ids = []
    normalized = [
        LEGACY_STAGE_TO_LIFECYCLE.get(str(item), str(item))
        for item in legacy_stage_ids
    ]
    if normalized:
        return sorted(dict.fromkeys(normalized))
    return ["solution_design"]


def _build_canonical_tags(payload: dict[str, Any]) -> list[str]:
    raw_tags = payload.get("tags", []) or []
    managed_prefixes = ("stage:", "capability:", "domain:", "form:", "runtime:", "lifecycle:", "input:", "output:")
    preserved_tags = [
        tag
        for tag in raw_tags
        if isinstance(tag, str) and (tag.startswith("risk:") or not any(tag.startswith(prefix) for prefix in managed_prefixes))
    ]
    primary_domain_id = str(payload.get("primary_domain_id", "cross_domain_shared"))
    tool_form_id = str(payload.get("tool_form_id", "skill"))
    runtime_platform_ids = [str(item) for item in (payload.get("runtime_platform_ids") or [])]
    lifecycle_stage_ids = [str(item) for item in (payload.get("lifecycle_stage_ids") or [])]
    input_types = [str(item) for item in (payload.get("input_types") or [])]
    output_types = [str(item) for item in (payload.get("output_types") or [])]

    canonical_tags = [
        f"domain:{primary_domain_id}",
        f"form:{tool_form_id}",
        *[f"runtime:{item}" for item in runtime_platform_ids],
        *[f"lifecycle:{item}" for item in lifecycle_stage_ids],
        *[f"input:{item}" for item in input_types],
        *[f"output:{item}" for item in output_types],
    ]
    return sorted(dict.fromkeys([*canonical_tags, *preserved_tags]))


class ToolVerification(BaseModel):
    status: ToolVerificationStatus = "unverified"
    last_verified_at: str | None = None
    last_verified_result: str = ""
    sample_case_ids: list[str] = Field(default_factory=list)


class ToolDefinitionWrite(BaseModel):
    name: str
    slug: str
    status: ToolStatus = "draft"
    summary: str = ""
    problem_statement: str = ""
    primary_domain_id: str
    tool_form_id: str
    runtime_platform_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    supported_sources: list[SupportedSource] = Field(default_factory=list)
    usage_notes: str = ""
    keywords: list[str] = Field(default_factory=list)
    verification: ToolVerification = Field(default_factory=ToolVerification)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "primary_domain_id" not in payload:
            payload["primary_domain_id"] = _infer_domain_from_legacy_payload(payload)
        if "tool_form_id" not in payload:
            payload["tool_form_id"] = _infer_tool_form(payload)
        if "runtime_platform_ids" not in payload or not payload.get("runtime_platform_ids"):
            payload["runtime_platform_ids"] = ["agent_runtime"]
        payload["lifecycle_stage_ids"] = _normalize_lifecycle_stage_ids(payload)
        payload["tags"] = _build_canonical_tags(payload)
        return payload


class ToolDefinition(ToolDefinitionWrite):
    tool_id: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolDemandSource(BaseModel):
    phase: str
    producer: str
    business_case: str
    scenario_id: str
    scenario_name: str


class ComponentSpec(BaseModel):
    component_name: str
    component_code: str
    problem_statement: str = ""
    required_input_types: list[str] = Field(default_factory=list)
    expected_output_types: list[str] = Field(default_factory=list)
    preferred_tool_forms: list[str] = Field(default_factory=list)
    preferred_runtime_platforms: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    acceptance_notes: str = ""


class ToolDemandNode(BaseModel):
    node_id: str
    node_type: ToolDemandNodeType
    node_name: str
    node_code: str
    description: str = ""
    business_domain_id: str = ""
    children: list["ToolDemandNode"] = Field(default_factory=list)
    component_spec: ComponentSpec | None = None

    @model_validator(mode="after")
    def validate_tree_shape(self) -> "ToolDemandNode":
        if self.node_type == "component":
            if self.children:
                raise ValueError("Component node must not contain children")
            if self.component_spec is None:
                raise ValueError("Component node must include component_spec")
        else:
            if not self.children:
                raise ValueError("Non-component node must contain children")
            if self.component_spec is not None:
                raise ValueError("Non-component node must not include component_spec")
        return self


class ToolDemandSheetCreateRequest(BaseModel):
    sheet_name: str
    source: ToolDemandSource
    requested_by: str
    root_node: ToolDemandNode
    notes: str = ""


class ToolFetchManifest(BaseModel):
    tool_id: str
    tool_name: str
    fetch_type: Literal["tool_definition"] = "tool_definition"
    fetch_path: str
    fetch_method: Literal["GET"] = "GET"
    note: str = ""


class ToolSupplyResult(BaseModel):
    result_type: ToolSupplyResultType
    summary: str = ""
    tool_id: str | None = None
    tool_name: str | None = None
    fetch_manifest: ToolFetchManifest | None = None
    progress_query_path: str | None = None
    estimated_ready_at: str | None = None
    estimated_ready_in_hours: int | None = None


class ToolDemandItem(BaseModel):
    item_id: str
    sheet_id: str
    source_node_id: str
    ancestry: list[str] = Field(default_factory=list)
    business_domain_id: str = ""
    component_name: str
    component_code: str
    problem_statement: str = ""
    required_input_types: list[str] = Field(default_factory=list)
    expected_output_types: list[str] = Field(default_factory=list)
    preferred_tool_forms: list[str] = Field(default_factory=list)
    preferred_runtime_platforms: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    acceptance_notes: str = ""
    status: ToolDemandItemStatus
    analysis_result: str = ""
    check_result: str = ""
    match_result: str = ""
    supply_result: ToolSupplyResult
    submitted_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolManufacturePlan(BaseModel):
    plan_id: str
    item_id: str
    status: ToolManufacturePlanStatus
    estimated_ready_at: str
    estimated_ready_in_hours: int
    planned_tool_name: str
    planned_tool_form_id: str
    planned_runtime_platform_ids: list[str] = Field(default_factory=list)
    manufactured_tool_id: str | None = None
    query_count: int = 0
    progress_percent: int = 15
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolDemandSheet(BaseModel):
    sheet_id: str
    sheet_name: str
    status: ToolDemandSheetStatus
    source: ToolDemandSource
    requested_by: str
    business_case: str
    root_node: ToolDemandNode
    item_ids: list[str] = Field(default_factory=list)
    item_count: int = 0
    matched_existing_count: int = 0
    manufacturing_count: int = 0
    ready_for_fetch_count: int = 0
    failed_count: int = 0
    submitted_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolDemandSheetDetail(ToolDemandSheet):
    items: list[ToolDemandItem] = Field(default_factory=list)


class ToolDemandSheetEnvelope(BaseModel):
    items: list[ToolDemandSheet]


class ItemProgressView(BaseModel):
    item_id: str
    sheet_id: str
    status: ToolDemandItemStatus
    result_type: ToolSupplyResultType
    progress_percent: int = 0
    summary: str = ""
    estimated_ready_at: str | None = None
    estimated_ready_in_hours: int | None = None
    progress_query_path: str | None = None
    fetch_manifest: ToolFetchManifest | None = None


class ToolListEnvelope(BaseModel):
    items: list[ToolDefinition]


class CatalogItem(BaseModel):
    id: str
    label: str
    description: str = ""


class ToolHubCatalogs(BaseModel):
    domains: list[CatalogItem]
    lifecycle_stages: list[CatalogItem]
    tool_forms: list[CatalogItem]
    runtime_platforms: list[CatalogItem]
    input_types: list[CatalogItem]
    output_types: list[CatalogItem]
    supported_sources: list[CatalogItem]
    verification_statuses: list[CatalogItem]
    tag_namespaces: list[CatalogItem]


class OverviewMetrics(BaseModel):
    tool_count: int = 0
    verified_tool_count: int = 0
    active_tool_count: int = 0
    draft_tool_count: int = 0
    archived_tool_count: int = 0
    match_run_count: int = 0
    evolution_run_count: int = 0
    active_chain_count: int = 0
    overlap_candidate_count: int = 0
    pending_suggestion_count: int = 0
    recent_success_rate: float = 0


class CoverageMatrixCell(BaseModel):
    column_id: str
    value: int = 0


class CoverageMatrixRow(BaseModel):
    row_id: str
    row_label: str
    cells: list[CoverageMatrixCell]


class CoverageMatrix(BaseModel):
    title: str
    x_axis_label: str
    y_axis_label: str
    columns: list[CatalogItem]
    rows: list[CoverageMatrixRow]


class RiskSummaryItem(BaseModel):
    kind: RiskKind
    title: str
    description: str
    severity: RiskSeverity = "info"


class RecentRunSummary(BaseModel):
    run_id: str
    run_type: Literal["match", "evolution"]
    title: str
    status: str
    created_at: str
    summary: str


class ToolHubRunMonitor(BaseModel):
    active_match_run_count: int = 0
    active_evolution_run_count: int = 0
    latest_match_run: RecentRunSummary | None = None
    latest_evolution_run: RecentRunSummary | None = None
    failing_run_count: int = 0
    stale_run_count: int = 0


class PendingSuggestionItem(BaseModel):
    finding_id: str
    source_run_id: str
    kind: RiskKind
    title: str
    description: str
    severity: RiskSeverity = "warning"
    tool_ids: list[str] = Field(default_factory=list)


class ToolMatchKnowledgeContext(BaseModel):
    archive_id: str | None = None
    entity_ids: list[str] = Field(default_factory=list)
    process_ids: list[str] = Field(default_factory=list)
    snapshot_version: str | None = None


class ToolMatchRequest(BaseModel):
    scenario_text: str = ""
    target_domain_ids: list[str] = Field(default_factory=list)
    lifecycle_stage_ids: list[str] = Field(default_factory=list)
    required_input_types: list[str] = Field(default_factory=list)
    expected_output_types: list[str] = Field(default_factory=list)
    preferred_tool_forms: list[str] = Field(default_factory=list)
    preferred_runtime_platforms: list[str] = Field(default_factory=list)
    preferred_tags: list[str] = Field(default_factory=list)
    knowledge_context: ToolMatchKnowledgeContext = Field(default_factory=ToolMatchKnowledgeContext)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_request(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "lifecycle_stage_ids" not in payload:
            legacy_stage = payload.get("target_stage")
            if isinstance(legacy_stage, str) and legacy_stage:
                payload["lifecycle_stage_ids"] = [LEGACY_STAGE_TO_LIFECYCLE.get(legacy_stage, legacy_stage)]
            else:
                payload["lifecycle_stage_ids"] = []
        if "target_domain_ids" not in payload:
            domain_ids: list[str] = []
            for tag in payload.get("preferred_tags", []) or []:
                if not isinstance(tag, str):
                    continue
                if tag.startswith("domain:"):
                    domain_ids.append(tag.split(":", 1)[1])
                    continue
                if tag.startswith("capability:"):
                    legacy_capability = tag.split(":", 1)[1]
                    mapped = LEGACY_CAPABILITY_TO_DOMAIN.get(legacy_capability)
                    if mapped:
                        domain_ids.append(mapped)
            payload["target_domain_ids"] = sorted(dict.fromkeys(domain_ids))
        payload.setdefault("preferred_tool_forms", [])
        payload.setdefault("preferred_runtime_platforms", [])
        payload.setdefault("preferred_tags", [])
        return payload


class ToolMatchCandidate(BaseModel):
    tool_id: str
    name: str
    match_score: int
    matched_dimensions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    verification_status: ToolVerificationStatus = "unverified"


class ToolMatchRun(BaseModel):
    run_id: str
    status: Literal["completed"] = "completed"
    created_at: str = Field(default_factory=now_iso)
    request: ToolMatchRequest
    candidates: list[ToolMatchCandidate]
    context_summary: str = ""


class ToolMatchRunEnvelope(BaseModel):
    items: list[ToolMatchRun]


class EvolutionFinding(BaseModel):
    finding_id: str
    kind: RiskKind
    title: str
    description: str
    severity: RiskSeverity = "warning"
    tool_ids: list[str] = Field(default_factory=list)


class EvolutionRunSummary(BaseModel):
    tool_count: int = 0
    finding_count: int = 0
    missing_description_count: int = 0
    taxonomy_issue_count: int = 0
    overlap_risk_count: int = 0
    coverage_gap_count: int = 0


class EvolutionRun(BaseModel):
    run_id: str
    status: Literal["completed"] = "completed"
    created_at: str = Field(default_factory=now_iso)
    summary: EvolutionRunSummary = Field(default_factory=EvolutionRunSummary)
    findings: list[EvolutionFinding] = Field(default_factory=list)


class EvolutionRunEnvelope(BaseModel):
    items: list[EvolutionRun]


class ToolHubSnapshotMeta(BaseModel):
    snapshot_id: str
    generated_at: str = Field(default_factory=now_iso)
    state_version: str = "p4-tool-hub-state-v2"
    source_contract_version: str = "p4-tool-hub-read-v2"


class ToolHubRawState(BaseModel):
    catalogs: ToolHubCatalogs
    tools: list[ToolDefinition] = Field(default_factory=list)
    demand_sheets: list[ToolDemandSheet] = Field(default_factory=list)
    match_runs: list[ToolMatchRun] = Field(default_factory=list)
    evolution_runs: list[EvolutionRun] = Field(default_factory=list)


class ToolHubDerivedState(BaseModel):
    metrics: OverviewMetrics
    run_monitor: ToolHubRunMonitor
    risk_summary: list[RiskSummaryItem] = Field(default_factory=list)
    coverage_matrix: CoverageMatrix
    pending_suggestions: list[PendingSuggestionItem] = Field(default_factory=list)


class ToolHubStateSnapshot(BaseModel):
    meta: ToolHubSnapshotMeta
    raw: ToolHubRawState
    derived: ToolHubDerivedState


class ToolHubOverview(BaseModel):
    metrics: OverviewMetrics
    run_monitor: ToolHubRunMonitor
    coverage_matrix: CoverageMatrix
    risk_summary: list[RiskSummaryItem]
    pending_suggestions: list[PendingSuggestionItem] = Field(default_factory=list)
    recent_demand_sheets: list[ToolDemandSheet] = Field(default_factory=list)
    recent_match_runs: list[RecentRunSummary]
    recent_evolution_runs: list[RecentRunSummary]
    catalogs: ToolHubCatalogs


class ToolHubOverviewReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: ToolHubOverview


class ToolListReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: ToolListEnvelope


class EvolutionRunReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: EvolutionRunEnvelope
