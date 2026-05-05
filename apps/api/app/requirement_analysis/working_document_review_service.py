from __future__ import annotations

from app.requirement_analysis.working_document_service import WorkingDocumentService


class WorkingDocumentReviewService:
    def __init__(self, *, working_document_service: WorkingDocumentService) -> None:
        self.working_document_service = working_document_service

    def review_section(
        self,
        *,
        working_document: dict,
        section_id: str,
        current_spec_node: dict,
    ) -> dict:
        snapshot = self.working_document_service.get_section_snapshot(
            working_document=working_document,
            section_id=section_id,
        )
        content = str(snapshot.get("content") or "").strip()
        target_section = str(snapshot.get("target_section") or current_spec_node.get("target_section") or "未绑定模板章节")
        missing_aspects = []
        if current_spec_node.get("question"):
            missing_aspects.append(str(current_spec_node["question"]))

        if not content:
            reason = "当前章节尚未形成临时正文草稿。"
            status = "insufficient"
        else:
            reason = "当前章节已具备可接受表达。"
            status = "acceptable"
            missing_aspects = []

        self.working_document_service.update_review_status(
            working_document=working_document,
            section_id=section_id,
            review_status=status,
            review_reason=reason,
        )
        return {
            "section_id": section_id,
            "target_section": target_section,
            "status": status,
            "reason": reason,
            "missing_aspects": missing_aspects,
        }

    @staticmethod
    def build_global_review(*, next_spec_node: dict, section_review: dict) -> dict:
        if str(section_review.get("status") or "") == "insufficient":
            return {
                "status": "continue_same_section",
                "summary": "当前章节仍需继续补充，暂不切换到下一节点。",
                "remaining_gaps": list(section_review.get("missing_aspects") or [section_review.get("reason")]),
            }
        if next_spec_node.get("node_id"):
            next_gap = str(next_spec_node.get("question") or next_spec_node.get("title") or "")
            return {
                "status": "move_next_node",
                "summary": f"下一处缺口位于 {next_spec_node.get('target_section')}。",
                "remaining_gaps": [next_gap] if next_gap else [],
            }
        return {
            "status": "whole_document_review",
            "summary": "当前完成度树暂无待确认节点，可以进入整体复核。",
            "remaining_gaps": [],
        }
