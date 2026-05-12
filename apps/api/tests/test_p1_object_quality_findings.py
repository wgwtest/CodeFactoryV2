from __future__ import annotations

from app.archive_knowledge.contracts.common import ArtifactRef
from app.archive_knowledge.contracts.knowledge_resolution import (
    ArchiveKnowledgeResolutionSnapshot,
    KnowledgeIdentityKey,
    ResolvedKnowledgeObject,
    ResolvedKnowledgeRelation,
)
from app.archive_knowledge.quality.object_findings import build_object_level_quality_findings


def test_object_level_quality_findings_apply_ontology_evidence_and_relation_contracts() -> None:
    source = _object(
        object_id="CK-source",
        name="NAS Enterprise Architecture",
        object_type="system",
        category="domain_concept",
        evidence_refs=[ArtifactRef(artifact_id="doc-1:item:evidence:1", artifact_type="source_anchor", document_id="doc-1", summary="excerpt")],
        explicit_definition_count=0,
    )
    target = _object(
        object_id="CK-target",
        name="SWIM",
        object_type="system",
        category="system",
        evidence_refs=[
            ArtifactRef(
                artifact_id="anchor-doc-2-swim",
                artifact_type="evidence_anchor",
                document_id="doc-2",
                summary="anchored evidence",
                metadata={"anchor_id": "anchor-doc-2-swim"},
            )
        ],
        explicit_definition_count=1,
    )
    relation = ResolvedKnowledgeRelation(
        relation_id="REL-support",
        source_object_id=source.object_id,
        target_object_id=target.object_id,
        relation_type="support",
        evidence_refs=[ArtifactRef(artifact_id="doc-1:rel:evidence:1", artifact_type="source_anchor", document_id="doc-1", summary="excerpt")],
        confidence=0.84,
        source_candidate_relation_ids=["doc-1:rel-support"],
        source_document_ids=["doc-1"],
    )
    snapshot = _snapshot(objects=[source, target], relations=[relation])

    report = build_object_level_quality_findings(
        archive_id="midterm",
        generated_at="2026-05-11T00:00:00+08:00",
        resolution_snapshot=snapshot,
    )

    codes = {finding.code for finding in report.findings}
    assert "category_not_publishable" in codes
    assert "item_evidence_excerpt_only" in codes
    assert "item_definition_missing" in codes
    assert "relation_endpoint_type_incompatible" in codes
    assert "relation_evidence_excerpt_only" in codes
    assert "publication_blocked_by_object_quality" in codes
    assert report.summary.publish_blocked is True


def test_object_level_quality_findings_block_publication_without_resolution_snapshot() -> None:
    report = build_object_level_quality_findings(
        archive_id="midterm",
        generated_at="2026-05-11T00:00:00+08:00",
        resolution_snapshot=None,
    )

    assert report.resolution_snapshot_id is None
    assert [finding.code for finding in report.findings] == ["resolution_snapshot_missing"]
    assert report.summary.blocked_count == 1
    assert report.summary.publish_blocked is True


def _object(
    *,
    object_id: str,
    name: str,
    object_type: str,
    category: str,
    evidence_refs: list[ArtifactRef],
    explicit_definition_count: int,
) -> ResolvedKnowledgeObject:
    return ResolvedKnowledgeObject(
        object_id=object_id,
        canonical_name=name,
        object_type=object_type,
        source_candidate_ids=[f"doc-1:{object_id}"],
        source_document_ids=["doc-1"],
        evidence_refs=evidence_refs,
        confidence=0.9,
        merge_decision="single_source",
        conflict_status="clean",
        identity_key=KnowledgeIdentityKey(
            identity_key_id=f"IK-{object_id}",
            knowledge_type=object_type,
            normalized_name=name.casefold(),
            business_scope="midterm",
            key_fields={"category": category},
        ),
        aliases=[],
        quality_summary={"explicit_definition_count": explicit_definition_count},
    )


def _snapshot(
    *,
    objects: list[ResolvedKnowledgeObject],
    relations: list[ResolvedKnowledgeRelation],
) -> ArchiveKnowledgeResolutionSnapshot:
    return ArchiveKnowledgeResolutionSnapshot(
        snapshot_id="RESOLVE-midterm",
        archive_id="midterm",
        input_document_ids=["doc-1", "doc-2"],
        generated_at="2026-05-11T00:00:00+08:00",
        resolved_objects=objects,
        resolved_relations=relations,
    )
