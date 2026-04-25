from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.tool_hub import get_tool_hub_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app
from app.tool_hub.service import ToolHubService


def _assert_snapshot_meta(payload: dict) -> str:
    assert "meta" in payload
    assert "data" in payload
    assert payload["meta"]["snapshot_id"]
    assert payload["meta"]["generated_at"]
    assert payload["meta"]["state_version"]
    return payload["meta"]["snapshot_id"]


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


def test_tool_hub_overview_and_tool_crud(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_payload = {
        "name": "审批规则校验器",
        "slug": "approval-rule-validator",
        "status": "active",
        "summary": "针对审批路径和规则集生成校验建议",
        "problem_statement": "降低审批方案设计阶段的人工比对成本",
        "primary_domain_id": "workflow_approval",
        "tool_form_id": "skill",
        "runtime_platform_ids": ["agent_runtime"],
        "tags": [
            "domain:workflow_approval",
            "form:skill",
            "runtime:agent_runtime",
            "lifecycle:solution_design",
            "input:process_list",
            "output:validation_report",
        ],
        "lifecycle_stage_ids": ["solution_design"],
        "input_types": ["process_list", "rule_set"],
        "output_types": ["validation_report"],
        "supported_sources": ["manual_input", "frozen_snapshot"],
        "usage_notes": "用于审批路径设计前的快速筛查",
        "keywords": ["审批", "校验"],
        "verification": {
            "status": "verified",
            "last_verified_result": "样例通过",
            "sample_case_ids": ["sample-1"],
        },
    }

    created = client.post("/api/tool-hub/tools", json=create_payload)
    assert created.status_code == 201
    created_body = created.json()
    tool_id = created_body["tool_id"]
    assert created_body["slug"] == "approval-rule-validator"

    listed = client.get("/api/tool-hub/tools")
    assert listed.status_code == 200
    listed_body = listed.json()
    listed_snapshot_id = _assert_snapshot_meta(listed_body)
    assert len(listed_body["data"]["items"]) == 1

    overview = client.get("/api/tool-hub/overview")
    assert overview.status_code == 200
    overview_body = overview.json()
    overview_snapshot_id = _assert_snapshot_meta(overview_body)
    assert overview_body["data"]["metrics"]["tool_count"] == 1
    assert overview_body["data"]["metrics"]["verified_tool_count"] == 1
    assert overview_body["data"]["metrics"]["active_tool_count"] == 1
    assert "case_management" in [item["id"] for item in overview_body["data"]["catalogs"]["domains"]]
    assert overview_snapshot_id == listed_snapshot_id

    detail = client.get(f"/api/tool-hub/tools/{tool_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "审批规则校验器"

    updated = client.put(
        f"/api/tool-hub/tools/{tool_id}",
        json={**create_payload, "summary": "针对流程清单输出结构化验证建议"},
    )
    assert updated.status_code == 200
    assert updated.json()["summary"] == "针对流程清单输出结构化验证建议"

    overview_after_update = client.get("/api/tool-hub/overview")
    tools_after_update = client.get("/api/tool-hub/tools")
    overview_after_update_body = overview_after_update.json()
    tools_after_update_body = tools_after_update.json()
    assert _assert_snapshot_meta(overview_after_update_body) == _assert_snapshot_meta(tools_after_update_body)
    assert overview_after_update_body["data"]["metrics"]["tool_count"] == len(tools_after_update_body["data"]["items"])


def test_tool_hub_can_delete_single_tool_and_clear_all_tools_for_testing(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    first_create_payload = {
        "name": "审批规则校验器",
        "slug": "approval-rule-validator",
        "status": "active",
        "summary": "针对审批路径和规则集生成校验建议",
        "problem_statement": "降低审批方案设计阶段的人工比对成本",
        "primary_domain_id": "workflow_approval",
        "tool_form_id": "skill",
        "runtime_platform_ids": ["agent_runtime"],
        "tags": [
            "domain:workflow_approval",
            "form:skill",
            "runtime:agent_runtime",
            "lifecycle:solution_design",
            "input:process_list",
            "output:validation_report",
        ],
        "lifecycle_stage_ids": ["solution_design"],
        "input_types": ["process_list"],
        "output_types": ["validation_report"],
        "supported_sources": ["manual_input"],
        "usage_notes": "用于审批验证",
        "keywords": ["审批", "验证"],
        "verification": {
            "status": "verified",
            "last_verified_result": "样例通过",
            "sample_case_ids": ["sample-1"],
        },
    }
    second_create_payload = {
        **first_create_payload,
        "name": "导航航路装配器",
        "slug": "navigation-route-assembler",
        "primary_domain_id": "cross_domain_shared",
        "keywords": ["导航", "航路"],
    }

    first_created = client.post("/api/tool-hub/tools", json=first_create_payload)
    second_created = client.post("/api/tool-hub/tools", json=second_create_payload)
    assert first_created.status_code == 201
    assert second_created.status_code == 201

    first_tool_id = first_created.json()["tool_id"]

    delete_response = client.delete(f"/api/tool-hub/tools/{first_tool_id}")
    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload["removed_tool_id"] == first_tool_id
    assert delete_payload["remaining_tool_count"] == 1

    listed_after_delete = client.get("/api/tool-hub/tools")
    assert listed_after_delete.status_code == 200
    assert len(listed_after_delete.json()["data"]["items"]) == 1

    clear_response = client.post("/api/tool-hub/testing/clear-tools")
    assert clear_response.status_code == 200
    clear_payload = clear_response.json()
    assert clear_payload["cleared_tool_count"] == 1
    assert clear_payload["cleared_match_run_count"] == 0
    assert clear_payload["cleared_evolution_run_count"] == 0

    listed_after_clear = client.get("/api/tool-hub/tools")
    assert listed_after_clear.status_code == 200
    assert listed_after_clear.json()["data"]["items"] == []


def test_tool_fetch_manifest_exposes_atomic_frontend_component_contract(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_payload = {
        "name": "查询表格元组件",
        "slug": "query-table-widget",
        "status": "draft",
        "summary": "可嵌入宿主项目的查询表格元组件",
        "problem_statement": "复用列表筛选、表格渲染和行级操作骨架",
        "primary_domain_id": "cross_domain_shared",
        "tool_form_id": "frontend_component",
        "tool_granularity": "atomic",
        "packaging_type": "source_package",
        "integration_mode": "import_component",
        "dependency_policy": "peer",
        "runtime_dependencies": ["react@18", "antd@5"],
        "host_constraints": {
            "frontend_framework": "react",
            "ui_library": "antd",
        },
        "runtime_platform_ids": ["web_frontend"],
        "lifecycle_stage_ids": ["solution_design", "verification_release"],
        "input_types": ["query_params", "column_schema"],
        "output_types": ["tsx_component", "delivery_manifest"],
        "supported_sources": ["manual_input"],
        "tags": [
            "domain:cross_domain_shared",
            "form:frontend_component",
            "runtime:web_frontend",
            "delivery:import_component",
        ],
    }

    created = client.post("/api/tool-hub/tools", json=create_payload)
    assert created.status_code == 201
    tool_id = created.json()["tool_id"]

    manifest = client.get(f"/api/tool-hub/tools/{tool_id}/fetch")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["tool_form_id"] == "frontend_component"
    assert payload["packaging_type"] == "source_package"
    assert payload["integration_mode"] == "import_component"
    assert payload["dependency_policy"] == "peer"
    assert payload["runtime_dependencies"] == ["react@18", "antd@5"]
    assert payload["entrypoint_type"] == "descriptor"
    assert payload["contract_version"] == "p4.fetch.v2"


def test_tool_hub_match_and_evolution_runs(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    tool_payloads = [
        {
            "name": "审批规则校验器",
            "slug": "approval-rule-validator",
            "status": "active",
            "summary": "针对审批路径和规则集生成验证建议",
            "problem_statement": "降低审批方案设计阶段的人工比对成本",
            "primary_domain_id": "workflow_approval",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [
                "domain:workflow_approval",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "input:process_list",
                "output:validation_report",
            ],
            "lifecycle_stage_ids": ["solution_design", "verification_release"],
            "input_types": ["process_list"],
            "output_types": ["validation_report"],
            "supported_sources": ["manual_input", "frozen_snapshot"],
            "usage_notes": "用于审批梳理前的快速筛查",
            "keywords": ["审批", "校验"],
            "verification": {
                "status": "verified",
                "last_verified_result": "样例通过",
                "sample_case_ids": ["sample-1"],
            },
        },
        {
            "name": "审批路径解释器",
            "slug": "approval-path-explainer",
            "status": "active",
            "summary": "给出审批路径命中的解释理由",
            "problem_statement": "帮助用户理解匹配逻辑",
            "primary_domain_id": "workflow_approval",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [
                "domain:workflow_approval",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "input:process_list",
                "output:review_suggestion",
            ],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["process_list"],
            "output_types": ["review_suggestion"],
            "supported_sources": ["manual_input"],
            "usage_notes": "适合解释审批链路场景",
            "keywords": ["审批", "解释"],
            "verification": {
                "status": "warning",
                "last_verified_result": "需要人工复核",
                "sample_case_ids": ["sample-2"],
            },
        },
    ]

    for payload in tool_payloads:
        created = client.post("/api/tool-hub/tools", json=payload)
        assert created.status_code == 201

    match_response = client.post(
        "/api/tool-hub/match-runs",
        json={
            "scenario_text": "需要针对审批流程挑选规则分析和验证工具",
            "target_domain_ids": ["workflow_approval"],
            "lifecycle_stage_ids": ["solution_design"],
            "required_input_types": ["process_list"],
            "expected_output_types": ["validation_report"],
            "preferred_tool_forms": ["skill"],
            "preferred_runtime_platforms": ["agent_runtime"],
            "preferred_tags": ["domain:workflow_approval"],
            "knowledge_context": {
                "archive_id": "20161116-nas",
                "entity_ids": [],
                "process_ids": ["process-collaboration"],
                "snapshot_version": "v1",
            },
        },
    )
    assert match_response.status_code == 201
    match_body = match_response.json()
    assert match_body["candidates"][0]["tool_id"]
    assert match_body["candidates"][0]["match_score"] >= match_body["candidates"][1]["match_score"]
    assert "domain" in match_body["candidates"][0]["matched_dimensions"]
    assert "lifecycle" in match_body["candidates"][0]["matched_dimensions"]
    assert match_body["request"]["knowledge_context"]["archive_id"] == "20161116-nas"

    evolution_response = client.post("/api/tool-hub/evolution-runs")
    assert evolution_response.status_code == 201
    evolution_body = evolution_response.json()
    assert evolution_body["summary"]["tool_count"] == 2
    assert evolution_body["summary"]["overlap_risk_count"] >= 1

    overview = client.get("/api/tool-hub/overview")
    tools = client.get("/api/tool-hub/tools")
    listed_runs = client.get("/api/tool-hub/evolution-runs")
    overview_body = overview.json()
    tools_body = tools.json()
    listed_runs_body = listed_runs.json()
    overview_snapshot_id = _assert_snapshot_meta(overview_body)
    tools_snapshot_id = _assert_snapshot_meta(tools_body)
    listed_runs_snapshot_id = _assert_snapshot_meta(listed_runs_body)
    assert overview_snapshot_id == tools_snapshot_id == listed_runs_snapshot_id
    assert overview_body["data"]["metrics"]["tool_count"] == len(tools_body["data"]["items"])

    assert listed_runs.status_code == 200
    assert len(listed_runs_body["data"]["items"]) == 1


def test_tool_hub_seeded_demo_data_is_not_rewritten_on_read(tmp_path: Path) -> None:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")

    service = ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=True,
    )

    save_calls: list[str] = []
    original_save_tool = service.repository.save_tool

    def spy_save_tool(tool):
        save_calls.append(tool.tool_id)
        return original_save_tool(tool)

    service.repository.save_tool = spy_save_tool  # type: ignore[method-assign]

    envelope = service.list_tools()

    assert len(envelope.data.items) >= 1
    assert save_calls == []


def test_tool_hub_internal_runtime_port_can_refresh_projections_and_run_cycle(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    refresh_response = client.post("/api/tool-hub/internal-runtime/projections/refresh")
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["snapshot_id"]
    assert set(refresh_payload["refreshed_projection_names"]) == {
        "overview",
        "tool_list",
        "evolution_workspace",
    }

    demand_response = client.post("/api/tool-hub/mock-generators/demand-sheets/navigation_planning")
    assert demand_response.status_code == 201
    demand_payload = demand_response.json()
    target_item = next(item for item in demand_payload["items"] if item["recommendation_type"] == "manufacture_candidate")

    review_response = client.post(
        f"/api/tool-hub/demand-items/{target_item['item_id']}/review",
        json={
            "decision": "approve_manufacture",
            "reviewed_by": "runtime-api-tester",
            "review_comment": "run cycle through internal port",
            "importance_score": 88,
            "urgency_score": 72,
            "rationality_verdict": "approved",
        },
    )
    assert review_response.status_code == 200

    cycle_response = client.post("/api/tool-hub/internal-runtime/cycles/run-once")
    assert cycle_response.status_code == 200
    cycle_payload = cycle_response.json()
    assert cycle_payload["processed_job_count"] >= 1
    assert "p4-manufacture" in cycle_payload["processed_queues"]

    progress_response = client.get(f"/api/tool-hub/demand-items/{target_item['item_id']}/progress")
    assert progress_response.status_code == 200
    assert progress_response.json()["status"] in {"manufacturing_in_progress", "ready_for_fetch"}
