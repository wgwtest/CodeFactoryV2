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


def build_quality_gate_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    knowledge_items: list[dict[str, Any]] | None = None,
    current_version: dict[str, Any] | None = None,
    document_published: bool = False,
) -> RuntimeStageSnapshot:
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
    gate_status = RuntimeStatus.BLOCKED if should_block else (RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING)

    nodes = [
        RuntimeGraphNode(
            node_id=rule_hit_id,
            label="规则命中",
            node_type="rule_hit",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"evidence_count": evidence_count, "pending_count": len(pending_items)},
            attributes={
                "rule_key": "min_supporting_documents",
                "rule_label": "最少支撑文档",
            },
        ),
        RuntimeGraphNode(
            node_id=gate_id,
            label="门禁决策",
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
                    label="人工复核",
                    node_type="manual_review",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.WARNING,
                    origin=RuntimeOrigin.DERIVED,
                    metrics={"pending_count": len(pending_items)},
                ),
                RuntimeGraphNode(
                    node_id=blocked_id,
                    label="阻断结果",
                    node_type="blocked_result",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.BLOCKED,
                    origin=RuntimeOrigin.DERIVED,
                    is_primary=True,
                    attributes={"reason": _block_reason(evidence_count, pending_items, rejected_items)},
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
                label="发布目标",
                node_type="publish_target",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"version_label": (current_version or {}).get("version_label") or "待生成"},
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
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:rule",
                kind="rule",
                level="warning" if should_block else "success",
                message=f"命中规则 min_supporting_documents，当前证据数 {evidence_count}，待复核 {len(pending_items)}。",
                object_id=rule_hit_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:decision",
                kind="block" if should_block else "result",
                level="danger" if should_block else "success",
                message=(
                    f"当前对象进入待人工复核，阻断发布，原因：{_block_reason(evidence_count, pending_items, rejected_items)}。"
                    if should_block
                    else "当前对象已通过门禁，可进入发布目标。"
                ),
                object_id=gate_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="gate-summary",
                title="门禁摘要",
                fields=[
                    RuntimeSummaryField(key="knowledge_item_count", label="knowledge_item_count", value=str(len(knowledge_items)), tone="info"),
                    RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="warning" if evidence_count <= 1 else "success"),
                    RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                    RuntimeSummaryField(key="current_version", label="current_version", value=(current_version or {}).get("version_label") or "未发布", tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="review-state",
                title="审核状态",
                fields=[
                    RuntimeSummaryField(key="approved_count", label="approved_count", value=str(len(approved_items)), tone="success"),
                    RuntimeSummaryField(key="pending_count", label="pending_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                    RuntimeSummaryField(key="rejected_count", label="rejected_count", value=str(len(rejected_items)), tone="danger" if rejected_items else "neutral"),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="查看阶段图谱", target_kind="graph"),
            RuntimeAction(action_id="view-rule-hits", label="查看规则命中", target_kind="node", target_id=rule_hit_id),
        ],
    )

    node_observers = {
        rule_hit_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 规则命中",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:rule-hit-node",
                    kind="rule",
                    level="warning" if should_block else "success",
                    message="最少支撑文档规则已完成评估，结果已流入门禁决策。",
                    object_id=rule_hit_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="rule",
                    title="规则信息",
                    fields=[
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="min_supporting_documents"),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-gate", label="查看门禁决策", target_kind="node", target_id=gate_id),
            ],
        ),
        gate_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 门禁决策",
            subtitle=document_title,
            status=gate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:gate-node",
                    kind="decision",
                    level="danger" if should_block else "success",
                    message="门禁决策正在汇总规则命中、审核状态和发布约束。",
                    object_id=gate_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="decision",
                    title="决策摘要",
                    fields=[
                        RuntimeSummaryField(key="gate_status", label="gate_status", value=gate_status.value, tone="danger" if should_block else "success"),
                        RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items)), tone="warning" if pending_items else "success"),
                        RuntimeSummaryField(key="block_reason", label="block_reason", value=_block_reason(evidence_count, pending_items, rejected_items) if should_block else "none"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-rule-hit", label="查看规则命中", target_kind="node", target_id=rule_hit_id),
            ],
        ),
    }

    if should_block:
        node_observers[blocked_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 阻断结果",
            subtitle=document_title,
            status=RuntimeStatus.BLOCKED,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:blocked-node",
                    kind="block",
                    level="danger",
                    message=f"当前对象被阻断，原因：{_block_reason(evidence_count, pending_items, rejected_items)}。",
                    object_id=blocked_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="blocked",
                    title="阻断摘要",
                    fields=[
                        RuntimeSummaryField(key="reason", label="reason", value=_block_reason(evidence_count, pending_items, rejected_items), tone="danger"),
                        RuntimeSummaryField(key="pending_review_count", label="pending_review_count", value=str(len(pending_items))),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-gate", label="查看门禁决策", target_kind="node", target_id=gate_id),
            ],
        )
    else:
        node_observers[publish_target_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 发布目标",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if document_published else RuntimeStatus.RUNNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:publish-node",
                    kind="result",
                    level="success",
                    message="门禁通过后，当前对象已进入发布目标生成路径。",
                    object_id=publish_target_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="publish-target",
                    title="发布目标",
                    fields=[
                        RuntimeSummaryField(key="version_label", label="version_label", value=(current_version or {}).get("version_label") or "待生成", tone="info"),
                        RuntimeSummaryField(key="document_published", label="document_published", value="true" if document_published else "false", tone="success" if document_published else "warning"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-gate", label="查看门禁决策", target_kind="node", target_id=gate_id),
            ],
        )

    edge_observers = {
        f"{rule_hit_id}:results_in": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="边视角 · results_in",
            subtitle=document_title,
            status=gate_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:results-in",
                    kind="result",
                    level="danger" if should_block else "success",
                    message="规则命中结果正在形成门禁决策。",
                    object_id=f"{rule_hit_id}:results_in",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation",
                    title="关系摘要",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="results_in"),
                        RuntimeSummaryField(key="source", label="source", value="规则命中"),
                        RuntimeSummaryField(key="target", label="target", value="门禁决策"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=rule_hit_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=gate_id),
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
        return "证据不足"
    if pending_items:
        return "存在待人工复核对象"
    if rejected_items:
        return "存在已拒绝对象"
    return "无"
