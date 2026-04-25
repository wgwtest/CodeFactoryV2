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
    RuntimeStageGraph,
    RuntimeStageSnapshot,
    RuntimeStatus,
    RuntimeSummaryField,
    RuntimeSummarySection,
    STAGE_DEFINITION_MAP,
)


def build_relation_review_family_normalization_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["relation_review_family_normalization"]
    all_items = _collect_items(contribution)
    relations = list(contribution.get("relations", []))
    family_groups = _build_family_groups(all_items)
    relation_count = len(relations)
    family_count = len(family_groups)
    alias_count = sum(len(group["aliases"]) for group in family_groups)
    status = RuntimeStatus.COMPLETED if relation_count or family_count else RuntimeStatus.WARNING

    relation_set_id = f"{document_id}:relation-review:set"
    policy_node_id = f"{document_id}:relation-review:review-policy"
    family_norm_id = f"{document_id}:relation-review:family-normalization"
    family_group_root_id = f"{document_id}:relation-review:family-groups"
    warning_id = f"{document_id}:relation-review:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=relation_set_id,
            label="关系候选集合",
            node_type="relation_candidate_set",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if relation_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"relation_count": relation_count},
        ),
        RuntimeGraphNode(
            node_id=policy_node_id,
            label="关系审查策略",
            node_type="relation_review_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"relation_count": relation_count, "family_count": family_count, "alias_count": alias_count},
            attributes={
                "rule_key": "relation_review_family_normalization.endpoint_family_policy",
                "default_action": "normalize_relation_endpoints",
                "review_scope": "relation_candidates_and_alias_families",
            },
        ),
        RuntimeGraphNode(
            node_id=family_norm_id,
            label="家族归一",
            node_type="family_normalization",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"family_count": family_count, "alias_count": alias_count},
        ),
        RuntimeGraphNode(
            node_id=family_group_root_id,
            label="家族集合",
            node_type="family_group_root",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"family_count": family_count},
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{relation_set_id}:feeds-policy",
            source=relation_set_id,
            target=policy_node_id,
            relation="feeds_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "relation candidates with source and target endpoints"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{policy_node_id}:governs-family-normalization",
            source=policy_node_id,
            target=family_norm_id,
            relation="governs",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "endpoint alias resolution and family grouping"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{relation_set_id}:normalized_by",
            source=relation_set_id,
            target=family_norm_id,
            relation="normalized_by",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
        ),
        RuntimeGraphEdge(
            edge_id=f"{family_norm_id}:contains",
            source=family_norm_id,
            target=family_group_root_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    family_node_ids: dict[str, str] = {}
    node_observers: dict[str, RuntimeObserverPayload] = {
        policy_node_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="关系审查策略",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:relation-review:policy",
                    kind="decision",
                    level="success" if relation_count or family_count else "warning",
                    message="关系审查策略会把关系端点解析到家族集合，并在形成发布候选前归一别名与方向。",
                    object_id=policy_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-basis",
                    title="策略 / 动作依据",
                    fields=[
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="relation_review_family_normalization.endpoint_family_policy", tone="info"),
                        RuntimeSummaryField(key="default_action", label="default_action", value="normalize_relation_endpoints", tone="info"),
                        RuntimeSummaryField(key="family_count", label="family_count", value=str(family_count), tone="success" if family_count else "warning"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-relation-set", label="查看关系集合", target_kind="node", target_id=relation_set_id),
                RuntimeAction(action_id="view-family-normalization", label="查看家族归一", target_kind="node", target_id=family_norm_id),
            ],
        ),
        relation_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Relation Candidate Set",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if relation_count else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:relation-review:set",
                    kind="result",
                    level="success" if relation_count else "warning",
                    message=(
                        f"Relation review assembled {relation_count} relation candidates for normalization."
                        if relation_count
                        else "Relation review did not materialize any relation candidates."
                    ),
                    object_id=relation_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation-set",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="relation_candidate_set"),
                        RuntimeSummaryField(key="relation_count", label="relation_count", value=str(relation_count), tone="success" if relation_count else "warning"),
                        RuntimeSummaryField(key="family_count", label="family_count", value=str(family_count), tone="info"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-stage-graph", label="查看阶段图谱", target_kind="graph"),
            ],
        ),
    }
    edge_observers: dict[str, RuntimeObserverPayload] = {
        f"{relation_set_id}:feeds-policy": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="送入策略",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:relation-review:feeds-policy",
                    kind="decision",
                    level="success" if relation_count else "warning",
                    message="关系候选会先送入端点家族策略，再执行归一化。",
                    object_id=f"{relation_set_id}:feeds-policy",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-edge",
                    title="动作依据",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="feeds_policy"),
                        RuntimeSummaryField(key="relation_count", label="relation_count", value=str(relation_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=relation_set_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=policy_node_id),
            ],
        ),
        f"{policy_node_id}:governs-family-normalization": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="governs",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:relation-review:governs-family-normalization",
                    kind="decision",
                    level="success" if family_count else "warning",
                    message="端点家族策略决定别名聚合与家族归一的输出。",
                    object_id=f"{policy_node_id}:governs-family-normalization",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-edge",
                    title="策略决策",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="governs"),
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="relation_review_family_normalization.endpoint_family_policy"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=policy_node_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=family_norm_id),
            ],
        ),
        f"{relation_set_id}:normalized_by": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="normalized_by",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:relation-review:normalized-by",
                    kind="decision",
                    level="success" if family_count else "warning",
                    message=(
                        f"Relation candidates were normalized through {family_count} family groups."
                        if family_count
                        else "No family groups were materialized during relation review."
                    ),
                    object_id=f"{relation_set_id}:normalized_by",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="normalized_by"),
                        RuntimeSummaryField(key="family_count", label="family_count", value=str(family_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=relation_set_id),
                RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=family_norm_id),
            ],
        ),
    }

    for family_index, group in enumerate(family_groups, start=1):
        family_node_id = f"{document_id}:relation-review:family:{family_index}"
        family_node_ids[group["key"]] = family_node_id
        nodes.append(
            RuntimeGraphNode(
                node_id=family_node_id,
                label=group["label"],
                node_type="family_group",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                metrics={"member_count": group["member_count"], "alias_count": len(group["aliases"])},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{family_group_root_id}:family:{family_index}",
                source=family_group_root_id,
                target=family_node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
            )
        )

        node_observers[family_node_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Family Group",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{family_node_id}:event",
                    kind="result",
                    level="info",
                    message=f"Family group {group['label']} currently contains {group['member_count']} members and {len(group['aliases'])} aliases.",
                    object_id=family_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="family-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="label", label="label", value=group["label"]),
                        RuntimeSummaryField(key="member_count", label="member_count", value=str(group["member_count"])),
                        RuntimeSummaryField(key="alias_count", label="alias_count", value=str(len(group["aliases"]))),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-family-root", label="View family root", target_kind="node", target_id=family_group_root_id),
            ],
        )

        for alias_index, alias in enumerate(group["aliases"], start=1):
            alias_node_id = f"{family_node_id}:alias:{alias_index}"
            nodes.append(
                RuntimeGraphNode(
                    node_id=alias_node_id,
                    label=alias,
                    node_type="family_alias",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.SOURCE,
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{family_node_id}:alias:{alias_index}",
                    source=family_node_id,
                    target=alias_node_id,
                    relation="contains",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.SOURCE,
                )
            )

    for index, relation in enumerate(relations, start=1):
        relation_node_id = f"{document_id}:relation-review:candidate:{index}"
        relation_type = relation.get("type") or "related_to"
        source_family_key = _resolve_family_key(relation.get("source_name"), all_items)
        target_family_key = _resolve_family_key(relation.get("target_name"), all_items)
        nodes.append(
            RuntimeGraphNode(
                node_id=relation_node_id,
                label=relation_type,
                node_type="relation_candidate",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={
                    "source_name": relation.get("source_name") or "",
                    "target_name": relation.get("target_name") or "",
                    "confidence": relation.get("confidence"),
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{relation_set_id}:relation:{index}",
                source=relation_set_id,
                target=relation_node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
            )
        )
        if source_family_key and source_family_key in family_node_ids:
            edge_id = f"{relation_node_id}:source-family"
            edges.append(
                RuntimeGraphEdge(
                    edge_id=edge_id,
                    source=relation_node_id,
                    target=family_node_ids[source_family_key],
                    relation="belongs_to_family",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )
            edge_observers[edge_id] = RuntimeObserverPayload(
                mode=RuntimeObserverMode.EDGE,
                title="belongs_to_family",
                subtitle=document_title,
                status=RuntimeStatus.COMPLETED,
                stream=[
                    RuntimeEvent(
                        event_id=f"{edge_id}:event",
                        kind="result",
                        level="info",
                        message=f"Source endpoint {relation.get('source_name') or 'unknown'} is normalized into family {source_family_key}.",
                        object_id=edge_id,
                        object_kind="edge",
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="relation-summary",
                        title="Relation Summary",
                        fields=[
                            RuntimeSummaryField(key="relation", label="relation", value="belongs_to_family"),
                            RuntimeSummaryField(key="endpoint_role", label="endpoint_role", value="source"),
                            RuntimeSummaryField(key="family", label="family", value=source_family_key),
                        ],
                    )
                ],
                actions=[
                    RuntimeAction(action_id="view-relation-node", label="View relation node", target_kind="node", target_id=relation_node_id),
                    RuntimeAction(action_id="view-family-node", label="View family node", target_kind="node", target_id=family_node_ids[source_family_key]),
                ],
            )
        if target_family_key and target_family_key in family_node_ids:
            edge_id = f"{relation_node_id}:target-family"
            edges.append(
                RuntimeGraphEdge(
                    edge_id=edge_id,
                    source=relation_node_id,
                    target=family_node_ids[target_family_key],
                    relation="belongs_to_family",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )
            edge_observers[edge_id] = RuntimeObserverPayload(
                mode=RuntimeObserverMode.EDGE,
                title="belongs_to_family",
                subtitle=document_title,
                status=RuntimeStatus.COMPLETED,
                stream=[
                    RuntimeEvent(
                        event_id=f"{edge_id}:event",
                        kind="result",
                        level="info",
                        message=f"Target endpoint {relation.get('target_name') or 'unknown'} is normalized into family {target_family_key}.",
                        object_id=edge_id,
                        object_kind="edge",
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="relation-summary",
                        title="Relation Summary",
                        fields=[
                            RuntimeSummaryField(key="relation", label="relation", value="belongs_to_family"),
                            RuntimeSummaryField(key="endpoint_role", label="endpoint_role", value="target"),
                            RuntimeSummaryField(key="family", label="family", value=target_family_key),
                        ],
                    )
                ],
                actions=[
                    RuntimeAction(action_id="view-relation-node", label="View relation node", target_kind="node", target_id=relation_node_id),
                    RuntimeAction(action_id="view-family-node", label="View family node", target_kind="node", target_id=family_node_ids[target_family_key]),
                ],
            )

        node_observers[relation_node_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Relation Candidate",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{relation_node_id}:event",
                    kind="result",
                    level="success",
                    message=f"Relation candidate {relation_type} links {relation.get('source_name') or 'unknown'} to {relation.get('target_name') or 'unknown'}.",
                    object_id=relation_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="relation_type", label="relation_type", value=relation_type),
                        RuntimeSummaryField(key="source_name", label="source_name", value=relation.get("source_name") or "unknown"),
                        RuntimeSummaryField(key="target_name", label="target_name", value=relation.get("target_name") or "unknown"),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="relation-context",
                    title="Context and Confidence",
                    fields=[
                        RuntimeSummaryField(key="confidence", label="confidence", value=str(relation.get("confidence") or "")),
                        RuntimeSummaryField(key="has_alias_family", label="has_alias_family", value="true" if source_family_key or target_family_key else "false"),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-relation-set", label="View relation set", target_kind="node", target_id=relation_set_id),
            ],
        )

    if not relation_count and not family_count:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Relation Review Warning",
                node_type="relation_review_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"message": "No relation candidates or family groups were materialized for the current document."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{family_norm_id}:warned_by",
                source=family_norm_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Relation Review / Family Normalization",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:relation-review:start",
                kind="progress",
                level="info",
                message="Relation review is normalizing relation candidates and resolving endpoint families for the current document.",
                object_id=relation_set_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:relation-review:result",
                kind="result",
                level="success" if relation_count or family_count else "warning",
                message=(
                    f"Relation review produced {relation_count} relation candidates across {family_count} family groups."
                    if relation_count or family_count
                    else "Relation review completed without relation candidates or family groups."
                ),
                object_id=family_norm_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="relation-summary",
                title="Relation Summary",
                fields=[
                    RuntimeSummaryField(key="relation_count", label="relation_count", value=str(relation_count), tone="success" if relation_count else "warning"),
                    RuntimeSummaryField(key="family_count", label="family_count", value=str(family_count), tone="info"),
                    RuntimeSummaryField(key="alias_count", label="alias_count", value=str(alias_count), tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="family-distribution",
                title="Family Distribution",
                fields=[
                    RuntimeSummaryField(key="largest_family", label="largest_family", value=_largest_family_label(family_groups)),
                    RuntimeSummaryField(key="families_with_aliases", label="families_with_aliases", value=str(sum(1 for group in family_groups if group["aliases"]))),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph"),
            RuntimeAction(action_id="view-family-normalization", label="View family normalization", target_kind="node", target_id=family_norm_id),
        ],
    )

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[node.node_id for node in nodes if node.is_primary],
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _collect_items(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in contribution.get("entities", []):
        items.append({"item_type": "entity", **item})
    for item in contribution.get("events", []):
        items.append({"item_type": "event", **item})
    for item in contribution.get("processes", []):
        items.append({"item_type": "process", **item})
    return items


def _build_family_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for item in items:
        aliases = list(item.get("aliases") or [])
        label = item.get("name") or item.get("id") or "family"
        key = label.lower()
        groups.append(
            {
                "key": key,
                "label": label,
                "aliases": aliases,
                "member_count": 1 + len(aliases),
            }
        )
    return groups


def _resolve_family_key(name: str | None, items: list[dict[str, Any]]) -> str | None:
    if not name:
        return None
    normalized = name.lower()
    for item in items:
        candidates = [str(item.get("name") or "").lower(), *(str(alias).lower() for alias in item.get("aliases", []))]
        if normalized in candidates:
            return str(item.get("name") or item.get("id") or name).lower()
    return None


def _largest_family_label(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return "none"
    largest = max(groups, key=lambda group: group["member_count"])
    return str(largest["label"])
