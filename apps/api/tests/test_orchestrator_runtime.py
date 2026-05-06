from app.orchestrators.contract_validator import OrchestratorContractValidator
from app.orchestrators.package_loader import OrchestratorPackageLoader
from app.orchestrators.runner_host import OrchestratorRunnerHost


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
