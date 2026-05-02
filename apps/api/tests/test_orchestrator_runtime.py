from app.orchestrators.contract_validator import OrchestratorContractValidator
from app.orchestrators.package_loader import OrchestratorPackageLoader
from app.orchestrators.runner_host import OrchestratorRunnerHost


def test_orchestrator_runtime_loads_assets_and_normalizes_output() -> None:
    loader = OrchestratorPackageLoader()
    heuristic = loader.load("xg-heuristic-orchestrator")
    assert heuristic.package.orchestrator_id == "xg-heuristic-orchestrator"
    assert "用户输入驱动" in heuristic.policy_text
    assert "Host 必须保证" in heuristic.prompt_text

    strong_rule = loader.load("xg-strong-rule-orchestrator")
    assert strong_rule.package.mode == "local_runner"
    assert strong_rule.entry_path.endswith("runner.py")

    validator = OrchestratorContractValidator()
    normalized = validator.normalize_turn_output(
        {
            "assistant_message": "已补齐定位。",
            "confirmed_facts_delta": ["软件定位初步确认：计算分析工具"],
            "document_patch": [
                {
                    "section": "2 项目概述 / 软件定位",
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
    assert normalized["document_patch"][0]["operation"] == "append_or_update"
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
    assert output["document_patch"][0]["section"] == "1 总则 / 编写目的"
    assert output["document_patch"][0]["write_policy"] == "patch_suggestion_only"
    assert output["raw_model_response"]["runner_invoked"] is True
    assert output["raw_model_response"]["runner_entry"].endswith("xg-strong-rule-orchestrator/runner.py")
