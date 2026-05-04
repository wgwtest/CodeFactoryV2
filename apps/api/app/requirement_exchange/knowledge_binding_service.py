from __future__ import annotations

from app.requirement_exchange.p1_knowledge_adapter import P1KnowledgeAdapter


class KnowledgeBindingService:
    def __init__(self) -> None:
        self.adapter = P1KnowledgeAdapter()

    def list_providers(self) -> dict:
        from app.requirement_exchange.knowledge_provider_registry import KnowledgeProviderRegistry

        return {"items": KnowledgeProviderRegistry().list()}

    def bind(self, provider_id: str, domain_id: str) -> dict | None:
        return self.adapter.bind_requirement_authoring_knowledge(provider_id, domain_id)

