import json
from pathlib import Path
from time import sleep
from types import SimpleNamespace

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


def _build_service(tmp_path: Path) -> ToolHubService:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")
    return ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=False,
        enable_background_executor=False,
    )


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


def _force_manufacture_plan_ready(tmp_path: Path, item_id: str) -> None:
    plan_path = tmp_path / "tool-hub" / "manufacture_plans" / f"{item_id}.json"
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["status"] = "manufacturing_in_progress"
    payload["estimated_ready_at"] = "2020-01-01T00:00:00+00:00"
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_create_mock_blue_force_demand_sheet_starts_in_pending_review(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    response = client.post("/api/tool-hub/mock-generators/blue-force-demand-sheets")
    assert response.status_code == 201

    payload = response.json()
    assert payload["sheet_id"]
    assert payload["sheet_name"] == "模拟蓝军一期工具需求单"
    assert payload["business_case"] == "simulated_blue_force"
    assert payload["lifecycle_status"] == "accepted"
    assert payload["review_status"] == "pending_review"
    assert payload["delivery_status"] == "not_delivered"
    assert payload["pending_review_count"] == payload["item_count"]
    assert payload["approved_delivery_count"] == 0
    assert payload["approved_manufacture_count"] == 0
    assert payload["rejected_item_count"] == 0
    assert payload["item_count"] >= 6
    first_item = payload["items"][0]
    assert first_item["review_status"] == "pending_review"
    assert first_item["recommendation_type"] in {"existing_tool", "manufacture_candidate", "insufficient_info"}
    assert first_item["supply_result"] is None


def test_mock_generators_support_multiple_scenarios(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    navigation_response = client.post("/api/tool-hub/mock-generators/demand-sheets/navigation_planning")
    assert navigation_response.status_code == 201
    navigation_payload = navigation_response.json()
    assert navigation_payload["business_case"] == "navigation_planning"
    assert navigation_payload["sheet_name"] == "导航规划一期工具需求单"
    assert navigation_payload["items"][0]["component_name"]

    governance_response = client.post("/api/tool-hub/mock-generators/demand-sheets/data_governance")
    assert governance_response.status_code == 201
    governance_payload = governance_response.json()
    assert governance_payload["business_case"] == "data_governance"
    assert governance_payload["sheet_name"] == "数据治理一期工具需求单"
    assert governance_payload["items"][0]["component_name"]


def test_simulation_profiles_expand_to_seconds_minutes_and_hours(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    durations_by_profile: dict[str, int] = {}
    for suffix in range(128):
        profile, duration = service._resolve_simulation_profile(
            SimpleNamespace(
                component_code="COMP-BLUE-FORCE-TREE-BUILDER",
                item_id=f"item-{suffix}",
            )
        )
        durations_by_profile.setdefault(profile, duration)
        if len(durations_by_profile) == 3:
            break

    assert set(durations_by_profile) == {"fast", "normal", "slow"}
    assert 5 <= durations_by_profile["fast"] <= 300
    assert 300 <= durations_by_profile["normal"] <= 3600
    assert 3600 <= durations_by_profile["slow"] <= 7200


def test_suggested_poll_interval_scales_with_simulation_duration(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    assert service._resolve_suggested_poll_after_seconds(5) == 5
    assert service._resolve_suggested_poll_after_seconds(600) == 60
    assert service._resolve_suggested_poll_after_seconds(7200) == 300


def test_review_can_approve_existing_tool_for_direct_delivery(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    tool_id = _create_matching_tool(client)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    item = created_payload["items"][0]
    item_id = item["item_id"]
    sheet_id = created_payload["sheet_id"]

    assert item["review_status"] == "pending_review"
    assert item["recommendation_type"] == "existing_tool"
    assert item["recommended_tool_id"] == tool_id
    assert item["supply_result"] is None

    review_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_delivery",
            "importance_score": 5,
            "urgency_score": 4,
            "rationality_verdict": "合理",
            "review_comment": "已有合适工具，直接交付。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert review_response.status_code == 200
    reviewed_item = review_response.json()
    assert reviewed_item["review_status"] == "approved_delivery"
    assert reviewed_item["importance_score"] == 5
    assert reviewed_item["supply_result"]["result_type"] == "existing_tool"
    assert reviewed_item["supply_result"]["tool_ref"] == tool_id
    assert reviewed_item["supply_result"]["fetch_interface"]["entrypoint_locator"] == (
        f"/api/tool-hub/tools/{tool_id}/fetch"
    )

    sheet_response = client.get(f"/api/tool-hub/demand-sheets/{sheet_id}")
    assert sheet_response.status_code == 200
    sheet_payload = sheet_response.json()
    assert sheet_payload["review_status"] == "reviewed"
    assert sheet_payload["delivery_status"] == "delivered"
    assert sheet_payload["approved_delivery_count"] == 1
    assert sheet_payload["ready_for_fetch_count"] == 1

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["item_id"] == item_id
    assert progress_payload["status"] == "matched_existing"
    assert progress_payload["sheet_lifecycle_status"] == "accepted"
    assert progress_payload["sheet_review_status"] == "reviewed"
    assert progress_payload["sheet_delivery_status"] == "delivered"
    assert progress_payload["result_type"] == "existing_tool"
    assert progress_payload["fetch_interface"]["entrypoint_locator"] == f"/api/tool-hub/tools/{tool_id}/fetch"

    fetch_response = client.get(f"/api/tool-hub/tools/{tool_id}/fetch")
    assert fetch_response.status_code == 200
    fetch_payload = fetch_response.json()
    assert fetch_payload["tool_id"] == tool_id
    assert fetch_payload["entrypoint_type"] == "descriptor"
    assert fetch_payload["contract_version"] == "p4.fetch.v2"
    assert fetch_payload["entrypoint_locator"] == "tool://blue-force-tree-builder"


def test_tool_delete_is_refused_when_demand_chain_still_references_it(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    tool_id = _create_matching_tool(client)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    item_id = created.json()["items"][0]["item_id"]

    review_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_delivery",
            "importance_score": 5,
            "urgency_score": 4,
            "rationality_verdict": "合理",
            "review_comment": "已有合适工具，直接交付。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert review_response.status_code == 200

    delete_response = client.delete(f"/api/tool-hub/tools/{tool_id}")
    assert delete_response.status_code == 400
    assert "referenced" in delete_response.json()["detail"]


def test_review_can_approve_manufacture_then_progress_to_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    item = created_payload["items"][0]
    item_id = item["item_id"]
    sheet_id = created_payload["sheet_id"]

    assert item["review_status"] == "pending_review"
    assert item["recommendation_type"] == "manufacture_candidate"
    assert item["supply_result"] is None

    review_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_manufacture",
            "importance_score": 4,
            "urgency_score": 5,
            "rationality_verdict": "合理",
            "review_comment": "当前无现成工具，批准进入研制。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert review_response.status_code == 200
    reviewed_item = review_response.json()
    assert reviewed_item["review_status"] == "approved_manufacture"
    assert reviewed_item["processing_status"] == "manufacturing_pending"
    assert reviewed_item["supply_result"]["result_type"] == "pending_manufacture"
    assert reviewed_item["supply_result"]["progress_query_interface"] == (
        f"/api/tool-hub/demand-items/{item_id}/progress"
    )
    assert reviewed_item["supply_result"]["estimated_ready_at"]

    sheet_response = client.get(f"/api/tool-hub/demand-sheets/{sheet_id}")
    assert sheet_response.status_code == 200
    sheet_payload = sheet_response.json()
    assert sheet_payload["review_status"] == "reviewed"
    assert sheet_payload["delivery_status"] == "not_delivered"
    assert sheet_payload["approved_manufacture_count"] == 1
    assert sheet_payload["manufacturing_count"] == 1

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["status"] in {"manufacturing_pending", "manufacturing_in_progress"}
    assert progress_payload["result_type"] == "pending_manufacture"
    assert progress_payload["estimated_ready_at"]

    _force_manufacture_plan_ready(tmp_path, item_id)
    sleep(0.2)

    ready_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["status"] == "ready_for_fetch"
    assert ready_payload["result_type"] == "manufactured_tool"
    assert ready_payload["fetch_interface"]["entrypoint_locator"].startswith("/api/tool-hub/tools/tool-")

    refreshed_sheet = client.get(f"/api/tool-hub/demand-sheets/{sheet_id}")
    assert refreshed_sheet.status_code == 200
    refreshed_sheet_payload = refreshed_sheet.json()
    assert refreshed_sheet_payload["delivery_status"] == "delivered"
    assert refreshed_sheet_payload["ready_for_fetch_count"] == 1


def test_background_executor_can_finish_manufacture_without_progress_queries(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    item_id = created.json()["items"][0]["item_id"]

    review_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_manufacture",
            "importance_score": 4,
            "urgency_score": 5,
            "rationality_verdict": "合理",
            "review_comment": "当前无现成工具，批准进入研制。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert review_response.status_code == 200

    _force_manufacture_plan_ready(tmp_path, item_id)
    sleep(0.2)

    item_response = client.get(f"/api/tool-hub/demand-items/{item_id}")
    assert item_response.status_code == 200
    item_payload = item_response.json()
    assert item_payload["processing_status"] == "ready_for_fetch"
    assert item_payload["supply_result"]["result_type"] == "manufactured_tool"
    assert item_payload["supply_result"]["fetch_interface"]["entrypoint_locator"].startswith("/api/tool-hub/tools/tool-")


def test_registry_can_read_simulated_manufacture_queue(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    item_id = created.json()["items"][0]["item_id"]

    review_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_manufacture",
            "importance_score": 4,
            "urgency_score": 5,
            "rationality_verdict": "合理",
            "review_comment": "当前无现成工具，批准进入研制。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert review_response.status_code == 200

    queue_response = client.get("/api/tool-hub/manufacture-plans")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    assert queue_payload["items"]
    assert queue_payload["items"][0]["item_id"] == item_id
    assert queue_payload["items"][0]["status"] in {"manufacturing_pending", "manufacturing_in_progress"}
    assert queue_payload["items"][0]["planned_tool_name"] == "蓝军编组树构造器"


def test_p3_can_withdraw_sheet_and_freeze_manufacture_progress(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    sheet_id = created_payload["sheet_id"]
    item_id = created_payload["items"][0]["item_id"]

    approve_response = client.post(
        f"/api/tool-hub/demand-items/{item_id}/review",
        json={
            "decision": "approve_manufacture",
            "importance_score": 4,
            "urgency_score": 3,
            "rationality_verdict": "合理",
            "review_comment": "先进入研制，再由 P5 查询。",
            "reviewed_by": "p4-reviewer",
        },
    )
    assert approve_response.status_code == 200

    withdraw_response = client.post(
        f"/api/tool-hub/demand-sheets/{sheet_id}/withdraw",
        json={
            "actor_id": "p3-sim",
            "reason_code": "user_reset",
            "reason_message": "人工撤销，准备重新测试构单。",
        },
    )
    assert withdraw_response.status_code == 200
    withdraw_payload = withdraw_response.json()
    assert withdraw_payload["lifecycle_status"] == "withdrawn"
    assert withdraw_payload["terminal_reason_code"] == "user_reset"
    assert withdraw_payload["lifecycle_events"][-1]["event_type"] == "withdrawn"

    _force_manufacture_plan_ready(tmp_path, item_id)

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["sheet_lifecycle_status"] == "withdrawn"
    assert progress_payload["status"] != "ready_for_fetch"


def test_p4_can_reject_sheet_and_keep_audit_record(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert created.status_code == 201
    created_payload = created.json()
    sheet_id = created_payload["sheet_id"]
    item_id = created_payload["items"][0]["item_id"]

    reject_response = client.post(
        f"/api/tool-hub/demand-sheets/{sheet_id}/reject",
        json={
            "actor_id": "p4-reviewer",
            "reason_code": "contract_incomplete",
            "reason_message": "工单约束不完整，当前不予受理。",
        },
    )
    assert reject_response.status_code == 200
    reject_payload = reject_response.json()
    assert reject_payload["lifecycle_status"] == "rejected"
    assert reject_payload["terminal_reason_code"] == "contract_incomplete"
    assert reject_payload["lifecycle_events"][-1]["event_type"] == "rejected"

    progress_response = client.get(f"/api/tool-hub/demand-items/{item_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["sheet_lifecycle_status"] == "rejected"
    assert progress_payload["status"] in {"checking", "matched_existing", "accepted"}


def test_testing_endpoint_can_clear_all_demand_chain_data(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    first_created = client.post("/api/tool-hub/mock-generators/blue-force-demand-sheets")
    assert first_created.status_code == 201
    second_created = client.post(
        "/api/tool-hub/demand-sheets",
        json=_build_component_sheet_payload("蓝军编组树构造器", "COMP-BLUE-FORCE-TREE-BUILDER"),
    )
    assert second_created.status_code == 201

    first_item_id = first_created.json()["items"][0]["item_id"]

    list_before = client.get("/api/tool-hub/demand-sheets")
    assert list_before.status_code == 200
    assert len(list_before.json()["items"]) == 2

    clear_response = client.post("/api/tool-hub/testing/clear-demand-sheets")
    assert clear_response.status_code == 200
    clear_payload = clear_response.json()
    assert clear_payload["cleared_sheet_count"] == 2
    assert clear_payload["cleared_item_count"] >= 2
    assert clear_payload["cleared_manufacture_plan_count"] >= 0

    list_after = client.get("/api/tool-hub/demand-sheets")
    assert list_after.status_code == 200
    assert list_after.json()["items"] == []

    item_after = client.get(f"/api/tool-hub/demand-items/{first_item_id}")
    assert item_after.status_code == 404
