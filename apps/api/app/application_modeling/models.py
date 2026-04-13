from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

RequirementStep = Literal["goal", "audience", "flow", "object_event", "structure"]
RequirementDraftStatus = Literal["draft", "completed"]
RecommendationSource = Literal["recommended_common", "recommended_domain", "manual"]


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class RecommendationItem(BaseModel):
    id: str
    name: str
    description: str = ""
    source: RecommendationSource
    tags: list[str] = Field(default_factory=list)
    related_knowledge_id: str | None = None


class RequirementGoal(BaseModel):
    problem_statement: str = ""
    target_outcome: str = ""
    success_criteria: list[str] = Field(default_factory=list)


class RequirementAudience(BaseModel):
    id: str
    name: str
    description: str = ""


class RequirementRole(BaseModel):
    id: str
    name: str
    audience_id: str = ""
    responsibility_summary: str = ""


class RequirementBusinessFlow(BaseModel):
    id: str
    name: str
    scope: str = ""
    priority: str = ""
    participants: list[str] = Field(default_factory=list)


class RequirementBusinessObject(BaseModel):
    id: str
    name: str
    description: str = ""


class RequirementEvent(BaseModel):
    id: str
    name: str
    description: str = ""


class RequirementWorkspace(BaseModel):
    id: str
    name: str


class RequirementPage(BaseModel):
    id: str
    name: str
    page_type: str = ""


class RequirementPermissionIntent(BaseModel):
    role_id: str
    access_scope: str


class RequirementApplicationStructure(BaseModel):
    workspaces: list[RequirementWorkspace] = Field(default_factory=list)
    pages: list[RequirementPage] = Field(default_factory=list)
    permission_intents: list[RequirementPermissionIntent] = Field(default_factory=list)


class RequirementKnowledgeReference(BaseModel):
    source_type: str
    source_id: str
    source_name: str


class RequirementManualAddition(BaseModel):
    target_type: str
    name: str


class ApplicationRequirementModel(BaseModel):
    archive_id: str
    application_name: str = ""
    application_goal: RequirementGoal = Field(default_factory=RequirementGoal)
    audiences: list[RequirementAudience] = Field(default_factory=list)
    roles: list[RequirementRole] = Field(default_factory=list)
    business_flows: list[RequirementBusinessFlow] = Field(default_factory=list)
    business_objects: list[RequirementBusinessObject] = Field(default_factory=list)
    key_events: list[RequirementEvent] = Field(default_factory=list)
    application_structure: RequirementApplicationStructure = Field(default_factory=RequirementApplicationStructure)
    knowledge_references: list[RequirementKnowledgeReference] = Field(default_factory=list)
    manual_additions: list[RequirementManualAddition] = Field(default_factory=list)


class RequirementDraft(ApplicationRequirementModel):
    draft_id: str
    status: RequirementDraftStatus = "draft"
    current_step: RequirementStep = "goal"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class RequirementDraftCreateRequest(BaseModel):
    archive_id: str


class RequirementDraftUpdate(BaseModel):
    current_step: RequirementStep | None = None
    application_name: str | None = None
    application_goal: RequirementGoal | None = None
    audiences: list[RequirementAudience] | None = None
    roles: list[RequirementRole] | None = None
    business_flows: list[RequirementBusinessFlow] | None = None
    business_objects: list[RequirementBusinessObject] | None = None
    key_events: list[RequirementEvent] | None = None
    application_structure: RequirementApplicationStructure | None = None
    knowledge_references: list[RequirementKnowledgeReference] | None = None
    manual_additions: list[RequirementManualAddition] | None = None


class RequirementDraftEnvelope(BaseModel):
    draft: RequirementDraft
    recommendations: dict[str, list[RecommendationItem]]


class RequirementDraftExport(BaseModel):
    draft_id: str
    model: ApplicationRequirementModel
    json_text: str
    yaml_text: str
    markdown: str
