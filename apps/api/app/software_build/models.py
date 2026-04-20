from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.software_design.models import DesignModule


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


P5DeliveryOrderStatus = Literal[
    "draft",
    "assembling",
    "exported_with_gaps",
    "completed_with_gaps",
    "completed",
    "failed",
]
P5BindingStatus = Literal["bound", "placeholder"]
P5BindingSource = Literal["heuristic", "manual", "empty"]
P5ValidationStatus = Literal["passed", "warning", "failed", "skipped"]
P5GapKind = Literal["design_gap", "supply_gap", "assembly_or_build_gap"]
P5FeedbackTaskStatus = Literal["pending_confirmation", "confirmed", "dismissed"]
P5RuntimeExecutorStatus = Literal["idle", "running", "completed", "blocked", "failed"]
P5RuntimeStageStatus = Literal["pending", "running", "completed", "warning", "failed"]
P5RuntimeLogLevel = Literal["info", "warning", "error"]
P5OutputArtifactStatus = Literal["generated", "generated_with_gaps", "placeholder"]
P5DesignInputSourceKind = Literal["p3_baseline", "xx_p3_doc_sim"]
P5SupplyInputSourceKind = Literal["p4_supply", "xx_p4_supply_sim"]
P5SupplyMode = Literal["snapshot", "empty"]


class P5DesignInputSimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_name: str
    requirement_spec_id: str
    baseline_id: str
    notes: str = ""
    module_specs: list[DesignModule] = Field(default_factory=list)


class P5SupplyInputTool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str
    tool_name: str
    tool_slug: str
    verification_status: str = "verified"
    keywords: list[str] = Field(default_factory=list)


class P5SupplyInputSimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_name: str
    notes: str = ""
    tools: list[P5SupplyInputTool] = Field(default_factory=list)


class P5DesignInputSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_input_id: str
    source_kind: P5DesignInputSourceKind
    source_ref_id: str
    p3_order_id: str | None = None
    application_name: str
    requirement_spec_id: str
    baseline_id: str
    notes: str = ""
    module_count: int = 0
    module_names: list[str] = Field(default_factory=list)
    modules: list[DesignModule] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class P5SupplyInputSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supply_input_id: str
    source_kind: P5SupplyInputSourceKind
    source_ref_id: str
    snapshot_name: str
    notes: str = ""
    tool_count: int = 0
    tool_names: list[str] = Field(default_factory=list)
    tools: list[P5SupplyInputTool] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class P5ModuleBindingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    tool_id: str
    tool_name: str | None = None
    source: Literal["manual"] = "manual"
    updated_by: str
    updated_at: str = Field(default_factory=now_iso)


class P5InputBindingConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_input_id: str
    supply_input_id: str | None = None
    supply_mode: P5SupplyMode = "empty"
    confirmed_by: str


class P5ModuleBindingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str
    updated_by: str


class P5InputBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str
    delivery_order_id: str
    design_input_id: str
    supply_input_id: str | None = None
    supply_mode: P5SupplyMode = "empty"
    module_bindings: list[P5ModuleBindingDecision] = Field(default_factory=list)
    is_confirmed: bool = False
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    updated_at: str = Field(default_factory=now_iso)


class P5DeliveryOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p3_order_id: str | None = None
    design_input_id: str | None = None
    requested_by: str
    notes: str = ""


class P5DeliveryOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_order_id: str
    p3_order_id: str
    requirement_spec_id: str
    application_name: str
    requested_by: str
    notes: str = ""
    status: P5DeliveryOrderStatus = "draft"
    current_attempt_count: int = 0
    formal_result_ready: bool = False
    active_input_binding: P5InputBinding
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class P5ExportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_root: str
    build_profile: str = "baseline"
    attempt_note: str = ""


class P5AssemblyModule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    name: str
    objective: str
    target_directories: list[str] = Field(default_factory=list)
    binding_status: P5BindingStatus = "placeholder"
    binding_source: P5BindingSource = "empty"
    bound_tool_id: str | None = None
    bound_tool_name: str | None = None
    gap_reason: str | None = None


