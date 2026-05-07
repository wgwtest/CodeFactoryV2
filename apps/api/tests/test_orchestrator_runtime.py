from pathlib import Path
import ast

from app.orchestrators.adapters.base import load_orchestrator_plugin_adapter
from app.orchestrators.contract_validator import OrchestratorContractValidator
from app.orchestrators.package_loader import OrchestratorPackageLoader
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.requirement_analysis.turn_engine import RequirementAnalysisTurnEngine


def test_orchestrator_runtime_loads_assets_and_normalizes_output() -> None:
    loader = OrchestratorPackageLoader()
    heuristic = loader.load("xg-heuristic-orchestrator")
    assert heuristic.package.orchestrator_id == "xg-heuristic-orchestrator"
    assert "用户输入驱动" in heuristic.policy_text
    assert "Host 必须保证" in heuristic.prompt_text
    assert heuristic.artifact_rules["clauses"]["REQ-2.1"]["fact_template"] == "软件定位初步确认：{semantic}"
    assert heuristic.artifact_rules["clauses"]["REQ-2.1"]["quick_options"][0]["label"] == "计算分析工具"
    assert heuristic.spec_strategy["clauses"]["REQ-2.1"]["question"] == "组织器策略问题：请确认软件定位、领域边界、解决的问题，以及第一阶段明确不做的内容。"

    strong_rule = loader.load("xg-strong-rule-orchestrator")
    assert strong_rule.package.mode == "local_runner"
    assert strong_rule.entry_path.endswith("runner.py")
    assert strong_rule.artifact_rules["clauses"]["REQ-2.1"]["patch_template"] == "软件定位为：{semantic}"
    assert strong_rule.spec_strategy["defaults"]["leaf_question_template"] == "强规则组织器要求补齐：{clause_title}。"

    validator = OrchestratorContractValidator()
    normalized = validator.normalize_turn_output(
        {
            "assistant_message": "已补齐定位。",
            "template_shape_assessment": {
                "shape_type": "coarse_grained_extensible",
                "reason": "测试模板允许条款下补写。",
            },
            "target_anchor_plan": [
                {
                    "plan_id": "AP-001",
                    "decision_type": "append_existing_clause",
                    "template_clause_id": "REQ-2.1",
                    "display_heading": "2.1 软件定位",
                }
            ],
            "confirmed_facts_delta": ["软件定位初步确认：计算分析工具"],
            "document_patch": [
                {
                    "plan_ref": "AP-001",
                    "content": "软件定位为：计算分析工具",
                }
            ],
        },
        provider_id="mock",
        model="mock-requirement-analysis-v1",
        write_policy="patch_suggestion_only",
        raw_response={"mock": True},
    )
    assert normalized["next_suggestion"]["reason"] == "Provider 未生成下一轮建议。"
    assert normalized["target_anchor_plan"][0]["template_clause_id"] == "REQ-2.1"
    assert normalized["document_patch"][0]["operation"] == "append_or_update"
    assert normalized["document_patch"][0]["plan_ref"] == "AP-001"
    assert normalized["raw_model_response"]["provider_id"] == "mock"

    host = OrchestratorRunnerHost(loader=loader, validator=validator)
    prompt_bundle = host.build_provider_prompt_bundle(
        "xg-heuristic-orchestrator",
        context={"topic": "空域运算软件需求规格探索"},
        output_schema={"assistant_message": "string"},
    )
    assert "空域运算软件需求规格探索" in prompt_bundle["context_json"]
    assert "需求规格说明写作 Lab" in prompt_bundle["assembled_prompt"]
    assert "用户输入驱动" in prompt_bundle["assembled_prompt"]

    brainstorm = loader.load("brainstorm-v1")
    assert brainstorm.package.orchestrator_id == "brainstorm-v1"
    assert brainstorm.spec_strategy["turn_strategy"]["strategy_id"] == "decision_state_loop"
    assert [stage["stage_id"] for stage in brainstorm.spec_strategy["turn_strategy"]["stages"]] == [
        "intent_understanding",
        "decision_state_delta",
        "next_interaction_planning",
    ]


def test_legacy_package_loader_ignores_non_local_plugin_packages() -> None:
    loader = OrchestratorPackageLoader()

    package_ids = {item.package.orchestrator_id for item in loader.load_all()}

    assert package_ids == {"brainstorm-v1", "xg-heuristic-orchestrator", "xg-strong-rule-orchestrator"}


def test_turn_engine_does_not_dispatch_by_plugin_type_or_adapter_entry() -> None:
    names = RequirementAnalysisTurnEngine.run_turn.__code__.co_names

    assert "adapter_entry" not in names
    assert "plugin_type" not in names


