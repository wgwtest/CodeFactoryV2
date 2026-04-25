from __future__ import annotations

from collections import Counter, defaultdict
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


def build_definition_summary_conflict_consolidation_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["definition_summary_conflict_consolidation"]
    items = _collect_items(contribution)
    relations = list(contribution.get("relations", []))
    definition_candidates = _build_definition_candidates(items)
    summary_candidates = _build_summary_candidates(
        document_title=document_title,
        items=items,
        relations=relations,
    )
    conflict_candidates = _build_conflict_candidates(items, relations)

    status = (
        RuntimeStatus.COMPLETED
        if definition_candidates or summary_candidates
        else RuntimeStatus.WARNING
    )

    relation_input_id = f"{document_id}:definition-stage:relation-input"
    definition_set_id = f"{document_id}:definition-stage:definition-set"
    summary_set_id = f"{document_id}:definition-stage:summary-set"
    conflict_set_id = f"{document_id}:definition-stage:conflict-set"
    consolidation_id = f"{document_id}:definition-stage:consolidation"
    warning_id = f"{document_id}:definition-stage:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=relation_input_id,
            label="Relation Review Input",
            node_type="relation_review_input",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if relations else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"relation_count": len(relations)},
        ),
        RuntimeGraphNode(
            node_id=definition_set_id,
            label="Definition Candidate Set",
            node_type="definition_candidate_set",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if definition_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"definition_count": len(definition_candidates)},
        ),
        RuntimeGraphNode(
            node_id=summary_set_id,
            label="Summary Candidate Set",
            node_type="summary_candidate_set",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if summary_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"summary_count": len(summary_candidates)},
        ),
        RuntimeGraphNode(
            node_id=conflict_set_id,
            label="Conflict Candidate Set",
            node_type="conflict_candidate_set",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if conflict_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"conflict_count": len(conflict_candidates)},
        ),
        RuntimeGraphNode(
            node_id=consolidation_id,
            label="Consolidation Decisions",
            node_type="consolidation_decisions",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "definition_count": len(definition_candidates),
                "summary_count": len(summary_candidates),
                "conflict_count": len(conflict_candidates),
            },
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{relation_input_id}:proposes:definitions",
            source=relation_input_id,
            target=definition_set_id,
            relation="proposes",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if definition_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{relation_input_id}:resolved_by:summaries",
            source=relation_input_id,
            target=summary_set_id,
            relation="resolved_by",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if summary_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{relation_input_id}:conflicts_with",
            source=relation_input_id,
            target=conflict_set_id,
            relation="conflicts_with",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if conflict_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{consolidation_id}:contains:definitions",
            source=consolidation_id,
            target=definition_set_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if definition_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{consolidation_id}:contains:summaries",
            source=consolidation_id,
            target=summary_set_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if summary_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{consolidation_id}:contains:conflicts",
            source=consolidation_id,
            target=conflict_set_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if conflict_candidates else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    node_observers: dict[str, RuntimeObserverPayload] = {
        definition_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Definition Candidate Set",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if definition_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:set",
                    kind="result",
                    level="success" if definition_candidates else "warning",
                    message=(
                        f"Definition consolidation materialized {len(definition_candidates)} definition candidates."
                        if definition_candidates
                        else "Definition consolidation did not produce any definition candidates."
                    ),
                    object_id=definition_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="definition-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="definition_candidate_set"),
                        RuntimeSummaryField(key="definition_count", label="definition_count", value=str(len(definition_candidates)), tone="success" if definition_candidates else "warning"),
                        RuntimeSummaryField(key="document_title", label="document_title", value=document_title, tone="info"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph")],
        ),
        summary_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Summary Candidate Set",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if summary_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:summary-set",
                    kind="result",
                    level="success" if summary_candidates else "warning",
                    message=(
                        f"Summary consolidation materialized {len(summary_candidates)} summary candidates."
                        if summary_candidates
                        else "Summary consolidation did not produce any summary candidates."
                    ),
                    object_id=summary_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="summary-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="summary_candidate_set"),
                        RuntimeSummaryField(key="summary_count", label="summary_count", value=str(len(summary_candidates)), tone="success" if summary_candidates else "warning"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph")],
        ),
        conflict_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Conflict Candidate Set",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if conflict_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:conflict-set",
                    kind="warning",
                    level="warning" if conflict_candidates else "info",
                    message=(
                        f"Conflict consolidation recorded {len(conflict_candidates)} unresolved definition or relation conflicts."
                        if conflict_candidates
                        else "Conflict consolidation did not detect unresolved conflicts."
                    ),
                    object_id=conflict_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="conflict-identity",
                    title="Object Identity",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="conflict_candidate_set"),
                        RuntimeSummaryField(key="conflict_count", label="conflict_count", value=str(len(conflict_candidates)), tone="warning" if conflict_candidates else "info"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View stage graph", target_kind="graph")],
        ),
        consolidation_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Consolidation Decisions",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:start",
                    kind="progress",
                    level="info",
                    message="Definition, summary, and conflict objects are being consolidated from normalized relation review outputs.",
                    object_id=consolidation_id,
                    object_kind="node",
                ),
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:result",
                    kind="result",
                    level="success" if definition_candidates or summary_candidates else "warning",
                    message=f"Consolidation produced {len(definition_candidates)} definitions, {len(summary_candidates)} summaries, and {len(conflict_candidates)} conflicts.",
                    object_id=consolidation_id,
                    object_kind="node",
                ),
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="consolidation-summary",
                    title="Consolidation Summary",
                    fields=[
                        RuntimeSummaryField(key="definition_count", label="definition_count", value=str(len(definition_candidates)), tone="success" if definition_candidates else "warning"),
                        RuntimeSummaryField(key="summary_count", label="summary_count", value=str(len(summary_candidates)), tone="success" if summary_candidates else "warning"),
                        RuntimeSummaryField(key="conflict_count", label="conflict_count", value=str(len(conflict_candidates)), tone="warning" if conflict_candidates else "info"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-definition-set", label="View definition set", target_kind="node", target_id=definition_set_id),
                RuntimeAction(action_id="view-summary-set", label="View summary set", target_kind="node", target_id=summary_set_id),
                RuntimeAction(action_id="view-conflict-set", label="View conflict set", target_kind="node", target_id=conflict_set_id),
            ],
        ),
    }

    edge_observers: dict[str, RuntimeObserverPayload] = {
        f"{relation_input_id}:proposes:definitions": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="proposes",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if definition_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:proposes",
                    kind="decision",
                    level="success" if definition_candidates else "warning",
                    message=(
                        f"Relation review input proposed {len(definition_candidates)} definition candidates."
                        if definition_candidates
                        else "Relation review input did not propose any definition candidates."
                    ),
                    object_id=f"{relation_input_id}:proposes:definitions",
                    object_kind="edge",
                )
            ],
            sections=[RuntimeSummarySection(section_id="propose-summary", title="Relation Summary", fields=[RuntimeSummaryField(key="relation", label="relation", value="proposes"), RuntimeSummaryField(key="definition_count", label="definition_count", value=str(len(definition_candidates)))])],
            actions=[RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=relation_input_id), RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=definition_set_id)],
        ),
        f"{relation_input_id}:resolved_by:summaries": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="resolved_by",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if summary_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:resolved-by-summaries",
                    kind="decision",
                    level="success" if summary_candidates else "warning",
                    message=(
                        f"Relation review input was summarized into {len(summary_candidates)} summary candidates."
                        if summary_candidates
                        else "Summary resolution did not materialize any summary candidates."
                    ),
                    object_id=f"{relation_input_id}:resolved_by:summaries",
                    object_kind="edge",
                )
            ],
            sections=[RuntimeSummarySection(section_id="summary-resolution", title="Summary Resolution", fields=[RuntimeSummaryField(key="relation", label="relation", value="resolved_by"), RuntimeSummaryField(key="summary_count", label="summary_count", value=str(len(summary_candidates)))])],
            actions=[RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=relation_input_id), RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=summary_set_id)],
        ),
        f"{relation_input_id}:conflicts_with": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="conflicts_with",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if conflict_candidates else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:definition-stage:conflicts-with",
                    kind="warning",
                    level="warning" if conflict_candidates else "info",
                    message=(
                        f"Relation review input produced {len(conflict_candidates)} conflict candidates requiring consolidation."
                        if conflict_candidates
                        else "No relation conflicts required consolidation."
                    ),
                    object_id=f"{relation_input_id}:conflicts_with",
                    object_kind="edge",
                )
            ],
            sections=[RuntimeSummarySection(section_id="conflict-resolution", title="Conflict Summary", fields=[RuntimeSummaryField(key="relation", label="relation", value="conflicts_with"), RuntimeSummaryField(key="conflict_count", label="conflict_count", value=str(len(conflict_candidates)), tone="warning" if conflict_candidates else "info")])],
            actions=[RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=relation_input_id), RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=conflict_set_id)],
        ),
    }

    for index, candidate in enumerate(definition_candidates, start=1):
        node_id = f"{document_id}:definition-stage:definition:{index}"
        nodes.append(
            RuntimeGraphNode(
                node_id=node_id,
                label=candidate["label"],
                node_type="definition_candidate",
                stage_id=definition.stage_id,
                status=_review_status_to_runtime(candidate["review_status"]),
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 4,
                metrics={"evidence_count": candidate["evidence_count"]},
                attributes={
                    "item_id": candidate["item_id"],
                    "item_type": candidate["item_type"],
                    "category": candidate["category"],
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{definition_set_id}:definition:{index}",
                source=definition_set_id,
                target=node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=_review_status_to_runtime(candidate["review_status"]),
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 4,
            )
        )

    for index, candidate in enumerate(summary_candidates, start=1):
        node_id = f"{document_id}:definition-stage:summary:{index}"
        nodes.append(
            RuntimeGraphNode(
                node_id=node_id,
                label=candidate["label"],
                node_type="summary_candidate",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index <= 3,
                metrics={"support_count": candidate["support_count"]},
                attributes={"summary_type": candidate["summary_type"]},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{summary_set_id}:summary:{index}",
                source=summary_set_id,
                target=node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index <= 3,
            )
        )

    for index, conflict in enumerate(conflict_candidates, start=1):
        node_id = f"{document_id}:definition-stage:conflict:{index}"
        nodes.append(
            RuntimeGraphNode(
                node_id=node_id,
                label=conflict["label"],
                node_type="conflict_candidate",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index <= 3,
                attributes={"reason": conflict["reason"], "scope": conflict["scope"]},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{conflict_set_id}:conflict:{index}",
                source=conflict_set_id,
                target=node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index <= 3,
            )
        )

    if not definition_candidates and not summary_candidates:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Definition Stage Warning",
                node_type="definition_stage_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"message": "No definition or summary candidates were materialized for the current document."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{consolidation_id}:warned_by",
                source=consolidation_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Definition / Summary / Conflict Consolidation",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:definition-stage:start",
                kind="progress",
                level="info",
                message="Definition consolidation is aligning summaries, conflict candidates, and retained definitions for the current document.",
                object_id=consolidation_id,
                object_kind="stage",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:definition-stage:result",
                kind="result",
                level="success" if definition_candidates or summary_candidates else "warning",
                message=f"Current document produced {len(definition_candidates)} definitions, {len(summary_candidates)} summaries, and {len(conflict_candidates)} conflicts.",
                object_id=consolidation_id,
                object_kind="stage",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="stage-summary",
                title="Stage Summary",
                fields=[
                    RuntimeSummaryField(key="definition_count", label="definition_count", value=str(len(definition_candidates)), tone="success" if definition_candidates else "warning"),
                    RuntimeSummaryField(key="summary_count", label="summary_count", value=str(len(summary_candidates)), tone="success" if summary_candidates else "warning"),
                    RuntimeSummaryField(key="conflict_count", label="conflict_count", value=str(len(conflict_candidates)), tone="warning" if conflict_candidates else "info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="current-focus",
                title="Current Focus",
                fields=[
                    RuntimeSummaryField(key="primary_path", label="primary_path", value="Relation Review Input -> Definition/Summary/Conflict Sets -> Consolidation Decisions", tone="info"),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-definition-set", label="View definition set", target_kind="node", target_id=definition_set_id),
            RuntimeAction(action_id="view-summary-set", label="View summary set", target_kind="node", target_id=summary_set_id),
            RuntimeAction(action_id="view-conflict-set", label="View conflict set", target_kind="node", target_id=conflict_set_id),
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
            primary_node_ids=[
                relation_input_id,
                definition_set_id,
                summary_set_id,
                conflict_set_id,
                consolidation_id,
            ],
            primary_edge_ids=[
                f"{relation_input_id}:proposes:definitions",
                f"{relation_input_id}:resolved_by:summaries",
                f"{relation_input_id}:conflicts_with",
            ],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _collect_items(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item_type, collection_name in (
        ("entity", "entities"),
        ("event", "events"),
        ("process", "processes"),
    ):
        for item in contribution.get(collection_name, []):
            items.append(
                {
                    "item_id": item.get("id") or item.get("name") or f"{item_type}-item",
                    "item_type": item_type,
                    "label": item.get("name") or item.get("id") or item_type,
                    "category": item.get("category"),
                    "aliases": list(item.get("aliases", [])),
                    "evidence": list(item.get("evidence", [])),
                    "review_status": item.get("review_status", "pending"),
                }
            )
    return items


def _build_definition_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": item["item_id"],
            "item_type": item["item_type"],
            "label": item["label"],
            "category": item.get("category"),
            "review_status": item.get("review_status", "pending"),
            "evidence_count": len(item.get("evidence", [])),
        }
        for item in items
        if item.get("evidence")
    ]


def _build_summary_candidates(
    *,
    document_title: str,
    items: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = [
        {
            "label": "Document Summary",
            "summary_type": "document",
            "support_count": max(len(items), 1),
        }
    ]
    if items:
        item_counter = Counter(item["item_type"] for item in items)
        for item_type in ("entity", "event", "process"):
            if item_counter.get(item_type):
                summaries.append(
                    {
                        "label": f"{item_type.title()} Summary",
                        "summary_type": item_type,
                        "support_count": item_counter[item_type],
                    }
                )
    if relations:
        summaries.append(
            {
                "label": "Relation Summary",
                "summary_type": "relation",
                "support_count": len(relations),
            }
        )
    if not summaries:
        summaries.append(
            {
                "label": document_title,
                "summary_type": "document",
                "support_count": 0,
            }
        )
    return summaries


def _build_conflict_candidates(items: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    alias_index: dict[str, set[str]] = defaultdict(set)
    for item in items:
        for alias in item.get("aliases", []):
            normalized = _normalize_name(alias)
            if normalized:
                alias_index[normalized].add(item["item_id"])
    for alias, item_ids in alias_index.items():
        if len(item_ids) > 1:
            conflicts.append({"label": f"Alias collision: {alias}", "reason": "alias_collision", "scope": "item"})

    item_names = {_normalize_name(item["label"]) for item in items if _normalize_name(item["label"])}
    for relation in relations:
        source_name = _normalize_name(relation.get("source_name"))
        target_name = _normalize_name(relation.get("target_name"))
        if source_name and source_name not in item_names:
            conflicts.append({"label": f"Missing source endpoint: {relation.get('source_name')}", "reason": "missing_source_endpoint", "scope": "relation"})
        if target_name and target_name not in item_names:
            conflicts.append({"label": f"Missing target endpoint: {relation.get('target_name')}", "reason": "missing_target_endpoint", "scope": "relation"})

    for item in items:
        if not item.get("evidence"):
            conflicts.append({"label": f"Missing evidence: {item['label']}", "reason": "missing_evidence", "scope": item["item_type"]})
    return conflicts


def _normalize_name(value: Any) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _review_status_to_runtime(review_status: str) -> RuntimeStatus:
    if review_status == "approved":
        return RuntimeStatus.COMPLETED
    if review_status == "rejected":
        return RuntimeStatus.BLOCKED
    return RuntimeStatus.WARNING
