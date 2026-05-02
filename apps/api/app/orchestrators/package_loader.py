from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT


XG_ORCHESTRATOR_CONTRACT = "xg-orchestrator-contract@1"
DEFAULT_ORCHESTRATOR_ROOT = REPO_ROOT / "orchestrators" / "xg"


@dataclass(frozen=True)
class OrchestratorPackage:
    orchestrator_id: str
    name: str
    version: str
    stage: str
    document_type: str
    contract: str
    mode: str
    status: str
    description: str
    entry: str | None
    capabilities: tuple[str, ...]
    requires: dict[str, Any]
    package_path: str
    priority: int

    def to_api(self) -> dict:
        return {
            "orchestrator_id": self.orchestrator_id,
            "name": self.name,
            "version": self.version,
            "stage": self.stage,
            "document_type": self.document_type,
            "contract": self.contract,
            "mode": self.mode,
            "status": self.status,
            "description": self.description,
            "entry": self.entry,
            "capabilities": list(self.capabilities),
            "requires": dict(self.requires),
            "package_path": self.package_path,
        }


@dataclass(frozen=True)
class LoadedOrchestratorPackage:
    package: OrchestratorPackage
    root_path: Path
    manifest: dict[str, Any]
    orchestrator_text: str
    policy_text: str
    prompt_text: str
    artifact_rules: dict[str, Any]
    contract_schema: dict[str, Any]
    entry_path: str | None


class OrchestratorPackageLoader:
    def __init__(self, root: Path = DEFAULT_ORCHESTRATOR_ROOT) -> None:
        self.root = root

    def load_all(self) -> list[LoadedOrchestratorPackage]:
        if not self.root.exists():
            raise RuntimeError(f"orchestrator root does not exist: {self.root}")
        loaded = [self._load_manifest(manifest_path) for manifest_path in sorted(self.root.glob("*/manifest.json"))]
        if not loaded:
            raise RuntimeError(f"no orchestrator packages found under: {self.root}")
        duplicated = self._duplicated_ids([item.package.orchestrator_id for item in loaded])
        if duplicated:
            raise RuntimeError(f"duplicate orchestrator id: {duplicated}")
        return sorted(loaded, key=lambda item: (item.package.priority, item.package.orchestrator_id))

    def load(self, orchestrator_id: str) -> LoadedOrchestratorPackage:
        for loaded in self.load_all():
            if loaded.package.orchestrator_id == orchestrator_id:
                return loaded
        raise ValueError("unsupported orchestrator")

    def _load_manifest(self, manifest_path: Path) -> LoadedOrchestratorPackage:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        package_dir = manifest_path.parent
        mode = str(payload.get("mode") or "")
        entry = payload.get("entry")
        required_files = ["ORCHESTRATOR.md", "contract.schema.json", "policy.md", "artifact_rules.json", "examples", "tests"]
        if mode == "policy_interpreted":
            required_files.append("prompt.md")
        elif mode == "local_runner":
            required_files.append(str(entry or "runner.py"))
        elif mode == "remote_service":
            required_files.append(str(entry or "remote.json"))
        else:
            raise RuntimeError(f"unsupported orchestrator mode in {manifest_path}: {mode}")

        missing = [item for item in required_files if not (package_dir / item).exists()]
        if missing:
            raise RuntimeError(f"orchestrator package {package_dir.name} missing required files: {', '.join(missing)}")

        capabilities = payload.get("capabilities") or []
        if not isinstance(capabilities, list):
            raise RuntimeError(f"orchestrator capabilities must be a list: {manifest_path}")
        requires = payload.get("requires") or {}
        if not isinstance(requires, dict):
            raise RuntimeError(f"orchestrator requires must be an object: {manifest_path}")

        package = OrchestratorPackage(
            orchestrator_id=str(payload["id"]),
            name=str(payload["name"]),
            version=str(payload["version"]),
            stage=str(payload["stage"]),
            document_type=str(payload["document_type"]),
            contract=str(payload["contract"]),
            mode=mode,
            status=str(payload.get("status") or "available"),
            description=str(payload.get("description") or ""),
            entry=str(entry) if entry is not None else None,
            capabilities=tuple(str(item) for item in capabilities),
            requires=requires,
            package_path=str(package_dir.relative_to(REPO_ROOT)),
            priority=int(payload.get("priority") or 100),
        )
        return LoadedOrchestratorPackage(
            package=package,
            root_path=package_dir,
            manifest=payload,
            orchestrator_text=(package_dir / "ORCHESTRATOR.md").read_text(encoding="utf-8"),
            policy_text=(package_dir / "policy.md").read_text(encoding="utf-8"),
            prompt_text=(package_dir / "prompt.md").read_text(encoding="utf-8")
            if (package_dir / "prompt.md").exists()
            else "",
            artifact_rules=json.loads((package_dir / "artifact_rules.json").read_text(encoding="utf-8"))
            if (package_dir / "artifact_rules.json").exists()
            else {"clauses": {}, "defaults": {}},
            contract_schema=json.loads((package_dir / "contract.schema.json").read_text(encoding="utf-8")),
            entry_path=str(package_dir / str(entry)) if entry else None,
        )

    @staticmethod
    def _duplicated_ids(values: list[str]) -> str | None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                return value
            seen.add(value)
        return None


class OrchestratorRegistry:
    def __init__(self, root: Path = DEFAULT_ORCHESTRATOR_ROOT) -> None:
        self.loader = OrchestratorPackageLoader(root)
        self._packages = {loaded.package.orchestrator_id: loaded for loaded in self.loader.load_all()}

    def list_packages(self) -> list[OrchestratorPackage]:
        return [loaded.package for loaded in sorted(self._packages.values(), key=lambda item: (item.package.priority, item.package.orchestrator_id))]

    def list_loaded_packages(self) -> list[LoadedOrchestratorPackage]:
        return sorted(self._packages.values(), key=lambda item: (item.package.priority, item.package.orchestrator_id))

    def get(self, orchestrator_id: str) -> OrchestratorPackage | None:
        loaded = self._packages.get(orchestrator_id)
        return loaded.package if loaded else None

    def get_loaded(self, orchestrator_id: str) -> LoadedOrchestratorPackage | None:
        return self._packages.get(orchestrator_id)

    def require(self, orchestrator_id: str) -> OrchestratorPackage:
        package = self.get(orchestrator_id)
        if package is None:
            raise ValueError("unsupported orchestrator")
        return package

    def require_loaded(self, orchestrator_id: str) -> LoadedOrchestratorPackage:
        loaded = self.get_loaded(orchestrator_id)
        if loaded is None:
            raise ValueError("unsupported orchestrator")
        return loaded


@lru_cache(maxsize=1)
def get_orchestrator_registry() -> OrchestratorRegistry:
    return OrchestratorRegistry()
