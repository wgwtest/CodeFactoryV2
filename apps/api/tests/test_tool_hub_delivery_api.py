from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.tool_hub import get_tool_hub_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app
from app.tool_hub.service import ToolHubService


def _write_archive(path: Path) -> None:
    path.write_text(
        """
{
  "summary": {
    "document_count": 1,
    "entity_count": 0,
    "event_count": 0,
    "process_count": 0
  },
  "documents": [],
  "entities": [],
  "events": [],
  "processes": [],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def _build_client(tmp_path: Path) -> TestClient:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")

    app = create_app()
    service = ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=False,
        enable_background_executor=False,
    )
    app.dependency_overrides[get_tool_hub_service] = lambda: service
    return TestClient(app)


def test_frontend_component_build_request_can_complete_and_publish_manifest(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    request_payload = {
        "requested_by": "p3-sim",
        "component_name": "QueryTableWidget",
        "scenario_id": "frontend-query-table-widget",
        "tool_definition": {
            "name": "查询表格元组件",
            "slug": "query-table-widget",
            "status": "draft",
            "summary": "可嵌入宿主的查询表格组件",
            "problem_statement": "复用表格和筛选骨架",
            "primary_domain_id": "cross_domain_shared",
            "tool_form_id": "frontend_component",
            "tool_granularity": "atomic",
            "packaging_type": "source_package",
            "integration_mode": "import_component",
            "dependency_policy": "peer",
            "runtime_dependencies": ["react@18", "antd@5"],
            "runtime_platform_ids": ["web_frontend"],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["query_params", "column_schema"],
            "output_types": ["tsx_component", "delivery_manifest"],
            "supported_sources": ["manual_input"],
            "tags": [],
        },
    }

    created = client.post("/api/tool-hub/build-requests/frontend-components", json=request_payload)
    assert created.status_code == 201
    build_run_id = created.json()["build_run_id"]

    service = client.app.dependency_overrides[get_tool_hub_service]()
    service.runtime_service.run_once()

    build_run = client.get(f"/api/tool-hub/build-runs/{build_run_id}")
    assert build_run.status_code == 200
    assert build_run.json()["status"] == "completed"

    tool_id = build_run.json()["tool_id"]
    manifest = client.get(f"/api/tool-hub/tools/{tool_id}/delivery-manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["integration_mode"] == "import_component"
    assert payload["dependency_policy"] == "peer"
    assert payload["runtime_dependencies"] == ["react@18", "antd@5"]
    assert payload["import_specifier"] == "@p4-tools/query-table-widget"
