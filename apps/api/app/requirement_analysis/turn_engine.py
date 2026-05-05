from __future__ import annotations

from datetime import UTC, datetime

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.next_interaction_service import NextInteractionService
from app.requirement_analysis.provider_call_log_service import ProviderCallLogService
from app.requirement_analysis.provider_call_service import RequirementAnalysisProviderCallService
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.spec_projection_service import SpecProjectionService
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.requirement_analysis.summary_artifact_service import RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.turn_audit_service import RequirementAnalysisTurnAuditService
from app.requirement_analysis.turn_context_builder import TurnContextBuilder
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.requirement_analysis.turn_output_service import RequirementAnalysisTurnOutputService
from app.requirement_analysis.turn_stage_executor import TurnStageExecutor
from app.requirement_analysis.turn_strategy_service import TurnStrategyService
from app.requirement_analysis.working_document_review_service import WorkingDocumentReviewService
from app.requirement_analysis.working_document_service import WorkingDocumentService


class RequirementAnalysisTurnEngine:
    def __init__(
        self,
        *,
        turn_context_builder: TurnContextBuilder,
        provider_call_service: RequirementAnalysisProviderCallService,
        provider_call_log_service: ProviderCallLogService,
        spec_tree_service: RequirementSpecTreeService,
        spec_projection_service: SpecProjectionService,
        summary_artifact_service: RequirementAnalysisSummaryArtifactService,
        turn_audit_service: RequirementAnalysisTurnAuditService,
        turn_output_service: RequirementAnalysisTurnOutputService,
        next_interaction_service: NextInteractionService,
        turn_strategy_service: TurnStrategyService,
        turn_stage_executor: TurnStageExecutor,
        working_document_service: WorkingDocumentService,
        working_document_review_service: WorkingDocumentReviewService,
    ) -> None:
        self.turn_context_builder = turn_context_builder
        self.provider_call_service = provider_call_service
        self.provider_call_log_service = provider_call_log_service
        self.spec_tree_service = spec_tree_service
        self.spec_projection_service = spec_projection_service
        self.summary_artifact_service = summary_artifact_service
        self.turn_audit_service = turn_audit_service
        self.turn_output_service = turn_output_service
        self.next_interaction_service = next_interaction_service
        self.turn_strategy_service = turn_strategy_service
        self.turn_stage_executor = turn_stage_executor
        self.working_document_service = working_document_service
        self.working_document_review_service = working_document_review_service

    def run_turn(self, session: SessionSnapshot, payload: RequirementAnalysisTurnCreate) -> TurnExecutionResult:
        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        turn_id = f"turn-{len(turns) + 1:04d}"
        user_input = payload.user_input.strip()
        now = self._now()
        orchestrator = self._orchestrator(session.orchestrator_id)
        context = self.turn_context_builder.build(session=session, turn_id=turn_id, user_input=user_input)

        strategy = self.turn_strategy_service.load(orchestrator=orchestrator, context=context)
        stage_results = [
            self.turn_stage_executor.run(
                stage=stage,
                orchestrator=orchestrator,
                session=session,
                context=context,
            )
            for stage in strategy.stages
        ]
        model_output = self._adopt_stage_model_output(strategy.adoption_policy, stage_results)
        model_output = self.turn_output_service.normalize_turn_model_output(model_output, session=session)
        provider_normalized_output = self.provider_call_log_service.provider_normalized_output(model_output)

        projection = self.spec_projection_service.project(
            spec_tree=context.spec_tree,
            model_output=model_output,
            fallback_node_id=context.active_spec_node_id,
        )
        model_output = self.turn_output_service.ensure_patch_target_section(
            model_output=model_output,
            current_spec_node=projection.projection_spec_node,
            session=session,
        )

        next_open_before_update = self.spec_tree_service.first_open_spec_node_id(context.spec_tree)
        decision_trace_seed = self.turn_audit_service.decision_trace_seed(
            projection_spec_node=projection.projection_spec_node,
            normalized=context.normalized_input,
            next_open_before_update=next_open_before_update,
            orchestrator=orchestrator,
        )
        artifact_update = self.summary_artifact_service.build_structured_summary_update(
            model_output=model_output,
            normalized=context.normalized_input,
            questions=context.questions,
            facts=context.facts,
            patches=context.patches,
            target_spec_node=projection.projection_spec_node,
            turn_id=turn_id,
            session=session,
        )
        structured_update = artifact_update.to_dict()
        working_document = dict(
            context.working_document
            or self.working_document_service.initialize(topic=session.topic, template_id=session.template_id)
        )
        working_document_update_result = self.working_document_service.apply_patches(
            working_document=working_document,
            document_patch=model_output["document_patch"],
            patch_proposals=structured_update["patches"],
            projection_spec_node=projection.projection_spec_node,
            turn_id=turn_id,
            user_input_summary=context.normalized_input.get("semantic") or user_input,
        )
        working_document_update = working_document_update_result.to_dict()
        review_result = self.working_document_review_service.review(
            working_document=working_document,
            review_target_paths=[
                str(block.get("anchor_path") or "")
                for block in working_document_update_result.blocks
                if str(block.get("anchor_path") or "").strip()
            ]
            or [str(projection.projection_spec_node.get("target_section") or "")],
            current_spec_node=projection.projection_spec_node,
        )
        target_review = review_result["target_review"]
        can_close = target_review["status"] in {"acceptable", "closed"}
        spec_update = self.spec_tree_service.update_spec_tree(
            spec_tree=context.spec_tree,
            active_node_id=projection.projection_spec_node_id,
            answer_summary=structured_update["answer_summary"],
            turn_id=turn_id,
            can_close=can_close,
        )
        spec_update_payload = spec_update.to_dict()
        next_spec_node = spec_update.next_spec_node
        global_review = self.working_document_review_service.build_global_review(
            next_spec_node=next_spec_node,
            target_review=target_review,
        )
        continue_same_topic = global_review["status"] == "continue_same_topic"
        model_output = self.next_interaction_service.align_model_output_to_next_node(
            model_output=model_output,
            next_spec_node=next_spec_node,
            current_spec_node=projection.projection_spec_node,
            session=session,
            continue_same_topic=continue_same_topic,
            target_review=target_review,
            global_review=global_review,
        )
        structured_update["questions"] = self.next_interaction_service.ensure_next_open_question(
            questions=structured_update["questions"],
            next_question=model_output["next_question"],
            next_spec_node=projection.projection_spec_node if continue_same_topic else next_spec_node,
            turn_id=turn_id,
        )
        state_changes = self.turn_audit_service.state_changes(
            previous_questions=context.questions,
            updated_questions=structured_update["questions"],
            closed_spec_node_ids=spec_update.closed_node_ids,
            next_active_spec_node_id=spec_update.active_spec_node_id,
        )
        spec_execution = self.turn_audit_service.spec_execution(
            model_output=model_output,
            affected_spec_nodes=projection.affected_spec_nodes,
            state_changes=state_changes,
            working_document_update=working_document_update,
        )
        post_update_review = self.turn_audit_service.post_update_review(
            target_review=target_review,
            global_review=global_review,
        )
        closure_decision = self.turn_audit_service.closure_decision(
            post_update_review=post_update_review,
            closed_spec_node_ids=spec_update.closed_node_ids,
        )
        next_interaction = self.next_interaction_service.build(
            next_spec_node=projection.projection_spec_node if continue_same_topic else next_spec_node,
            model_output=model_output,
            turn_index=context.turn_index,
        )
        decision_trace = self.turn_audit_service.decision_trace(
            previous_interaction=context.previous_interaction,
            input_relation=context.input_relation,
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closure_decision=closure_decision,
            next_interaction=next_interaction,
            seed=decision_trace_seed,
        )

        turn = {
            "turn_id": turn_id,
            "session_id": session.session_id,
            "user_input": user_input,
            "previous_interaction": context.previous_interaction,
            "normalized_input": context.normalized_input,
            "input_relation": context.input_relation,
            "spec_execution": spec_execution,
            "post_update_review": post_update_review,
            "closure_decision": closure_decision,
            "next_interaction": next_interaction,
            "decision_trace": decision_trace,
            "confidence": model_output["confidence"],
            "service_steps": self._service_steps(),
            "raw_model_response": model_output["raw_model_response"],
            "created_at": now,
        }

        updated_turns = [*turns, turn]
        messages = [
            *list(state.get("messages", [])),
            {"id": f"msg-{len(updated_turns) * 2:04d}", "role": "user", "content": user_input, "turn_id": turn_id, "created_at": now},
            {
                "id": f"msg-{len(updated_turns) * 2 + 1:04d}",
                "role": "assistant",
                "content": spec_execution["assistant_message"],
                "turn_id": turn_id,
                "created_at": now,
            },
        ]
        confirmed_facts = self.summary_artifact_service.append_unique(
            list(state.get("confirmed_facts", [])),
            model_output["confirmed_facts_delta"],
        )
        open_questions = self.summary_artifact_service.append_unique(
            list(state.get("open_questions", [])),
            model_output["open_questions_delta"],
        )
        turn_path = [
            *list(state.get("turn_path", [])),
            {
                "turn_id": turn_id,
                "node_id": projection.projection_spec_node_id,
                "question_id": structured_update["source_question_id"],
                "previous_interaction_id": context.previous_interaction.get("interaction_id"),
                "input_relation": context.input_relation["relation"],
                "affected_node_ids": [node["node_id"] for node in projection.affected_spec_nodes if node.get("node_id")],
                "next_interaction_id": next_interaction.get("interaction_id"),
                "closed_node_ids": spec_update.closed_node_ids,
                "answer_summary": structured_update["answer_summary"],
            },
        ]
        annotations = self.summary_artifact_service.append_unique(
            list(state.get("annotations", [])),
            model_output["annotations"],
        )
        risks = self.summary_artifact_service.append_unique(
            list(state.get("risks", [])),
            model_output["risks"],
        )
        provider_logs = [
            self.provider_call_log_service.build(
                turn_id=turn_id,
                session=session,
                orchestrator=orchestrator,
                user_input=user_input,
                normalized=context.normalized_input,
                model_output=model_output,
                provider_normalized_output=provider_normalized_output,
                service_output={
                    **self.provider_call_log_service.service_output(model_output),
                    "working_document_update": working_document_update,
                    "post_update_review": post_update_review,
                },
                prompt_bundle_overrides={
                    "working_document_json": str(working_document),
                    "working_document_excerpt": working_document_update.get("after_excerpt", ""),
                    "review_target_paths": target_review.get("review_target", []),
                    "recent_revision_fragments": working_document_update.get("applied_fragment_ids", []),
                    "review_goal": (
                        projection.projection_spec_node.get("question")
                        or projection.projection_spec_node.get("target_section")
                        or ""
                    ),
                },
                provider_response_overrides={
                    "target_review_json": target_review,
                    "global_review_json": global_review,
                },
                created_at=now,
                call_index=len(updated_turns),
            ),
        ]
        return TurnExecutionResult(
            turn=turn,
            state_patch={
                "turns": updated_turns,
                "messages": messages,
                "confirmed_facts": confirmed_facts,
                "open_questions": open_questions,
                "document_patch": model_output["document_patch"],
                "working_document": working_document,
                "questions": structured_update["questions"],
                "facts": structured_update["facts"],
                "patches": structured_update["patches"],
                "spec_tree": spec_update_payload["spec_tree"],
                "active_spec_node_id": spec_update_payload["active_spec_node_id"],
                "turn_path": turn_path,
                "next_interaction": next_interaction,
                "last_quick_options": next_interaction.get("options", []),
                "annotations": annotations,
                "risks": risks,
            },
            provider_logs=provider_logs,
        )

    @staticmethod
    def _service_steps() -> list[dict]:
        return [
            {"step": 1, "title": "接收用户输入", "status": "completed"},
            {"step": 2, "title": "读取会话状态", "status": "completed"},
            {"step": 3, "title": "读取模板与知识包", "status": "completed"},
            {"step": 4, "title": "组装组织器上下文", "status": "completed"},
            {"step": 5, "title": "调用组织器 / Provider", "status": "completed"},
            {"step": 6, "title": "解析结构化输出", "status": "completed"},
            {"step": 7, "title": "校验并落状态", "status": "completed"},
        ]

    @staticmethod
    def _orchestrator(orchestrator_id: str) -> OrchestratorPackage:
        from app.orchestrators.package_loader import get_orchestrator_registry

        return get_orchestrator_registry().require(orchestrator_id)

    @staticmethod
    def _adopt_stage_model_output(adoption_policy: str, stage_results: list) -> dict:
        if not stage_results:
            raise ValueError("turn strategy produced no stage results")
        if adoption_policy == "adopt_last_completed_stage":
            for result in reversed(stage_results):
                if result.stage_type != "server_review":
                    return result.model_output
            return stage_results[-1].model_output
        return stage_results[0].model_output

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
