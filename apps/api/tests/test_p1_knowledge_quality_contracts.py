from __future__ import annotations

from app.archive_knowledge.contracts.evidence import build_legacy_evidence_ref, infer_traceability_level
from app.archive_knowledge.contracts.ontology import (
    category_allows_item_type,
    is_publishable_category,
    is_publishable_item_type,
    is_supported_category,
    is_supported_item_type,
    normalize_category,
    normalize_item_type,
)
from app.archive_knowledge.contracts.quality_findings import QualityFinding, summarize_findings
from app.archive_knowledge.contracts.relation_contracts import (
    get_relation_contract,
    normalize_relation_type,
    validate_relation_endpoint_types,
)


def test_ontology_registry_normalizes_legacy_values_without_free_text_publish() -> None:
    assert normalize_item_type("system") == "entity"
    assert is_supported_item_type("rule") is True
    assert is_publishable_item_type("evidence") is False

    assert normalize_category("系统") == "system"
    assert normalize_category("system_or_service") == "system"
    assert normalize_category("domain_concept") == "needs_classification"
    assert is_supported_category("service_taxonomy") is True
    assert is_publishable_category("needs_classification") is False
    assert category_allows_item_type("domain_process", "process") is True
    assert category_allows_item_type("domain_process", "entity") is False


def test_evidence_contract_keeps_legacy_excerpt_but_marks_traceability() -> None:
    evidence = build_legacy_evidence_ref(
        document_id="doc-1",
        excerpt="  Alpha   system is described in the source.  ",
        evidence_role="definition",
        supports_field="definition",
    )

    assert evidence.document_id == "doc-1"
    assert evidence.normalized_excerpt == "Alpha system is described in the source."
    assert evidence.traceability_level == "excerpt"
    assert infer_traceability_level(evidence) == "excerpt"

    anchored = evidence.model_copy(update={"anchor_ids": ["anchor-1"]})
    assert infer_traceability_level(anchored) == "anchored"


def test_relation_contract_registry_maps_legacy_types_and_validates_endpoints() -> None:
    assert normalize_relation_type("operational_exchange") == "exchanges_with"
    contract = get_relation_contract("constrains")

    assert contract is not None
    assert contract.evidence_required is True
    assert contract.min_confidence >= 0.75
    assert validate_relation_endpoint_types("constrains", "rule", "process") is True
    assert validate_relation_endpoint_types("constrains", "entity", "process") is False
    assert validate_relation_endpoint_types("unknown_relation", "entity", "entity") is False


def test_quality_finding_summary_marks_publication_blockers() -> None:
    findings = [
        QualityFinding(
            finding_id="item-1-definition",
            scope="item",
            severity="blocked",
            code="definition_missing",
            message="Definition is required before publication.",
            target_id="item-1",
            target_type="entity",
            suggested_action="add_definition",
            blocking_publish=True,
        ),
        QualityFinding(
            finding_id="relation-1-evidence",
            scope="relation",
            severity="warning",
            code="relation_evidence_weak",
            message="Relation evidence is excerpt-only.",
            target_id="relation-1",
            target_type="relation",
            suggested_action="add_evidence",
        ),
    ]

    summary = summarize_findings(findings)

    assert summary.finding_count == 2
    assert summary.blocked_count == 1
    assert summary.warning_count == 1
    assert summary.publish_blocked is True
