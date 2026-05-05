from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkingDocumentUpdateResult:
    working_document: dict
    applied_section_ids: list[str]
    sections: list[dict]
    before: str
    after: str

    def to_dict(self) -> dict:
        return {
            "applied_section_ids": self.applied_section_ids,
            "sections": self.sections,
            "before": self.before,
            "after": self.after,
        }


class WorkingDocumentService:
    def initialize(self, *, topic: str, template_id: str) -> dict:
        return {
            "document_id": "lab-working-document",
            "title": f"{template_id}需求规格说明（Lab 临时正文）",
            "topic": topic,
            "sections": [],
        }

    def apply_patches(
        self,
        *,
        working_document: dict,
        document_patch: list[dict],
        patch_proposals: list[dict],
        projection_spec_node: dict,
        turn_id: str,
    ) -> WorkingDocumentUpdateResult:
        sections = list(working_document.get("sections", []))
        working_document["sections"] = sections

        target_section = str(projection_spec_node.get("target_section") or "未绑定模板章节")
        section_id = str(projection_spec_node.get("node_id") or target_section)
        current_section = self._find_or_create_section(
            sections=sections,
            section_id=section_id,
            target_section=target_section,
        )

        before_rendered = self._render_section(current_section)
        current_content = str(current_section.get("content") or "")
        patch_ids = self._current_patch_ids(
            patch_proposals=patch_proposals,
            target_section=target_section,
            turn_id=turn_id,
        )

        for patch in document_patch:
            content = str(patch.get("content") or "").strip()
            if not content:
                continue
            current_content = self._merge_content(current_content, content)

        current_section["content"] = current_content
        current_section["source_patch_ids"] = self._append_unique(
            list(current_section.get("source_patch_ids", [])),
            patch_ids,
        )
        current_section["last_turn_id"] = turn_id
        current_section["review_status"] = "waiting_review"
        current_section["review_reason"] = ""

        after_rendered = self._render_section(current_section)
        return WorkingDocumentUpdateResult(
            working_document=working_document,
            applied_section_ids=[section_id],
            sections=[
                {
                    "section_id": section_id,
                    "target_section": target_section,
                    "before": before_rendered,
                    "after": after_rendered,
                    "source_patch_ids": list(current_section.get("source_patch_ids", [])),
                    "last_turn_id": turn_id,
                }
            ],
            before=before_rendered,
            after=after_rendered,
        )

    def update_review_status(
        self,
        *,
        working_document: dict,
        section_id: str,
        review_status: str,
        review_reason: str,
    ) -> dict:
        section = self.find_section(working_document=working_document, section_id=section_id)
        if section is None:
            return working_document
        section["review_status"] = review_status
        section["review_reason"] = review_reason
        return working_document

    def find_section(self, *, working_document: dict, section_id: str) -> dict | None:
        for section in list(working_document.get("sections", [])):
            if str(section.get("section_id") or "") == section_id:
                return section
        return None

    def get_section_snapshot(self, *, working_document: dict, section_id: str) -> dict:
        section = self.find_section(working_document=working_document, section_id=section_id)
        if section is None:
            return {
                "section_id": section_id,
                "target_section": "未绑定模板章节",
                "content": "",
                "review_status": "missing",
                "review_reason": "当前章节尚未形成临时正文草稿。",
            }
        return {
            "section_id": str(section.get("section_id") or section_id),
            "target_section": str(section.get("target_section") or "未绑定模板章节"),
            "content": str(section.get("content") or ""),
            "review_status": str(section.get("review_status") or "waiting_review"),
            "review_reason": str(section.get("review_reason") or ""),
        }

    @staticmethod
    def _find_or_create_section(*, sections: list[dict], section_id: str, target_section: str) -> dict:
        for section in sections:
            if str(section.get("section_id") or "") == section_id:
                return section
        created = {
            "section_id": section_id,
            "target_section": target_section,
            "content": "",
            "source_patch_ids": [],
            "last_turn_id": None,
            "review_status": "waiting_review",
            "review_reason": "",
        }
        sections.append(created)
        return created

    @staticmethod
    def _merge_content(previous: str, new_content: str) -> str:
        normalized_previous = previous.strip()
        normalized_new = new_content.strip()
        if not normalized_previous:
            return normalized_new
        if normalized_new in normalized_previous:
            return normalized_previous
        return f"{normalized_previous}\n{normalized_new}"

    @staticmethod
    def _append_unique(current: list[str], additions: list[str]) -> list[str]:
        result = list(current)
        for item in additions:
            if item and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _render_section(section: dict) -> str:
        target_section = str(section.get("target_section") or "未绑定模板章节")
        content = str(section.get("content") or "").strip()
        if not content:
            return ""
        return f"{target_section}\n{content}"

    @staticmethod
    def _current_patch_ids(*, patch_proposals: list[dict], target_section: str, turn_id: str) -> list[str]:
        result: list[str] = []
        for patch in patch_proposals:
            if str(patch.get("source_turn_id") or "") != turn_id:
                continue
            if str(patch.get("target_section") or "") != target_section:
                continue
            patch_id = str(patch.get("patch_id") or "").strip()
            if patch_id:
                result.append(patch_id)
        return result
