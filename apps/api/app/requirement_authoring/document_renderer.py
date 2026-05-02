from __future__ import annotations


class RequirementDocumentRenderer:
    def render_document(self, template_payload: dict, fields: dict[str, str]) -> dict:
        return {
            "title": self.standard_document_title(fields),
            "sections": [
                {
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "clauses": [self.render_clause(clause, fields) for clause in section.get("clauses", [])],
                }
                for section in template_payload.get("sections", [])
            ],
        }

    def patch_clause(self, document_body: dict, clause_id: str, content: str) -> dict:
        return {
            **document_body,
            "sections": [
                {
                    **section,
                    "clauses": [
                        {
                            **clause,
                            "content": content.strip(),
                            "status": "pending_mapping"
                            if clause["clause_id"] == clause_id
                            else clause.get("status", "missing"),
                        }
                        if clause["clause_id"] == clause_id
                        else clause
                        for clause in section.get("clauses", [])
                    ],
                }
                for section in document_body.get("sections", [])
            ],
        }

    def standard_document_title(self, fields: dict[str, str]) -> str:
        application_name = fields.get("application_name", "").strip()
        if not application_name:
            return "标准需求规格说明"
        if application_name.endswith("需求规格说明"):
            return application_name
        return f"{application_name}需求规格说明"

    def render_clause(self, clause: dict, fields: dict[str, str]) -> dict:
        clause_id = clause["clause_id"]
        content_by_clause = {
            "REQ-1.1": self._render_text(
                fields,
                ["application_name", "domain_scope"],
                f"本文档用于定义{fields.get('application_name') or '该软件'}在{fields.get('domain_scope') or '目标领域'}内的需求边界、功能行为和验收准则。",
                "待补齐：软件名称和领域范围。",
            ),
            "REQ-2.1": self._render_text(
                fields,
                ["application_name", "domain_scope", "target_users"],
                f"{fields.get('application_name')}面向{fields.get('domain_scope')}，服务于{fields.get('target_users')}。",
                "待补齐：软件定位、领域范围和目标用户。",
            ),
            "REQ-3.1": self._render_text(
                fields,
                ["target_users"],
                f"本软件的主要使用对象包括：{fields.get('target_users')}。",
                "待补齐：目标用户、角色和职责。",
            ),
            "REQ-3.2": self._render_text(
                fields,
                ["main_process", "normal_flow"],
                f"核心流程为{fields.get('main_process')}；正常流程包括：{fields.get('normal_flow')}",
                "待补齐：核心业务流程和正常流程。",
            ),
            "REQ-3.3": self._render_text(
                fields,
                ["exception_flow"],
                fields.get("exception_flow", ""),
                "待补齐：异常流程、超时和补偿策略。",
            ),
            "REQ-4.1": self._render_text(
                fields,
                ["non_functional"],
                fields.get("non_functional", ""),
                "待补齐：性能、可靠性和可追溯要求。",
            ),
            "REQ-5.1": self._render_text(
                fields,
                ["acceptance_criteria"],
                fields.get("acceptance_criteria", ""),
                "待补齐：验收准则。",
            ),
        }
        content = content_by_clause.get(clause_id, "待补齐：条款正文。")
        return {
            "clause_id": clause_id,
            "title": clause["title"],
            "content": content,
            "status": "missing" if content.startswith("待补齐") else "synced",
        }

    @staticmethod
    def _render_text(fields: dict[str, str], required: list[str], text: str, fallback: str) -> str:
        if any(not fields.get(field_key) for field_key in required):
            return fallback
        return text
