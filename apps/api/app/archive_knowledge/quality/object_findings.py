from __future__ import annotations

from hashlib import sha1
from typing import Iterable

from app.archive_knowledge.contracts.common import ArtifactRef
from app.archive_knowledge.contracts.knowledge_resolution import (
    ArchiveKnowledgeResolutionSnapshot,
    ResolvedKnowledgeObject,
    ResolvedKnowledgeRelation,
)
from app.archive_knowledge.contracts.ontology import (
    category_allows_item_type,
    is_publishable_category,
    is_publishable_item_type,
    is_supported_category,
    is_supported_item_type,
    normalize_category,
    normalize_item_type,
)
from app.archive_knowledge.contracts.quality_findings import (
    QualityFinding,
    QualityFindingReport,
    summarize_findings,
)
from app.archive_knowledge.contracts.relation_contracts import get_relation_contract, normalize_relation_type


TRACEABLE_METADATA_KEYS = {
    "anchor_id",
    "anchor_ids",
    "chunk_id",
    "chunk_ids",
    "page",
    "section_path",
    "segment_id",
    "segment_ids",
    "source_file_path",
}


def build_object_level_quality_findings(
    *,
    archive_id: str,
    generated_at: str,
    resolution_snapshot: ArchiveKnowledgeResolutionSnapshot | None,
    publication_snapshot_id: str | None = None,
) -> QualityFindingReport:
    findings: list[QualityFinding] = []
    if resolution_snapshot is None:
        findings.append(
            _finding(
                scope="publication",
                severity="blocked",
                code="resolution_snapshot_missing",
                message="Object-level quality cannot run without a knowledge resolution snapshot.",
                target_id=archive_id,
                suggested_action="defer_publish",
                blocking_publish=True,
            )
        )
        return _report(
            archive_id=archive_id,
            generated_at=generated_at,
            resolution_snapshot_id=None,
            publication_snapshot_id=publication_snapshot_id,
            findings=findings,
        )

    object_by_id = {item.object_id: item for item in resolution_snapshot.resolved_objects}
    for item in resolution_snapshot.resolved_objects:
        findings.extend(_item_findings(item))
    for relation in resolution_snapshot.resolved_relations:
        findings.extend(_relation_findings(relation, object_by_id))

    blocking_count = sum(1 for finding in findings if finding.blocking_publish)
    if blocking_count:
        findings.append(
            _finding(
                scope="publication",
                severity="blocked",
                code="publication_blocked_by_object_quality",
                message="Publication is blocked because object-level or relation-level quality findings require action.",
                target_id=resolution_snapshot.snapshot_id,
                suggested_action="defer_publish",
                blocking_publish=True,
                metadata={"blocking_finding_count": blocking_count},
            )
        )

    return _report(
        archive_id=archive_id,
        generated_at=generated_at,
        resolution_snapshot_id=resolution_snapshot.snapshot_id,
        publication_snapshot_id=publication_snapshot_id,
        findings=findings,
    )


