from __future__ import annotations

from datetime import UTC, datetime
from itertools import count

from app.xx_p1_sim.fixtures import ARCHIVE_VERSION, ARCHIVES, DOMAINS, FIXED_SEED, PROVIDER
from app.xx_p1_sim.models import (
    P1DomainKnowledgeArchive,
    P1DomainKnowledgeCatalog,
    P1DomainKnowledgeCatalogItem,
    P1KnowledgeProviderRegistration,
    P1SimCallLog,
    P1SimCallLogEnvelope,
    P1SimResetResult,
)


class XXP1SimService:
    _call_counter = count(1)
    _logs: list[P1SimCallLog] = []

    def register(self) -> P1KnowledgeProviderRegistration:
        self._record_call("POST", "/api/xx-p1-sim/register", None, 200)
        return self.provider()

    def provider(self) -> P1KnowledgeProviderRegistration:
        return P1KnowledgeProviderRegistration.model_validate(PROVIDER)

    def list_domains(self, record_log: bool = True) -> P1DomainKnowledgeCatalog:
        if record_log:
            self._record_call("GET", "/api/xx-p1-sim/domains", None, 200)
        return P1DomainKnowledgeCatalog(
            provider=self.provider(),
            items=[P1DomainKnowledgeCatalogItem.model_validate(item) for item in DOMAINS],
        )

    def get_domain(self, domain_id: str) -> P1DomainKnowledgeCatalogItem | None:
        for item in DOMAINS:
            if item["domain_id"] == domain_id:
                return P1DomainKnowledgeCatalogItem.model_validate(item)
        return None

    def get_knowledge_archive(self, domain_id: str, record_log: bool = True) -> P1DomainKnowledgeArchive | None:
        archive = ARCHIVES.get(domain_id)
        status_code = 200 if archive is not None else 404
        if record_log:
            self._record_call("GET", f"/api/xx-p1-sim/domains/{domain_id}/knowledge", domain_id, status_code)
        if archive is None:
            return None
        return P1DomainKnowledgeArchive.model_validate(archive)

    def reset(self) -> P1SimResetResult:
        type(self)._logs = []
        self._record_call("POST", "/api/xx-p1-sim/reset", None, 200)
        return P1SimResetResult(
            provider_id=PROVIDER["provider_id"],
            seed=FIXED_SEED,
            archive_version=ARCHIVE_VERSION,
            log_count=len(type(self)._logs),
        )

    def list_logs(self) -> P1SimCallLogEnvelope:
        return P1SimCallLogEnvelope(items=list(type(self)._logs))

    def build_requirement_authoring_provider(self) -> dict:
        catalog = self.list_domains(record_log=False)
        provider = self.provider().model_dump()
        return {
            **provider,
            "domains": [item.model_dump() for item in catalog.items],
        }

    def bind_requirement_authoring_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        if provider_id != PROVIDER["provider_id"]:
            return None

        domain = self.get_domain(domain_id)
        archive = self.get_knowledge_archive(domain_id)
        if domain is None or archive is None:
            return None

        return {
            "binding_id": f"binding-{provider_id}-{domain_id}",
            "provider": self.provider().model_dump(),
            "domain": domain.model_dump(),
            "knowledge_archive": archive.model_dump(),
            "editor_badge": "领域知识已绑定",
            "created_document": None,
            "frozen_package": None,
        }

    def _record_call(self, method: str, path: str, domain_id: str | None, status_code: int) -> None:
        type(self)._logs.append(
            P1SimCallLog(
                call_id=f"p1-sim-call-{next(type(self)._call_counter):04d}",
                called_at=datetime.now(UTC).isoformat(),
                method=method,
                path=path,
                domain_id=domain_id,
                status_code=status_code,
                archive_version=ARCHIVE_VERSION,
            )
        )
