from fastapi.testclient import TestClient

from app.requirement_analysis.deepseek_client import DeepSeekRequirementAnalysisClient
from app.requirement_analysis import deepseek_client as requirement_analysis_client_module
from app.main import create_app


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
    assert "spec_execution" in turn
    assert "post_update_review" in turn
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


def test_requirement_analysis_lab_session_turn_and_recovery() -> None:
    client = TestClient(create_app())

    orchestrators = client.get("/api/requirement-analysis/orchestrators")
    assert orchestrators.status_code == 200
    items = orchestrators.json()["items"]
    assert items[0]["orchestrator_id"] == "xg-heuristic-orchestrator"
    assert items[0]["status"] == "active"
    assert items[0]["document_type"] == "xg"
    assert items[0]["contract"] == "xg-orchestrator-contract@1"
    assert items[0]["mode"] == "policy_interpreted"
    assert {item["orchestrator_id"] for item in items} >= {
        "xg-heuristic-orchestrator",
        "xg-strong-rule-orchestrator",
    }
    strong_rule = next(item for item in items if item["orchestrator_id"] == "xg-strong-rule-orchestrator")
    assert strong_rule["mode"] == "local_runner"
    assert "rule_based_flow" in strong_rule["capabilities"]

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
    assert session["orchestrator"]["orchestrator_id"] == "xg-heuristic-orchestrator"
    assert session["orchestrator"]["document_type"] == "xg"
    assert session["orchestrator"]["mode"] == "policy_interpreted"
    assert session["stable_contract"]["formal_document"] is True
    assert session["write_policy"] == "patch_suggestion_only"
    assert session["document_patch"] == []
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
        "question": "谁使用这个系统？请说明主要用户角色、职责和是否存在协作者或管理员。",
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
    assert payload["turn"]["turn_id"] == "turn-0001"
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["previous_interaction"]["type"] == "none"
    assert payload["turn"]["input_relation"]["relation"] == "none"
    assert payload["turn"]["closure_decision"]["status"] == "closed"
    assert payload["turn"]["post_update_review"]["previous_interaction_resolved"] is True
    assert payload["turn"]["post_update_review"]["current_spec_node_sufficient"] is True
    assert "空域运算软件" in payload["turn"]["spec_execution"]["confirmed_facts"][0]
    assert payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-1.1"
    assert any("用户输入是本轮 Turn 起点" in item for item in payload["turn"]["decision_trace"])
    assert payload["turn"]["normalized_input"]["input_type"] == "free_text"
    assert "基于你的输入，本轮更新了" in payload["turn"]["spec_execution"]["assistant_message"]
    assert "1 总则 / 编写目的" in payload["turn"]["spec_execution"]["assistant_message"]
    assert "软件定位" in payload["turn"]["next_interaction"]["prompt"]
    assert payload["turn"]["next_interaction"]["type"] == "choice_question"
    assert [option["label"] for option in payload["turn"]["next_interaction"]["options"]] == [
        "计算分析工具",
        "协同规划平台",
        "二者兼有但先做分析",
    ]
    assert payload["turn"]["spec_execution"]["document_patch"][0]["section"] == "1 总则 / 编写目的"
    assert payload["turn"]["spec_execution"]["document_patch"][0]["operation"] == "append_or_update"
    assert payload["turn"]["confidence"] == "medium"
    assert "空域运算软件" in payload["session"]["confirmed_facts"][0]
    assert payload["session"]["document_patch"][0]["section"] == "1 总则 / 编写目的"
    assert payload["session"]["questions"][0]["question_id"] == "Q-001"
    assert payload["session"]["questions"][0]["status"] == "confirmed"
    assert payload["session"]["questions"][0]["resolution_fact_ids"] == ["F-001"]
    assert payload["session"]["questions"][1]["question_id"] == "Q-002"
    assert payload["session"]["questions"][1]["status"] == "open"
    assert payload["session"]["facts"][0]["fact_id"] == "F-001"
    assert payload["session"]["facts"][0]["source_question_ids"] == ["Q-001"]
    assert payload["session"]["patches"][0]["patch_id"] == "P-001"
    assert payload["session"]["patches"][0]["target_section"] == "1 总则 / 编写目的"
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
    assert second_payload["turn"]["previous_interaction"]["interaction_id"] == payload["turn"]["next_interaction"]["interaction_id"]
    assert second_payload["turn"]["input_relation"]["relation"] == "answered"
    assert second_payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-2.1"
    assert "谁使用这个系统" in second_payload["turn"]["next_interaction"]["prompt"]
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
    assert second_payload["session"]["patches"][1]["target_section"] == "2 项目概述 / 软件定位"
    assert second_payload["session"]["patches"][1]["source_question_ids"] == ["Q-002"]
    assert second_payload["session"]["active_spec_node_id"] == "SPEC-REQ-3.1"
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
    assert session["orchestrator"]["orchestrator_id"] == "xg-strong-rule-orchestrator"
    assert session["orchestrator"]["document_type"] == "xg"
    assert session["orchestrator"]["mode"] == "local_runner"
    assert "strict_turn_closure" in session["orchestrator"]["capabilities"]

    turn = client.post(
        f"/api/requirement-analysis/sessions/{session['session_id']}/turns",
        json={"user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert_new_turn_contract(payload["turn"])
    assert payload["turn"]["spec_execution"]["interpretation"]["intent"] == "supplement_requirement"
    assert "强规则组织器" in payload["turn"]["spec_execution"]["assistant_message"]
    assert payload["turn"]["spec_execution"]["affected_spec_nodes"][0]["node_id"] == "SPEC-REQ-1.1"
    assert payload["turn"]["closure_decision"]["status"] == "closed"
    assert any("强规则组织器" in item for item in payload["turn"]["decision_trace"])
    assert payload["turn"]["raw_model_response"]["orchestrator_id"] == "xg-strong-rule-orchestrator"
    assert payload["turn"]["raw_model_response"]["mode"] == "local_runner"
    assert payload["turn"]["raw_model_response"]["runner_invoked"] is True
    assert payload["turn"]["raw_model_response"]["runner_entry"].endswith("xg-strong-rule-orchestrator/runner.py")
    assert payload["session"]["provider_logs"][0]["orchestrator_id"] == "xg-strong-rule-orchestrator"
    assert payload["session"]["provider_logs"][0]["orchestrator_mode"] == "local_runner"
    assert payload["session"]["active_spec_node_id"] == "SPEC-REQ-2.1"


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

        def run_turn(self, *, session, user_input: str, normalized: dict) -> dict:
            captured["session_provider"] = session.provider_id
            captured["user_input"] = user_input
            captured["normalized"] = normalized
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
                "confirmed_facts_delta": ["DeepSeek 确认系统初步定位为空域计算分析工具"],
                "open_questions_delta": ["输入数据来源尚未确认。"],
                "document_patch": [
                    {
                        "section": "1.1 系统目标",
                        "operation": "append_or_update",
                        "content": "本系统支持空域计算分析任务的需求澄清。",
                        "write_policy": session.write_policy,
                    }
                ],
                "annotations": ["DeepSeek Provider 返回结构化 Turn 输出。"],
                "risks": [],
                "confidence": "medium",
                "raw_model_response": {"provider_id": "deepseek", "mock": False},
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
    assert payload["session"]["provider_logs"][0]["provider_id"] == "deepseek"
    assert payload["session"]["provider_logs"][0]["model"] == "deepseek-chat"
    assert payload["session"]["provider_logs"][0]["status"] == "completed"
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


def test_requirement_analysis_lab_projects_provider_patch_to_matching_spec_node_without_confirming_first_open_question(
    monkeypatch,
) -> None:
    class FakeDeepSeekClient:
        def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
            self.model = model

        def run_turn(self, *, session, user_input: str, normalized: dict) -> dict:
            return {
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
                "confirmed_facts_delta": ["目标用户确认：领域专家直接使用，管理员负责配置。"],
                "open_questions_delta": [],
                "document_patch": [
                    {
                        "section": "3 功能需求 / 用户与角色",
                        "operation": "append_or_update",
                        "content": "本软件主要面向领域专家使用，管理员负责初始化配置和权限维护。",
                        "write_policy": session.write_policy,
                    }
                ],
                "annotations": [],
                "risks": [],
                "confidence": "high",
                "raw_model_response": {"provider_id": "deepseek", "mock": False},
            }

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
    assert questions[1]["target_section"] == "3 功能需求 / 用户与角色"
    assert questions[1]["resolution_fact_ids"] == ["F-001"]
    assert [question["content"] for question in questions].count(questions[0]["content"]) == 1
    assert find_spec_node(payload["session"]["spec_tree"], "SPEC-REQ-1.1")["status"] == "open"
    assert find_spec_node(payload["session"]["spec_tree"], "SPEC-REQ-3.1")["status"] == "closed"


def test_deepseek_prompt_uses_user_input_turn_contract() -> None:
    class DummyClient(DeepSeekRequirementAnalysisClient):
        def __init__(self) -> None:
            self.model = "deepseek-chat"

    class DummySession:
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
        }

    prompt = DummyClient()._build_prompt(  # noqa: SLF001
        session=DummySession(),
        user_input="主要给领域专家使用",
        normalized={"input_type": "free_text", "matched_option": None, "semantic": "主要给领域专家使用"},
    )

    assert "用户输入是本轮 Turn 的起点" in prompt
    assert "previous_interaction" in prompt
    assert "REQ-3.1 用户与角色" in prompt
    assert "不要把用户输入强行解释为对某个 active 节点的回答" in prompt
    assert "next_interaction" in prompt
    assert "post_update_review" in prompt


def test_deepseek_client_run_turn_parses_json_response_without_network() -> None:
    class DummyClient(DeepSeekRequirementAnalysisClient):
        def __init__(self) -> None:
            self.model = "deepseek-chat"
            self.runner_host = None
            self.client = FakeOpenAIClient()

        def _build_prompt_bundle(self, *, session, user_input: str, normalized: dict, orchestrator_id: str) -> dict:
            return {"assembled_prompt": "prompt"}

    class FakeMessage:
        content = (
            '{"organizer_interpretation":{"summary":"已理解","intent":"supplement_requirement","confidence":"high"},'
            '"assistant_message":"已更新需求规格。",'
            '"next_suggestion":{"kind":"topic","content":"继续补齐用户角色","reason":"角色仍缺","related_spec_node_ids":["SPEC-REQ-3.1"]},'
            '"quick_options":[{"key":"A","label":"领域专家直接使用","recommended":true}],'
            '"confirmed_facts_delta":["系统用于空域计算分析"],'
            '"open_questions_delta":["谁使用这个系统？"],'
            '"document_patch":[{"section":"1 总则 / 编写目的","content":"本文档定义空域计算分析软件需求。"}],'
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

    output = DummyClient().run_turn(
        session=DummySession(),
        user_input="这个系统叫空域运算软件",
        normalized={"input_type": "free_text", "semantic": "这个系统叫空域运算软件"},
    )

    assert output["organizer_interpretation"]["confidence"] == "high"
    assert output["assistant_message"] == "已更新需求规格。"
    assert output["quick_options"][0]["label"] == "领域专家直接使用"
    assert output["document_patch"][0]["write_policy"] == "patch_suggestion_only"
    assert output["raw_model_response"]["mock"] is False
