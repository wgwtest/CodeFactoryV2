from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


BrainstormOrchestratorId = Literal["brainstorming", "wizard", "form_driven", "rule_based_review"]
BrainstormProviderId = Literal["mock", "deepseek", "openai"]


class BrainstormSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    orchestrator_id: str = "xg-brainstorming-orchestrator"
    provider_id: str = "mock"
    model: str = "mock-brainstorm-v1"
    template_id: str = "81433号"
    knowledge_package_id: str = "airspace-domain-demo"
    write_policy: str = "patch_suggestion_only"


class BrainstormTurnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str
