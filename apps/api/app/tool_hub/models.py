from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


ToolStatus = Literal["draft", "active", "archived"]
ToolVerificationStatus = Literal["unverified", "verified", "warning", "failed"]
SupportedSource = Literal["p1_readonly_api", "frozen_snapshot", "manual_input", "tool_hub_snapshot"]
ToolGranularity = Literal["atomic", "composite", "page_level"]
ToolPackagingType = Literal["source_package", "build_artifact", "http_endpoint", "descriptor_only"]
ToolIntegrationMode = Literal[
    "import_component",
    "import_module",
    "include_router",
    "call_http_api",
    "mount_page",
    "manual",
]
ToolDependencyPolicy = Literal["peer", "bundled", "external"]
ToolBuildRequestType = Literal["frontend_component"]
ToolBuildRecipeStatus = Literal["pending", "generated", "failed"]
ToolBuildRunStatus = Literal["queued", "running", "completed", "failed"]
ToolValidationOverallStatus = Literal["pending", "passed", "failed"]
RiskKind = Literal["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"]
RiskSeverity = Literal["info", "warning", "critical"]
EvolutionRunStatus = Literal["queued", "running", "completed", "failed"]
EvolutionTriggerType = Literal["manual", "scheduled"]
EvolutionFindingDecisionStatus = Literal["pending", "accepted_to_task", "ignored"]
EvolutionTaskType = Literal["auto_apply", "manual_followup"]
EvolutionTaskStatus = Literal["queued", "running", "completed", "failed", "rolled_back"]
EvolutionTaskPriority = Literal["low", "medium", "high"]
ToolDemandSheetLifecycleStatus = Literal["submitted", "accepted", "rejected", "withdrawn", "closed"]
ToolDemandSheetReviewStatus = Literal["pending_review", "reviewing", "reviewed"]
ToolDemandSheetDeliveryStatus = Literal["not_delivered", "delivering", "delivered"]
ToolDemandSheetProcessingStatus = Literal["not_started", "processing", "partially_ready", "ready", "failed"]
ToolDemandNodeType = Literal["system", "subsystem", "sub_subsystem", "module", "component"]
ToolDemandLifecycleEventType = Literal["submitted", "accepted", "rejected", "withdrawn", "closed"]
ToolDemandItemRecommendationType = Literal["existing_tool", "manufacture_candidate", "insufficient_info"]
ToolDemandItemReviewStatus = Literal["pending_review", "approved_delivery", "approved_manufacture", "rejected"]
ToolDemandReviewDecision = Literal["approve_delivery", "approve_manufacture", "reject"]
ToolDemandItemProcessingStatus = Literal[
    "accepted",
    "analyzing",
    "checking",
    "matched_existing",
    "manufacturing_pending",
    "manufacturing_in_progress",
    "ready_for_fetch",
    "failed",
]
ToolSupplyResultType = Literal["existing_tool", "pending_manufacture", "manufactured_tool"]
ToolManufacturePlanStatus = Literal["manufacturing_pending", "manufacturing_in_progress", "ready_for_fetch", "failed"]
ToolManufactureSimulationProfile = Literal["fast", "normal", "slow"]
ToolDemandSheetStatus = ToolDemandSheetProcessingStatus
ToolDemandItemStatus = ToolDemandItemProcessingStatus

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

