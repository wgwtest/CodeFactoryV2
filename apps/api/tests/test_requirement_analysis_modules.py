from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.session_repository import RequirementAnalysisSessionRepository
from app.orchestrators.package_loader import OrchestratorPackageLoader, get_orchestrator_registry
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService, SpecTreeUpdateResult
from app.db.models.requirements import RequirementAnalysisSession
from app.requirement_analysis.provider_call_service import ProviderRunResult
from app.requirement_analysis.summary_artifact_service import ArtifactUpdateResult, RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.turn_context_builder import TurnContext
from app.requirement_analysis.turn_decision_service import TurnDecisionService, TurnDecisionResult
from app.requirement_analysis.turn_stage_planner import TurnStagePlanner, TurnStagePlan
from app.requirement_analysis.turn_stage_reducer import TurnStageAudit, TurnStageReducer
from app.requirement_analysis.turn_stage_executor import TurnStageExecutor, TurnStageResult
from app.requirement_analysis.turn_strategy_service import TurnStrategyService
from app.requirement_analysis.working_document_review_service import WorkingDocumentReviewService
from app.requirement_analysis.working_document_service import WorkingDocumentService


def test_requirement_analysis_modules_cover_turn_core_contract(db_session) -> None:
    normalizer = InputNormalizer()
    normalized = normalizer.normalize_input(
        "A",
        quick_options=[
            {"key": "A", "label": "计算分析工具", "recommended": True},
            {"key": "B", "label": "协同规划平台", "recommended": False},
        ],
    )
    assert normalized == {
        "input_type": "quick_option_answer",
        "matched_option": "A",
        "matched_option_label": "计算分析工具",
        "semantic": "计算分析工具",
    }
    assert normalizer.normalize_input("A") == {
        "input_type": "quick_option_answer",
        "matched_option": "A",
        "matched_option_label": None,
        "semantic": "A",
    }

    relation = InputRelationClassifier(normalizer=normalizer).classify(
        {"type": "choice_question", "prompt": "软件定位是什么？", "options": []},
        normalized,
        last_quick_options=[{"key": "A", "label": "计算分析工具", "recommended": True}],
    )
    assert relation["relation"] == "selected_option"

    spec_tree_service = RequirementSpecTreeService(db_session)
    spec_tree = spec_tree_service.new_spec_tree(
        "81433号",
        orchestrator_id="xg-heuristic-orchestrator",
    )
    assert spec_tree[0]["title"] == "需求规格说明完成度树（81433号）"
    assert spec_tree_service.first_open_spec_node_id(spec_tree) == "SPEC-REQ-1.1"

    node = spec_tree_service.active_spec_node_context(spec_tree, "SPEC-REQ-2.1")
    assert node["target_section"] == "2 项目概述 / 软件定位"
    assert node["question"] == "组织器策略问题：请确认软件定位、领域边界、解决的问题，以及第一阶段明确不做的内容。"
    strong_tree = spec_tree_service.new_spec_tree(
        "81433号",
        orchestrator_id="xg-strong-rule-orchestrator",
    )
    strong_node = spec_tree_service.active_spec_node_context(strong_tree, "SPEC-REQ-2.1")
    assert strong_node["question"] == "强规则组织器要求补齐：软件定位。"

    artifact_service = ProcessArtifactService()
    assert (
        artifact_service.fact_for_node("xg-heuristic-orchestrator", {"node_id": "SPEC-REQ-2.1"}, "计算分析工具")
        == "软件定位初步确认：计算分析工具"
    )
    assert (
        artifact_service.patch_for_node("xg-heuristic-orchestrator", {"node_id": "SPEC-REQ-2.1"}, "计算分析工具")
        == "软件定位为：计算分析工具"
    )
    assert artifact_service.quick_options_for_node("xg-heuristic-orchestrator", {"node_id": "SPEC-REQ-2.1"})[0]["label"] == "计算分析工具"
    assert get_orchestrator_registry().require_loaded("xg-heuristic-orchestrator").spec_strategy["root_question"]


