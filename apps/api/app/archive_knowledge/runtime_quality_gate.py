from __future__ import annotations

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
from app.archive_knowledge.runtime_trace_utils import (
    build_runtime_events,
    build_runtime_sections,
    merge_runtime_events,
    merge_runtime_sections,
)


def build_quality_gate_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    knowledge_items: list[dict[str, Any]] | None = None,
    current_version: dict[str, Any] | None = None,
    document_published: bool = False,
    runtime_trace: dict[str, Any] | None = None,
    status_override: RuntimeStatus | None = None,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["quality_policy_evaluation_governance_gate"]
    evidence_count = _count_evidence(contribution)
    knowledge_items = list(knowledge_items or _derive_items_from_contribution(contribution))
    pending_items = [item for item in knowledge_items if item.get("review_status", "pending") == "pending"]
    approved_items = [item for item in knowledge_items if item.get("review_status") == "approved"]
    rejected_items = [item for item in knowledge_items if item.get("review_status") == "rejected"]

    rule_hit_id = f"{document_id}:quality-gate:rule-hit"
    gate_id = f"{document_id}:quality-gate:gate"
    blocked_id = f"{document_id}:quality-gate:blocked"
    manual_review_id = f"{document_id}:quality-gate:manual-review"
    publish_target_id = f"{document_id}:quality-gate:publish-target"

    should_block = evidence_count == 0 or bool(pending_items) or bool(rejected_items)
    gate_status = status_override or (
        RuntimeStatus.BLOCKED if should_block else (RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING)
    )
    trace_events = build_runtime_events(runtime_trace)
    trace_sections = build_runtime_sections(runtime_trace)
    trace_rule_hit = ((runtime_trace or {}).get("rule_hits") or [{}])[0]
    rule_key = str(trace_rule_hit.get("key") or "min_supporting_documents")
    rule_label = str(trace_rule_hit.get("label") or "minimum supporting documents")
    trace_decision = (runtime_trace or {}).get("decision") or {}
    block_reason = str(trace_decision.get("reason") or _block_reason(evidence_count, pending_items, rejected_items))

    nodes = [
        RuntimeGraphNode(
            node_id=rule_hit_id,
            label="Rule Hit",
            node_type="rule_hit",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"evidence_count": evidence_count, "pending_count": len(pending_items)},
            attributes={"rule_key": rule_key, "rule_label": rule_label},
        ),
        RuntimeGraphNode(
            node_id=gate_id,
            label="Gate Decision",
            node_type="gate_decision",
            stage_id=definition.stage_id,
            status=gate_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "knowledge_item_count": len(knowledge_items),
                "approved_count": len(approved_items),
                "pending_count": len(pending_items),
                "rejected_count": len(rejected_items),
            },
            attributes={"decision": trace_decision.get("status") or gate_status.value},
        ),
    ]

    edges = [
        RuntimeGraphEdge(
            edge_id=f"{rule_hit_id}:results_in",
            source=rule_hit_id,
            target=gate_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=gate_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        )
    ]

    for index, item in enumerate(knowledge_items, start=1):
        item_node_id = f"{document_id}:quality-gate:item:{index}"
        item_status = _review_status_to_runtime(item.get("review_status", "pending"))
        nodes.append(
            RuntimeGraphNode(
                node_id=item_node_id,
                label=item.get("name") or item.get("id") or f"item-{index}",
                node_type=f"canonical_{item.get('item_type', 'item')}",
                stage_id=definition.stage_id,
                status=item_status,
                origin=RuntimeOrigin.SOURCE,
                attributes={
                    "item_id": item.get("id"),
                    "item_type": item.get("item_type", "item"),
                    "review_status": item.get("review_status", "pending"),
                    "category": item.get("category"),
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{item_node_id}:evaluated_by",
                source=item_node_id,
                target=rule_hit_id,
                relation="evaluated_by",
                stage_id=definition.stage_id,
                status=item_status,
                origin=RuntimeOrigin.SOURCE,
                attributes={"review_status": item.get("review_status", "pending")},
            )
        )

    if should_block:
        nodes.extend(
            [
                RuntimeGraphNode(
                    node_id=manual_review_id,
                    label="Manual Review",
                    node_type="manual_review",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.WARNING,
                    origin=RuntimeOrigin.DERIVED,
                    metrics={"pending_count": len(pending_items)},
                ),
                RuntimeGraphNode(
                    node_id=blocked_id,
                    label="Blocked Result",
                    node_type="blocked_result",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.BLOCKED,
                    origin=RuntimeOrigin.DERIVED,
                    is_primary=True,
                    attributes={"reason": block_reason},
                ),
            ]
        )
        edges.extend(
            [
                RuntimeGraphEdge(
                    edge_id=f"{gate_id}:reviewed_by",
                    source=gate_id,
                    target=manual_review_id,
                    relation="reviewed_by",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.WARNING,
                    origin=RuntimeOrigin.DERIVED,
                ),
                RuntimeGraphEdge(
                    edge_id=f"{gate_id}:blocked_by",
                    source=gate_id,
                    target=blocked_id,
                    relation="blocked_by",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.BLOCKED,
                    origin=RuntimeOrigin.DERIVED,
                    is_primary=True,
                ),
            ]
        )
    else:
        nodes.append(
            RuntimeGraphNode(
                node_id=publish_target_id,
                label="Publish Target",
                node_type="publish_target",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"version_label": (current_version or {}).get("version_label") or "pending"},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{gate_id}:publishes_to",
                source=gate_id,
                target=publish_target_id,
                relation="publishes_to",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="阶段视角 · 质量门禁",
        subtitle=document_title,
        status=gate_status,
        stream=merge_runtime_events(
            [
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:rule",
                    kind="rule",
                    level="warning" if should_block else "success",
                    message=f"Rule {rule_key} evaluated evidence_count={evidence_count} and pending_review_count={len(pending_items)}.",
                    object_id=rule_hit_id,
                    object_kind="node",
                ),
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:decision",
                    kind="block" if should_block else "result",
                    level="danger" if should_block else "success",
                    message=(
                        f"Quality gate blocked publication because {block_reason}."
                        if should_block
                        else "Quality gate passed and the document can proceed toward publication outputs."
                    ),
                    object_id=gate_id,
                    object_kind="node",
                ),
            ],
            trace_events,
        ),
        sections=merge_runtime_sections(
            [
                RuntimeSummarySection(
                    section_id="gate-summary",
                    title="Gate Summary",
                    fields=[
                        RuntimeSummaryField(key="knowledge_item_count", label="knowledge_item_count", value=str(len(knowledge_items)), tone="info"),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="warning" if evidence_count <= 1 else "success"),
                        RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                        RuntimeSummaryField(key="current_version", label="current_version", value=(current_version or {}).get("version_label") or "unpublished", tone="info"),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="review-state",
                    title="Review State",
                    fields=[
                        RuntimeSummaryField(key="approved_count", label="approved_count", value=str(len(approved_items)), tone="success"),
                        RuntimeSummaryField(key="pending_count", label="pending_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                        RuntimeSummaryField(key="rejected_count", label="rejected_count", value=str(len(rejected_items)), tone="danger" if rejected_items else "neutral"),
                    ],
                ),
            ],
            trace_sections,
        ),
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(action_id="view-rule-hits", label="View Rule Hits", target_kind="node", target_id=rule_hit_id),
        ],
    )

    node_observers = {
        rule_hit_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Rule Hit",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:rule-hit-node",
                    kind="rule",
                    level="warning" if should_block else "success",
                    message=f"Rule {rule_key} has finished evaluation and fed the gate decision.",
                    object_id=rule_hit_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="rule",
                    title="Rule Information",
                    fields=[
                        RuntimeSummaryField(key="rule_key", label="rule_key", value=rule_key),
                        RuntimeSummaryField(key="rule_label", label="rule_label", value=rule_label),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count)),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-gate", label="View Gate Decision", target_kind="node", target_id=gate_id)],
        ),
        gate_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Gate Decision",
            subtitle=document_title,
            status=gate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:gate-node",
                    kind="decision",
                    level="danger" if should_block else "success",
                    message="Gate decision is aggregating rule hits, review state, and publication constraints.",
                    object_id=gate_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="decision",
                    title="Decision Summary",
                    fields=[
                        RuntimeSummaryField(key="gate_status", label="gate_status", value=gate_status.value, tone="danger" if should_block else "success"),
                        RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                        RuntimeSummaryField(key="block_reason", label="block_reason", value=block_reason if should_block else "none"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-rule-hit", label="View Rule Hit", target_kind="node", target_id=rule_hit_id)],
        ),
    }

    if should_block:
        node_observers[blocked_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Blocked Result",
            subtitle=document_title,
            status=RuntimeStatus.BLOCKED,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:blocked-node",
                    kind="block",
                    level="danger",
                    message=f"Current object is blocked because {block_reason}.",
                    object_id=blocked_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="blocked",
                    title="Blocked Summary",
                    fields=[
                        RuntimeSummaryField(key="reason", label="reason", value=block_reason, tone="danger"),
                        RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items))),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-gate", label="View Gate Decision", target_kind="node", target_id=gate_id)],
        )
    else:
        node_observers[publish_target_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Publish Target",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:publish-node",
                    kind="result",
                    level="success",
                    message="Gate pass has moved the object into the publication target path.",
                    object_id=publish_target_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="publish-target",
                    title="Publish Target",
                    fields=[
                        RuntimeSummaryField(key="version_label", label="version_label", value=(current_version or {}).get("version_label") or "pending", tone="info"),
                        RuntimeSummaryField(key="document_published", label="document_published", value="true" if document_published else "false", tone="success" if document_published else "warning"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-gate", label="View Gate Decision", target_kind="node", target_id=gate_id)],
        )

    edge_observers = {
        f"{rule_hit_id}:results_in": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="results_in",
            subtitle=document_title,
            status=gate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:results-in",
                    kind="result",
                    level="danger" if should_block else "success",
                    message="Rule evaluation results are being folded into the gate decision.",
                    object_id=f"{rule_hit_id}:results_in",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="results_in"),
                        RuntimeSummaryField(key="source", label="source", value="Rule Hit"),
                        RuntimeSummaryField(key="target", label="target", value="Gate Decision"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View Source Node", target_kind="node", target_id=rule_hit_id),
                RuntimeAction(action_id="view-target-node", label="View Target Node", target_kind="node", target_id=gate_id),
            ],
        )
    }

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=gate_status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[rule_hit_id, gate_id, blocked_id if should_block else publish_target_id],
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _count_evidence(contribution: dict[str, Any]) -> int:
    count = 0
    for collection_name in ("entities", "events", "processes"):
        for item in contribution.get(collection_name, []):
            count += len(item.get("evidence", []))
    return count


def _derive_items_from_contribution(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    collection_map = {
        "entities": "entity",
        "events": "event",
        "processes": "process",
    }
    items: list[dict[str, Any]] = []
    for collection_name, item_type in collection_map.items():
        for item in contribution.get(collection_name, []):
            items.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "item_type": item_type,
                    "category": item.get("category"),
                    "review_status": item.get("review_status", "pending"),
                }
            )
    return items


def _review_status_to_runtime(review_status: str) -> RuntimeStatus:
    if review_status == "approved":
        return RuntimeStatus.COMPLETED
    if review_status == "rejected":
        return RuntimeStatus.BLOCKED
    return RuntimeStatus.WARNING


def _block_reason(evidence_count: int, pending_items: list[dict[str, Any]], rejected_items: list[dict[str, Any]]) -> str:
    if evidence_count == 0:
        return "evidence is insufficient"
    if pending_items:
        return "manual review is still pending"
    if rejected_items:
        return "rejected knowledge items remain in the candidate set"
    return "no blocking condition"
