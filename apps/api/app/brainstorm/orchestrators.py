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


class OrchestratorRegistry:
    def __init__(self, root: Path = DEFAULT_ORCHESTRATOR_ROOT) -> None:
        self.root = root
        self._packages = self._load_packages()

    def list_packages(self) -> list[OrchestratorPackage]:
        return sorted(self._packages.values(), key=lambda item: (item.priority, item.orchestrator_id))

    def get(self, orchestrator_id: str) -> OrchestratorPackage | None:
        return self._packages.get(orchestrator_id)

    def require(self, orchestrator_id: str) -> OrchestratorPackage:
        package = self.get(orchestrator_id)
        if package is None:
            raise ValueError("unsupported orchestrator")
        return package

    def _load_packages(self) -> dict[str, OrchestratorPackage]:
        if not self.root.exists():
            raise RuntimeError(f"orchestrator root does not exist: {self.root}")
        packages: dict[str, OrchestratorPackage] = {}
        for manifest_path in sorted(self.root.glob("*/manifest.json")):
            package = self._load_manifest(manifest_path)
            if package.orchestrator_id in packages:
                raise RuntimeError(f"duplicate orchestrator id: {package.orchestrator_id}")
            packages[package.orchestrator_id] = package
        if not packages:
            raise RuntimeError(f"no orchestrator packages found under: {self.root}")
        return packages

    def _load_manifest(self, manifest_path: Path) -> OrchestratorPackage:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        package_dir = manifest_path.parent
        required_files = ["ORCHESTRATOR.md", "contract.schema.json", "policy.md", "examples", "tests"]
        mode = str(payload.get("mode") or "")
        if mode == "policy_interpreted":
            required_files.append("prompt.md")
        elif mode == "local_runner":
            required_files.append(str(payload.get("entry") or "runner.py"))
        elif mode == "remote_service":
            required_files.append(str(payload.get("entry") or "remote.json"))
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

        return OrchestratorPackage(
            orchestrator_id=str(payload["id"]),
            name=str(payload["name"]),
            version=str(payload["version"]),
            stage=str(payload["stage"]),
            document_type=str(payload["document_type"]),
            contract=str(payload["contract"]),
            mode=mode,
            status=str(payload.get("status") or "available"),
            description=str(payload.get("description") or ""),
            entry=str(payload["entry"]) if payload.get("entry") is not None else None,
            capabilities=tuple(str(item) for item in capabilities),
            requires=requires,
            package_path=str(package_dir.relative_to(REPO_ROOT)),
            priority=int(payload.get("priority") or 100),
        )


@lru_cache(maxsize=1)
def get_orchestrator_registry() -> OrchestratorRegistry:
    return OrchestratorRegistry()
