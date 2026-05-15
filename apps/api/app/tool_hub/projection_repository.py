from __future__ import annotations

import json
from pathlib import Path
from threading import Lock, RLock
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.tool_hub.query_models import (
    EvolutionWorkspaceProjection,
    OverviewProjection,
    P4ObjectWorkbenchProjection,
    ToolListProjection,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ToolHubProjectionRepository:
    _root_locks: dict[str, RLock] = {}
    _root_locks_guard = Lock()

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        root_key = str(self.root.resolve())
        with self._root_locks_guard:
            if root_key not in self._root_locks:
                self._root_locks[root_key] = RLock()
            self._lock = self._root_locks[root_key]
        self.projections_dir = self.root / "projections"
        self.overview_dir = self.projections_dir / "overview"
        self.registry_dir = self.projections_dir / "registry"
        self.evolution_dir = self.projections_dir / "evolution"
        self.workbench_dir = self.projections_dir / "workbench"
        for directory in (self.projections_dir, self.overview_dir, self.registry_dir, self.evolution_dir, self.workbench_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def get_overview_projection(self) -> OverviewProjection | None:
        return self._read_model(self.overview_dir / "default.json", OverviewProjection)

    def save_overview_projection(self, projection: OverviewProjection) -> OverviewProjection:
        self._write_json(self.overview_dir / "default.json", projection.model_dump(mode="json"))
        return projection

    def get_tool_list_projection(self) -> ToolListProjection | None:
        return self._read_model(self.registry_dir / "tool_list.json", ToolListProjection)

    def save_tool_list_projection(self, projection: ToolListProjection) -> ToolListProjection:
        self._write_json(self.registry_dir / "tool_list.json", projection.model_dump(mode="json"))
        return projection

    def get_evolution_workspace_projection(self) -> EvolutionWorkspaceProjection | None:
        return self._read_model(self.evolution_dir / "workspace.json", EvolutionWorkspaceProjection)

    def save_evolution_workspace_projection(
        self,
        projection: EvolutionWorkspaceProjection,
    ) -> EvolutionWorkspaceProjection:
        self._write_json(self.evolution_dir / "workspace.json", projection.model_dump(mode="json"))
        return projection

    def get_object_workbench_projection(self) -> P4ObjectWorkbenchProjection | None:
        return self._read_model(self.workbench_dir / "object_view.json", P4ObjectWorkbenchProjection)

    def save_object_workbench_projection(self, projection: P4ObjectWorkbenchProjection) -> P4ObjectWorkbenchProjection:
        self._write_json(self.workbench_dir / "object_view.json", projection.model_dump(mode="json"))
        return projection

    def has_core_projections(self) -> bool:
        with self._lock:
            return (
                (self.overview_dir / "default.json").exists()
                and (self.registry_dir / "tool_list.json").exists()
                and (self.evolution_dir / "workspace.json").exists()
                and (self.workbench_dir / "object_view.json").exists()
            )

    def clear_all(self) -> int:
        with self._lock:
            removed = 0
            for directory in (self.overview_dir, self.registry_dir, self.evolution_dir, self.workbench_dir):
                for path in directory.glob("*.json"):
                    path.unlink(missing_ok=True)
                    removed += 1
            return removed

    def _read_model(self, path: Path, model_type: type[ModelT]) -> ModelT | None:
        with self._lock:
            if not path.exists():
                return None
            return model_type.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _write_json(self, path: Path, payload: dict) -> None:
        with self._lock:
            temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
            temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(path)
