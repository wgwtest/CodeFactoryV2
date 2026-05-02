from __future__ import annotations

from datetime import UTC, datetime

from app.config import settings
from app.db.models.requirements import RequirementAnalysisSession
from app.orchestrators.package_loader import OrchestratorPackage, get_orchestrator_registry
from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.provider_call_service import RequirementAnalysisProviderCallService
from app.requirement_analysis.provider_registry import PROVIDER_DEFINITIONS, supported_provider_ids
from app.requirement_analysis.session_repository import RequirementAnalysisSessionRepository
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.requirement_analysis.summary_artifact_service import RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.turn_audit_service import RequirementAnalysisTurnAuditService
from app.requirement_analysis.turn_engine import RequirementAnalysisTurnEngine
from app.requirement_analysis.turn_output_service import RequirementAnalysisTurnOutputService


class RequirementAnalysisSessionService:
    def __init__(self, session) -> None:
        self.session = session
        self.repository = RequirementAnalysisSessionRepository(session)
        self.input_normalizer = InputNormalizer()
        self.input_relation_classifier = InputRelationClassifier(normalizer=self.input_normalizer)
        self.process_artifact_service = ProcessArtifactService()
        self.provider_call_service = RequirementAnalysisProviderCallService(self)
        self.spec_tree_service = RequirementSpecTreeService(session)
        self.summary_artifact_service = RequirementAnalysisSummaryArtifactService(self)
        self.turn_audit_service = RequirementAnalysisTurnAuditService(self)
        self.turn_output_service = RequirementAnalysisTurnOutputService(self)
        self.turn_engine = RequirementAnalysisTurnEngine(self)

    def list_orchestrators(self) -> dict:
        registry = get_orchestrator_registry()
        return {
            "items": [package.to_api() for package in registry.list_packages()],
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
        orchestrator = self._orchestrator(orchestrator_id)
        if payload.provider_id not in supported_provider_ids():
            raise ValueError("unsupported provider")
        if payload.provider_id == "deepseek" and not settings.requirement_analysis_deepseek_api_key:
            raise ValueError("DeepSeek provider is not configured")

        now = self._now()
        model = self._resolve_model(payload.provider_id, payload.model)
        spec_tree = self._new_spec_tree(payload.template_id, orchestrator_id=orchestrator.orchestrator_id)
        active_spec_node_id = self._first_open_spec_node_id(spec_tree)
        state = {
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
            "open_questions": [self._suggestion_content_for_node(self._find_spec_node(spec_tree, active_spec_node_id or ""))],
            "document_patch": [],
            "questions": [
                {
                    "question_id": "Q-001",
                    "content": self._suggestion_content_for_node(self._find_spec_node(spec_tree, active_spec_node_id or "")),
                    "status": "open",
                    "target_section": self._find_spec_node(spec_tree, active_spec_node_id or "").get("target_section")
                    if self._find_spec_node(spec_tree, active_spec_node_id or "")
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
            orchestrator_id=orchestrator.orchestrator_id,
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
        turn = self.turn_engine.add_turn(session, payload)
        self.repository.save(session)
        return {"session": self._serialize_session(session), "turn": turn}

    def _serialize_session(self, session: RequirementAnalysisSession) -> dict:
        state = dict(session.payload or {})
        spec_tree = list(
            state.get("spec_tree")
            or self._new_spec_tree(session.template_id, orchestrator_id=session.orchestrator_id)
        )
        return {
            "session_id": session.id,
            "topic": session.topic,
            "status": session.status,
            "orchestrator": self._orchestrator(session.orchestrator_id).to_api(),
            "provider_id": session.provider_id,
            "model": session.model,
            "template_id": session.template_id,
            "knowledge_package_id": session.knowledge_package_id,
            "write_policy": session.write_policy,
            "stable_contract": self._stable_contract(),
            "messages": list(state.get("messages", [])),
            "turns": list(state.get("turns", [])),
            "confirmed_facts": list(state.get("confirmed_facts", [])),
            "open_questions": list(state.get("open_questions", [])),
            "document_patch": list(state.get("document_patch", [])),
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
        normalized = orchestrator_id.strip()
        return normalized

    def _orchestrator(self, orchestrator_id: str) -> OrchestratorPackage:
        return get_orchestrator_registry().require(self._normalize_orchestrator_id(orchestrator_id))

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

    def _run_orchestrator(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
    ) -> dict:
        return self.provider_call_service.run_orchestrator(
            orchestrator=orchestrator,
            session=session,
            user_input=user_input,
            normalized=normalized,
        )

    def _run_provider(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        return self.provider_call_service.run_provider(
            session,
            user_input,
            normalized,
            orchestrator=orchestrator,
        )

    def _deepseek_client_class(self):
        return self.provider_call_service._deepseek_client_class()

    def _normalize_input(self, user_input: str, *, quick_options: list[dict] | None = None) -> dict:
        return self.input_normalizer.normalize_input(user_input, quick_options=quick_options)

    def _normalize_quick_options(self, value: object) -> list[dict]:
        return self.input_normalizer.normalize_quick_options(value)

    def _find_quick_option(self, options: list[dict], key: str) -> dict | None:
        return self.input_normalizer.find_quick_option(options, key)

    def _mock_model_output(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        return self.provider_call_service.mock_model_output(
            session,
            user_input,
            normalized,
            orchestrator=orchestrator,
        )

    def _strong_rule_model_output(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        return self.provider_call_service.run_local_runner(session, user_input, normalized, orchestrator=orchestrator)

    def _build_structured_summary_update(
        self,
        *,
        model_output: dict,
        normalized: dict,
        questions: list[dict],
        facts: list[dict],
        patches: list[dict],
        target_spec_node: dict,
        turn_id: str,
        session: RequirementAnalysisSession,
    ) -> dict:
        return self.summary_artifact_service.build_structured_summary_update(
            model_output=model_output,
            normalized=normalized,
            questions=questions,
            facts=facts,
            patches=patches,
            target_spec_node=target_spec_node,
            turn_id=turn_id,
            session=session,
        )

    def _new_spec_tree(self, template_id: str = "81433号", *, orchestrator_id: str) -> list[dict]:
        return self.spec_tree_service.new_spec_tree(template_id, orchestrator_id=orchestrator_id)

    def _resolve_template_payload(self, template_id: str) -> dict:
        return self.spec_tree_service.resolve_template_payload(template_id)

    def _template_code_from_id(self, template_id: str) -> str:
        return self.spec_tree_service.template_code_from_id(template_id)

    def _active_spec_node_context(self, spec_tree: list[dict], node_id: str | None) -> dict:
        return self.spec_tree_service.active_spec_node_context(spec_tree, node_id)

    def _spec_node_path(self, nodes: list[dict], node_id: str, current: list[str] | None = None) -> list[str]:
        return self.spec_tree_service.spec_node_path(nodes, node_id, current)

    def _decision_trace_seed(
        self,
        *,
        projection_spec_node: dict,
        normalized: dict,
        next_open_before_update: str | None,
        orchestrator: OrchestratorPackage,
    ) -> list[str]:
        return self.turn_audit_service.decision_trace_seed(
            projection_spec_node=projection_spec_node,
            normalized=normalized,
            next_open_before_update=next_open_before_update,
            orchestrator=orchestrator,
        )

    def _previous_interaction(self, value: object, *, last_quick_options: list[dict]) -> dict:
        return self.turn_audit_service.previous_interaction(value, last_quick_options=last_quick_options)

    def _state_changes(
        self,
        *,
        previous_questions: list[dict],
        updated_questions: list[dict],
        closed_spec_node_ids: list[str],
        next_active_spec_node_id: str | None,
    ) -> dict:
        return self.turn_audit_service.state_changes(
            previous_questions=previous_questions,
            updated_questions=updated_questions,
            closed_spec_node_ids=closed_spec_node_ids,
            next_active_spec_node_id=next_active_spec_node_id,
        )

    def _spec_execution(self, *, model_output: dict, affected_spec_nodes: list[dict], state_changes: dict) -> dict:
        return self.turn_audit_service.spec_execution(
            model_output=model_output,
            affected_spec_nodes=affected_spec_nodes,
            state_changes=state_changes,
        )

    def _post_update_review(
        self,
        *,
        previous_interaction: dict,
        next_spec_node: dict,
        closed_spec_node_ids: list[str],
    ) -> dict:
        return self.turn_audit_service.post_update_review(
            previous_interaction=previous_interaction,
            next_spec_node=next_spec_node,
            closed_spec_node_ids=closed_spec_node_ids,
        )

    def _closure_decision(
        self,
        *,
        spec_execution: dict,
        post_update_review: dict,
        closed_spec_node_ids: list[str],
    ) -> dict:
        return self.turn_audit_service.closure_decision(
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closed_spec_node_ids=closed_spec_node_ids,
        )

    def _next_interaction(self, *, next_spec_node: dict, model_output: dict, turn_index: int) -> dict:
        return self.turn_audit_service.next_interaction(
            next_spec_node=next_spec_node,
            model_output=model_output,
            turn_index=turn_index,
        )

    def _align_model_output_to_next_node(
        self,
        *,
        model_output: dict,
        next_spec_node: dict,
        current_spec_node: dict,
        session: RequirementAnalysisSession,
    ) -> dict:
        return self.turn_output_service.align_model_output_to_next_node(
            model_output=model_output,
            next_spec_node=next_spec_node,
            current_spec_node=current_spec_node,
            session=session,
        )

    def _ensure_patch_target_section(self, *, model_output: dict, current_spec_node: dict, session: RequirementAnalysisSession) -> dict:
        return self.turn_output_service.ensure_patch_target_section(
            model_output=model_output,
            current_spec_node=current_spec_node,
            session=session,
        )

    def _fact_for_node(self, orchestrator_id: str, node: dict | None, semantic: str) -> str:
        return self.process_artifact_service.fact_for_node(orchestrator_id, node, semantic)

    def _patch_for_node(self, orchestrator_id: str, node: dict | None, semantic: str) -> str:
        return self.process_artifact_service.patch_for_node(orchestrator_id, node, semantic)

    def _quick_options_for_node(self, node: dict | None, *, orchestrator_id: str) -> list[dict]:
        return self.process_artifact_service.quick_options_for_node(orchestrator_id, node)

    def _update_spec_tree(self, *, spec_tree: list[dict], active_node_id: str, answer_summary: str, turn_id: str) -> dict:
        return self.spec_tree_service.update_spec_tree(
            spec_tree=spec_tree,
            active_node_id=active_node_id,
            answer_summary=answer_summary,
            turn_id=turn_id,
        )

    def _find_spec_node(self, nodes: list[dict], node_id: str) -> dict | None:
        return self.spec_tree_service.find_spec_node(nodes, node_id)

    def _first_open_spec_node_id(self, nodes: list[dict]) -> str | None:
        return self.spec_tree_service.first_open_spec_node_id(nodes)

    def _refresh_parent_statuses(self, nodes: list[dict]) -> None:
        self.spec_tree_service.refresh_parent_statuses(nodes)

    def _resolve_answering_question(
        self,
        questions: list[dict],
        *,
        target_section: str | None,
        target_spec_node: dict,
        turn_id: str,
    ) -> dict | None:
        return self.summary_artifact_service.resolve_answering_question(
            questions,
            target_section=target_section,
            target_spec_node=target_spec_node,
            turn_id=turn_id,
        )

    def _infer_target_section(self, content: str) -> str:
        return self.summary_artifact_service.infer_target_section(content)

    def _infer_target_section_from_model_output(self, model_output: dict, open_question: str) -> str:
        return self.summary_artifact_service.infer_target_section_from_model_output(model_output, open_question)

    def _select_projection_spec_node_id(self, spec_tree: list[dict], model_output: dict, fallback_node_id: str) -> str:
        return self.turn_output_service.select_projection_spec_node_id(spec_tree, model_output, fallback_node_id)

    def _find_spec_node_by_target_section(self, nodes: list[dict], target_section: str) -> dict | None:
        return self.spec_tree_service.find_spec_node_by_target_section(nodes, target_section)

    def _ensure_next_open_question(
        self,
        *,
        questions: list[dict],
        next_question: str,
        next_spec_node: dict,
        turn_id: str,
    ) -> list[dict]:
        return self.turn_output_service.ensure_next_open_question(
            questions=questions,
            next_question=next_question,
            next_spec_node=next_spec_node,
            turn_id=turn_id,
        )

    def _is_same_question_content(self, candidate: str, existing: str) -> bool:
        return self.summary_artifact_service.is_same_question_content(candidate, existing)

    def _service_steps(self) -> list[dict]:
        return [
            {"step": 1, "title": "接收用户输入", "status": "completed"},
            {"step": 2, "title": "读取会话状态", "status": "completed"},
            {"step": 3, "title": "读取模板与知识包", "status": "completed"},
            {"step": 4, "title": "组装组织器上下文", "status": "completed"},
            {"step": 5, "title": "调用组织器 / Provider", "status": "completed"},
            {"step": 6, "title": "解析结构化输出", "status": "completed"},
            {"step": 7, "title": "校验并落状态", "status": "completed"},
        ]

    def _stable_contract(self) -> dict:
        return {
            "formal_document": True,
            "template_object": True,
            "knowledge_binding": True,
            "draft_persistence": True,
            "check_and_freeze": True,
            "p2_to_p3_output": True,
        }

    def _append_unique(self, current: list[str], additions: list[str]) -> list[str]:
        result = list(current)
        for item in additions:
            if item not in result:
                result.append(item)
        return result

    def _normalize_turn_model_output(self, model_output: dict, *, session: RequirementAnalysisSession) -> dict:
        return self.turn_output_service.normalize_turn_model_output(model_output, session=session)

    def _normalize_organizer_interpretation(self, value: object) -> dict:
        return self.turn_output_service.normalize_organizer_interpretation(value)

    def _classify_input_relation(
        self,
        previous_interaction: object,
        normalized: dict,
        *,
        last_quick_options: list[dict],
    ) -> dict:
        return self.input_relation_classifier.classify(
            previous_interaction,
            normalized,
            last_quick_options=last_quick_options,
        )

    def _affected_spec_nodes(self, *, spec_tree: list[dict], node_ids: list[str]) -> list[dict]:
        return self.turn_output_service.affected_spec_nodes(spec_tree=spec_tree, node_ids=node_ids)

    def _decision_trace(
        self,
        *,
        previous_interaction: dict,
        input_relation: dict,
        spec_execution: dict,
        post_update_review: dict,
        closure_decision: dict,
        next_interaction: dict,
        seed: list[str],
    ) -> list[str]:
        return self.turn_audit_service.decision_trace(
            previous_interaction=previous_interaction,
            input_relation=input_relation,
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closure_decision=closure_decision,
            next_interaction=next_interaction,
            seed=seed,
        )

    def _suggestion_content_for_node(self, node: dict | None) -> str:
        if node is None:
            return "请直接描述你希望形成的需求规格说明内容。"
        return f"可以补齐：{node.get('question') or node.get('title')}"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
