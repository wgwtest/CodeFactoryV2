from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef
from app.archive_knowledge.contracts.publication import PublishedKnowledgeSnapshot


class DeprecatedOutputRoute(BaseModel):
    deprecated: bool = True
    replacement_path: str
    removal_policy: str


class P1KnowledgeSupplyExport(BaseModel):
    export_id: str
    archive_id: str
    contract_version: Literal["P1KnowledgeSupplyExport.v1"]
    published_snapshot_id: str
    formal_version: str
    governed_by: str
    published_at: str
    published_snapshot: PublishedKnowledgeSnapshot
    formal_knowledge_refs: list[ArtifactRef] = Field(default_factory=list)
    quality_report_ref: ArtifactRef | None = None
    graph_quality_report_ref: ArtifactRef | None = None
    consumer_systems: list[str]
    api_base_path: str
    knowledge_read_path: str
    graph_query_path: str
    generated_at: str
    deprecation: DeprecatedOutputRoute | None = None


class P6DisplayExportContractV2(BaseModel):
    export_id: str
    source_export_id: str
    contract_version: Literal["P6DisplayExportContract.v2"]
    published_snapshot_id: str
    formal_version: str
    governed_by: str
    published_at: str
    graph_summary_path: str
    entity_lookup_path: str
    relation_lookup_path: str
    source_trace: list[ArtifactRef] = Field(default_factory=list)


class FormalKnowledgeInterface(BaseModel):
    method: Literal["GET", "POST"]
    path: str
    purpose: str
    source: Literal["formal_publication_snapshot"]
    requires_publication_snapshot_id: bool = True


class FormalKnowledgeVersionRule(BaseModel):
    rule_id: str
    description: str
    selected_publication_snapshot_id: str
    selected_version_label: str
    governance_boundary: Literal["post_publication_confirmation"]


class SystemOutputAdapterContract(BaseModel):
    adapter_name: str
    contract_version: str
    input_keys: list[str]
    output_keys: list[str]
    allowed_backend_calls: list[str]
    forbidden_sources: list[str]


class DownstreamConsumptionGuide(BaseModel):
    consumer: Literal["P2", "P3"]
    read_pattern: str
    notes: list[str] = Field(default_factory=list)


class FormalApiExposureScope(BaseModel):
    exposure_mode: Literal["formal_only", "not_available"] = "formal_only"
    formal_api_paths: list[str] = Field(default_factory=list)
    candidate_api_paths: list[str] = Field(default_factory=list)
    blocked_candidate_sources: list[str] = Field(default_factory=list)
    not_supply_reason: str | None = None


class SystemReadableKnowledgeObject(BaseModel):
    object_id: str
    name: str
    item_type: str
    category: str | None = None
    document_count: int = 0
    evidence_count: int = 0
    version_id: str | None = None


class SystemReadableKnowledgeRelation(BaseModel):
    relation_id: str
    source_object_id: str
    target_object_id: str
    relation_type: str
    version_id: str | None = None


class SystemReadableEvidence(BaseModel):
    evidence_id: str
    object_id: str
    document_id: str | None = None
    excerpt: str | None = None
    version_id: str | None = None


class P1CleanSystemOutputContract(BaseModel):
    contract_version: Literal["P1CleanSystemOutputContract.v1"]
    archive_id: str
    publication_snapshot_id: str | None
    canonical_publication_snapshot_id: str | None
    formal_version: str | None
    formal_version_id: str | None = None
    governed_by: str | None
    published_at: str | None
    generated_at: str
    source_kind: Literal["governed_publication_snapshot"]
    is_formalized: bool = True
    supply_available: bool = True
    unavailable_reason: str | None = None
    boundary: str
    source_summary: dict[str, int]
    formal_interfaces: list[FormalKnowledgeInterface]
    version_selection_rules: list[FormalKnowledgeVersionRule]
    api_exposure_scope: FormalApiExposureScope = Field(default_factory=FormalApiExposureScope)
    readable_objects: list[SystemReadableKnowledgeObject] = Field(default_factory=list)
    readable_relations: list[SystemReadableKnowledgeRelation] = Field(default_factory=list)
    readable_evidence: list[SystemReadableEvidence] = Field(default_factory=list)
    adapter_contract: SystemOutputAdapterContract
    downstream_consumers: list[DownstreamConsumptionGuide]
