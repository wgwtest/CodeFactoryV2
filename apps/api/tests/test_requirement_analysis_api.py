import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.requirement_analysis.template_service import RequirementAnalysisTemplateService
from app.requirement_analysis.deepseek_client import DeepSeekRequirementAnalysisClient
from app.requirement_analysis import deepseek_client as requirement_analysis_client_module
from app.main import create_app
from app.orchestrators.plugin_contracts import OrchestratorRunResult
from app.orchestrators.plugin_discovery import OrchestratorPluginDiscovery


def find_spec_node(nodes: list[dict], node_id: str) -> dict | None:
    for node in nodes:
        if node["node_id"] == node_id:
            return node
        found = find_spec_node(node.get("children", []), node_id)
        if found is not None:
            return found
    return None


def assert_new_turn_contract(turn: dict) -> None:
    assert "previous_interaction" in turn
    assert "input_relation" in turn
    assert "intent_understanding_result" in turn
    assert "target_document_structure" in turn
    assert "stage_task_definition" in turn
    assert "stage_quality_constraints" in turn
    assert "spec_execution" in turn
    assert "post_update_review" in turn
    assert "review_after_apply_result" in turn
    assert "next_interaction_plan" in turn
    assert "closure_decision" in turn
    assert "next_interaction" in turn
    assert "decision_trace" in turn
    for removed_field in [
        "previous_suggestion",
        "previous_user_focus",
        "input_relation_to_previous_suggestion",
        "organizer_interpretation",
        "affected_spec_nodes",
        "closure_assessment",
        "current_user_focus",
        "next_suggestion",
        "quick_options",
        "confirmed_facts_delta",
        "open_questions_delta",
        "document_patch",
        "assistant_message",
    ]:
        assert removed_field not in turn


def _write_reload_test_plugin(
    root: Path,
    *,
    plugin_id: str = "xg-reload-test-orchestrator",
    plugin_name: str = "XG Reload Test Orchestrator",
) -> Path:
    plugin_dir = root / "xg" / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "plugin_id": plugin_id,
                "name": plugin_name,
                "plugin_type": "dify_workflow",
                "document_type": "xg",
                "contract": "xg-observable-orchestrator-contract@1",
                "status": "active",
                "priority": 10,
                "capabilities": {"filled_document_text": True},
                "requires": {"template": True, "model_provider": "optional"},
                "adapter_entry": "dify_workflow",
                "adapter_module": "adapter",
                "adapter_class": "ReloadTestAdapter",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (plugin_dir / "adapter.py").write_text(
        "class ReloadTestAdapter:\n"
        "    def __init__(self, *, manifest, package=None):\n"
        "        self.manifest = manifest\n",
        encoding="utf-8",
    )
    return plugin_dir