def test_requirement_analysis_turn_strategy_comes_from_orchestrator_package() -> None:
    registry = get_orchestrator_registry()
    orchestrator = registry.require("xg-heuristic-orchestrator")
    context = TurnContext(
        turn_id="turn-0001",
        turn_index=1,
        session_id="session-1",
        topic="空域运算软件需求规格探索",
        template_id="81433号",
        knowledge_package_id="airspace-domain-demo",
        orchestrator_id="xg-heuristic-orchestrator",
        provider_id="mock",
        model="mock-requirement-analysis-v1",
        write_policy="patch_suggestion_only",
        user_input="补充系统目标",
        normalized_input={"semantic": "补充系统目标"},
        previous_interaction={"type": "none"},
        input_relation={"relation": "none"},
        spec_tree=[],
        active_spec_node_id="SPEC-REQ-1.1",
        active_spec_node={},
        working_document={},
        questions=[],
        facts=[],
        patches=[],
        last_quick_options=[],
    )

    strategy = TurnStrategyService(registry=registry).load(orchestrator=orchestrator, context=context)

    assert strategy.strategy_id == "xg-heuristic-orchestrator:intent_write_review_plan"
    assert strategy.adoption_policy == "adopt_last_completed_stage"
    assert [stage["stage_id"] for stage in strategy.stages] == [
        "intent_understanding",
        "write",
        "review_after_apply",
        "next_interaction_planning",
    ]
    assert [stage["stage_type"] for stage in strategy.stages] == ["policy_interpreted"] * 4
    assert [stage["stage_kind"] for stage in strategy.stages] == [
        "intent",
        "write",
        "review",
        "next_interaction",
    ]
    assert [stage["prompt_id"] for stage in strategy.stages] == [
        "intent_understanding",
        "write",
        "review_after_apply",
        "next_interaction_planning",
    ]


def test_orchestrator_package_loads_stage_prompt_schema_and_adoption_assets() -> None:
    loaded = OrchestratorPackageLoader().load("xg-heuristic-orchestrator")

    assert "base_contract" in loaded.stage_prompts
    assert "intent_understanding.system" in loaded.stage_prompts
    assert "intent_understanding.user" in loaded.stage_prompts
    assert "write.system" in loaded.stage_prompts
    assert "write.user" in loaded.stage_prompts
    assert "review_after_apply.system" in loaded.stage_prompts
    assert "review_after_apply.user" in loaded.stage_prompts
    assert "next_interaction_planning.system" in loaded.stage_prompts
    assert "next_interaction_planning.user" in loaded.stage_prompts
    assert loaded.stage_schemas["intent_understanding"]["type"] == "object"
    assert "intent_understanding_result" in loaded.stage_schemas["intent_understanding"]["properties"]
    assert loaded.stage_schemas["write"]["type"] == "object"
    assert "document_patch" in loaded.stage_schemas["write"]["properties"]
    assert "target_review" in loaded.stage_schemas["review_after_apply"]["properties"]
    assert "next_interaction_plan" in loaded.stage_schemas["next_interaction_planning"]["properties"]
    assert loaded.stage_adoption_policies["intent_understanding"]["adopt_fields"] == [
        "intent_understanding_result",
        "target_document_structure",
        "stage_task_definition",
        "stage_quality_constraints",
        "confidence",
    ]
    assert loaded.stage_adoption_policies["write"]["adopt_fields"] == [
        "organizer_interpretation",
        "confirmed_facts_delta",
        "document_patch",
        "annotations",
        "risks",
        "confidence",
    ]
    assert loaded.stage_adoption_policies["review_after_apply"]["adopt_fields"] == [
        "target_review",
        "global_review",
        "review_annotations",
        "confidence",
    ]
    assert loaded.stage_adoption_policies["next_interaction_planning"]["adopt_fields"] == [
        "next_interaction_plan",
        "planning_trace",
        "confidence",
    ]


