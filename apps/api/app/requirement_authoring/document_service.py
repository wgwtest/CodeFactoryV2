from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.requirements import RequirementAuthoringDocument, RequirementAuthoringTemplate
from app.requirement_authoring.annotation_service import RequirementAnnotationService
from app.requirement_authoring.document_renderer import RequirementDocumentRenderer
from app.requirement_authoring.freeze_service import RequirementFreezeService
from app.requirement_authoring.gap_checker import RequirementGapChecker


class RequirementDocumentService:
    def __init__(self) -> None:
        self.document_renderer = RequirementDocumentRenderer()
        self.annotation_service = RequirementAnnotationService()
        self.gap_checker = RequirementGapChecker()
        self.freeze_service = RequirementFreezeService()

    def create_document(
        self,
        *,
        title: str,
        template: RequirementAuthoringTemplate,
        layout_ratio: str,
        archive_ids: list[str],
    ) -> RequirementAuthoringDocument:
        fields = self.initial_fields()
        semantic_state = self.build_semantic_state(fields, template)
        return RequirementAuthoringDocument(
            title=title.strip() or "未命名需求规格说明",
            template_id=template.id,
            status="draft",
            layout_ratio=layout_ratio,
            archive_ids=archive_ids,
            semantic_state=semantic_state,
            document=self.document_renderer.render_document(template.payload, fields),
            conversation=[
                {
                    "id": "msg-1",
                    "role": "assistant",
                    "content": "我会按标准规格骨架持续起草和修补。你可以直接回：可以 / 更正式 / 加超时 / 重拟 / 继续。",
                    "created_at": self.now(),
                }
            ],
            annotations=self.annotation_service.build_annotations(template.payload, fields),
            check_result=self.gap_checker.empty_check_result(),
            frozen_package=None,
        )

    def save_document_context(
        self,
        *,
        document: RequirementAuthoringDocument,
        template: RequirementAuthoringTemplate,
        title: str | None,
        archive_ids: list[str] | None,
        knowledge_binding_was_set: bool,
        knowledge_binding: dict | None,
    ) -> None:
        if document.status != "frozen":
            document.status = "draft"
        if title is not None:
            document.title = title.strip() or "未命名软件需求规格说明"
        if archive_ids is not None:
            document.archive_ids = archive_ids
        semantic_state = dict(document.semantic_state or {})
        if knowledge_binding_was_set:
            semantic_state["knowledge_binding"] = knowledge_binding
        elif "knowledge_binding" not in semantic_state:
            semantic_state["knowledge_binding"] = None
        semantic_state["template_id"] = template.id
        semantic_state["template_code"] = template.template_code
        semantic_state["updated_at"] = self.now()
        document.semantic_state = semantic_state
        document.document = dict(document.document or {})
        document.conversation = list(document.conversation or [])
        document.annotations = list(document.annotations or [])
        document.check_result = dict(document.check_result or {})

    def change_template(self, *, document: RequirementAuthoringDocument, template: RequirementAuthoringTemplate) -> None:
        document.template_id = template.id
        fields = dict((document.semantic_state or {}).get("fields", {}))
        document.document = self.document_renderer.render_document(template.payload, fields)
        document.annotations = self.annotation_service.build_annotations(template.payload, fields)
        document.check_result = self.gap_checker.empty_check_result()

    def append_message(
        self,
        *,
        document: RequirementAuthoringDocument,
        template: RequirementAuthoringTemplate,
        user_content: str,
    ) -> None:
        fields = dict(document.semantic_state.get("fields", {}))
        normalized = user_content.lower()
        if "超时" in user_content:
            fields["exception_flow"] = "包含超时提醒和人工确认，不扩展复杂补偿链路。"
        elif "更正式" in user_content:
            fields["normal_flow"] = self.formalize_sentence(fields.get("normal_flow", ""))
        elif "重拟" in user_content:
            fields["normal_flow"] = "系统应支持创建、校验、协同确认和归档核心业务记录。"
        elif user_content and normalized not in {"a", "b", "c", "可以", "继续"}:
            fields["normal_flow"] = user_content
        elif not fields.get("main_process"):
            fields["main_process"] = "待确认核心业务流程"

        conversation = list(document.conversation)
        next_index = len(conversation) + 1
        conversation.extend(
            [
                {"id": f"msg-{next_index}", "role": "user", "content": user_content, "created_at": self.now()},
                {
                    "id": f"msg-{next_index + 1}",
                    "role": "assistant",
                    "content": self.build_assistant_reply(fields, user_content),
                    "created_at": self.now(),
                },
            ]
        )
        self.write_document_state(document, template, fields)
        document.conversation = conversation
        document.status = "draft"

    def patch_form_fields(
        self,
        *,
        document: RequirementAuthoringDocument,
        template: RequirementAuthoringTemplate,
        fields_patch: dict[str, str],
    ) -> None:
        fields = dict(document.semantic_state.get("fields", {}))
        for key, value in fields_patch.items():
            fields[key] = value.strip()
        self.write_document_state(document, template, fields)
        document.status = "draft"

    def patch_clause(self, *, document: RequirementAuthoringDocument, clause_id: str, content: str) -> None:
        document.document = self.document_renderer.patch_clause(document.document, clause_id, content)
        document.annotations = self.annotation_service.mark_clause_pending_mapping(document.annotations, clause_id)
        document.status = "draft"

    def run_check(self, *, document: RequirementAuthoringDocument, template: RequirementAuthoringTemplate) -> None:
        fields = document.semantic_state.get("fields", {})
        check_result = self.gap_checker.run(template.payload, fields)
        document.check_result = check_result
        document.status = "ready_to_freeze" if not check_result["items"] else "checking"
        document.annotations = self.annotation_service.build_annotations(template.payload, fields, check_result["items"])

    def freeze(self, *, document: RequirementAuthoringDocument) -> None:
        fields = document.semantic_state.get("fields", {})
        document.status = "frozen"
        document.frozen_package = self.freeze_service.build_frozen_package(
            standard_document=document.document,
            annotations=document.annotations,
            fields=fields,
            archive_ids=document.archive_ids,
            frozen_at=self.now(),
        )

    def write_document_state(
        self,
        document: RequirementAuthoringDocument,
        template: RequirementAuthoringTemplate,
        fields: dict[str, str],
    ) -> None:
        document.semantic_state = self.build_semantic_state(fields, template)
        document.document = self.document_renderer.render_document(template.payload, fields)
        document.annotations = self.annotation_service.build_annotations(template.payload, fields)
        document.check_result = self.gap_checker.empty_check_result()

    @staticmethod
    def initial_fields() -> dict[str, str]:
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

    def build_semantic_state(self, fields: dict[str, str], template: RequirementAuthoringTemplate) -> dict:
        return {
            "template_id": template.id,
            "template_code": template.template_code,
            "fields": fields,
            "knowledge_binding": None,
            "updated_at": self.now(),
        }

    @staticmethod
    def build_assistant_reply(fields: dict[str, str], user_content: str) -> str:
        if "超时" in user_content:
            return "已补入一个克制版超时提醒，不扩展复杂补偿链路。你可以直接回：可以 / 更正式 / 重拟。"
        if fields.get("normal_flow"):
            return "我已把这句业务事实并入核心流程草稿。你可以直接回：可以 / 加超时 / 更正式 / 继续。"
        return "我会继续补齐缺口，优先处理功能需求和验收准则。你可以直接回：可以 / A / B / 重拟。"

    @staticmethod
    def formalize_sentence(value: str) -> str:
        if not value:
            return "系统应支持核心业务流程的创建、校验、协同确认与结果留痕。"
        return f"系统应支持{value.rstrip('。')}，并形成可审计的处理记录。"

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()