def test_requirement_analysis_lab_template_assets_can_be_managed_as_instances(tmp_path, monkeypatch) -> None:
    template_root = tmp_path / "templates"
    template_root.mkdir()
    instance_root = tmp_path / "instances"
    (template_root / "01-81433-软件级需求规格模板.md").write_text("# 81433 软件级需求规格模板\n\n## 1. 范围\n", encoding="utf-8")
    (template_root / "02-82259-平台级规格模板.md").write_text("# 82259 平台级规格模板\n\n## 1. 边界\n", encoding="utf-8")
    monkeypatch.setattr(RequirementAnalysisTemplateService, "TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(RequirementAnalysisTemplateService, "INSTANCE_ROOT", instance_root)

    client = TestClient(create_app())

    base_listed = client.get("/api/requirement-analysis/template-bases")
    assert base_listed.status_code == 200
    assert base_listed.json()["items"] == [
        {
            "template_id": "81433号",
            "template_code": "81433",
            "name": "软件级需求规格说明模板",
            "description": "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
            "status": "active",
        },
        {
            "template_id": "82259号",
            "template_code": "82259",
            "name": "平台级需求规格说明模板",
            "description": "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
            "status": "available",
        },
    ]

    listed = client.get("/api/requirement-analysis/templates")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["template_id"] == "xg-template-81433-default"
    assert listed.json()["items"][0]["base_template_id"] == "81433号"
    assert listed.json()["items"][0]["template_code"] == "81433"
    assert (instance_root / "manifest.json").exists()
    assert (instance_root / "xg-template-81433-default.md").read_text(encoding="utf-8").startswith(
        "# 81433 软件级需求规格模板"
    )

    created = client.post(
        "/api/requirement-analysis/templates",
        json={
            "base_template_id": "81433号",
            "name": "态势分析系统需求规格模板",
            "description": "基于 81433 扩充的项目实例模板。",
        },
    )
    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["base_template_id"] == "81433号"
    assert created_payload["template_code"] == "81433"
    assert created_payload["name"] == "态势分析系统需求规格模板"
    assert created_payload["content"].startswith("# 81433 软件级需求规格模板")
    created_template_id = created_payload["template_id"]
    assert created_template_id != "81433号"

    detail = client.get(f"/api/requirement-analysis/templates/{created_template_id}")
    assert detail.status_code == 200
    assert detail.json()["template_id"] == created_template_id
    assert detail.json()["base_template_id"] == "81433号"
    assert detail.json()["content"].startswith("# 81433 软件级需求规格模板")
    assert detail.json()["format"] == "markdown"

    saved = client.put(
        f"/api/requirement-analysis/templates/{created_template_id}",
        json={
            "name": "态势分析系统需求规格模板 V2",
            "description": "已补充项目约束。",
            "content": "# 81433 软件级需求规格模板\n\n## 1. 修改后的范围\n",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["name"] == "态势分析系统需求规格模板 V2"
    assert saved.json()["content"].endswith("## 1. 修改后的范围\n")
    assert (instance_root / f"{created_template_id}.md").read_text(encoding="utf-8").endswith("## 1. 修改后的范围\n")
    assert (template_root / "01-81433-软件级需求规格模板.md").read_text(encoding="utf-8").endswith("## 1. 范围\n")

    deleted = client.delete(f"/api/requirement-analysis/templates/{created_template_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "template_id": created_template_id}
    assert not (instance_root / f"{created_template_id}.md").exists()

    missing = client.get("/api/requirement-analysis/templates/unknown")
    assert missing.status_code == 404


def test_requirement_analysis_lab_session_turn_and_recovery() -> None:
    client = TestClient(create_app())

    lab_config = client.get("/api/requirement-analysis/lab-config")
    assert lab_config.status_code == 200
    config = lab_config.json()
    assert config["page"]["title"] == "P2 XG 需求分析组织器 Lab"
    assert config["defaults"] == {
        "topic": "默认运算软件需求规格说明",
        "orchestrator_id": "xg-local-heuristic-orchestrator",
        "provider_id": "deepseek",
        "model": "provider-default",
        "template_id": "xg-template-81433-default",
        "knowledge_package_id": "airspace-domain-demo",
        "write_policy": "patch_suggestion_only",
    }
    assert config["provider_log_schema"]["fields"][0]["path"] == "user_input"
    assert config["provider_log_schema"]["fields"][0]["used_when"]
    assert "previous_interaction" in config["turn_audit_schema"]["required_fields"]
    assert "spec_execution" in config["turn_audit_schema"]["required_fields"]

    orchestrators = client.get("/api/requirement-analysis/orchestrators")
    assert orchestrators.status_code == 200
    items = orchestrators.json()["items"]
    plugin_ids = {item["plugin_id"] for item in items}
    assert {
        "brainstorm-v1",
        "brainstorm-v1-dify-workflow",
        "xg-local-heuristic-orchestrator",
        "xg-local-strong-rule-orchestrator",
        "xg-dify-workflow-orchestrator",
    }.issubset(plugin_ids)

    heuristic = next(item for item in items if item["plugin_id"] == "xg-local-heuristic-orchestrator")
    assert heuristic["orchestrator_id"] == "xg-local-heuristic-orchestrator"
    assert heuristic["plugin_type"] == "local_package"
    assert heuristic["document_type"] == "xg"
    assert heuristic["contract"] == "xg-observable-orchestrator-contract@1"
    assert heuristic["observability_level"] == "full"
    assert heuristic["capabilities"]["document_patch"] is True
    assert heuristic["capabilities"]["stage_audits"] is True

    dify = next(item for item in items if item["plugin_id"] == "xg-dify-workflow-orchestrator")
    assert dify["plugin_type"] == "dify_workflow"
    assert dify["observability_level"] == "limited"
    assert dify["capabilities"]["filled_document_text"] is True
    assert dify["capabilities"]["stage_audits"] is False

    brainstorm = next(item for item in items if item["plugin_id"] == "brainstorm-v1")
    assert brainstorm["plugin_type"] == "local_package"
    assert brainstorm["observability_level"] == "full"
    assert brainstorm["capabilities"]["decision_trace"] is True
    assert brainstorm["package_id"] == "brainstorm-v1"

    brainstorm_dify = next(item for item in items if item["plugin_id"] == "brainstorm-v1-dify-workflow")
    assert brainstorm_dify["plugin_type"] == "dify_workflow"
    assert brainstorm_dify["package_id"] == "brainstorm-v1"
    assert brainstorm_dify["observability_level"] == "limited"
    assert brainstorm_dify["capabilities"]["decision_trace"] is True
    assert brainstorm_dify["capabilities"]["stage_audits"] is False

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()
    assert session["status"] == "created"
    assert session["session_phase"] == "exploration_convergence"
    assert session["orchestrator"]["orchestrator_id"] == "xg-local-heuristic-orchestrator"
    assert session["orchestrator"]["plugin_id"] == "xg-local-heuristic-orchestrator"
    assert session["orchestrator"]["plugin_type"] == "local_package"
    assert session["orchestrator"]["observability_level"] == "full"
    assert session["orchestrator"]["name"] == "XG Heuristic Orchestrator"
    assert session["orchestrator"]["document_type"] == "xg"
    assert session["orchestrator"]["mode"] == "policy_interpreted"
    assert session["stable_contract"]["formal_document"] is True
    assert session["write_policy"] == "patch_suggestion_only"
    assert session["document_patch"] == []
    assert session["decision_state"]["confirmed_facts"] == []
    assert session["decision_state"]["confirmed_decisions"] == []
    assert session["decision_state"]["tentative_assumptions"] == []
    assert session["decision_state"]["open_questions"] != []
    assert session["decision_state_document"]["title"] == "需求分析结构化状态"
    assert session["working_document"]["document_id"] == "lab-working-document"
    assert session["working_document"]["title"].startswith("81433号需求规格说明")
    assert "sections" not in session["working_document"]
    assert session["working_document"]["blocks"] == []
    assert session["working_document"]["revision_fragments"] == []
    assert session["questions"][0]["question_id"] == "Q-001"
    assert session["questions"][0]["status"] == "open"
    assert session["facts"] == []
    assert session["patches"] == []
    assert session["active_spec_node_id"] == "SPEC-REQ-1.1"
    assert session["turn_path"] == []
    assert session["next_interaction"] is None
    assert "previous_user_focus" not in session
    assert "next_suggestion" not in session
    assert session["spec_tree"][0]["title"] == "需求规格说明完成度树（81433号）"
    assert [node["title"] for node in session["spec_tree"][0]["children"]] == [
        "1 总则",
        "2 项目概述",
        "3 功能需求",
        "4 非功能需求",
        "5 验收准则",
    ]
    assert find_spec_node(session["spec_tree"], "SPEC-REQ-3.1") == {
        "node_id": "SPEC-REQ-3.1",
        "title": "REQ-3.1 用户与角色",
        "target_section": "3 功能需求 / 用户与角色",
        "node_type": "clause",
        "question": "组织器策略问题：请说明主要用户角色、职责、协作者和管理员边界。",
        "status": "open",
        "answer_summary": "",
        "completion_reason": "",
        "children": [],
    }
    assert "直接描述" in session["messages"][0]["content"]

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    assert payload["session"]["status"] == "waiting_user"
    assert payload["session"]["session_phase"] == "exploration_convergence"
    assert payload["turn"]["turn_id"] == "turn-0001"
    assert_new_turn_contract(payload["turn"])
    assert [item["stage_id"] for item in payload["turn"]["stage_audits"]] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]
    assert [item["stage_kind"] for item in payload["turn"]["stage_audits"]] == [
        "intent",
        "decision_state_delta",
        "next_interaction",
    ]
    assert payload["turn"]["intent_understanding_result"]["input_type"] == "first_round_product_concept"
    assert payload["turn"]["stage_task_definition"]["target_sections"] == ["1 总则 / 编写目的"]
    assert payload["turn"]["next_interaction_plan"]["target_spec_nodes"] == ["SPEC-REQ-2.1"]
    assert payload["turn"]["previous_interaction"]["type"] == "none"
    assert payload["turn"]["input_relation"]["relation"] == "none"
    assert payload["turn"]["closure_decision"]["status"] == "closed"
    assert "applied_section_ids" not in payload["turn"]["spec_execution"]["working_document_update"]
    assert payload["turn"]["spec_execution"]["working_document_update"]["applied_block_ids"] == ["blk-0001"]
    assert payload["turn"]["spec_execution"]["working_document_update"]["applied_fragment_ids"] == ["frag-0001"]
    assert "1.1 编写目的" in payload["turn"]["spec_execution"]["working_document_update"]["after_excerpt"]
    assert "section_review" not in payload["turn"]["post_update_review"]
    assert payload["turn"]["post_update_review"]["target_review"]["status"] in {"acceptable", "closed"}
    assert payload["turn"]["post_update_review"]["global_review"]["status"] in {"move_next_node", "continue"}
    assert "空域运算软件" in payload["turn"]["spec_execution"]["confirmed_facts"][0]
    assert payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-1.1"
    assert any("用户输入是本轮 Turn 起点" in item for item in payload["turn"]["decision_trace"])
    assert payload["turn"]["normalized_input"]["input_type"] == "free_text"
    assert "临时正文" in payload["turn"]["spec_execution"]["assistant_message"]
    assert "建议下一步确认" in payload["turn"]["spec_execution"]["assistant_message"]
    assert "软件定位" in payload["turn"]["next_interaction"]["prompt"]
    assert payload["turn"]["next_interaction"]["type"] == "choice_question"
    assert [option["label"] for option in payload["turn"]["next_interaction"]["options"]] == [
        "计算分析工具",
        "协同规划平台",
        "二者兼有但先做分析",
    ]
    assert payload["turn"]["spec_execution"]["target_anchor_plan"][0]["template_clause_id"] == "REQ-1.1"
    assert payload["turn"]["spec_execution"]["document_patch"][0]["plan_ref"] == "AP-001"
    assert payload["turn"]["spec_execution"]["document_patch"][0]["operation"] == "append_or_update"
    assert payload["turn"]["confidence"] == "medium"
    assert [item["stage_id"] for item in payload["session"]["provider_logs"]] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]
    assert [item["call_id"] for item in payload["session"]["provider_logs"]] == [
        "requirement-analysis-provider-call-0001",
        "requirement-analysis-provider-call-0002",
        "requirement-analysis-provider-call-0003",
    ]
    assert payload["session"]["provider_logs"][0]["stage_type"] == "policy_interpreted"
    assert payload["session"]["provider_logs"][2]["stage_type"] == "policy_interpreted"
    assert payload["session"]["provider_logs"][1]["audit"]["provider_request"]["mock_context"]["stage"]["prompt_id"] == "decision_state_delta"
    assert payload["session"]["provider_logs"][2]["audit"]["provider_request"]["mock_context"]["stage"]["prompt_id"] == "next_interaction_planning"
    assert "软件名称" in payload["session"]["provider_logs"][2]["audit"]["provider_request"]["prompt_bundle"]["decision_state_json"]
    assert "需求分析结构化状态" in payload["session"]["provider_logs"][2]["audit"]["provider_request"]["prompt_bundle"]["decision_state_document_json"]
    assert "空域运算软件" in payload["session"]["decision_state"]["confirmed_facts"][0]["content"]
    assert payload["session"]["decision_state_document"]["sections"][0]["heading"] == "一、已确认事实"
    assert "空域运算软件" in payload["session"]["confirmed_facts"][0]
    assert payload["session"]["document_patch"][0]["plan_ref"] == "AP-001"
    assert "sections" not in payload["session"]["working_document"]
    assert payload["session"]["working_document"]["blocks"][0]["block_id"] == "blk-0001"
    assert payload["session"]["working_document"]["blocks"][0]["anchor_path"] == "REQ-1.1"
    assert payload["session"]["working_document"]["blocks"][0]["display_heading"] == "1.1 编写目的"
    assert "空域运算软件" in payload["session"]["working_document"]["blocks"][0]["text"]
    assert payload["session"]["working_document"]["revision_fragments"][0]["fragment_id"] == "frag-0001"
    assert payload["session"]["working_document"]["revision_fragments"][0]["turn_id"] == "turn-0001"
    assert payload["session"]["questions"][0]["question_id"] == "Q-001"
    assert payload["session"]["questions"][0]["status"] == "confirmed"
    assert payload["session"]["questions"][0]["resolution_fact_ids"] == ["F-001"]
    assert payload["session"]["questions"][1]["question_id"] == "Q-002"
    assert payload["session"]["questions"][1]["status"] == "open"
    assert payload["session"]["facts"][0]["fact_id"] == "F-001"
    assert payload["session"]["facts"][0]["source_question_ids"] == ["Q-001"]
    assert payload["session"]["patches"][0]["patch_id"] == "P-001"
    assert payload["session"]["patches"][0]["target_section"] == "1.1 编写目的"
    assert payload["session"]["patches"][0]["source_fact_ids"] == ["F-001"]
    assert payload["session"]["patches"][0]["source_question_ids"] == ["Q-001"]
    assert payload["session"]["next_interaction"]["interaction_id"] == payload["turn"]["next_interaction"]["interaction_id"]
    assert payload["session"]["active_spec_node_id"] == "SPEC-REQ-2.1"
    first_spec_leaf = find_spec_node(payload["session"]["spec_tree"], "SPEC-REQ-1.1")
    assert first_spec_leaf["status"] == "closed"
    assert "空域运算软件" in first_spec_leaf["answer_summary"]
    assert first_spec_leaf["completion_reason"] == "turn-0001 用户已确认"
    assert payload["session"]["turn_path"][0]["turn_id"] == "turn-0001"
    assert payload["session"]["turn_path"][0]["node_id"] == "SPEC-REQ-1.1"
    assert payload["session"]["turn_path"][0]["affected_node_ids"] == ["SPEC-REQ-1.1"]
    assert payload["session"]["turn_path"][0]["input_relation"] == "none"
    assert payload["session"]["turn_path"][0]["closed_node_ids"] == ["SPEC-REQ-1.1"]

    second_turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "它是面向空域领域的计算分析工具，第一阶段不做协同规划。"},
    )
    assert second_turn.status_code == 200
    second_payload = second_turn.json()
    assert second_payload["turn"]["turn_id"] == "turn-0002"
    assert_new_turn_contract(second_payload["turn"])
    assert [item["stage_id"] for item in second_payload["turn"]["stage_audits"]] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]
    assert second_payload["turn"]["previous_interaction"]["interaction_id"] == payload["turn"]["next_interaction"]["interaction_id"]
    assert second_payload["turn"]["input_relation"]["relation"] == "answered"
    assert second_payload["turn"]["spec_execution"]["working_document_update"]["applied_block_ids"] == ["blk-0002"]
    assert second_payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-2.1"
    assert second_payload["turn"]["spec_execution"]["confirmed_facts"][0] == "它是面向空域领域的计算分析工具，第一阶段不做协同规划。"
    assert "空域领域的计算分析工具" in second_payload["turn"]["spec_execution"]["document_patch"][0]["content"]
    assert second_payload["turn"]["next_interaction"]["prompt"] == "组织器策略问题：请说明主要用户角色、职责、协作者和管理员边界。"
    assert [option["label"] for option in second_payload["turn"]["next_interaction"]["options"]] == [
        "领域专家直接使用",
        "管理员配置后专家使用",
        "多角色协同使用",
    ]
    assert second_payload["session"]["questions"][0]["question_id"] == "Q-001"
    assert second_payload["session"]["questions"][0]["resolution_fact_ids"] == ["F-001"]
    assert second_payload["session"]["questions"][1]["question_id"] == "Q-002"
    assert second_payload["session"]["questions"][1]["status"] == "confirmed"
    assert second_payload["session"]["questions"][1]["resolution_fact_ids"] == ["F-002"]
    assert second_payload["session"]["facts"][1]["fact_id"] == "F-002"
    assert "空域领域" in second_payload["session"]["facts"][1]["content"]
    assert second_payload["session"]["facts"][1]["source_question_ids"] == ["Q-002"]
    assert second_payload["session"]["patches"][1]["patch_id"] == "P-002"
    assert second_payload["session"]["patches"][1]["target_section"] == "2.1 软件定位"
    assert second_payload["session"]["patches"][1]["source_question_ids"] == ["Q-002"]
    assert second_payload["session"]["active_spec_node_id"] == "SPEC-REQ-3.1"
    assert [item["call_id"] for item in second_payload["session"]["provider_logs"]] == [
        "requirement-analysis-provider-call-0001",
        "requirement-analysis-provider-call-0002",
        "requirement-analysis-provider-call-0003",
        "requirement-analysis-provider-call-0004",
        "requirement-analysis-provider-call-0005",
        "requirement-analysis-provider-call-0006",
    ]
    second_spec_leaf = find_spec_node(second_payload["session"]["spec_tree"], "SPEC-REQ-2.1")
    assert second_spec_leaf["status"] == "closed"
    assert "空域领域" in second_spec_leaf["answer_summary"]
    assert second_payload["session"]["turn_path"][1]["turn_id"] == "turn-0002"
    assert second_payload["session"]["turn_path"][1]["node_id"] == "SPEC-REQ-2.1"
    assert second_payload["session"]["turn_path"][1]["affected_node_ids"] == ["SPEC-REQ-2.1"]
    assert second_payload["session"]["next_interaction"]["interaction_id"] == second_payload["turn"]["next_interaction"]["interaction_id"]

    recovered = client.get(f"/api/requirement-analysis/sessions/{session['session_id']}")
    assert recovered.status_code == 200
    recovered_payload = recovered.json()
    assert recovered_payload["session_id"] == session["session_id"]
    assert recovered_payload["status"] == "waiting_user"
    assert recovered_payload["turns"][0]["turn_id"] == "turn-0001"
    assert recovered_payload["turns"][1]["turn_id"] == "turn-0002"
    assert_new_turn_contract(recovered_payload["turns"][0])
    assert_new_turn_contract(recovered_payload["turns"][1])
    assert recovered_payload["messages"][-1]["role"] == "assistant"
    assert recovered_payload["messages"][-1]["turn_id"] == "turn-0002"


