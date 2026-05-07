from __future__ import annotations

import json
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.requirement_analysis.session_snapshot import SessionSnapshot


class DeepSeekRequirementAnalysisClient:
    def __init__(self, *, api_key: str, base_url: str, model: str, runner_host: OrchestratorRunnerHost | None = None) -> None:
        self.model = model
        self.runner_host = runner_host or OrchestratorRunnerHost()
        self.client = OpenAI(api_key=api_key, base_url=base_url, http_client=httpx.Client(trust_env=False))

    def run_stage(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator_id: str,
        stage: dict,
        stage_input: dict | None = None,
    ) -> dict:
        prompt_bundle = self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=orchestrator_id,
            stage=stage,
            stage_input=stage_input or {},
        )
        request_messages = [
            {
                "role": "system",
                "content": (
                    "你是 CodeFactory V2 P2 XG 需求分析组织器 Lab 的可插拔组织器 Provider。"
                    "你只返回 JSON，不要返回 Markdown。"
                ),
            },
            {"role": "user", "content": prompt_bundle["assembled_prompt"]},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = self._extract_content(response)
        parsed = json.loads(content)
        return self._normalize_output(
            parsed,
            session=session,
            user_input=user_input,
            prompt_bundle=prompt_bundle,
            request_messages=request_messages,
            raw_content=content,
            stage=stage,
        )

    def _build_prompt_bundle(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator_id: str,
        stage: dict | None = None,
        stage_input: dict | None = None,
    ) -> dict:
        state = dict(session.payload or {})
        stage = stage or {"stage_id": "write", "stage_kind": "write", "prompt_id": "write"}
        context = dict(stage_input or self._base_stage_context(session=session, user_input=user_input, normalized=normalized))
        extra_prompt_bundle = {
            "working_document_json": json.dumps(context.get("working_document") or {}, ensure_ascii=False),
            "working_document_after_apply_json": json.dumps(context.get("working_document_after_apply") or {}, ensure_ascii=False),
            "working_document_update_json": json.dumps(context.get("working_document_update") or {}, ensure_ascii=False),
            "chapter_configuration_context_json": json.dumps(context.get("chapter_configuration_context") or {}, ensure_ascii=False),
            "template_shape_assessment_json": json.dumps(context.get("template_shape_assessment") or {}, ensure_ascii=False),
            "target_anchor_plan_json": json.dumps(context.get("target_anchor_plan") or [], ensure_ascii=False),
            "decision_state_json": json.dumps(context.get("decision_state") or state.get("decision_state") or {}, ensure_ascii=False),
            "decision_state_document_json": json.dumps(
                context.get("decision_state_document") or state.get("decision_state_document") or {},
                ensure_ascii=False,
            ),
            "working_document_excerpt": str((context.get("working_document_after_apply") or {}).get("excerpt") or context.get("working_document_excerpt") or ""),
            "review_target_paths": list(context.get("review_target_paths") or []),
            "recent_revision_fragments": list(context.get("recent_revision_fragments") or []),
            "review_goal": str(context.get("review_goal") or ""),
            "stage_task_definition_json": json.dumps(context.get("stage_task_definition") or {}, ensure_ascii=False),
            "quality_constraints_json": json.dumps(context.get("stage_quality_constraints") or {}, ensure_ascii=False),
        }
        runner_host = getattr(self, "runner_host", None) or OrchestratorRunnerHost()
        self.runner_host = runner_host
        return runner_host.build_stage_prompt_bundle(
            orchestrator_id,
            stage=stage,
            context=context,
            extra_prompt_bundle=extra_prompt_bundle,
        )

    @staticmethod
    def _working_document_excerpt(*, state: dict) -> str:
        active_node_id = str(state.get("active_spec_node_id") or "")
        working_document = dict(state.get("working_document") or {})
        active_node = DeepSeekRequirementAnalysisClient._find_spec_node_static(
            list(state.get("spec_tree", [])),
            active_node_id,
        )
        active_anchor = str((active_node or {}).get("target_section") or "").strip()
        blocks = [block for block in list(working_document.get("blocks", [])) if isinstance(block, dict)]
        if active_anchor:
            matched = [
                str(block.get("text") or "").strip()
                for block in blocks
                if str(block.get("anchor_path") or "").strip() == active_anchor and str(block.get("text") or "").strip()
            ]
            if matched:
                return "\n\n".join(matched)
        return "\n\n".join(str(block.get("text") or "").strip() for block in blocks if str(block.get("text") or "").strip())

    @staticmethod
    def _base_stage_context(*, session: SessionSnapshot, user_input: str, normalized: dict) -> dict:
        state = dict(getattr(session, "payload", {}) or {})
        return {
            "turn_context": {
                "topic": getattr(session, "topic", ""),
                "template_id": getattr(session, "template_id", ""),
                "knowledge_package_id": getattr(session, "knowledge_package_id", ""),
                "write_policy": getattr(session, "write_policy", ""),
                "previous_interaction": state.get("next_interaction"),
                "last_quick_options": list(state.get("last_quick_options", [])),
                "messages": list(state.get("messages", []))[-8:],
                "confirmed_facts": list(state.get("confirmed_facts", [])),
                "open_questions": list(state.get("open_questions", [])),
                "user_input": user_input,
                "normalized_input": normalized,
                "active_spec_node_id": str(state.get("active_spec_node_id") or ""),
            },
            "working_document": dict(state.get("working_document") or {}),
            "spec_tree": list(state.get("spec_tree", [])),
            "previous_interaction": state.get("next_interaction"),
            "user_input": user_input,
            "normalized_input": normalized,
        }

    @staticmethod
    def _review_target_paths(*, state: dict) -> list[str]:
        active_node_id = str(state.get("active_spec_node_id") or "")
        active_node = DeepSeekRequirementAnalysisClient._find_spec_node_static(
            list(state.get("spec_tree", [])),
            active_node_id,
        )
        target = str((active_node or {}).get("target_section") or "").strip()
        return [target] if target else []

    @staticmethod
    def _recent_revision_fragments(*, state: dict) -> list[str]:
        working_document = dict(state.get("working_document") or {})
        fragments = [
            str(fragment.get("fragment_id") or "").strip()
            for fragment in list(working_document.get("revision_fragments", []))[-5:]
            if isinstance(fragment, dict) and str(fragment.get("fragment_id") or "").strip()
        ]
        return fragments

    def _review_goal(self, *, state: dict) -> str:
        active_node_id = str(state.get("active_spec_node_id") or "")
        spec_tree = list(state.get("spec_tree", []))
        node = self._find_spec_node(spec_tree, active_node_id)
        return str((node or {}).get("question") or (node or {}).get("target_section") or "")

    def _build_prompt(self, *, session: SessionSnapshot, user_input: str, normalized: dict) -> str:
        runner_host = getattr(self, "runner_host", None) or OrchestratorRunnerHost()
        self.runner_host = runner_host
        return self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=session.orchestrator_id,
        )["assembled_prompt"]

    def _find_spec_node(self, nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            found = self._find_spec_node(list(node.get("children", [])), node_id)
            if found is not None:
                return found
        return None

    def _spec_node_path(self, nodes: list[dict], node_id: str, current: list[str] | None = None) -> list[str]:
        current = current or []
        for node in nodes:
            next_path = [*current, str(node.get("title") or node.get("node_id"))]
            if node.get("node_id") == node_id:
                return next_path
            child_path = self._spec_node_path(list(node.get("children", [])), node_id, next_path)
            if child_path:
                return child_path
        return []

    @staticmethod
    def _extract_content(response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("DeepSeek 未返回 choices")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 响应缺少 JSON 文本")
        return content

    def _normalize_output(
        self,
        payload: dict[str, Any],
        *,
        session: SessionSnapshot,
        user_input: str,
        prompt_bundle: dict[str, Any] | None = None,
        request_messages: list[dict[str, str]] | None = None,
        raw_content: str | None = None,
        stage: dict | None = None,
    ) -> dict:
        prompt_id = str((prompt_bundle or {}).get("prompt_id") or (stage or {}).get("prompt_id") or "write")
        if prompt_id == "intent_understanding":
            normalized_output = {
                "intent_understanding_result": self._normalize_intent_understanding_result(payload.get("intent_understanding_result")),
                "target_document_structure": self._normalize_target_document_structure(payload.get("target_document_structure")),
                "stage_task_definition": self._normalize_stage_task_definition(payload.get("stage_task_definition")),
                "stage_quality_constraints": self._normalize_stage_quality_constraints(payload.get("stage_quality_constraints")),
                "confidence": self._normalize_confidence(payload.get("confidence")),
            }
            return {
                **normalized_output,
                "raw_model_response": self._stage_raw_model_response(
                    session=session,
                    user_input=user_input,
                    prompt_bundle=prompt_bundle,
                    request_messages=request_messages,
                    raw_content=raw_content,
                    payload=payload,
                    normalized_output=normalized_output,
                    stage=stage,
                ),
            }
        if prompt_id == "decision_state_delta":
            target_anchor_plan = self._normalize_target_anchor_plan(payload.get("target_anchor_plan"))
            normalized_output = {
                "organizer_interpretation": self._normalize_organizer_interpretation(payload.get("organizer_interpretation")),
                "assistant_message": str(payload.get("assistant_message") or "本轮已更新结构化状态。"),
                "next_suggestion": self._normalize_next_suggestion(payload.get("next_suggestion")),
                "next_question": str(payload.get("next_question") or ""),
                "quick_options": self._normalize_quick_options(payload.get("quick_options")),
                "decision_state_delta": self._normalize_decision_state_delta(payload.get("decision_state_delta")),
                "template_shape_assessment": self._normalize_template_shape_assessment(payload.get("template_shape_assessment")),
                "target_anchor_plan": target_anchor_plan,
                "confirmed_facts_delta": self._string_list(payload.get("confirmed_facts_delta")),
                "open_questions_delta": self._string_list(payload.get("open_questions_delta")),
                "document_patch": self._normalize_document_patch(
                    payload.get("document_patch"),
                    session=session,
                    target_anchor_plan=target_anchor_plan,
                ),
                "annotations": self._string_list(payload.get("annotations")),
                "risks": self._string_list(payload.get("risks")),
                "confidence": self._normalize_confidence(payload.get("confidence")),
            }
            return {
                **normalized_output,
                "raw_model_response": self._stage_raw_model_response(
                    session=session,
                    user_input=user_input,
                    prompt_bundle=prompt_bundle,
                    request_messages=request_messages,
                    raw_content=raw_content,
                    payload=payload,
                    normalized_output=normalized_output,
                    stage=stage,
                ),
            }
        if prompt_id == "review_after_apply":
            normalized_output = {
                "compliance_result": str(payload.get("compliance_result") or "needs_followup"),
                "written_fact_summary": self._string_list(payload.get("written_fact_summary")),
                "blocking_findings": self._string_list(payload.get("blocking_findings")),
                "blocking_reasons": self._string_list(payload.get("blocking_reasons")),
                "planning_evidence": self._string_list(payload.get("planning_evidence")),
                "target_review": self._normalize_target_review(payload.get("target_review")),
                "global_review": self._normalize_global_review(payload.get("global_review")),
                "rewrite_advice": self._string_list(payload.get("rewrite_advice")),
                "review_annotations": self._string_list(payload.get("review_annotations")),
                "confidence": self._normalize_confidence(payload.get("confidence")),
            }
            return {
                **normalized_output,
                "raw_model_response": self._stage_raw_model_response(
                    session=session,
                    user_input=user_input,
                    prompt_bundle=prompt_bundle,
                    request_messages=request_messages,
                    raw_content=raw_content,
                    payload=payload,
                    normalized_output=normalized_output,
                    stage=stage,
                ),
            }
        if prompt_id == "next_interaction_planning":
            normalized_output = {
                "next_interaction_plan": self._normalize_next_interaction_plan(payload.get("next_interaction_plan")),
                "planning_trace": self._string_list(payload.get("planning_trace")),
                "confidence": self._normalize_confidence(payload.get("confidence")),
            }
            return {
                **normalized_output,
                "raw_model_response": self._stage_raw_model_response(
                    session=session,
                    user_input=user_input,
                    prompt_bundle=prompt_bundle,
                    request_messages=request_messages,
                    raw_content=raw_content,
                    payload=payload,
                    normalized_output=normalized_output,
                    stage=stage,
                ),
            }
        normalized_output = {
            "organizer_interpretation": self._normalize_organizer_interpretation(payload.get("organizer_interpretation")),
            "assistant_message": str(payload.get("assistant_message") or "已接收，本轮需要继续补齐需求信息。"),
            "next_suggestion": self._normalize_next_suggestion(payload.get("next_suggestion")),
            "next_question": str(payload.get("next_question") or ""),
            "quick_options": self._normalize_quick_options(payload.get("quick_options")),
            "template_shape_assessment": self._normalize_template_shape_assessment(payload.get("template_shape_assessment")),
            "target_anchor_plan": self._normalize_target_anchor_plan(payload.get("target_anchor_plan")),
            "confirmed_facts_delta": self._string_list(payload.get("confirmed_facts_delta")),
            "open_questions_delta": self._string_list(payload.get("open_questions_delta")),
            "document_patch": self._normalize_document_patch(
                payload.get("document_patch"),
                session=session,
                target_anchor_plan=self._normalize_target_anchor_plan(payload.get("target_anchor_plan")),
            ),
            "annotations": self._string_list(payload.get("annotations")),
            "risks": self._string_list(payload.get("risks")),
            "confidence": self._normalize_confidence(payload.get("confidence")),
        }
        return {
            **normalized_output,
            "raw_model_response": self._stage_raw_model_response(
                session=session,
                user_input=user_input,
                prompt_bundle=prompt_bundle,
                request_messages=request_messages,
                raw_content=raw_content,
                payload=payload,
                normalized_output=normalized_output,
                stage=stage,
            ),
        }

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _normalize_target_review(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "status": "insufficient",
                "review_target": [],
                "reason": "模型未返回目标范围回看结果。",
                "covered_points": [],
                "missing_aspects": [],
                "evidence_block_ids": [],
                "evidence_fragment_ids": [],
            }
        return {
            "status": str(value.get("status") or "insufficient"),
            "review_target": DeepSeekRequirementAnalysisClient._string_list(value.get("review_target")),
            "reason": str(value.get("reason") or ""),
            "covered_points": DeepSeekRequirementAnalysisClient._string_list(value.get("covered_points")),
            "missing_aspects": DeepSeekRequirementAnalysisClient._string_list(value.get("missing_aspects")),
            "evidence_block_ids": DeepSeekRequirementAnalysisClient._string_list(value.get("evidence_block_ids")),
            "evidence_fragment_ids": DeepSeekRequirementAnalysisClient._string_list(value.get("evidence_fragment_ids")),
        }

    @staticmethod
    def _normalize_global_review(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "status": "continue_same_topic",
                "summary": "",
                "remaining_gaps": [],
            }
        status = str(value.get("status") or "continue_same_topic")
        if status == "continue_same_target":
            status = "continue_same_topic"
        return {
            "status": status,
            "summary": str(value.get("summary") or ""),
            "remaining_gaps": DeepSeekRequirementAnalysisClient._string_list(value.get("remaining_gaps")),
        }

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        confidence = str(value or "medium").lower()
        return confidence if confidence in {"low", "medium", "high"} else "medium"

    @staticmethod
    def _normalize_organizer_interpretation(value: Any) -> dict:
        if not isinstance(value, dict):
            return {"summary": "已理解用户本轮输入。", "intent": "supplement_requirement", "confidence": "medium"}
        return {
            "summary": str(value.get("summary") or "已理解用户本轮输入。"),
            "intent": str(value.get("intent") or "supplement_requirement"),
            "confidence": DeepSeekRequirementAnalysisClient._normalize_confidence(value.get("confidence")),
        }

    @staticmethod
    def _normalize_next_suggestion(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "kind": "topic",
                "content": "",
                "reason": "Provider 未生成下一轮建议。",
                "related_spec_node_ids": [],
            }
        related = value.get("related_spec_node_ids")
        return {
            "kind": str(value.get("kind") or "topic"),
            "content": str(value.get("content") or ""),
            "reason": str(value.get("reason") or ""),
            "related_spec_node_ids": [str(item) for item in related if str(item).strip()] if isinstance(related, list) else [],
        }

    @staticmethod
    def _normalize_quick_options(value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []
        options = []
        for item in value[:5]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()[:4]
            label = str(item.get("label") or "").strip()
            if key and label:
                options.append({"key": key, "label": label, "recommended": bool(item.get("recommended"))})
        return options

    @staticmethod
    def _normalize_template_shape_assessment(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "shape_type": "coarse_grained_extensible",
                "reason": "",
                "allowed_write_modes": [],
                "forbidden_write_modes": [],
                "template_revision_recommendations": [],
            }
        return {
            "shape_type": str(value.get("shape_type") or "coarse_grained_extensible"),
            "reason": str(value.get("reason") or ""),
            "allowed_write_modes": DeepSeekRequirementAnalysisClient._string_list(value.get("allowed_write_modes")),
            "forbidden_write_modes": DeepSeekRequirementAnalysisClient._string_list(value.get("forbidden_write_modes")),
            "template_revision_recommendations": DeepSeekRequirementAnalysisClient._string_list(
                value.get("template_revision_recommendations")
            ),
        }

    @staticmethod
    def _normalize_target_anchor_plan(value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []
        plans: list[dict] = []
        seen: set[str] = set()
        for index, item in enumerate(value[:8], start=1):
            if not isinstance(item, dict):
                continue
            plan_id = str(item.get("plan_id") or f"AP-{index:03d}").strip()
            if not plan_id or plan_id in seen:
                raise ValueError(f"invalid target_anchor_plan.plan_id: {plan_id}")
            seen.add(plan_id)
            template_clause_id = str(item.get("template_clause_id") or "").strip()
            if not template_clause_id:
                raise ValueError(f"target_anchor_plan {plan_id} missing template_clause_id")
            plans.append(
                {
                    "plan_id": plan_id,
                    "decision_type": str(item.get("decision_type") or "append_existing_clause"),
                    "template_clause_id": template_clause_id,
                    "canonical_clause_heading": str(item.get("canonical_clause_heading") or ""),
                    "subtopic_action": str(item.get("subtopic_action") or "none"),
                    "subtopic_key": str(item.get("subtopic_key") or ""),
                    "subtopic_title": str(item.get("subtopic_title") or ""),
                    "display_heading": str(item.get("display_heading") or item.get("canonical_clause_heading") or template_clause_id),
                    "template_shape_ref": str(item.get("template_shape_ref") or ""),
                    "reason": str(item.get("reason") or ""),
                    "confidence": DeepSeekRequirementAnalysisClient._normalize_confidence(item.get("confidence")),
                    "anchor_path": str(item.get("anchor_path") or ""),
                }
            )
        return plans

    @staticmethod
    def _normalize_document_patch(
        value: Any,
        *,
        session: SessionSnapshot,
        target_anchor_plan: list[dict] | None = None,
    ) -> list[dict]:
        if not isinstance(value, list):
            return []
        known_plan_ids = {str(plan.get("plan_id")) for plan in list(target_anchor_plan or [])}
        patches = []
        for item in value[:6]:
            if not isinstance(item, dict):
                continue
            plan_ref = str(item.get("plan_ref") or "").strip()
            content = str(item.get("content") or "").strip()
            if not plan_ref or not content:
                continue
            if known_plan_ids and plan_ref not in known_plan_ids:
                raise ValueError(f"document_patch.plan_ref does not match target_anchor_plan: {plan_ref}")
            patches.append(
                {
                    "plan_ref": plan_ref,
                    "operation": str(item.get("operation") or "append_or_update"),
                    "content": content,
                    "write_policy": str(item.get("write_policy") or session.write_policy),
                }
            )
        return patches

    @staticmethod
    def _normalize_intent_understanding_result(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "user_goal_summary": "",
                "input_type": "free_supplement",
                "relation_to_previous_interaction": "none",
                "option_handling": "not_option",
                "matched_option": None,
                "supplemental_facts": [],
                "target_section_candidates": [],
                "document_strategy": "write_targeted_sections",
                "write_task_candidate": "",
                "review_focus_candidate": "",
                "ambiguities": [],
            }
        return {
            "user_goal_summary": str(value.get("user_goal_summary") or ""),
            "input_type": str(value.get("input_type") or "free_supplement"),
            "relation_to_previous_interaction": str(value.get("relation_to_previous_interaction") or "none"),
            "option_handling": str(value.get("option_handling") or "not_option"),
            "matched_option": str(value.get("matched_option")) if value.get("matched_option") is not None else None,
            "supplemental_facts": DeepSeekRequirementAnalysisClient._string_list(value.get("supplemental_facts")),
            "target_section_candidates": DeepSeekRequirementAnalysisClient._string_list(value.get("target_section_candidates")),
            "document_strategy": str(value.get("document_strategy") or "write_targeted_sections"),
            "write_task_candidate": str(value.get("write_task_candidate") or ""),
            "review_focus_candidate": str(value.get("review_focus_candidate") or ""),
            "ambiguities": DeepSeekRequirementAnalysisClient._string_list(value.get("ambiguities")),
        }

    @staticmethod
    def _normalize_target_document_structure(value: Any) -> dict:
        if not isinstance(value, dict):
            return {"target_sections": [], "target_anchor_paths": [], "current_major_gaps": []}
        return {
            "target_sections": DeepSeekRequirementAnalysisClient._string_list(value.get("target_sections")),
            "target_anchor_paths": DeepSeekRequirementAnalysisClient._string_list(value.get("target_anchor_paths")),
            "current_major_gaps": DeepSeekRequirementAnalysisClient._string_list(value.get("current_major_gaps")),
        }

    @staticmethod
    def _normalize_stage_task_definition(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "task_summary": "",
                "target_sections": [],
                "non_goals": [],
                "must_output": [],
                "review_standard": "",
            }
        return {
            "task_summary": str(value.get("task_summary") or ""),
            "target_sections": DeepSeekRequirementAnalysisClient._string_list(value.get("target_sections")),
            "non_goals": DeepSeekRequirementAnalysisClient._string_list(value.get("non_goals")),
            "must_output": DeepSeekRequirementAnalysisClient._string_list(value.get("must_output")),
            "review_standard": str(value.get("review_standard") or ""),
        }

    @staticmethod
    def _normalize_stage_quality_constraints(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "minimum_depth": "",
                "must_cover_dimensions": [],
                "assistant_reply_style": "",
            }
        return {
            "minimum_depth": str(value.get("minimum_depth") or ""),
            "must_cover_dimensions": DeepSeekRequirementAnalysisClient._string_list(value.get("must_cover_dimensions")),
            "assistant_reply_style": str(value.get("assistant_reply_style") or ""),
        }

    @staticmethod
    def _normalize_next_interaction_plan(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "planning_strategy": "wait_user_input",
                "user_message": "",
                "next_question": "",
                "quick_options": [],
                "plan_reason": "",
                "review_acknowledgement": "",
                "target_spec_nodes": [],
            }
        return {
            "planning_strategy": str(value.get("planning_strategy") or "wait_user_input"),
            "user_message": str(value.get("user_message") or ""),
            "next_question": str(value.get("next_question") or ""),
            "quick_options": DeepSeekRequirementAnalysisClient._normalize_quick_options(value.get("quick_options")),
            "plan_reason": str(value.get("plan_reason") or ""),
            "review_acknowledgement": str(value.get("review_acknowledgement") or ""),
            "target_spec_nodes": DeepSeekRequirementAnalysisClient._string_list(value.get("target_spec_nodes")),
        }

    @staticmethod
    def _normalize_decision_state_delta(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "confirmed_facts": [],
                "confirmed_decisions": [],
                "tentative_assumptions": [],
                "open_questions": [],
                "rejected_directions": [],
                "chapter_projections": [],
                "next_focus": "",
            }
        return {
            "confirmed_facts": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("confirmed_facts")),
            "confirmed_decisions": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("confirmed_decisions")),
            "tentative_assumptions": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("tentative_assumptions")),
            "open_questions": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("open_questions")),
            "rejected_directions": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("rejected_directions")),
            "chapter_projections": DeepSeekRequirementAnalysisClient._normalize_decision_state_items(value.get("chapter_projections")),
            "next_focus": str(value.get("next_focus") or ""),
        }

    @staticmethod
    def _normalize_decision_state_items(value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []
        items: list[dict] = []
        for item in value[:12]:
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("summary") or item.get("text") or "").strip()
                if not content:
                    continue
                items.append(
                    {
                        "content": content,
                        "source_turn_id": item.get("source_turn_id"),
                        "target_section": str(item.get("target_section") or ""),
                        "status": str(item.get("status") or "active"),
                    }
                )
                continue
            content = str(item).strip()
            if content:
                items.append({"content": content, "source_turn_id": None, "target_section": "", "status": "active"})
        return items

    @staticmethod
    def _stage_raw_model_response(
        *,
        session: SessionSnapshot,
        user_input: str,
        prompt_bundle: dict[str, Any] | None,
        request_messages: list[dict[str, str]] | None,
        raw_content: str | None,
        payload: dict[str, Any],
        normalized_output: dict[str, Any],
        stage: dict | None,
    ) -> dict:
        safe_prompt_bundle = {
            "assembled_prompt": str((prompt_bundle or {}).get("assembled_prompt") or ""),
            "context_json": str((prompt_bundle or {}).get("context_json") or ""),
            "working_document_json": str((prompt_bundle or {}).get("working_document_json") or ""),
            "working_document_after_apply_json": str((prompt_bundle or {}).get("working_document_after_apply_json") or ""),
            "working_document_update_json": str((prompt_bundle or {}).get("working_document_update_json") or ""),
            "chapter_configuration_context_json": str((prompt_bundle or {}).get("chapter_configuration_context_json") or ""),
            "template_shape_assessment_json": str((prompt_bundle or {}).get("template_shape_assessment_json") or ""),
            "target_anchor_plan_json": str((prompt_bundle or {}).get("target_anchor_plan_json") or ""),
            "decision_state_json": str((prompt_bundle or {}).get("decision_state_json") or ""),
            "decision_state_document_json": str((prompt_bundle or {}).get("decision_state_document_json") or ""),
            "working_document_excerpt": str((prompt_bundle or {}).get("working_document_excerpt") or ""),
            "review_target_paths": list((prompt_bundle or {}).get("review_target_paths") or []),
            "recent_revision_fragments": list((prompt_bundle or {}).get("recent_revision_fragments") or []),
            "review_goal": str((prompt_bundle or {}).get("review_goal") or ""),
            "schema_json": str((prompt_bundle or {}).get("schema_json") or ""),
            "adoption_policy_json": str((prompt_bundle or {}).get("adoption_policy_json") or ""),
            "stage_task_definition_json": str((prompt_bundle or {}).get("stage_task_definition_json") or ""),
            "quality_constraints_json": str((prompt_bundle or {}).get("quality_constraints_json") or ""),
            "policy_text": str((prompt_bundle or {}).get("policy_text") or ""),
            "prompt_text": str((prompt_bundle or {}).get("prompt_text") or ""),
            "stage_id": str((prompt_bundle or {}).get("stage_id") or ""),
            "prompt_id": str((prompt_bundle or {}).get("prompt_id") or ""),
        }
        return {
            "provider_id": "deepseek",
            "model": str(getattr(session, "model", "") or "deepseek-chat"),
            "mock": False,
            "user_input": user_input,
            "orchestrator_id": str((prompt_bundle or {}).get("orchestrator_id") or session.orchestrator_id),
            "mode": str((prompt_bundle or {}).get("mode") or "provider"),
            "stage_id": str((prompt_bundle or {}).get("stage_id") or (stage or {}).get("stage_id") or ""),
            "provider_request": {
                "messages": list(request_messages or []),
                "prompt_bundle": safe_prompt_bundle,
            },
            "provider_response": {
                "raw_content": str(raw_content or ""),
                "parsed_json": payload,
            },
            "provider_normalized_output": normalized_output,
        }

    @staticmethod
    def _find_spec_node_static(nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            found = DeepSeekRequirementAnalysisClient._find_spec_node_static(list(node.get("children", [])), node_id)
            if found is not None:
                return found
        return None
