from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.requirements import RequirementAuthoringDocument, RequirementAuthoringTemplate
from app.requirement_authoring.annotation_service import RequirementAnnotationService
from app.requirement_authoring.document_repository import RequirementAuthoringRepository
from app.requirement_authoring.document_renderer import RequirementDocumentRenderer
from app.requirement_authoring.freeze_service import RequirementFreezeService
from app.requirement_authoring.gap_checker import RequirementGapChecker
from app.requirement_authoring.models import (
    RequirementAuthoringDocumentCreate,
    RequirementAuthoringDocumentSave,
    RequirementAuthoringFormPatch,
    RequirementAuthoringMessageWrite,
    RequirementAuthoringTemplateWrite,
    default_template_payload,
)
from app.xx_p1_sim.service import XXP1SimService


class RequirementAuthoringService:
    def __init__(self, session) -> None:
        self.session = session
        self.repository = RequirementAuthoringRepository(session)
        self.document_renderer = RequirementDocumentRenderer()
        self.annotation_service = RequirementAnnotationService()
        self.gap_checker = RequirementGapChecker()
        self.freeze_service = RequirementFreezeService()

    def list_templates(self) -> list[dict]:
        self._ensure_default_templates()
        templates = self.repository.list_templates()
        return [self._serialize_template(template) for template in templates]

    def create_template(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        template_payload = self._template_payload_from_write(payload)
        template = RequirementAuthoringTemplate(
            template_code=payload.template_code.strip(),
            name=payload.name.strip() or payload.template_code.strip(),
            status=payload.status,
            payload=template_payload,
        )
        return self._serialize_template(self.repository.add_template(template))

    def update_template(self, template_id: str, payload: RequirementAuthoringTemplateWrite) -> dict | None:
        template = self.repository.get_template(template_id)
        if template is None:
            return None

        template.template_code = payload.template_code.strip()
        template.name = payload.name.strip() or payload.template_code.strip()
        template.status = payload.status
        template.payload = self._template_payload_from_write(payload)
        return self._serialize_template(self.repository.save_template(template))

    def activate_template(self, template_id: str) -> dict | None:
        template = self.repository.get_template(template_id)
        if template is None:
            return None

        template.status = "active"
        return self._serialize_template(self.repository.save_template(template))

    def list_documents(self) -> list[dict]:
        documents = self.repository.list_documents()
        return [self._serialize_document_summary(document) for document in documents]

    def create_document(self, payload: RequirementAuthoringDocumentCreate) -> dict:
        self._ensure_default_templates()
        template = self.repository.get_template(payload.template_id)
        if template is None:
            raise ValueError("template not found")

        fields = self._initial_fields()
        semantic_state = self._build_semantic_state(fields, template)
        document_body = self.document_renderer.render_document(template.payload, fields)
        annotations = self.annotation_service.build_annotations(template.payload, fields)
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
            check_result=self.gap_checker.empty_check_result(),
            frozen_package=None,
        )
        return self._serialize_document_detail(self.repository.add_document(document))

    def list_knowledge_providers(self) -> dict:
        provider = XXP1SimService().build_requirement_authoring_provider()
        return {"items": [provider]}

    def bind_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        return XXP1SimService().bind_requirement_authoring_knowledge(provider_id, domain_id)

    def get_document(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        return self._serialize_document_detail(document)

    def delete_document(self, document_id: str) -> bool:
        document = self.repository.get_document(document_id)
        if document is None:
            return False
        self.repository.delete_document(document)
        return True

    def save_document(self, document_id: str, payload: RequirementAuthoringDocumentSave) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        if document.status != "frozen":
            document.status = "draft"
        if payload.title is not None:
            document.title = payload.title.strip() or "未命名软件需求规格说明"
        template = self._get_document_template(document)
        if payload.template_id is not None and payload.template_id != document.template_id:
            next_template = self.repository.get_template(payload.template_id)
            if next_template is None:
                raise ValueError("template not found")
            document.template_id = next_template.id
            template = next_template
            fields = dict((document.semantic_state or {}).get("fields", {}))
            document.document = self.document_renderer.render_document(template.payload, fields)
            document.annotations = self.annotation_service.build_annotations(template.payload, fields)
            document.check_result = self.gap_checker.empty_check_result()
        if payload.archive_ids is not None:
            document.archive_ids = payload.archive_ids
        semantic_state = dict(document.semantic_state or {})
        if "knowledge_binding" in payload.model_fields_set:
            semantic_state["knowledge_binding"] = payload.knowledge_binding
        elif "knowledge_binding" not in semantic_state:
            semantic_state["knowledge_binding"] = None
        semantic_state["template_id"] = template.id
        semantic_state["template_code"] = template.template_code
        semantic_state["updated_at"] = self._now()
        document.semantic_state = semantic_state
        document.document = dict(document.document or {})
        document.conversation = list(document.conversation or [])
        document.annotations = list(document.annotations or [])
        document.check_result = dict(document.check_result or {})
        return self._serialize_document_detail(self.repository.save_document(document))

    def append_message(self, document_id: str, payload: RequirementAuthoringMessageWrite) -> dict | None:
        document = self.repository.get_document(document_id)
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
        return self._serialize_document_detail(self.repository.save_document(document))

    def patch_form_fields(self, document_id: str, payload: RequirementAuthoringFormPatch) -> dict | None:
        document = self.repository.get_document(document_id)
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
        return self._serialize_document_detail(self.repository.save_document(document))

    def patch_clause(self, document_id: str, clause_id: str, content: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")

        document.document = self.document_renderer.patch_clause(document.document, clause_id, content)
        document.annotations = self.annotation_service.mark_clause_pending_mapping(document.annotations, clause_id)
        document.status = "draft"
        return self._serialize_document_detail(self.repository.save_document(document))

    def run_check(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None

        template = self._get_document_template(document)
        fields = document.semantic_state.get("fields", {})
        check_result = self.gap_checker.run(template.payload, fields)
        document.check_result = check_result
        document.status = "ready_to_freeze" if not check_result["items"] else "checking"
        document.annotations = self.annotation_service.build_annotations(template.payload, fields, check_result["items"])
        return self._serialize_document_detail(self.repository.save_document(document))

    def freeze(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        if document.status != "ready_to_freeze":
            self.run_check(document_id)
            self.session.refresh(document)
        if document.check_result.get("blocking_count", 0) > 0:
            raise ValueError("document has blocking gaps")

        fields = document.semantic_state.get("fields", {})
        frozen_package = self.freeze_service.build_frozen_package(
            standard_document=document.document,
            annotations=document.annotations,
            fields=fields,
            archive_ids=document.archive_ids,
            frozen_at=self._now(),
        )
        document.status = "frozen"
        document.frozen_package = frozen_package
        return self._serialize_document_detail(self.repository.save_document(document))

    def _ensure_default_templates(self) -> None:
        self.repository.ensure_default_templates()

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
        template = self.repository.get_template(document.template_id)
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
        document.document = self.document_renderer.render_document(template.payload, fields)
        document.annotations = self.annotation_service.build_annotations(template.payload, fields)
        document.check_result = self.gap_checker.empty_check_result()

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
            "knowledge_binding": None,
            "updated_at": self._now(),
        }

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
