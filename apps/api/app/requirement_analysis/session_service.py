from __future__ import annotations

from datetime import UTC, datetime

from app.config import settings
from app.db.models.requirements import RequirementAnalysisSession
from app.orchestrators.package_loader import OrchestratorPackage, get_orchestrator_registry
from app.orchestrators.plugin_registry import get_orchestrator_plugin_registry, reload_orchestrator_plugin_registry
from app.orchestrators.runtime.decision_state_service import DecisionStateService
from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.next_interaction_service import NextInteractionService
from app.requirement_analysis.provider_call_log_service import ProviderCallLogService
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.provider_call_service import RequirementAnalysisProviderCallService
from app.requirement_analysis.provider_registry import PROVIDER_DEFINITIONS, supported_provider_ids
from app.requirement_analysis.session_repository import RequirementAnalysisSessionRepository
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.spec_projection_service import SpecProjectionService
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.requirement_analysis.summary_artifact_service import RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.template_service import RequirementAnalysisTemplateService
from app.requirement_analysis.turn_audit_service import RequirementAnalysisTurnAuditService
from app.requirement_analysis.turn_context_builder import TurnContextBuilder
from app.requirement_analysis.turn_decision_service import TurnDecisionService
from app.requirement_analysis.turn_engine import RequirementAnalysisTurnEngine
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.requirement_analysis.turn_output_service import RequirementAnalysisTurnOutputService
from app.requirement_analysis.working_document_review_service import WorkingDocumentReviewService
from app.requirement_analysis.working_document_service import WorkingDocumentService


