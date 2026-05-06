from __future__ import annotations

from functools import lru_cache

from app.orchestrators.orchestrator_id_mapper import normalize_orchestrator_plugin_id
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest


def _full_local_capabilities() -> dict[str, bool]:
    return {
        "filled_document_text": False,
        "document_patch": True,
        "stage_results": True,
        "stage_audits": True,
        "provider_logs": True,
        "decision_trace": True,
        "review_after_apply": True,
        "spec_tree_update": True,
        "streaming_events": False,
    }


class OrchestratorPluginRegistry:
    def __init__(self) -> None:
        self._plugins = {
            "xg-local-heuristic-orchestrator": OrchestratorPluginManifest(
                plugin_id="xg-local-heuristic-orchestrator",
                name="XG Local Heuristic Orchestrator",
                plugin_type="local_package",
                status="active",
                priority=10,
                capabilities=_full_local_capabilities(),
                requires={"template": True, "knowledge_binding": True, "model_provider": "optional"},
                adapter_entry="local_xg",
            ),
            "xg-local-strong-rule-orchestrator": OrchestratorPluginManifest(
                plugin_id="xg-local-strong-rule-orchestrator",
                name="XG Local Strong Rule Orchestrator",
                plugin_type="local_package",
                status="active",
                priority=20,
                capabilities=_full_local_capabilities(),
                requires={"template": True, "knowledge_binding": False, "model_provider": "optional"},
                adapter_entry="local_xg",
            ),
            "xg-dify-workflow-orchestrator": OrchestratorPluginManifest(
                plugin_id="xg-dify-workflow-orchestrator",
                name="XG Dify Workflow Orchestrator",
                plugin_type="dify_workflow",
                status="available",
                priority=90,
                capabilities={
                    "filled_document_text": True,
                    "document_patch": False,
                    "stage_results": False,
                    "stage_audits": False,
                    "provider_logs": False,
                    "decision_trace": False,
                    "review_after_apply": False,
                    "spec_tree_update": False,
                    "streaming_events": True,
                },
                requires={"template": True, "knowledge_binding": False, "model_provider": "external_workflow"},
                adapter_entry="dify_workflow",
            ),
        }

    def list_plugins(self) -> list[OrchestratorPluginManifest]:
        return sorted(self._plugins.values(), key=lambda item: (item.priority, item.plugin_id))

    def get(self, plugin_id: str) -> OrchestratorPluginManifest | None:
        return self._plugins.get(self._normalize(plugin_id))

    def require(self, plugin_id: str) -> OrchestratorPluginManifest:
        plugin = self.get(plugin_id)
        if plugin is None:
            raise ValueError("unsupported orchestrator")
        return plugin

    @staticmethod
    def _normalize(plugin_id: str) -> str:
        return normalize_orchestrator_plugin_id(plugin_id)


@lru_cache(maxsize=1)
def get_orchestrator_plugin_registry() -> OrchestratorPluginRegistry:
    return OrchestratorPluginRegistry()
