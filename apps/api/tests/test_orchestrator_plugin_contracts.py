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


def test_brainstorm_v1_dify_workflow_adapter_runs_local_workflow_shape() -> None:
    registry = OrchestratorPluginRegistry()
    manifest = registry.require("brainstorm-v1-dify-workflow")

    adapter = load_orchestrator_plugin_adapter(manifest)
    result = adapter.run(
        OrchestratorRunRequest(
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
    )

    assert result.plugin["plugin_id"] == "brainstorm-v1-dify-workflow"
    assert result.plugin["plugin_type"] == "dify_workflow"
    assert result.plugin["observability_level"] == "limited"
    assert "空域运算软件" in result.final_output["filled_document_text"]
    assert result.state_output["decision_state_delta"]["confirmed_facts"]
    assert result.state_output["decision_state_document"]["title"] == "需求分析结构化状态"
    assert result.process_output["decision_trace"]
    assert result.process_output["stage_audits"] == []
    assert result.raw_output["raw_workflow_trace"]["workflow_id"] == "brainstorm-v1-dify-shaped-workflow"
    assert [node["node_id"] for node in result.raw_output["raw_workflow_trace"]["nodes"]] == [
        "normalize_input",
        "intent_understanding",
        "decision_state_delta",
        "document_projection",
        "next_interaction_planning",
        "normalize_output",
    ]
    assert result.raw_output["turn_execution_result"].turn["decision_state_delta"]["confirmed_facts"]


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
