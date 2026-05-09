import json
import sys

import httpx
import pytest

from app.orchestrators.adapters.plugin_turn_result_materializer import PluginTurnResultMaterializer
from app.orchestrators.plugin_contracts import (
    OrchestratorPluginManifest,
    OrchestratorRunRequest,
    OrchestratorRunResult,
)
from app.orchestrators.plugin_registry import OrchestratorPluginRegistry
from app.orchestrators.plugin_result_normalizer import OrchestratorPluginResultNormalizer
from app.orchestrators.adapters.base import load_orchestrator_plugin_adapter
from app.requirement_analysis.session_service import RequirementAnalysisSessionService


def test_observable_orchestrator_plugin_manifest_contract() -> None:
    manifest = OrchestratorPluginManifest(
        plugin_id="xg-local-heuristic-orchestrator",
        name="XG Local Heuristic Orchestrator",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=10,
        capabilities={
            "filled_document_text": False,
            "document_patch": True,
            "stage_results": True,
            "stage_audits": True,
            "provider_logs": True,
            "decision_trace": True,
            "review_after_apply": True,
            "spec_tree_update": True,
            "streaming_events": False,
        },
        requires={"template": True, "model_provider": "optional"},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="LocalXGOrchestratorPluginAdapter",
    )

    assert manifest.plugin_id == "xg-local-heuristic-orchestrator"
    assert manifest.observability_level == "full"
    assert manifest.capabilities["stage_audits"] is True
    assert manifest.to_api()["contract"] == "xg-observable-orchestrator-contract@1"


def test_orchestrator_run_request_and_result_contract() -> None:
    request = OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={
            "session_id": "ra-001",
            "topic": "空域运算软件需求规格探索",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "orchestrator_id": "xg-local-heuristic-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "write_policy": "patch_suggestion_only",
        },
        turn={
            "turn_id": "turn-0001",
            "turn_index": 1,
            "user_input": "这个系统叫空域运算软件",
            "normalized_input": {"input_type": "free_text", "semantic": "这个系统叫空域运算软件"},
            "previous_interaction": {"type": "none"},
            "input_relation": {"relation": "none"},
        },
        template={
            "template_id": "81433号",
            "format": "structured",
            "content": "",
            "parsed_structure": {"source": "spec_tree"},
        },
        document_context={
            "working_document": {"document_id": "lab-working-document", "blocks": []},
            "active_spec_node": {"node_id": "SPEC-REQ-1.1", "target_section": "1 总则 / 编写目的"},
            "spec_tree": [],
            "confirmed_facts": [],
            "open_questions": [],
            "patches": [],
            "history_summary": "",
        },
        execution_options={
            "expected_output": "both",
            "observability_required": "full",
            "streaming_enabled": False,
        },
    )
    assert request.turn["turn_id"] == "turn-0001"
    assert request.template["format"] == "structured"

    result = OrchestratorRunResult(
        contract_version="xg-observable-orchestrator-contract@1",
        plugin={
            "plugin_id": "xg-local-heuristic-orchestrator",
            "plugin_type": "local_package",
            "observability_level": "full",
        },
        final_output={
            "filled_document_text": "",
            "document_patch": [{"plan_ref": "AP-001", "operation": "append_or_update", "content": "软件名称为：空域运算软件。"}],
            "changed_sections": ["REQ-1.1"],
            "completion_status": "partial",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "本轮已补入临时正文。",
            "next_question": "请确认软件定位。",
            "quick_options": [],
            "suggested_focus": {"target_spec_node_ids": ["SPEC-REQ-2.1"]},
        },
        process_output={
            "stage_results": [],
            "stage_audits": [],
            "decision_trace": ["插件输出通过合同校验。"],
            "provider_logs": [],
            "review_after_apply_result": {},
            "annotations": [],
            "risks": [],
        },
        state_output={
            "confirmed_facts_delta": ["软件名称初步确认：空域运算软件"],
            "open_questions_delta": ["请确认软件定位。"],
            "spec_tree_update": {},
            "working_document_update": {},
            "turn_path_update": {},
        },
        raw_output={
            "raw_plugin_response": {},
            "raw_model_response": {},
            "raw_workflow_trace": {},
        },
    )
    assert result.plugin["observability_level"] == "full"
    assert result.final_output["document_patch"][0]["plan_ref"] == "AP-001"