LEGACY_SHEET_STATUS_TO_STATE: dict[str, tuple[ToolDemandSheetLifecycleStatus, ToolDemandSheetProcessingStatus]] = {
    "accepted": ("accepted", "not_started"),
    "processing": ("accepted", "processing"),
    "partially_ready": ("accepted", "partially_ready"),
    "ready": ("accepted", "ready"),
    "failed": ("accepted", "failed"),
    "submitted": ("submitted", "not_started"),
    "rejected": ("rejected", "not_started"),
    "withdrawn": ("withdrawn", "not_started"),
    "closed": ("closed", "ready"),
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


def _infer_tool_granularity(payload: dict[str, Any]) -> ToolGranularity:
    raw = payload.get("tool_granularity")
    if raw in {"atomic", "composite", "page_level"}:
        return raw
    return "atomic"


def _infer_packaging_type(payload: dict[str, Any]) -> ToolPackagingType:
    raw = payload.get("packaging_type")
    if raw in {"source_package", "build_artifact", "http_endpoint", "descriptor_only"}:
        return raw

    tool_form_id = str(payload.get("tool_form_id", "skill"))
    if tool_form_id == "frontend_component":
        return "source_package"
    if tool_form_id == "service_endpoint":
        return "http_endpoint"
    if tool_form_id in {"package_bundle", "static_library", "dynamic_library"}:
        return "build_artifact"
    return "descriptor_only"


def _infer_integration_mode(payload: dict[str, Any]) -> ToolIntegrationMode:
    raw = payload.get("integration_mode")
    if raw in {"import_component", "import_module", "include_router", "call_http_api", "mount_page", "manual"}:
        return raw

    tool_form_id = str(payload.get("tool_form_id", "skill"))
    if tool_form_id == "frontend_component":
        return "import_component"
    if tool_form_id == "service_endpoint":
        return "call_http_api"
    if tool_form_id in {"package_bundle", "static_library", "dynamic_library"}:
        return "import_module"
    if tool_form_id == "template":
        return "mount_page"
    return "manual"


def _infer_dependency_policy(payload: dict[str, Any]) -> ToolDependencyPolicy:
    raw = payload.get("dependency_policy")
    if raw in {"peer", "bundled", "external"}:
        return raw

    tool_form_id = str(payload.get("tool_form_id", "skill"))
    if tool_form_id == "frontend_component":
        return "peer"
    if tool_form_id == "service_endpoint":
        return "external"
    if tool_form_id in {"package_bundle", "static_library", "dynamic_library"}:
        return "bundled"
    return "external"


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


def _normalize_legacy_sheet_status(
    status: Any,
) -> tuple[ToolDemandSheetLifecycleStatus, ToolDemandSheetProcessingStatus]:
    if isinstance(status, str) and status in LEGACY_SHEET_STATUS_TO_STATE:
        return LEGACY_SHEET_STATUS_TO_STATE[status]
    return ("submitted", "not_started")


def _normalize_legacy_item_status(status: Any) -> ToolDemandItemProcessingStatus:
    if isinstance(status, str):
        if status in {
            "accepted",
            "analyzing",
            "checking",
            "matched_existing",
            "manufacturing_pending",
            "manufacturing_in_progress",
            "ready_for_fetch",
            "failed",
        }:
            return status
    return "accepted"


def _derive_legacy_item_review_status(payload: dict[str, Any]) -> ToolDemandItemReviewStatus:
    review_status = payload.get("review_status")
    if review_status in {"pending_review", "approved_delivery", "approved_manufacture", "rejected"}:
        return review_status

    supply_result = payload.get("supply_result")
    result_type = supply_result.get("result_type") if isinstance(supply_result, dict) else None
    if result_type == "existing_tool":
        return "approved_delivery"
    if result_type in {"pending_manufacture", "manufactured_tool"}:
        return "approved_manufacture"
    return "pending_review"


def _derive_legacy_item_recommendation_type(payload: dict[str, Any]) -> ToolDemandItemRecommendationType:
    recommendation_type = payload.get("recommendation_type")
    if recommendation_type in {"existing_tool", "manufacture_candidate", "insufficient_info"}:
        return recommendation_type

    supply_result = payload.get("supply_result")
    result_type = supply_result.get("result_type") if isinstance(supply_result, dict) else None
    processing_status = payload.get("processing_status") or payload.get("status")
    if result_type == "existing_tool" or processing_status == "matched_existing":
        return "existing_tool"
    if result_type in {"pending_manufacture", "manufactured_tool"} or processing_status in {
        "manufacturing_pending",
        "manufacturing_in_progress",
        "ready_for_fetch",
    }:
        return "manufacture_candidate"
    if payload.get("required_input_types") or payload.get("expected_output_types"):
        return "manufacture_candidate"
    return "insufficient_info"


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
    tool_granularity: ToolGranularity = "atomic"
    packaging_type: ToolPackagingType = "descriptor_only"
    integration_mode: ToolIntegrationMode = "manual"
    dependency_policy: ToolDependencyPolicy = "external"
    runtime_dependencies: list[str] = Field(default_factory=list)
    host_constraints: dict[str, str | list[str]] = Field(default_factory=dict)
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
        payload["tool_granularity"] = _infer_tool_granularity(payload)
        payload["packaging_type"] = _infer_packaging_type(payload)
        payload["integration_mode"] = _infer_integration_mode(payload)
        payload["dependency_policy"] = _infer_dependency_policy(payload)
        payload.setdefault("runtime_dependencies", [])
        payload.setdefault("host_constraints", {})
        if "runtime_platform_ids" not in payload or not payload.get("runtime_platform_ids"):
            payload["runtime_platform_ids"] = ["agent_runtime"]
        payload["lifecycle_stage_ids"] = _normalize_lifecycle_stage_ids(payload)
        payload["tags"] = _build_canonical_tags(payload)
        return payload


class ToolDefinition(ToolDefinitionWrite):
    tool_id: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolBuildRequest(BaseModel):
    build_request_id: str
    tool_id: str
    request_type: ToolBuildRequestType = "frontend_component"
    requested_by: str
    recipe_status: ToolBuildRecipeStatus = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    recipe_id: str | None = None
    last_error: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolBuildRun(BaseModel):
    build_run_id: str
    build_request_id: str
    tool_id: str
    status: ToolBuildRunStatus = "queued"
    queue_name: str = "p4-build"
    payload: dict[str, Any] = Field(default_factory=dict)
    artifact_version_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolArtifactVersion(BaseModel):
    artifact_version_id: str
    tool_id: str
    build_run_id: str
    version_label: str = "v1"
    artifact_root: str
    manifest_path: str
    packaging_type: ToolPackagingType = "descriptor_only"
    integration_mode: ToolIntegrationMode = "manual"
    dependency_policy: ToolDependencyPolicy = "external"
    runtime_dependencies: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolValidationReport(BaseModel):
    validation_report_id: str
    build_run_id: str
    overall_status: ToolValidationOverallStatus = "pending"
    checks: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ToolRecipe(BaseModel):
    recipe_id: str
    component_name: str
    package_name: str
    props_schema: dict[str, dict[str, Any]] = Field(default_factory=dict)
    peer_dependencies: dict[str, str] = Field(default_factory=dict)
    host_constraints: dict[str, str | list[str]] = Field(default_factory=dict)


class GeneratedArtifactBundle(BaseModel):
    artifact_root: str
    manifest_path: str
    import_specifier: str
    example_host_path: str
    files: list[str] = Field(default_factory=list)


class ToolDeliveryManifest(BaseModel):
    tool_id: str
    tool_name: str
    tool_form_id: str = "frontend_component"
    packaging_type: ToolPackagingType = "source_package"
    integration_mode: ToolIntegrationMode = "import_component"
    dependency_policy: ToolDependencyPolicy = "peer"
    runtime_dependencies: list[str] = Field(default_factory=list)
    import_specifier: str
    example_host_path: str
    artifact_version_id: str | None = None
    manifest_path: str
    contract_version: str = "p4.delivery.v1"
    updated_at: str = Field(default_factory=now_iso)


class FrontendComponentBuildRequest(BaseModel):
    requested_by: str
    component_name: str
    scenario_id: str
    tool_definition: ToolDefinitionWrite


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
    tool_version: str = "v1"
    tool_form_id: str = "skill"
    packaging_type: ToolPackagingType = "descriptor_only"
    integration_mode: ToolIntegrationMode = "manual"
    dependency_policy: ToolDependencyPolicy = "external"
    runtime_dependencies: list[str] = Field(default_factory=list)
    runtime_platform_ids: list[str] = Field(default_factory=list)
    fetch_mode: Literal["descriptor"] = "descriptor"
    entrypoint_type: Literal["http", "descriptor", "artifact_ref", "manual"] = "descriptor"
    entrypoint_locator: str
    contract_version: str = "p4.fetch.v2"
    updated_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "entrypoint_locator" not in payload and "fetch_path" in payload:
            payload["entrypoint_locator"] = payload["fetch_path"]
        payload.setdefault("tool_version", "v1")
        payload.setdefault("tool_form_id", "skill")
        payload["packaging_type"] = _infer_packaging_type(payload)
        payload["integration_mode"] = _infer_integration_mode(payload)
        payload["dependency_policy"] = _infer_dependency_policy(payload)
        payload.setdefault("runtime_dependencies", [])
        payload.setdefault("runtime_platform_ids", ["agent_runtime"])
        payload.setdefault("fetch_mode", "descriptor")
        locator = str(payload.get("entrypoint_locator", ""))
        payload.setdefault("entrypoint_type", "http" if locator.startswith("/") else "descriptor")
        payload.setdefault("contract_version", "p4.fetch.v2")
        payload.setdefault("updated_at", now_iso())
        return payload


class ToolSupplyResult(BaseModel):
    result_type: ToolSupplyResultType
    item_id: str
    tool_ref: str | None = None
    fetch_interface: ToolFetchManifest | None = None
    progress_query_interface: str | None = None
    estimated_ready_at: str | None = None
    suggested_poll_after_seconds: int | None = None
    available_at: str | None = None
    last_message: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "tool_ref" not in payload and payload.get("tool_id"):
            payload["tool_ref"] = payload["tool_id"]
        if "fetch_interface" not in payload and payload.get("fetch_manifest") is not None:
            payload["fetch_interface"] = payload["fetch_manifest"]
        if "progress_query_interface" not in payload and payload.get("progress_query_path"):
            payload["progress_query_interface"] = payload["progress_query_path"]
        if "last_message" not in payload and payload.get("summary"):
            payload["last_message"] = payload["summary"]
        payload.setdefault("item_id", "")
        payload.setdefault("suggested_poll_after_seconds", None)
        payload.setdefault("available_at", None)
        return payload


class ToolDemandLifecycleEvent(BaseModel):
    event_id: str
    event_type: ToolDemandLifecycleEventType
    actor_phase: str
    actor_id: str
    from_status: ToolDemandSheetLifecycleStatus | None = None
    to_status: ToolDemandSheetLifecycleStatus
    reason_code: str = ""
    reason_message: str = ""
    occurred_at: str = Field(default_factory=now_iso)


class ToolDemandSheetActionRequest(BaseModel):
    actor_id: str
    reason_code: str
    reason_message: str
    actor_phase: str | None = None


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
    recommendation_type: ToolDemandItemRecommendationType
    recommendation_summary: str = ""
    recommended_tool_id: str | None = None
    recommended_tool_name: str | None = None
    review_status: ToolDemandItemReviewStatus
    importance_score: int | None = None
    urgency_score: int | None = None
    rationality_verdict: str = ""
    review_comment: str = ""
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    processing_status: ToolDemandItemProcessingStatus
    analysis_result: str = ""
    check_result: str = ""
    match_result: str = ""
    supply_result: ToolSupplyResult | None = None
    submitted_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "processing_status" not in payload:
            payload["processing_status"] = _normalize_legacy_item_status(payload.get("status"))
        payload.setdefault("review_status", _derive_legacy_item_review_status(payload))
        payload.setdefault("recommendation_type", _derive_legacy_item_recommendation_type(payload))
        payload.setdefault(
            "recommendation_summary",
            str(payload.get("match_result") or payload.get("analysis_result") or ""),
        )
        supply_result = payload.get("supply_result")
        if isinstance(supply_result, dict):
            payload.setdefault("recommended_tool_id", supply_result.get("tool_id") or supply_result.get("tool_ref"))
            payload.setdefault("recommended_tool_name", supply_result.get("tool_name"))
        payload.setdefault("importance_score", None)
        payload.setdefault("urgency_score", None)
        payload.setdefault("rationality_verdict", "")
        payload.setdefault("review_comment", "")
        payload.setdefault("reviewed_by", None)
        payload.setdefault("reviewed_at", None)
        return payload


class ToolManufacturePlan(BaseModel):
    plan_id: str
    item_id: str
    status: ToolManufacturePlanStatus
    simulation_profile: ToolManufactureSimulationProfile = "normal"
    target_duration_seconds: int = 300
    estimated_ready_at: str
    estimated_ready_in_hours: int | None = None
    suggested_poll_after_seconds: int = 60
    planned_tool_name: str
    planned_tool_form_id: str
    planned_runtime_platform_ids: list[str] = Field(default_factory=list)
    manufactured_tool_id: str | None = None
    query_count: int = 0
    progress_percent: int = 15
    started_at: str | None = None
    completed_at: str | None = None
    last_progress_message: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        payload.setdefault("simulation_profile", "normal")
        payload.setdefault("target_duration_seconds", 300)
        payload.setdefault("suggested_poll_after_seconds", 60)
        payload.setdefault("started_at", None)
        payload.setdefault("completed_at", None)
        payload.setdefault("last_progress_message", "")
        return payload


class ToolDemandSheet(BaseModel):
    sheet_id: str
    sheet_name: str
    lifecycle_status: ToolDemandSheetLifecycleStatus
    review_status: ToolDemandSheetReviewStatus
    delivery_status: ToolDemandSheetDeliveryStatus
    processing_status: ToolDemandSheetProcessingStatus
    source: ToolDemandSource
    requested_by: str
    business_case: str
    root_node: ToolDemandNode
    item_ids: list[str] = Field(default_factory=list)
    item_count: int = 0
    pending_review_count: int = 0
    approved_delivery_count: int = 0
    approved_manufacture_count: int = 0
    rejected_item_count: int = 0
    matched_existing_count: int = 0
    manufacturing_count: int = 0
    ready_for_fetch_count: int = 0
    failed_count: int = 0
    lifecycle_events: list[ToolDemandLifecycleEvent] = Field(default_factory=list)
    last_actor_phase: str | None = None
    last_actor_id: str | None = None
    terminal_reason_code: str | None = None
    terminal_reason_message: str | None = None
    submitted_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        lifecycle_status, processing_status = _normalize_legacy_sheet_status(payload.get("status"))
        payload.setdefault("lifecycle_status", lifecycle_status)
        payload.setdefault("review_status", "pending_review")
        payload.setdefault("delivery_status", "not_delivered")
        payload.setdefault("processing_status", processing_status)
        payload.setdefault("pending_review_count", 0)
        payload.setdefault("approved_delivery_count", 0)
        payload.setdefault("approved_manufacture_count", 0)
        payload.setdefault("rejected_item_count", 0)
        payload.setdefault("lifecycle_events", [])
        payload.setdefault("last_actor_phase", None)
        payload.setdefault("last_actor_id", None)
        payload.setdefault("terminal_reason_code", None)
        payload.setdefault("terminal_reason_message", None)
        return payload


class ToolDemandSheetDetail(ToolDemandSheet):
    items: list[ToolDemandItem] = Field(default_factory=list)


class ToolDemandSheetEnvelope(BaseModel):
    items: list[ToolDemandSheet]


class ToolManufacturePlanView(BaseModel):
    plan_id: str
    item_id: str
    sheet_id: str
    component_name: str
    planned_tool_name: str
    status: ToolManufacturePlanStatus
    progress_percent: int = 0
    simulation_profile: ToolManufactureSimulationProfile = "normal"
    target_duration_seconds: int = 300
    estimated_ready_at: str
    started_at: str | None = None
    completed_at: str | None = None
    last_progress_message: str = ""
    updated_at: str = Field(default_factory=now_iso)


class ToolManufacturePlanEnvelope(BaseModel):
    items: list[ToolManufacturePlanView]


class ToolRegistryDeleteResult(BaseModel):
    removed_tool_id: str
    remaining_tool_count: int = 0


class ToolRegistryTestingClearResult(BaseModel):
    cleared_tool_count: int = 0
    cleared_match_run_count: int = 0
    cleared_evolution_run_count: int = 0


class ToolDemandTestingClearResult(BaseModel):
    cleared_sheet_count: int = 0
    cleared_item_count: int = 0
    cleared_manufacture_plan_count: int = 0


class ItemProgressView(BaseModel):
    item_id: str
    sheet_id: str
    status: ToolDemandItemProcessingStatus
    sheet_lifecycle_status: ToolDemandSheetLifecycleStatus
    sheet_review_status: ToolDemandSheetReviewStatus = "pending_review"
    sheet_delivery_status: ToolDemandSheetDeliveryStatus = "not_delivered"
    review_status: ToolDemandItemReviewStatus = "pending_review"
    result_type: ToolSupplyResultType | None = None
    progress_percent: int = 0
    estimated_ready_at: str | None = None
    suggested_poll_after_seconds: int | None = None
    fetch_interface: ToolFetchManifest | None = None
    last_message: str = ""
    updated_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "status" not in payload:
            payload["status"] = _normalize_legacy_item_status(payload.get("processing_status") or payload.get("status"))
        if "fetch_interface" not in payload and payload.get("fetch_manifest") is not None:
            payload["fetch_interface"] = payload["fetch_manifest"]
        if "last_message" not in payload and payload.get("summary"):
            payload["last_message"] = payload["summary"]
        payload.setdefault("sheet_lifecycle_status", "accepted")
        payload.setdefault("sheet_review_status", "pending_review")
        payload.setdefault("sheet_delivery_status", "not_delivered")
        payload.setdefault("review_status", "pending_review")
        payload.setdefault("updated_at", now_iso())
        return payload


class ToolDemandReviewDecisionRequest(BaseModel):
    decision: ToolDemandReviewDecision
    importance_score: int | None = None
    urgency_score: int | None = None
    rationality_verdict: str = ""
    review_comment: str = ""
    reviewed_by: str


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
    run_id: str = ""
    title: str
    description: str
    severity: RiskSeverity = "warning"
    tool_ids: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    decision_status: EvolutionFindingDecisionStatus = "pending"
    decision_by: str | None = None
    decision_at: str | None = None
    decision_note: str = ""
    linked_task_id: str | None = None
    updated_at: str = Field(default_factory=now_iso)


class EvolutionRunSummary(BaseModel):
    tool_count: int = 0
    finding_count: int = 0
    missing_description_count: int = 0
    taxonomy_issue_count: int = 0
    overlap_risk_count: int = 0
    coverage_gap_count: int = 0
    accepted_count: int = 0
    ignored_count: int = 0
    generated_task_count: int = 0


class EvolutionRun(BaseModel):
    run_id: str
    status: EvolutionRunStatus = "completed"
    trigger_type: EvolutionTriggerType = "manual"
    triggered_by: str = "p4-system"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    snapshot_id: str | None = None
    error_message: str = ""
    summary: EvolutionRunSummary = Field(default_factory=EvolutionRunSummary)
    findings: list[EvolutionFinding] = Field(default_factory=list)


class EvolutionRunEnvelope(BaseModel):
    items: list[EvolutionRun]


class EvolutionInspectionConfig(BaseModel):
    config_id: str = "default"
    enabled: bool = True
    schedule_mode: Literal["manual_and_scheduled"] = "manual_and_scheduled"
    interval_minutes: float = 60
    include_draft_tools: bool = True
    focus_rule_ids: list[RiskKind] = Field(
        default_factory=lambda: ["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"]
    )
    overlap_threshold: int = 3
    max_run_history: int = 50
    auto_apply_rule_ids: list[RiskKind] = Field(default_factory=lambda: ["missing_description", "taxonomy_issue"])
    updated_by: str = "p4-system"
    updated_at: str = Field(default_factory=now_iso)


class EvolutionConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    interval_minutes: float | None = None
    include_draft_tools: bool | None = None
    focus_rule_ids: list[RiskKind] | None = None
    overlap_threshold: int | None = None
    max_run_history: int | None = None
    auto_apply_rule_ids: list[RiskKind] | None = None


class EvolutionRunCreateRequest(BaseModel):
    actor_id: str


class EvolutionFindingDecisionRequest(BaseModel):
    actor_id: str
    decision: Literal["accept", "ignore"]
    note: str = ""


class EvolutionTask(BaseModel):
    task_id: str
    source_run_id: str
    source_finding_id: str
    task_type: EvolutionTaskType
    task_status: EvolutionTaskStatus = "queued"
    priority: EvolutionTaskPriority = "medium"
    planned_action: str
    target_tool_ids: list[str] = Field(default_factory=list)
    result_summary: str = ""
    change_count: int = 0
    rollback_available: bool = False
    created_by: str
    created_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str = Field(default_factory=now_iso)


class EvolutionTaskEnvelope(BaseModel):
    items: list[EvolutionTask]


class EvolutionTaskRollbackRequest(BaseModel):
    actor_id: str
    note: str = ""


class EvolutionChangeSet(BaseModel):
    change_set_id: str
    task_id: str
    tool_id: str
    change_kind: str
    before_snapshot: dict[str, Any]
    after_snapshot: dict[str, Any]
    applied_at: str = Field(default_factory=now_iso)
    applied_by: str = "p4-runtime"


class EvolutionRollbackRecord(BaseModel):
    rollback_id: str
    task_id: str
    change_set_ids: list[str] = Field(default_factory=list)
    rolled_back_by: str
    rolled_back_at: str = Field(default_factory=now_iso)
    rollback_summary: str = ""


class EvolutionRuntimeState(BaseModel):
    evolution_dirty: bool = True
    last_scheduled_evolution_at: str | None = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


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
    evolution_config: EvolutionInspectionConfig = Field(default_factory=EvolutionInspectionConfig)
    evolution_runs: list[EvolutionRun] = Field(default_factory=list)
    evolution_tasks: list[EvolutionTask] = Field(default_factory=list)
    runtime_state: EvolutionRuntimeState = Field(default_factory=EvolutionRuntimeState)


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


class EvolutionConfigReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: EvolutionInspectionConfig


class EvolutionTaskReadEnvelope(BaseModel):
    meta: ToolHubSnapshotMeta
    data: EvolutionTaskEnvelope
