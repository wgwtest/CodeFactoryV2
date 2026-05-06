from app.orchestrators.plugin_contracts import (
    OrchestratorPluginManifest,
    OrchestratorRunRequest,
    OrchestratorRunResult,
)
from app.orchestrators.plugin_registry import OrchestratorPluginRegistry
from app.orchestrators.adapters.local_xg_plugin import LocalXGOrchestratorPluginAdapter


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
    assert "xg-local-strong-rule-orchestrator" in plugin_ids
    assert "xg-dify-workflow-orchestrator" in plugin_ids

    dify = registry.require("xg-dify-workflow-orchestrator")
    assert dify.plugin_type == "dify_workflow"
    assert dify.observability_level == "limited"
    assert dify.capabilities["filled_document_text"] is True
    assert dify.capabilities["stage_audits"] is False


def test_local_xg_plugin_wraps_existing_runner_output() -> None:
    registry = OrchestratorPluginRegistry()
    manifest = registry.require("xg-local-strong-rule-orchestrator")
    adapter = LocalXGOrchestratorPluginAdapter(manifest=manifest)
    request = OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={
            "session_id": "ra-001",
            "topic": "空域运算软件需求规格探索",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "orchestrator_id": "xg-local-strong-rule-orchestrator",
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
        execution_options={"expected_output": "both", "observability_required": "full", "streaming_enabled": False},
    )

    result = adapter.run(request)

    assert result.plugin["plugin_id"] == "xg-local-strong-rule-orchestrator"
    assert result.plugin["observability_level"] == "full"
    assert result.final_output["document_patch"][0]["plan_ref"] == "AP-001"
    assert result.interaction_output["assistant_message"].startswith("强规则组织器")
    assert result.state_output["confirmed_facts_delta"]
    assert result.raw_output["raw_model_response"]["runner_invoked"] is True
