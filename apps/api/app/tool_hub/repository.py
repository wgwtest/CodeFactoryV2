from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.tool_hub.models import (
    EvolutionRun,
    ToolDefinition,
    ToolDemandItem,
    ToolDemandSheet,
    ToolManufacturePlan,
    ToolMatchRun,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ToolHubRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.tools_dir = self.root / "tools"
        self.demand_sheets_dir = self.root / "demand_sheets"
        self.demand_items_dir = self.root / "demand_items"
        self.manufacture_plans_dir = self.root / "manufacture_plans"
        self.match_runs_dir = self.root / "runs" / "match"
        self.evolution_runs_dir = self.root / "runs" / "evolution"
        self.catalogs_dir = self.root / "catalogs"
        for directory in (
            self.tools_dir,
            self.demand_sheets_dir,
            self.demand_items_dir,
            self.manufacture_plans_dir,
            self.match_runs_dir,
            self.evolution_runs_dir,
            self.catalogs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def list_tools(self) -> list[ToolDefinition]:
        return sorted(
            self._read_models(self.tools_dir, ToolDefinition),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        path = self.tools_dir / f"{tool_id}.json"
        if not path.exists():
            return None
        return ToolDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        self._write_json(self.tools_dir / f"{tool.tool_id}.json", tool.model_dump(mode="json"))
        return tool

    def list_demand_sheets(self) -> list[ToolDemandSheet]:
        return sorted(
            self._read_models(self.demand_sheets_dir, ToolDemandSheet),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def get_demand_sheet(self, sheet_id: str) -> ToolDemandSheet | None:
        path = self.demand_sheets_dir / f"{sheet_id}.json"
        if not path.exists():
            return None
        return ToolDemandSheet.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_demand_sheet(self, sheet: ToolDemandSheet) -> ToolDemandSheet:
        self._write_json(self.demand_sheets_dir / f"{sheet.sheet_id}.json", sheet.model_dump(mode="json"))
        return sheet

    def list_demand_items(self, sheet_id: str | None = None) -> list[ToolDemandItem]:
        items = sorted(
            self._read_models(self.demand_items_dir, ToolDemandItem),
            key=lambda item: item.updated_at,
            reverse=True,
        )
        if sheet_id is None:
            return items
        return [item for item in items if item.sheet_id == sheet_id]

    def get_demand_item(self, item_id: str) -> ToolDemandItem | None:
        path = self.demand_items_dir / f"{item_id}.json"
        if not path.exists():
            return None
        return ToolDemandItem.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_demand_item(self, item: ToolDemandItem) -> ToolDemandItem:
        self._write_json(self.demand_items_dir / f"{item.item_id}.json", item.model_dump(mode="json"))
        return item

    def get_manufacture_plan(self, item_id: str) -> ToolManufacturePlan | None:
        path = self.manufacture_plans_dir / f"{item_id}.json"
        if not path.exists():
            return None
        return ToolManufacturePlan.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_manufacture_plan(self, plan: ToolManufacturePlan) -> ToolManufacturePlan:
        self._write_json(self.manufacture_plans_dir / f"{plan.item_id}.json", plan.model_dump(mode="json"))
        return plan

    def list_match_runs(self) -> list[ToolMatchRun]:
        return sorted(
            self._read_models(self.match_runs_dir, ToolMatchRun),
            key=lambda item: item.created_at,
            reverse=True,
        )

    def save_match_run(self, run: ToolMatchRun) -> ToolMatchRun:
        self._write_json(self.match_runs_dir / f"{run.run_id}.json", run.model_dump(mode="json"))
        return run

    def list_evolution_runs(self) -> list[EvolutionRun]:
        return sorted(
            self._read_models(self.evolution_runs_dir, EvolutionRun),
            key=lambda item: item.created_at,
            reverse=True,
        )

    def save_evolution_run(self, run: EvolutionRun) -> EvolutionRun:
        self._write_json(self.evolution_runs_dir / f"{run.run_id}.json", run.model_dump(mode="json"))
        return run

    def _read_models(self, directory: Path, model_type: type[ModelT]) -> list[ModelT]:
        items: list[ModelT] = []
        for path in sorted(directory.glob("*.json")):
            items.append(model_type.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
