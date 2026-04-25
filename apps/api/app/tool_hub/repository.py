from __future__ import annotations

import json
from pathlib import Path
from threading import Lock, RLock
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.tool_hub.models import (
    EvolutionChangeSet,
    EvolutionInspectionConfig,
    EvolutionRollbackRecord,
    EvolutionRuntimeState,
    EvolutionTask,
    EvolutionRun,
    ToolDefinition,
    ToolDemandItem,
    ToolDemandSheet,
    ToolManufacturePlan,
    ToolMatchRun,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ToolHubRepository:
    _root_locks: dict[str, RLock] = {}
    _root_locks_guard = Lock()

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        root_key = str(self.root.resolve())
        with self._root_locks_guard:
            if root_key not in self._root_locks:
                self._root_locks[root_key] = RLock()
            self._lock = self._root_locks[root_key]
        self.tools_dir = self.root / "tools"
        self.demand_sheets_dir = self.root / "demand_sheets"
        self.demand_items_dir = self.root / "demand_items"
        self.manufacture_plans_dir = self.root / "manufacture_plans"
        self.match_runs_dir = self.root / "runs" / "match"
        self.evolution_runs_dir = self.root / "runs" / "evolution"
        self.evolution_root_dir = self.root / "evolution"
        self.evolution_config_dir = self.evolution_root_dir / "config"
        self.evolution_tasks_dir = self.evolution_root_dir / "tasks"
        self.evolution_change_sets_dir = self.evolution_root_dir / "change_sets"
        self.evolution_rollbacks_dir = self.evolution_root_dir / "rollbacks"
        self.catalogs_dir = self.root / "catalogs"
        self.runtime_dir = self.root / "runtime"
        self.runtime_jobs_dir = self.runtime_dir / "jobs"
        self.runtime_execution_records_dir = self.runtime_dir / "execution_records"
        for directory in (
            self.tools_dir,
            self.demand_sheets_dir,
            self.demand_items_dir,
            self.manufacture_plans_dir,
            self.match_runs_dir,
            self.evolution_runs_dir,
            self.evolution_root_dir,
            self.evolution_config_dir,
            self.evolution_tasks_dir,
            self.evolution_change_sets_dir,
            self.evolution_rollbacks_dir,
            self.catalogs_dir,
            self.runtime_dir,
            self.runtime_jobs_dir,
            self.runtime_execution_records_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def list_tools(self) -> list[ToolDefinition]:
        with self._lock:
            return sorted(
                self._read_models(self.tools_dir, ToolDefinition),
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        with self._lock:
            path = self.tools_dir / f"{tool_id}.json"
            if not path.exists():
                return None
            return ToolDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        with self._lock:
            self._write_json(self.tools_dir / f"{tool.tool_id}.json", tool.model_dump(mode="json"))
            return tool

    def delete_tool(self, tool_id: str) -> bool:
        with self._lock:
            path = self.tools_dir / f"{tool_id}.json"
            if not path.exists():
                return False
            path.unlink(missing_ok=True)
            return True

    def list_demand_sheets(self) -> list[ToolDemandSheet]:
        with self._lock:
            return sorted(
                self._read_models(self.demand_sheets_dir, ToolDemandSheet),
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def get_demand_sheet(self, sheet_id: str) -> ToolDemandSheet | None:
        with self._lock:
            path = self.demand_sheets_dir / f"{sheet_id}.json"
            if not path.exists():
                return None
            return ToolDemandSheet.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_demand_sheet(self, sheet: ToolDemandSheet) -> ToolDemandSheet:
        with self._lock:
            self._write_json(self.demand_sheets_dir / f"{sheet.sheet_id}.json", sheet.model_dump(mode="json"))
            return sheet

    def list_demand_items(self, sheet_id: str | None = None) -> list[ToolDemandItem]:
        with self._lock:
            items = sorted(
                self._read_models(self.demand_items_dir, ToolDemandItem),
                key=lambda item: item.updated_at,
                reverse=True,
            )
            if sheet_id is None:
                return items
            return [item for item in items if item.sheet_id == sheet_id]

    def get_demand_item(self, item_id: str) -> ToolDemandItem | None:
        with self._lock:
            path = self.demand_items_dir / f"{item_id}.json"
            if not path.exists():
                return None
            return ToolDemandItem.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_demand_item(self, item: ToolDemandItem) -> ToolDemandItem:
        with self._lock:
            self._write_json(self.demand_items_dir / f"{item.item_id}.json", item.model_dump(mode="json"))
            return item

    def list_manufacture_plans(self) -> list[ToolManufacturePlan]:
        with self._lock:
            return sorted(
                self._read_models(self.manufacture_plans_dir, ToolManufacturePlan),
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def get_manufacture_plan(self, item_id: str) -> ToolManufacturePlan | None:
        with self._lock:
            path = self.manufacture_plans_dir / f"{item_id}.json"
            if not path.exists():
                return None
            return ToolManufacturePlan.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_manufacture_plan(self, plan: ToolManufacturePlan) -> ToolManufacturePlan:
        with self._lock:
            self._write_json(self.manufacture_plans_dir / f"{plan.item_id}.json", plan.model_dump(mode="json"))
            return plan

    def clear_demand_chain_runtime(self) -> tuple[int, int, int]:
        with self._lock:
            return (
                self._delete_json_files(self.demand_sheets_dir),
                self._delete_json_files(self.demand_items_dir),
                self._delete_json_files(self.manufacture_plans_dir),
            )

    def clear_tool_runtime(self) -> tuple[int, int, int]:
        with self._lock:
            self._delete_json_files(self.evolution_tasks_dir)
            self._delete_json_files(self.evolution_change_sets_dir)
            self._delete_json_files(self.evolution_rollbacks_dir)
            return (
                self._delete_json_files(self.tools_dir),
                self._delete_json_files(self.match_runs_dir),
                self._delete_json_files(self.evolution_runs_dir),
            )

    def list_match_runs(self) -> list[ToolMatchRun]:
        with self._lock:
            return sorted(
                self._read_models(self.match_runs_dir, ToolMatchRun),
                key=lambda item: item.created_at,
                reverse=True,
            )

    def save_match_run(self, run: ToolMatchRun) -> ToolMatchRun:
        with self._lock:
            self._write_json(self.match_runs_dir / f"{run.run_id}.json", run.model_dump(mode="json"))
            return run

    def list_evolution_runs(self) -> list[EvolutionRun]:
        with self._lock:
            return sorted(
                self._read_models(self.evolution_runs_dir, EvolutionRun),
                key=lambda item: item.created_at,
                reverse=True,
            )

    def save_evolution_run(self, run: EvolutionRun) -> EvolutionRun:
        with self._lock:
            self._write_json(self.evolution_runs_dir / f"{run.run_id}.json", run.model_dump(mode="json"))
            return run

    def get_evolution_run(self, run_id: str) -> EvolutionRun | None:
        with self._lock:
            path = self.evolution_runs_dir / f"{run_id}.json"
            if not path.exists():
                return None
            return EvolutionRun.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def get_evolution_finding(self, finding_id: str) -> tuple[EvolutionRun, int] | None:
        with self._lock:
            for run in self.list_evolution_runs():
                for index, finding in enumerate(run.findings):
                    if finding.finding_id == finding_id:
                        return run, index
        return None

    def get_evolution_config(self) -> EvolutionInspectionConfig:
        with self._lock:
            path = self.evolution_config_dir / "default.json"
            if not path.exists():
                config = EvolutionInspectionConfig()
                self._write_json(path, config.model_dump(mode="json"))
                return config
            return EvolutionInspectionConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_evolution_config(self, config: EvolutionInspectionConfig) -> EvolutionInspectionConfig:
        with self._lock:
            self._write_json(self.evolution_config_dir / "default.json", config.model_dump(mode="json"))
            return config

    def list_evolution_tasks(self) -> list[EvolutionTask]:
        with self._lock:
            return sorted(
                self._read_models(self.evolution_tasks_dir, EvolutionTask),
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def get_evolution_task(self, task_id: str) -> EvolutionTask | None:
        with self._lock:
            path = self.evolution_tasks_dir / f"{task_id}.json"
            if not path.exists():
                return None
            return EvolutionTask.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_evolution_task(self, task: EvolutionTask) -> EvolutionTask:
        with self._lock:
            self._write_json(self.evolution_tasks_dir / f"{task.task_id}.json", task.model_dump(mode="json"))
            return task

    def list_evolution_change_sets(self, task_id: str | None = None) -> list[EvolutionChangeSet]:
        with self._lock:
            items = sorted(
                self._read_models(self.evolution_change_sets_dir, EvolutionChangeSet),
                key=lambda item: item.applied_at,
                reverse=True,
            )
            if task_id is None:
                return items
            return [item for item in items if item.task_id == task_id]

    def save_evolution_change_set(self, change_set: EvolutionChangeSet) -> EvolutionChangeSet:
        with self._lock:
            self._write_json(
                self.evolution_change_sets_dir / f"{change_set.change_set_id}.json",
                change_set.model_dump(mode="json"),
            )
            return change_set

    def save_evolution_rollback(self, rollback: EvolutionRollbackRecord) -> EvolutionRollbackRecord:
        with self._lock:
            self._write_json(
                self.evolution_rollbacks_dir / f"{rollback.rollback_id}.json",
                rollback.model_dump(mode="json"),
            )
            return rollback

    def get_runtime_state(self) -> EvolutionRuntimeState:
        with self._lock:
            path = self.runtime_dir / "state.json"
            if not path.exists():
                state = EvolutionRuntimeState()
                self._write_json(path, state.model_dump(mode="json"))
                return state
            return EvolutionRuntimeState.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_runtime_state(self, state: EvolutionRuntimeState) -> EvolutionRuntimeState:
        with self._lock:
            self._write_json(self.runtime_dir / "state.json", state.model_dump(mode="json"))
            return state

    def _read_models(self, directory: Path, model_type: type[ModelT]) -> list[ModelT]:
        items: list[ModelT] = []
        for path in sorted(directory.glob("*.json")):
            items.append(model_type.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items

    def _write_json(self, path: Path, payload: dict) -> None:
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)

    def _delete_json_files(self, directory: Path) -> int:
        count = 0
        for path in directory.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        return count
