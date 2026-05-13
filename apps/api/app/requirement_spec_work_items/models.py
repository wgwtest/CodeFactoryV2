from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CreateAction = Literal["enter_config", "stay"]


class RequirementSpecWorkItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    initial_description: str = ""
    template_id: str
    knowledge_binding: dict | None = None
    create_action: CreateAction = "enter_config"


class RequirementSpecWorkItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    initial_description: str | None = None
    template_id: str | None = None
    knowledge_binding: dict | None = None


class RequirementSpecWorkItemConfigure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    orchestrator_id: str = ""
    provider_id: str = "mock"
    model: str = "mock-requirement-analysis-v1"
    template_id: str = "81433号"
    knowledge_package_id: str = "airspace-domain-demo"
    write_policy: str = "patch_suggestion_only"


class RequirementSpecWorkItemRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None


class RequirementSpecWorkItemSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_item_id: str
    title: str
    initial_description: str
    status: str
    template_id: str
    knowledge_binding: dict | None = None
    authoring_document_id: str
    analysis_session_id: str | None = None
    published_requirement_spec_id: str | None = None
    published_package_id: str | None = None
    version: int
    p3_consumable: bool
    next_action: CreateAction | None = None
    available_actions: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class RequirementSpecWorkItemEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RequirementSpecWorkItemSummary]
