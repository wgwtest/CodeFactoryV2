from __future__ import annotations

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.input_normalizer import InputNormalizer


class RequirementAnalysisTurnAuditService:
    def __init__(self, normalizer: InputNormalizer | None = None) -> None:
        self.normalizer = normalizer or InputNormalizer()

    def decision_trace_seed(
        self,
        *,
        projection_spec_node: dict,
        normalized: dict,
        next_open_before_update: str | None,
        orchestrator: OrchestratorPackage,
    ) -> list[str]:
        orchestrator_label = (
            "强规则组织器"
            if orchestrator.orchestrator_id == "xg-strong-rule-orchestrator"
            else orchestrator.name
        )
        return [
            f"当前组织器：{orchestrator_label}（{orchestrator.orchestrator_id} / {orchestrator.mode}）。",
            "用户输入是本轮 Turn 起点。",
            f"本轮投影节点为 {projection_spec_node.get('node_id')} / {projection_spec_node.get('title')}。",
            f"投影目标章节为 {projection_spec_node.get('target_section')}。",
            f"本轮输入类型为 {normalized.get('input_type')}，语义摘要为：{normalized.get('semantic')}。",
            f"处理前第一个 open 叶子节点为 {next_open_before_update or '无'}。",
            "组织器规则：先更新结构化状态，再同步渲染临时正文和完成度树投影。",
        ]

    def previous_interaction(self, value: object, *, last_quick_options: list[dict]) -> dict:
        if not isinstance(value, dict):
            return {
                "interaction_id": None,
                "type": "none",
                "prompt": "无，用户自由发起。",
                "options": [],
                "target_spec_node_ids": [],
                "reason": "首轮或上轮没有系统留题。",
            }
        return {
            "interaction_id": value.get("interaction_id"),
            "type": str(value.get("type") or "suggestion"),
            "prompt": str(value.get("prompt") or ""),
            "options": self.normalizer.normalize_quick_options(value.get("options") or last_quick_options),
            "target_spec_node_ids": [
                str(item) for item in value.get("target_spec_node_ids", []) if str(item).strip()
            ]
            if isinstance(value.get("target_spec_node_ids"), list)
            else [],
            "reason": str(value.get("reason") or ""),
        }

    @staticmethod
    def state_changes(
        *,
        previous_questions: list[dict],
        updated_questions: list[dict],
        closed_spec_node_ids: list[str],
        next_active_spec_node_id: str | None,
    ) -> dict:
        previous_by_id = {question.get("question_id"): question for question in previous_questions}
        closed_question_ids = [
            str(question.get("question_id"))
            for question in updated_questions
            if question.get("status") == "confirmed"
            and previous_by_id.get(question.get("question_id"), {}).get("status") != "confirmed"
        ]
        created_question_ids = [
            str(question.get("question_id"))
            for question in updated_questions
            if question.get("question_id") not in previous_by_id
        ]
        return {
            "closed_question_ids": closed_question_ids,
            "created_question_ids": created_question_ids,
            "closed_spec_node_ids": closed_spec_node_ids,
            "next_active_spec_node_id": next_active_spec_node_id,
        }

    @staticmethod
    def spec_execution(
        *,
        model_output: dict,
        affected_spec_nodes: list[dict],
        state_changes: dict,
        working_document_update: dict,
    ) -> dict:
        return {
            "interpretation": model_output["organizer_interpretation"],
            "assistant_message": model_output["assistant_message"],
            "confirmed_facts": model_output["confirmed_facts_delta"],
            "affected_spec_nodes": affected_spec_nodes,
            "template_shape_assessment": model_output.get("template_shape_assessment", {}),
            "target_anchor_plan": model_output.get("target_anchor_plan", []),
            "document_patch": model_output["document_patch"],
            "working_document_update": working_document_update,
            "state_changes": state_changes,
            "annotations": model_output["annotations"],
            "risks": model_output["risks"],
        }

    @staticmethod
    def post_update_review(
        *,
        target_review: dict,
        global_review: dict,
    ) -> dict:
        return {
            "summary": f"{target_review.get('reason')} {global_review.get('summary')}".strip(),
            "target_review": target_review,
            "global_review": global_review,
        }

    @staticmethod
    def closure_decision(
        *,
        post_update_review: dict,
        closed_spec_node_ids: list[str],
    ) -> dict:
        target_review = post_update_review.get("target_review") or {}
        global_review = post_update_review.get("global_review") or {}
        status = "closed" if str(target_review.get("status") or "") in {"acceptable", "closed"} else "needs_followup"
        global_status = str(global_review.get("status") or "")
        if global_status == "continue_same_topic":
            next_action = "continue_same_topic"
        elif global_status == "whole_document_review":
            next_action = "whole_document_review"
        else:
            next_action = "propose_next_interaction"
        return {
            "status": status,
            "reason": (
                "本轮输入已被吸收，并形成需求规格正文建议；无需继续追问同一题。"
                if status == "closed"
                else "本轮已有回应，但尚未形成足够的需求规格正文建议，需要继续追问同一题。"
            ),
            "next_action": next_action,
        }

    @staticmethod
    def decision_trace(
        *,
        previous_interaction: dict,
        input_relation: dict,
        spec_execution: dict,
        post_update_review: dict,
        closure_decision: dict,
        next_interaction: dict,
        seed: list[str],
    ) -> list[str]:
        trace = list(seed)
        trace.append(f"读取上轮系统留题：{previous_interaction.get('type')} / {previous_interaction.get('prompt')}")
        trace.append(f"输入关系判定为 {input_relation.get('relation')}：{input_relation.get('reason')}")
        affected_labels = "、".join(
            str(node.get("target_section") or node.get("node_id"))
            for node in spec_execution.get("affected_spec_nodes", [])
        )
        trace.append(f"先执行结构化状态更新并同步规格投影：{affected_labels or '无'}。")
        working_document_update = spec_execution.get("working_document_update") or {}
        after_excerpt = working_document_update.get("after_excerpt") or working_document_update.get("after")
        if after_excerpt:
            trace.append(f"临时正文应用后内容：{after_excerpt}")
        trace.append(f"补充后回看：{post_update_review.get('summary')}")
        trace.append(
            f"本轮处理闭环：{closure_decision.get('status')}，下一步策略 {closure_decision.get('next_action')}。"
        )
        trace.append(f"下一轮交互设计：{next_interaction.get('type')} / {next_interaction.get('prompt')}")
        return trace
