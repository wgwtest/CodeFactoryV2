import json
import sys
import importlib.util
from pathlib import Path

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
from app.orchestrators.runtime.decision_state_service import DecisionStateService
from app.requirement_analysis.turn_output_service import RequirementAnalysisTurnOutputService
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
    assert "brainstorm-v1-dify-workflow" in plugin_ids
    assert "xg-local-strong-rule-orchestrator" not in plugin_ids
    assert "xg-dify-workflow-orchestrator" not in plugin_ids

    brainstorm_dify = registry.require("brainstorm-v1-dify-workflow")
    assert brainstorm_dify.plugin_type == "dify_workflow"
    assert brainstorm_dify.package_id == "brainstorm-v1"
    assert brainstorm_dify.observability_level == "limited"
    assert brainstorm_dify.capabilities["decision_trace"] is True
    assert brainstorm_dify.capabilities["stage_audits"] is False


def test_brainstorm_v1_dify_workflow_projection_rules_use_current_81433_template_anchors() -> None:
    workflow = json.loads(Path("orchestrators/xg/brainstorm-v1-dify-workflow/workflow.json").read_text(encoding="utf-8"))
    rules = list(workflow.get("section_projection_rules") or [])

    anchors = {str(rule.get("anchor_path") or "") for rule in rules}
    target_sections = {str(rule.get("target_section") or "") for rule in rules}

    assert {
        "REQ-1.1",
        "REQ-2.1",
        "REQ-3.1",
        "REQ-3.2",
        "REQ-3.3",
        "REQ-3.4",
        "REQ-3.6",
        "REQ-3.7",
        "REQ-5.1",
        "REQ-5.2",
        "REQ-5.3",
        "REQ-5.4",
        "REQ-6.2",
    }.issubset(anchors)
    assert not {"REQ-3.UI", "REQ-3.COLLAB", "REQ-3.ERR"}.intersection(anchors)
    assert "3 功能需求 / 主要界面列表" not in target_sections
    assert "3 功能需求 / 协同与共享" not in target_sections
    assert "4 非功能需求 / 性能与可靠性" not in target_sections
    assert "5 验收准则 / 验收准则" not in target_sections
    assert any(
        rule.get("target_section") == "4 数据需求 / 输入数据" and rule.get("anchor_path") == "REQ-4.1"
        for rule in rules
    )
    assert any(
        rule.get("target_section") == "5 非功能需求 / 性能与可靠性" and rule.get("anchor_path") == "REQ-5.1"
        for rule in rules
    )


def test_brainstorm_v1_dify_document_projection_draft_preserves_output_performance_and_acceptance_facts() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "semantic": "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。",
        "normalized_context": {"draft_requested": True},
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "导出地图、结果、参数和说明给业务专家复核。"},
                {"content": "地图浏览要比较流畅，普通分析应在可接受时间内返回。"},
                {"content": "验收时至少覆盖态势创建编辑、分析工具使用、成果导出复核、结果追溯、权限日志和异常提示。"},
            ],
            "confirmed_decisions": [],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])
    patch_by_anchor = {patch["anchor_path"]: patch for patch in projection["document_patch"]}

    assert patch_by_anchor["REQ-3.6"]["operation"] == "replace"
    assert "业务专家复核" in patch_by_anchor["REQ-3.6"]["content"]
    assert "本章节待确认" not in patch_by_anchor["REQ-3.6"]["content"]
    assert "可接受时间" in patch_by_anchor["REQ-5.1"]["content"]
    assert "本章节待确认" not in patch_by_anchor["REQ-5.1"]["content"]
    assert "分析工具使用" in patch_by_anchor["REQ-6.2"]["content"]
    assert "成果导出复核" in patch_by_anchor["REQ-6.2"]["content"]


def test_brainstorm_v1_dify_document_projection_draft_is_reviewable_and_retains_real_gaps() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "semantic": "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。",
        "normalized_context": {
            "draft_requested": True,
            "open_question_summaries": [
                "组织器策略问题：请先确认软件名称、背景领域和编写目的。",
                "部署分析的算法边界仍需确认。",
                "报告模板字段仍需确认。",
            ],
        },
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "主要用户倾向于科研分析人员。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "业务专家参与结果复核。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "系统支撑日常地理信息分析、典型业务场景验证、基础数据分析和成果汇报。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "核心功能包括态势工程管理、地图浏览、图层控制、标绘、量算、坡度坡向高程剖面、通视分析、大气光照辅助运算和分析结果管理。", "target_section": "3 功能需求 / 核心功能项说明"},
            ],
            "confirmed_decisions": [],
            "open_questions": [
                {"content": "报告模板字段仍需确认。"},
            ],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])
    patch_by_anchor = {patch["anchor_path"]: patch for patch in projection["document_patch"]}

    assert len(patch_by_anchor["REQ-3.1"]["content"]) >= 80
    assert "主要用户" in patch_by_anchor["REQ-3.1"]["content"]
    assert "业务专家" in patch_by_anchor["REQ-3.1"]["content"]
    assert len(patch_by_anchor["REQ-3.4"]["content"]) >= 120
    assert "通视分析" in patch_by_anchor["REQ-3.4"]["content"]
    retained_gaps = "\n".join(projection["retained_gaps"])
    assert "组织器策略问题" not in retained_gaps
    assert "报告模板字段仍需确认" in retained_gaps
    assert projection["decision_state_delta"]["open_questions"]


