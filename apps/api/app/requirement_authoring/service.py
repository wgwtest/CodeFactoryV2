from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument, RequirementAuthoringTemplate
from app.requirement_authoring.models import (
    RequirementAuthoringDocumentCreate,
    RequirementAuthoringFormPatch,
    RequirementAuthoringMessageWrite,
    RequirementAuthoringTemplateWrite,
    default_template_payload,
)


class RequirementAuthoringService:
    def __init__(self, session) -> None:
        self.session = session

    def list_templates(self) -> list[dict]:
        self._ensure_default_templates()
        templates = self.session.scalars(
            select(RequirementAuthoringTemplate).order_by(RequirementAuthoringTemplate.template_code)
        ).all()
        return [self._serialize_template(template) for template in templates]

    def create_template(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        template_payload = self._template_payload_from_write(payload)
        template = RequirementAuthoringTemplate(
            template_code=payload.template_code.strip(),
            name=payload.name.strip() or payload.template_code.strip(),
            status=payload.status,
            payload=template_payload,
        )
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return self._serialize_template(template)

    def update_template(self, template_id: str, payload: RequirementAuthoringTemplateWrite) -> dict | None:
        template = self.session.get(RequirementAuthoringTemplate, template_id)
        if template is None:
            return None

        template.template_code = payload.template_code.strip()
        template.name = payload.name.strip() or payload.template_code.strip()
        template.status = payload.status
        template.payload = self._template_payload_from_write(payload)
        self.session.commit()
        self.session.refresh(template)
        return self._serialize_template(template)

    def activate_template(self, template_id: str) -> dict | None:
        template = self.session.get(RequirementAuthoringTemplate, template_id)
        if template is None:
            return None

        template.status = "active"
        self.session.commit()
        self.session.refresh(template)
        return self._serialize_template(template)

    def list_documents(self) -> list[dict]:
        documents = self.session.scalars(
            select(RequirementAuthoringDocument).order_by(RequirementAuthoringDocument.updated_at.desc())
        ).all()
        return [self._serialize_document_summary(document) for document in documents]

    def create_document(self, payload: RequirementAuthoringDocumentCreate) -> dict:
        self._ensure_default_templates()
        template = self.session.get(RequirementAuthoringTemplate, payload.template_id)
        if template is None:
            raise ValueError("template not found")

        fields = self._initial_fields()
        semantic_state = self._build_semantic_state(fields, template)
        document_body = self._render_document(template.payload, fields)
        annotations = self._build_annotations(template.payload, fields)
        conversation = [
            {
                "id": "msg-1",
                "role": "assistant",
                "content": "我会按标准规格骨架持续起草和修补。你可以直接回：可以 / 更正式 / 加超时 / 重拟 / 继续。",
                "created_at": self._now(),
            }
        ]
        document = RequirementAuthoringDocument(
            title=payload.title.strip() or "未命名需求规格说明",
            template_id=template.id,
            status="draft",
            layout_ratio=payload.layout_ratio,
            archive_ids=payload.archive_ids,
            semantic_state=semantic_state,
            document=document_body,
            conversation=conversation,
            annotations=annotations,
            check_result=self._empty_check_result(),
            frozen_package=None,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def get_document(self, document_id: str) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        return self._serialize_document_detail(document)

    def append_message(self, document_id: str, payload: RequirementAuthoringMessageWrite) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")

        template = self._get_document_template(document)
        fields = dict(document.semantic_state.get("fields", {}))
        user_content = payload.content.strip()
        normalized = user_content.lower()

        if "超时" in user_content:
            fields["exception_flow"] = "包含超时提醒和人工确认，不扩展复杂补偿链路。"
        elif "更正式" in user_content:
            fields["normal_flow"] = self._formalize_sentence(fields.get("normal_flow", ""))
        elif "重拟" in user_content:
            fields["normal_flow"] = "系统应支持创建、校验、协同确认和归档核心业务记录。"
        elif user_content and normalized not in {"a", "b", "c", "可以", "继续"}:
            fields["normal_flow"] = user_content
        elif not fields.get("main_process"):
            fields["main_process"] = "待确认核心业务流程"

        assistant_content = self._build_assistant_reply(fields, user_content)
        conversation = list(document.conversation)
        next_index = len(conversation) + 1
        conversation.extend(
            [
                {"id": f"msg-{next_index}", "role": "user", "content": user_content, "created_at": self._now()},
                {
                    "id": f"msg-{next_index + 1}",
                    "role": "assistant",
                    "content": assistant_content,
                    "created_at": self._now(),
                },
            ]
        )

        self._write_document_state(document, template, fields)
        document.conversation = conversation
        document.status = "draft"
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def patch_form_fields(self, document_id: str, payload: RequirementAuthoringFormPatch) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")

        template = self._get_document_template(document)
        fields = dict(document.semantic_state.get("fields", {}))
        for key, value in payload.fields.items():
            fields[key] = value.strip()
        self._write_document_state(document, template, fields)
        document.status = "draft"
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def patch_clause(self, document_id: str, clause_id: str, content: str) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")

        next_document = {
            **document.document,
            "sections": [
                {
                    **section,
                    "clauses": [
                        {
                            **clause,
                            "content": content.strip(),
                            "status": "pending_mapping" if clause["clause_id"] == clause_id else clause.get("status", "missing"),
                        }
                        if clause["clause_id"] == clause_id
                        else clause
                        for clause in section.get("clauses", [])
                    ],
                }
                for section in document.document.get("sections", [])
            ],
        }
        document.document = next_document
        document.annotations = [
            {
                **annotation,
                "pending_confirmations": ["正文已轻量编辑，结构化映射待确认。"],
            }
            if annotation["clause_id"] == clause_id
            else annotation
            for annotation in document.annotations
        ]
        document.status = "draft"
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def run_check(self, document_id: str) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None

        template = self._get_document_template(document)
        fields = document.semantic_state.get("fields", {})
        required_fields = template.payload.get("gap_rules", {}).get("required_fields", [])
        form_labels = self._form_labels(template.payload)
        blocking_items = [
            {
                "severity": "blocking",
                "field_key": field_key,
                "clause_id": self._field_clause_id(template.payload, field_key),
                "message": f"{form_labels.get(field_key, field_key)} 缺少确认内容。",
            }
            for field_key in required_fields
            if not fields.get(field_key)
        ]
        passed_count = max(len(required_fields) - len(blocking_items), 0)
        check_result = {
            "blocking_count": len(blocking_items),
            "warning_count": 0,
            "passed_count": passed_count,
            "items": blocking_items,
        }
        document.check_result = check_result
        document.status = "ready_to_freeze" if not blocking_items else "checking"
        document.annotations = self._build_annotations(template.payload, fields, blocking_items)
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def freeze(self, document_id: str) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status != "ready_to_freeze":
            self.run_check(document_id)
            self.session.refresh(document)
        if document.check_result.get("blocking_count", 0) > 0:
            raise ValueError("document has blocking gaps")

        fields = document.semantic_state.get("fields", {})
        frozen_package = {
            "p3_consumable": True,
            "frozen_at": self._now(),
            "standard_document": document.document,
            "annotations": document.annotations,
            "structured_spec": self._build_structured_spec(fields, document.archive_ids),
        }
        document.status = "frozen"
        document.frozen_package = frozen_package
        self.session.commit()
        self.session.refresh(document)
        return self._serialize_document_detail(document)

    def _ensure_default_templates(self) -> None:
        existing_codes = {
            template.template_code
            for template in self.session.scalars(select(RequirementAuthoringTemplate)).all()
        }
        for template_code, name in [
            ("81433", "软件级需求规格说明模板"),
            ("82259", "平台级需求规格说明模板"),
        ]:
            if template_code in existing_codes:
                continue
            self.session.add(
                RequirementAuthoringTemplate(
                    id=f"tpl-{template_code}-default",
                    template_code=template_code,
                    name=name,
                    status="active",
                    payload=default_template_payload(template_code),
                )
            )
        self.session.commit()

    def _template_payload_from_write(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        base_payload = default_template_payload(payload.template_code)
        if payload.sections is not None:
            base_payload["sections"] = payload.sections
        if payload.form_groups is not None:
            base_payload["form_groups"] = payload.form_groups
        if payload.field_mappings is not None:
            base_payload["field_mappings"] = payload.field_mappings
        if payload.questionnaire_policy is not None:
            base_payload["questionnaire_policy"] = payload.questionnaire_policy
        if payload.gap_rules is not None:
            base_payload["gap_rules"] = payload.gap_rules
        if payload.knowledge_bindings is not None:
            base_payload["knowledge_bindings"] = payload.knowledge_bindings
        base_payload["description"] = payload.description
        return base_payload

    def _get_document_template(self, document: RequirementAuthoringDocument) -> RequirementAuthoringTemplate:
        template = self.session.get(RequirementAuthoringTemplate, document.template_id)
        if template is None:
            raise ValueError("template not found")
        return template

    def _write_document_state(
        self,
        document: RequirementAuthoringDocument,
        template: RequirementAuthoringTemplate,
        fields: dict[str, str],
    ) -> None:
        document.semantic_state = self._build_semantic_state(fields, template)
        document.document = self._render_document(template.payload, fields)
        document.annotations = self._build_annotations(template.payload, fields)
        document.check_result = self._empty_check_result()

    def _initial_fields(self) -> dict[str, str]:
        return {
            "application_name": "",
            "domain_scope": "",
            "target_users": "",
            "main_process": "",
            "normal_flow": "",
            "exception_flow": "",
            "acceptance_criteria": "",
            "non_functional": "",
        }

    def _build_semantic_state(self, fields: dict[str, str], template: RequirementAuthoringTemplate) -> dict:
        return {
            "template_id": template.id,
            "template_code": template.template_code,
            "fields": fields,
            "updated_at": self._now(),
        }

    def _render_document(self, template_payload: dict, fields: dict[str, str]) -> dict:
        return {
            "title": fields.get("application_name") or "标准需求规格说明",
            "sections": [
                {
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "clauses": [self._render_clause(clause, fields) for clause in section.get("clauses", [])],
                }
                for section in template_payload.get("sections", [])
            ],
        }

    def _render_clause(self, clause: dict, fields: dict[str, str]) -> dict:
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

    def _render_text(self, fields: dict[str, str], required: list[str], text: str, fallback: str) -> str:
        if any(not fields.get(field_key) for field_key in required):
            return fallback
        return text

    def _build_annotations(
        self,
        template_payload: dict,
        fields: dict[str, str],
        blocking_items: list[dict] | None = None,
    ) -> list[dict]:
        blocking_by_clause = {item["clause_id"]: item for item in blocking_items or []}
        field_mappings = template_payload.get("field_mappings", [])
        annotations = []
        for section in template_payload.get("sections", []):
            for clause in section.get("clauses", []):
                clause_id = clause["clause_id"]
                mappings = [item for item in field_mappings if item.get("clause_id") == clause_id]
                annotations.append(
                    {
                        "clause_id": clause_id,
                        "title": clause["title"],
                        "interpretation": f"{clause['title']}用于约束标准规格正文与后台语义字段的一致性。",
                        "source_refs": [
                            binding["label"]
                            for binding in template_payload.get("knowledge_bindings", [])
                            if binding.get("enabled", True)
                        ],
                        "semantic_mapping": mappings,
                        "p3_mapping": [item.get("structured_path") for item in mappings],
                        "gaps": [blocking_by_clause[clause_id]["message"]] if clause_id in blocking_by_clause else [],
                        "pending_confirmations": []
                        if any(fields.get(field_key) for field_key in clause.get("field_keys", []))
                        else ["该条款仍需专家确认。"],
                    }
                )
        return annotations

    def _build_assistant_reply(self, fields: dict[str, str], user_content: str) -> str:
        if "超时" in user_content:
            return "已补入一个克制版超时提醒，不扩展复杂补偿链路。你可以直接回：可以 / 更正式 / 重拟。"
        if fields.get("normal_flow"):
            return "我已把这句业务事实并入核心流程草稿。你可以直接回：可以 / 加超时 / 更正式 / 继续。"
        return "我会继续补齐缺口，优先处理功能需求和验收准则。你可以直接回：可以 / A / B / 重拟。"

    def _formalize_sentence(self, value: str) -> str:
        if not value:
            return "系统应支持核心业务流程的创建、校验、协同确认与结果留痕。"
        return f"系统应支持{value.rstrip('。')}，并形成可审计的处理记录。"

    def _build_structured_spec(self, fields: dict[str, str], archive_ids: list[str]) -> dict:
        return {
            "application": {
                "name": fields.get("application_name", ""),
                "domain": fields.get("domain_scope", ""),
                "summary": fields.get("normal_flow", ""),
                "target_users": [item.strip() for item in fields.get("target_users", "").replace("、", ",").split(",") if item.strip()],
            },
            "objects": [],
            "processes": [
                {
                    "id": "process-main",
                    "name": fields.get("main_process", ""),
                    "process_kind": "collaboration",
                    "source_kind": "temporary",
                    "description": fields.get("normal_flow", ""),
                    "participant_object_ids": [],
                    "source_archive_id": archive_ids[0] if archive_ids else None,
                    "source_item_type": None,
                    "source_item_id": None,
                }
            ],
            "rules": [{"id": "rule-exception-flow", "name": "异常流程", "description": fields.get("exception_flow", "")}],
            "metrics": [{"id": "metric-acceptance", "name": "验收准则", "description": fields.get("acceptance_criteria", "")}],
            "non_functional_constraints": [
                {
                    "id": "constraint-performance",
                    "name": "性能与可靠性",
                    "category": "quality",
                    "description": fields.get("non_functional", ""),
                }
            ],
        }

    def _form_labels(self, template_payload: dict) -> dict[str, str]:
        labels = {}
        for group in template_payload.get("form_groups", []):
            for field in group.get("fields", []):
                labels[field["field_key"]] = field["label"]
        return labels

    def _field_clause_id(self, template_payload: dict, field_key: str) -> str:
        for group in template_payload.get("form_groups", []):
            for field in group.get("fields", []):
                if field["field_key"] == field_key:
                    return field["clause_id"]
        return "REQ-1.1"

    def _empty_check_result(self) -> dict:
        return {"blocking_count": 0, "warning_count": 0, "passed_count": 0, "items": []}

    def _serialize_template(self, template: RequirementAuthoringTemplate) -> dict:
        return {
            "template_id": template.id,
            "template_code": template.template_code,
            "name": template.name,
            "status": template.status,
            "description": template.payload.get("description", ""),
            "sections": template.payload.get("sections", []),
            "form_groups": template.payload.get("form_groups", []),
            "field_mappings": template.payload.get("field_mappings", []),
            "questionnaire_policy": template.payload.get("questionnaire_policy", {}),
            "gap_rules": template.payload.get("gap_rules", {}),
            "knowledge_bindings": template.payload.get("knowledge_bindings", []),
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    def _serialize_document_summary(self, document: RequirementAuthoringDocument) -> dict:
        return {
            "document_id": document.id,
            "title": document.title,
            "template_id": document.template_id,
            "status": document.status,
            "layout_ratio": document.layout_ratio,
            "archive_ids": document.archive_ids,
            "updated_at": document.updated_at.isoformat(),
        }

    def _serialize_document_detail(self, document: RequirementAuthoringDocument) -> dict:
        return {
            **self._serialize_document_summary(document),
            "created_at": document.created_at.isoformat(),
            "semantic_state": document.semantic_state,
            "document": document.document,
            "conversation": document.conversation,
            "annotations": document.annotations,
            "check_result": document.check_result,
            "frozen_package": document.frozen_package,
        }

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
