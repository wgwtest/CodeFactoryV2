from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.session_service import RequirementAnalysisSessionService


def test_requirement_analysis_session_service_preserves_requirement_analysis_flow(db_session) -> None:
    service = RequirementAnalysisSessionService(db_session)
    created = service.create_session(
        RequirementAnalysisSessionCreate(
            topic="空域运算软件需求规格探索",
            orchestrator_id="xg-heuristic-orchestrator",
            provider_id="mock",
            template_id="81433号",
            knowledge_package_id="airspace-domain-demo",
            write_policy="patch_suggestion_only",
        )
    )
    assert created["status"] == "created"
    assert created["questions"][0]["question_id"] == "Q-001"
    assert created["active_spec_node_id"] == "SPEC-REQ-1.1"

    turn = service.add_turn(
        created["session_id"],
        RequirementAnalysisTurnCreate(user_input="这个系统叫空域运算软件，主要解决空域计算分析需求"),
    )
    assert turn is not None
    assert turn["turn"]["turn_id"] == "turn-0001"
    assert turn["session"]["status"] == "waiting_user"
    assert turn["session"]["questions"][0]["status"] == "confirmed"
    assert turn["session"]["active_spec_node_id"] == "SPEC-REQ-2.1"
