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


class P3DesignConversionRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str = "standard_sdd_draft"
