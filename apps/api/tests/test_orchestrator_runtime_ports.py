from __future__ import annotations

from types import SimpleNamespace

from app.orchestrators.plugin_contracts import (
    OrchestratorPluginManifest,
    OrchestratorRunRequest,
    OrchestratorRunResult,
)
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.turn_engine import RequirementAnalysisTurnEngine
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.orchestrators.runtime.runtime_host import OrchestratorRuntimeHost
from app.orchestrators.runtime.request_mapper import OrchestratorRunRequestMapper


def test_adapter_loader_passes_runtime_host_to_plugin_constructor(tmp_path) -> None:
    plugin_dir = tmp_path / "xg" / "xg-runtime-host-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "adapter.py").write_text(
        "class RuntimeHostAwareAdapter:\n"
        "    def __init__(self, *, manifest, package=None, runtime_host=None):\n"
        "        self.manifest = manifest\n"
        "        self.runtime_host = runtime_host\n"
        "\n"
        "    def run(self, request):\n"
        "        if self.runtime_host is None:\n"
        "            raise RuntimeError('runtime_host_missing')\n"
        "        return {'runtime_host_id': id(self.runtime_host)}\n",
        encoding="utf-8",
    )
    manifest = OrchestratorPluginManifest(
        plugin_id="xg-runtime-host-plugin",
        name="Runtime Host Plugin",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=1,
        capabilities={"document_patch": True},
        requires={"template": True},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="RuntimeHostAwareAdapter",
        package_path=str(plugin_dir),
    )

    from app.orchestrators.adapters.base import load_orchestrator_plugin_adapter

    runtime_host = object()
    adapter = load_orchestrator_plugin_adapter(manifest, runtime_host=runtime_host)

    assert adapter.runtime_host is runtime_host


def test_turn_engine_passes_runtime_host_to_plugin_loader(monkeypatch) -> None:
    captured: dict[str, object] = {}
    runtime_host = object()
    manifest = OrchestratorPluginManifest(
        plugin_id="xg-runtime-host-plugin",
        name="Runtime Host Plugin",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=1,
        capabilities={"document_patch": True},
        requires={"template": True},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="RuntimeHostAwareAdapter",
        package_path="orchestrators/xg/xg-heuristic-orchestrator",
    )

    class StubAdapter:
        def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
            return OrchestratorRunResult(
                contract_version=request.contract_version,
                plugin={
                    "plugin_id": "xg-runtime-host-plugin",
                    "plugin_type": "local_package",
                    "observability_level": "full",
                },
                final_output={
                    "filled_document_text": "",
                    "document_patch": [],
                    "changed_sections": [],
                    "completion_status": "partial",
                    "confidence": "medium",
                },
                interaction_output={
                    "assistant_message": "",
                    "next_question": "",
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
                    "turn_execution_result": TurnExecutionResult(turn={}, state_patch={}, provider_logs=[]),
                },
            )

    class StubTurnContextBuilder:
        def build(self, *, session, turn_id, user_input):
            return SimpleNamespace(
                turn_index=1,
                working_document={},
                spec_tree=[],
                active_spec_node={},
                active_spec_node_id="",
                facts=[],
                questions=[],
                patches=[],
                previous_interaction={},
                input_relation={},
                normalized_input={"semantic": user_input, "input_type": "free_text"},
            )

    class StubWorkingDocumentService:
        def initialize(self, *, topic, template_id):
            return {"document_id": "lab-working-document", "blocks": []}

    class StubRegistry:
        def require(self, orchestrator_id):
            return manifest

    def fake_loader(plugin_manifest, *, package=None, runtime_host=None):
        captured["plugin_manifest"] = plugin_manifest
        captured["runtime_host"] = runtime_host
        return StubAdapter()

    from app.requirement_analysis import turn_engine as turn_engine_module

    monkeypatch.setattr(turn_engine_module, "get_orchestrator_plugin_registry", lambda: StubRegistry())
    monkeypatch.setattr(turn_engine_module, "load_orchestrator_plugin_adapter", fake_loader)

    engine = RequirementAnalysisTurnEngine(
        turn_context_builder=StubTurnContextBuilder(),
        working_document_service=StubWorkingDocumentService(),
        runtime_host=runtime_host,
    )
    engine.run_turn(
        SessionSnapshot(
            session_id="ra-001",
            topic="空域运算软件需求规格探索",
            orchestrator_id="xg-runtime-host-plugin",
            provider_id="mock",
            model="mock-requirement-analysis-v1",
            template_id="81433号",
            knowledge_package_id="airspace-domain-demo",
            write_policy="patch_suggestion_only",
            status="created",
            payload={},
        ),
        RequirementAnalysisTurnCreate(user_input="测试输入"),
    )

    assert captured["plugin_manifest"] is manifest
    assert captured["runtime_host"] is runtime_host