def _item_findings(item: ResolvedKnowledgeObject) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    normalized_item_type = normalize_item_type(item.object_type)
    raw_category = _object_category(item)
    normalized_category = normalize_category(raw_category)

    if not is_supported_item_type(item.object_type):
        findings.append(
            _finding(
                scope="item",
                severity="blocked",
                code="item_type_invalid",
                message="Knowledge item type is outside the controlled ontology.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="fix_contract",
                blocking_publish=True,
                metadata={"raw_item_type": item.object_type, "normalized_item_type": normalized_item_type},
            )
        )
    elif not is_publishable_item_type(item.object_type):
        findings.append(
            _finding(
                scope="item",
                severity="blocked",
                code="item_type_not_publishable",
                message="Knowledge item type is reserved or not publishable in the current ontology contract.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="manual_review",
                blocking_publish=True,
                metadata={"normalized_item_type": normalized_item_type},
            )
        )

    if not is_supported_category(raw_category):
        findings.append(
            _finding(
                scope="category",
                severity="blocked",
                code="category_invalid",
                message="Knowledge item category is outside the controlled vocabulary.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="fix_contract",
                blocking_publish=True,
                metadata={"raw_category": raw_category, "normalized_category": normalized_category},
            )
        )
    elif not is_publishable_category(raw_category):
        findings.append(
            _finding(
                scope="category",
                severity="blocked",
                code="category_not_publishable",
                message="Knowledge item category requires classification before publication.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="manual_review",
                blocking_publish=True,
                metadata={"raw_category": raw_category, "normalized_category": normalized_category},
            )
        )
    elif not category_allows_item_type(raw_category, item.object_type):
        findings.append(
            _finding(
                scope="category",
                severity="blocked",
                code="category_item_type_incompatible",
                message="Knowledge item category is not compatible with the normalized item type.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="fix_contract",
                blocking_publish=True,
                metadata={"normalized_category": normalized_category, "normalized_item_type": normalized_item_type},
            )
        )

    if not item.evidence_refs:
        findings.append(
            _finding(
                scope="evidence",
                severity="blocked",
                code="item_evidence_missing",
                message="Knowledge item has no evidence reference.",
                target_id=item.object_id,
                target_type=item.object_type,
                suggested_action="add_evidence",
                blocking_publish=True,
            )
        )
    elif not _has_traceable_location(item.evidence_refs):
        findings.append(
            _finding(
                scope="evidence",
                severity="warning",
                code="item_evidence_excerpt_only",
                message="Knowledge item evidence is present but lacks page, chunk, segment, or anchor metadata.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="add_evidence",
                blocking_publish=True,
            )
        )

    explicit_definition_count = _int_quality_value(item.quality_summary.get("explicit_definition_count"))
    if explicit_definition_count <= 0:
        findings.append(
            _finding(
                scope="item",
                severity="warning",
                code="item_definition_missing",
                message="Knowledge item has no explicit definition; evidence excerpts must not be treated as a stable definition.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="add_definition",
                blocking_publish=True,
            )
        )

    if item.conflict_status in {"conflict_pending", "rule_conflict"}:
        findings.append(
            _finding(
                scope="item",
                severity="blocked",
                code="item_conflict_unresolved",
                message="Knowledge item has unresolved conflict status.",
                target_id=item.object_id,
                target_type=item.object_type,
                evidence_refs=item.evidence_refs,
                suggested_action="manual_review",
                blocking_publish=True,
                metadata={"conflict_status": item.conflict_status},
            )
        )

    return findings