class RequirementAnalysisSessionService:
    def __init__(self, session) -> None:
        self.session = session
        self.repository = RequirementAnalysisSessionRepository(session)
        self.input_normalizer = InputNormalizer()
        self.input_relation_classifier = InputRelationClassifier(normalizer=self.input_normalizer)
        self.process_artifact_service = ProcessArtifactService()
        self.decision_state_service = DecisionStateService()
        self.spec_tree_service = RequirementSpecTreeService(session)
        self.template_service = RequirementAnalysisTemplateService()
        self.provider_call_service = RequirementAnalysisProviderCallService(
            spec_tree_service=self.spec_tree_service,
            process_artifact_service=self.process_artifact_service,
        )
        self.provider_call_log_service = ProviderCallLogService()
        self.summary_artifact_service = RequirementAnalysisSummaryArtifactService()
        self.turn_audit_service = RequirementAnalysisTurnAuditService(normalizer=self.input_normalizer)
        self.turn_output_service = RequirementAnalysisTurnOutputService(spec_tree_service=self.spec_tree_service)
        self.spec_projection_service = SpecProjectionService(spec_tree_service=self.spec_tree_service)
        self.working_document_service = WorkingDocumentService()
        self.working_document_review_service = WorkingDocumentReviewService(
            working_document_service=self.working_document_service,
        )
        self.turn_decision_service = TurnDecisionService()
        self.next_interaction_service = NextInteractionService(
            input_normalizer=self.input_normalizer,
            process_artifact_service=self.process_artifact_service,
        )
        self.turn_context_builder = TurnContextBuilder(
            input_normalizer=self.input_normalizer,
            input_relation_classifier=self.input_relation_classifier,
            spec_tree_service=self.spec_tree_service,
            turn_audit_service=self.turn_audit_service,
        )
        self.turn_engine = RequirementAnalysisTurnEngine(
            turn_context_builder=self.turn_context_builder,
            provider_call_service=self.provider_call_service,
            provider_call_log_service=self.provider_call_log_service,
            spec_tree_service=self.spec_tree_service,
            spec_projection_service=self.spec_projection_service,
            summary_artifact_service=self.summary_artifact_service,
            turn_audit_service=self.turn_audit_service,
            turn_output_service=self.turn_output_service,
            next_interaction_service=self.next_interaction_service,
            working_document_service=self.working_document_service,
            working_document_review_service=self.working_document_review_service,
            turn_decision_service=self.turn_decision_service,
            decision_state_service=self.decision_state_service,
        )

    def list_orchestrators(self) -> dict:
        registry = get_orchestrator_plugin_registry()
        return self._orchestrator_envelope(registry.list_plugins())

    def reload_orchestrators(self) -> dict:
        registry = reload_orchestrator_plugin_registry()
        return self._orchestrator_envelope(registry.list_plugins())

    def _orchestrator_envelope(self, plugins: list) -> dict:
        return {
            "items": [plugin.to_api() for plugin in plugins],
            "stable_contract": self._stable_contract(),
            "output_protocol": [
                "previous_interaction",
                "input_relation",
                "spec_execution",
                "post_update_review",
                "closure_decision",
                "next_interaction",
                "decision_trace",
            ],
        }

    def list_providers(self) -> dict:
        return {"items": [self._provider(provider["provider_id"]) for provider in PROVIDER_DEFINITIONS]}

    def create_session(self, payload: RequirementAnalysisSessionCreate) -> dict:
        orchestrator_id = self._normalize_orchestrator_id(payload.orchestrator_id)
        orchestrator_plugin = self._orchestrator_plugin(orchestrator_id)
        orchestrator = self._orchestrator(orchestrator_id) if orchestrator_plugin.plugin_type == "local_package" else None
        if payload.provider_id not in supported_provider_ids():
            raise ValueError("unsupported provider")
        if payload.provider_id == "deepseek" and not settings.requirement_analysis_deepseek_api_key:
            raise ValueError("DeepSeek provider is not configured")

        now = self._now()
        model = self._resolve_model(payload.provider_id, payload.model)
        template_runtime = self._resolve_template_runtime(payload.template_id)
        spec_tree = self._new_spec_tree(
            payload.template_id,
            orchestrator_id=orchestrator.orchestrator_id if orchestrator is not None else orchestrator_id,
            template_payload=template_runtime,
        )
        active_spec_node_id = self._first_open_spec_node_id(spec_tree)
        working_document = self.working_document_service.initialize(
            topic=payload.topic.strip() or "未命名 Requirement Analysis 课题",
            template_id=payload.template_id,
            template_runtime=template_runtime,
        )
        initial_question = self.summary_artifact_service.suggestion_content_for_node(
            self.spec_tree_service.find_spec_node(spec_tree, active_spec_node_id or "")
        )
        initial_active_node = self.spec_tree_service.find_spec_node(spec_tree, active_spec_node_id or "")
        decision_state = self.decision_state_service.initialize(
            topic=payload.topic.strip() or "未命名 Requirement Analysis 课题",
            initial_question=initial_question,
            active_spec_node=initial_active_node,
        )
        state = {
            "session_phase": "exploration_convergence",
            "decision_state": decision_state,
            "decision_state_document": self.decision_state_service.render_document(
                decision_state=decision_state,
                session_phase="exploration_convergence",
            ),
            "template_runtime": self._template_runtime_for_state(template_runtime),
            "draft_snapshot": None,
            "messages": [
                {
                    "id": "msg-0001",
                    "role": "assistant",
                    "content": (
                        f"我会按{payload.template_id}需求规格模板维护完成度树。"
                        "你可以直接描述、提问、反驳或补充；我会说明本轮更新了哪些规格内容。"
                    ),
                    "created_at": now,
                }
            ],
            "turns": [],
            "confirmed_facts": [],
            "open_questions": [initial_question],
            "document_patch": [],
            "working_document": working_document,
            "questions": [
                {
                    "question_id": "Q-001",
                    "content": initial_question,
                    "status": "open",
                    "target_section": self.spec_tree_service.find_spec_node(spec_tree, active_spec_node_id or "").get("target_section")
                    if self.spec_tree_service.find_spec_node(spec_tree, active_spec_node_id or "")
                    else "未绑定模板章节",
                    "source_turn_id": None,
                    "resolution_fact_ids": [],
                }
            ],
            "facts": [],
            "patches": [],
            "spec_tree": spec_tree,
            "active_spec_node_id": active_spec_node_id,
            "turn_path": [],
            "next_interaction": None,
            "last_quick_options": [],
            "annotations": ["Lab 只生成 document_patch 建议，不直接写入正式需求规格草稿。"],
            "risks": [],
            "provider_logs": [],
        }
        session = RequirementAnalysisSession(
            topic=payload.topic.strip() or "未命名 Requirement Analysis 课题",
            orchestrator_id=orchestrator_id,
            provider_id=payload.provider_id,
            model=model,
            template_id=payload.template_id,
            knowledge_package_id=payload.knowledge_package_id,
            write_policy=payload.write_policy,
            status="created",
            payload=state,
        )
        return self._serialize_session(self.repository.add(session))

    def get_session(self, session_id: str) -> dict | None:
        session = self.repository.get(session_id)
        if session is None:
            return None
        return self._serialize_session(session)

    def add_turn(self, session_id: str, payload: RequirementAnalysisTurnCreate) -> dict | None:
        session = self.repository.get(session_id)
        if session is None:
            return None
        turn_result = self.turn_engine.run_turn(self.load_snapshot(session), payload)
        session = self.apply_turn_execution_result(session, turn_result)
        self.repository.save(session)
        return {"session": self._serialize_session(session), "turn": turn_result.turn}

    def load_snapshot(self, session: RequirementAnalysisSession) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=session.id,
            topic=session.topic,
            orchestrator_id=session.orchestrator_id,
            provider_id=session.provider_id,
            model=session.model,
            template_id=session.template_id,
            knowledge_package_id=session.knowledge_package_id,
            write_policy=session.write_policy,
            status=session.status,
            payload=dict(session.payload or {}),
        )

    def apply_turn_execution_result(
        self,
        session: RequirementAnalysisSession,
        turn_result: TurnExecutionResult,
    ) -> RequirementAnalysisSession:
        state = dict(session.payload or {})
        state.update(turn_result.state_patch)
        state["provider_logs"] = [
            *list(state.get("provider_logs", [])),
            *turn_result.provider_logs,
        ]
        session.payload = state
        session.status = "waiting_user"
        return session

    def _serialize_session(self, session: RequirementAnalysisSession) -> dict:
        state = dict(session.payload or {})
        spec_tree = list(
            state.get("spec_tree")
            or self._new_spec_tree(
                session.template_id,
                orchestrator_id=session.orchestrator_id,
                template_payload=dict(state.get("template_runtime") or {}),
            )
        )
        return {
            "session_id": session.id,
            "topic": session.topic,
            "status": session.status,
            "orchestrator": self._serialize_orchestrator(session.orchestrator_id),
            "provider_id": session.provider_id,
            "model": session.model,
            "template_id": session.template_id,
            "knowledge_package_id": session.knowledge_package_id,
            "write_policy": session.write_policy,
            "session_phase": str(state.get("session_phase") or "exploration_convergence"),
            "decision_state": self.decision_state_service.normalize_state(state.get("decision_state")),
            "decision_state_document": dict(
                state.get("decision_state_document")
                or self.decision_state_service.render_document(
                    decision_state=self.decision_state_service.normalize_state(state.get("decision_state")),
                    session_phase=str(state.get("session_phase") or "exploration_convergence"),
                )
            ),
            "draft_snapshot": state.get("draft_snapshot"),
            "stable_contract": self._stable_contract(),
            "messages": list(state.get("messages", [])),
            "turns": list(state.get("turns", [])),
            "confirmed_facts": list(state.get("confirmed_facts", [])),
            "open_questions": list(state.get("open_questions", [])),
            "decision_state": dict(state.get("decision_state") or {}),
            "decision_state_document": dict(state.get("decision_state_document") or {}),
            "document_patch": list(state.get("document_patch", [])),
            "working_document": dict(
                state.get("working_document")
                or self.working_document_service.initialize(
                    topic=session.topic,
                    template_id=session.template_id,
                    template_runtime=dict(state.get("template_runtime") or {}),
                )
            ),
            "questions": list(state.get("questions", [])),
            "facts": list(state.get("facts", [])),
            "patches": list(state.get("patches", [])),
            "spec_tree": spec_tree,
            "active_spec_node_id": state.get("active_spec_node_id") or self._first_open_spec_node_id(spec_tree),
            "turn_path": list(state.get("turn_path", [])),
            "next_interaction": state.get("next_interaction"),
            "annotations": list(state.get("annotations", [])),
            "risks": list(state.get("risks", [])),
            "provider_logs": list(state.get("provider_logs", [])),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def _normalize_orchestrator_id(self, orchestrator_id: str) -> str:
        registry = get_orchestrator_plugin_registry()
        normalized = orchestrator_id.strip()
        if not normalized:
            return registry.default_plugin().plugin_id
        return registry.require(normalized).plugin_id

    def _orchestrator(self, orchestrator_id: str) -> OrchestratorPackage:
        package_id = get_orchestrator_plugin_registry().local_package_id_for_plugin(orchestrator_id)
        return get_orchestrator_registry().require(package_id)

    def _orchestrator_plugin(self, orchestrator_id: str):
        return get_orchestrator_plugin_registry().require(self._normalize_orchestrator_id(orchestrator_id))

    def _serialize_orchestrator(self, orchestrator_id: str) -> dict:
        plugin = self._orchestrator_plugin(orchestrator_id).to_api()
        if plugin["plugin_type"] != "local_package":
            return plugin
        package = self._orchestrator(orchestrator_id).to_api()
        return {
            **plugin,
            **package,
            "plugin_id": plugin["plugin_id"],
            "plugin_type": plugin["plugin_type"],
            "observability_level": plugin["observability_level"],
            "capabilities": plugin["capabilities"],
            "contract": plugin["contract"],
            "orchestrator_id": plugin["orchestrator_id"],
        }

    def _provider(self, provider_id: str) -> dict:
        for provider in PROVIDER_DEFINITIONS:
            if provider["provider_id"] == provider_id:
                status = "active" if provider_id == "mock" else "not_configured"
                if provider_id == "deepseek" and settings.requirement_analysis_deepseek_api_key:
                    status = "active"
                return {**provider, "status": status}
        raise ValueError("unsupported provider")

    def _resolve_model(self, provider_id: str, model: str) -> str:
        if provider_id == "deepseek" and (not model or model == "mock-requirement-analysis-v1" or model == "provider-default"):
            return settings.requirement_analysis_deepseek_model
        return model or "mock-requirement-analysis-v1"

    def _new_spec_tree(
        self,
        template_id: str = "81433号",
        *,
        orchestrator_id: str,
        template_payload: dict | None = None,
    ) -> list[dict]:
        return self.spec_tree_service.new_spec_tree(
            template_id,
            orchestrator_id=orchestrator_id,
            template_payload=template_payload,
        )

    def _resolve_template_runtime(self, template_id: str) -> dict:
        runtime = self.template_service.resolve_runtime_payload(template_id)
        if runtime is None:
            if template_id in {"81433号", "82259号"}:
                runtime = self._legacy_template_runtime(template_id)
            else:
                raise ValueError("Requirement Analysis template instance not found")
        blocking = [
            item
            for item in list(runtime.get("parse_diagnostics") or [])
            if isinstance(item, dict) and str(item.get("severity") or "") == "error"
        ]
        if blocking:
            raise ValueError("Requirement Analysis template instance structure is invalid")
        return runtime

    def _legacy_template_runtime(self, template_id: str) -> dict:
        payload = self.spec_tree_service.resolve_template_payload(template_id)
        return {
            "template_id": template_id,
            "template_code": self.spec_tree_service.template_code_from_id(template_id),
            "base_template_id": template_id,
            "base_template_name": f"{self.spec_tree_service.template_code_from_id(template_id)}号需求规格模板",
            "name": f"{template_id}需求规格模板",
            "description": "兼容旧入口的内置模板运行时对象。",
            "format": "structured",
            "content": "",
            "sections": list(payload.get("sections") or []),
            "parse_diagnostics": [],
        }

    @staticmethod
    def _template_runtime_for_state(template_runtime: dict) -> dict:
        return {
            key: value
            for key, value in dict(template_runtime).items()
            if key != "content"
        }

    def _first_open_spec_node_id(self, nodes: list[dict]) -> str | None:
        return self.spec_tree_service.first_open_spec_node_id(nodes)

    def _stable_contract(self) -> dict:
        return {
            "formal_document": True,
            "template_object": True,
            "knowledge_binding": True,
            "draft_persistence": True,
            "check_and_freeze": True,
            "p2_to_p3_output": True,
        }

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