def test_orchestrator_runner_host_builds_stage_specific_prompt_bundle() -> None:
    host = OrchestratorRunnerHost()

    write_bundle = host.build_stage_prompt_bundle(
        "xg-heuristic-orchestrator",
        stage={"stage_id": "write", "stage_kind": "write"},
        context={"user_input": "补充系统目标", "working_document": {"blocks": []}},
    )
    intent_bundle = host.build_stage_prompt_bundle(
        "xg-heuristic-orchestrator",
        stage={"stage_id": "intent_understanding", "stage_kind": "intent"},
        context={"user_input": "补充系统目标", "previous_interaction": {"type": "none"}},
    )
    review_bundle = host.build_stage_prompt_bundle(
        "xg-heuristic-orchestrator",
        stage={"stage_id": "review_after_apply", "stage_kind": "review", "prompt_id": "review_after_apply"},
        context={
            "working_document_after_apply": {"blocks": [{"block_id": "blk-0001", "text": "目标正文"}]},
            "target_review": {"status": "acceptable"},
        },
    )
    planning_bundle = host.build_stage_prompt_bundle(
        "xg-heuristic-orchestrator",
        stage={"stage_id": "next_interaction_planning", "stage_kind": "next_interaction"},
        context={"target_review": {"status": "acceptable"}, "global_review": {"status": "move_next_node"}},
    )

    assert intent_bundle["stage_id"] == "intent_understanding"
    assert intent_bundle["prompt_id"] == "intent_understanding"
    assert "识别用户这一轮真正想做什么" in intent_bundle["stage_prompt_text"]
    assert "intent_understanding_result" in intent_bundle["schema_json"]
    assert write_bundle["stage_id"] == "write"
    assert write_bundle["prompt_id"] == "write"
    assert "只返回 JSON" in write_bundle["base_contract_text"]
    assert "理解用户本轮输入" in write_bundle["stage_prompt_text"]
    assert "document_patch" in write_bundle["schema_json"]
    assert "adoption_policy_json" in write_bundle
    assert review_bundle["stage_id"] == "review_after_apply"
    assert review_bundle["prompt_id"] == "review_after_apply"
    assert "应用后的临时正文" in review_bundle["stage_prompt_text"]
    assert "target_review" in review_bundle["schema_json"]
    assert planning_bundle["stage_id"] == "next_interaction_planning"
    assert planning_bundle["prompt_id"] == "next_interaction_planning"
    assert "下一步交互规划" in planning_bundle["stage_prompt_text"]
    assert "next_interaction_plan" in planning_bundle["schema_json"]
    assert write_bundle["assembled_prompt"] != review_bundle["assembled_prompt"]


def test_requirement_analysis_turn_stage_plan_and_reducer_are_typed() -> None:
    context = TurnContext(
        turn_id="turn-0001",
        turn_index=1,
        session_id="session-1",
        topic="空域运算软件需求规格探索",
        template_id="81433号",
        knowledge_package_id="airspace-domain-demo",
        orchestrator_id="xg-heuristic-orchestrator",
        provider_id="mock",
        model="mock-requirement-analysis-v1",
        write_policy="patch_suggestion_only",
        user_input="补充系统目标",
        normalized_input={"semantic": "补充系统目标"},
        previous_interaction={"type": "none"},
        input_relation={"relation": "none"},
        spec_tree=[],
        active_spec_node_id="SPEC-REQ-1.1",
        active_spec_node={},
        working_document={},
        questions=[],
        facts=[],
        patches=[],
        last_quick_options=[],
    )
    registry = get_orchestrator_registry()
    orchestrator = registry.require("xg-heuristic-orchestrator")
    strategy = TurnStrategyService(registry=registry).load(orchestrator=orchestrator, context=context)

    plan = TurnStagePlanner().build_plan(strategy=strategy, context=context, orchestrator=orchestrator)

    assert isinstance(plan, TurnStagePlan)
    assert plan.strategy_id.endswith("intent_write_review_plan")
    assert [stage["stage_id"] for stage in plan.stages] == [
        "intent_understanding",
        "write",
        "review_after_apply",
        "next_interaction_planning",
    ]
    assert plan.stages[0]["stage_kind"] == "intent"
    assert plan.stages[0]["requires_provider_call"] is True
    assert plan.stages[1]["stage_kind"] == "write"
    assert plan.stages[2]["stage_kind"] == "review"
    assert plan.stages[2]["requires_provider_call"] is True
    assert plan.stages[2]["execution_mode"] == "model"
    assert plan.stages[2]["input_sources"] == ["working_document_after_apply", "working_document_update"]
    assert plan.stages[3]["stage_kind"] == "next_interaction"
    assert plan.stages[3]["input_sources"] == ["review_after_apply", "spec_tree", "working_document"]

    reducer = TurnStageReducer()
    audit = reducer.stage_audit(
        stage=plan.stages[0],
        validation_status="accepted",
        adopted_fields=["document_patch"],
        provider_call_log_id="call-0001",
        summary="补写阶段已采纳。",
    )

    assert isinstance(audit, TurnStageAudit)
    assert audit.stage_id == "intent_understanding"
    assert audit.to_dict()["adopted_fields"] == ["document_patch"]