class P5AssemblyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modules: list[P5AssemblyModule] = Field(default_factory=list)


class P5GapRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_id: str
    kind: P5GapKind
    module_id: str | None = None
    module_name: str | None = None
    summary: str
    detail: str


class P5FeedbackTaskReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirmed", "dismissed"]
    reviewed_by: str
    review_note: str = ""


class P5FeedbackTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    gap_id: str
    kind: P5GapKind
    title: str
    detail: str
    status: P5FeedbackTaskStatus = "pending_confirmation"
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None


class P5ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_closure_status: P5ValidationStatus = "passed"
    structure_status: P5ValidationStatus = "passed"
    build_status: P5ValidationStatus = "skipped"
    summary: str = ""


class P5DesignInputSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str
    design_input_id: str
    order_id: str
    baseline_id: str
    module_count: int = 0
    module_names: list[str] = Field(default_factory=list)


class P5SupplyInputSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str
    supply_input_id: str | None = None
    tool_count: int = 0
    tool_names: list[str] = Field(default_factory=list)
    matched_tool_count: int = 0


class P5InputSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_input: P5DesignInputSnapshot
    supply_input: P5SupplyInputSnapshot


class P5RuntimeStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str
    label: str
    status: P5RuntimeStageStatus
    detail: str = ""


class P5RuntimeLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(default_factory=now_iso)
    level: P5RuntimeLogLevel = "info"
    message: str


class P5RuntimeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executor_name: str = "p5-mvp-executor"
    executor_status: P5RuntimeExecutorStatus = "idle"
    attempt_status: P5DeliveryOrderStatus = "draft"
    progress_percent: int = 0
    stages: list[P5RuntimeStage] = Field(default_factory=list)
    recent_logs: list[P5RuntimeLog] = Field(default_factory=list)
    block_reason: str | None = None


class P5OutputArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    kind: Literal["file", "directory"] = "file"
    status: P5OutputArtifactStatus = "generated"
    summary: str = ""


class P5OutputPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_directory: str
    directories: list[str] = Field(default_factory=list)
    key_files: list[P5OutputArtifact] = Field(default_factory=list)


class P5AssemblyAttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_root: str
    build_profile: str = "baseline"
    attempt_note: str = ""


class P5AssemblyAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: str
    delivery_order_id: str
    sequence: int
    export_config: P5ExportConfig
    input_snapshot: P5InputSnapshot
    assembly_plan: P5AssemblyPlan
    runtime_snapshot: P5RuntimeSnapshot
    validation_report: P5ValidationReport
    output_preview: P5OutputPreview
    gaps: list[P5GapRecord] = Field(default_factory=list)
    feedback_tasks: list[P5FeedbackTask] = Field(default_factory=list)
    export_directory: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class P5DeliveryOrderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_order_id: str
    p3_order_id: str
    application_name: str
    status: P5DeliveryOrderStatus
    current_attempt_count: int
    updated_at: str


class P5BuildMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_count: int = 0
    draft_count: int = 0
    exported_with_gaps_count: int = 0
    completed_count: int = 0
    failed_count: int = 0


class P5BuildOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: P5BuildMetrics
    recent_orders: list[P5DeliveryOrderSummary] = Field(default_factory=list)


class P5DeliveryOrderDetail(P5DeliveryOrder):
    model_config = ConfigDict(extra="forbid")

    attempts: list[P5AssemblyAttempt] = Field(default_factory=list)


class P5WorkspaceBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_root: str
    build_profile: str = "demo"
    attempt_note: str = "bootstrap-demo"


class P5WorkspaceBootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_order_id: str
    attempt_id: str
    created_demo_inputs: bool = False


class P5DeliveryRuntimeClearResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cleared_order_count: int = 0
    cleared_attempt_count: int = 0
    cleared_export_directory_count: int = 0