def test_plugin_registry_lists_local_and_dify_plugins() -> None:
    registry = OrchestratorPluginRegistry()
    plugins = registry.list_plugins()
    plugin_ids = {plugin.plugin_id for plugin in plugins}

    assert "xg-local-heuristic-orchestrator" in plugin_ids
    assert "xg-dify-workflow-orchestrator" in plugin_ids
    assert "brainstorm-v1-dify-workflow" in plugin_ids
    assert "xg-local-strong-rule-orchestrator" not in plugin_ids

    dify = registry.require("xg-dify-workflow-orchestrator")
    assert dify.plugin_type == "dify_workflow"
    assert dify.observability_level == "limited"
    assert dify.capabilities["filled_document_text"] is True
    assert dify.capabilities["stage_audits"] is False

    brainstorm_dify = registry.require("brainstorm-v1-dify-workflow")
    assert brainstorm_dify.plugin_type == "dify_workflow"
    assert brainstorm_dify.package_id == "brainstorm-v1"
    assert brainstorm_dify.observability_level == "limited"
    assert brainstorm_dify.capabilities["decision_trace"] is True
    assert brainstorm_dify.capabilities["stage_audits"] is False


def test_plugin_registry_resolves_manifest_aliases_and_package_ids() -> None:
    registry = OrchestratorPluginRegistry()

    heuristic = registry.require("xg-heuristic-orchestrator")

    assert heuristic.plugin_id == "xg-local-heuristic-orchestrator"
    assert heuristic.package_id == "xg-heuristic-orchestrator"
    assert heuristic.aliases == ("xg-heuristic-orchestrator",)
    assert registry.local_package_id_for_plugin("xg-local-heuristic-orchestrator") == "xg-heuristic-orchestrator"
    assert registry.local_package_id_for_plugin("xg-heuristic-orchestrator") == "xg-heuristic-orchestrator"
    try:
        registry.require("xg-strong-rule-orchestrator")
    except ValueError as exc:
        assert "unsupported orchestrator" in str(exc)
    else:
        raise AssertionError("removed strong-rule orchestrator should not resolve by alias")


def test_plugin_manifest_requires_local_adapter_entry() -> None:
    try:
        OrchestratorPluginManifest(
            plugin_id="xg-no-entry-orchestrator",
            name="No Entry",
            plugin_type="local_package",
            capabilities={"document_patch": True},
            requires={"template": True},
            adapter_entry="local_xg",
        )
    except ValueError as exc:
        assert "adapter_module" in str(exc)
        assert "adapter_class" in str(exc)
    else:
        raise AssertionError("manifest without local adapter entry should fail")


def test_policy_interpreted_stage_strategy_must_declare_explicit_runtime_fields() -> None:
    registry = OrchestratorPluginRegistry()
    plugin_ids = ("xg-local-heuristic-orchestrator", "brainstorm-v1")

    for plugin_id in plugin_ids:
        package_id = registry.local_package_id_for_plugin(plugin_id)
        spec_strategy_path = f"orchestrators/xg/{package_id}/spec_strategy.json"
        import json
        from pathlib import Path

        payload = json.loads(Path(spec_strategy_path).read_text(encoding="utf-8"))
        stages = list((payload.get("turn_strategy") or {}).get("stages") or [])
        assert stages, f"{plugin_id} must declare turn_strategy.stages"
        for stage in stages:
            assert stage.get("stage_id"), f"{plugin_id} stage missing stage_id"
            assert stage.get("stage_kind"), f"{plugin_id} stage missing stage_kind"
            assert stage.get("execution_mode"), f"{plugin_id} stage missing execution_mode"
            assert stage.get("prompt_id"), f"{plugin_id} stage missing prompt_id"
            assert stage.get("input_sources") is not None, f"{plugin_id} stage missing input_sources"
            assert stage.get("adopt_fields") is not None, f"{plugin_id} stage missing adopt_fields"
            assert stage.get("failure_policy"), f"{plugin_id} stage missing failure_policy"


