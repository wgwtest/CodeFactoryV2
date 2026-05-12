from __future__ import annotations

from hashlib import sha1
from typing import Literal

from pydantic import BaseModel, Field


EvidenceRole = Literal["name", "definition", "relation", "constraint", "metric", "example", "source"]
SupportsField = Literal["canonical_name", "category", "definition", "summary", "relation", "boundary", "unknown"]
TraceabilityLevel = Literal["anchored", "segment", "chunk", "excerpt", "document", "missing"]


class EvidenceRef(BaseModel):
    evidence_id: str
    document_id: str
    document_title: str | None = None
    source_file_path: str | None = None
    page: int | None = None
    section_path: list[str] = Field(default_factory=list)
    heading: str | None = None
    chunk_id: str | None = None
    segment_ids: list[str] = Field(default_factory=list)
    anchor_ids: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    evidence_role: EvidenceRole = "source"
    supports_field: SupportsField = "unknown"
    confidence: float = Field(default=0.5, ge=0, le=1)
    policy_snapshot_id: str | None = None


class EvidenceObject(EvidenceRef):
    normalized_excerpt: str | None = None
    extraction_method: str | None = None
    traceability_level: TraceabilityLevel = "missing"


def normalize_excerpt(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(str(value).split())
    return collapsed[:500] if collapsed else None


def infer_traceability_level(evidence: EvidenceRef | EvidenceObject) -> TraceabilityLevel:
    if evidence.anchor_ids:
        return "anchored"
    if evidence.segment_ids:
        return "segment"
    if evidence.chunk_id:
        return "chunk"
    if evidence.excerpt:
        return "excerpt"
    if evidence.document_id:
        return "document"
    return "missing"


def build_legacy_evidence_ref(
    *,
    document_id: str,
    excerpt: str | None,
    evidence_id: str | None = None,
    evidence_role: EvidenceRole = "source",
    supports_field: SupportsField = "unknown",
) -> EvidenceObject:
    digest_source = f"{document_id}\n{normalize_excerpt(excerpt) or ''}".encode("utf-8")
    stable_evidence_suffix = sha1(digest_source).hexdigest()[:12]
    ref = EvidenceObject(
        evidence_id=evidence_id or f"{document_id}:legacy-evidence:{stable_evidence_suffix}",
        document_id=document_id,
        excerpt=normalize_excerpt(excerpt),
        normalized_excerpt=normalize_excerpt(excerpt),
        evidence_role=evidence_role,
        supports_field=supports_field,
        extraction_method="legacy_excerpt",
    )
    ref.traceability_level = infer_traceability_level(ref)
    return ref
