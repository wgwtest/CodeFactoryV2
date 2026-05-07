from __future__ import annotations

from functools import lru_cache

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest
from app.orchestrators.plugin_discovery import OrchestratorPluginDiscovery


class OrchestratorPluginRegistry:
    def __init__(self) -> None:
        discovery_result = OrchestratorPluginDiscovery().discover()
        if discovery_result.errors:
            messages = "; ".join(error.message for error in discovery_result.errors)
            raise ValueError(f"orchestrator plugin discovery failed: {messages}")
        self._plugins = {item.manifest.plugin_id: item.manifest for item in discovery_result.plugins}
        self._aliases = {
            alias: item.manifest.plugin_id
            for item in discovery_result.plugins
            for alias in item.manifest.aliases
        }

    def list_plugins(self) -> list[OrchestratorPluginManifest]:
        return sorted(self._plugins.values(), key=lambda item: (item.priority, item.plugin_id))

    def default_plugin(self) -> OrchestratorPluginManifest:
        active_plugins = [
            plugin
            for plugin in self.list_plugins()
            if str(plugin.status or "").lower() in {"active", "available"}
        ]
        plugins = active_plugins or self.list_plugins()
        if not plugins:
            raise ValueError("no orchestrator plugins available")
        return plugins[0]

    def get(self, plugin_id: str) -> OrchestratorPluginManifest | None:
        return self._plugins.get(self._normalize(plugin_id))

    def require(self, plugin_id: str) -> OrchestratorPluginManifest:
        plugin = self.get(plugin_id)
        if plugin is None:
            raise ValueError("unsupported orchestrator")
        return plugin

    @staticmethod
    def _normalize_id(plugin_id: str) -> str:
        return plugin_id.strip()

    def _normalize(self, plugin_id: str) -> str:
        normalized = self._normalize_id(plugin_id)
        return self._aliases.get(normalized, normalized)

    def local_package_id_for_plugin(self, plugin_id: str) -> str:
        plugin = self.require(plugin_id)
        return plugin.package_id or plugin.plugin_id


@lru_cache(maxsize=1)
def get_orchestrator_plugin_registry() -> OrchestratorPluginRegistry:
    return OrchestratorPluginRegistry()


def reload_orchestrator_plugin_registry() -> OrchestratorPluginRegistry:
    get_orchestrator_plugin_registry.cache_clear()
    return get_orchestrator_plugin_registry()