def test_requirement_analysis_stage_executor_passes_model_review_stage_input_to_provider() -> None:
    captured: dict = {}

    class FakeProviderCallService:
        def run_orchestrator(self, *, orchestrator, session, user_input: str, normalized: dict, stage: dict, stage_input: dict):
            captured["stage"] = stage
            captured["stage_input"] = stage_input
            return ProviderRunResult(
                model_output={
                    "target_review": {
                        "status": "acceptable",
                        "reason": "应用后的临时正文已覆盖目标。",
                        "covered_points": ["系统目标"],
                        "missing_aspects": [],
                        "evidence_block_ids": ["blk-0001"],
                        "evidence_fragment_ids": ["frag-0001"],
                    },
                    "global_review": {
                        "status": "move_next_node",
                        "summary": "可以推进下一节点。",
                        "remaining_gaps": [],
                    },
                    "review_annotations": ["模型 Review 已执行。"],
                    "confidence": "high",
                    "raw_model_response": {
                        "provider_id": "deepseek",
                        "model": "deepseek-chat",
                        "mock": False,
                        "provider_request": {"prompt_bundle": {"assembled_prompt": "review prompt"}},
                        "provider_response": {"raw_content": "{}", "parsed_json": {}},
                        "provider_normalized_output": {
                            "target_review": {"status": "acceptable"},
                            "global_review": {"status": "move_next_node"},
                        },
                    },
                },
                provider_request={"prompt_bundle": {"assembled_prompt": "review prompt"}},
                provider_response={"raw_content": "{}", "parsed_json": {}},
                normalized_output={
                    "target_review": {"status": "acceptable"},
                    "global_review": {"status": "move_next_node"},
                },
            )

    context = TurnContext(
        turn_id="turn-0001",
        turn_index=1,
        session_id="session-1",
        topic="默认运算软件需求规格说明",
        template_id="81433号",
        knowledge_package_id="airspace-domain-demo",
        orchestrator_id="xg-heuristic-orchestrator",
        provider_id="deepseek",
        model="deepseek-chat",
        write_policy="patch_suggestion_only",
        user_input="补充系统目标",
        normalized_input={"semantic": "补充系统目标"},
        previous_interaction={"type": "none"},
        input_relation={"relation": "none"},
        spec_tree=[],
        active_spec_node_id="SPEC-REQ-1.1",
        active_spec_node={"question": "请确认系统目标。"},
        working_document={},
        questions=[],
        facts=[],
        patches=[],
        last_quick_options=[],
    )
    review_stage_input = {
        "working_document_after_apply": {"blocks": [{"block_id": "blk-0001", "text": "目标正文"}]},
        "working_document_update": {"applied_fragment_ids": ["frag-0001"]},
        "target_review": {"status": "acceptable"},
        "global_review": {"status": "move_next_node"},
    }

    result = TurnStageExecutor(provider_call_service=FakeProviderCallService()).run(
        stage={
            "stage_id": "review_after_apply",
            "stage_type": "policy_interpreted",
            "stage_kind": "review",
            "execution_mode": "model",
            "prompt_id": "review_after_apply",
            "requires_provider_call": True,
        },
        orchestrator=get_orchestrator_registry().require("xg-heuristic-orchestrator"),
        session=type("Session", (), {"provider_id": "deepseek", "model": "deepseek-chat"})(),
        context=context,
        stage_input=review_stage_input,
    )

    assert result.stage_id == "review_after_apply"
    assert result.stage_type == "policy_interpreted"
    assert result.model_output["target_review"]["status"] == "acceptable"
    assert captured["stage"]["prompt_id"] == "review_after_apply"
    assert captured["stage_input"]["working_document_after_apply"]["blocks"][0]["block_id"] == "blk-0001"


