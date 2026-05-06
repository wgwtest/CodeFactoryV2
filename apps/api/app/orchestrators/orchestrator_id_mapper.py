from __future__ import annotations


LEGACY_PACKAGE_TO_PLUGIN_ID = {
    "xg-heuristic-orchestrator": "xg-local-heuristic-orchestrator",
    "xg-strong-rule-orchestrator": "xg-local-strong-rule-orchestrator",
}

LOCAL_PLUGIN_TO_PACKAGE_ID = {
    plugin_id: package_id for package_id, plugin_id in LEGACY_PACKAGE_TO_PLUGIN_ID.items()
}


def normalize_orchestrator_plugin_id(orchestrator_id: str) -> str:
    normalized = orchestrator_id.strip()
    return LEGACY_PACKAGE_TO_PLUGIN_ID.get(normalized, normalized)


def local_package_id_for_orchestrator(orchestrator_id: str) -> str:
    normalized = orchestrator_id.strip()
    return LOCAL_PLUGIN_TO_PACKAGE_ID.get(normalized, normalized)