def test_requirement_analysis_lab_config_default_orchestrator_comes_from_plugin_registry(tmp_path: Path, monkeypatch) -> None:
    from app.orchestrators import plugin_registry as plugin_registry_module

    _write_reload_test_plugin(
        tmp_path,
        plugin_id="xg-registry-default-orchestrator",
        plugin_name="XG Registry Default Orchestrator",
    )

    monkeypatch.setattr(
        plugin_registry_module,
        "OrchestratorPluginDiscovery",
        lambda: OrchestratorPluginDiscovery(root=tmp_path),
    )
    plugin_registry_module.reload_orchestrator_plugin_registry()
    client = TestClient(create_app())

    try:
        lab_config = client.get("/api/requirement-analysis/lab-config")

        assert lab_config.status_code == 200
        assert lab_config.json()["defaults"]["orchestrator_id"] == "xg-registry-default-orchestrator"
    finally:
        plugin_registry_module.get_orchestrator_plugin_registry.cache_clear()


def test_requirement_analysis_session_can_default_to_discovered_orchestrator() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )

    assert created.status_code == 200
    assert created.json()["orchestrator"]["orchestrator_id"] == "xg-local-heuristic-orchestrator"



def test_requirement_analysis_decision_state_is_applied_before_next_interaction_planning(monkeypatch) -> None:
    captured_next_stage_input: dict = {}

    class FakeDeepSeekClient:
        def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
            self.model = model

        def run_stage(
            self,
            *,
            session,
            user_input: str,
            normalized: dict,
            orchestrator_id: str,
            stage: dict,
            stage_input: dict | None = None,
        ) -> dict:
            stage_input = dict(stage_input or {})
            stage_id = str(stage["stage_id"])
            raw = {
                "provider_id": "deepseek",
                "model": self.model,
                "mock": False,
                "provider_request": {
                    "messages": [{"role": "user", "content": f"{stage_id} prompt"}],
                    "prompt_bundle": {
                        "stage_id": stage_id,
                        "prompt_id": str(stage.get("prompt_id") or stage_id),
                        "assembled_prompt": f"{stage_id} prompt",
                        "schema_json": "{}",
                    },
                },
                "provider_response": {"raw_content": "{}", "parsed_json": {}},
            }
            if stage_id == "intent_understanding":
                output = {
                    "intent_understanding_result": {
                        "user_goal_summary": "用户确认态势展示和 GIS 分析工具。",
                        "input_type": "first_round_product_concept",
                        "relation_to_previous_interaction": "none",
                        "option_handling": "not_option",
                        "matched_option": None,
                        "supplemental_facts": ["态势展示", "GIS 分析工具"],
                        "target_section_candidates": ["1 总则 / 编写目的"],
                        "document_strategy": "explore_decision_state",
                        "write_task_candidate": "沉淀结构化状态。",
                        "review_focus_candidate": "检查结构化状态是否推进。",
                        "ambiguities": [],
                    },
                    "target_document_structure": {
                        "target_sections": ["1 总则 / 编写目的"],
                        "target_anchor_paths": ["1 总则 / 编写目的"],
                        "current_major_gaps": ["用户角色仍未明确。"],
                    },
                    "stage_task_definition": {
                        "task_summary": "沉淀态势分析系统的起始结构化状态。",
                        "target_sections": ["1 总则 / 编写目的"],
                        "non_goals": [],
                        "must_output": ["decision_state_delta"],
                        "review_standard": "结构化状态要包含事实和未闭合问题。",
                    },
                    "stage_quality_constraints": {
                        "minimum_depth": "明确已知事实和下一步问题。",
                        "must_cover_dimensions": ["事实", "问题"],
                        "assistant_reply_style": "说明结构化状态变化。",
                    },
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}
            if stage_id == "decision_state_delta":
                output = {
                    "organizer_interpretation": {
                        "summary": "用户提出了态势分析系统的初始能力方向。",
                        "intent": "first_round_product_concept",
                        "confidence": "high",
                    },
                    "assistant_message": "本轮已沉淀态势展示与 GIS 分析工具方向。",
                    "decision_state_delta": {
                        "confirmed_facts": [
                            {
                                "content": "系统需要态势展示能力和 GIS 分析工具。",
                                "target_section": "1 总则 / 编写目的",
                                "status": "active",
                            }
                        ],
                        "confirmed_decisions": [],
                        "tentative_assumptions": [],
                        "open_questions": [
                            {
                                "content": "第一版主要服务哪类用户仍未明确。",
                                "target_section": "3 功能需求 / 用户与角色",
                                "status": "open",
                            }
                        ],
                        "rejected_directions": [],
                        "chapter_projections": [
                            {
                                "content": "1.1 编写目的",
                                "target_section": "1 总则 / 编写目的",
                                "status": "projected",
                            }
                        ],
                        "next_focus": "确认第一版主要用户。",
                    },
                    "template_shape_assessment": {
                        "shape_type": "coarse_grained_extensible",
                        "reason": "当前仅做探索阶段投影。",
                        "allowed_write_modes": ["append_existing_clause"],
                        "forbidden_write_modes": [],
                        "template_revision_recommendations": [],
                    },
                    "target_anchor_plan": [
                        {
                            "plan_id": "AP-001",
                            "decision_type": "append_existing_clause",
                            "template_clause_id": "REQ-1.1",
                            "canonical_clause_heading": "1.1 编写目的",
                            "subtopic_action": "none",
                            "subtopic_key": "",
                            "subtopic_title": "",
                            "display_heading": "1.1 编写目的",
                            "template_shape_ref": "coarse_grained_extensible",
                            "reason": "起始输入形成系统目的投影。",
                            "confidence": "high",
                            "anchor_path": "REQ-1.1",
                        }
                    ],
                    "confirmed_facts_delta": ["系统需要态势展示能力和 GIS 分析工具。"],
                    "open_questions_delta": ["第一版主要服务哪类用户仍未明确。"],
                    "document_patch": [
                        {
                            "plan_ref": "AP-001",
                            "operation": "append_or_update",
                            "content": "本系统面向态势展示和 GIS 分析工具的需求探索。",
                            "write_policy": session.write_policy,
                        }
                    ],
                    "annotations": [],
                    "risks": [],
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}

            captured_next_stage_input.update(stage_input)
            decision_state = dict(stage_input.get("decision_state") or {})
            assert any(
                item.get("content") == "系统需要态势展示能力和 GIS 分析工具。"
                for item in decision_state.get("confirmed_facts", [])
            )
            assert any(
                item.get("content") == "第一版主要服务哪类用户仍未明确。"
                for item in decision_state.get("open_questions", [])
            )
            output = {
                "next_interaction_plan": {
                    "planning_strategy": "ask_key_decision",
                    "user_message": "本轮已沉淀结构化状态，下一步确认主用户。",
                    "next_question": "第一版最主要服务哪类用户？",
                    "quick_options": [{"key": "A", "label": "指挥管理人员", "recommended": True}],
                    "plan_reason": "结构化状态显示用户角色是当前最大未闭合问题。",
                    "review_acknowledgement": "结构化状态已应用。",
                    "target_spec_nodes": ["SPEC-REQ-3.1"],
                },
                "planning_trace": ["读取本轮应用后的 decision_state 后规划。"],
                "confidence": "high",
            }
            return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}

    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_api_key", "test-deepseek-key")
    monkeypatch.setattr(requirement_analysis_client_module, "DeepSeekRequirementAnalysisClient", FakeDeepSeekClient)

    client = TestClient(create_app())
    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "态势分析系统需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "deepseek",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "我希望创建一个态势分析系统，要有态势展示和 GIS 分析工具。"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["turn"]["next_interaction"]["prompt"] == "第一版最主要服务哪类用户？"
    assert captured_next_stage_input["decision_state_document"]["title"] == "需求分析结构化状态"
    assert "系统需要态势展示能力和 GIS 分析工具。" in str(captured_next_stage_input["decision_state_document"])