def test_adapter_loader_instantiates_plugins_from_manifest_entry() -> None:
    registry = OrchestratorPluginRegistry()
    manifest = registry.require("xg-dify-workflow-orchestrator")

    adapter = load_orchestrator_plugin_adapter(manifest)
    result = adapter.run(
        OrchestratorRunRequest(
            contract_version="xg-observable-orchestrator-contract@1",
            session={
                "session_id": "ra-001",
                "topic": "空域运算软件需求规格探索",
                "template_id": "81433号",
                "knowledge_package_id": "airspace-domain-demo",
                "orchestrator_id": "xg-dify-workflow-orchestrator",
                "provider_id": "mock",
                "model": "mock-requirement-analysis-v1",
                "write_policy": "patch_suggestion_only",
            },
            turn={
                "turn_id": "turn-0001",
                "turn_index": 1,
                "user_input": "这个系统叫空域运算软件",
                "normalized_input": {"input_type": "free_text", "semantic": "这个系统叫空域运算软件"},
                "previous_interaction": {"type": "none"},
                "input_relation": {"relation": "none"},
            },
            template={"template_id": "81433号", "format": "markdown", "content": "# 需求规格说明\n", "parsed_structure": {}},
            document_context={
                "working_document": {"document_id": "lab-working-document", "blocks": []},
                "active_spec_node": {"node_id": "SPEC-REQ-1.1", "target_section": "1 总则 / 编写目的"},
                "spec_tree": [],
                "confirmed_facts": [],
                "open_questions": [],
                "patches": [],
                "history_summary": "",
            },
            execution_options={"expected_output": "full_document", "observability_required": "limited", "streaming_enabled": False},
        )
    )

    assert result.plugin["plugin_id"] == "xg-dify-workflow-orchestrator"
    assert result.plugin["observability_level"] == "limited"


def _brainstorm_dify_request() -> OrchestratorRunRequest:
    return OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={
            "session_id": "ra-001",
            "topic": "空域运算软件需求规格探索",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "orchestrator_id": "brainstorm-v1-dify-workflow",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "write_policy": "patch_suggestion_only",
        },
        turn={
            "turn_id": "turn-0001",
            "turn_index": 1,
            "user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求",
            "normalized_input": {
                "input_type": "free_text",
                "semantic": "这个系统叫空域运算软件，主要解决空域计算分析需求",
            },
            "previous_interaction": {"type": "none"},
            "input_relation": {"relation": "none"},
        },
        template={"template_id": "81433号", "format": "structured", "content": "", "parsed_structure": {}},
        document_context={
            "state": {},
            "working_document": {"document_id": "lab-working-document", "blocks": []},
            "active_spec_node": {
                "node_id": "SPEC-REQ-1.1",
                "title": "REQ-1.1 编写目的",
                "target_section": "1 总则 / 编写目的",
                "question": "系统要做什么？",
            },
            "spec_tree": [],
            "confirmed_facts": [],
            "open_questions": [],
            "patches": [],
            "history_summary": "",
        },
        execution_options={"expected_output": "both", "observability_required": "limited", "streaming_enabled": False},
    )


def test_brainstorm_v1_dify_workflow_adapter_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    registry = OrchestratorPluginRegistry()
    manifest = registry.require("brainstorm-v1-dify-workflow")
    adapter = load_orchestrator_plugin_adapter(manifest)

    with pytest.raises(ValueError, match="DIFY_API_KEY"):
        adapter.run(_brainstorm_dify_request())


