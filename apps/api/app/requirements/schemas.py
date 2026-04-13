from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequirementApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    domain: str = ""
    summary: str = ""
    target_users: list[str] = Field(default_factory=list)


class RequirementObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    object_kind: Literal["business", "supporting"]
    source_kind: Literal["formal", "temporary"]
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    source_archive_id: str | None = None
    source_item_type: Literal["entity", "process"] | None = None
    source_item_id: str | None = None

    @model_validator(mode="after")
    def validate_source_fields(self) -> "RequirementObject":
        if self.source_kind == "formal":
            if not self.source_archive_id or not self.source_item_type or not self.source_item_id:
                raise ValueError("formal objects require source archive, item type, and item id")
        return self


class RequirementProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    process_kind: Literal["lifecycle", "collaboration"] = "collaboration"
    source_kind: Literal["formal", "temporary"] = "temporary"
    description: str | None = None
    participant_object_ids: list[str] = Field(default_factory=list)
    source_archive_id: str | None = None
    source_item_type: Literal["process"] | None = None
    source_item_id: str | None = None


class RequirementRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""


class RequirementMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""


class RequirementConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    description: str


class RequirementSpecPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application: RequirementApplication = Field(default_factory=RequirementApplication)
    objects: list[RequirementObject] = Field(default_factory=list)
    processes: list[RequirementProcess] = Field(default_factory=list)
    rules: list[RequirementRule] = Field(default_factory=list)
    metrics: list[RequirementMetric] = Field(default_factory=list)
    non_functional_constraints: list[RequirementConstraint] = Field(default_factory=list)


class RequirementSpecWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_id: str | None = None
    status: Literal["draft", "reviewing", "ready"] = "draft"
    payload: RequirementSpecPayload