def test_turn_engine_does_not_own_local_xg_stage_orchestration() -> None:
    names = set(RequirementAnalysisTurnEngine.run_turn.__code__.co_names)
    constants = {item for item in RequirementAnalysisTurnEngine.run_turn.__code__.co_consts if isinstance(item, str)}

    assert "_stages_by_kind" not in names
    assert "intent" not in constants
    assert "write" not in constants
    assert "review" not in constants
    assert "next_interaction" not in constants


def test_turn_engine_source_does_not_materialize_stage_shaped_plugin_results() -> None:
    source = Path("apps/api/app/requirement_analysis/turn_engine.py").read_text(encoding="utf-8")

    assert "_materialize_plugin_result" not in source
    assert "intent_understanding_result" not in source
    assert "stage_task_definition" not in source
    assert "review_after_apply_result" not in source
    assert "next_interaction_plan" not in source


def test_plugin_adapter_loader_supports_plugin_local_relative_imports(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "xg" / "xg-relative-import-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "helper.py").write_text(
        "from app.orchestrators.plugin_contracts import OrchestratorRunResult\n"
        "\n"
        "def build_result(request):\n"
        "    return OrchestratorRunResult(\n"
        "        contract_version=request.contract_version,\n"
        "        plugin={'plugin_id':'xg-relative-import-plugin','plugin_type':'dify_workflow','observability_level':'limited'},\n"
        "        final_output={'filled_document_text':'ok','document_patch':[],'changed_sections':[],'completion_status':'partial','confidence':'medium'},\n"
        "        interaction_output={'assistant_message':'ok','next_question':'next','quick_options':[],'suggested_focus':{}},\n"
        "        process_output={'stage_results':[],'stage_audits':[],'decision_trace':[],'provider_logs':[],'review_after_apply_result':{},'annotations':[],'risks':[]},\n"
        "        state_output={'confirmed_facts_delta':[],'open_questions_delta':[],'spec_tree_update':{},'working_document_update':{},'turn_path_update':{}},\n"
        "        raw_output={'raw_plugin_response':{},'raw_model_response':{},'raw_workflow_trace':{},'turn_execution_result':{'turn':{},'state_patch':{},'provider_logs':[]}},\n"
        "    )\n",
        encoding="utf-8",
    )
    (plugin_dir / "adapter.py").write_text(
        "from .helper import build_result\n"
        "\n"
        "class RelativeImportAdapter:\n"
        "    def __init__(self, *, manifest, package=None):\n"
        "        self.manifest = manifest\n"
        "\n"
        "    def run(self, request):\n"
        "        return build_result(request)\n",
        encoding="utf-8",
    )

    manifest = OrchestratorPluginManifest(
        plugin_id="xg-relative-import-plugin",
        name="XG Relative Import Plugin",
        plugin_type="dify_workflow",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=1,
        capabilities={"filled_document_text": True},
        requires={"template": True},
        adapter_entry="dify_workflow",
        adapter_module="adapter",
        adapter_class="RelativeImportAdapter",
        package_path=str(plugin_dir),
    )

    adapter = load_orchestrator_plugin_adapter(manifest)
    result = adapter.run(
        OrchestratorRunRequest(
            contract_version="xg-observable-orchestrator-contract@1",
            session={},
            turn={},
            template={},
            document_context={},
            execution_options={},
        )
    )

    assert result.final_output["filled_document_text"] == "ok"


