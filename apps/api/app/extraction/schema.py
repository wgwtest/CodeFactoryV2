from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedCandidate(BaseModel):
    item_type: str
    canonical_name: str
    status: str = "extracted"
    confidence: float = 0.5
    payload: dict = Field(default_factory=dict)


class ExtractedRelation(BaseModel):
    relation_type: str
    source_name: str
    target_name: str
    confidence: float = 0.5
    payload: dict = Field(default_factory=dict)


class DocumentSourceRef(BaseModel):
    chunk_id: str
    chunk_heading: str
    segment_ids: list[str] = Field(default_factory=list)
    anchors: list[dict] = Field(default_factory=list)


class ExtractionBatch(BaseModel):
    document_id: str
    title: str
    strategy: str = "schema_rules"
    schema_version: str = "p1.v1"
    candidates: list[ExtractedCandidate] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class StructuredExtractionCandidate(BaseModel):
    item_type: Literal["entity", "event", "process"]
    canonical_name: str
    category: str
    aliases: list[str] = Field(default_factory=list)
    evidence: str | None = None
    confidence: float = 0.7


class StructuredExtractionRelation(BaseModel):
    relation_type: Literal[
        "describes",
        "owned_by",
        "part_of",
        "operational_exchange",
        "participates_in_exchange",
        "scoped_by",
        "process_scoped_by",
    ]
    source_name: str
    target_name: str
    evidence: str | None = None
    confidence: float = 0.7


class StructuredExtractionResponse(BaseModel):
    candidates: list[StructuredExtractionCandidate] = Field(default_factory=list)
    relations: list[StructuredExtractionRelation] = Field(default_factory=list)
    notes: str | None = None
