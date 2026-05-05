from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class P3DesignSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_package_id: str
    generation_policy: dict[str, str] = Field(default_factory=dict)


class P3DesignTurnWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str