def test_requirement_analysis_lab_accepts_selected_previous_quick_option() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()

    first_turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )
    assert first_turn.status_code == 200
    first_payload = first_turn.json()
    assert [option["label"] for option in first_payload["turn"]["next_interaction"]["options"]] == [
        "计算分析工具",
        "协同规划平台",
        "二者兼有但先做分析",
    ]

    second_turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "A，计算分析工具"},
    )
    assert second_turn.status_code == 200
    second_payload = second_turn.json()
    assert_new_turn_contract(second_payload["turn"])
    relation = second_payload["turn"]["input_relation"]
    assert relation["relation"] == "selected_option"
    assert "上轮选项 A：计算分析工具" in relation["reason"]
    assert second_payload["turn"]["normalized_input"] == {
        "input_type": "quick_option_answer",
        "matched_option": "A",
        "matched_option_label": "计算分析工具",
        "semantic": "计算分析工具",
    }

    third_turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "A"},
    )
    assert third_turn.status_code == 200
    third_payload = third_turn.json()
    assert_new_turn_contract(third_payload["turn"])
    third_relation = third_payload["turn"]["input_relation"]
    assert third_relation["relation"] == "selected_option"
    assert "上轮选项 A：领域专家直接使用" in third_relation["reason"]
    assert third_payload["turn"]["normalized_input"]["semantic"] == "领域专家直接使用"


def test_requirement_analysis_lab_runs_xg_strong_rule_orchestrator_package() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-strong-rule-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )

    assert created.status_code == 200
    session = created.json()
    assert session["orchestrator"]["orchestrator_id"] == "xg-local-strong-rule-orchestrator"
    assert session["orchestrator"]["plugin_id"] == "xg-local-strong-rule-orchestrator"
    assert session["orchestrator"]["plugin_type"] == "local_package"
    assert session["orchestrator"]["observability_level"] == "full"
    assert session["orchestrator"]["document_type"] == "xg"
    assert session["orchestrator"]["mode"] == "local_runner"
    assert session["orchestrator"]["capabilities"]["stage_audits"] is True

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["orchestrator_plugin"]["plugin_id"] == "xg-local-strong-rule-orchestrator"
    assert payload["turn"]["orchestrator_plugin"]["observability_level"] == "full"
    assert payload["turn"]["orchestrator_plugin"]["plugin_type"] == "local_package"
    assert payload["turn"]["raw_plugin_response"]["contract_version"] == "xg-observable-orchestrator-contract@1"
    assert payload["turn"]["raw_plugin_response"]["plugin"]["plugin_id"] == "xg-local-strong-rule-orchestrator"
    assert payload["turn"]["spec_execution"]["interpretation"]["intent"] == "supplement_requirement"
    assert "强规则组织器" in payload["turn"]["spec_execution"]["assistant_message"]
    assert payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-1.1"
    assert payload["turn"]["closure_decision"]["status"] == "closed"
    assert any("强规则组织器" in item for item in payload["turn"]["decision_trace"])
    assert payload["turn"]["raw_model_response"]["orchestrator_id"] == "xg-strong-rule-orchestrator"
    assert payload["turn"]["raw_model_response"]["mode"] == "local_runner"
    assert payload["turn"]["raw_model_response"]["runner_invoked"] is True
    runner_entry = payload["turn"]["raw_model_response"]["runner_entry"].replace("\\", "/")
    assert runner_entry.endswith("xg-strong-rule-orchestrator/runner.py")
    assert payload["session"]["provider_logs"][0]["orchestrator_id"] == "xg-strong-rule-orchestrator"
    assert payload["session"]["provider_logs"][0]["orchestrator_mode"] == "local_runner"
    assert len(payload["session"]["provider_logs"]) == 1
    assert payload["session"]["provider_logs"][0]["stage_id"] == "run"
    assert payload["session"]["active_spec_node_id"] == "SPEC-REQ-2.1"


def test_requirement_analysis_lab_runs_brainstorm_v1_as_plugin() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "brainstorm-v1",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )

    assert created.status_code == 200
    session = created.json()
    assert session["orchestrator"]["orchestrator_id"] == "brainstorm-v1"
    assert session["orchestrator"]["plugin_id"] == "brainstorm-v1"
    assert session["orchestrator"]["plugin_type"] == "local_package"
    assert session["orchestrator"]["observability_level"] == "full"

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["orchestrator_plugin"]["plugin_id"] == "brainstorm-v1"
    assert payload["turn"]["decision_state_delta"]["confirmed_facts"]
    assert payload["turn"]["decision_state_change_summary"]["added_counts"]["confirmed_facts"] == 1
    assert payload["turn"]["decision_state_document"]["title"] == "需求分析结构化状态"
    assert payload["session"]["decision_state"]["confirmed_facts"]
    assert payload["session"]["decision_state_document"]["title"] == "需求分析结构化状态"
    assert payload["session"]["provider_logs"][1]["stage_id"] == "decision_state_delta"


def test_requirement_analysis_lab_runs_brainstorm_v1_dify_workflow_plugin() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "brainstorm-v1-dify-workflow",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )

    assert created.status_code == 200
    session = created.json()
    assert session["orchestrator"]["orchestrator_id"] == "brainstorm-v1-dify-workflow"
    assert session["orchestrator"]["plugin_id"] == "brainstorm-v1-dify-workflow"
    assert session["orchestrator"]["plugin_type"] == "dify_workflow"
    assert session["orchestrator"]["observability_level"] == "limited"

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["orchestrator_plugin"]["plugin_id"] == "brainstorm-v1-dify-workflow"
    assert payload["turn"]["orchestrator_plugin"]["observability_level"] == "limited"
    assert payload["turn"]["decision_state_delta"]["confirmed_facts"]
    assert payload["turn"]["decision_state_document"]["title"] == "需求分析结构化状态"
    assert payload["turn"]["stage_audits"] == []
    assert payload["turn"]["raw_plugin_response"]["raw_output"]["raw_workflow_trace"]["workflow_id"] == "brainstorm-v1-dify-shaped-workflow"
    assert payload["session"]["decision_state"]["confirmed_facts"]
    assert payload["session"]["decision_state_document"]["title"] == "需求分析结构化状态"
    assert "空域运算软件" in payload["session"]["working_document"]["blocks"][0]["text"]


def test_requirement_analysis_lab_can_run_fake_dify_plugin_with_limited_observability() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-dify-workflow-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()
    assert session["orchestrator"]["plugin_type"] == "dify_workflow"
    assert session["orchestrator"]["observability_level"] == "limited"

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    assert payload["turn"]["orchestrator_plugin"]["plugin_id"] == "xg-dify-workflow-orchestrator"
    assert payload["turn"]["orchestrator_plugin"]["observability_level"] == "limited"
    assert payload["turn"]["stage_audits"] == []
    assert payload["turn"]["raw_plugin_response"]["raw_output"]["raw_workflow_trace"]["fake"] is True
    assert "空域运算软件" in payload["session"]["working_document"]["blocks"][0]["text"]


def test_requirement_analysis_lab_runs_dify_through_manifest_adapter_loader(monkeypatch) -> None:
    from app.requirement_analysis import turn_engine as turn_engine_module

    calls: list[str] = []

    class FakeAdapter:
        def __init__(self, plugin_id: str) -> None:
            self.plugin_id = plugin_id

        def run(self, request) -> OrchestratorRunResult:
            from app.orchestrators.adapters.plugin_turn_result_materializer import PluginTurnResultMaterializer

            base_result = OrchestratorRunResult(
                contract_version=request.contract_version,
                plugin={
                    "plugin_id": self.plugin_id,
                    "plugin_type": "dify_workflow",
                    "observability_level": "limited",
                },
                final_output={
                    "filled_document_text": "# 需求规格说明\n\nadapter loader sentinel",
                    "document_patch": [],
                    "changed_sections": [],
                    "completion_status": "partial",
                    "confidence": "medium",
                },
                interaction_output={
                    "assistant_message": "adapter loader sentinel",
                    "next_question": "继续补充。",
                    "quick_options": [],
                    "suggested_focus": {},
                },
                process_output={
                    "stage_results": [],
                    "stage_audits": [],
                    "decision_trace": ["adapter loader was used"],
                    "provider_logs": [],
                    "review_after_apply_result": {},
                    "annotations": [],
                    "risks": [],
                },
                state_output={
                    "confirmed_facts_delta": ["adapter loader sentinel"],
                    "open_questions_delta": ["继续补充。"],
                    "spec_tree_update": {},
                    "working_document_update": {},
                    "turn_path_update": {},
                },
                raw_output={
                    "raw_plugin_response": {},
                    "raw_model_response": {},
                    "raw_workflow_trace": {"sentinel": True},
                },
            )
            turn_result = PluginTurnResultMaterializer().materialize(request=request, result=base_result)
            return base_result.model_copy(
                update={
                    "raw_output": {
                    **dict(base_result.raw_output or {}),
                    "turn_execution_result": turn_result,
                    },
                }
            )

    def fake_loader(manifest, **_kwargs):
        calls.append(manifest.plugin_id)
        return FakeAdapter(manifest.plugin_id)

    monkeypatch.setattr(turn_engine_module, "load_orchestrator_plugin_adapter", fake_loader, raising=False)

    client = TestClient(create_app())
    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-dify-workflow-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200

    turn = client.post(
        f"/api/requirement-analysis/sessions/{created.json()['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert calls == ["xg-dify-workflow-orchestrator"]
    assert payload["turn"]["spec_execution"]["assistant_message"] == "adapter loader sentinel"
    assert payload["turn"]["raw_plugin_response"]["raw_output"]["raw_workflow_trace"]["sentinel"] is True


def test_requirement_analysis_lab_runs_local_xg_through_manifest_adapter_loader(monkeypatch) -> None:
    from app.requirement_analysis import turn_engine as turn_engine_module

    original_loader = turn_engine_module.load_orchestrator_plugin_adapter
    calls: list[str] = []

    def recording_loader(manifest, **kwargs):
        calls.append(manifest.plugin_id)
        return original_loader(manifest, **kwargs)

    monkeypatch.setattr(turn_engine_module, "load_orchestrator_plugin_adapter", recording_loader, raising=False)

    client = TestClient(create_app())
    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200

    turn = client.post(
        f"/api/requirement-analysis/sessions/{created.json()['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件"},
    )

    assert turn.status_code == 200
    assert calls == ["xg-local-heuristic-orchestrator"]


