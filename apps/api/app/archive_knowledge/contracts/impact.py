from __future__ import annotations

from pydantic import BaseModel, Field


class ImpactSet(BaseModel):
    impact_set_id: str
    archive_id: str
    policy_package_version_id: str
    previous_policy_package_version_id: str
    changed_rule_ids: list[str] = Field(default_factory=list)
    affected_stage_ids: list[str] = Field(default_factory=list)
    affected_chunk_ids: list[str] = Field(default_factory=list)
    affected_candidate_ids: list[str] = Field(default_factory=list)
    minimum_rebuild_stage_id: str
    affected_document_ids: list[str] = Field(default_factory=list)
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    affected_publication_snapshot_ids: list[str] = Field(default_factory=list)
    requires_governance_reconfirmation: bool = False
    generated_at: str | None = None
    writes_official_knowledge: bool = False
