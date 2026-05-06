from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


PluginType = Literal["local_package", "dify_workflow", "remote_service"]
ObservabilityLevel = Literal["full", "limited", "none"]

OBSERVABILITY_CAPABILITY_KEYS = (
    "stage_results",
    "stage_audits",
    "provider_logs",
    "decision_trace",
    "review_after_apply",
    "spec_tree_update",
)


class OrchestratorPluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin_id: str
    name: str
    plugin_type: PluginType
    document_type: str = "xg"
    contract: str = "xg-observable-orchestrator-contract@1"
    status: str = "active"
    priority: int = 100
    capabilities: dict[str, bool] = Field(default_factory=dict)
    requires: dict[str, Any] = Field(default_factory=dict)
    adapter_entry: str

    @property
    def observability_level(self) -> ObservabilityLevel:
        if all(bool(self.capabilities.get(key)) for key in OBSERVABILITY_CAPABILITY_KEYS):
            return "full"
        if (
            any(bool(self.capabilities.get(key)) for key in OBSERVABILITY_CAPABILITY_KEYS)
            or bool(self.capabilities.get("filled_document_text"))
            or bool(self.capabilities.get("document_patch"))
        ):
            return "limited"
        return "none"

    def to_api(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "orchestrator_id": self.plugin_id,
            "name": self.name,
            "plugin_type": self.plugin_type,
            "document_type": self.document_type,
            "contract": self.contract,
            "status": self.status,
            "priority": self.priority,
            "capabilities": dict(self.capabilities),
            "requires": dict(self.requires),
            "adapter_entry": self.adapter_entry,
            "observability_level": self.observability_level,
        }


class OrchestratorRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    session: dict[str, Any]
    turn: dict[str, Any]
    template: dict[str, Any]
    document_context: dict[str, Any]
    execution_options: dict[str, Any]


class OrchestratorRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    plugin: dict[str, Any]
    final_output: dict[str, Any]
    interaction_output: dict[str, Any]
    process_output: dict[str, Any]
    state_output: dict[str, Any]
    raw_output: dict[str, Any]