def test_brainstorm_v1_dify_document_projection_status_review_filters_stale_strategy_gap() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "semantic": "你先回看一下：目前哪些关键决策已经闭合，哪些还没有闭合？先不要急着完整定稿。",
        "normalized_context": {
            "open_question_summaries": [
                "组织器策略问题：请先确认软件名称、背景领域和编写目的。",
                "报告模板字段仍需确认。",
            ]
        },
        "decision_state": {
            "confirmed_facts": [
                {"content": "主要用户倾向于科研分析人员。"},
                {"content": "系统支持导出地图、结果、参数和说明给业务专家复核。"},
            ],
            "open_questions": [
                {"content": "部署分析的算法边界仍需确认。"},
            ],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])

    assert projection["branch_taken"] == "review_status"
    assert "组织器策略问题" not in projection["assistant_message"]
    assert "报告模板字段仍需确认" in projection["assistant_message"]
    assert "部署分析的算法边界仍需确认" in projection["assistant_message"]


def test_brainstorm_v1_dify_document_projection_uses_current_turn_id_for_state_items() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "turn_id": "turn-0007",
        "semantic": "核心功能先考虑态势工程管理、地图浏览、图层控制、通视分析和分析结果管理。",
        "write_policy": "patch_suggestion_only",
        "decision_state": {"confirmed_facts": [], "confirmed_decisions": []},
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])
    delta = projection["decision_state_delta"]

    assert {item["source_turn_id"] for item in delta["confirmed_facts"]} == {"turn-0007"}
    assert {item["source_turn_id"] for item in delta["chapter_projections"]} == {"turn-0007"}


def test_brainstorm_v1_dify_document_projection_adds_confirmed_decisions_for_decision_like_facts() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "turn_id": "turn-0005",
        "semantic": "第一阶段不做实时多源情报接入，不做自动决策推荐，也不做多单位在线协同指挥。分析结果只能作为辅助判断。",
        "write_policy": "patch_suggestion_only",
        "decision_state": {"confirmed_facts": [], "confirmed_decisions": []},
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])
    decisions = projection["decision_state_delta"]["confirmed_decisions"]

    assert decisions
    assert all(item["item_id"].startswith("DS-D-") for item in decisions)
    assert all(item["source_turn_id"] == "turn-0005" for item in decisions)
    assert any("不做实时多源情报接入" in item["content"] for item in decisions)


def test_brainstorm_v1_dify_document_projection_draft_removes_bullet_prefix_and_raw_user_noise() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "semantic": "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。",
        "normalized_context": {"draft_requested": True},
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "这个我还没完全想清楚，但目前倾向于主要用户是科研分析人员。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "第一阶段不做实时多源情报接入。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "不做自动决策推荐。", "target_section": "2 项目概述 / 软件定位"},
            ],
            "confirmed_decisions": [],
            "open_questions": [],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])
    patch_by_anchor = {patch["anchor_path"]: patch for patch in projection["document_patch"]}

    assert not patch_by_anchor["REQ-2.1"]["content"].startswith("- ")
    assert not patch_by_anchor["REQ-3.1"]["content"].startswith("- ")
    assert "这个我还没完全想清楚" not in patch_by_anchor["REQ-3.1"]["content"]
    assert "科研分析人员" in patch_by_anchor["REQ-3.1"]["content"]


def test_brainstorm_v1_dify_document_projection_keeps_collecting_before_review_or_draft_when_core_gaps_remain() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "turn_id": "turn-0006",
        "semantic": "非功能先按内网部署、角色权限、操作审计、结果可追溯考虑；地图浏览要比较流畅，普通分析应在可接受时间内返回，所有分析结果都要标注数据来源、参数和适用限制。",
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "主要用户倾向于科研分析人员。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "系统支撑日常地理信息分析、典型业务场景验证、基础数据分析和成果汇报。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "核心流程包括创建工程、加载图层、执行分析和导出复核。", "target_section": "3 功能需求 / 核心业务流程"},
                {"content": "第一阶段不做实时多源情报接入，不做自动决策推荐。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "输入数据包括底图、地形数据、矢量数据、栅格数据、业务对象数据和分析参数。", "target_section": "4 数据需求 / 输入数据"},
                {"content": "输出包括态势工程文件、地图图片、分析结果图层、结果参数表和简要报告片段。", "target_section": "4 数据需求 / 输出数据与报表"},
                {"content": "导出地图、结果、参数和说明给业务专家复核。", "target_section": "3 功能需求 / 结果输出与共享"},
            ],
            "confirmed_decisions": [],
            "open_questions": [],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])

    assert projection["branch_taken"] == "document_projection"
    assert "回看闭合项或直接输出草案" not in projection["next_question"]
    assert "草案" not in projection["next_question"]
    assert any(
        keyword in projection["next_question"]
        for keyword in ["异常", "补偿", "失败", "验收", "通过标准"]
    )


