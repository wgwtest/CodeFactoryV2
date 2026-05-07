from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.orchestrators.plugin_discovery import OrchestratorPluginDiscovery


def write_plugin(
    root: Path,
    domain: str,
    plugin: str,
    *,
    plugin_id: str | None = None,
    adapter_module: str = "adapter",
    adapter_class: str = "ExampleAdapter",
    write_adapter: bool = True,
) -> Path:
    plugin_dir = root / domain / plugin
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "plugin_id": plugin_id or plugin,
                "name": plugin,
                "plugin_type": "local_package",
                "document_type": "xg",
                "contract": "xg-observable-orchestrator-contract@1",
                "status": "active",
                "priority": 10,
                "capabilities": {"document_patch": True},
                "requires": {"template": True, "model_provider": "optional"},
                "adapter_module": adapter_module,
                "adapter_class": adapter_class,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if write_adapter:
        (plugin_dir / "adapter.py").write_text(
            "class ExampleAdapter:\n"
            "    def __init__(self, *, manifest, package=None):\n"
            "        self.manifest = manifest\n"
            "        self.package = package\n",
            encoding="utf-8",
        )
    return plugin_dir


def test_plugin_discovery_scans_one_domain_plugin_level(tmp_path: Path) -> None:
    write_plugin(tmp_path, "xg", "xg-local-example-orchestrator")
    write_plugin(tmp_path, "xg", "nested/too-deep-orchestrator")

    discovered = OrchestratorPluginDiscovery(root=tmp_path).discover()

    assert [item.manifest.plugin_id for item in discovered.plugins] == ["xg-local-example-orchestrator"]
    assert discovered.errors == []
    assert discovered.plugins[0].plugin_dir == tmp_path / "xg" / "xg-local-example-orchestrator"
    assert discovered.plugins[0].adapter_path == tmp_path / "xg" / "xg-local-example-orchestrator" / "adapter.py"


def test_plugin_discovery_rejects_manifest_without_local_entry(tmp_path: Path) -> None:
    plugin_dir = write_plugin(tmp_path, "xg", "xg-broken-orchestrator")
    manifest = json.loads((plugin_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("adapter_module")
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    discovered = OrchestratorPluginDiscovery(root=tmp_path).discover()

    assert discovered.plugins == []
    assert any("adapter_module" in error.message for error in discovered.errors)


def test_plugin_discovery_rejects_missing_adapter_file(tmp_path: Path) -> None:
    write_plugin(tmp_path, "xg", "xg-missing-entry-orchestrator", write_adapter=False)

    discovered = OrchestratorPluginDiscovery(root=tmp_path).discover()

    assert discovered.plugins == []
    assert any("adapter file does not exist" in error.message for error in discovered.errors)


def test_plugin_discovery_reflects_removed_and_restored_plugin_directory(tmp_path: Path) -> None:
    plugin_dir = write_plugin(tmp_path, "xg", "xg-removable-orchestrator")
    backup_dir = tmp_path / "xg" / "xg-removable-orchestrator.bak"

    assert [item.manifest.plugin_id for item in OrchestratorPluginDiscovery(root=tmp_path).discover().plugins] == [
        "xg-removable-orchestrator"
    ]

    shutil.move(plugin_dir, backup_dir)
    assert OrchestratorPluginDiscovery(root=tmp_path).discover().plugins == []

    shutil.move(backup_dir, plugin_dir)
    assert [item.manifest.plugin_id for item in OrchestratorPluginDiscovery(root=tmp_path).discover().plugins] == [
        "xg-removable-orchestrator"
    ]


def test_repository_plugins_are_discoverable() -> None:
    discovered = OrchestratorPluginDiscovery().discover()
    plugin_ids = {item.manifest.plugin_id for item in discovered.plugins}

    assert "xg-local-heuristic-orchestrator" in plugin_ids
    assert "xg-local-strong-rule-orchestrator" in plugin_ids
    assert "xg-dify-workflow-orchestrator" in plugin_ids
    assert all(item.adapter_path.parent == item.plugin_dir for item in discovered.plugins)
    assert discovered.errors == []
