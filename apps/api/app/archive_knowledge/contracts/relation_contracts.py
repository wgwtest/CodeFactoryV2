from __future__ import annotations

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.ontology import normalize_item_type


class RelationContract(BaseModel):
    relation_type: str
    relation_family: str
    source_item_types: list[str] = Field(default_factory=list)
    target_item_types: list[str] = Field(default_factory=list)
    source_categories: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    direction_semantics: str
    inverse_relation_type: str | None = None
    evidence_required: bool = True
    anchor_required: bool = False
    min_confidence: float = Field(default=0.65, ge=0, le=1)
    publish_allowed: bool = True
    manual_review_required: bool = False


RELATION_CONTRACT_REGISTRY: dict[str, RelationContract] = {
    "contains": RelationContract(
        relation_type="contains",
        relation_family="structure",
        source_item_types=["entity", "document_artifact"],
        target_item_types=["entity", "document_artifact"],
        direction_semantics="source contains target",
        inverse_relation_type="part_of",
    ),
    "part_of": RelationContract(
        relation_type="part_of",
        relation_family="structure",
        source_item_types=["entity", "document_artifact"],
        target_item_types=["entity", "document_artifact"],
        direction_semantics="source is part of target",
        inverse_relation_type="contains",
    ),
    "decomposes_to": RelationContract(
        relation_type="decomposes_to",
        relation_family="structure",
        source_item_types=["entity", "process", "document_artifact"],
        target_item_types=["entity", "process", "document_artifact"],
        direction_semantics="source decomposes to target",
        inverse_relation_type=None,
    ),
    "owned_by": RelationContract(
        relation_type="owned_by",
        relation_family="responsibility",
        source_item_types=["entity", "process", "document_artifact"],
        target_item_types=["entity"],
        target_categories=["organization", "role", "stakeholder"],
        direction_semantics="source is owned by target",
        inverse_relation_type=None,
    ),
    "responsible_for": RelationContract(
        relation_type="responsible_for",
        relation_family="responsibility",
        source_item_types=["entity"],
        source_categories=["organization", "role", "stakeholder"],
        target_item_types=["entity", "process", "rule", "constraint"],
        direction_semantics="source is responsible for target",
        inverse_relation_type=None,
    ),
    "has_step": RelationContract(
        relation_type="has_step",
        relation_family="process",
        source_item_types=["process"],
        target_item_types=["process", "entity"],
        direction_semantics="source process has step target",
        inverse_relation_type=None,
    ),
    "precedes": RelationContract(
        relation_type="precedes",
        relation_family="process",
        source_item_types=["process", "event"],
        target_item_types=["process", "event"],
        direction_semantics="source precedes target",
        inverse_relation_type=None,
    ),
    "consumes": RelationContract(
        relation_type="consumes",
        relation_family="process",
        source_item_types=["process", "entity"],
        target_item_types=["entity"],
        direction_semantics="source consumes target",
        inverse_relation_type=None,
    ),
    "produces": RelationContract(
        relation_type="produces",
        relation_family="process",
        source_item_types=["process", "entity"],
        target_item_types=["entity"],
        direction_semantics="source produces target",
        inverse_relation_type=None,
    ),
    "exchanges_with": RelationContract(
        relation_type="exchanges_with",
        relation_family="data_interface",
        source_item_types=["entity"],
        target_item_types=["entity"],
        direction_semantics="source exchanges information with target",
        inverse_relation_type="exchanges_with",
    ),
    "sends": RelationContract(
        relation_type="sends",
        relation_family="data_interface",
        source_item_types=["entity"],
        target_item_types=["entity"],
        direction_semantics="source sends data or information to target",
        inverse_relation_type="receives",
    ),
    "receives": RelationContract(
        relation_type="receives",
        relation_family="data_interface",
        source_item_types=["entity"],
        target_item_types=["entity"],
        direction_semantics="source receives data or information from target",
        inverse_relation_type="sends",
    ),
    "provides_interface": RelationContract(
        relation_type="provides_interface",
        relation_family="data_interface",
        source_item_types=["entity"],
        target_item_types=["entity"],
        target_categories=["interface"],
        direction_semantics="source provides interface target",
        inverse_relation_type="uses_interface",
    ),
    "uses_interface": RelationContract(
        relation_type="uses_interface",
        relation_family="data_interface",
        source_item_types=["entity", "process"],
        target_item_types=["entity"],
        target_categories=["interface"],
        direction_semantics="source uses interface target",
        inverse_relation_type="provides_interface",
    ),
    "constrains": RelationContract(
        relation_type="constrains",
        relation_family="rule_metric",
        source_item_types=["rule", "constraint"],
        target_item_types=["entity", "process", "rule"],
        direction_semantics="source constrains target",
        inverse_relation_type=None,
        min_confidence=0.75,
    ),
    "applies_to": RelationContract(
        relation_type="applies_to",
        relation_family="rule_metric",
        source_item_types=["rule", "metric", "constraint"],
        target_item_types=["entity", "process", "document_artifact"],
        direction_semantics="source applies to target",
        inverse_relation_type=None,
    ),
    "measures": RelationContract(
        relation_type="measures",
        relation_family="rule_metric",
        source_item_types=["metric"],
        target_item_types=["entity", "process", "rule", "constraint"],
        direction_semantics="source measures target",
        inverse_relation_type=None,
    ),
    "evidenced_by": RelationContract(
        relation_type="evidenced_by",
        relation_family="governance",
        source_item_types=["entity", "event", "process", "rule", "metric", "constraint", "document_artifact"],
        target_item_types=["evidence"],
        direction_semantics="source is supported by target evidence",
        inverse_relation_type=None,
        publish_allowed=False,
    ),
    "derived_from": RelationContract(
        relation_type="derived_from",
        relation_family="governance",
        source_item_types=["entity", "event", "process", "rule", "metric", "constraint"],
        target_item_types=["document_artifact", "evidence"],
        direction_semantics="source is derived from target",
        inverse_relation_type=None,
        publish_allowed=False,
    ),
    "conflicts_with": RelationContract(
        relation_type="conflicts_with",
        relation_family="governance",
        source_item_types=["entity", "event", "process", "rule", "metric", "constraint"],
        target_item_types=["entity", "event", "process", "rule", "metric", "constraint"],
        direction_semantics="source conflicts with target",
        inverse_relation_type="conflicts_with",
        publish_allowed=False,
        manual_review_required=True,
    ),
    "updates": RelationContract(
        relation_type="updates",
        relation_family="governance",
        source_item_types=["entity", "event", "process", "rule", "metric", "constraint"],
        target_item_types=["entity", "event", "process", "rule", "metric", "constraint"],
        direction_semantics="source updates target",
        inverse_relation_type=None,
        manual_review_required=True,
    ),
}


LEGACY_RELATION_TYPE_MAPPING: dict[str, str] = {
    "operational_exchange": "exchanges_with",
    "participates_in_exchange": "exchanges_with",
    "process_scoped_by": "applies_to",
    "scoped_by": "applies_to",
    "describes": "derived_from",
    "depends_on": "uses_interface",
    "support": "applies_to",
    "supports": "applies_to",
    "composition": "part_of",
    "exchange": "exchanges_with",
    "constraint": "constrains",
}


def normalize_relation_type(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return LEGACY_RELATION_TYPE_MAPPING.get(normalized, normalized)


def get_relation_contract(value: str | None) -> RelationContract | None:
    return RELATION_CONTRACT_REGISTRY.get(normalize_relation_type(value))


def validate_relation_endpoint_types(
    relation_type: str | None,
    source_item_type: str | None,
    target_item_type: str | None,
) -> bool:
    contract = get_relation_contract(relation_type)
    if contract is None:
        return False
    normalized_source = normalize_item_type(source_item_type)
    normalized_target = normalize_item_type(target_item_type)
    return normalized_source in contract.source_item_types and normalized_target in contract.target_item_types
