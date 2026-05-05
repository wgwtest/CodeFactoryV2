from __future__ import annotations

from app.requirement_analysis.working_document_service import WorkingDocumentService


class WorkingDocumentReviewService:
    def __init__(self, *, working_document_service: WorkingDocumentService) -> None:
        self.working_document_service = working_document_service

    def review(
        self,
        *,
        working_document: dict,
        review_target_paths: list[str],
        current_spec_node: dict,
    ) -> dict:
        target_snapshot = self.working_document_service.build_review_target(
            working_document=working_document,
            anchor_paths=review_target_paths,
        )
        excerpt = str(target_snapshot.get("excerpt") or "").strip()
        missing_aspects = []
        question = str(current_spec_node.get("question") or "").strip()
        if question and not excerpt:
            missing_aspects.append(question)

        if not excerpt:
            target_review = {
                "status": "insufficient",
                "review_target": list(target_snapshot.get("review_target_paths") or review_target_paths),
                "reason": "当前目标范围尚未形成可审查的正文。",
                "missing_aspects": missing_aspects or ["缺少正文内容"],
            }
        else:
            target_review = {
                "status": "acceptable",
                "review_target": list(target_snapshot.get("review_target_paths") or review_target_paths),
                "reason": "当前目标范围已具备可接受表达。",
                "missing_aspects": [],
            }

        global_review = self.build_global_review(
            next_spec_node={},
            target_review=target_review,
        )
        return {
            "target_review": target_review,
            "global_review": global_review,
        }

    @staticmethod
    def build_global_review(*, next_spec_node: dict, target_review: dict) -> dict:
        if str(target_review.get("status") or "") == "insufficient":
            return {
                "status": "continue_same_topic",
                "summary": "当前目标范围仍需继续补充，暂不切换到下一节点。",
                "remaining_gaps": list(target_review.get("missing_aspects") or [target_review.get("reason")]),
            }
        if next_spec_node.get("node_id"):
            next_gap = str(next_spec_node.get("question") or next_spec_node.get("title") or "")
            return {
                "status": "move_next_node",
                "summary": f"下一处缺口位于 {next_spec_node.get('target_section')}.",
                "remaining_gaps": [next_gap] if next_gap else [],
            }
        return {
            "status": "whole_document_review",
            "summary": "当前完成度树暂无待确认节点，可以进入整体复核。",
            "remaining_gaps": [],
        }
