from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


ToolStatus = Literal["draft", "active", "archived"]
ToolVerificationStatus = Literal["unverified", "verified", "warning", "failed"]
SupportedSource = Literal["p1_readonly_api", "frozen_snapshot", "manual_input"]
RiskKind = Literal["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"]
RiskSeverity = Literal["info", "warning", "critical"]


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
    primary_category_id: str
    tags: list[str] = Field(default_factory=list)
    applicable_stages: list[str] = Field(default_factory=list)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    supported_sources: list[SupportedSource] = Field(default_factory=list)
    usage_notes: str = ""
    keywords: list[str] = Field(default_factory=list)
    verification: ToolVerification = Field(default_factory=ToolVerification)


class ToolDefinition(ToolDefinitionWrite):
    tool_id: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolListEnvelope(BaseModel):
    items: list[ToolDefinition]


class CatalogItem(BaseModel):
    id: str
    label: str
    description: str = ""


class ToolHubCatalogs(BaseModel):
    categories: list[CatalogItem]
    stages: list[CatalogItem]
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
    stage_id: str
    value: int = 0


class CoverageMatrixRow(BaseModel):
    category_id: str
    category_label: str
    cells: list[CoverageMatrixCell]


class CoverageMatrix(BaseModel):
    stages: list[CatalogItem]
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
    target_stage: str = ""
    required_input_types: list[str] = Field(default_factory=list)
    expected_output_types: list[str] = Field(default_factory=list)
    preferred_tags: list[str] = Field(default_factory=list)
    knowledge_context: ToolMatchKnowledgeContext = Field(default_factory=ToolMatchKnowledgeContext)


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
    state_version: str = "p4-tool-hub-state-v1"
    source_contract_version: str = "p4-tool-hub-read-v1"


class ToolHubRawState(BaseModel):
    catalogs: ToolHubCatalogs
    tools: list[ToolDefinition] = Field(default_factory=list)
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