def test_requirement_analysis_stage_executor_blocks_when_model_stage_fails() -> None:
    class FailingProviderCallService:
        def run_orchestrator(self, **kwargs):
            raise RuntimeError("review provider unavailable")

    context = TurnContext(
        turn_id="turn-0001",
        turn_index=1,
        session_id="session-1",
        topic="默认运算软件需求规格说明",
        template_id="81433号",
        knowledge_package_id="airspace-domain-demo",
        orchestrator_id="xg-heuristic-orchestrator",
        provider_id="deepseek",
        model="deepseek-chat",
        write_policy="patch_suggestion_only",
        user_input="补充系统目标",
        normalized_input={"semantic": "补充系统目标"},
        previous_interaction={"type": "open_question", "prompt": "请确认系统目标。"},
        input_relation={"relation": "answered"},
        spec_tree=[],
        active_spec_node_id="SPEC-REQ-1.1",
        active_spec_node={"question": "请确认系统目标。"},
        working_document={},
        questions=[],
        facts=[],
        patches=[],
        last_quick_options=[],
    )

    try:
        TurnStageExecutor(provider_call_service=FailingProviderCallService()).run(
            stage={
                "stage_id": "review_after_apply",
                "stage_type": "policy_interpreted",
                "stage_kind": "review",
                "execution_mode": "model",
                "prompt_id": "review_after_apply",
                "requires_provider_call": True,
            },
            orchestrator=get_orchestrator_registry().require("xg-heuristic-orchestrator"),
            session=type("Session", (), {"provider_id": "deepseek", "model": "deepseek-chat"})(),
            context=context,
            stage_input={
                "working_document_after_apply": {"excerpt": "本规格说明用于定义默认运算软件。"},
                "working_document_update": {"after_excerpt": "本规格说明用于定义默认运算软件。"},
                "target_review": {"status": "acceptable"},
                "global_review": {"status": "move_next_node"},
            },
        )
    except RuntimeError as exc:
        assert str(exc) == "review provider unavailable"
    else:
        raise AssertionError("expected model stage failure to block turn execution")


def test_turn_decision_service_decides_after_review() -> None:
    result = TurnDecisionService().decide(
        normalized_input={"semantic": "补充系统目标"},
        working_document_update={"after_excerpt": "1 总则 / 编写目的\n本系统用于空域计算分析。"},
        post_update_review={
            "target_review": {"status": "acceptable", "reason": "目标范围已有正文。"},
            "global_review": {"status": "move_next_node", "summary": "可以推进下一节点。"},
        },
        projection={"projection_spec_node_id": "SPEC-REQ-1.1"},
        next_interaction={"type": "choice_question", "prompt": "建议下一步确认软件定位。"},
    )

    assert isinstance(result, TurnDecisionResult)
    assert result.closure_decision["status"] == "closed"
    assert result.closure_decision["next_action"] == "propose_next_interaction"
    assert result.next_interaction["prompt"] == "建议下一步确认软件定位。"
    assert any("正文已应用后再进行回看" in item for item in result.decision_trace)


def test_requirement_analysis_update_services_return_typed_contracts(db_session) -> None:
    spec_tree_service = RequirementSpecTreeService(db_session)
    spec_tree = spec_tree_service.new_spec_tree(
        "81433号",
        orchestrator_id="xg-heuristic-orchestrator",
    )
    spec_update = spec_tree_service.update_spec_tree(
        spec_tree=spec_tree,
        active_node_id="SPEC-REQ-1.1",
        answer_summary="系统名称为空域运算软件。",
        turn_id="turn-0001",
    )
    assert isinstance(spec_update, SpecTreeUpdateResult)
    assert spec_update.closed_node_ids == ["SPEC-REQ-1.1"]
    assert spec_update.active_spec_node_id == "SPEC-REQ-2.1"
    assert spec_update.next_spec_node["node_id"] == "SPEC-REQ-2.1"
    assert spec_update.to_dict()["active_spec_node_id"] == "SPEC-REQ-2.1"

    artifact_update = RequirementAnalysisSummaryArtifactService().build_structured_summary_update(
        model_output={
            "confirmed_facts_delta": ["系统名称为空域运算软件。"],
            "open_questions_delta": [],
            "document_patch": [
                {
                    "section": "1 总则 / 编写目的",
                    "operation": "append_or_update",
                    "content": "系统名称为空域运算软件。",
                    "write_policy": "patch_suggestion_only",
                }
            ],
        },
        normalized={"semantic": "系统名称为空域运算软件。"},
        questions=[
            {
                "question_id": "Q-001",
                "content": "可以补齐：软件名称",
                "status": "open",
                "target_section": "1 总则 / 编写目的",
                "source_turn_id": None,
                "resolution_fact_ids": [],
            }
        ],
        facts=[],
        patches=[],
        target_spec_node={"node_id": "SPEC-REQ-1.1", "target_section": "1 总则 / 编写目的"},
        turn_id="turn-0001",
        session=type("Session", (), {"write_policy": "patch_suggestion_only"})(),
    )
    assert isinstance(artifact_update, ArtifactUpdateResult)
    assert artifact_update.source_question_id == "Q-001"
    assert artifact_update.to_dict()["facts"][0]["fact_id"] == "F-001"


