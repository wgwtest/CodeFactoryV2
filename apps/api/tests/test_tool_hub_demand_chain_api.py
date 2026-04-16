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
    "entity_count": 1,
    "event_count": 0,
    "process_count": 1
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
    )
    app.dependency_overrides[get_tool_hub_service] = lambda: service
    return TestClient(app)


def _build_component_sheet_payload(component_name: str, component_code: str) -> dict:
    return {
        "sheet_name": "模拟蓝军叶子工具需求单",
        "source": {
            "phase": "p3_simulator",
            "producer": "mock_blue_force_generator",
            "business_case": "simulated_blue_force",
            "scenario_id": "blue-force-sim-001",
            "scenario_name": "模拟蓝军对抗推演一期",
        },
        "requested_by": "P3",
        "notes": "用于验证 P3-sim -> P4 -> P5-sim 闭环",
        "root_node": {
            "node_id": "sys-blue-force",
            "node_type": "system",
            "node_name": "模拟蓝军系统",
            "node_code": "SYS-BLUE-FORCE",
            "business_domain_id": "simulated_blue_force",
            "children": [
                {
                    "node_id": "subsys-blue-force",
                    "node_type": "subsystem",
                    "node_name": "蓝军编组",
                    "node_code": "SUBSYS-BLUE-FORCE",
                    "business_domain_id": "simulated_blue_force",
                    "children": [
                        {
                            "node_id": "subsub-blue-force-structure",
                            "node_type": "sub_subsystem",
                            "node_name": "兵力结构编组",
                            "node_code": "SUBSUB-BLUE-FORCE-STRUCTURE",
                            "business_domain_id": "simulated_blue_force",
                            "children": [
                                {
                                    "node_id": "module-blue-force-tree",
                                    "node_type": "module",
                                    "node_name": "编制树生成",
                                    "node_code": "MODULE-BLUE-FORCE-TREE",
                                    "business_domain_id": "simulated_blue_force",
                                    "children": [
                                        {
                                            "node_id": "component-blue-force-tree-builder",
                                            "node_type": "component",
                                            "node_name": component_name,
                                            "node_code": component_code,
                                            "business_domain_id": "simulated_blue_force",
                                            "children": [],
                                            "component_spec": {
                                                "component_name": component_name,
                                                "component_code": component_code,
                                                "problem_statement": "生成蓝军编组树并输出结构化结果",
                                                "required_input_types": ["force_definition"],
                                                "expected_output_types": ["force_tree"],
                                                "preferred_tool_forms": ["skill"],
                                                "preferred_runtime_platforms": ["agent_runtime"],
                                                "lifecycle_stage_ids": ["solution_design"],
                                                "keywords": ["蓝军", "编组", "树"],
                                                "acceptance_notes": "输出结构化蓝军编组树",
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    }


def _create_matching_tool(client: TestClient) -> str:
    response = client.post(
        "/api/tool-hub/tools",
        json={
            "name": "蓝军编组树构造器",
            "slug": "blue-force-tree-builder",
            "status": "active",
            "summary": "根据兵力定义生成蓝军编组树",
            "problem_statement": "支撑蓝军编组设计阶段的工具匹配",
            "primary_domain_id": "simulated_blue_force",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [
                "domain:simulated_blue_force",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "input:force_definition",
                "output:force_tree",
            ],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["force_definition"],
            "output_types": ["force_tree"],
            "supported_sources": ["manual_input", "frozen_snapshot"],
            "usage_notes": "命中模拟蓝军编组树生成场景",
            "keywords": ["蓝军", "编组", "树"],
            "verification": {
                "status": "verified",
                "last_verified_result": "模拟蓝军样例通过",
                "sample_case_ids": ["blue-force-tree-sample"],
            },
        },
    )
    assert response.status_code == 201
    return response.json()["tool_id"]


def test_create_mock_blue_force_demand_sheet(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    response = client.post("/api/tool-hub/mock-generators/blue-force-demand-sheets")
    assert response.status_code == 201

    payload = response.json()
    assert payload["sheet_id"]
    assert payload["sheet_name"] == "模拟蓝军一期工具需求单"
    assert payload["business_case"] == "simulated_blue_force"
    assert payload["status"] == "accepted"
    assert payload["item_count"] >= 6
    assert payload["root_node"]["node_type"] == "system"
    assert payload["items"][0]["item_id"]


def test_query_demand_sheet_item_progress_and_fetch_manifest_for_existing_tool(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    tool_id = _create_matching_tool(client)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    assert created_payload["item_count"] == 1

    item_id = created_payload["items"][0]["item_id"]
    sheet_id = created_payload["sheet_id"]

    sheet_response = client.get(f"/api/tool-hub/demand-sheets/{sheet_id}")
    assert sheet_response.status_code == 200
    sheet_payload = sheet_response.json()
    assert sheet_payload["sheet_id"] == sheet_id
    assert sheet_payload["matched_existing_count"] == 1

    item_response = client.get(f"/api/tool-hub/demand-items/{item_id}")
    assert item_response.status_code == 200
    item_payload = item_response.json()
    assert item_payload["status"] == "matched_existing"
    assert item_payload["supply_result"]["result_type"] == "existing_tool"
    assert item_payload["supply_result"]["tool_id"] == tool_id
    assert item_payload["supply_result"]["fetch_manifest"]["fetch_path"] == f"/api/tool-hub/tools/{tool_id}/fetch"

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["item_id"] == item_id
    assert progress_payload["status"] == "matched_existing"
    assert progress_payload["result_type"] == "existing_tool"

    fetch_response = client.get(f"/api/tool-hub/tools/{tool_id}/fetch")
    assert fetch_response.status_code == 200
    fetch_payload = fetch_response.json()
    assert fetch_payload["tool_id"] == tool_id
    assert fetch_payload["tool_name"] == "蓝军编组树构造器"
    assert fetch_payload["fetch_type"] == "tool_definition"
    assert fetch_payload["fetch_path"] == f"/api/tool-hub/tools/{tool_id}"


def test_pending_manufacture_item_exposes_progress_query(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    item_id = created_payload["items"][0]["item_id"]

    item_response = client.get(f"/api/tool-hub/demand-items/{item_id}")
    assert item_response.status_code == 200
    item_payload = item_response.json()
    assert item_payload["status"] == "manufacturing_pending"
    assert item_payload["supply_result"]["result_type"] == "pending_manufacture"
    assert item_payload["supply_result"]["progress_query_path"] == f"/api/tool-hub/demand-items/{item_id}/progress"
    assert item_payload["supply_result"]["estimated_ready_in_hours"] > 0

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["item_id"] == item_id
    assert progress_payload["status"] == "manufacturing_pending"
    assert progress_payload["result_type"] == "pending_manufacture"
    assert progress_payload["estimated_ready_in_hours"] > 0
