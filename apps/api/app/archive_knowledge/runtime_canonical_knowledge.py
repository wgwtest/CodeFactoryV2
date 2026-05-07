from __future__ import annotations

from collections import Counter
from typing import Any

from app.archive_knowledge.runtime_contract import (
    RuntimeAction,
    RuntimeEvent,
    RuntimeGraphEdge,
    RuntimeGraphNode,
    RuntimeObserverMode,
    RuntimeObserverPayload,
    RuntimeOrigin,
    RuntimeStageSnapshot,
    RuntimeStatus,
    RuntimeSummaryField,
    RuntimeSummarySection,
    STAGE_DEFINITION_MAP,
)


def build_canonical_knowledge_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    knowledge_items: list[dict[str, Any]],
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["canonical_knowledge"]
    knowledge_items = list(knowledge_items)
    relations = list(contribution.get("relations", []))

    item_count = len(knowledge_items)
    relation_count = len(relations)
    status = RuntimeStatus.COMPLETED if item_count else RuntimeStatus.WARNING

    input_set_id = f"{document_id}:canonical:input-set"
    policy_node_id = f"{document_id}:canonical:canonicalization-policy"
    item_set_id = f"{document_id}:canonical:item-set"
    relation_set_id = f"{document_id}:canonical:relation-set"
    merge_decision_id = f"{document_id}:canonical:merge-decisions"
    dropped_candidate_id = f"{document_id}:canonical:dropped-candidates"
    warning_id = f"{document_id}:canonical:warning"

    item_type_counter = Counter(item.get("item_type") or "item" for item in knowledge_items)

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=input_set_id,
            label="整合候选集合",
            node_type="canonical_candidate_input_set",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"candidate_count": item_count, "relation_count": relation_count},
            attributes={
                "source_stage": "definition_summary_conflict_consolidation",
                "aggregation": "semantic",
            },
        ),
        RuntimeGraphNode(
            node_id=policy_node_id,
            label="规范化策略",
            node_type="canonicalization_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"merged_item_count": item_count, "relation_count": relation_count},
            attributes={
                "rule_key": "canonical_knowledge.merge_and_normalize",
                "default_action": "merge_supported_candidates",
                "review_scope": "canonical_items_and_relations",
            },
        ),
        RuntimeGraphNode(
            node_id=item_set_id,
            label="规范知识对象集合",
            node_type="canonical_item_set",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "item_count": item_count,
                "entity_count": item_type_counter.get("entity", 0),
                "event_count": item_type_counter.get("event", 0),
                "process_count": item_type_counter.get("process", 0),
            },
        ),
        RuntimeGraphNode(
            node_id=relation_set_id,
            label="规范关系集合",
            node_type="canonical_relation_set",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if relation_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"relation_count": relation_count},
        ),
        RuntimeGraphNode(
            node_id=merge_decision_id,
            label="合并决策",
            node_type="merge_decision_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"merged_item_count": item_count},
        ),
        RuntimeGraphNode(
            node_id=dropped_candidate_id,
            label="剔除候选集合",
            node_type="dropped_candidate_group",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.DERIVED,
            metrics={"dropped_candidate_count": 0},
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{input_set_id}:feeds-policy",
            source=input_set_id,
            target=policy_node_id,
            relation="feeds_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "consolidated definitions, summaries, conflicts, and relations"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{policy_node_id}:governs-merge",
            source=policy_node_id,
            target=merge_decision_id,
            relation="governs",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "canonical merge, dedupe, and relation exposure policy"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{merge_decision_id}:results_in",
            source=merge_decision_id,
            target=item_set_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{item_set_id}:supports",
            source=item_set_id,
            target=relation_set_id,
            relation="supports",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if relation_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    item_node_id_map: dict[str, str] = {}
    name_index: dict[str, str] = {}
    item_node_ids: list[str] = []
    for index, item in enumerate(knowledge_items, start=1):
        node_id = f"{document_id}:canonical:item:{index}"
        item_node_ids.append(node_id)
        item_node_id_map[item.get("id") or node_id] = node_id
        for candidate_name in _candidate_names(item):
            name_index.setdefault(candidate_name, node_id)
        nodes.append(
            RuntimeGraphNode(
                node_id=node_id,
                label=item.get("name") or item.get("id") or f"canonical-item-{index}",
                node_type=f"canonical_{item.get('item_type') or 'item'}",
                stage_id=definition.stage_id,
                status=_review_status_to_runtime(item.get("review_status", "pending")),
                origin=RuntimeOrigin.SOURCE,
                metrics={"evidence_count": len(item.get("evidence", []))},
                attributes={
                    "item_id": item.get("id"),
                    "item_type": item.get("item_type") or "item",
                    "category": item.get("category"),
                    "review_status": item.get("review_status", "pending"),
                    "alias_count": len(item.get("aliases", [])),
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{item_set_id}:item:{index}",
                source=item_set_id,
                target=node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=_review_status_to_runtime(item.get("review_status", "pending")),
                origin=RuntimeOrigin.SOURCE,
            )
        )

    relation_edge_ids: list[str] = []
    for index, relation in enumerate(relations, start=1):
        source_node_id = _resolve_relation_endpoint(
            relation.get("source_name"),
            knowledge_items=knowledge_items,
            name_index=name_index,
            item_node_id_map=item_node_id_map,
        )
        target_node_id = _resolve_relation_endpoint(
            relation.get("target_name"),
            knowledge_items=knowledge_items,
            name_index=name_index,
            item_node_id_map=item_node_id_map,
        )
        if source_node_id is None or target_node_id is None:
            continue
        edge_id = f"{document_id}:canonical:relation:{index}"
        relation_edge_ids.append(edge_id)
        edges.append(
            RuntimeGraphEdge(
                edge_id=edge_id,
                source=source_node_id,
                target=target_node_id,
                relation=relation.get("type") or "related_to",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={
                    "confidence": str(relation.get("confidence") or ""),
                    "evidence": relation.get("evidence") or "",
                    "source_name": relation.get("source_name") or "",
                    "target_name": relation.get("target_name") or "",
                },
            )
        )

    if not knowledge_items:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Canonical Knowledge Warning",
                node_type="canonical_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"message": "No canonical items were materialized for the current document."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{merge_decision_id}:warned_by",
                source=merge_decision_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Canonical Knowledge",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:canonical:start",
                kind="progress",
                level="info",
                message="Canonical knowledge is consolidating concept, relation, and definition outputs into normalized document-scoped objects.",
                object_id=merge_decision_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:canonical:result",
                kind="result",
                level="success" if item_count else "warning",
                message=(
                    f"Canonical consolidation produced {item_count} items and {len(relation_edge_ids)} relation edges."
                    if item_count
                    else "Canonical consolidation completed without materialized canonical items."
                ),
                object_id=item_set_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="canonical-summary",
                title="Canonical Summary",
                fields=[
                    RuntimeSummaryField(key="item_count", label="item_count", value=str(item_count), tone="success" if item_count else "warning"),
                    RuntimeSummaryField(key="relation_count", label="relation_count", value=str(len(relation_edge_ids)), tone="info"),
                    RuntimeSummaryField(key="entity_count", label="entity_count", value=str(item_type_counter.get("entity", 0)), tone="info"),
                    RuntimeSummaryField(key="process_count", label="process_count", value=str(item_type_counter.get("process", 0)), tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="review-distribution",
                title="Review Distribution",
                fields=[
                    RuntimeSummaryField(key="approved_count", label="approved_count", value=str(sum(1 for item in knowledge_items if item.get("review_status") == "approved")), tone="success"),
                    RuntimeSummaryField(key="pending_count", label="pending_count", value=str(sum(1 for item in knowledge_items if item.get("review_status", "pending") == "pending")), tone="warning"),
                    RuntimeSummaryField(key="rejected_count", label="rejected_count", value=str(sum(1 for item in knowledge_items if item.get("review_status") == "rejected")), tone="danger"),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(action_id="view-canonical-set", label="View Canonical Item Set", target_kind="node", target_id=item_set_id),
        ],
    )

    node_observers: dict[str, RuntimeObserverPayload] = {
        input_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="整合候选集合",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:canonical:input-set",
                    kind="progress",
                    level="success" if item_count else "warning",
                    message=f"规范知识阶段接收上游 {item_count} 个整合候选和 {relation_count} 条关系候选。",
                    object_id=input_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="input-set",
                    title="输入集合",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="canonical_candidate_input_set"),
                        RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(item_count), tone="success" if item_count else "warning"),
                        RuntimeSummaryField(key="source_stage", label="source_stage", value="definition_summary_conflict_consolidation", tone="info"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-policy", label="查看规范化策略", target_kind="node", target_id=policy_node_id),
            ],
        ),
        policy_node_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="规范化策略",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:canonical:policy",
                    kind="decision",
                    level="success" if item_count else "warning",
                    message="规范化策略会在质量评估前，把受支撑的候选合并为稳定的规范知识对象和关系集合。",
                    object_id=policy_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-basis",
                    title="策略 / 动作依据",
                    fields=[
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="canonical_knowledge.merge_and_normalize", tone="info"),
                        RuntimeSummaryField(key="default_action", label="default_action", value="merge_supported_candidates", tone="info"),
                        RuntimeSummaryField(key="merged_item_count", label="merged_item_count", value=str(item_count), tone="success" if item_count else "warning"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-input-set", label="查看整合输入集合", target_kind="node", target_id=input_set_id),
                RuntimeAction(action_id="view-merge-decisions", label="查看合并决策", target_kind="node", target_id=merge_decision_id),
            ],
        ),
        item_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Canonical Item Set",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:canonical:item-set",
                    kind="result",
                    level="success" if item_count else "warning",
                    message=f"The current document contributes {item_count} canonical items into the normalized item set.",
                    object_id=item_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="canonical_item_set"),
                        RuntimeSummaryField(key="item_count", label="item_count", value=str(item_count)),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="composition",
                    title="Composition",
                    fields=[
                        RuntimeSummaryField(key="entity_count", label="entity_count", value=str(item_type_counter.get("entity", 0))),
                        RuntimeSummaryField(key="event_count", label="event_count", value=str(item_type_counter.get("event", 0))),
                        RuntimeSummaryField(key="process_count", label="process_count", value=str(item_type_counter.get("process", 0))),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-merge-decisions", label="查看合并决策", target_kind="node", target_id=merge_decision_id),
                RuntimeAction(action_id="view-canonical-relations", label="查看规范关系集合", target_kind="node", target_id=relation_set_id),
            ],
        ),
        relation_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Canonical Relation Set",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if relation_edge_ids else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:canonical:relation-set",
                    kind="result",
                    level="success" if relation_edge_ids else "warning",
                    message=f"The canonical relation layer currently materializes {len(relation_edge_ids)} relations between canonical items.",
                    object_id=relation_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="canonical_relation_set"),
                        RuntimeSummaryField(key="relation_count", label="relation_count", value=str(len(relation_edge_ids))),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-stage-graph", label="查看阶段图谱", target_kind="graph"),
            ],
        ),
        merge_decision_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Merge Decisions",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:canonical:merge",
                    kind="decision",
                    level="info",
                    message="合并决策会在治理评估前，把候选输出收敛为规范对象。",
                    object_id=merge_decision_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="merge-summary",
                    title="Merge Summary",
                    fields=[
                        RuntimeSummaryField(key="merged_item_count", label="merged_item_count", value=str(item_count)),
                        RuntimeSummaryField(key="dropped_candidate_count", label="dropped_candidate_count", value="0"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-item-set", label="查看规范知识对象集合", target_kind="node", target_id=item_set_id),
            ],
        ),
    }

    for index, item in enumerate(knowledge_items, start=1):
        node_id = f"{document_id}:canonical:item:{index}"
        node_observers[node_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Canonical Item",
            subtitle=item.get("name") or item.get("id") or node_id,
            status=_review_status_to_runtime(item.get("review_status", "pending")),
            stream=[
                RuntimeEvent(
                    event_id=f"{node_id}:item",
                    kind="result",
                    level="success" if item.get("review_status") == "approved" else "warning",
                    message=f"Canonical item '{item.get('name') or item.get('id')}' is available for downstream governance with {len(item.get('evidence', []))} evidence records.",
                    object_id=node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="item_id", label="item_id", value=str(item.get("id") or "")),
                        RuntimeSummaryField(key="item_type", label="item_type", value=str(item.get("item_type") or "item")),
                        RuntimeSummaryField(key="review_status", label="review_status", value=str(item.get("review_status", "pending"))),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="content",
                    title="Canonical Content",
                    fields=[
                        RuntimeSummaryField(key="category", label="category", value=str(item.get("category") or "unknown")),
                        RuntimeSummaryField(key="alias_count", label="alias_count", value=str(len(item.get("aliases", [])))),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(len(item.get("evidence", [])))),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-item-set", label="View Canonical Item Set", target_kind="node", target_id=item_set_id),
                RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            ],
        )

    edge_observers: dict[str, RuntimeObserverPayload] = {}
    for edge in edges:
        edge_observers[edge.edge_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title=f"Canonical Relation · {edge.relation}",
            subtitle=document_title,
            status=edge.status,
            stream=[
                RuntimeEvent(
                    event_id=f"{edge.edge_id}:relation",
                    kind="result",
                    level="info",
                    message=f"The '{edge.relation}' relation links canonical objects within the normalized knowledge layer.",
                    object_id=edge.edge_id,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="source", label="source", value=edge.source),
                        RuntimeSummaryField(key="target", label="target", value=edge.target),
                        RuntimeSummaryField(key="relation", label="relation", value=edge.relation),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View Source Node", target_kind="node", target_id=edge.source),
                RuntimeAction(action_id="view-target-node", label="View Target Node", target_kind="node", target_id=edge.target),
            ],
        )

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=status,
        graph={
            "nodes": nodes,
            "edges": edges,
            "primary_node_ids": [
                input_set_id,
                policy_node_id,
                merge_decision_id,
                item_set_id,
                relation_set_id,
            ],
            "primary_edge_ids": [
                f"{input_set_id}:feeds-policy",
                f"{policy_node_id}:governs-merge",
                f"{merge_decision_id}:results_in",
                f"{item_set_id}:supports",
            ],
        },
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _candidate_names(item: dict[str, Any]) -> list[str]:
    names = [item.get("name") or ""]
    names.extend(item.get("aliases", []))
    return [normalized for value in names if (normalized := _normalize_name(value))]


def _normalize_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _resolve_relation_endpoint(
    name: str | None,
    *,
    knowledge_items: list[dict[str, Any]],
    name_index: dict[str, str],
    item_node_id_map: dict[str, str],
) -> str | None:
    normalized = _normalize_name(name)
    if not normalized:
        return None
    if normalized in name_index:
        return name_index[normalized]
    for item in knowledge_items:
        if _normalize_name(item.get("id")) == normalized:
            node_id = item_node_id_map.get(item.get("id") or "")
            if node_id is not None:
                return node_id
    return None


def _review_status_to_runtime(review_status: str) -> RuntimeStatus:
    normalized = (review_status or "pending").strip().lower()
    if normalized == "approved":
        return RuntimeStatus.COMPLETED
    if normalized == "rejected":
        return RuntimeStatus.BLOCKED
    return RuntimeStatus.WARNING
