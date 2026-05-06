from __future__ import annotations

from datetime import UTC, datetime

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.next_interaction_service import NextInteractionService
from app.requirement_analysis.provider_call_log_service import ProviderCallLogService
from app.requirement_analysis.provider_call_service import RequirementAnalysisProviderCallService
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.spec_projection_service import SpecProjectionService
from app.requirement_analysis.stage_runtime_context_builder import StageRuntimeContextBuilder
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.requirement_analysis.summary_artifact_service import RequirementAnalysisSummaryArtifactService
from app.requirement_analysis.turn_audit_service import RequirementAnalysisTurnAuditService
from app.requirement_analysis.turn_context_builder import TurnContextBuilder
from app.requirement_analysis.turn_decision_service import TurnDecisionService
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.requirement_analysis.turn_output_service import RequirementAnalysisTurnOutputService
from app.requirement_analysis.turn_stage_executor import TurnStageExecutor, TurnStageResult
from app.requirement_analysis.turn_stage_planner import TurnStagePlan, TurnStagePlanner
from app.requirement_analysis.turn_stage_reducer import TurnStageReducer
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
        turn_stage_planner: TurnStagePlanner,
        turn_stage_executor: TurnStageExecutor,
        turn_stage_reducer: TurnStageReducer,
        working_document_service: WorkingDocumentService,
        working_document_review_service: WorkingDocumentReviewService,
        turn_decision_service: TurnDecisionService,
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
        self.turn_stage_planner = turn_stage_planner
        self.turn_stage_executor = turn_stage_executor
        self.turn_stage_reducer = turn_stage_reducer
        self.working_document_service = working_document_service
        self.working_document_review_service = working_document_review_service
        self.turn_decision_service = turn_decision_service
        self.stage_runtime_context_builder = StageRuntimeContextBuilder(
            working_document_service=working_document_service,
        )

    def run_turn(self, session: SessionSnapshot, payload: RequirementAnalysisTurnCreate) -> TurnExecutionResult:
        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        turn_id = f"turn-{len(turns) + 1:04d}"
        user_input = payload.user_input.strip()
        now = self._now()
        orchestrator = self._orchestrator(session.orchestrator_id)
        context = self.turn_context_builder.build(session=session, turn_id=turn_id, user_input=user_input)

        strategy = self.turn_strategy_service.load(orchestrator=orchestrator, context=context)
        stage_plan = self.turn_stage_planner.build_plan(strategy=strategy, context=context, orchestrator=orchestrator)
        stage_results: list[TurnStageResult] = []

        working_document = dict(
            context.working_document
            or self.working_document_service.initialize(topic=session.topic, template_id=session.template_id)
        )
        intent_output = {
            "intent_understanding_result": {},
            "target_document_structure": {},
            "stage_task_definition": {},
            "stage_quality_constraints": {},
            "confidence": "medium",
        }
        for stage in self._stages_by_kind(stage_plan=stage_plan, stage_kind="intent"):
            stage_input = self.stage_runtime_context_builder.build(
                session=session,
                context=context,
                stage=stage,
                working_document=working_document,
            ).to_prompt_context()
            stage_results.append(
                self.turn_stage_executor.run(
                    stage=stage,
                    orchestrator=orchestrator,
                    session=session,
                    context=context,
                    stage_input=stage_input,
                )
            )
        intent_output = self.turn_stage_reducer.reduce_intent_stage(plan=stage_plan, stage_results=stage_results)
        intent_understanding_result = dict(intent_output.get("intent_understanding_result") or {})
        target_document_structure = dict(intent_output.get("target_document_structure") or {})
        stage_task_definition = dict(intent_output.get("stage_task_definition") or {})
        stage_quality_constraints = dict(intent_output.get("stage_quality_constraints") or {})

        for stage in self._stages_by_kind(stage_plan=stage_plan, stage_kind="write"):
            stage_input = self.stage_runtime_context_builder.build(
                session=session,
                context=context,
                stage=stage,
                intent_understanding_result=intent_understanding_result,
                target_document_structure=target_document_structure,
                stage_task_definition=stage_task_definition,
                stage_quality_constraints=stage_quality_constraints,
                working_document=working_document,
            ).to_prompt_context()
            stage_results.append(
                self.turn_stage_executor.run(
                    stage=stage,
                    orchestrator=orchestrator,
                    session=session,
                    context=context,
                    stage_input=stage_input,
                )
            )
        model_output = self.turn_stage_reducer.reduce_write_stage(plan=stage_plan, stage_results=stage_results)
        model_output = self.turn_output_service.normalize_turn_model_output(model_output, session=session)
        model_output = self.turn_output_service.validate_anchor_plan_refs(
            model_output=model_output,
            chapter_configuration_context=self.stage_runtime_context_builder.build(
                session=session,
                context=context,
                stage={"stage_id": "write", "stage_kind": "write", "prompt_id": "write"},
                working_document=working_document,
            ).chapter_configuration_context,
        )
        projection = self.spec_projection_service.project(
            spec_tree=context.spec_tree,
            model_output=model_output,
            fallback_node_id=context.active_spec_node_id,
        )
        write_provider_normalized_output = self.provider_call_log_service.provider_normalized_output(model_output)

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
        working_document_update_result = self.working_document_service.apply_patches(
            working_document=working_document,
            document_patch=model_output["document_patch"],
            patch_proposals=structured_update["patches"],
            projection_spec_node=projection.projection_spec_node,
            turn_id=turn_id,
            user_input_summary=context.normalized_input.get("semantic") or user_input,
            target_anchor_plan=model_output["target_anchor_plan"],
        )
        working_document_update = working_document_update_result.to_dict()
        server_review_evidence = self.working_document_review_service.review(
            working_document=working_document,
            review_target_paths=[
                str(block.get("anchor_path") or "")
                for block in working_document_update_result.blocks
                if str(block.get("anchor_path") or "").strip()
            ]
            or [str(projection.projection_spec_node.get("target_section") or "")],
            current_spec_node=projection.projection_spec_node,
        )
        target_review = dict(server_review_evidence["target_review"])
        global_review = dict(server_review_evidence["global_review"])
        review_stage_input = self._review_stage_input(
            working_document=working_document,
            working_document_update=working_document_update,
            target_review=target_review,
            global_review=global_review,
            review_target_paths=target_review.get("review_target", []),
        )
        for stage in self._stages_by_kind(stage_plan=stage_plan, stage_kind="review"):
            stage_input = self.stage_runtime_context_builder.build(
                session=session,
                context=context,
                stage=stage,
                intent_understanding_result=intent_understanding_result,
                target_document_structure=target_document_structure,
                stage_task_definition=stage_task_definition,
                stage_quality_constraints=stage_quality_constraints,
                template_shape_assessment=model_output["template_shape_assessment"],
                target_anchor_plan=model_output["target_anchor_plan"],
                working_document=working_document,
                working_document_after_apply=review_stage_input["working_document_after_apply"],
                working_document_update=working_document_update,
            ).to_prompt_context()
            stage_input.update(review_stage_input)
            stage_results.append(
                self.turn_stage_executor.run(
                    stage=stage,
                    orchestrator=orchestrator,
                    session=session,
                    context=context,
                    stage_input=review_stage_input,
                )
            )
        review_reduction = self.turn_stage_reducer.reduce_review_stage(
            plan=stage_plan,
            stage_results=stage_results,
            target_review=target_review,
            global_review=global_review,
        )
        target_review = dict(review_reduction["target_review"])
        global_review = dict(review_reduction["global_review"])
        review_after_apply_result = {
            **dict(review_reduction.get("review_stage_output") or {}),
            "target_review": target_review,
            "global_review": global_review,
        }
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
        model_global_review = dict(global_review)
        global_review = self._resolved_global_review(
            model_global_review=model_global_review,
            next_spec_node=next_spec_node,
            target_review=target_review,
        )
        review_after_apply_result = {
            **review_after_apply_result,
            "target_review": target_review,
            "global_review": global_review,
            "model_global_review": model_global_review,
        }
        continue_same_topic = global_review["status"] == "continue_same_topic"
        focus_spec_node = projection.projection_spec_node if continue_same_topic else next_spec_node

        next_planning_output = {
            "next_interaction_plan": {},
            "planning_trace": [],
            "confidence": "medium",
        }
        for stage in self._stages_by_kind(stage_plan=stage_plan, stage_kind="next_interaction"):
            stage_input = self.stage_runtime_context_builder.build(
                session=session,
                context=context,
                stage=stage,
                intent_understanding_result=intent_understanding_result,
                target_document_structure=target_document_structure,
                stage_task_definition=stage_task_definition,
                stage_quality_constraints=stage_quality_constraints,
                template_shape_assessment=model_output["template_shape_assessment"],
                target_anchor_plan=model_output["target_anchor_plan"],
                working_document=working_document,
                working_document_after_apply=review_stage_input["working_document_after_apply"],
                working_document_update=working_document_update,
                review_after_apply_result=review_after_apply_result,
            ).to_prompt_context()
            stage_input.update(
                {
                    "review_after_apply_result": review_after_apply_result,
                    "target_review": target_review,
                    "global_review": global_review,
                    "next_spec_node": next_spec_node,
                    "current_spec_node": projection.projection_spec_node,
                    "focus_spec_node": focus_spec_node,
                    "spec_tree": spec_update_payload["spec_tree"],
                }
            )
            stage_results.append(
                self.turn_stage_executor.run(
                    stage=stage,
                    orchestrator=orchestrator,
                    session=session,
                    context=context,
                    stage_input=stage_input,
                )
            )
        next_planning_output = self.turn_stage_reducer.reduce_next_interaction_stage(
            plan=stage_plan,
            stage_results=stage_results,
        )
        next_interaction_plan = dict(next_planning_output.get("next_interaction_plan") or {})
        next_interaction = self._next_interaction_from_plan(
            plan=next_interaction_plan,
            focus_spec_node=focus_spec_node,
            turn_index=context.turn_index,
        )
        model_output = self._apply_next_interaction_plan_to_model_output(
            model_output=model_output,
            next_interaction_plan=next_interaction_plan,
            next_interaction=next_interaction,
        )
        structured_update["questions"] = self.next_interaction_service.ensure_next_open_question(
            questions=structured_update["questions"],
            next_question=model_output["next_question"],
            next_spec_node=focus_spec_node,
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
        preliminary_closure_decision = self.turn_decision_service.build_closure_decision(
            post_update_review=post_update_review,
        )
        preliminary_trace = self.turn_audit_service.decision_trace(
            previous_interaction=context.previous_interaction,
            input_relation=context.input_relation,
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closure_decision=preliminary_closure_decision,
            next_interaction=next_interaction,
            seed=decision_trace_seed,
        )
        provider_logs = self._build_provider_logs(
            stage_plan=stage_plan,
            turn_id=turn_id,
            session=session,
            orchestrator=orchestrator,
            user_input=user_input,
            normalized=context.normalized_input,
            stage_results=stage_results,
            final_write_model_output=model_output,
            final_write_provider_normalized_output=write_provider_normalized_output,
            working_document=working_document,
            working_document_update=working_document_update,
            target_review=target_review,
            global_review=global_review,
            projection_spec_node=projection.projection_spec_node,
            post_update_review=post_update_review,
            now=now,
            first_call_index=len(list(state.get("provider_logs", []))) + 1,
        )
        stage_audits = [
            item.to_dict()
            for item in self.turn_stage_reducer.build_audits(
                plan=stage_plan,
                stage_results=stage_results,
                provider_logs=provider_logs,
            )
        ]
        decision_result = self.turn_decision_service.decide(
            normalized_input=context.normalized_input,
            working_document_update=working_document_update,
            post_update_review=post_update_review,
            projection={"projection_spec_node_id": projection.projection_spec_node_id},
            next_interaction=next_interaction,
            base_trace=preliminary_trace,
            closed_spec_node_ids=spec_update.closed_node_ids,
        )
        closure_decision = decision_result.closure_decision
        decision_trace = decision_result.decision_trace

        turn = {
            "turn_id": turn_id,
            "session_id": session.session_id,
            "user_input": user_input,
            "previous_interaction": context.previous_interaction,
            "normalized_input": context.normalized_input,
            "input_relation": context.input_relation,
            "intent_understanding_result": intent_understanding_result,
            "target_document_structure": target_document_structure,
            "stage_task_definition": stage_task_definition,
            "stage_quality_constraints": stage_quality_constraints,
            "spec_execution": spec_execution,
            "post_update_review": post_update_review,
            "review_after_apply_result": review_after_apply_result,
            "next_interaction_plan": next_interaction_plan,
            "closure_decision": closure_decision,
            "next_interaction": next_interaction,
            "stage_audits": stage_audits,
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
    def _stages_by_kind(*, stage_plan: TurnStagePlan, stage_kind: str) -> list[dict]:
        return [
            stage
            for stage in stage_plan.stages
            if str(stage.get("stage_kind") or "") == stage_kind
        ]

    def _review_stage_input(
        self,
        *,
        working_document: dict,
        working_document_update: dict,
        target_review: dict,
        global_review: dict,
        review_target_paths: list[str],
    ) -> dict:
        return {
            "working_document_after_apply": self.working_document_service.build_review_target(
                working_document=working_document,
                anchor_paths=[str(path) for path in review_target_paths if str(path).strip()],
            ),
            "working_document_update": working_document_update,
            "target_review": target_review,
            "global_review": global_review,
        }

    def _next_interaction_from_plan(self, *, plan: dict, focus_spec_node: dict, turn_index: int) -> dict:
        options = self.next_interaction_service.input_normalizer.normalize_quick_options(plan.get("quick_options"))
        question = str(plan.get("next_question") or "").strip()
        if not question:
            question = str(focus_spec_node.get("question") or focus_spec_node.get("title") or "请继续补充需求规格说明。")
        target_nodes = [
            str(item)
            for item in list(plan.get("target_spec_nodes") or [])
            if str(item).strip()
        ]
        if not target_nodes and focus_spec_node.get("node_id"):
            target_nodes = [str(focus_spec_node["node_id"])]
        if not focus_spec_node.get("node_id") and not target_nodes:
            interaction_type = "free_continue"
        else:
            interaction_type = "choice_question" if options else "open_question"
        return {
            "interaction_id": f"interaction-{turn_index:04d}",
            "type": interaction_type,
            "prompt": question,
            "options": options,
            "target_spec_node_ids": target_nodes,
            "reason": str(plan.get("plan_reason") or plan.get("review_acknowledgement") or ""),
        }

    def _resolved_global_review(self, *, model_global_review: dict, next_spec_node: dict, target_review: dict) -> dict:
        status = str(model_global_review.get("status") or "")
        if status == "continue_same_target":
            status = "continue_same_topic"
        if status == "continue_same_topic":
            return {
                **self.working_document_review_service.build_global_review(
                    next_spec_node={},
                    target_review={"status": "insufficient", "missing_aspects": model_global_review.get("remaining_gaps") or []},
                ),
                **model_global_review,
                "status": "continue_same_topic",
            }
        return self.working_document_review_service.build_global_review(
            next_spec_node=next_spec_node,
            target_review=target_review,
        )

    @staticmethod
    def _apply_next_interaction_plan_to_model_output(
        *,
        model_output: dict,
        next_interaction_plan: dict,
        next_interaction: dict,
    ) -> dict:
        user_message = str(next_interaction_plan.get("user_message") or "").strip()
        next_question = str(next_interaction_plan.get("next_question") or next_interaction.get("prompt") or "").strip()
        quick_options = list(next_interaction_plan.get("quick_options") or next_interaction.get("options") or [])
        assistant_message = RequirementAnalysisTurnEngine._assistant_message_after_planning(
            model_output=model_output,
            planning_user_message=user_message,
            next_question=next_question,
        )
        next_suggestion = {
            "suggestion_id": "",
            "kind": str(next_interaction_plan.get("planning_strategy") or "topic"),
            "content": next_question,
            "reason": str(next_interaction_plan.get("plan_reason") or ""),
            "related_spec_node_ids": list(next_interaction.get("target_spec_node_ids") or []),
        }
        return {
            **model_output,
            "assistant_message": assistant_message,
            "next_suggestion": next_suggestion,
            "next_question": next_question,
            "quick_options": quick_options,
            "open_questions_delta": [next_question] if next_question else [],
        }

    @staticmethod
    def _assistant_message_after_planning(
        *,
        model_output: dict,
        planning_user_message: str,
        next_question: str,
    ) -> str:
        plan_by_id = {
            str(plan.get("plan_id") or "").strip(): dict(plan)
            for plan in list(model_output.get("target_anchor_plan") or [])
            if isinstance(plan, dict) and str(plan.get("plan_id") or "").strip()
        }
        sections = []
        for patch in list(model_output.get("document_patch") or []):
            plan = plan_by_id.get(str(patch.get("plan_ref") or "").strip(), {})
            section = str(
                plan.get("display_heading")
                or plan.get("canonical_clause_heading")
                or plan.get("template_clause_id")
                or ""
            ).strip()
            if section and section not in sections:
                sections.append(section)
        if sections:
            write_summary = f"本轮已把{'、'.join(sections)}写入临时正文。"
        else:
            write_summary = str(model_output.get("assistant_message") or "本轮已更新临时正文。").strip()

        planning_message = planning_user_message
        if planning_message and "临时正文" in planning_message:
            base_message = planning_message
            if sections and not any(section in base_message for section in sections):
                base_message = RequirementAnalysisTurnEngine._append_sentence(
                    base_message,
                    f"写入位置：{'、'.join(sections)}。",
                )
        else:
            base_message = write_summary
        if next_question and next_question not in planning_message:
            base_message = RequirementAnalysisTurnEngine._append_sentence(
                base_message,
                f"建议下一步确认：{next_question}",
            )
        return base_message

    @staticmethod
    def _append_sentence(base: str, addition: str) -> str:
        base = base.strip()
        addition = addition.strip()
        if not addition:
            return base
        if not base:
            return addition
        if addition in base:
            return base
        separator = "" if base.endswith(("。", "！", "？", ".", "!", "?")) else "。"
        return f"{base}{separator}{addition}"

    def _build_provider_logs(
        self,
        *,
        stage_plan: TurnStagePlan,
        turn_id: str,
        session: SessionSnapshot,
        orchestrator: OrchestratorPackage,
        user_input: str,
        normalized: dict,
        stage_results: list[TurnStageResult],
        final_write_model_output: dict,
        final_write_provider_normalized_output: dict,
        working_document: dict,
        working_document_update: dict,
        target_review: dict,
        global_review: dict,
        projection_spec_node: dict,
        post_update_review: dict,
        now: str,
        first_call_index: int,
    ) -> list[dict]:
        logs: list[dict] = []
        prompt_bundle_overrides = {
            "working_document_json": str(working_document),
            "working_document_excerpt": working_document_update.get("after_excerpt", ""),
            "review_target_paths": target_review.get("review_target", []),
            "recent_revision_fragments": working_document_update.get("applied_fragment_ids", []),
            "review_goal": (
                projection_spec_node.get("question")
                or projection_spec_node.get("target_section")
                or ""
            ),
        }
        provider_response_overrides = {
            "target_review_json": target_review,
            "global_review_json": global_review,
        }
        call_offset = 0
        for stage_result in stage_results:
            stage = self._stage_for_result(stage_plan=stage_plan, stage_result=stage_result)
            if not self._should_write_provider_log(stage=stage):
                continue
            stage_kind = self._stage_kind(stage_result=stage_result)
            if stage_kind == "review":
                model_output = stage_result.model_output
                provider_normalized_output = self.provider_call_log_service.provider_normalized_output(model_output)
                service_output = {
                    "target_review": target_review,
                    "global_review": global_review,
                    "review_after_apply_result": {
                        **self.provider_call_log_service.service_output(model_output),
                        "target_review": target_review,
                        "global_review": global_review,
                    },
                }
            elif stage_kind == "write":
                model_output = final_write_model_output
                provider_normalized_output = final_write_provider_normalized_output
                service_output = {
                    **self.provider_call_log_service.service_output(final_write_model_output),
                    "working_document_update": working_document_update,
                    "post_update_review": post_update_review,
                }
            else:
                model_output = stage_result.model_output
                provider_normalized_output = self.provider_call_log_service.provider_normalized_output(model_output)
                service_output = self.provider_call_log_service.service_output(model_output)
            logs.append(
                self.provider_call_log_service.build(
                    turn_id=turn_id,
                    session=session,
                    orchestrator=orchestrator,
                    user_input=user_input,
                    normalized=normalized,
                    model_output=model_output,
                    provider_normalized_output=provider_normalized_output,
                    service_output=service_output,
                    prompt_bundle_overrides=prompt_bundle_overrides,
                    provider_response_overrides=provider_response_overrides,
                    stage_id=stage_result.stage_id,
                    stage_type=stage_result.stage_type,
                    created_at=now,
                    call_index=first_call_index + call_offset,
                )
            )
            call_offset += 1
        return logs

    @staticmethod
    def _stage_for_result(*, stage_plan: TurnStagePlan, stage_result: TurnStageResult) -> dict:
        for stage in stage_plan.stages:
            if str(stage.get("stage_id") or "") == stage_result.stage_id:
                return stage
        return {"stage_id": stage_result.stage_id, "stage_type": stage_result.stage_type}

    @staticmethod
    def _should_write_provider_log(*, stage: dict) -> bool:
        if not bool(stage.get("requires_provider_call")):
            return False
        execution_mode = str(stage.get("execution_mode") or "")
        return execution_mode in {"model", "local_runner"}

    @staticmethod
    def _stage_kind(*, stage_result: TurnStageResult) -> str:
        if "intent" in stage_result.stage_id:
            return "intent"
        if "next_interaction" in stage_result.stage_id or "planning" in stage_result.stage_id:
            return "next_interaction"
        if "review" in stage_result.stage_id:
            return "review"
        return "write"

    @staticmethod
    def _orchestrator(orchestrator_id: str) -> OrchestratorPackage:
        from app.orchestrators.package_loader import get_orchestrator_registry

        return get_orchestrator_registry().require(orchestrator_id)

    @staticmethod
    def _adopt_stage_model_output(adoption_policy: str, stage_results: list) -> dict:
        if not stage_results:
            raise ValueError("turn strategy produced no stage results")
        if adoption_policy == "adopt_last_completed_stage":
            return stage_results[-1].model_output
        return stage_results[0].model_output

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
