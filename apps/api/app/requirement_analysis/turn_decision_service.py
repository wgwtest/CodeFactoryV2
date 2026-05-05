from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurnDecisionResult:
    closure_decision: dict
    next_interaction: dict
    decision_trace: list[str]

    def to_dict(self) -> dict:
        return {
            "closure_decision": self.closure_decision,
            "next_interaction": self.next_interaction,
            "decision_trace": list(self.decision_trace),
        }


class TurnDecisionService:
    @staticmethod
    def build_closure_decision(*, post_update_review: dict) -> dict:
        target_review = dict(post_update_review.get("target_review") or {})
        global_review = dict(post_update_review.get("global_review") or {})
        target_status = str(target_review.get("status") or "")
        status = "closed" if target_status in {"acceptable", "closed"} else "needs_followup"
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

    def decide(
        self,
        *,
        normalized_input: dict,
        working_document_update: dict,
        post_update_review: dict,
        projection: dict,
        next_interaction: dict,
        base_trace: list[str] | None = None,
        closed_spec_node_ids: list[str] | None = None,
    ) -> TurnDecisionResult:
        closure_decision = self.build_closure_decision(post_update_review=post_update_review)
        trace = list(base_trace or [])
        trace.append("正文已应用后再进行回看，回看结果用于本轮闭环判断。")
        trace.append(
            f"闭环输入摘要：{normalized_input.get('semantic') or ''}；投影节点：{projection.get('projection_spec_node_id') or '未绑定'}。"
        )
        if working_document_update.get("after_excerpt"):
            trace.append(f"本轮临时正文证据：{working_document_update.get('after_excerpt')}")
        if closed_spec_node_ids:
            trace.append(f"本轮关闭规格节点：{', '.join(closed_spec_node_ids)}。")
        return TurnDecisionResult(
            closure_decision=closure_decision,
            next_interaction=next_interaction,
            decision_trace=trace,
        )
