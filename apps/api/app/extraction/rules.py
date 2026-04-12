from __future__ import annotations

from app.extraction.schema import ExtractedCandidate, ExtractedRelation, ExtractionBatch
from app.knowledge_builder import (
    SourceDocument,
    _extract_entities,
    _extract_events,
    _extract_operational_interactions,
    _extract_processes,
)
from app.parsing.models import ParsedSegment


def extract_candidates(segments: list[ParsedSegment]) -> list[ExtractedCandidate]:
    batch = extract_document_batch(
        document_id="ad-hoc-document",
        document=SourceDocument(
            path="ad-hoc-document.txt",
            title="ad-hoc-document",
            file_type="txt",
            source_archive="runtime",
            text="\n".join(segment.content for segment in segments),
        ),
        segments=segments,
    )
    return batch.candidates


def extract_document_batch(
    *,
    document_id: str,
    document: SourceDocument,
    segments: list[ParsedSegment],
) -> ExtractionBatch:
    lines = [segment.content.strip() for segment in segments if segment.content.strip()]
    interactions = _extract_operational_interactions(lines)
    candidates: list[ExtractedCandidate] = []
    relations: list[ExtractedRelation] = []
    seen_candidates: set[tuple[str, str]] = set()
    seen_relations: set[tuple[str, str, str]] = set()

    for item in _extract_entities(document, lines, interactions):
        _append_candidate(
            candidates,
            seen_candidates,
            ExtractedCandidate(
                item_type="entity",
                canonical_name=item["name"],
                confidence=0.86,
                payload={
                    "category": item["category"],
                    "aliases": item.get("aliases", []),
                    "summary": item.get("summary"),
                    "evidence": item.get("evidence"),
                    "document_id": document_id,
                },
            ),
        )

    for item in _extract_events(document, lines):
        _append_candidate(
            candidates,
            seen_candidates,
            ExtractedCandidate(
                item_type="event",
                canonical_name=item["name"],
                confidence=0.82,
                payload={
                    "category": item["category"],
                    "aliases": item.get("aliases", []),
                    "evidence": item.get("evidence"),
                    "document_id": document_id,
                },
            ),
        )

    for item in _extract_processes(document, lines):
        _append_candidate(
            candidates,
            seen_candidates,
            ExtractedCandidate(
                item_type="process",
                canonical_name=item["name"],
                confidence=0.8,
                payload={
                    "category": item["category"],
                    "aliases": item.get("aliases", []),
                    "evidence": item.get("evidence"),
                    "document_id": document_id,
                },
            ),
        )

    _append_document_relations(
        document_id=document_id,
        document=document,
        candidates=candidates,
        relations=relations,
        seen_relations=seen_relations,
        interactions=interactions,
    )

    return ExtractionBatch(
        document_id=document_id,
        title=document.title,
        candidates=candidates,
        relations=relations,
        metadata={"source_path": document.path, "line_count": len(lines)},
    )


def _append_candidate(
    candidates: list[ExtractedCandidate],
    seen_candidates: set[tuple[str, str]],
    candidate: ExtractedCandidate,
) -> None:
    key = (candidate.item_type, candidate.canonical_name)
    if key in seen_candidates:
        return
    seen_candidates.add(key)
    candidates.append(candidate)


def _append_relation(
    relations: list[ExtractedRelation],
    seen_relations: set[tuple[str, str, str]],
    relation_type: str,
    source_name: str,
    target_name: str,
    confidence: float = 0.78,
    payload: dict | None = None,
) -> None:
    key = (relation_type, source_name, target_name)
    if key in seen_relations:
        return
    seen_relations.add(key)
    relations.append(
        ExtractedRelation(
            relation_type=relation_type,
            source_name=source_name,
            target_name=target_name,
            confidence=confidence,
            payload=payload or {},
        )
    )


def _append_document_relations(
    *,
    document_id: str,
    document: SourceDocument,
    candidates: list[ExtractedCandidate],
    relations: list[ExtractedRelation],
    seen_relations: set[tuple[str, str, str]],
    interactions: list[dict],
) -> None:
    del document_id, document
    candidate_names = {candidate.canonical_name for candidate in candidates}
    artifact_names = {
        candidate.canonical_name
        for candidate in candidates
        if candidate.item_type == "entity" and candidate.payload.get("category") == "architecture_artifact"
    }
    if "国家空域系统" in candidate_names:
        for artifact_name in artifact_names:
            _append_relation(relations, seen_relations, "describes", artifact_name, "国家空域系统", 0.92)

        for candidate in candidates:
            if candidate.canonical_name == "国家空域系统":
                continue
            if candidate.item_type == "entity" and candidate.payload.get("category") in {"operational_node", "information_exchange"}:
                _append_relation(relations, seen_relations, "part_of", candidate.canonical_name, "国家空域系统", 0.74)
            if candidate.item_type == "process":
                _append_relation(relations, seen_relations, "part_of", candidate.canonical_name, "国家空域系统", 0.72)

    owner_names = {
        candidate.canonical_name
        for candidate in candidates
        if candidate.item_type == "entity" and candidate.payload.get("category") == "organization"
    }
    for artifact_name in artifact_names:
        if "联邦航空管理局" in owner_names:
            _append_relation(relations, seen_relations, "owned_by", artifact_name, "联邦航空管理局", 0.84)

    event_names = {
        candidate.canonical_name
        for candidate in candidates
        if candidate.item_type == "event"
    }
    for artifact_name in artifact_names:
        for event_name in event_names:
            _append_relation(relations, seen_relations, "scoped_by", artifact_name, event_name, 0.75)

    for interaction in interactions:
        source_name = interaction["source_name"]
        target_name = interaction["target_name"]
        if source_name and target_name:
            _append_relation(
                relations,
                seen_relations,
                "operational_exchange",
                source_name,
                target_name,
                0.9,
                {"evidence": interaction["evidence"]},
            )

        for exchange in interaction["exchanges"]:
            exchange_name = exchange["name"]
            _append_relation(relations, seen_relations, "participates_in_exchange", source_name, exchange_name, 0.88)
            _append_relation(relations, seen_relations, "participates_in_exchange", target_name, exchange_name, 0.88)