def test_local_xg_runtime_is_plugin_local_not_host_owned() -> None:
    host_adapter = Path("apps/api/app/orchestrators/adapters/local_xg_plugin.py")
    host_runtime = Path("apps/api/app/orchestrators/adapters/local_xg_turn_runtime.py")
    host_stage_runtime_context_builder = Path("apps/api/app/requirement_analysis/stage_runtime_context_builder.py")
    host_turn_strategy_service = Path("apps/api/app/requirement_analysis/turn_strategy_service.py")
    host_turn_stage_planner = Path("apps/api/app/requirement_analysis/turn_stage_planner.py")
    host_turn_stage_executor = Path("apps/api/app/requirement_analysis/turn_stage_executor.py")
    host_turn_stage_reducer = Path("apps/api/app/requirement_analysis/turn_stage_reducer.py")
    heuristic_runtime = Path("orchestrators/xg/xg-heuristic-orchestrator/local_xg_turn_runtime.py")
    heuristic_stage_runtime_context_builder = Path("orchestrators/xg/xg-heuristic-orchestrator/stage_runtime_context_builder.py")
    heuristic_turn_strategy_service = Path("orchestrators/xg/xg-heuristic-orchestrator/turn_strategy_service.py")
    heuristic_turn_stage_planner = Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_planner.py")
    heuristic_turn_stage_executor = Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_executor.py")
    heuristic_turn_stage_reducer = Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_reducer.py")
    strong_rule_runtime = Path("orchestrators/xg/xg-strong-rule-orchestrator/local_xg_turn_runtime.py")
    strong_rule_stage_runtime_context_builder = Path("orchestrators/xg/xg-strong-rule-orchestrator/stage_runtime_context_builder.py")
    strong_rule_turn_strategy_service = Path("orchestrators/xg/xg-strong-rule-orchestrator/turn_strategy_service.py")
    strong_rule_turn_stage_planner = Path("orchestrators/xg/xg-strong-rule-orchestrator/turn_stage_planner.py")
    strong_rule_turn_stage_executor = Path("orchestrators/xg/xg-strong-rule-orchestrator/turn_stage_executor.py")
    strong_rule_turn_stage_reducer = Path("orchestrators/xg/xg-strong-rule-orchestrator/turn_stage_reducer.py")
    heuristic_adapter_source = Path("orchestrators/xg/xg-heuristic-orchestrator/adapter.py").read_text(encoding="utf-8")
    heuristic_runtime_source = heuristic_runtime.read_text(encoding="utf-8")
    strong_rule_adapter_source = Path("orchestrators/xg/xg-strong-rule-orchestrator/adapter.py").read_text(encoding="utf-8")
    strong_rule_runtime_source = strong_rule_runtime.read_text(encoding="utf-8")

    assert not host_adapter.exists()
    assert not host_runtime.exists()
    assert not host_stage_runtime_context_builder.exists()
    assert not host_turn_strategy_service.exists()
    assert not host_turn_stage_planner.exists()
    assert not host_turn_stage_executor.exists()
    assert not host_turn_stage_reducer.exists()
    assert heuristic_runtime.exists()
    assert heuristic_stage_runtime_context_builder.exists()
    assert heuristic_turn_strategy_service.exists()
    assert heuristic_turn_stage_planner.exists()
    assert heuristic_turn_stage_executor.exists()
    assert heuristic_turn_stage_reducer.exists()
    assert strong_rule_runtime.exists()
    assert strong_rule_stage_runtime_context_builder.exists()
    assert strong_rule_turn_strategy_service.exists()
    assert strong_rule_turn_stage_planner.exists()
    assert strong_rule_turn_stage_executor.exists()
    assert strong_rule_turn_stage_reducer.exists()
    assert "app.orchestrators.adapters.local_xg_plugin" not in heuristic_adapter_source
    assert "app.orchestrators.adapters.local_xg_plugin" not in strong_rule_adapter_source
    assert "service.turn_strategy_service" not in heuristic_adapter_source
    assert "service.turn_stage_planner" not in heuristic_adapter_source
    assert "service.turn_stage_executor" not in heuristic_adapter_source
    assert "service.turn_stage_reducer" not in heuristic_adapter_source
    assert "service.turn_strategy_service" not in strong_rule_adapter_source
    assert "service.turn_stage_planner" not in strong_rule_adapter_source
    assert "service.turn_stage_executor" not in strong_rule_adapter_source
    assert "service.turn_stage_reducer" not in strong_rule_adapter_source
    assert "app.requirement_analysis.stage_runtime_context_builder" not in heuristic_runtime_source
    assert "app.requirement_analysis.turn_strategy_service" not in heuristic_runtime_source
    assert "app.requirement_analysis.turn_stage_planner" not in heuristic_runtime_source
    assert "app.requirement_analysis.turn_stage_executor" not in heuristic_runtime_source
    assert "app.requirement_analysis.turn_stage_reducer" not in heuristic_runtime_source
    assert "app.requirement_analysis.stage_runtime_context_builder" not in strong_rule_runtime_source
    assert "app.requirement_analysis.turn_strategy_service" not in strong_rule_runtime_source
    assert "app.requirement_analysis.turn_stage_planner" not in strong_rule_runtime_source
    assert "app.requirement_analysis.turn_stage_executor" not in strong_rule_runtime_source
    assert "app.requirement_analysis.turn_stage_reducer" not in strong_rule_runtime_source


def test_dify_workflow_adapter_implementation_is_plugin_local() -> None:
    host_dify_adapter = Path("apps/api/app/orchestrators/adapters/dify_workflow_plugin.py")
    plugin_dify_adapter = Path("orchestrators/xg/xg-dify-workflow-orchestrator/adapter.py")
    plugin_source = plugin_dify_adapter.read_text(encoding="utf-8")

    assert not host_dify_adapter.exists()
    assert "app.orchestrators.adapters.dify_workflow_plugin" not in plugin_source
    assert "class DifyWorkflowOrchestratorPluginAdapter" in plugin_source


