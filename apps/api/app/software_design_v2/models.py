from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class P3DesignSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_package_id: str
    design_title: str
    version_label: str
    generation_policy: dict[str, str] = Field(default_factory=dict)


class P3DesignTurnWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str
    turn_type: str = "design_turn"
    interaction_mode: str = "propose_patch"
    scope_anchor: dict | None = None
    expected_output: list[str] = Field(default_factory=list)


class P3DesignConversionRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str = "standard_sdd_draft"
    converter_id: str | None = None
    options: dict[str, str] = Field(default_factory=dict)


class P3DesignPatchProposalApply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str | None = None
    base_revision_id: str
    apply_scope: str = "document_only"
    user_note: str | None = None
