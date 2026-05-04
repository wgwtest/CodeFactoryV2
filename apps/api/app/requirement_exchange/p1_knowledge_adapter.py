from __future__ import annotations

from app.xx_p1_sim.service import XXP1SimService


class P1KnowledgeAdapter:
    def bind_requirement_authoring_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        return XXP1SimService().bind_requirement_authoring_knowledge(provider_id, domain_id)

