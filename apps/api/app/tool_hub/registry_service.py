from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from app.tool_hub.models import (
    ToolDefinition,
    ToolDefinitionWrite,
    ToolRegistryDeleteResult,
    ToolRegistryTestingClearResult,
    now_iso,
)

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class RegistryService:
    def __init__(self, hub: "ToolHubService") -> None:
        self.hub = hub
        self.repository = hub.repository

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        self.hub._ensure_demo_data()
        return self.repository.get_tool(tool_id)

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        self.hub._ensure_demo_data()
        self.hub._ensure_slug_unique(payload.slug)
        tool = ToolDefinition(
            tool_id=f"tool-{uuid4().hex[:12]}",
            **payload.model_dump(mode="json"),
        )
        saved = self.repository.save_tool(tool)
        self.hub.mark_evolution_dirty()
        return saved

    def update_tool(self, tool_id: str, payload: ToolDefinitionWrite) -> ToolDefinition | None:
        existing = self.repository.get_tool(tool_id)
        if existing is None:
            return None
        self.hub._ensure_slug_unique(payload.slug, ignore_tool_id=tool_id)
        updated = ToolDefinition.model_validate(
            {
                **existing.model_dump(mode="json"),
                **payload.model_dump(mode="json"),
                "tool_id": tool_id,
                "created_at": existing.created_at,
                "updated_at": now_iso(),
            }
        )
        saved = self.repository.save_tool(updated)
        self.hub.mark_evolution_dirty()
        return saved

    def delete_tool(self, tool_id: str) -> ToolRegistryDeleteResult | None:
        self.hub._ensure_demo_data()
        tool = self.repository.get_tool(tool_id)
        if tool is None:
            return None
        self.hub._ensure_tool_is_not_referenced(tool_id)
        self.repository.delete_tool(tool_id)
        self.hub.mark_evolution_dirty()
        return ToolRegistryDeleteResult(
            removed_tool_id=tool_id,
            remaining_tool_count=len(self.repository.list_tools()),
        )

    def clear_tool_registry_for_testing(self) -> ToolRegistryTestingClearResult:
        self.hub._mark_demo_seed_initialized()
        cleared_tool_count, cleared_match_run_count, cleared_evolution_run_count = (
            self.repository.clear_tool_runtime()
        )
        self.hub.mark_evolution_dirty()
        return ToolRegistryTestingClearResult(
            cleared_tool_count=cleared_tool_count,
            cleared_match_run_count=cleared_match_run_count,
            cleared_evolution_run_count=cleared_evolution_run_count,
        )