def test_brainstorm_v1_dify_document_projection_asks_acceptance_before_review_when_exception_exists() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "turn_id": "turn-0008",
        "semantic": "异常方面要处理数据缺失、坐标系不一致、计算失败、保存失败、权限不足和导出失败。",
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "主要用户倾向于科研分析人员。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "系统支撑日常地理信息分析和成果汇报。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "核心流程包括创建工程、执行分析和导出复核。", "target_section": "3 功能需求 / 核心业务流程"},
                {"content": "第一阶段不做实时多源情报接入，不做自动决策推荐。", "target_section": "2 项目概述 / 软件定位"},
                {"content": "输入数据包括底图、地形数据和分析参数。", "target_section": "4 数据需求 / 输入数据"},
                {"content": "输出包括态势工程文件、地图图片、分析结果图层和报告片段。", "target_section": "4 数据需求 / 输出数据与报表"},
                {"content": "导出地图、结果、参数和说明给业务专家复核。", "target_section": "3 功能需求 / 结果输出与共享"},
                {"content": "地图浏览要流畅，普通分析在可接受时间内返回。", "target_section": "5 非功能需求 / 性能与可靠性"},
                {"content": "内网部署、角色权限、操作审计、结果可追溯。", "target_section": "5 非功能需求 / 安全与权限"},
            ],
            "confirmed_decisions": [],
            "open_questions": [],
        },
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])

    assert "回看闭合项或直接输出草案" not in projection["next_question"]
    assert "草案" not in projection["next_question"]
    assert any(keyword in projection["next_question"] for keyword in ["验收", "通过标准", "任务链"])