def test_brainstorm_v1_dify_workflow_adapter_calls_remote_dify_when_configured(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, *, headers, json, timeout, trust_env):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        captured["trust_env"] = trust_env
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-remote-001",
                "data": {
                    "id": "run-remote-001",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "assistant_message": "远端 Dify 已完成。",
                                "next_question": "请继续确认软件背景。",
                                "quick_options": [],
                                "filled_document_text": "围绕当前章节，空域运算软件用于空域计算分析。",
                                "document_patch": [
                                    {
                                        "plan_ref": "BRAINSTORM-DIFY-AP-001",
                                        "operation": "append_or_update",
                                        "content": "围绕当前章节，空域运算软件用于空域计算分析。",
                                        "write_policy": "patch_suggestion_only",
                                    }
                                ],
                                "target_anchor_plan": [],
                                "changed_sections": ["1 总则 / 编写目的"],
                                "completion_status": "partial",
                                "confidence": "medium",
                                "confirmed_facts_delta": ["空域运算软件用于空域计算分析"],
                                "open_questions_delta": ["请继续确认软件背景。"],
                                "decision_state_delta": {
                                    "confirmed_facts": [
                                        {
                                            "item_id": "DS-F-001",
                                            "content": "空域运算软件用于空域计算分析",
                                            "source_turn_id": "turn-0001",
                                            "target_section": "1 总则 / 编写目的",
                                            "status": "active",
                                        }
                                    ],
                                    "confirmed_decisions": [],
                                    "tentative_assumptions": [],
                                    "open_questions": [],
                                    "rejected_directions": [],
                                    "chapter_projections": [],
                                    "next_focus": "请继续确认软件背景。",
                                },
                                "decision_trace": [{"step": "remote", "decision": "called dify"}],
                                "annotations": ["remote dify"],
                                "risks": [],
                                "raw_workflow_trace": {"workflow_id": "remote-workflow", "run_id": "run-remote-001"},
                            },
                            ensure_ascii=False,
                        )
                    },
                },
            },
        )

    json_module = json
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    monkeypatch.setenv("DIFY_RESPONSE_MODE", "blocking")
    monkeypatch.setenv("DIFY_WORKFLOW_ID", "workflow-config-id")
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    result = adapter.run(_brainstorm_dify_request())

    assert captured["url"] == "http://dify.local/v1/workflows/run"
    assert captured["headers"]["Authorization"] == "Bearer test-dify-key"
    assert captured["trust_env"] is False
    assert captured["json"]["response_mode"] == "blocking"
    assert captured["json"]["user"] == "codefactoryv2"
    assert captured["json"]["inputs"]["user_input"] == "这个系统叫空域运算软件，主要解决空域计算分析需求"
    assert captured["json"]["inputs"]["active_spec_node_json"]
    assert result.plugin["plugin_id"] == "brainstorm-v1-dify-workflow"
    assert result.plugin["plugin_type"] == "dify_workflow"
    assert result.plugin["observability_level"] == "limited"
    assert result.final_output["filled_document_text"] == "围绕当前章节，空域运算软件用于空域计算分析。"
    assert result.interaction_output["assistant_message"] == "远端 Dify 已完成。"
    assert result.state_output["decision_state_delta"]["confirmed_facts"]
    assert result.state_output["decision_state_document"]["title"] == "需求分析结构化状态"
    assert result.process_output["stage_audits"] == []
    assert result.raw_output["raw_workflow_trace"]["remote"] is True
    assert result.raw_output["raw_workflow_trace"]["workflow_run_id"] == "run-remote-001"
    assert result.raw_output["turn_execution_result"].turn["decision_state_delta"]["confirmed_facts"]