def test_requirement_analysis_orchestrator_reload_reflects_plugin_directory_changes(tmp_path: Path, monkeypatch) -> None:
    from app.orchestrators import plugin_registry as plugin_registry_module

    plugin_dir = _write_reload_test_plugin(tmp_path)
    backup_dir = tmp_path / ".backup" / plugin_dir.name

    monkeypatch.setattr(
        plugin_registry_module,
        "OrchestratorPluginDiscovery",
        lambda: OrchestratorPluginDiscovery(root=tmp_path),
    )
    plugin_registry_module.reload_orchestrator_plugin_registry()
    client = TestClient(create_app())

    listed = client.get("/api/requirement-analysis/orchestrators")
    assert listed.status_code == 200
    assert {item["plugin_id"] for item in listed.json()["items"]} == {"xg-reload-test-orchestrator"}

    try:
        created = client.post(
            "/api/requirement-analysis/sessions",
            json={
                "topic": "目录插拔验证",
                "orchestrator_id": "xg-reload-test-orchestrator",
                "provider_id": "mock",
                "model": "mock-requirement-analysis-v1",
                "template_id": "81433号",
                "knowledge_package_id": "airspace-domain-demo",
                "write_policy": "patch_suggestion_only",
            },
        )
        assert created.status_code == 200

        backup_dir.parent.mkdir(parents=True)
        shutil.move(plugin_dir, backup_dir)

        reloaded = client.post("/api/requirement-analysis/orchestrators/reload")
        assert reloaded.status_code == 200
        assert reloaded.json()["items"] == []

        rejected = client.post(
            "/api/requirement-analysis/sessions",
            json={
                "topic": "目录插拔验证",
                "orchestrator_id": "xg-reload-test-orchestrator",
                "provider_id": "mock",
                "model": "mock-requirement-analysis-v1",
                "template_id": "81433号",
                "knowledge_package_id": "airspace-domain-demo",
                "write_policy": "patch_suggestion_only",
            },
        )
        assert rejected.status_code == 400
        assert rejected.json()["detail"] == "unsupported orchestrator"

        shutil.move(backup_dir, plugin_dir)
        restored = client.post("/api/requirement-analysis/orchestrators/reload")
        assert restored.status_code == 200
        assert [item["plugin_id"] for item in restored.json()["items"]] == ["xg-reload-test-orchestrator"]
    finally:
        plugin_registry_module.get_orchestrator_plugin_registry.cache_clear()


def test_requirement_analysis_lab_rejects_unknown_orchestrator() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "unknown",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported orchestrator"


def test_requirement_analysis_lab_uses_deepseek_provider_when_configured(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeDeepSeekClient:
        def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["model"] = model

        def run_stage(self, *, session, user_input: str, normalized: dict, orchestrator_id: str, stage: dict, stage_input: dict | None = None) -> dict:
            captured["session_provider"] = session.provider_id
            captured["user_input"] = user_input
            captured["normalized"] = normalized
            stage_id = stage["stage_id"]
            prompt_bundle = {
                "assembled_prompt": "assembled prompt",
                "context_json": '{"user_input":"A，先按计算分析工具理解"}',
                "schema_json": '{"assistant_message":"string"}',
                "stage_id": stage_id,
                "prompt_id": stage.get("prompt_id", stage_id),
            }
            if stage_id == "intent_understanding":
                return {
                    "intent_understanding_result": {
                        "user_goal_summary": "先按计算分析工具理解。",
                        "input_type": "option_answer_with_supplement",
                        "relation_to_previous_interaction": "selected_option",
                        "option_handling": "matched_option_with_supplement",
                        "matched_option": "A",
                        "supplemental_facts": ["先按计算分析工具理解"],
                        "target_section_candidates": ["2 项目概述 / 软件定位"],
                        "document_strategy": "write_targeted_sections",
                        "write_task_candidate": "将软件定位写入需求规格正文。",
                        "review_focus_candidate": "检查软件定位是否成文。",
                        "ambiguities": [],
                    },
                    "target_document_structure": {
                        "target_sections": ["2 项目概述 / 软件定位"],
                        "target_anchor_paths": ["2 项目概述 / 软件定位"],
                        "current_major_gaps": ["软件定位仍需写入正文。"],
                    },
                    "stage_task_definition": {
                        "task_summary": "将软件定位写入需求规格正文。",
                        "target_sections": ["2 项目概述 / 软件定位"],
                        "non_goals": [],
                        "must_output": ["document_patch", "assistant_message"],
                        "review_standard": "软件定位需要形成可接受表达。",
                    },
                    "stage_quality_constraints": {
                        "minimum_depth": "明确系统定位和阶段边界。",
                        "must_cover_dimensions": ["定位", "边界"],
                        "assistant_reply_style": "先解释写入结果。",
                    },
                    "confidence": "high",
                    "raw_model_response": {
                        "provider_id": "deepseek",
                        "mock": False,
                        "provider_request": {"messages": [{"role": "system", "content": "system prompt"}, {"role": "user", "content": "assembled prompt"}], "prompt_bundle": prompt_bundle},
                        "provider_response": {"raw_content": '{"intent_understanding_result":{}}', "parsed_json": {}},
                    },
                }
            if stage_id == "review_after_apply":
                return {
                    "compliance_result": "pass",
                    "written_fact_summary": ["软件定位已形成正文"],
                    "blocking_findings": [],
                    "blocking_reasons": [],
                    "planning_evidence": ["blk-0001", "frag-0001"],
                    "target_review": {
                        "status": "acceptable",
                        "reason": "模型基于应用后的临时正文确认目标范围已覆盖。",
                        "review_target": ["2 项目概述 / 软件定位"],
                        "covered_points": ["软件定位"],
                        "missing_aspects": [],
                        "evidence_block_ids": ["blk-0001"],
                        "evidence_fragment_ids": ["frag-0001"],
                    },
                    "global_review": {
                        "status": "move_next_node",
                        "summary": "模型建议推进到输入数据来源。",
                        "remaining_gaps": [],
                    },
                    "rewrite_advice": [],
                    "review_annotations": ["模型 Review 读取了应用后的临时正文。"],
                    "confidence": "high",
                    "raw_model_response": {
                        "provider_id": "deepseek",
                        "mock": False,
                        "provider_request": {"messages": [{"role": "system", "content": "system prompt"}, {"role": "user", "content": "assembled prompt"}], "prompt_bundle": prompt_bundle},
                        "provider_response": {"raw_content": '{"target_review":{"status":"acceptable"}}', "parsed_json": {"target_review": {"status": "acceptable"}}},
                    },
                }
            if stage_id == "next_interaction_planning":
                return {
                    "next_interaction_plan": {
                        "planning_strategy": "move_next_node",
                        "user_message": "本轮已把软件定位写入临时正文。",
                        "next_question": "下一轮可以确认输入数据来源。",
                        "quick_options": [
                            {"key": "A", "label": "先确认输入", "recommended": True},
                            {"key": "B", "label": "先确认输出", "recommended": False},
                        ],
                        "plan_reason": "系统定位已补充，输入章节仍薄弱。",
                        "review_acknowledgement": "软件定位已覆盖。",
                        "target_spec_nodes": ["SPEC-REQ-3.2"],
                    },
                    "planning_trace": ["规划阶段基于 review 结果推进输入章节。"],
                    "confidence": "medium",
                    "raw_model_response": {
                        "provider_id": "deepseek",
                        "mock": False,
                        "provider_request": {"messages": [{"role": "system", "content": "system prompt"}, {"role": "user", "content": "assembled prompt"}], "prompt_bundle": prompt_bundle},
                        "provider_response": {"raw_content": '{"next_interaction_plan":{"next_question":"下一轮可以确认输入数据来源。"}}', "parsed_json": {}},
                    },
                }
            if stage_id == "decision_state_delta":
                return {
                    "organizer_interpretation": {
                        "summary": "用户选择先按计算分析工具理解。",
                        "intent": "confirm_direction",
                        "confidence": "high",
                    },
                    "assistant_message": "DeepSeek 已确认：本轮把系统定位更新为计算分析工具。",
                    "decision_state_delta": {
                        "confirmed_facts": [
                            {
                                "content": "DeepSeek 确认系统初步定位为空域计算分析工具",
                                "target_section": "2 项目概述 / 软件定位",
                                "status": "active",
                            }
                        ],
                        "confirmed_decisions": [
                            {
                                "content": "先按计算分析工具理解。",
                                "target_section": "2 项目概述 / 软件定位",
                                "status": "active",
                            }
                        ],
                        "tentative_assumptions": [],
                        "open_questions": [
                            {
                                "content": "输入数据来源尚未确认。",
                                "target_section": "3 功能需求 / 输入数据来源",
                                "status": "open",
                            }
                        ],
                        "rejected_directions": [],
                        "chapter_projections": [
                            {
                                "content": "2.1 软件定位",
                                "target_section": "2 项目概述 / 软件定位",
                                "status": "projected",
                            }
                        ],
                        "next_focus": "下一轮可以确认输入数据来源。",
                    },
                    "template_shape_assessment": {
                        "shape_type": "coarse_grained_extensible",
                        "reason": "模板允许在既有条款下补写软件定位。",
                        "allowed_write_modes": ["append_existing_clause"],
                        "forbidden_write_modes": [],
                        "template_revision_recommendations": [],
                    },
                    "target_anchor_plan": [
                        {
                            "plan_id": "AP-001",
                            "decision_type": "append_existing_clause",
                            "template_clause_id": "REQ-2.1",
                            "canonical_clause_heading": "2.1 软件定位",
                            "subtopic_action": "none",
                            "subtopic_key": "",
                            "subtopic_title": "",
                            "display_heading": "2.1 软件定位",
                            "template_shape_ref": "coarse_grained_extensible",
                            "reason": "用户选择了计算分析工具定位。",
                            "confidence": "high",
                            "anchor_path": "REQ-2.1",
                        }
                    ],
                    "confirmed_facts_delta": ["DeepSeek 确认系统初步定位为空域计算分析工具"],
                    "open_questions_delta": ["输入数据来源尚未确认。"],
                    "document_patch": [
                        {
                            "plan_ref": "AP-001",
                            "operation": "append_or_update",
                            "content": "本系统支持空域计算分析任务的需求澄清。",
                            "write_policy": session.write_policy,
                        }
                    ],
                    "annotations": ["DeepSeek Provider 返回结构化 Turn 输出。"],
                    "risks": [],
                    "confidence": "medium",
                    "raw_model_response": {
                        "provider_id": "deepseek",
                        "mock": False,
                        "provider_request": {
                            "messages": [
                                {"role": "system", "content": "system prompt"},
                                {"role": "user", "content": "assembled prompt"},
                            ],
                            "prompt_bundle": prompt_bundle,
                        },
                        "provider_response": {
                            "raw_content": '{"decision_state_delta":{"confirmed_facts":[{"content":"DeepSeek 确认系统初步定位为空域计算分析工具"}]}}',
                            "parsed_json": {
                                "decision_state_delta": {
                                    "confirmed_facts": [
                                        {"content": "DeepSeek 确认系统初步定位为空域计算分析工具"}
                                    ]
                                }
                            },
                        },
                    },
                }
            return {
                "organizer_interpretation": {
                    "summary": "用户选择先按计算分析工具理解。",
                    "intent": "confirm_direction",
                    "confidence": "high",
                },
                "assistant_message": "DeepSeek 已确认：本轮把系统定位更新为计算分析工具。",
                "next_suggestion": {
                    "kind": "topic",
                    "content": "下一轮可以确认输入数据来源。",
                    "reason": "系统定位已补充，输入章节仍薄弱。",
                    "related_spec_node_ids": ["SPEC-REQ-3.2"],
                },
                "quick_options": [
                    {"key": "A", "label": "先确认输入"},
                    {"key": "B", "label": "先确认输出"},
                ],
                "template_shape_assessment": {
                    "shape_type": "coarse_grained_extensible",
                    "reason": "模板允许在既有条款下补写软件定位。",
                    "allowed_write_modes": ["append_existing_clause"],
                    "forbidden_write_modes": [],
                    "template_revision_recommendations": [],
                },
                "target_anchor_plan": [
                    {
                        "plan_id": "AP-001",
                        "decision_type": "append_existing_clause",
                        "template_clause_id": "REQ-2.1",
                        "canonical_clause_heading": "2.1 软件定位",
                        "subtopic_action": "none",
                        "subtopic_key": "",
                        "subtopic_title": "",
                        "display_heading": "2.1 软件定位",
                        "template_shape_ref": "coarse_grained_extensible",
                        "reason": "用户选择了计算分析工具定位。",
                        "confidence": "high",
                        "anchor_path": "REQ-2.1",
                    }
                ],
                "confirmed_facts_delta": ["DeepSeek 确认系统初步定位为空域计算分析工具"],
                "open_questions_delta": ["输入数据来源尚未确认。"],
                "document_patch": [
                    {
                        "plan_ref": "AP-001",
                        "operation": "append_or_update",
                        "content": "本系统支持空域计算分析任务的需求澄清。",
                        "write_policy": session.write_policy,
                    }
                ],
                "annotations": ["DeepSeek Provider 返回结构化 Turn 输出。"],
                "risks": [],
                "confidence": "medium",
                "raw_model_response": {
                    "provider_id": "deepseek",
                    "mock": False,
                    "provider_request": {
                        "messages": [
                            {"role": "system", "content": "system prompt"},
                            {"role": "user", "content": "assembled prompt"},
                        ],
                        "prompt_bundle": prompt_bundle,
                    },
                    "provider_response": {
                        "raw_content": '{"assistant_message":"DeepSeek 已确认：本轮把系统定位更新为计算分析工具。"}',
                        "parsed_json": {"assistant_message": "DeepSeek 已确认：本轮把系统定位更新为计算分析工具。"},
                    },
                },
            }

    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_api_key", "test-deepseek-key")
    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_model", "deepseek-chat")
    monkeypatch.setattr(requirement_analysis_client_module, "DeepSeekRequirementAnalysisClient", FakeDeepSeekClient)

    client = TestClient(create_app())

    providers = client.get("/api/requirement-analysis/providers")
    assert providers.status_code == 200
    deepseek = next(item for item in providers.json()["items"] if item["provider_id"] == "deepseek")
    assert deepseek["status"] == "active"

    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "deepseek",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()
    assert session["provider_id"] == "deepseek"
    assert session["model"] == "deepseek-chat"

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "A，先按计算分析工具理解"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    assert payload["turn"]["raw_model_response"]["mock"] is False
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["spec_execution"]["interpretation"]["intent"] == "confirm_direction"
    assert payload["turn"]["next_interaction"]["prompt"] == "下一轮可以确认输入数据来源。"
    assert [log["stage_id"] for log in payload["session"]["provider_logs"]] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]
    assert payload["session"]["provider_logs"][0]["provider_id"] == "deepseek"
    assert payload["session"]["provider_logs"][0]["model"] == "deepseek-chat"
    assert payload["session"]["provider_logs"][0]["status"] == "completed"
    provider_log = payload["session"]["provider_logs"][1]
    assert provider_log["turn_id"] == "turn-0001"
    assert provider_log["audit"]["user_input"] == "A，先按计算分析工具理解"
    assert provider_log["audit"]["normalized_input"]["semantic"] == "先按计算分析工具理解"
    assert provider_log["audit"]["provider_request"]["prompt_bundle"]["assembled_prompt"] == "assembled prompt"
    assert "working_document_json" in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert "current_section_draft" not in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert "working_document_excerpt" in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert "review_target_paths" in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert "recent_revision_fragments" in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert "review_goal" in provider_log["audit"]["provider_request"]["prompt_bundle"]
    assert provider_log["audit"]["provider_request"]["prompt_bundle"]["stage_id"] == "decision_state_delta"
    assert provider_log["audit"]["provider_normalized_output"]["decision_state_delta"]["confirmed_facts"]
    assert provider_log["audit"]["service_output"]["assistant_message"].startswith("本轮已把软件定位写入临时正文")
    assert provider_log["audit"]["service_output"]["target_anchor_plan"][0]["template_clause_id"] == "REQ-2.1"
    assert provider_log["audit"]["service_output"]["document_patch"][0]["plan_ref"] == "AP-001"
    assert captured == {
        "api_key": "test-deepseek-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "session_provider": "deepseek",
        "user_input": "A，先按计算分析工具理解",
            "normalized": {
                "input_type": "quick_option_answer",
                "matched_option": "A",
                "matched_option_label": None,
                "semantic": "先按计算分析工具理解",
            },
        }


