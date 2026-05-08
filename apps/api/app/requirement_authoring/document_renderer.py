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
            "REQ-1.2": self._render_text(
                fields,
                ["application_scope", "target_users"],
                f"本文档适用于{fields.get('application_scope')}，主要服务对象为{fields.get('target_users')}。",
                "待补齐：适用范围和目标用户。",
            ),
            "REQ-1.3": self._render_text(
                fields,
                ["terms_glossary"],
                fields.get("terms_glossary", ""),
                "待补齐：术语与缩略语。",
            ),
            "REQ-2.1": self._render_text(
                fields,
                ["application_name", "domain_scope", "target_users"],
                f"{fields.get('application_name')}面向{fields.get('domain_scope')}，服务于{fields.get('target_users')}。",
                "待补齐：软件定位、领域范围和目标用户。",
            ),
            "REQ-2.2": self._render_text(
                fields,
                ["business_goals"],
                self._join_sentences([fields.get("business_goals", ""), fields.get("expected_value", "")]),
                "待补齐：建设目标和预期价值。",
            ),
            "REQ-2.3": self._render_text(
                fields,
                ["main_scenarios", "usage_modes"],
                f"主要使用场景包括：{fields.get('main_scenarios')}；主要使用模式为：{fields.get('usage_modes')}",
                "待补齐：主要使用场景和使用模式。",
            ),
            "REQ-2.4": self._render_text(
                fields,
                ["in_scope", "out_of_scope"],
                f"本阶段纳入范围包括：{fields.get('in_scope')}；明确不纳入范围的内容包括：{fields.get('out_of_scope')}",
                "待补齐：纳入范围和排除范围。",
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
                ["situational_display"],
                fields.get("situational_display", ""),
                "待补齐：态势展示与浏览能力。",
            ),
            "REQ-3.4": self._render_text(
                fields,
                ["gis_analysis_tools"],
                fields.get("gis_analysis_tools", ""),
                "待补齐：空间分析工具能力。",
            ),
            "REQ-3.5": self._render_text(
                fields,
                ["deployment_analysis"],
                fields.get("deployment_analysis", ""),
                "待补齐：部署分析能力。",
            ),
            "REQ-3.6": self._render_text(
                fields,
                ["result_outputs", "collaboration_mode"],
                f"系统应支持以下结果输出：{fields.get('result_outputs')}；协同与共享方式包括：{fields.get('collaboration_mode')}",
                "待补齐：结果输出与共享方式。",
            ),
            "REQ-3.7": self._render_text(
                fields,
                ["exception_flow"],
                self._join_sentences([fields.get("exception_flow", ""), fields.get("fallback_rules", "")]),
                "待补齐：异常流程和补偿策略。",
            ),
            "REQ-4.1": self._render_text(
                fields,
                ["input_data_sources", "input_data_mode"],
                f"系统输入数据来源包括：{fields.get('input_data_sources')}；输入模式为：{fields.get('input_data_mode')}",
                "待补齐：输入数据来源和输入模式。",
            ),
            "REQ-4.2": self._render_text(
                fields,
                ["output_data_products"],
                fields.get("output_data_products", ""),
                "待补齐：输出数据与报表。",
            ),
            "REQ-4.3": self._render_text(
                fields,
                ["external_interfaces"],
                fields.get("external_interfaces", ""),
                "待补齐：外部接口。",
            ),
            "REQ-5.1": self._render_text(
                fields,
                ["performance_requirements", "reliability_requirements"],
                f"性能要求包括：{fields.get('performance_requirements')}；可靠性要求包括：{fields.get('reliability_requirements')}",
                "待补齐：性能与可靠性要求。",
            ),
            "REQ-5.2": self._render_text(
                fields,
                ["security_requirements", "permission_model"],
                f"安全要求包括：{fields.get('security_requirements')}；权限模型包括：{fields.get('permission_model')}",
                "待补齐：安全要求和权限模型。",
            ),
            "REQ-5.3": self._render_text(
                fields,
                ["deployment_environment"],
                fields.get("deployment_environment", ""),
                "待补齐：部署与运行环境。",
            ),
            "REQ-5.4": self._render_text(
                fields,
                ["accuracy_constraints"],
                self._join_sentences([fields.get("accuracy_constraints", ""), fields.get("quality_constraints", "")]),
                "待补齐：精度与质量约束。",
            ),
            "REQ-6.1": self._render_text(
                fields,
                ["acceptance_scenarios"],
                fields.get("acceptance_scenarios", ""),
                "待补齐：验收场景。",
            ),
            "REQ-6.2": self._render_text(
                fields,
                ["acceptance_criteria"],
                fields.get("acceptance_criteria", ""),
                "待补齐：验收准则。",
            ),
            "REQ-6.3": self._render_text(
                fields,
                ["open_decision_items"],
                fields.get("open_decision_items", ""),
                "待补齐：待确认事项。",
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

    @staticmethod
    def _join_sentences(parts: list[str]) -> str:
        normalized = [part.strip() for part in parts if part and part.strip()]
        return "；".join(normalized)
