from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class P1KnowledgeProviderRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    provider_name: str
    provider_kind: Literal["p1_knowledge_provider"]
    status: Literal["online", "offline"]
    capabilities: list[Literal["domain_catalog", "knowledge_archive"]]
    version: str
    seed: str


class P1DomainKnowledgeCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_id: str
    domain_name: str
    domain_summary: str
    archive_version: str
    concept_count: int
    rule_count: int
    process_count: int
    evidence_count: int


class P1DomainKnowledgeCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: P1KnowledgeProviderRegistration
    items: list[P1DomainKnowledgeCatalogItem]


class P1KnowledgeConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str
    name: str
    definition: str


class P1KnowledgeRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    description: str


class P1KnowledgeProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: str
    name: str
    steps: list[str]


class P1KnowledgeConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    category: str
    description: str


class P1KnowledgeEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    excerpt: str


class P1DomainKnowledgeArchive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    domain_id: str
    archive_id: str
    archive_version: str
    published_at: str
    concepts: list[P1KnowledgeConcept]
    entities: list[P1KnowledgeConcept]
    rules: list[P1KnowledgeRule]
    processes: list[P1KnowledgeProcess]
    constraints: list[P1KnowledgeConstraint]
    evidence_refs: list[P1KnowledgeEvidenceRef]


class P1SimCallLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str
    called_at: str
    method: str
    path: str
    domain_id: str | None = None
    status_code: int
    archive_version: str


class P1SimCallLogEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[P1SimCallLog]


class P1SimResetResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    seed: str
    archive_version: str
    log_count: int


class RequirementAuthoringKnowledgeProviderEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict]


class RequirementAuthoringKnowledgeBindingWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    domain_id: str