def test_runtime_host_build_policy_interpreted_runtime_returns_shared_runtime() -> None:
    runtime_host = OrchestratorRuntimeHost(
        turn_context_builder=object(),
        provider_call_service=object(),
        provider_call_log_service=object(),
        spec_tree_service=object(),
        spec_projection_service=object(),
        summary_artifact_service=object(),
        turn_audit_service=object(),
        turn_output_service=object(),
        next_interaction_service=object(),
        working_document_service=object(),
        working_document_review_service=object(),
        turn_decision_service=object(),
    )

    runtime = runtime_host.build_policy_interpreted_runtime()

    from app.orchestrators.runtime.policy_interpreted_runtime import PolicyInterpretedRuntime

    assert isinstance(runtime, PolicyInterpretedRuntime)


def test_request_mapper_builds_shared_runtime_input() -> None:
    manifest = OrchestratorPluginManifest(
        plugin_id="brainstorm-v1",
        name="Brainstorm V1",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=1,
        capabilities={"document_patch": True},
        requires={"template": True},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="LocalXGOrchestratorPluginAdapter",
        package_path="orchestrators/xg/brainstorm-v1",
    )
    request = OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={
            "session_id": "ra-001",
            "topic": "默认运算软件需求规格说明",
            "provider_id": "deepseek",
            "model": "deepseek-chat",
            "template_id": "81433号",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
        turn={
            "user_input": "请补充软件定位",
            "previous_interaction": {"type": "choice_question", "prompt": "上一问"},
        },
        template={},
        document_context={
            "state": {"session_phase": "exploration_convergence"},
            "confirmed_facts": ["已确认事实 A"],
            "open_questions": ["未闭合问题 A"],
            "working_document": {"blocks": [{"block_id": "blk-1"}]},
            "patches": [{"patch_id": "p-1"}],
            "spec_tree": [{"node_id": "SPEC-REQ-1.1"}],
            "active_spec_node": {"node_id": "SPEC-REQ-1.1"},
        },
        execution_options={},
    )

    runtime_input = OrchestratorRunRequestMapper().build(request=request, manifest=manifest)

    assert runtime_input.session_snapshot.orchestrator_id == "brainstorm-v1"
    assert runtime_input.session_snapshot.provider_id == "deepseek"
    assert runtime_input.turn_payload.user_input == "请补充软件定位"
    assert runtime_input.session_snapshot.payload["confirmed_facts"] == ["已确认事实 A"]
    assert runtime_input.session_snapshot.payload["questions"] == ["未闭合问题 A"]
    assert runtime_input.session_snapshot.payload["next_interaction"] == {"type": "choice_question", "prompt": "上一问"}
    assert runtime_input.session_snapshot.payload["session_phase"] == "exploration_convergence"


def test_runtime_host_run_policy_interpreted_uses_shared_request_mapper(monkeypatch) -> None:
    runtime_host = OrchestratorRuntimeHost(
        turn_context_builder=object(),
        provider_call_service=object(),
        provider_call_log_service=object(),
        spec_tree_service=object(),
        spec_projection_service=object(),
        summary_artifact_service=object(),
        turn_audit_service=object(),
        turn_output_service=object(),
        next_interaction_service=object(),
        working_document_service=object(),
        working_document_review_service=object(),
        turn_decision_service=object(),
    )
    manifest = OrchestratorPluginManifest(
        plugin_id="xg-heuristic-orchestrator",
        name="Heuristic",
        plugin_type="local_package",
        document_type="xg",
        contract="xg-observable-orchestrator-contract@1",
        status="active",
        priority=1,
        capabilities={"document_patch": True},
        requires={"template": True},
        adapter_entry="local_xg",
        adapter_module="adapter",
        adapter_class="LocalXGOrchestratorPluginAdapter",
        package_path="orchestrators/xg/xg-heuristic-orchestrator",
    )
    request = OrchestratorRunRequest(
        contract_version="xg-observable-orchestrator-contract@1",
        session={"session_id": "ra-001", "topic": "默认运算软件需求规格说明"},
        turn={"user_input": "测试输入"},
        template={},
        document_context={},
        execution_options={},
    )
    captured: dict[str, object] = {}

    class StubRuntime:
        def run_turn(self, session, payload):
            captured["session"] = session
            captured["payload"] = payload
            return TurnExecutionResult(turn={"turn_id": "turn-0001"}, state_patch={}, provider_logs=[])

    monkeypatch.setattr(runtime_host, "build_policy_interpreted_runtime", lambda: StubRuntime())

    result = runtime_host.run_policy_interpreted(request, manifest)

    assert isinstance(captured["session"], SessionSnapshot)
    assert isinstance(captured["payload"], RequirementAnalysisTurnCreate)
    assert result.turn["turn_id"] == "turn-0001"
