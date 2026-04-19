import json
from pathlib import Path

from app.tool_hub.generators.query_table_widget import render_query_table_widget
from app.tool_hub.models import ToolRecipe


def test_query_table_widget_generator_writes_component_bundle_and_manifest(tmp_path: Path) -> None:
    recipe = ToolRecipe(
        recipe_id="recipe-query-table",
        component_name="QueryTableWidget",
        package_name="@p4-tools/query-table-widget",
        props_schema={
            "columns": {"type": "array"},
            "filters": {"type": "array"},
            "fetcher": {"type": "function"},
        },
        peer_dependencies={"react": "^18.0.0", "antd": "^5.0.0"},
        host_constraints={"frontend_framework": "react", "ui_library": "antd"},
    )

    bundle = render_query_table_widget(recipe, tmp_path / "artifact-query-table")

    component_path = Path(bundle.artifact_root) / "src" / "QueryTableWidget.tsx"
    example_path = Path(bundle.artifact_root) / "example" / "HostPage.tsx"
    manifest_path = Path(bundle.manifest_path)

    assert component_path.exists()
    assert example_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["tool_form_id"] == "frontend_component"
    assert manifest["packaging_type"] == "source_package"
    assert manifest["integration_mode"] == "import_component"
    assert manifest["dependency_policy"] == "peer"
    assert manifest["runtime_dependencies"] == ["react@18", "antd@5"]
    assert manifest["import_specifier"] == "@p4-tools/query-table-widget"