def _relation_findings(
    relation: ResolvedKnowledgeRelation,
    object_by_id: dict[str, ResolvedKnowledgeObject],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    contract = get_relation_contract(relation.relation_type)
    normalized_relation_type = normalize_relation_type(relation.relation_type)
    source_object = object_by_id.get(relation.source_object_id)
    target_object = object_by_id.get(relation.target_object_id)

    if contract is None:
        findings.append(
            _finding(
                scope="relation",
                severity="blocked",
                code="relation_type_invalid",
                message="Relation type is outside the relation contract registry.",
                target_id=relation.relation_id,
                target_type=relation.relation_type,
                evidence_refs=relation.evidence_refs,
                suggested_action="fix_contract",
                blocking_publish=True,
                metadata={"normalized_relation_type": normalized_relation_type},
            )
        )
    else:
        source_type = normalize_item_type(source_object.object_type if source_object else None)
        target_type = normalize_item_type(target_object.object_type if target_object else None)
        if source_type not in contract.source_item_types or target_type not in contract.target_item_types:
            findings.append(
                _finding(
                    scope="relation",
                    severity="blocked",
                    code="relation_endpoint_type_incompatible",
                    message="Relation endpoints do not satisfy the relation contract endpoint constraints.",
                    target_id=relation.relation_id,
                    target_type=relation.relation_type,
                    evidence_refs=relation.evidence_refs,
                    suggested_action="fix_contract",
                    blocking_publish=True,
                    metadata={
                        "normalized_relation_type": normalized_relation_type,
                        "source_item_type": source_type,
                        "target_item_type": target_type,
                    },
                )
            )
        if relation.confidence < contract.min_confidence:
            findings.append(
                _finding(
                    scope="relation",
                    severity="warning",
                    code="relation_confidence_below_contract",
                    message="Relation confidence is below the relation contract minimum.",
                    target_id=relation.relation_id,
                    target_type=relation.relation_type,
                    evidence_refs=relation.evidence_refs,
                    suggested_action="manual_review",
                    blocking_publish=True,
                    metadata={
                        "actual_confidence": relation.confidence,
                        "min_confidence": contract.min_confidence,
                        "normalized_relation_type": normalized_relation_type,
                    },
                )
            )
        if contract.evidence_required and not relation.evidence_refs:
            findings.append(
                _finding(
                    scope="relation",
                    severity="blocked",
                    code="relation_evidence_missing",
                    message="Relation contract requires evidence but the relation has no evidence reference.",
                    target_id=relation.relation_id,
                    target_type=relation.relation_type,
                    suggested_action="add_evidence",
                    blocking_publish=True,
                    metadata={"normalized_relation_type": normalized_relation_type},
                )
            )
        elif contract.evidence_required and not _has_traceable_location(relation.evidence_refs):
            findings.append(
                _finding(
                    scope="relation",
                    severity="warning",
                    code="relation_evidence_excerpt_only",
                    message="Relation evidence is present but lacks page, chunk, segment, or anchor metadata.",
                    target_id=relation.relation_id,
                    target_type=relation.relation_type,
                    evidence_refs=relation.evidence_refs,
                    suggested_action="add_evidence",
                    blocking_publish=True,
                    metadata={"normalized_relation_type": normalized_relation_type},
                )
            )

    if source_object is None or target_object is None:
        findings.append(
            _finding(
                scope="relation",
                severity="blocked",
                code="relation_endpoint_missing",
                message="Relation endpoint cannot be resolved to a knowledge object.",
                target_id=relation.relation_id,
                target_type=relation.relation_type,
                evidence_refs=relation.evidence_refs,
                suggested_action="fix_contract",
                blocking_publish=True,
                metadata={
                    "source_object_id": relation.source_object_id,
                    "target_object_id": relation.target_object_id,
                },
            )
        )

    return findings


def _report(
    *,
    archive_id: str,
    generated_at: str,
    resolution_snapshot_id: str | None,
    publication_snapshot_id: str | None,
    findings: list[QualityFinding],
) -> QualityFindingReport:
    return QualityFindingReport(
        report_id=f"QFR-{_digest([archive_id, resolution_snapshot_id, publication_snapshot_id, len(findings)])}",
        archive_id=archive_id,
        generated_at=generated_at,
        resolution_snapshot_id=resolution_snapshot_id,
        publication_snapshot_id=publication_snapshot_id,
        findings=findings,
        summary=summarize_findings(findings),
    )


def _object_category(item: ResolvedKnowledgeObject) -> str:
    if item.identity_key and isinstance(item.identity_key.key_fields, dict):
        category = item.identity_key.key_fields.get("category")
        if isinstance(category, str) and category.strip():
            return category
    return "unknown"


def _has_traceable_location(refs: Iterable[ArtifactRef]) -> bool:
    for ref in refs:
        if ref.artifact_type == "evidence_anchor" or ref.artifact_id.startswith("anchor-"):
            return True
        if any(_has_metadata_value(ref.metadata.get(key)) for key in TRACEABLE_METADATA_KEYS):
            return True
    return False


def _has_metadata_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _int_quality_value(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _finding(
    *,
    scope: str,
    severity: str,
    code: str,
    message: str,
    target_id: str | None = None,
    target_type: str | None = None,
    evidence_refs: list[ArtifactRef] | None = None,
    suggested_action: str = "manual_review",
    blocking_publish: bool = False,
    metadata: dict[str, str | int | float | bool | None] | None = None,
) -> QualityFinding:
    return QualityFinding(
        finding_id=f"QF-{_digest([scope, code, target_id, target_type])}",
        scope=scope,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        target_id=target_id,
        target_type=target_type,
        evidence_refs=evidence_refs or [],
        suggested_action=suggested_action,  # type: ignore[arg-type]
        blocking_publish=blocking_publish,
        metadata=metadata or {},
    )


def _digest(parts: object) -> str:
    return sha1(repr(parts).encode("utf-8")).hexdigest()[:12]
