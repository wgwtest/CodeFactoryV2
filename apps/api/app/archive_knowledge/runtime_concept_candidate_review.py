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


def build_concept_candidate_review_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["concept_candidate_review"]
    candidate_items = _collect_candidate_items(contribution)
    candidate_count = len(candidate_items)
    alias_count = sum(len(item.get("aliases", [])) for item in candidate_items)
    category_counter = Counter(item.get("category") or "uncategorized" for item in candidate_items)
    type_counter = Counter(item.get("item_type") or "concept" for item in candidate_items)
    evidence_count = sum(len(item.get("evidence", [])) for item in candidate_items)
    status = RuntimeStatus.COMPLETED if candidate_count else RuntimeStatus.WARNING

    pack_input_id = f"{document_id}:concept-review:evidence-pack"
    concept_set_id = f"{document_id}:concept-review:candidate-set"
    category_group_id = f"{document_id}:concept-review:categories"
    alias_group_id = f"{document_id}:concept-review:aliases"
    warning_id = f"{document_id}:concept-review:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=pack_input_id,
            label="Evidence Pack Input",
            node_type="evidence_pack_input",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "candidate_count": candidate_count,
                "evidence_count": evidence_count,
            },
        ),
        RuntimeGraphNode(
            node_id=concept_set_id,
            label="Concept Candidate Set",
            node_type="concept_candidate_set",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "candidate_count": candidate_count,
                "entity_count": type_counter.get("entity", 0),
                "event_count": type_counter.get("event", 0),
                "process_count": type_counter.get("process", 0),
            },
        ),
        RuntimeGraphNode(
            node_id=category_group_id,
            label="Category Groups",
            node_type="category_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            metrics={"category_count": len(category_counter)},
        ),
        RuntimeGraphNode(
            node_id=alias_group_id,
            label="Alias Groups",
            node_type="alias_group",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if alias_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            metrics={"alias_count": alias_count},
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{pack_input_id}:proposes",
            source=pack_input_id,
            target=concept_set_id,
            relation="proposes",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{concept_set_id}:categorized_as",
            source=concept_set_id,
            target=category_group_id,
            relation="categorized_as",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{concept_set_id}:aliased_as",
            source=concept_set_id,
            target=alias_group_id,
            relation="aliased_as",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if alias_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
        ),
    ]

    node_observers: dict[str, RuntimeObserverPayload] = {
        concept_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Concept Candidate Set",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:concept-review:set",
                    kind="result",
                    level="success" if candidate_count else "warning",
                    message=(
                        f"Concept candidate review assembled {candidate_count} candidates from the current evidence pack."
                        if candidate_count
                        else "Concept candidate review did not materialize any candidates for the current document."
                    ),
                    object_id=concept_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="candidate-set-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="concept_candidate_set"),
                        RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(candidate_count), tone="success" if candidate_count else "warning"),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="info"),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="candidate-set-distribution",
                    title="Candidate Distribution",
                    fields=[
                        RuntimeSummaryField(key="entity_count", label="entity_count", value=str(type_counter.get("entity", 0))),
                        RuntimeSummaryField(key="event_count", label="event_count", value=str(type_counter.get("event", 0))),
                        RuntimeSummaryField(key="process_count", label="process_count", value=str(type_counter.get("process", 0))),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph"),
            ],
        ),
    }
    edge_observers: dict[str, RuntimeObserverPayload] = {
        f"{pack_input_id}:proposes": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="proposes",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:concept-review:edge-proposes",
                    kind="decision",
                    level="success" if candidate_count else "warning",
                    message=(
                        f"The evidence pack proposed {candidate_count} concept candidates for review."
                        if candidate_count
                        else "The evidence pack could not propose any concept candidates."
                    ),
                    object_id=f"{pack_input_id}:proposes",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="edge-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="proposes"),
                        RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(candidate_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=pack_input_id),
                RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=concept_set_id),
            ],
        ),
    }

    category_node_ids: dict[str, str] = {}
    alias_index = 0
    for index, item in enumerate(candidate_items, start=1):
        node_id = f"{document_id}:concept-review:candidate:{index}"
        candidate_status = _review_status_to_runtime(item.get("review_status", "pending"))
        nodes.append(
            RuntimeGraphNode(
                node_id=node_id,
                label=item.get("name") or item.get("id") or f"candidate-{index}",
                node_type=f"concept_candidate_{item.get('item_type') or 'concept'}",
                stage_id=definition.stage_id,
                status=candidate_status,
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 4,
                metrics={"evidence_count": len(item.get("evidence", [])), "alias_count": len(item.get("aliases", []))},
                attributes={
                    "item_id": item.get("id"),
                    "item_type": item.get("item_type") or "concept",
                    "category": item.get("category"),
                    "review_status": item.get("review_status", "pending"),
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{concept_set_id}:candidate:{index}",
                source=concept_set_id,
                target=node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=candidate_status,
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 4,
            )
        )

        category = item.get("category") or "uncategorized"
        category_node_id = category_node_ids.get(category)
        if category_node_id is None:
            category_node_id = f"{document_id}:concept-review:category:{len(category_node_ids) + 1}"
            category_node_ids[category] = category_node_id
            nodes.append(
                RuntimeGraphNode(
                    node_id=category_node_id,
                    label=category,
                    node_type="concept_category",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    metrics={"candidate_count": category_counter[category]},
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{category_group_id}:{category_node_id}",
                    source=category_group_id,
                    target=category_node_id,
                    relation="contains",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )
        category_edge_id = f"{node_id}:categorized_as"
        edges.append(
            RuntimeGraphEdge(
                edge_id=category_edge_id,
                source=node_id,
                target=category_node_id,
                relation="categorized_as",
                stage_id=definition.stage_id,
                status=candidate_status,
                origin=RuntimeOrigin.DERIVED,
            )
        )
        edge_observers[category_edge_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="categorized_as",
            subtitle=document_title,
            status=candidate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{category_edge_id}:event",
                    kind="decision",
                    level="info",
                    message=f"Candidate {item.get('name') or item.get('id')} is currently categorized as {category}.",
                    object_id=category_edge_id,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="categorized_as"),
                        RuntimeSummaryField(key="source", label="source", value=item.get("name") or item.get("id") or f"candidate-{index}"),
                        RuntimeSummaryField(key="target", label="target", value=category),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=node_id),
                RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=category_node_id),
            ],
        )

        for alias in item.get("aliases", []):
            alias_index += 1
            alias_node_id = f"{document_id}:concept-review:alias:{alias_index}"
            nodes.append(
                RuntimeGraphNode(
                    node_id=alias_node_id,
                    label=alias,
                    node_type="concept_alias",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.SOURCE,
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{alias_group_id}:{alias_node_id}",
                    source=alias_group_id,
                    target=alias_node_id,
                    relation="contains",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )
            alias_edge_id = f"{node_id}:alias:{alias_index}"
            edges.append(
                RuntimeGraphEdge(
                    edge_id=alias_edge_id,
                    source=node_id,
                    target=alias_node_id,
                    relation="aliased_as",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.SOURCE,
                )
            )
            edge_observers[alias_edge_id] = RuntimeObserverPayload(
                mode=RuntimeObserverMode.EDGE,
                title="aliased_as",
                subtitle=document_title,
                status=RuntimeStatus.COMPLETED,
                stream=[
                    RuntimeEvent(
                        event_id=f"{alias_edge_id}:event",
                        kind="result",
                        level="info",
                        message=f"Alias {alias} is attached to candidate {item.get('name') or item.get('id')}.",
                        object_id=alias_edge_id,
                        object_kind="edge",
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="relation-summary",
                        title="Relation Summary",
                        fields=[
                            RuntimeSummaryField(key="relation", label="relation", value="aliased_as"),
                            RuntimeSummaryField(key="source", label="source", value=item.get("name") or item.get("id") or f"candidate-{index}"),
                            RuntimeSummaryField(key="target", label="target", value=alias),
                        ],
                    )
                ],
                actions=[
                    RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=node_id),
                    RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=alias_node_id),
                ],
            )

        node_observers[node_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Concept Candidate",
            subtitle=document_title,
            status=candidate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{node_id}:event",
                    kind="result",
                    level="success" if len(item.get("evidence", [])) else "warning",
                    message=(
                        f"Concept candidate {item.get('name') or item.get('id')} was proposed with {len(item.get('evidence', []))} evidence entries."
                    ),
                    object_id=node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="candidate-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="label", label="label", value=item.get("name") or item.get("id") or f"candidate-{index}"),
                        RuntimeSummaryField(key="item_type", label="item_type", value=item.get("item_type") or "concept"),
                        RuntimeSummaryField(key="category", label="category", value=category),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="candidate-context",
                    title="Context and Review",
                    fields=[
                        RuntimeSummaryField(key="review_status", label="review_status", value=item.get("review_status", "pending"), tone=_review_tone(item.get("review_status", "pending"))),
                        RuntimeSummaryField(key="alias_count", label="alias_count", value=str(len(item.get("aliases", [])))),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(len(item.get("evidence", []))), tone="success" if item.get("evidence") else "warning"),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-evidence-pack", label="View evidence pack", target_kind="node", target_id=pack_input_id),
            ],
        )

    if not candidate_items:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Concept Candidate Warning",
                node_type="concept_candidate_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"message": "No concept candidates were materialized from the current evidence pack."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{concept_set_id}:warned_by",
                source=concept_set_id,
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
        title="Concept Candidate Review",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:concept-review:start",
                kind="progress",
                level="info",
                message="Concept candidate review is evaluating evidence-pack outputs and materializing candidate concepts for the current document.",
                object_id=pack_input_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:concept-review:result",
                kind="result",
                level="success" if candidate_count else "warning",
                message=(
                    f"Concept candidate review produced {candidate_count} candidates, {len(category_counter)} categories, and {alias_count} aliases."
                    if candidate_count
                    else "Concept candidate review completed without materialized concept candidates."
                ),
                object_id=concept_set_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="candidate-summary",
                title="Candidate Summary",
                fields=[
                    RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(candidate_count), tone="success" if candidate_count else "warning"),
                    RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="info"),
                    RuntimeSummaryField(key="category_count", label="category_count", value=str(len(category_counter)), tone="info"),
                    RuntimeSummaryField(key="alias_count", label="alias_count", value=str(alias_count), tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="type-distribution",
                title="Type Distribution",
                fields=[
                    RuntimeSummaryField(key="entity_count", label="entity_count", value=str(type_counter.get("entity", 0))),
                    RuntimeSummaryField(key="event_count", label="event_count", value=str(type_counter.get("event", 0))),
                    RuntimeSummaryField(key="process_count", label="process_count", value=str(type_counter.get("process", 0))),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph"),
            RuntimeAction(action_id="view-concept-set", label="View concept set", target_kind="node", target_id=concept_set_id),
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


def _collect_candidate_items(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in contribution.get("entities", []):
        items.append({"item_type": "entity", **item})
    for item in contribution.get("events", []):
        items.append({"item_type": "event", **item})
    for item in contribution.get("processes", []):
        items.append({"item_type": "process", **item})
    return items


def _review_status_to_runtime(review_status: str) -> RuntimeStatus:
    if review_status == "approved":
        return RuntimeStatus.COMPLETED
    if review_status == "rejected":
        return RuntimeStatus.BLOCKED
    return RuntimeStatus.WARNING


def _review_tone(review_status: str) -> str:
    if review_status == "approved":
        return "success"
    if review_status == "rejected":
        return "danger"
    return "warning"