def test_requirement_analysis_lab_records_decision_state_provider_logs(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeDeepSeekClient:
        def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
            self.model = model

        def run_stage(
            self,
            *,
            session,
            user_input: str,
            normalized: dict,
            orchestrator_id: str,
            stage: dict,
            stage_input: dict | None = None,
        ) -> dict:
            calls.append({"stage": dict(stage), "stage_input": dict(stage_input or {})})
            stage_id = str(stage["stage_id"])
            raw = {
                "provider_id": "deepseek",
                "model": self.model,
                "mock": False,
                "user_input": user_input,
                "orchestrator_id": orchestrator_id,
                "mode": "policy_interpreted",
                "stage_id": stage_id,
                "provider_request": {
                    "messages": [{"role": "user", "content": f"{stage_id} prompt"}],
                    "prompt_bundle": {
                        "stage_id": stage_id,
                        "prompt_id": str(stage.get("prompt_id") or stage_id),
                        "assembled_prompt": f"{stage_id} prompt",
                        "schema_json": "{}",
                    },
                },
                "provider_response": {
                    "raw_content": "{}",
                    "parsed_json": {},
                },
            }
            if stage["stage_kind"] == "intent":
                output = {
                    "intent_understanding_result": {
                        "user_goal_summary": "用户确认系统名称和编写目的。",
                        "input_type": "first_round_product_concept",
                        "relation_to_previous_interaction": "none",
                        "option_handling": "not_option",
                        "matched_option": None,
                        "supplemental_facts": ["系统名称和编写目的已确认。"],
                        "target_section_candidates": ["1 总则 / 编写目的"],
                        "document_strategy": "bootstrap_document",
                        "write_task_candidate": "补写编写目的。",
                        "review_focus_candidate": "检查编写目的是否成文。",
                        "ambiguities": [],
                    },
                    "target_document_structure": {
                        "target_sections": ["1 总则 / 编写目的"],
                        "target_anchor_paths": ["1 总则 / 编写目的"],
                        "current_major_gaps": ["编写目的仍缺正文。"],
                    },
                    "stage_task_definition": {
                        "task_summary": "补写编写目的。",
                        "target_sections": ["1 总则 / 编写目的"],
                        "non_goals": [],
                        "must_output": ["document_patch", "confirmed_facts_delta"],
                        "review_standard": "编写目的形成完整段落。",
                    },
                    "stage_quality_constraints": {
                        "minimum_depth": "至少一段完整正文。",
                        "must_cover_dimensions": ["系统名称", "编写目的"],
                        "assistant_reply_style": "先说明写入结果。",
                    },
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}
            if stage["stage_kind"] == "decision_state_delta":
                output = {
                    "organizer_interpretation": {
                        "summary": "用户确认系统名称和编写目的。",
                        "intent": "supplement_requirement",
                        "confidence": "high",
                    },
                    "assistant_message": "本轮已沉淀系统名称和编写目的。",
                    "decision_state_delta": {
                        "confirmed_facts": [
                            {
                                "content": "系统名称和编写目的已确认。",
                                "target_section": "1 总则 / 编写目的",
                                "status": "active",
                            }
                        ],
                        "confirmed_decisions": [],
                        "tentative_assumptions": [],
                        "open_questions": [
                            {
                                "content": "下一轮确认软件定位。",
                                "target_section": "2 项目概述 / 软件定位",
                                "status": "open",
                            }
                        ],
                        "rejected_directions": [],
                        "chapter_projections": [
                            {
                                "content": "1.1 编写目的",
                                "target_section": "1 总则 / 编写目的",
                                "status": "projected",
                            }
                        ],
                        "next_focus": "下一轮确认软件定位。",
                    },
                    "template_shape_assessment": {
                        "shape_type": "coarse_grained_extensible",
                        "reason": "模板允许在既有条款下补写编写目的。",
                        "allowed_write_modes": ["append_existing_clause"],
                        "forbidden_write_modes": [],
                        "template_revision_recommendations": [],
                    },
                    "target_anchor_plan": [
                        {
                            "plan_id": "AP-001",
                            "decision_type": "append_existing_clause",
                            "template_clause_id": "REQ-1.1",
                            "canonical_clause_heading": "1.1 编写目的",
                            "subtopic_action": "none",
                            "subtopic_key": "",
                            "subtopic_title": "",
                            "display_heading": "1.1 编写目的",
                            "template_shape_ref": "coarse_grained_extensible",
                            "reason": "用户确认系统名称和编写目的。",
                            "confidence": "high",
                            "anchor_path": "REQ-1.1",
                        }
                    ],
                    "confirmed_facts_delta": ["系统名称和编写目的已确认。"],
                    "open_questions_delta": ["下一轮确认软件定位。"],
                    "document_patch": [
                        {
                            "plan_ref": "AP-001",
                            "operation": "append_or_update",
                            "content": "本需求规格说明用于定义默认运算软件的建设目标和需求边界。",
                            "write_policy": session.write_policy,
                        }
                    ],
                    "annotations": [],
                    "risks": [],
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}
            if stage["stage_kind"] == "next_interaction":
                output = {
                    "next_interaction_plan": {
                        "planning_strategy": "move_next_node",
                        "user_message": "模型规划：编写目的已补齐，下一步确认软件定位。",
                        "next_question": "建议下一步确认软件定位。",
                        "quick_options": [{"key": "A", "label": "计算分析工具", "recommended": True}],
                        "plan_reason": "结构化状态显示软件定位仍需确认。",
                        "review_acknowledgement": "结构化状态已应用。",
                        "target_spec_nodes": ["SPEC-REQ-2.1"],
                    },
                    "planning_trace": ["模型规划阶段已读取 decision_state。"],
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}
            output = {
                "organizer_interpretation": {
                    "summary": "用户确认系统名称和编写目的。",
                    "intent": "supplement_requirement",
                    "confidence": "high",
                },
                "assistant_message": "已补充编写目的。",
                "next_suggestion": {
                    "kind": "topic",
                    "content": "下一轮确认软件定位。",
                    "reason": "总则已有正文。",
                    "related_spec_node_ids": ["SPEC-REQ-2.1"],
                },
                "quick_options": [],
                "template_shape_assessment": {
                    "shape_type": "coarse_grained_extensible",
                    "reason": "模板允许在既有条款下补写编写目的。",
                    "allowed_write_modes": ["append_existing_clause"],
                    "forbidden_write_modes": [],
                    "template_revision_recommendations": [],
                },
                "target_anchor_plan": [
                    {
                        "plan_id": "AP-001",
                        "decision_type": "append_existing_clause",
                        "template_clause_id": "REQ-1.1",
                        "canonical_clause_heading": "1.1 编写目的",
                        "subtopic_action": "none",
                        "subtopic_key": "",
                        "subtopic_title": "",
                        "display_heading": "1.1 编写目的",
                        "template_shape_ref": "coarse_grained_extensible",
                        "reason": "用户确认系统名称和编写目的。",
                        "confidence": "high",
                        "anchor_path": "REQ-1.1",
                    }
                ],
                "confirmed_facts_delta": ["系统名称和编写目的已确认。"],
                "open_questions_delta": ["下一轮确认软件定位。"],
                "document_patch": [
                    {
                        "plan_ref": "AP-001",
                        "operation": "append_or_update",
                        "content": "本需求规格说明用于定义默认运算软件的建设目标和需求边界。",
                        "write_policy": session.write_policy,
                    }
                ],
                "annotations": [],
                "risks": [],
                "confidence": "high",
            }
            return {**output, "raw_model_response": {**raw, "provider_normalized_output": output}}

    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_api_key", "test-deepseek-key")
    monkeypatch.setattr(requirement_analysis_client_module, "DeepSeekRequirementAnalysisClient", FakeDeepSeekClient)

    client = TestClient(create_app())
    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "默认运算软件需求规格说明",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "deepseek",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫默认运算软件，用于沉淀需求规格说明。"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    provider_logs = payload["session"]["provider_logs"]
    assert [log["stage_id"] for log in provider_logs] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]
    assert [log["call_id"] for log in provider_logs] == [
        "requirement-analysis-provider-call-0001",
        "requirement-analysis-provider-call-0002",
        "requirement-analysis-provider-call-0003",
    ]
    assert provider_logs[0]["audit"]["provider_request"]["prompt_bundle"]["stage_id"] == "intent_understanding"
    assert provider_logs[1]["audit"]["provider_request"]["prompt_bundle"]["stage_id"] == "decision_state_delta"
    assert provider_logs[1]["audit"]["provider_request"]["prompt_bundle"]["prompt_id"] == "decision_state_delta"
    assert provider_logs[2]["audit"]["provider_request"]["prompt_bundle"]["stage_id"] == "next_interaction_planning"
    assert provider_logs[1]["audit"]["provider_normalized_output"]["decision_state_delta"]["confirmed_facts"][0]["content"] == "系统名称和编写目的已确认。"
    assert provider_logs[2]["audit"]["provider_request"]["prompt_bundle"]["decision_state_json"]
    assert payload["turn"]["decision_state_document"]["title"] == "需求分析结构化状态"
    assert payload["turn"]["next_interaction_plan"]["next_question"] == "建议下一步确认软件定位。"
    assert calls[1]["stage"]["prompt_id"] == "decision_state_delta"
    assert calls[2]["stage"]["prompt_id"] == "next_interaction_planning"
    assert calls[2]["stage_input"]["decision_state"]["confirmed_facts"]


