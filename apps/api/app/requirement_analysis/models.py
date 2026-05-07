from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RequirementAnalysisSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    orchestrator_id: str = ""
    provider_id: str = "mock"
    model: str = "mock-requirement-analysis-v1"
    template_id: str = "81433号"
    knowledge_package_id: str = "airspace-domain-demo"
    write_policy: str = "patch_suggestion_only"


class RequirementAnalysisTurnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str
