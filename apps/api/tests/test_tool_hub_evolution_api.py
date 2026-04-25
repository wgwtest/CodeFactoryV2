from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.tool_hub import get_tool_hub_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app
from app.tool_hub.models import ToolDefinitionWrite
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
  "documents": [
    {
      "id": "doc-1",
      "title": "NAS AV-1",
      "path": "archive/NAS AV-1.pdf",
      "file_type": "pdf",
      "source_archive": "20161116体系结构文献翻译汇总",
      "character_count": 1200
    }
  ],
  "entities": [
    {
      "id": "entity-nas",
      "name": "国家空域系统",
      "category": "system_or_service",
      "aliases": ["NAS"],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "NAS excerpt"}
      ]
    }
  ],
  "events": [],
  "processes": [
    {
      "id": "process-collaboration",
      "name": "协同处置流程",
      "category": "domain_process",
      "aliases": [],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Collaboration excerpt"}
      ]
    }
  ],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def _build_service(
    tmp_path: Path,
    *,
    seed_demo_data: bool = False,
    executor_tick_seconds: float = 0.05,
) -> ToolHubService:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")
    return ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=seed_demo_data,
        executor_tick_seconds=executor_tick_seconds,
    )


def _build_client(tmp_path: Path) -> TestClient:
    app = create_app()
    service = _build_service(tmp_path)
    app.dependency_overrides[get_tool_hub_service] = lambda: service
    return TestClient(app)


def _create_tool_with_missing_problem_statement(client: TestClient) -> str:
    response = client.post(
        "/api/tool-hub/tools",
        json={
            "name": "案例标签修复器",
            "slug": "case-tag-fixer",
            "status": "active",
            "summary": "修复案例工具的标签与摘要问题",
            "problem_statement": "",
            "primary_domain_id": "case_management",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [
                "domain:case_management",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "input:manual_text",
                "output:structured_json",
            ],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["manual_text"],
            "output_types": ["structured_json"],
            "supported_sources": ["manual_input"],
            "usage_notes": "用于演示自演进自动修复",
            "keywords": ["案例", "修复"],
            "verification": {
                "status": "unverified",
                "last_verified_result": "",
                "sample_case_ids": [],
            },
        },
    )
    assert response.status_code == 201
    return response.json()["tool_id"]


def _wait_for_task_status(client: TestClient, task_id: str, expected_status: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/tool-hub/evolution/tasks/{task_id}")
        if response.status_code == 200 and response.json()["task_status"] == expected_status:
            return response.json()
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not reach status {expected_status}")


def test_tool_hub_service_delegates_to_domain_services(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    assert service.registry_service is not None
    assert service.demand_service is not None
    assert service.manufacture_service is not None
    assert service.evolution_service is not None

    detail = service.create_mock_blue_force_demand_sheet()
    assert detail.sheet_id.startswith("tds-")

    run = service.run_evolution(actor_id="tester", trigger_type="manual")
    assert run.run_id.startswith("evolution-run-")


def test_evolution_run_decision_and_task_creation(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _create_tool_with_missing_problem_statement(client)

    run_response = client.post("/api/tool-hub/evolution/runs", json={"actor_id": "tester"})
    assert run_response.status_code == 201
    run_body = run_response.json()
    assert run_body["status"] in {"running", "completed"}
    assert run_body["summary"]["finding_count"] >= 1

    runs_response = client.get("/api/tool-hub/evolution/runs")
    assert runs_response.status_code == 200
    run_id = runs_response.json()["data"]["items"][0]["run_id"]
    finding_id = runs_response.json()["data"]["items"][0]["findings"][0]["finding_id"]

    decision_response = client.post(
        f"/api/tool-hub/evolution/findings/{finding_id}/decision",
        json={"actor_id": "tester", "decision": "accept", "note": "turn into task"},
    )
    assert decision_response.status_code == 200
    decision_body = decision_response.json()
    assert decision_body["run_id"] == run_id
    assert decision_body["decision_status"] == "accepted_to_task"
    assert decision_body["linked_task_id"]

    tasks_response = client.get("/api/tool-hub/evolution/tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["data"]["items"]
    assert len(tasks) >= 1
    assert tasks[0]["source_run_id"] == run_id


def test_evolution_auto_apply_and_task_rollback(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    tool_id = _create_tool_with_missing_problem_statement(client)

    run_response = client.post("/api/tool-hub/evolution/runs", json={"actor_id": "tester"})
    assert run_response.status_code == 201
    run_id = run_response.json()["run_id"]

    run_detail_response = client.get(f"/api/tool-hub/evolution/runs/{run_id}")
    assert run_detail_response.status_code == 200
    finding_id = run_detail_response.json()["findings"][0]["finding_id"]

    decision_response = client.post(
        f"/api/tool-hub/evolution/findings/{finding_id}/decision",
        json={"actor_id": "tester", "decision": "accept", "note": "auto apply"},
    )
    assert decision_response.status_code == 200
    task_id = decision_response.json()["linked_task_id"]

    completed_task = _wait_for_task_status(client, task_id, "completed")
    assert completed_task["task_type"] == "auto_apply"
    assert completed_task["change_count"] >= 1
    assert completed_task["rollback_available"] is True

    tool_response = client.get(f"/api/tool-hub/tools/{tool_id}")
    assert tool_response.status_code == 200
    assert tool_response.json()["problem_statement"]

    rollback_response = client.post(
        f"/api/tool-hub/evolution/tasks/{task_id}/rollback",
        json={"actor_id": "tester", "note": "revert auto change"},
    )
    assert rollback_response.status_code == 200
    rollback_body = rollback_response.json()
    assert rollback_body["task_status"] == "rolled_back"
    assert rollback_body["rollback_available"] is False

    reverted_tool_response = client.get(f"/api/tool-hub/tools/{tool_id}")
    assert reverted_tool_response.status_code == 200
    assert reverted_tool_response.json()["problem_statement"] == ""


def test_evolution_scheduler_runs_when_dirty(tmp_path: Path) -> None:
    service = _build_service(tmp_path, executor_tick_seconds=0.05)
    service.create_tool(
        ToolDefinitionWrite.model_validate(
            {
            "name": "巡检定时器演示器",
            "slug": "inspection-scheduler-demo",
            "status": "active",
            "summary": "用于演示调度器触发的工具",
            "problem_statement": "",
            "primary_domain_id": "cross_domain_shared",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["manual_text"],
            "output_types": ["structured_json"],
            "supported_sources": ["manual_input"],
            "usage_notes": "",
            "keywords": [],
            "verification": {
                "status": "unverified",
                "last_verified_result": "",
                "sample_case_ids": [],
            },
        }
        )
    )

    service.update_evolution_config(
        {
            "enabled": True,
            "interval_minutes": 0.001,
            "focus_rule_ids": ["missing_description"],
            "auto_apply_rule_ids": ["missing_description"],
        },
        actor_id="tester",
    )

    deadline = time.time() + 3
    while time.time() < deadline:
        runs = service.list_evolution_runs().data.items
        if runs and runs[0].trigger_type == "scheduled":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("scheduled evolution run was not created")

    latest = service.list_evolution_runs().data.items[0]
    assert latest.trigger_type == "scheduled"
    assert latest.status in {"running", "completed"}