def test_brainstorm_v1_dify_workflow_adapter_replaces_open_questions_on_draft_compose(monkeypatch) -> None:
    base_request = _brainstorm_dify_request()
    json_module = json
    request = base_request.model_copy(
        update={
            "document_context": {
                **base_request.document_context,
                "state": {
                    "decision_state": {
                        "topic": "空域运算软件需求规格探索",
                        "confirmed_facts": [],
                        "confirmed_decisions": [],
                        "tentative_assumptions": [],
                        "open_questions": [
                            {
                                "item_id": "Q-001",
                                "content": "组织器策略问题：请先确认软件名称、背景领域和编写目的。",
                                "target_section": "1 总则 / 编写目的",
                                "status": "open",
                            }
                        ],
                        "rejected_directions": [],
                        "next_focus": "",
                        "chapter_projections": [],
                    }
                },
                "open_questions": [
                    {
                        "question_id": "Q-001",
                        "content": "组织器策略问题：请先确认软件名称、背景领域和编写目的。",
                        "target_section": "1 总则 / 编写目的",
                        "status": "open",
                    }
                ],
            }
        }
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-remote-002",
                "data": {
                    "id": "run-remote-002",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "assistant_message": "已输出草案。",
                                "next_question": "请确认是否接受当前草案，或选择继续细化哪个缺口？",
                                "quick_options": [{"key": "A", "label": "接受草案并进入人工审阅", "recommended": True}],
                                "filled_document_text": "1 总则 / 编写目的\n本文用于明确空域运算软件的需求范围。",
                                "document_patch": [
                                    {
                                        "plan_ref": "BRAINSTORM-DIFY-DRAFT-001",
                                        "operation": "append_or_update",
                                        "content": "本文用于明确空域运算软件的需求范围。",
                                        "write_policy": "patch_suggestion_only",
                                        "target_section": "1 总则 / 编写目的",
                                        "anchor_path": "REQ-1.1",
                                    }
                                ],
                                "changed_sections": ["1 总则 / 编写目的"],
                                "completion_status": "partial",
                                "confidence": "high",
                                "confirmed_facts_delta": [],
                                "open_questions_delta": ["需补充部署约束。"],
                                "decision_state_delta": {
                                    "confirmed_facts": [],
                                    "confirmed_decisions": [],
                                    "tentative_assumptions": [],
                                    "open_questions": [
                                        {
                                            "item_id": "DS-Q-001",
                                            "content": "需补充部署约束。",
                                            "target_section": "待确认事项",
                                            "status": "deferred_to_draft_gap",
                                        }
                                    ],
                                    "rejected_directions": [],
                                    "chapter_projections": [],
                                    "next_focus": "请确认是否接受当前草案，或选择继续细化哪个缺口？",
                                },
                                "decision_trace": [],
                                "annotations": [],
                                "risks": ["需补充部署约束。"],
                                "raw_workflow_trace": {"workflow_id": "remote-workflow", "run_id": "run-remote-002", "branch_taken": "draft_compose"},
                            },
                            ensure_ascii=False,
                        )
                    },
                },
            },
        )

    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    result = adapter.run(request)

    questions = result.raw_output["turn_execution_result"].state_patch["decision_state"]["open_questions"]
    assert questions == [
        {
            "item_id": "DS-Q-001",
            "content": "需补充部署约束。",
            "target_section": "待确认事项",
            "status": "deferred_to_draft_gap",
        }
    ]
    assert result.state_output["open_questions_delta"] == ["需补充部署约束。"]


def test_plugin_turn_result_materializer_preserves_structured_document_patches() -> None:
    materializer = PluginTurnResultMaterializer()
    request = _brainstorm_dify_request()
    result = OrchestratorRunResult(
        contract_version=request.contract_version,
        plugin={
            "plugin_id": "brainstorm-v1-dify-workflow",
            "plugin_type": "dify_workflow",
            "observability_level": "limited",
        },
        final_output={
            "filled_document_text": (
                "1 总则 / 编写目的\n空域运算软件用于空域计算分析。\n\n"
                "3 功能需求 / 核心业务流程\n导入数据后执行空域评估。"
            ),
            "document_patch": [
                {
                    "operation": "append_or_update",
                    "anchor_path": "REQ-1.1",
                    "target_section": "1 总则 / 编写目的",
                    "content": "空域运算软件用于空域计算分析。",
                },
                {
                    "operation": "append_or_update",
                    "anchor_path": "REQ-3.2",
                    "target_section": "3 功能需求 / 核心业务流程",
                    "content": "导入数据后执行空域评估。",
                },
            ],
            "changed_sections": ["1 总则 / 编写目的", "3 功能需求 / 核心业务流程"],
            "completion_status": "partial",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "已生成章节化补丁。",
            "next_question": "是否继续补充异常处理？",
            "quick_options": [],
            "suggested_focus": {},
        },
        process_output={
            "stage_results": [],
            "stage_audits": [],
            "decision_trace": [],
            "provider_logs": [],
            "review_after_apply_result": {},
            "annotations": [],
            "risks": [],
        },
        state_output={
            "confirmed_facts_delta": [],
            "open_questions_delta": [],
            "spec_tree_update": {},
            "working_document_update": {},
            "turn_path_update": {},
        },
        raw_output={
            "raw_plugin_response": {},
            "raw_model_response": {},
            "raw_workflow_trace": {},
        },
    )

    turn_result = materializer.materialize(request=request, result=result)

    assert len(turn_result.turn["spec_execution"]["document_patch"]) == 2
    assert [patch["anchor_path"] for patch in turn_result.turn["spec_execution"]["document_patch"]] == [
        "REQ-1.1",
        "REQ-3.2",
    ]
    assert [plan["anchor_path"] for plan in turn_result.turn["spec_execution"]["target_anchor_plan"]] == [
        "REQ-1.1",
        "REQ-3.2",
    ]
    assert [block["anchor_path"] for block in turn_result.state_patch["working_document"]["blocks"]] == [
        "REQ-1.1",
        "REQ-3.2",
    ]