def test_working_document_uses_continuous_blocks_and_revision_fragments() -> None:
    service = WorkingDocumentService()
    working_document = service.initialize(topic="运算软件需求规格说明", template_id="81433号")

    assert "sections" not in working_document
    assert working_document["blocks"] == []
    assert working_document["revision_fragments"] == []

    update = service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "anchor_path": "1.1/编写目的",
                "operation": "append_to_block",
                "content": "本规格说明用于定义运算软件首版的建设目标。",
                "reason": "补入编写目的首句",
            },
            {
                "anchor_path": "1.2/适用范围",
                "operation": "create_block_after_anchor",
                "content": "首版聚焦运算能力，不覆盖协同规划闭环。",
                "reason": "补入范围边界",
            },
        ],
        patch_proposals=[
            {"patch_id": "P-001", "source_turn_id": "turn-0001", "target_section": "1 总则 / 编写目的"},
            {"patch_id": "P-002", "source_turn_id": "turn-0001", "target_section": "1 总则 / 适用范围"},
        ],
        projection_spec_node={"node_id": "SPEC-REQ-1.1", "target_section": "1 总则 / 编写目的"},
        turn_id="turn-0001",
        user_input_summary="用户确认要建设运算软件需求规格说明",
    )

    payload = update.to_dict()
    assert "applied_section_ids" not in payload
    assert payload["applied_block_ids"] == ["blk-0001", "blk-0002"]
    assert payload["applied_fragment_ids"] == ["frag-0001", "frag-0002"]
    assert "本规格说明用于定义运算软件首版的建设目标。" in payload["after_excerpt"]
    assert working_document["blocks"][0]["anchor_path"] == "1.1/编写目的"
    assert working_document["blocks"][1]["anchor_path"] == "1.2/适用范围"
    assert working_document["revision_fragments"][0]["turn_id"] == "turn-0001"
    assert working_document["revision_fragments"][0]["color_token"] == "turn-color-01"
    assert working_document["revision_fragments"][1]["color_token"] == "turn-color-01"

    review = WorkingDocumentReviewService(working_document_service=service).review(
        working_document=working_document,
        review_target_paths=["1.1/编写目的", "1.2/适用范围"],
        current_spec_node={"node_id": "SPEC-REQ-1.1", "question": "请确认编写目的。"},
    )
    assert review["target_review"]["status"] == "acceptable"
    assert review["target_review"]["review_target"] == ["1.1/编写目的", "1.2/适用范围"]
    assert review["global_review"]["status"] in {"move_next_node", "whole_document_review", "continue_same_topic"}


