from __future__ import annotations

import ast
from pathlib import Path


def test_local_policy_interpreted_adapters_do_not_construct_db_or_session_service() -> None:
    adapter_paths = [
        Path("orchestrators/xg/xg-heuristic-orchestrator/adapter.py"),
        Path("orchestrators/xg/brainstorm-v1/adapter.py"),
    ]
    forbidden_fragments = (
        "SessionLocal",
        "RequirementAnalysisSessionService",
        "from app.db.session import SessionLocal",
        "from app.requirement_analysis.session_service import RequirementAnalysisSessionService",
    )

    for path in adapter_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in source, f"{path} still references forbidden runtime construction fragment: {fragment}"


def test_policy_interpreted_plugins_do_not_keep_copied_runtime_implementation() -> None:
    copied_runtime_files = [
        Path("orchestrators/xg/xg-heuristic-orchestrator/local_xg_turn_runtime.py"),
        Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_planner.py"),
        Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_executor.py"),
        Path("orchestrators/xg/xg-heuristic-orchestrator/turn_stage_reducer.py"),
        Path("orchestrators/xg/xg-heuristic-orchestrator/stage_runtime_context_builder.py"),
        Path("orchestrators/xg/xg-heuristic-orchestrator/turn_strategy_service.py"),
        Path("orchestrators/xg/brainstorm-v1/local_xg_turn_runtime.py"),
        Path("orchestrators/xg/brainstorm-v1/turn_stage_planner.py"),
        Path("orchestrators/xg/brainstorm-v1/turn_stage_executor.py"),
        Path("orchestrators/xg/brainstorm-v1/turn_stage_reducer.py"),
        Path("orchestrators/xg/brainstorm-v1/stage_runtime_context_builder.py"),
        Path("orchestrators/xg/brainstorm-v1/turn_strategy_service.py"),
    ]

    for path in copied_runtime_files:
        assert not path.exists(), f"{path} should be served by app.orchestrators.runtime, not copied in plugin package"


def test_policy_interpreted_runtime_does_not_infer_stage_kind_from_stage_id() -> None:
    source = Path("apps/api/app/orchestrators/runtime/policy_interpreted_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    stage_kind_function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_stage_kind"
    )
    constants = {
        node.value
        for node in ast.walk(stage_kind_function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert "intent" not in constants
    assert "review" not in constants
    assert "next_interaction" not in constants
    assert "planning" not in constants
