from __future__ import annotations

from app.requirement_exchange.frozen_package_projector import FrozenPackageProjector
from app.requirement_exchange.knowledge_binding_service import KnowledgeBindingService
from app.requirement_exchange.requirement_spec_service import RequirementSpecApplicationService


class RequirementExchangeApplicationService:
    def __init__(self, session) -> None:
        self.knowledge_binding_service = KnowledgeBindingService()
        self.projector = FrozenPackageProjector()
        self.spec_service = RequirementSpecApplicationService(session)

    def list_knowledge_providers(self) -> dict:
        return self.knowledge_binding_service.list_providers()

    def bind_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        return self.knowledge_binding_service.bind(provider_id, domain_id)

    def build_requirement_spec_from_document(self, document_detail: dict) -> dict:
        draft = self.projector.project(document_detail)
        spec = self.spec_service.create_from_projected_draft(draft)
        return self.spec_service.serialize_detail(spec)
