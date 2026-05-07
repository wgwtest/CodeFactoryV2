from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import REPO_ROOT
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest


DEFAULT_PLUGIN_ROOT = REPO_ROOT / "orchestrators"


@dataclass(frozen=True)
class OrchestratorPluginDiscoveryError:
    manifest_path: Path
    message: str


@dataclass(frozen=True)
class DiscoveredOrchestratorPlugin:
    manifest: OrchestratorPluginManifest
    plugin_dir: Path
    manifest_path: Path
    adapter_path: Path


@dataclass(frozen=True)
class OrchestratorPluginDiscoveryResult:
    plugins: list[DiscoveredOrchestratorPlugin]
    errors: list[OrchestratorPluginDiscoveryError]


class OrchestratorPluginDiscovery:
    def __init__(self, root: Path = DEFAULT_PLUGIN_ROOT) -> None:
        self.root = root

    def discover(self) -> OrchestratorPluginDiscoveryResult:
        if not self.root.exists():
            return OrchestratorPluginDiscoveryResult(plugins=[], errors=[])

        plugins: list[DiscoveredOrchestratorPlugin] = []
        errors: list[OrchestratorPluginDiscoveryError] = []
        seen_ids: set[str] = set()

        for manifest_path in self._manifest_paths():
            try:
                plugin = self._load_manifest(manifest_path)
            except ValueError as exc:
                errors.append(OrchestratorPluginDiscoveryError(manifest_path=manifest_path, message=str(exc)))
                continue
            if plugin.manifest.plugin_id in seen_ids:
                errors.append(
                    OrchestratorPluginDiscoveryError(
                        manifest_path=manifest_path,
                        message=f"duplicate orchestrator plugin id: {plugin.manifest.plugin_id}",
                    )
                )
                continue
            seen_ids.add(plugin.manifest.plugin_id)
            plugins.append(plugin)

        plugins.sort(key=lambda item: (item.manifest.priority, item.manifest.plugin_id))
        return OrchestratorPluginDiscoveryResult(plugins=plugins, errors=errors)

    def _manifest_paths(self) -> list[Path]:
        manifest_paths: list[Path] = []
        for domain_dir in sorted(path for path in self.root.iterdir() if _is_scannable_dir(path)):
            for plugin_dir in sorted(path for path in domain_dir.iterdir() if _is_scannable_dir(path)):
                manifest_path = plugin_dir / "manifest.json"
                if manifest_path.exists():
                    manifest_paths.append(manifest_path)
        return manifest_paths

    def _load_manifest(self, manifest_path: Path) -> DiscoveredOrchestratorPlugin:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid manifest json: {exc.msg}") from exc

        payload = self._normalize_legacy_manifest(payload)
        payload["package_path"] = _package_path(manifest_path.parent)
        try:
            manifest = OrchestratorPluginManifest(**payload)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        adapter_path = self._adapter_path(manifest_path.parent, manifest.adapter_module)
        if not adapter_path.exists():
            raise ValueError(f"adapter file does not exist: {adapter_path}")

        return DiscoveredOrchestratorPlugin(
            manifest=manifest,
            plugin_dir=manifest_path.parent,
            manifest_path=manifest_path,
            adapter_path=adapter_path,
        )

    @staticmethod
    def _normalize_legacy_manifest(payload: dict) -> dict:
        normalized = dict(payload)
        if "plugin_id" not in normalized and "id" in normalized:
            normalized["plugin_id"] = normalized["id"]
        normalized.setdefault("plugin_type", "local_package")
        if normalized.get("contract") == "xg-orchestrator-contract@1":
            normalized["contract"] = "xg-observable-orchestrator-contract@1"
        normalized.setdefault("contract", "xg-observable-orchestrator-contract@1")
        if "adapter_entry" not in normalized:
            normalized["adapter_entry"] = "local_xg" if normalized.get("plugin_type") == "local_package" else str(normalized.get("mode") or "")
        if normalized.get("plugin_type") == "local_package" and "package_id" not in normalized and "id" in normalized:
            normalized["package_id"] = normalized["id"]
        normalized["aliases"] = _normalize_aliases(normalized.get("aliases") or ())
        normalized["capabilities"] = _normalize_capabilities(normalized.get("capabilities") or {})
        return {
            key: normalized[key]
            for key in OrchestratorPluginManifest.model_fields
            if key in normalized
        }

    @staticmethod
    def _adapter_path(plugin_dir: Path, adapter_module: str) -> Path:
        module_path = adapter_module.replace(".", "/")
        if module_path.startswith("apps/"):
            return REPO_ROOT / f"{module_path}.py"
        if module_path.startswith("app/"):
            return REPO_ROOT / "apps" / "api" / f"{module_path}.py"
        return plugin_dir / f"{module_path}.py"


def _normalize_capabilities(value: object) -> dict[str, bool]:
    if isinstance(value, dict):
        return {str(key): bool(item) for key, item in value.items()}
    if isinstance(value, list):
        capability_names = {str(item) for item in value}
        return {
            "filled_document_text": False,
            "document_patch": "document_patch" in capability_names,
            "stage_results": "turn_audit" in capability_names,
            "stage_audits": "turn_audit" in capability_names,
            "provider_logs": "turn_audit" in capability_names,
            "decision_trace": "turn_audit" in capability_names,
            "review_after_apply": "turn_audit" in capability_names,
            "spec_tree_update": "spec_tree_update" in capability_names,
            "streaming_events": False,
        }
    return {}


def _normalize_aliases(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    aliases = []
    for item in value:
        alias = str(item).strip()
        if alias and alias not in aliases:
            aliases.append(alias)
    return tuple(aliases)


def _is_scannable_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    name = path.name
    return not name.startswith(".") and not name.endswith(".bak")


def _package_path(plugin_dir: Path) -> str:
    try:
        return str(plugin_dir.relative_to(REPO_ROOT))
    except ValueError:
        return str(plugin_dir)
