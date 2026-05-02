from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.session_repository import RequirementAnalysisSessionRepository
from app.orchestrators.package_loader import get_orchestrator_registry
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.db.models.requirements import RequirementAnalysisSession


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
