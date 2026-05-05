from __future__ import annotations

from app.xx_p1_sim.service import XXP1SimService


class KnowledgeProviderRegistry:
    def list(self) -> list[dict]:
        provider = XXP1SimService().build_requirement_authoring_provider()
        return [provider]