def test_requirement_analysis_lab_projects_provider_patch_to_matching_spec_node_without_confirming_first_open_question(
    monkeypatch,
) -> None:
    class FakeDeepSeekClient:
        def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
            self.model = model

        def run_stage(
            self,
            *,
            session,
            user_input: str,
            normalized: dict,
            orchestrator_id: str,
            stage: dict,
            stage_input: dict | None = None,
        ) -> dict:
            stage_id = str(stage["stage_id"])
            raw_model_response = {
                "provider_id": "deepseek",
                "model": self.model,
                "mock": False,
                "user_input": user_input,
                "orchestrator_id": orchestrator_id,
                "mode": "policy_interpreted",
                "stage_id": stage_id,
                "provider_request": {
                    "messages": [{"role": "user", "content": f"{stage_id} prompt"}],
                    "prompt_bundle": {
                        "stage_id": stage_id,
                        "prompt_id": str(stage.get("prompt_id") or stage_id),
                        "assembled_prompt": f"{stage_id} prompt",
                        "schema_json": "{}",
                    },
                },
                "provider_response": {"raw_content": "{}", "parsed_json": {}},
            }
            if stage["stage_kind"] == "intent":
                output = {
                    "intent_understanding_result": {
                        "user_goal_summary": "用户本轮直接补充了目标用户，而不是回答编写目的。",
                        "input_type": "free_supplement",
                        "relation_to_previous_interaction": "none",
                        "option_handling": "not_option",
                        "matched_option": None,
                        "supplemental_facts": ["领域专家直接使用，管理员负责初始化配置。"],
                        "target_section_candidates": ["3 功能需求 / 用户与角色"],
                        "document_strategy": "write_targeted_sections",
                        "write_task_candidate": "补写用户与角色。",
                        "review_focus_candidate": "检查用户与角色是否成文。",
                        "ambiguities": [],
                    },
                    "target_document_structure": {
                        "target_sections": ["3 功能需求 / 用户与角色"],
                        "target_anchor_paths": ["3 功能需求 / 用户与角色"],
                        "current_major_gaps": ["用户与角色仍缺正文。"],
                    },
                    "stage_task_definition": {
                        "task_summary": "补写用户与角色。",
                        "target_sections": ["3 功能需求 / 用户与角色"],
                        "non_goals": [],
                        "must_output": ["document_patch", "confirmed_facts_delta"],
                        "review_standard": "用户与角色形成完整段落。",
                    },
                    "stage_quality_constraints": {
                        "minimum_depth": "至少一段完整正文。",
                        "must_cover_dimensions": ["主要用户", "管理员职责"],
                        "assistant_reply_style": "先说明写入结果。",
                    },
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw_model_response, "provider_normalized_output": output}}
            if stage["stage_kind"] == "review":
                output = {
                    "target_review": {
                        "status": "acceptable",
                        "review_target": ["3 功能需求 / 用户与角色"],
                        "reason": "模型基于应用后的临时正文确认用户与角色已覆盖。",
                        "covered_points": ["领域专家", "管理员"],
                        "missing_aspects": [],
                        "evidence_block_ids": ["blk-0001"],
                        "evidence_fragment_ids": ["frag-0001"],
                    },
                    "global_review": {
                        "status": "move_next_node",
                        "summary": "模型建议回到第一个未完成节点。",
                        "remaining_gaps": [],
                    },
                    "compliance_result": "pass",
                    "written_fact_summary": ["领域专家", "管理员"],
                    "blocking_findings": [],
                    "blocking_reasons": [],
                    "planning_evidence": ["blk-0001", "frag-0001"],
                    "rewrite_advice": [],
                    "review_annotations": ["模型 Review 读取了应用后的临时正文。"],
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw_model_response, "provider_normalized_output": output}}
            if stage["stage_kind"] == "next_interaction":
                output = {
                    "next_interaction_plan": {
                        "planning_strategy": "move_next_node",
                        "user_message": "目标用户已写入临时正文。",
                        "next_question": "下一轮可以补充编写目的。",
                        "quick_options": [],
                        "plan_reason": "目标用户已确认，但编写目的仍为空。",
                        "review_acknowledgement": "用户与角色已覆盖。",
                        "target_spec_nodes": ["SPEC-REQ-1.1"],
                    },
                    "planning_trace": ["规划阶段选择回到第一个未完成节点。"],
                    "confidence": "high",
                }
                return {**output, "raw_model_response": {**raw_model_response, "provider_normalized_output": output}}
            output = {
                "organizer_interpretation": {
                    "summary": "用户本轮直接补充了目标用户，而不是回答编写目的。",
                    "intent": "supplement_requirement",
                    "confidence": "high",
                },
                "assistant_message": "已更新目标用户。",
                "next_suggestion": {
                    "kind": "topic",
                    "content": "下一轮可以补充编写目的。",
                    "reason": "目标用户已确认，但编写目的仍为空。",
                    "related_spec_node_ids": ["SPEC-REQ-1.1"],
                },
                "quick_options": [],
                "template_shape_assessment": {
                    "shape_type": "coarse_grained_extensible",
                    "reason": "模板允许在既有条款下补写用户与角色。",
                    "allowed_write_modes": ["append_existing_clause"],
                    "forbidden_write_modes": [],
                    "template_revision_recommendations": [],
                },
                "target_anchor_plan": [
                    {
                        "plan_id": "AP-001",
                        "decision_type": "append_existing_clause",
                        "template_clause_id": "REQ-3.1",
                        "canonical_clause_heading": "3.1 用户与角色",
                        "subtopic_action": "none",
                        "subtopic_key": "",
                        "subtopic_title": "",
                        "display_heading": "3.1 用户与角色",
                        "template_shape_ref": "coarse_grained_extensible",
                        "reason": "用户本轮直接补充了角色信息。",
                        "confidence": "high",
                        "anchor_path": "REQ-3.1",
                    }
                ],
                "confirmed_facts_delta": ["目标用户确认：领域专家直接使用，管理员负责配置。"],
                "open_questions_delta": [],
                "document_patch": [
                    {
                        "plan_ref": "AP-001",
                        "operation": "append_or_update",
                        "content": "本软件主要面向领域专家使用，管理员负责初始化配置和权限维护。",
                        "write_policy": session.write_policy,
                    }
                ],
                "annotations": [],
                "risks": [],
                "confidence": "high",
            }
            return {**output, "raw_model_response": {**raw_model_response, "provider_normalized_output": output}}

    monkeypatch.setattr(requirement_analysis_client_module.settings, "requirement_analysis_deepseek_api_key", "test-deepseek-key")
    monkeypatch.setattr(requirement_analysis_client_module, "DeepSeekRequirementAnalysisClient", FakeDeepSeekClient)

    client = TestClient(create_app())
    created = client.post(
        "/api/requirement-analysis/sessions",
        json={
            "topic": "空域运算软件需求规格探索",
            "orchestrator_id": "xg-heuristic-orchestrator",
            "provider_id": "deepseek",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert created.status_code == 200
    session = created.json()

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "主要给领域专家使用，管理员负责初始化配置。"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    questions = payload["session"]["questions"]
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-3.1"
    assert payload["session"]["turn_path"][0]["node_id"] == "SPEC-REQ-3.1"
    assert payload["session"]["turn_path"][0]["question_id"] == "Q-002"
    assert questions[0]["question_id"] == "Q-001"
    assert questions[0]["status"] == "open"
    assert questions[0]["target_section"] == "1 总则 / 编写目的"
    assert questions[1]["question_id"] == "Q-002"
    assert questions[1]["status"] == "confirmed"
    assert questions[1]["target_section"] == "3.1 用户与角色"
    assert questions[1]["resolution_fact_ids"] == ["F-001"]
    assert [question["content"] for question in questions].count(questions[0]["content"]) == 1
    assert find_spec_node(payload["session"]["spec_tree"], "SPEC-REQ-1.1")["status"] == "open"
    assert find_spec_node(payload["session"]["spec_tree"], "SPEC-REQ-3.1")["status"] == "closed"


def test_deepseek_prompt_uses_user_input_turn_contract() -> None:
    class DummyClient(DeepSeekRequirementAnalysisClient):
        def __init__(self) -> None:
            self.model = "deepseek-chat"
            self.runner_host = None

    class DummySession:
        orchestrator_id = "xg-heuristic-orchestrator"
        topic = "空域运算软件需求规格探索"
        template_id = "81433号"
        knowledge_package_id = "airspace-domain-demo"
        write_policy = "patch_suggestion_only"
        payload = {
            "next_interaction": {
                "interaction_id": "interaction-0001",
                "type": "open_question",
                "prompt": "下一轮可以确认用户角色。",
                "options": [],
                "target_spec_node_ids": ["SPEC-REQ-3.1"],
                "reason": "用户与角色章节仍缺材料。",
            },
            "last_quick_options": [],
            "spec_tree": [
                {
                    "node_id": "SPEC-ROOT",
                    "title": "需求规格说明完成度树（81433号）",
                    "target_section": "81433号 需求规格说明",
                    "status": "partial",
                    "children": [
                        {
                            "node_id": "SPEC-REQ-3.1",
                            "title": "REQ-3.1 用户与角色",
                            "target_section": "3 功能需求 / 用户与角色",
                            "question": "谁使用这个系统？请说明主要用户角色、职责和是否存在协作者或管理员。",
                            "status": "open",
                            "children": [],
                        }
                    ],
                }
            ],
            "messages": [],
            "confirmed_facts": [],
            "open_questions": [],
            "decision_state": {
                "topic": "空域运算软件需求规格探索",
                "confirmed_facts": [{"content": "系统初步定位为空域计算分析工具"}],
                "confirmed_decisions": [],
                "tentative_assumptions": [],
                "open_questions": [],
                "rejected_directions": [],
                "next_focus": "确认用户角色。",
                "chapter_projections": [],
            },
            "decision_state_document": {
                "document_id": "decision-state-document",
                "title": "需求分析结构化状态",
                "phase": "exploration_convergence",
                "sections": [],
            },
        }

    prompt_bundle = DummyClient()._build_prompt_bundle(  # noqa: SLF001
        session=DummySession(),
        user_input="主要给领域专家使用",
        normalized={"input_type": "free_text", "matched_option": None, "semantic": "主要给领域专家使用"},
        orchestrator_id="xg-heuristic-orchestrator",
        stage={"stage_id": "intent_understanding", "stage_kind": "intent", "prompt_id": "intent_understanding"},
        stage_input={},
    )
    prompt = prompt_bundle["assembled_prompt"]

    assert "用户输入是本轮 Turn 的起点" in prompt
    assert "previous_interaction" in prompt
    assert "REQ-3.1 用户与角色" in prompt
    assert "不要强行把它解释成当前 active 节点的答案" in prompt
    assert "intent_understanding_result" in prompt
    assert "stage_task_definition" in prompt
    assert "系统初步定位为空域计算分析工具" in prompt_bundle["decision_state_json"]
    assert "需求分析结构化状态" in prompt_bundle["decision_state_document_json"]


def test_deepseek_client_run_stage_parses_write_json_response_without_network() -> None:
    class DummyClient(DeepSeekRequirementAnalysisClient):
        def __init__(self) -> None:
            self.model = "deepseek-chat"
            self.runner_host = None
            self.client = FakeOpenAIClient()

        def _build_prompt_bundle(
            self,
            *,
            session,
            user_input: str,
            normalized: dict,
            orchestrator_id: str,
            stage: dict | None = None,
            stage_input: dict | None = None,
        ) -> dict:
            return {
                "orchestrator_id": orchestrator_id,
                "mode": "policy_interpreted",
                "stage_id": str((stage or {}).get("stage_id") or "write"),
                "prompt_id": str((stage or {}).get("prompt_id") or "write"),
                "assembled_prompt": "prompt",
                "context_json": '{"user_input":"这个系统叫空域运算软件"}',
                "schema_json": '{"assistant_message":"string"}',
                "policy_text": "policy",
                "prompt_text": "prompt text",
            }

    class FakeMessage:
        content = (
            '{"organizer_interpretation":{"summary":"已理解","intent":"supplement_requirement","confidence":"high"},'
            '"assistant_message":"已更新需求规格。",'
            '"next_suggestion":{"kind":"topic","content":"继续补齐用户角色","reason":"角色仍缺","related_spec_node_ids":["SPEC-REQ-3.1"]},'
            '"quick_options":[{"key":"A","label":"领域专家直接使用","recommended":true}],'
            '"template_shape_assessment":{"shape_type":"coarse_grained_extensible","reason":"模板允许补写。",'
            '"allowed_write_modes":["append_existing_clause"],"forbidden_write_modes":[],"template_revision_recommendations":[]},'
            '"target_anchor_plan":[{"plan_id":"AP-001","decision_type":"append_existing_clause","template_clause_id":"REQ-1.1",'
            '"canonical_clause_heading":"1.1 编写目的","subtopic_action":"none","subtopic_key":"","subtopic_title":"",'
            '"display_heading":"1.1 编写目的","template_shape_ref":"coarse_grained_extensible","reason":"用户说明系统目标。",'
            '"confidence":"high","anchor_path":"REQ-1.1"}],'
            '"confirmed_facts_delta":["系统用于空域计算分析"],'
            '"open_questions_delta":["谁使用这个系统？"],'
            '"document_patch":[{"plan_ref":"AP-001","content":"本文档定义空域计算分析软件需求。"}],'
            '"annotations":[],"risks":[],"confidence":"high"}'
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAIClient:
        chat = FakeChat()

    class DummySession:
        orchestrator_id = "xg-heuristic-orchestrator"
        write_policy = "patch_suggestion_only"

    output = DummyClient().run_stage(
        session=DummySession(),
        user_input="这个系统叫空域运算软件",
        normalized={"input_type": "free_text", "semantic": "这个系统叫空域运算软件"},
        orchestrator_id="xg-heuristic-orchestrator",
        stage={"stage_id": "write", "stage_kind": "write", "prompt_id": "write"},
        stage_input={},
    )

    assert output["organizer_interpretation"]["confidence"] == "high"
    assert output["assistant_message"] == "已更新需求规格。"
    assert output["quick_options"][0]["label"] == "领域专家直接使用"
    assert output["target_anchor_plan"][0]["template_clause_id"] == "REQ-1.1"
    assert output["document_patch"][0]["plan_ref"] == "AP-001"
    assert output["document_patch"][0]["write_policy"] == "patch_suggestion_only"
    assert output["raw_model_response"]["mock"] is False
    assert output["raw_model_response"]["provider_request"]["prompt_bundle"]["assembled_prompt"] == "prompt"
    assert output["raw_model_response"]["provider_request"]["prompt_bundle"]["decision_state_json"] == ""
    assert output["raw_model_response"]["provider_request"]["prompt_bundle"]["decision_state_document_json"] == ""
    assert output["raw_model_response"]["provider_request"]["messages"][1]["content"] == "prompt"
    assert "已更新需求规格" in output["raw_model_response"]["provider_response"]["raw_content"]
    assert output["raw_model_response"]["provider_response"]["parsed_json"]["assistant_message"] == "已更新需求规格。"
    assert output["raw_model_response"]["provider_normalized_output"]["assistant_message"] == "已更新需求规格。"