def test_brainstorm_v1_dify_document_projection_collects_positioning_or_core_before_review() -> None:
    node_path = Path("orchestrators/xg/brainstorm-v1-dify-workflow/nodes/document_projection.py")
    spec = importlib.util.spec_from_file_location("brainstorm_v1_dify_document_projection", node_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = {
        "turn_id": "turn-0007",
        "semantic": "验收时至少覆盖态势创建编辑、分析工具使用、成果导出复核、结果追溯、权限日志和异常提示。",
        "write_policy": "patch_suggestion_only",
        "decision_state": {
            "confirmed_facts": [
                {"content": "主要用户倾向于科研分析人员。", "target_section": "3 功能需求 / 用户与角色"},
                {"content": "创建工程、加载图层、添加对象和保存工程。", "target_section": "3 功能需求 / 核心业务流程"},
                {"content": "输入数据包括底图、地形数据、矢量数据、栅格数据、业务对象数据和分析参数。", "target_section": "4 数据需求 / 输入数据"},
                {"content": "异常方面要处理数据缺失、坐标系不一致、计算失败、保存失败、权限不足和导出失败。", "target_section": "3 功能需求 / 异常与补偿"},
                {"content": "非功能先按内网部署、角色权限、操作审计、结果可追溯考虑。", "target_section": "5 非功能需求 / 安全与权限"},
            ],
            "confirmed_decisions": [],
            "open_questions": [],
        },
        "normalized_context": {"last_question": "验收任务链和通过标准是什么？"},
    }

    output = module.main(json.dumps(context, ensure_ascii=False), "{}")
    projection = json.loads(output["document_projection_json"])

    assert projection["branch_taken"] == "document_projection"
    assert "回看闭合项或直接输出草案" not in projection["next_question"]
    assert "草案" not in projection["next_question"]
    assert any(keyword in projection["next_question"] for keyword in ["定位", "核心功能", "功能"])


def test_brainstorm_v1_dify_adapter_cleans_remote_document_patch_user_noise(monkeypatch) -> None:
    base_request = _brainstorm_dify_request()
    request = base_request.model_copy(
        update={
            "turn": {
                **base_request.turn,
                "turn_id": "turn-0007",
                "turn_index": 7,
                "user_input": "强制停止追问，输出草案。",
                "normalized_input": {"input_type": "convergence_command", "semantic": "强制停止追问，输出草案。"},
            }
        }
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-remote-noise-001",
                "data": {
                    "id": "run-remote-noise-001",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "assistant_message": "已输出草案。",
                                "next_question": "",
                                "quick_options": [],
                                "filled_document_text": "3 功能需求 / 用户与角色\n这个我还没完全想清楚，但目前倾向于主要用户是科研分析人员。",
                                "document_patch": [
                                    {
                                        "plan_ref": "BRAINSTORM-DIFY-DRAFT-001",
                                        "operation": "replace",
                                        "target_section": "3 功能需求 / 用户与角色",
                                        "anchor_path": "REQ-3.1",
                                        "content": "这个我还没完全想清楚，但目前倾向于主要用户是科研分析人员。",
                                        "write_policy": "patch_suggestion_only",
                                    }
                                ],
                                "changed_sections": ["3 功能需求 / 用户与角色"],
                                "completion_status": "completed",
                                "confidence": "medium",
                                "confirmed_facts_delta": [],
                                "open_questions_delta": [],
                                "decision_state_delta": {
                                    "confirmed_facts": [],
                                    "confirmed_decisions": [],
                                    "tentative_assumptions": [],
                                    "open_questions": [],
                                    "rejected_directions": [],
                                    "chapter_projections": [],
                                    "next_focus": "等待用户审阅草案后主动提出修改意见。",
                                },
                                "decision_trace": [],
                                "annotations": [],
                                "risks": [],
                                "raw_workflow_trace": {"branch_taken": "draft_compose"},
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
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    result = adapter.run(request)

    patch = result.final_output["document_patch"][0]
    assert "这个我还没完全想清楚" not in patch["content"]
    assert "科研分析人员" in patch["content"]
    assert "这个我还没完全想清楚" not in result.final_output["filled_document_text"]


def test_brainstorm_v1_decision_state_delta_requires_structured_patch_anchors_for_delivery() -> None:
    schema = json.loads(
        Path("orchestrators/xg/brainstorm-v1/schemas/decision_state_delta.output.schema.json").read_text(
            encoding="utf-8"
        )
    )
    prompt_text = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
    )

    assert "target_anchor_plan" in schema["required"]
    assert "document_patch" in schema["required"]
    patch_schema = schema["properties"]["document_patch"]["items"]
    assert {"plan_ref", "operation", "content", "template_clause_id", "display_heading", "anchor_path"}.issubset(
        set(patch_schema["required"])
    )
    assert "每个 document_patch 必须通过 plan_ref 引用 target_anchor_plan.plan_id" in prompt_text
    assert "不能使用 draft-001" in prompt_text


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
    manifest = registry.require("brainstorm-v1-dify-workflow")

    adapter = load_orchestrator_plugin_adapter(manifest)
    assert adapter.manifest.plugin_id == "brainstorm-v1-dify-workflow"
    assert adapter.manifest.plugin_type == "dify_workflow"


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
    assert len(result.process_output["provider_logs"]) == 1
    provider_log = result.process_output["provider_logs"][0]
    assert provider_log["stage_id"] == "dify_workflow"
    assert provider_log["provider_id"] == "dify"
    assert provider_log["audit"]["provider_request"]["url"] == "http://dify.local/v1/workflows/run"
    assert provider_log["audit"]["provider_response"]["workflow_run_id"] == "run-remote-001"
    assert provider_log["audit"]["provider_normalized_output"]["assistant_message"] == "远端 Dify 已完成。"
    assert result.raw_output["raw_workflow_trace"]["remote"] is True
    assert result.raw_output["raw_workflow_trace"]["workflow_run_id"] == "run-remote-001"
    assert result.raw_output["turn_execution_result"].turn["decision_state_delta"]["confirmed_facts"]
    assert result.raw_output["turn_execution_result"].provider_logs == result.process_output["provider_logs"]


def test_brainstorm_v1_dify_workflow_adapter_reports_remote_workflow_failure(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-failed-001",
                "data": {
                    "id": "run-failed-001",
                    "status": "failed",
                    "outputs": {},
                    "error": "PluginInvokeError: API request failed with status code 402: Insufficient Balance",
                },
            },
        )

    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    with pytest.raises(ValueError) as exc_info:
        adapter.run(_brainstorm_dify_request())

    message = str(exc_info.value)
    assert "remote dify workflow failed" in message
    assert "run-failed-001" in message
    assert "Insufficient Balance" in message


def test_brainstorm_v1_dify_workflow_adapter_preserves_draft_delivery_without_next_question(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-draft-001",
                "data": {
                    "id": "run-draft-001",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "assistant_message": "已生成完整需求规格说明草案，本轮不再继续追问。",
                                "next_question": "",
                                "quick_options": [],
                                "filled_document_text": "## 需求规格说明草案\n\n空域运算软件用于空域计算分析。",
                                "document_patch": [
                                    {
                                        "plan_ref": "BRAINSTORM-DIFY-DRAFT-001",
                                        "operation": "replace",
                                        "anchor_path": "REQ-6.3",
                                        "target_section": "6 验收准则 / 待确认事项",
                                        "content": "## 需求规格说明草案\n\n空域运算软件用于空域计算分析。",
                                        "write_policy": "patch_suggestion_only",
                                    }
                                ],
                                "changed_sections": ["6 验收准则 / 待确认事项"],
                                "completion_status": "completed",
                                "confidence": "medium",
                                "confirmed_facts_delta": [],
                                "open_questions_delta": [],
                                "decision_state_delta": {
                                    "confirmed_facts": [],
                                    "confirmed_decisions": [],
                                    "tentative_assumptions": [],
                                    "open_questions": [],
                                    "rejected_directions": [],
                                    "chapter_projections": [],
                                    "next_focus": "等待用户审阅草案后主动提出修改意见。",
                                },
                                "decision_trace": ["进入 draft_compose 收束交付分支。"],
                                "annotations": ["草案已交付。"],
                                "risks": [],
                                "raw_workflow_trace": {"branch_taken": "draft_compose"},
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
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    result = adapter.run(_brainstorm_dify_request())
    materialized = result.raw_output["turn_execution_result"]

    assert result.interaction_output["next_question"] == ""
    assert result.interaction_output["quick_options"] == []
    assert result.interaction_output["suggested_focus"]["should_ask_user"] is False
    assert result.interaction_output["suggested_focus"]["interaction_mode"] == "draft_delivery"
    assert result.state_output["open_questions_delta"] == []
    assert materialized.turn["next_interaction"]["type"] == "draft_delivery"
    assert materialized.turn["next_interaction"]["options"] == []
    assert materialized.turn["next_interaction"]["target_spec_node_ids"] == []
    assert "已生成完整需求规格说明草案" in materialized.turn["next_interaction"]["prompt"]


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
            "source_turn_id": "turn-0001",
            "target_section": "待确认事项",
            "status": "deferred_to_draft_gap",
        }
    ]
    assert result.state_output["open_questions_delta"] == []


def test_brainstorm_v1_dify_workflow_adapter_uniquifies_state_item_ids() -> None:
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    state, _summary = adapter._apply_decision_delta(
        current_state={
            "confirmed_facts": [
                {
                    "item_id": "DS-F-001",
                    "content": "主要用户为科研分析人员。",
                    "target_section": "3 功能需求 / 用户与角色",
                    "status": "active",
                }
            ],
            "confirmed_decisions": [],
            "tentative_assumptions": [],
            "open_questions": [
                {
                    "item_id": "DS-Q-001",
                    "content": "用户角色有哪些？",
                    "target_section": "3 功能需求 / 用户与角色",
                    "status": "open",
                }
            ],
            "rejected_directions": [],
            "next_focus": "",
            "chapter_projections": [],
        },
        delta={
            "confirmed_facts": [
                {
                    "item_id": "DS-F-001",
                    "content": "业务专家参与复核。",
                    "target_section": "3 功能需求 / 用户与角色",
                    "status": "active",
                }
            ],
            "open_questions": [
                {
                    "item_id": "DS-Q-001",
                    "content": "导出格式是什么？",
                    "target_section": "3 功能需求 / 结果输出与共享",
                    "status": "open",
                }
            ],
        },
        next_focus="继续确认导出。",
    )

    assert [item["item_id"] for item in state["confirmed_facts"]] == ["DS-F-001", "DS-F-002"]
    assert [item["item_id"] for item in state["open_questions"]] == ["DS-Q-001", "DS-Q-002"]


def test_brainstorm_v1_dify_workflow_adapter_promotes_decision_like_facts_for_legacy_remote(monkeypatch) -> None:
    base_request = _brainstorm_dify_request()
    request = base_request.model_copy(
        update={
            "turn": {
                **base_request.turn,
                "turn_id": "turn-0005",
                "turn_index": 5,
                "user_input": "第一阶段不做实时多源情报接入，不做自动决策推荐。分析结果只能作为辅助判断。",
                "normalized_input": {
                    "input_type": "free_text",
                    "semantic": "第一阶段不做实时多源情报接入，不做自动决策推荐。分析结果只能作为辅助判断。",
                },
            }
        }
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-legacy-decision-001",
                "data": {
                    "id": "run-legacy-decision-001",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "assistant_message": "已吸收边界信息。",
                                "next_question": "下一步确认验收口径。",
                                "quick_options": [],
                                "filled_document_text": "第一阶段不做实时多源情报接入，不做自动决策推荐。",
                                "document_patch": [],
                                "changed_sections": ["2 项目概述 / 软件定位"],
                                "completion_status": "partial",
                                "confidence": "medium",
                                "confirmed_facts_delta": [],
                                "open_questions_delta": [],
                                "decision_state_delta": {
                                    "confirmed_facts": [
                                        {
                                            "item_id": "DS-F-001",
                                            "content": "第一阶段不做实时多源情报接入，不做自动决策推荐。分析结果只能作为辅助判断。",
                                            "source_turn_id": "turn-0001",
                                            "target_section": "2 项目概述 / 软件定位",
                                            "status": "active",
                                        }
                                    ],
                                    "confirmed_decisions": [],
                                    "tentative_assumptions": [],
                                    "open_questions": [],
                                    "rejected_directions": [],
                                    "chapter_projections": [],
                                    "next_focus": "下一步确认验收口径。",
                                },
                                "decision_trace": [],
                                "annotations": [],
                                "risks": [],
                                "raw_workflow_trace": {"workflow_id": "remote-workflow", "run_id": "run-legacy-decision-001"},
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
    registry = OrchestratorPluginRegistry()
    adapter = load_orchestrator_plugin_adapter(registry.require("brainstorm-v1-dify-workflow"))
    brainstorm_adapter_module = sys.modules["_codefactory_plugin_brainstorm_v1_dify_workflow.adapter"]
    monkeypatch.setattr(brainstorm_adapter_module.httpx, "post", fake_post)

    result = adapter.run(request)
    delta = result.state_output["decision_state_delta"]

    assert delta["confirmed_facts"][0]["source_turn_id"] == "turn-0005"
    assert delta["confirmed_decisions"]
    assert delta["confirmed_decisions"][0]["item_id"].startswith("DS-D-")
    assert delta["confirmed_decisions"][0]["source_turn_id"] == "turn-0005"
    assert "不做实时多源情报接入" in delta["confirmed_decisions"][0]["content"]


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


def test_turn_output_service_materializes_missing_anchor_plan_for_patch_with_structured_anchor() -> None:
    service = RequirementAnalysisTurnOutputService()

    model_output = {
        "target_anchor_plan": [
            {
                "plan_id": "plan-001",
                "template_clause_id": "REQ-1.1",
                "display_heading": "1.1 编写目的",
                "anchor_path": "REQ-1.1",
            }
        ],
        "document_patch": [
            {
                "plan_ref": "plan-001",
                "operation": "append_or_update",
                "content": "本文用于明确软件需求范围。",
                "write_policy": "patch_suggestion_only",
            },
            {
                "plan_ref": "plan-005-1",
                "operation": "append_or_update",
                "anchor_path": "REQ-3.1",
                "target_section": "3.1 用户与角色",
                "content": "主要用户包括科研分析人员和业务专家。",
                "write_policy": "patch_suggestion_only",
            },
        ],
    }

    normalized = service.validate_anchor_plan_refs(
        model_output=model_output,
        chapter_configuration_context={
            "canonical_clause_map": {
                "REQ-1.1": {"display_heading": "1.1 编写目的"},
                "REQ-3.1": {"display_heading": "3.1 用户与角色"},
            }
        },
    )

    assert [plan["plan_id"] for plan in normalized["target_anchor_plan"]] == ["plan-001", "plan-005-1"]
    materialized_plan = normalized["target_anchor_plan"][1]
    assert materialized_plan["template_clause_id"] == "REQ-3.1"
    assert materialized_plan["display_heading"] == "3.1 用户与角色"
    assert materialized_plan["anchor_path"] == "REQ-3.1"


def test_turn_output_service_materializes_missing_anchor_plan_from_plan_ref_clause_alias() -> None:
    service = RequirementAnalysisTurnOutputService()

    model_output = {
        "target_anchor_plan": [],
        "document_patch": [
            {
                "plan_ref": "plan-REQ-1.2",
                "operation": "append_or_update",
                "content": "第一阶段不做实时多源情报接入，不做自动决策推荐。",
                "write_policy": "patch_suggestion_only",
            },
        ],
    }

    normalized = service.validate_anchor_plan_refs(
        model_output=model_output,
        chapter_configuration_context={
            "canonical_clause_map": {
                "REQ-1.2": {"display_heading": "1.2 适用范围"},
            }
        },
    )

    assert normalized["target_anchor_plan"] == [
        {
            "plan_id": "plan-REQ-1.2",
            "decision_type": "append_existing_clause",
            "template_clause_id": "REQ-1.2",
            "canonical_clause_heading": "1.2 适用范围",
            "subtopic_action": "none",
            "subtopic_key": "",
            "subtopic_title": "",
            "display_heading": "1.2 适用范围",
            "template_shape_ref": "",
            "reason": "由 document_patch 自带结构化锚点补齐 target_anchor_plan，未做业务语义匹配。",
            "confidence": "medium",
            "anchor_path": "REQ-1.2",
        }
    ]


def test_turn_output_service_materializes_missing_anchor_plan_from_numbered_plan_ref_alias() -> None:
    service = RequirementAnalysisTurnOutputService()

    model_output = {
        "target_anchor_plan": [],
        "document_patch": [
            {
                "plan_ref": "plan-1.1-fix",
                "operation": "replace",
                "content": "修正模板与当前项目事实混淆的表述。",
                "write_policy": "patch_suggestion_only",
            },
        ],
    }

    normalized = service.validate_anchor_plan_refs(
        model_output=model_output,
        chapter_configuration_context={
            "canonical_clause_map": {
                "REQ-1.1": {"display_heading": "1.1 编写目的"},
            }
        },
    )

    assert normalized["target_anchor_plan"][0]["plan_id"] == "plan-1.1-fix"
    assert normalized["target_anchor_plan"][0]["template_clause_id"] == "REQ-1.1"
    assert normalized["target_anchor_plan"][0]["display_heading"] == "1.1 编写目的"


def test_turn_output_service_materializes_missing_anchor_plan_from_patch_display_heading() -> None:
    service = RequirementAnalysisTurnOutputService()

    model_output = {
        "target_anchor_plan": [],
        "document_patch": [
            {
                "plan_ref": "PLAN-016",
                "operation": "append_or_update",
                "target_section": "2.4 范围边界",
                "display_heading": "2.4 范围边界",
                "content": "第一阶段不做实时多源情报接入，不做自动决策推荐。",
                "write_policy": "patch_suggestion_only",
            },
        ],
    }

    normalized = service.validate_anchor_plan_refs(
        model_output=model_output,
        chapter_configuration_context={
            "canonical_clause_map": {
                "REQ-2.4": {"display_heading": "2.4 范围边界", "heading": "2.4 范围边界"},
                "REQ-3.4": {"display_heading": "3.4 核心功能项说明", "heading": "3.4 核心功能项说明"},
            }
        },
    )

    assert normalized["target_anchor_plan"][0]["plan_id"] == "PLAN-016"
    assert normalized["target_anchor_plan"][0]["template_clause_id"] == "REQ-2.4"
    assert normalized["target_anchor_plan"][0]["display_heading"] == "2.4 范围边界"


def test_turn_output_service_materializes_missing_anchor_plan_from_template_path_heading() -> None:
    service = RequirementAnalysisTurnOutputService()

    model_output = {
        "target_anchor_plan": [],
        "document_patch": [
            {
                "plan_ref": "plan-026",
                "operation": "append_or_update",
                "target_section": "3 功能需求 / 异常与补偿",
                "content": "系统应处理数据缺失、坐标系不一致、计算失败、保存失败、权限不足和导出失败。",
                "write_policy": "patch_suggestion_only",
            },
            {
                "plan_ref": "plan-027",
                "operation": "append_or_update",
                "target_section": "6 验收准则 / 验收准则",
                "content": "验收应覆盖态势创建编辑、分析工具使用、成果导出复核、结果追溯、权限日志和异常提示。",
                "write_policy": "patch_suggestion_only",
            },
        ],
    }

    normalized = service.validate_anchor_plan_refs(
        model_output=model_output,
        chapter_configuration_context={
            "canonical_clause_map": {
                "REQ-3.7": {"display_heading": "3.7 异常与补偿", "heading": "3.7 异常与补偿"},
                "REQ-6.2": {"display_heading": "6.2 验收准则", "heading": "6.2 验收准则"},
            }
        },
    )

    assert [plan["template_clause_id"] for plan in normalized["target_anchor_plan"]] == ["REQ-3.7", "REQ-6.2"]
    assert [plan["display_heading"] for plan in normalized["target_anchor_plan"]] == [
        "3 功能需求 / 异常与补偿",
        "6 验收准则 / 验收准则",
    ]


def test_decision_state_service_applies_question_lifecycle_refs_without_semantic_matching() -> None:
    service = DecisionStateService()
    state = {
        "topic": "态势分析系统需求规格探索",
        "confirmed_facts": [],
        "confirmed_decisions": [],
        "tentative_assumptions": [],
        "open_questions": [
            {
                "item_id": "DS-Q-001",
                "content": "用户角色有哪些？",
                "source_turn_id": "turn-0001",
                "target_section": "3 功能需求 / 用户与角色",
                "status": "open",
            },
            {
                "item_id": "DS-Q-002",
                "content": "软件名称是什么？",
                "source_turn_id": "turn-0001",
                "target_section": "1 总则 / 编写目的",
                "status": "open",
            },
        ],
        "rejected_directions": [],
        "next_focus": "用户角色有哪些？",
        "chapter_projections": [],
    }
    delta = {
        "confirmed_facts": [
            {
                "content": "主要用户是科研分析人员。",
                "target_section": "3 功能需求 / 用户与角色",
            }
        ],
        "confirmed_decisions": [],
        "tentative_assumptions": [],
        "open_questions": [],
        "closed_question_refs": [
            {
                "item_id": "DS-Q-001",
                "status": "closed",
                "reason": "用户已回答主要用户问题。",
            }
        ],
        "deferred_question_refs": [
            {
                "content": "软件名称是什么？",
                "status": "deferred",
                "reason": "允许后续补充。",
            }
        ],
        "rejected_directions": [],
        "chapter_projections": [],
        "next_focus": "继续确认使用流程。",
    }

    result = service.apply_delta(decision_state=state, delta=delta, turn_id="turn-0002")

    questions = result.decision_state["open_questions"]
    assert questions[0]["item_id"] == "DS-Q-001"
    assert questions[0]["status"] == "closed"
    assert questions[0]["resolution_reason"] == "用户已回答主要用户问题。"
    assert questions[1]["item_id"] == "DS-Q-002"
    assert questions[1]["status"] == "deferred"
    assert questions[1]["resolution_reason"] == "允许后续补充。"
    assert result.decision_state_change_summary["question_lifecycle_counts"] == {
        "closed": 1,
        "deferred": 1,
        "superseded": 0,
    }


def test_decision_state_service_keeps_item_ids_unique_without_business_semantic_matching() -> None:
    service = DecisionStateService()
    state = {
        "topic": "态势分析系统需求规格探索",
        "confirmed_facts": [
            {
                "item_id": "DS-F-001",
                "content": "主要用户倾向为科研分析人员。",
                "source_turn_id": "turn-0001",
                "target_section": "3 功能需求 / 用户与角色",
                "status": "active",
            }
        ],
        "confirmed_decisions": [],
        "tentative_assumptions": [],
        "open_questions": [
            {
                "item_id": "DS-Q-001",
                "content": "用户角色有哪些？",
                "source_turn_id": "turn-0001",
                "target_section": "3 功能需求 / 用户与角色",
                "status": "open",
            }
        ],
        "rejected_directions": [],
        "next_focus": "用户角色有哪些？",
        "chapter_projections": [],
    }
    delta = {
        "confirmed_facts": [
            {
                "item_id": "DS-F-001",
                "content": "业务专家参与结果复核。",
                "target_section": "3 功能需求 / 用户与角色",
            }
        ],
        "confirmed_decisions": [],
        "tentative_assumptions": [],
        "open_questions": [
            {
                "item_id": "DS-Q-001",
                "content": "导出格式是什么？",
                "target_section": "3 功能需求 / 结果输出与共享",
                "status": "open",
            },
            {
                "item_id": "DS-Q-001",
                "content": "验收口径是什么？",
                "target_section": "6 验收准则 / 验收准则",
                "status": "open",
            },
        ],
        "rejected_directions": [],
        "chapter_projections": [],
        "next_focus": "继续确认输出与验收。",
    }

    result = service.apply_delta(decision_state=state, delta=delta, turn_id="turn-0002")

    facts = result.decision_state["confirmed_facts"]
    questions = result.decision_state["open_questions"]
    assert [item["item_id"] for item in facts] == ["DS-F-001", "DS-F-002"]
    assert [item["item_id"] for item in questions] == ["DS-Q-001", "DS-Q-002", "DS-Q-003"]
    assert [item["content"] for item in questions] == [
        "用户角色有哪些？",
        "导出格式是什么？",
        "验收口径是什么？",
    ]


def test_decision_state_service_defers_open_questions_on_delivery_without_semantic_matching() -> None:
    service = DecisionStateService()
    state = {
        "topic": "态势分析系统需求规格探索",
        "confirmed_facts": [],
        "confirmed_decisions": [],
        "tentative_assumptions": [],
        "open_questions": [
            {
                "item_id": "DS-Q-001",
                "content": "用户角色有哪些？",
                "source_turn_id": "turn-0001",
                "target_section": "3 功能需求 / 用户与角色",
                "status": "open",
            },
            {
                "item_id": "DS-Q-002",
                "content": "部署环境是什么？",
                "source_turn_id": "turn-0002",
                "target_section": "5 非功能需求 / 运行环境",
                "status": "open",
            },
            {
                "item_id": "DS-Q-003",
                "content": "已人工后置的问题。",
                "source_turn_id": "turn-0003",
                "target_section": "6 验收准则 / 待确认事项",
                "status": "deferred",
            },
        ],
        "rejected_directions": [],
        "next_focus": "输出草案",
        "chapter_projections": [],
    }

    result = service.defer_open_questions_for_delivery(
        decision_state=state,
        reason="交付模式下未闭合问题转入草案待确认事项。",
    )

    questions = result.decision_state["open_questions"]
    assert questions[0]["status"] == "deferred"
    assert questions[0]["resolution_reason"] == "交付模式下未闭合问题转入草案待确认事项。"
    assert questions[1]["status"] == "deferred"
    assert questions[2]["status"] == "deferred"
    assert "resolution_reason" not in questions[2]
    assert result.decision_state_change_summary["question_lifecycle_counts"] == {
        "closed": 0,
        "deferred": 2,
        "superseded": 0,
    }


def test_plugin_turn_result_materializer_supports_delivery_interaction_without_open_question() -> None:
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
            "filled_document_text": "## 需求规格说明草案\n\n空域运算软件用于空域计算分析。",
            "document_patch": [
                {
                    "operation": "replace",
                    "anchor_path": "REQ-6.3",
                    "target_section": "6 验收准则 / 待确认事项",
                    "content": "## 需求规格说明草案\n\n空域运算软件用于空域计算分析。",
                }
            ],
            "changed_sections": ["6 验收准则 / 待确认事项"],
            "completion_status": "completed",
            "confidence": "medium",
        },
        interaction_output={
            "assistant_message": "已生成完整需求规格说明草案，本轮不再继续追问。",
            "next_question": "",
            "quick_options": [],
            "suggested_focus": {"should_ask_user": False, "interaction_mode": "draft_delivery"},
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

    assert turn_result.turn["next_interaction"]["type"] == "draft_delivery"
    assert turn_result.turn["next_interaction"]["prompt"] == "已生成完整需求规格说明草案，本轮不再继续追问。"
    assert turn_result.turn["next_interaction"]["options"] == []
    assert turn_result.turn["next_interaction"]["target_spec_node_ids"] == []
    assert turn_result.state_patch["last_quick_options"] == []
    assert turn_result.state_patch["next_interaction"]["type"] == "draft_delivery"


def test_plugin_turn_result_materializer_falls_back_to_filled_document_text_when_document_patch_missing() -> None:
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


def test_removed_legacy_dify_workflow_plugin_is_not_loadable() -> None:
    registry = OrchestratorPluginRegistry()

    with pytest.raises(ValueError, match="unsupported orchestrator"):
        registry.require("xg-dify-workflow-orchestrator")


def test_plugin_result_normalizer_projects_observable_result_to_turn_payload() -> None:
    result = OrchestratorRunResult(
        contract_version="xg-observable-orchestrator-contract@1",
        plugin={
            "plugin_id": "brainstorm-v1-dify-workflow",
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
