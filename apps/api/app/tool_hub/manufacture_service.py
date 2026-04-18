from __future__ import annotations

from typing import TYPE_CHECKING

from app.tool_hub.models import ToolFetchManifest, ToolManufacturePlanEnvelope, ToolManufacturePlanView

TERMINAL_SHEET_LIFECYCLE_STATUSES = {"rejected", "withdrawn", "closed"}

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class ManufactureService:
    def __init__(self, hub: "ToolHubService") -> None:
        self.hub = hub
        self.repository = hub.repository

    def list_manufacture_plans(self) -> ToolManufacturePlanEnvelope:
        items: list[ToolManufacturePlanView] = []
        for plan in self.repository.list_manufacture_plans():
            item = self.repository.get_demand_item(plan.item_id)
            if item is None:
                continue
            items.append(self.hub._build_manufacture_plan_view(plan, item))
        return ToolManufacturePlanEnvelope(items=items)

    def run_executor_cycle(self) -> None:
        for plan in self.repository.list_manufacture_plans():
            if plan.status not in {"manufacturing_pending", "manufacturing_in_progress"}:
                continue
            item = self.repository.get_demand_item(plan.item_id)
            if item is None:
                continue
            sheet = self.repository.get_demand_sheet(item.sheet_id)
            if sheet is not None and sheet.lifecycle_status in TERMINAL_SHEET_LIFECYCLE_STATUSES:
                continue
            self.hub._advance_manufacture_plan(plan, item)

    def get_tool_fetch_manifest(self, tool_id: str) -> ToolFetchManifest | None:
        tool = self.repository.get_tool(tool_id)
        if tool is None:
            return None
        return self.hub._build_tool_fetch_manifest_response(tool)