def test_plugin_turn_result_materializer_falls_back_to_filled_document_text_when_document_patch_missing() -> None:
    materializer = PluginTurnResultMaterializer()
    request = _brainstorm_dify_request()
    result = OrchestratorRunResult(
        contract_version=request.contract_version,
        plugin={
            "plugin_id": "xg-dify-workflow-orchestrator",
            "plugin_type": "dify_workflow",
            "observability_level": "limited",
        },
        final_output={
            "filled_document_text": "围绕当前章节，空域运算软件用于空域计算分析。",
            "document_patch": [],
            "changed_sections": ["1 总则 / 编写目的"],
            "completion_status": "partial",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "已生成整篇正文。",
            "next_question": "请继续确认软件背景。",
            "quick_options": [],
            "suggested_focus": {},
        },
        process_output={
            "stage_results": [],
            "stage_audits": [],
            "decision_trace": [],
            "provider_logs": [],
            "review_after_apply_result": {},
            "annotations": [],
            "risks": [],
        },
        state_output={
            "confirmed_facts_delta": [],
            "open_questions_delta": [],
            "spec_tree_update": {},
            "working_document_update": {},
            "turn_path_update": {},
        },
        raw_output={
            "raw_plugin_response": {},
            "raw_model_response": {},
            "raw_workflow_trace": {},
        },
    )

    turn_result = materializer.materialize(request=request, result=result)

    assert len(turn_result.turn["spec_execution"]["document_patch"]) == 1
    assert turn_result.turn["spec_execution"]["document_patch"][0]["plan_ref"] == "AP-PLUGIN-001"
    assert turn_result.state_patch["working_document"]["blocks"][0]["anchor_path"] == "REQ-1.1"


def test_removed_strong_rule_plugin_is_not_loadable(db_session) -> None:
    registry = OrchestratorPluginRegistry()

    try:
        registry.require("xg-local-strong-rule-orchestrator")
    except ValueError as exc:
        assert "unsupported orchestrator" in str(exc)
    else:
        raise AssertionError("removed strong-rule plugin should not be loadable")


def test_dify_workflow_plugin_returns_limited_observability_result() -> None:
    registry = OrchestratorPluginRegistry()
    manifest = registry.require("xg-dify-workflow-orchestrator")
    adapter = load_orchestrator_plugin_adapter(manifest)
    request = OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={
            "session_id": "ra-001",
            "topic": "空域运算软件需求规格探索",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "orchestrator_id": "xg-dify-workflow-orchestrator",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "write_policy": "patch_suggestion_only",
        },
        turn={
            "turn_id": "turn-0001",
            "turn_index": 1,
            "user_input": "这个系统叫空域运算软件",
            "normalized_input": {"input_type": "free_text", "semantic": "这个系统叫空域运算软件"},
            "previous_interaction": {"type": "none"},
            "input_relation": {"relation": "none"},
        },
        template={"template_id": "81433号", "format": "markdown", "content": "# 需求规格说明\n", "parsed_structure": {}},
        document_context={
            "working_document": {"document_id": "lab-working-document", "blocks": []},
            "active_spec_node": {"node_id": "SPEC-REQ-1.1", "target_section": "1 总则 / 编写目的"},
            "spec_tree": [],
            "confirmed_facts": [],
            "open_questions": [],
            "patches": [],
            "history_summary": "",
        },
        execution_options={"expected_output": "full_document", "observability_required": "limited", "streaming_enabled": False},
    )

    result = adapter.run(request)

    assert result.plugin["plugin_id"] == "xg-dify-workflow-orchestrator"
    assert result.plugin["observability_level"] == "limited"
    assert "空域运算软件" in result.final_output["filled_document_text"]
    assert result.final_output["document_patch"] == []
    assert result.process_output["stage_audits"] == []
    assert result.raw_output["raw_workflow_trace"]["fake"] is True