def test_host_stage_asset_resolvers_do_not_encode_xg_stage_names() -> None:
    resolver_paths = [
        Path("apps/api/app/orchestrators/stage_prompt_resolver.py"),
        Path("apps/api/app/orchestrators/stage_schema_resolver.py"),
        Path("apps/api/app/orchestrators/stage_adoption_policy_resolver.py"),
    ]
    forbidden = {
        "intent_understanding",
        "review_after_apply",
        "next_interaction_planning",
    }

    for path in resolver_paths:
        source = path.read_text(encoding="utf-8")
        constants = {node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        assert constants.isdisjoint(forbidden), f"{path} must not hardcode XG stage asset names"


def test_host_provider_layers_do_not_branch_on_xg_stage_protocol() -> None:
    provider_paths = [
        Path("apps/api/app/requirement_analysis/deepseek_client.py"),
        Path("apps/api/app/requirement_analysis/provider_call_service.py"),
    ]
    forbidden = {
        "intent_understanding",
        "review_after_apply",
        "next_interaction_planning",
    }

    for path in provider_paths:
        source = path.read_text(encoding="utf-8")
        constants = {node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        assert constants.isdisjoint(forbidden), f"{path} must not hardcode XG stage protocol names"


def test_orchestrator_runtime_executes_local_runner_entry() -> None:
    host = OrchestratorRunnerHost()

    output = host.execute_local_runner(
        "xg-strong-rule-orchestrator",
        context={
            "session": {
                "provider_id": "mock",
                "model": "mock-requirement-analysis-v1",
                "write_policy": "patch_suggestion_only",
            },
            "user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求",
            "normalized": {
                "input_type": "free_text",
                "semantic": "这个系统叫空域运算软件，主要解决空域计算分析需求",
            },
            "active_spec_node": {
                "node_id": "SPEC-REQ-1.1",
                "title": "REQ-1.1 编写目的",
                "target_section": "1 总则 / 编写目的",
                "question": "系统要做什么？",
            },
        },
    )

    assert output["organizer_interpretation"]["confidence"] == "high"
    assert "强规则组织器" in output["assistant_message"]
    assert output["target_anchor_plan"][0]["template_clause_id"] == "REQ-1.1"
    assert output["document_patch"][0]["plan_ref"] == "AP-001"
    assert output["document_patch"][0]["write_policy"] == "patch_suggestion_only"
    assert output["raw_model_response"]["runner_invoked"] is True
    assert output["raw_model_response"]["runner_entry"].endswith("xg-strong-rule-orchestrator/runner.py")


def test_brainstorm_v1_adapter_returns_decision_state_output() -> None:
    manifest = OrchestratorPluginManifest(
        plugin_id="brainstorm-v1",
        name="Brainstorm v1",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=20,
        capabilities={"document_patch": True, "decision_trace": True, "spec_tree_update": True},
        requires={"template": True},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="LocalXGOrchestratorPluginAdapter",
        package_path="orchestrators/xg/brainstorm-v1",
        package_id="brainstorm-v1",
    )
    adapter = load_orchestrator_plugin_adapter(manifest)

    result = adapter.run(
        OrchestratorRunRequest(
            contract_version="xg-observable-orchestrator-contract@1",
            session={
                "session_id": "session-brainstorm-v1",
                "topic": "空域运算软件",
                "orchestrator_id": "brainstorm-v1",
                "provider_id": "mock",
                "model": "mock-requirement-analysis-v1",
                "template_id": "81433号",
                "write_policy": "patch_suggestion_only",
            },
            turn={"user_input": "系统用于空域计算分析"},
            template={"template_id": "81433号"},
            document_context={
                "active_spec_node": {
                    "node_id": "SPEC-REQ-1.1",
                    "title": "REQ-1.1 编写目的",
                    "target_section": "1 总则 / 编写目的",
                    "question": "请确认软件名称、背景领域和编写目的。",
                },
                "spec_tree": [],
                "working_document": {},
                "state": {},
            },
            execution_options={},
        )
    )

    assert result.plugin["plugin_id"] == "brainstorm-v1"
    assert result.state_output["decision_state_delta"]["confirmed_facts"]
    assert result.state_output["decision_state_change_summary"]["added_counts"]["confirmed_facts"] == 1
    assert result.state_output["decision_state_document"]["title"] == "需求分析结构化状态"
    assert result.final_output["document_patch"]
