from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


OrderStatus = Literal[
    "pending_approval",
    "rejected",
    "approved_for_generation",
    "generating",
    "draft_ready",
    "in_revision",
    "pending_review",
    "changes_requested",
    "frozen",
    "package_ready",
    "pushed_to_p4",
]


class P3OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_spec_id: str
    requested_by: str
    notes: str = ""


class P3Order(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    requirement_spec_id: str
    application_name: str
    domain_name: str
    requirement_spec_status: str
    requested_by: str
    notes: str = ""
    status: OrderStatus = "pending_approval"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class DesignSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    summary: str
    body: str


class DesignModule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    name: str
    objective: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)


class SoftwareDesignBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: str
    order_id: str
    requirement_spec_id: str
    architecture_mode: Literal["unified_service", "microservice"] = "unified_service"
    interaction_mode: Literal["bs", "cs"] = "bs"
    sections: list[DesignSection] = Field(default_factory=list)
    modules: list[DesignModule] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ReviewThreadWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    anchor: str
    message: str


class ReviewThread(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    order_id: str
    topic: str
    anchor: str
    status: Literal["open", "resolved"] = "open"
    messages: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ModuleWorkorderBatchOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architecture_recommendation: str
    interaction_mode: str
    deployment_hint: str = "intranet_first"
    tool_recommendations: list[str] = Field(default_factory=list)
    design_notes: list[str] = Field(default_factory=list)


class ModuleWorkorderBatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    module_id: str
    title: str
    objective: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)


class ModuleWorkorderBatchPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    order_id: str
    design_description_id: str
    package_overview: ModuleWorkorderBatchOverview
    items: list[ModuleWorkorderBatchItem] = Field(default_factory=list)
    push_status: Literal["not_pushed", "pushed"] = "not_pushed"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class P3OrderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    requirement_spec_id: str
    application_name: str
    status: OrderStatus
    updated_at: str


class SoftwareDesignMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_count: int = 0
    pending_approval_count: int = 0
    frozen_count: int = 0
    package_ready_count: int = 0
    pushed_count: int = 0


class PackageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    order_id: str
    item_count: int
    push_status: str


class SoftwareDesignOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: SoftwareDesignMetrics
    recent_orders: list[P3OrderSummary] = Field(default_factory=list)
    recent_packages: list[PackageSummary] = Field(default_factory=list)


class RequirementSpecSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_name: str
    domain_name: str
    status: str


class SoftwareDesignDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[DesignSection] = Field(default_factory=list)
    modules: list[DesignModule] = Field(default_factory=list)


class P3OrderDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    status: OrderStatus
    requirement_spec_summary: RequirementSpecSummary
    design_description: SoftwareDesignDescription | None = None
    review_threads: list[ReviewThread] = Field(default_factory=list)
    workorder_batch: ModuleWorkorderBatchPackage | None = None
