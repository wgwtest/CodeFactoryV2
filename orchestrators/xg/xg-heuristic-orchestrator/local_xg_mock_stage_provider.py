from __future__ import annotations

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.provider_call_service import ProviderRunResult, RequirementAnalysisProviderCallService
from app.requirement_analysis.session_snapshot import SessionSnapshot


class LocalXGMockStageProvider:
    def __init__(self, *, provider_call_service: RequirementAnalysisProviderCallService) -> None:
        self.spec_tree_service = provider_call_service.spec_tree_service
        self.process_artifact_service = provider_call_service.process_artifact_service
        self.runner_host = provider_call_service.runner_host

    def run(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        stage: dict,
        stage_input: dict,
    ) -> ProviderRunResult:
        stage_kind = str(stage.get("stage_kind") or "write")
        if stage_kind == "intent":
            return self._intent_output(
                session=session,
                user_input=user_input,
                normalized=normalized,
                orchestrator=orchestrator,
                stage=stage,
                stage_input=stage_input,
            )
        if stage_kind == "review":
            return self._review_output(
                session=session,
                user_input=user_input,
                normalized=normalized,
                orchestrator=orchestrator,
                stage=stage,
                stage_input=stage_input,
            )
        if stage_kind == "next_interaction":
            return self._next_interaction_output(
                session=session,
                user_input=user_input,
                normalized=normalized,
                orchestrator=orchestrator,
                stage=stage,
                stage_input=stage_input,
            )
        return self._write_output(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator=orchestrator,
            stage=stage,
            stage_input=stage_input,
        )

    def _intent_output(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator: OrchestratorPackage,
        stage: dict,
        stage_input: dict,
    ) -> ProviderRunResult:
        context = dict(stage_input.get("turn_context") or {})
        active_node = dict(context.get("active_spec_node") or {})
        active_section = str(active_node.get("target_section") or "1 总则 / 编写目的")
        semantic = str(normalized.get("semantic") or user_input)
        matched_option = normalized.get("matched_option")
        input_type = str(normalized.get("input_type") or "free_text")
        if matched_option and semantic != str(matched_option):
            intent_input_type = "option_answer_with_supplement"
        elif matched_option:
            intent_input_type = "option_answer"
        elif not dict(stage_input.get("working_document") or {}).get("blocks"):
            intent_input_type = "first_round_product_concept"
        else:
            intent_input_type = input_type or "free_supplement"
        intent_result = {
            "user_goal_summary": semantic,
            "input_type": intent_input_type,
            "relation_to_previous_interaction": str((context.get("input_relation") or {}).get("relation") or "none"),
            "option_handling": "matched_option" if matched_option else "not_option",
            "matched_option": str(matched_option) if matched_option else None,
            "supplemental_facts": [semantic] if semantic else [],
            "target_section_candidates": [active_section],
            "document_strategy": "bootstrap_document" if intent_input_type == "first_round_product_concept" else "write_targeted_sections",
            "write_task_candidate": f"围绕“{active_section}”把用户输入转成需求规格正文。",
            "review_focus_candidate": f"检查“{active_section}”是否形成可作为需求规格说明的正文。",
            "ambiguities": [],
        }
        target_document_structure = {
            "target_sections": [active_section],
            "target_anchor_paths": [active_section],
            "current_major_gaps": [str(active_node.get("question") or "当前章节仍缺少正文。")],
        }
        stage_task_definition = {
            "task_summary": intent_result["write_task_candidate"],
            "target_sections": [active_section],
            "non_goals": ["不要直接生成正式需求规格文档；只维护 Lab 临时正文。"],
            "must_output": ["confirmed_facts_delta", "document_patch", "assistant_message"],
            "review_standard": intent_result["review_focus_candidate"],
        }
        stage_quality_constraints = {
            "minimum_depth": "至少写出可进入需求规格说明的一段完整正文，不只输出章节名或六个字摘要。",
            "must_cover_dimensions": ["用户输入中的明确事实", "目标章节成文", "后续缺口"],
            "assistant_reply_style": "先说明本轮写入内容，再说明下一步由规划阶段给出。",
        }
        provider_response = {
            "intent_understanding_result": intent_result,
            "target_document_structure": target_document_structure,
            "stage_task_definition": stage_task_definition,
            "stage_quality_constraints": stage_quality_constraints,
            "confidence": "medium",
        }
        return self._provider_result(
            session=session,
            orchestrator=orchestrator,
            user_input=user_input,
            normalized=normalized,
            stage=stage,
            stage_input=stage_input,
            provider_response=provider_response,
            raw_content="mock_intent_understanding_output",
        )

    def _write_output(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator: OrchestratorPackage,
        stage: dict,
        stage_input: dict,
    ) -> ProviderRunResult:
        semantic = str(normalized.get("semantic") or user_input)
        state = dict(session.payload or {})
        spec_tree = list(
            state.get("spec_tree")
            or self.spec_tree_service.new_spec_tree(session.template_id, orchestrator_id=orchestrator.orchestrator_id)
        )
        active_node = self.spec_tree_service.find_spec_node(
            spec_tree,
            str(state.get("active_spec_node_id") or ""),
        )
        active_section = active_node.get("target_section") if active_node else "未绑定模板章节"
        template_clause_id = str(active_node.get("node_id") or "SPEC-REQ-1.1").removeprefix("SPEC-")
        display_heading = self._display_heading_from_stage_input(
            stage_input=stage_input,
            template_clause_id=template_clause_id,
            fallback=str(active_section),
        )
        target_anchor_plan = [
            {
                "plan_id": "AP-001",
                "decision_type": "append_existing_clause",
                "template_clause_id": template_clause_id,
                "canonical_clause_heading": display_heading,
                "subtopic_action": "none",
                "subtopic_key": "",
                "subtopic_title": "",
                "display_heading": display_heading,
                "template_shape_ref": "coarse_grained_extensible",
                "reason": "Mock Provider 使用当前活动节点作为结构化锚点。",
                "confidence": "medium",
                "anchor_path": template_clause_id,
            }
        ]
        provider_response = {
            "organizer_interpretation": {
                "summary": f"用户输入可转化为 {active_section} 的需求规格材料。",
                "intent": "supplement_requirement",
                "confidence": "medium",
            },
            "assistant_message": f"基于你的输入，本轮更新了：{active_section}。",
            "next_suggestion": {
                "kind": "topic",
                "content": "",
                "reason": "",
                "related_spec_node_ids": [],
            },
            "next_question": str(active_node.get("question") if active_node else "请继续补充需求规格说明。"),
            "quick_options": self.process_artifact_service.quick_options_for_node(orchestrator.orchestrator_id, active_node),
            "template_shape_assessment": {
                "shape_type": "coarse_grained_extensible",
                "reason": "Mock Provider 不做业务语义判断，仅生成符合协议的结构化输出。",
                "allowed_write_modes": ["append_existing_clause", "revise_existing_anchor", "create_subtopic_under_clause"],
                "forbidden_write_modes": ["invent_new_template_clause", "invent_new_section_number"],
                "template_revision_recommendations": [],
            },
            "target_anchor_plan": target_anchor_plan,
            "confirmed_facts_delta": [
                self.process_artifact_service.fact_for_node(orchestrator.orchestrator_id, active_node, semantic)
            ],
            "open_questions_delta": [str(active_node.get("question") if active_node else "请继续补充需求规格说明。")],
            "document_patch": [
                {
                    "plan_ref": "AP-001",
                    "operation": "append_or_update",
                    "content": self.process_artifact_service.patch_for_node(orchestrator.orchestrator_id, active_node, semantic),
                    "write_policy": session.write_policy,
                }
            ],
            "annotations": ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
            "risks": [],
            "confidence": "medium",
        }
        return self._provider_result(
            session=session,
            orchestrator=orchestrator,
            user_input=user_input,
            normalized=normalized,
            stage=stage,
            stage_input={
                **stage_input,
                "working_document": stage_input.get("working_document") or dict(state.get("working_document") or {}),
                "active_spec_node": active_node or {},
            },
            provider_response=provider_response,
            raw_content="mock_model_output",
        )

    def _review_output(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator: OrchestratorPackage,
        stage: dict,
        stage_input: dict,
    ) -> ProviderRunResult:
        working_document_after_apply = dict(stage_input.get("working_document_after_apply") or {})
        working_document_update = dict(stage_input.get("working_document_update") or {})
        fallback_target_review = dict(stage_input.get("target_review") or {})
        fallback_global_review = dict(stage_input.get("global_review") or {})
        excerpt = str(working_document_after_apply.get("excerpt") or working_document_update.get("after_excerpt") or "").strip()
        target_review = {
            "status": "acceptable" if excerpt else "insufficient",
            "review_target": list(working_document_after_apply.get("review_target_paths") or fallback_target_review.get("review_target") or []),
            "reason": "Mock 模型 Review：应用后的临时正文已具备可回看表达。" if excerpt else "Mock 模型 Review：应用后的临时正文不足。",
            "covered_points": ["临时正文已形成"] if excerpt else [],
            "missing_aspects": [] if excerpt else list(fallback_target_review.get("missing_aspects") or ["缺少应用后的正文"]),
            "evidence_block_ids": [
                str(block.get("block_id"))
                for block in list(working_document_after_apply.get("blocks") or [])
                if isinstance(block, dict) and block.get("block_id")
            ],
            "evidence_fragment_ids": list(working_document_update.get("applied_fragment_ids") or []),
        }
        global_review = dict(fallback_global_review)
        if not global_review:
            global_review = {
                "status": "move_next_node" if excerpt else "continue_same_topic",
                "summary": "Mock 模型 Review：可推进下一节点。" if excerpt else "Mock 模型 Review：继续补充当前目标。",
                "remaining_gaps": [] if excerpt else target_review["missing_aspects"],
            }
        provider_response = {
            "target_review": target_review,
            "global_review": global_review,
            "compliance_result": "pass" if target_review["status"] == "acceptable" else "needs_followup",
            "written_fact_summary": target_review["covered_points"],
            "blocking_findings": [] if target_review["status"] == "acceptable" else target_review["missing_aspects"],
            "blocking_reasons": [] if target_review["status"] == "acceptable" else [target_review["reason"]],
            "planning_evidence": [
                str(item)
                for item in [
                    *target_review.get("evidence_block_ids", []),
                    *target_review.get("evidence_fragment_ids", []),
                ]
                if str(item).strip()
            ],
            "rewrite_advice": [],
            "review_annotations": ["Mock 模型 Review 读取了应用后的临时正文。"],
            "confidence": "medium",
        }
        return self._provider_result(
            session=session,
            orchestrator=orchestrator,
            user_input=user_input,
            normalized=normalized,
            stage=stage,
            stage_input={
                **stage_input,
                "working_document_after_apply": working_document_after_apply,
                "working_document_update": working_document_update,
            },
            provider_response=provider_response,
            raw_content="mock_review_output",
        )

    def _next_interaction_output(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator: OrchestratorPackage,
        stage: dict,
        stage_input: dict,
    ) -> ProviderRunResult:
        next_spec_node = dict(stage_input.get("next_spec_node") or {})
        current_spec_node = dict(stage_input.get("current_spec_node") or {})
        review_result = dict(stage_input.get("review_after_apply_result") or {})
        target_review = dict(review_result.get("target_review") or stage_input.get("target_review") or {})
        global_review = dict(review_result.get("global_review") or stage_input.get("global_review") or {})
        focus_node = current_spec_node if str(global_review.get("status") or "") == "continue_same_topic" else next_spec_node
        if focus_node.get("node_id"):
            question = str(focus_node.get("question") or focus_node.get("title") or "请继续补充需求规格说明。")
            quick_options = self.process_artifact_service.quick_options_for_node(orchestrator.orchestrator_id, focus_node)
            strategy = "continue_same_topic" if focus_node == current_spec_node else "move_next_node"
            user_message = f"本轮已补入临时正文，并完成应用后回看。建议下一步确认：{question}"
        else:
            question = "当前完成度树暂无待确认节点，可以进入整体复核。"
            quick_options = []
            strategy = "whole_document_review"
            user_message = "本轮已补入临时正文，并完成应用后回看。当前可进入整体复核。"
        provider_response = {
            "next_interaction_plan": {
                "planning_strategy": strategy,
                "user_message": user_message,
                "next_question": question,
                "quick_options": quick_options,
                "plan_reason": str(global_review.get("summary") or target_review.get("reason") or "基于应用后回看规划下一轮交互。"),
                "review_acknowledgement": str(target_review.get("reason") or ""),
                "target_spec_nodes": [str(focus_node["node_id"])] if focus_node.get("node_id") else [],
            },
            "planning_trace": ["Mock 下一步交互规划读取了 review 结果和完成度树状态。"],
            "confidence": "medium",
        }
        return self._provider_result(
            session=session,
            orchestrator=orchestrator,
            user_input=user_input,
            normalized=normalized,
            stage=stage,
            stage_input=stage_input,
            provider_response=provider_response,
            raw_content="mock_next_interaction_planning_output",
        )

    @staticmethod
    def _display_heading_from_stage_input(*, stage_input: dict, template_clause_id: str, fallback: str) -> str:
        chapter_context = dict(stage_input.get("chapter_configuration_context") or {})
        canonical_clause_map = dict(chapter_context.get("canonical_clause_map") or {})
        clause = dict(canonical_clause_map.get(template_clause_id) or {})
        return str(clause.get("display_heading") or clause.get("heading") or fallback)

    def _provider_result(
        self,
        *,
        session: SessionSnapshot,
        orchestrator: OrchestratorPackage,
        user_input: str,
        normalized: dict,
        stage: dict,
        stage_input: dict,
        provider_response: dict,
        raw_content: str,
    ) -> ProviderRunResult:
        provider_request = self._mock_provider_request(
            orchestrator=orchestrator,
            session=session,
            user_input=user_input,
            normalized=normalized,
            stage=stage,
            stage_input=stage_input,
        )
        return self._to_provider_run_result({
            **provider_response,
            "raw_model_response": {
                "provider_id": session.provider_id,
                "model": session.model,
                "mock": True,
                "orchestrator_id": orchestrator.orchestrator_id,
                "mode": orchestrator.mode,
                "user_input": user_input,
                "provider_request": provider_request,
                "provider_response": {
                    "raw_content": raw_content,
                    "parsed_json": provider_response,
                },
                "provider_normalized_output": provider_response,
            },
        })

    def _mock_provider_request(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        stage: dict,
        stage_input: dict,
    ) -> dict:
        stage_payload = dict(stage)
        prompt_bundle = self.runner_host.build_stage_prompt_bundle(
            orchestrator.orchestrator_id,
            stage=stage_payload,
            context=stage_input,
        )
        return {
            "messages": [{"role": "user", "content": prompt_bundle["assembled_prompt"]}],
            "prompt_bundle": prompt_bundle,
            "mock_context": {
                "topic": session.topic,
                "template_id": session.template_id,
                "knowledge_package_id": session.knowledge_package_id,
                "write_policy": session.write_policy,
                "user_input": user_input,
                "normalized_input": normalized,
                "stage": stage_payload,
            },
        }

    @staticmethod
    def _to_provider_run_result(model_output: dict) -> ProviderRunResult:
        raw_model_response = dict(model_output.get("raw_model_response") or {})
        normalized_output = raw_model_response.get("provider_normalized_output")
        if not isinstance(normalized_output, dict):
            normalized_output = {
                key: value for key, value in model_output.items() if key != "raw_model_response"
            }
        return ProviderRunResult(
            model_output=model_output,
            provider_request=dict(raw_model_response.get("provider_request") or {}),
            provider_response=dict(raw_model_response.get("provider_response") or {}),
            normalized_output=normalized_output,
        )