def test_working_document_replace_and_delete_keep_current_text_clean() -> None:
    service = WorkingDocumentService()
    working_document = service.initialize(topic="运算软件需求规格说明", template_id="81433号")

    service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "section": "2 项目概述 / 软件定位",
                "operation": "append_or_update",
                "content": "本软件定位为通用运算分析工具。",
            }
        ],
        patch_proposals=[],
        projection_spec_node={"node_id": "SPEC-REQ-2.1", "target_section": "2 项目概述 / 软件定位"},
        turn_id="turn-0001",
        user_input_summary="初始定位",
    )

    replace_update = service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "section": "2 项目概述 / 软件定位",
                "operation": "replace",
                "content": "本软件定位为空域运算分析工具，第一阶段不做协同规划。",
            }
        ],
        patch_proposals=[],
        projection_spec_node={"node_id": "SPEC-REQ-2.1", "target_section": "2 项目概述 / 软件定位"},
        turn_id="turn-0002",
        user_input_summary="修正定位",
    )

    assert working_document["blocks"][0]["text"] == "本软件定位为空域运算分析工具，第一阶段不做协同规划。"
    assert "通用运算分析工具" not in replace_update.after_excerpt
    assert working_document["revision_fragments"][-1]["apply_mode"] == "replace"
    assert working_document["revision_fragments"][-1]["deleted_text"] == "本软件定位为通用运算分析工具。"

    delete_update = service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "section": "2 项目概述 / 软件定位",
                "operation": "delete",
                "content": "第一阶段不做协同规划",
            }
        ],
        patch_proposals=[],
        projection_spec_node={"node_id": "SPEC-REQ-2.1", "target_section": "2 项目概述 / 软件定位"},
        turn_id="turn-0003",
        user_input_summary="删除阶段边界",
    )

    assert working_document["blocks"][0]["text"] == "本软件定位为空域运算分析工具，。"
    assert "第一阶段不做协同规划" not in delete_update.after_excerpt
    assert working_document["revision_fragments"][-1]["apply_mode"] == "delete"
    assert working_document["revision_fragments"][-1]["deleted_text"] == "第一阶段不做协同规划"


def test_working_document_inserts_late_general_clause_by_template_order() -> None:
    service = WorkingDocumentService()
    working_document = service.initialize(topic="运算软件需求规格说明", template_id="81433号")

    service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "section": "2 总体描述 / 产品范围",
                "operation": "append_or_update",
                "content": "系统第一阶段覆盖态势展示和地理信息分析。",
            },
            {
                "section": "2 总体描述 / 产品功能",
                "operation": "append_or_update",
                "content": "系统提供量算、坡度分析和部署分析工具。",
            },
        ],
        patch_proposals=[],
        projection_spec_node={"node_id": "SPEC-REQ-2.1", "target_section": "2 总体描述 / 产品范围"},
        turn_id="turn-0001",
        user_input_summary="先补总体描述",
    )

    service.apply_patches(
        working_document=working_document,
        document_patch=[
            {
                "section": "1 总则 / 适用范围",
                "operation": "append_or_update",
                "content": "本需求规格说明适用于态势分析系统第一阶段建设。",
            }
        ],
        patch_proposals=[],
        projection_spec_node={"node_id": "SPEC-REQ-1.2", "target_section": "1 总则 / 适用范围"},
        turn_id="turn-0002",
        user_input_summary="回补总则",
    )

    assert [block["anchor_path"] for block in working_document["blocks"]] == [
        "1 总则 / 适用范围",
        "2 总体描述 / 产品范围",
        "2 总体描述 / 产品功能",
    ]
    assert [block["display_heading"] for block in working_document["blocks"]] == [
        "1.2 适用范围",
        "2.1 产品范围",
        "2.2 产品功能",
    ]
    assert [block["order_index"] for block in working_document["blocks"]] == [120, 210, 220]


def test_requirement_analysis_session_repository_persists_lab_session(db_session) -> None:
    repository = RequirementAnalysisSessionRepository(db_session)
    session = RequirementAnalysisSession(
        topic="仓储边界验证",
        orchestrator_id="xg-heuristic-orchestrator",
        provider_id="mock",
        model="mock-requirement-analysis-v1",
        template_id="81433号",
        knowledge_package_id="airspace-domain-demo",
        write_policy="patch_suggestion_only",
        status="created",
        payload={"messages": []},
    )

    saved = repository.add(session)
    assert saved.id

    loaded = repository.get(saved.id)
    assert loaded is not None
    assert loaded.topic == "仓储边界验证"

    loaded.status = "waiting_user"
    loaded.payload = {"messages": [{"role": "assistant", "content": "ok"}]}
    updated = repository.save(loaded)
    assert updated.status == "waiting_user"
    assert updated.payload["messages"][0]["content"] == "ok"
