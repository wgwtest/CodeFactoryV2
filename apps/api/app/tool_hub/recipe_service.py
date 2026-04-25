from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.tool_hub.models import ToolBuildRequest, ToolRecipe


class ToolRecipeService:
    def __init__(self, *, artifact_root: Path) -> None:
        self.artifact_root = artifact_root

    def create_query_table_widget_recipe(self, request: ToolBuildRequest) -> ToolRecipe:
        payload = request.payload
        component_name = str(payload.get("component_name") or "QueryTableWidget")
        return ToolRecipe(
            recipe_id=f"recipe-{uuid4().hex[:12]}",
            component_name=component_name,
            package_name="@p4-tools/query-table-widget",
            props_schema={
                "columns": {"type": "array"},
                "filters": {"type": "array"},
                "fetcher": {"type": "function"},
            },
            peer_dependencies={"react": "^18.0.0", "antd": "^5.0.0"},
            host_constraints={"frontend_framework": "react", "ui_library": "antd"},
        )
