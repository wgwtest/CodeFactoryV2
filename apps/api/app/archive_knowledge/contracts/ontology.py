from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


KnowledgeItemType = Literal[
    "entity",
    "event",
    "process",
    "rule",
    "metric",
    "constraint",
    "document_artifact",
    "requirement",
    "decision",
    "evidence",
]

KnowledgeCategory = Literal[
    "organization",
    "role",
    "system",
    "service",
    "capability",
    "function",
    "interface",
    "data_object",
    "facility",
    "architecture_artifact",
    "technology",
    "operational_node",
    "stakeholder",
    "document_section",
    "timeline_event",
    "domain_process",
    "unknown",
    "needs_classification",
]


class KnowledgeItemTypeDefinition(BaseModel):
    item_type: str
    label: str
    publishable: bool = True
    extraction_enabled: bool = True
    notes: str | None = None


class KnowledgeCategoryDefinition(BaseModel):
    category: str
    label: str
    allowed_item_types: list[str] = Field(default_factory=list)
    publishable: bool = True
    notes: str | None = None


KNOWLEDGE_ITEM_TYPE_REGISTRY: dict[str, KnowledgeItemTypeDefinition] = {
    "entity": KnowledgeItemTypeDefinition(item_type="entity", label="stable domain object"),
    "event": KnowledgeItemTypeDefinition(item_type="event", label="business or lifecycle event"),
    "process": KnowledgeItemTypeDefinition(item_type="process", label="process with steps or inputs/outputs"),
    "rule": KnowledgeItemTypeDefinition(item_type="rule", label="rule, policy, or condition"),
    "metric": KnowledgeItemTypeDefinition(item_type="metric", label="metric, measure, or threshold"),
    "constraint": KnowledgeItemTypeDefinition(item_type="constraint", label="constraint or limitation"),
    "document_artifact": KnowledgeItemTypeDefinition(
        item_type="document_artifact",
        label="document artifact, view, section, table, or model fragment",
    ),
    "requirement": KnowledgeItemTypeDefinition(
        item_type="requirement",
        label="downstream requirement candidate",
        publishable=False,
        extraction_enabled=False,
        notes="Reserved for P2-facing requirement modeling.",
    ),
    "decision": KnowledgeItemTypeDefinition(
        item_type="decision",
        label="governance or revision decision",
        publishable=False,
        extraction_enabled=False,
        notes="Reserved for governance workflow outputs.",
    ),
    "evidence": KnowledgeItemTypeDefinition(
        item_type="evidence",
        label="evidence object",
        publishable=False,
        extraction_enabled=False,
        notes="Evidence is first-class in the evidence layer, not a business graph node by default.",
    ),
}


KNOWLEDGE_CATEGORY_REGISTRY: dict[str, KnowledgeCategoryDefinition] = {
    "organization": KnowledgeCategoryDefinition(category="organization", label="organization", allowed_item_types=["entity"]),
    "role": KnowledgeCategoryDefinition(category="role", label="role", allowed_item_types=["entity"]),
    "system": KnowledgeCategoryDefinition(category="system", label="system", allowed_item_types=["entity"]),
    "service": KnowledgeCategoryDefinition(category="service", label="service", allowed_item_types=["entity"]),
    "capability": KnowledgeCategoryDefinition(category="capability", label="capability", allowed_item_types=["entity"]),
    "function": KnowledgeCategoryDefinition(category="function", label="function", allowed_item_types=["entity"]),
    "interface": KnowledgeCategoryDefinition(category="interface", label="interface", allowed_item_types=["entity"]),
    "data_object": KnowledgeCategoryDefinition(category="data_object", label="data object", allowed_item_types=["entity"]),
    "facility": KnowledgeCategoryDefinition(category="facility", label="facility", allowed_item_types=["entity"]),
    "architecture_artifact": KnowledgeCategoryDefinition(
        category="architecture_artifact",
        label="architecture artifact",
        allowed_item_types=["entity", "document_artifact"],
    ),
    "technology": KnowledgeCategoryDefinition(category="technology", label="technology", allowed_item_types=["entity"]),
    "operational_node": KnowledgeCategoryDefinition(
        category="operational_node",
        label="operational node",
        allowed_item_types=["entity"],
    ),
    "stakeholder": KnowledgeCategoryDefinition(category="stakeholder", label="stakeholder", allowed_item_types=["entity"]),
    "document_section": KnowledgeCategoryDefinition(
        category="document_section",
        label="document section",
        allowed_item_types=["document_artifact"],
    ),
    "timeline_event": KnowledgeCategoryDefinition(
        category="timeline_event",
        label="timeline event",
        allowed_item_types=["event"],
    ),
    "domain_process": KnowledgeCategoryDefinition(
        category="domain_process",
        label="domain process",
        allowed_item_types=["process"],
    ),
    "unknown": KnowledgeCategoryDefinition(category="unknown", label="unknown", publishable=False),
    "needs_classification": KnowledgeCategoryDefinition(
        category="needs_classification",
        label="needs classification",
        publishable=False,
    ),
}


LEGACY_CATEGORY_MAPPING: dict[str, str] = {
    "系统": "system",
    "system_or_service": "system",
    "service_taxonomy": "service",
    "domain_concept": "needs_classification",
    "architecture_concept": "architecture_artifact",
    "activity": "function",
    "operational_process": "domain_process",
}


LEGACY_ITEM_TYPE_MAPPING: dict[str, str] = {
    "capability": "entity",
    "system": "entity",
    "node": "entity",
    "information_exchange": "entity",
}


def normalize_item_type(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return LEGACY_ITEM_TYPE_MAPPING.get(normalized, normalized)


def is_supported_item_type(value: str | None) -> bool:
    return normalize_item_type(value) in KNOWLEDGE_ITEM_TYPE_REGISTRY


def is_publishable_item_type(value: str | None) -> bool:
    definition = KNOWLEDGE_ITEM_TYPE_REGISTRY.get(normalize_item_type(value))
    return bool(definition and definition.publishable)


def normalize_category(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "unknown"
    normalized = raw.lower().replace("-", "_").replace(" ", "_")
    return LEGACY_CATEGORY_MAPPING.get(raw, LEGACY_CATEGORY_MAPPING.get(normalized, normalized))


def is_supported_category(value: str | None) -> bool:
    return normalize_category(value) in KNOWLEDGE_CATEGORY_REGISTRY


def is_publishable_category(value: str | None) -> bool:
    definition = KNOWLEDGE_CATEGORY_REGISTRY.get(normalize_category(value))
    return bool(definition and definition.publishable)


def category_allows_item_type(category: str | None, item_type: str | None) -> bool:
    category_definition = KNOWLEDGE_CATEGORY_REGISTRY.get(normalize_category(category))
    normalized_item_type = normalize_item_type(item_type)
    if category_definition is None:
        return False
    if not category_definition.allowed_item_types:
        return True
    return normalized_item_type in category_definition.allowed_item_types