def test_plugin_result_normalizer_projects_observable_result_to_turn_payload() -> None:
    result = OrchestratorRunResult(
        contract_version="xg-observable-orchestrator-contract@1",
        plugin={
            "plugin_id": "xg-dify-workflow-orchestrator",
            "plugin_type": "dify_workflow",
            "observability_level": "limited",
        },
        final_output={
            "filled_document_text": "# 需求规格说明\n\n空域运算软件",
            "document_patch": [],
            "changed_sections": [],
            "completion_status": "partial",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "Dify workflow 预留插件已生成整篇正文草稿。",
            "next_question": "请继续补充下一项需求规格信息。",
            "quick_options": [],
            "suggested_focus": {},
        },
        process_output={
            "stage_results": [],
            "stage_audits": [],
            "decision_trace": ["fake Dify workflow 已返回有限观测结果。"],
            "provider_logs": [],
            "review_after_apply_result": {},
            "annotations": [],
            "risks": [],
        },
        state_output={
            "confirmed_facts_delta": ["这个系统叫空域运算软件"],
            "open_questions_delta": ["请继续补充下一项需求规格信息。"],
            "spec_tree_update": {},
            "working_document_update": {},
            "turn_path_update": {},
        },
        raw_output={
            "raw_plugin_response": {},
            "raw_model_response": {},
            "raw_workflow_trace": {"fake": True, "workflow_id": "fake-xg-dify-workflow"},
        },
    )

    normalized = OrchestratorPluginResultNormalizer().normalize(result)

    assert normalized["model_output"]["assistant_message"] == "Dify workflow 预留插件已生成整篇正文草稿。"
    assert normalized["model_output"]["next_question"] == "请继续补充下一项需求规格信息。"
    assert normalized["model_output"]["filled_document_text"].endswith("空域运算软件")
    assert normalized["process_output"]["stage_audits"] == []
    assert normalized["process_output"]["decision_trace"] == ["fake Dify workflow 已返回有限观测结果。"]
    assert normalized["raw_plugin_response"]["contract_version"] == "xg-observable-orchestrator-contract@1"
    assert normalized["raw_plugin_response"]["raw_output"]["raw_workflow_trace"]["workflow_id"] == "fake-xg-dify-workflow"


def test_plugin_result_normalizer_converts_string_quick_options_to_contract_objects() -> None:
    result = OrchestratorRunResult(
        contract_version="xg-observable-orchestrator-contract@1",
        plugin={
            "plugin_id": "brainstorm-v1-dify-workflow",
            "plugin_type": "dify_workflow",
            "observability_level": "limited",
        },
        final_output={
            "filled_document_text": "",
            "document_patch": [],
            "changed_sections": [],
            "completion_status": "partial",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "请确认关键选项。",
            "next_question": "请选择一个方向。",
            "quick_options": ["指挥员查看态势", "参谋分析员研判态势", "值班员维护态势"],
            "suggested_focus": {},
        },
        process_output={
            "stage_results": [],
            "stage_audits": [],
            "decision_trace": [],
            "provider_logs": [],
            "review_after_apply_result": {},
            "annotations": [],
            "risks": [],
        },
        state_output={
            "confirmed_facts_delta": [],
            "open_questions_delta": [],
            "spec_tree_update": {},
            "working_document_update": {},
            "turn_path_update": {},
        },
        raw_output={},
    )

    normalized = OrchestratorPluginResultNormalizer().normalize(result)

    assert normalized["model_output"]["quick_options"] == [
        {"key": "A", "label": "指挥员查看态势", "recommended": True},
        {"key": "B", "label": "参谋分析员研判态势", "recommended": False},
        {"key": "C", "label": "值班员维护态势", "recommended": False},
    ]
