from __future__ import annotations

from app.db.models.requirements import RequirementAuthoringDocument
from app.requirement_authoring.document_repository import RequirementAuthoringRepository
from app.requirement_authoring.document_service import RequirementDocumentService
from app.requirement_authoring.models import (
    RequirementAuthoringDocumentCreate,
    RequirementAuthoringDocumentSave,
    RequirementAuthoringFormPatch,
    RequirementAuthoringMessageWrite,
)
from app.requirement_configuration.template_application_service import RequirementConfigurationApplicationService
from app.requirement_exchange.exchange_application_service import RequirementExchangeApplicationService


class RequirementAuthoringApplicationService:
    def __init__(self, session) -> None:
        self.session = session
        self.repository = RequirementAuthoringRepository(session)
        self.configuration_service = RequirementConfigurationApplicationService(session)
        self.exchange_service = RequirementExchangeApplicationService(session)
        self.document_service = RequirementDocumentService()

    def list_documents(self) -> list[dict]:
        return [self.serialize_document_summary(document) for document in self.repository.list_documents()]

    def create_document(self, payload: RequirementAuthoringDocumentCreate) -> dict:
        self.configuration_service.ensure_default_templates()
        template = self.configuration_service.get_template_model(payload.template_id)
        if template is None:
            raise ValueError("template not found")
        document = self.document_service.create_document(
            title=payload.title,
            template=template,
            layout_ratio=payload.layout_ratio,
            archive_ids=payload.archive_ids,
        )
        return self.serialize_document_detail(self.repository.add_document(document))

    def get_document(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        return self.serialize_document_detail(document)

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
        template = self.get_document_template(document)
        if payload.template_id is not None and payload.template_id != document.template_id:
            next_template = self.configuration_service.get_template_model(payload.template_id)
            if next_template is None:
                raise ValueError("template not found")
            template = next_template
            self.document_service.change_template(document=document, template=template)
        self.document_service.save_document_context(
            document=document,
            template=template,
            title=payload.title,
            archive_ids=payload.archive_ids,
            knowledge_binding_was_set="knowledge_binding" in payload.model_fields_set,
            knowledge_binding=payload.knowledge_binding,
        )
        return self.serialize_document_detail(self.repository.save_document(document))

    def append_message(self, document_id: str, payload: RequirementAuthoringMessageWrite) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        self.ensure_editable(document)
        self.document_service.append_message(
            document=document,
            template=self.get_document_template(document),
            user_content=payload.content.strip(),
        )
        return self.serialize_document_detail(self.repository.save_document(document))

    def patch_form_fields(self, document_id: str, payload: RequirementAuthoringFormPatch) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        self.ensure_editable(document)
        self.document_service.patch_form_fields(
            document=document,
            template=self.get_document_template(document),
            fields_patch=payload.fields,
        )
        return self.serialize_document_detail(self.repository.save_document(document))

    def patch_clause(self, document_id: str, clause_id: str, content: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        self.ensure_editable(document)
        self.document_service.patch_clause(document=document, clause_id=clause_id, content=content)
        return self.serialize_document_detail(self.repository.save_document(document))

    def run_check(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        self.document_service.run_check(document=document, template=self.get_document_template(document))
        return self.serialize_document_detail(self.repository.save_document(document))

    def freeze(self, document_id: str) -> dict | None:
        document = self.repository.get_document(document_id)
        if document is None:
            return None
        if document.status != "ready_to_freeze":
            self.run_check(document_id)
            self.session.refresh(document)
        if document.check_result.get("blocking_count", 0) > 0:
            raise ValueError("document has blocking gaps")
        self.document_service.freeze(document=document)
        return self.serialize_document_detail(self.repository.save_document(document))

    def list_knowledge_providers(self) -> dict:
        return self.exchange_service.list_knowledge_providers()

    def bind_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        return self.exchange_service.bind_knowledge(provider_id, domain_id)

    def get_document_template(self, document: RequirementAuthoringDocument):
        template = self.configuration_service.get_template_model(document.template_id)
        if template is None:
            raise ValueError("template not found")
        return template

    @staticmethod
    def ensure_editable(document: RequirementAuthoringDocument) -> None:
        if document.status == "frozen":
            raise ValueError("document is frozen")

    @staticmethod
    def serialize_document_summary(document: RequirementAuthoringDocument) -> dict:
        return {
            "document_id": document.id,
            "title": document.title,
            "template_id": document.template_id,
            "status": document.status,
            "layout_ratio": document.layout_ratio,
            "archive_ids": document.archive_ids,
            "updated_at": document.updated_at.isoformat(),
        }

    def serialize_document_detail(self, document: RequirementAuthoringDocument) -> dict:
        return {
            **self.serialize_document_summary(document),
            "created_at": document.created_at.isoformat(),
            "semantic_state": document.semantic_state,
            "document": document.document,
            "conversation": document.conversation,
            "annotations": document.annotations,
            "check_result": document.check_result,
            "frozen_package": document.frozen_package,
        }
