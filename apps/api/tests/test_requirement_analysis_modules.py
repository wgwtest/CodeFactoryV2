from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.session_repository import RequirementAnalysisSessionRepository
from app.orchestrators.package_loader import get_orchestrator_registry
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService, SpecTreeUpdateResult
from app.db.models.requirements import RequirementAnalysisSession
from app.requirement_analysis.summary_artifact_service import ArtifactUpdateResult, RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.turn_context_builder import TurnContext
from app.requirement_analysis.turn_stage_executor import TurnStageExecutor, TurnStageResult
from app.requirement_analysis.turn_strategy_service import TurnStrategyService


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

    assert strategy.strategy_id == "xg-heuristic-orchestrator:write_then_review"
    assert strategy.adoption_policy == "adopt_last_completed_stage"
    assert [stage["stage_id"] for stage in strategy.stages] == ["write", "review"]
    assert strategy.stages[0]["stage_type"] == "policy_interpreted"
    assert strategy.stages[1]["stage_type"] == "server_review"


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


def test_requirement_analysis_stage_executor_server_review_is_typed() -> None:
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
    executor = TurnStageExecutor(provider_call_service=type("Provider", (), {})())

    result = executor.run(
        stage={"stage_id": "review", "stage_type": "server_review"},
        orchestrator=get_orchestrator_registry().require("xg-heuristic-orchestrator"),
        session=type("Session", (), {})(),
        context=context,
    )

    assert isinstance(result, TurnStageResult)
    assert result.stage_id == "review"
    assert result.stage_type == "server_review"
    assert result.model_output["raw_model_response"]["provider_id"] == "server_review"


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
