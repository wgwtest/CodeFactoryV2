from __future__ import annotations

from hashlib import sha256
import json
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
    definition = STAGE_DEFINITION_MAP["quality_policy_evaluation_governance_gate"]
    knowledge_items = list(knowledge_items or _derive_items_from_contribution(contribution))
    pending_items = [item for item in knowledge_items if item.get("review_status", "pending") == "pending"]
    approved_items = [item for item in knowledge_items if item.get("review_status") == "approved"]
    rejected_items = [item for item in knowledge_items if item.get("review_status") == "rejected"]

    trace = runtime_trace or {}
    trace_events = build_runtime_events(trace)
    trace_sections = build_runtime_sections(trace)
    rule_hits = _normalize_rule_hits(trace, contribution)
    decision = _normalize_decision(trace, contribution, pending_items, rejected_items)
    metrics = _normalize_metrics(trace, contribution, knowledge_items)
    gate_status = status_override or _decision_runtime_status(decision.get("status"), document_published=document_published)
    rule_execution_records = _build_rule_execution_records(
        archive_id=archive_id,
        document_id=document_id,
        stage_id=definition.stage_id,
        rule_hits=rule_hits,
        knowledge_items=knowledge_items,
        decision=decision,
        trace=trace,
    )
    records_by_rule = {record["rule_id"]: record for record in rule_execution_records}

    gate_id = f"{document_id}:quality-gate:gate"
    candidate_set_id = f"{document_id}:quality-gate:candidate-set"
    policy_set_id = f"{document_id}:quality-gate:policy-set"
    rule_hit_set_id = f"{document_id}:quality-gate:rule-hit-set"
    blocked_id = f"{document_id}:quality-gate:blocked"
    publish_target_id = f"{document_id}:quality-gate:publish-target"
    primary_rule_node_id = _rule_node_id(document_id, rule_hits[0]) if rule_hits else gate_id
    candidate_status = (
        RuntimeStatus.BLOCKED
        if rejected_items
        else RuntimeStatus.WARNING
        if pending_items
        else RuntimeStatus.COMPLETED
    )

    nodes: list[RuntimeGraphNode] = []
    edges: list[RuntimeGraphEdge] = []
    node_observers: dict[str, RuntimeObserverPayload] = {}
    edge_observers: dict[str, RuntimeObserverPayload] = {}

    nodes.append(
        RuntimeGraphNode(
            node_id=candidate_set_id,
            label="候选知识集合",
            node_type="quality_candidate_set",
            stage_id=definition.stage_id,
            status=candidate_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={
                "knowledge_item_count": len(knowledge_items),
                "approved_count": len(approved_items),
                "pending_count": len(pending_items),
                "rejected_count": len(rejected_items),
            },
            attributes={
                "input_object": "canonical_knowledge_items",
                "policy_snapshot_id": (trace.get("policy") or {}).get("snapshot_id"),
                "rule_count": len(rule_hits),
                "decision": decision.get("status"),
            },
        )
    )
    nodes.extend(
        [
            RuntimeGraphNode(
                node_id=policy_set_id,
                label="质量策略集合",
                node_type="quality_policy_set",
                stage_id=definition.stage_id,
                status=gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                metrics={
                    "rule_count": len(rule_hits),
                    "failed_rule_count": int(decision.get("failed_rule_count") or 0),
                },
                attributes={
                    "policy_snapshot_id": (trace.get("policy") or {}).get("snapshot_id"),
                    "default_action": "block_return",
                    "decision": decision.get("status"),
                },
            ),
            RuntimeGraphNode(
                node_id=rule_hit_set_id,
                label="规则命中集合",
                node_type="rule_hit_set",
                stage_id=definition.stage_id,
                status=gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                metrics={
                    "rule_count": len(rule_hits),
                    "failed_rule_count": int(decision.get("failed_rule_count") or 0),
                },
                attributes={
                    "decision": decision.get("status"),
                    "reason": decision.get("reason"),
                },
            ),
        ]
    )
    edges.extend(
        [
            RuntimeGraphEdge(
                edge_id=f"{candidate_set_id}:feeds-policy",
                source=candidate_set_id,
                target=policy_set_id,
                relation="feeds_policy",
                stage_id=definition.stage_id,
                status=gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"rule_count": len(rule_hits), "decision": decision.get("status")},
            ),
            RuntimeGraphEdge(
                edge_id=f"{policy_set_id}:governs-rule-hits",
                source=policy_set_id,
                target=rule_hit_set_id,
                relation="governs",
                stage_id=definition.stage_id,
                status=gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"failed_rule_count": int(decision.get("failed_rule_count") or 0)},
            ),
            RuntimeGraphEdge(
                edge_id=f"{rule_hit_set_id}:results_in",
                source=rule_hit_set_id,
                target=gate_id,
                relation="results_in",
                stage_id=definition.stage_id,
                status=gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=True,
                attributes={"decision": decision.get("status"), "reason": decision.get("reason")},
            ),
        ]
    )

    for rule_hit in rule_hits:
        rule_node_id = _rule_node_id(document_id, rule_hit)
        rule_status = _rule_hit_runtime_status(rule_hit)
        record = records_by_rule.get(str(rule_hit.get("rule_id") or rule_hit.get("key") or "rule"), {})
        nodes.append(
            RuntimeGraphNode(
                node_id=rule_node_id,
                label=str(rule_hit.get("label") or rule_hit.get("key") or "Rule Hit"),
                node_type="rule_hit",
                stage_id=definition.stage_id,
                status=rule_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=False,
                metrics={
                    "passed": 1 if rule_hit.get("passed") else 0,
                    "actual": rule_hit.get("actual"),
                },
                attributes={
                    "rule_key": rule_hit.get("key"),
                    "threshold": rule_hit.get("threshold"),
                    "action": rule_hit.get("action"),
                    "outcome": rule_hit.get("outcome"),
                    "detail": rule_hit.get("detail"),
                    "rule_id": record.get("rule_id"),
                    "rule_version": record.get("rule_version"),
                    "rule_hash": record.get("rule_hash"),
                    "snapshot_id": record.get("snapshot_id"),
                    "input_hash": record.get("input_hash"),
                    "output_hash": record.get("output_hash"),
                    "affected_object_ids": record.get("affected_object_ids", []),
                },
            )
        )
        candidate_edge_id = f"{candidate_set_id}:evaluated_by:{rule_hit.get('key') or rule_node_id}"
        edges.append(
            RuntimeGraphEdge(
                edge_id=candidate_edge_id,
                source=candidate_set_id,
                target=rule_node_id,
                relation="evaluated_by",
                stage_id=definition.stage_id,
                status=rule_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=False,
                attributes={
                    "rule_key": rule_hit.get("key"),
                    "threshold": rule_hit.get("threshold"),
                    "action": rule_hit.get("action"),
                },
            )
        )
        edge_id = f"{rule_node_id}:results_in"
        edges.append(
            RuntimeGraphEdge(
                edge_id=edge_id,
                source=rule_node_id,
                target=rule_hit_set_id,
                relation="results_in",
                stage_id=definition.stage_id,
                status=rule_status if rule_status != RuntimeStatus.COMPLETED else gate_status,
                origin=RuntimeOrigin.DERIVED,
                is_primary=False,
                attributes={"action": rule_hit.get("action"), "outcome": rule_hit.get("outcome")},
            )
        )
        node_observers[rule_node_id] = _build_rule_observer(
            document_id=document_id,
            document_title=document_title,
            rule_node_id=rule_node_id,
            gate_id=gate_id,
            rule_hit=rule_hit,
            status=rule_status,
        )
        edge_observers[candidate_edge_id] = _build_candidate_rule_edge_observer(
            document_id=document_id,
            document_title=document_title,
            edge_id=candidate_edge_id,
            candidate_set_id=candidate_set_id,
            rule_node_id=rule_node_id,
            rule_hit=rule_hit,
            status=rule_status,
        )
        edge_observers[edge_id] = _build_rule_edge_observer(
            document_id=document_id,
            document_title=document_title,
            edge_id=edge_id,
            rule_node_id=rule_node_id,
            gate_id=rule_hit_set_id,
            status=gate_status,
        )

    nodes.append(
        RuntimeGraphNode(
            node_id=gate_id,
            label="Gate 决策",
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
                "failed_rule_count": int(decision.get("failed_rule_count") or 0),
            },
            attributes={
                "decision": decision.get("status"),
                "reason": decision.get("reason"),
                "next_action": decision.get("next_action"),
                "policy_snapshot_id": (trace.get("policy") or {}).get("snapshot_id"),
            },
        )
    )

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
                edge_id=f"{item_node_id}:feeds_candidate_set",
                source=item_node_id,
                target=candidate_set_id,
                relation="feeds_candidate_set",
                stage_id=definition.stage_id,
                status=item_status,
                origin=RuntimeOrigin.SOURCE,
                attributes={"review_status": item.get("review_status", "pending")},
            )
        )

    outcome_node_id = _append_outcome_path(
        nodes=nodes,
        edges=edges,
        gate_id=gate_id,
        blocked_id=blocked_id,
        publish_target_id=publish_target_id,
        document_id=document_id,
        definition_stage_id=definition.stage_id,
        decision=decision,
        current_version=current_version,
        document_published=document_published,
    )

    stage_observer = _build_stage_observer(
        document_id=document_id,
        document_title=document_title,
        gate_id=gate_id,
        first_rule_node_id=primary_rule_node_id,
        gate_status=gate_status,
        decision=decision,
        metrics=metrics,
        rule_hits=rule_hits,
        current_version=current_version,
        trace_events=trace_events,
        trace_sections=trace_sections,
    )
    node_observers[candidate_set_id] = _build_candidate_set_observer(
        document_id=document_id,
        document_title=document_title,
        candidate_set_id=candidate_set_id,
        first_rule_node_id=primary_rule_node_id,
        status=candidate_status,
        metrics={
            "knowledge_item_count": len(knowledge_items),
            "approved_count": len(approved_items),
            "pending_count": len(pending_items),
            "rejected_count": len(rejected_items),
            "rule_count": len(rule_hits),
        },
    )
    node_observers[policy_set_id] = _build_policy_set_observer(
        document_id=document_id,
        document_title=document_title,
        policy_set_id=policy_set_id,
        rule_hit_set_id=rule_hit_set_id,
        status=gate_status,
        decision=decision,
        rule_hits=rule_hits,
    )
    node_observers[rule_hit_set_id] = _build_rule_hit_set_observer(
        document_id=document_id,
        document_title=document_title,
        rule_hit_set_id=rule_hit_set_id,
        first_rule_node_id=primary_rule_node_id,
        gate_id=gate_id,
        status=gate_status,
        decision=decision,
        rule_hits=rule_hits,
    )
    node_observers[gate_id] = _build_gate_observer(
        document_id=document_id,
        document_title=document_title,
        gate_id=gate_id,
        first_rule_node_id=primary_rule_node_id,
        gate_status=gate_status,
        decision=decision,
        metrics=metrics,
    )
    node_observers[outcome_node_id] = _build_outcome_observer(
        document_id=document_id,
        document_title=document_title,
        outcome_node_id=outcome_node_id,
        gate_id=gate_id,
        decision=decision,
        status=gate_status,
        current_version=current_version,
        document_published=document_published,
    )

    primary_node_ids = [candidate_set_id, policy_set_id, rule_hit_set_id, gate_id, outcome_node_id]
    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=gate_status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=primary_node_ids,
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
        rule_execution_records=rule_execution_records,
    )


def _append_outcome_path(
    *,
    nodes: list[RuntimeGraphNode],
    edges: list[RuntimeGraphEdge],
    gate_id: str,
    blocked_id: str,
    publish_target_id: str,
    document_id: str,
    definition_stage_id: str,
    decision: dict[str, Any],
    current_version: dict[str, Any] | None,
    document_published: bool,
) -> str:
    decision_status = str(decision.get("status") or "blocked")
    if decision_status == "blocked":
        outcome_node_id = blocked_id
        outcome_status = RuntimeStatus.BLOCKED
        relation = "blocked_by"
        label = "阻断结果"
        node_type = "blocked_result"
    else:
        outcome_node_id = publish_target_id
        outcome_status = RuntimeStatus.COMPLETED if decision_status == "passed" and document_published else RuntimeStatus.WARNING if decision_status != "passed" else RuntimeStatus.RUNNING
        relation = "publishes_to" if decision_status == "passed" else "continues_with_policy_note"
        label = "发布目标" if decision_status == "passed" else "带策略告警继续"
        node_type = "publish_target"

    nodes.append(
        RuntimeGraphNode(
            node_id=outcome_node_id,
            label=label,
            node_type=node_type,
            stage_id=definition_stage_id,
            status=outcome_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "decision": decision_status,
                "reason": decision.get("reason"),
                "version_label": (current_version or {}).get("version_label") or "pending",
                "document_published": document_published,
            },
        )
    )
    edges.append(
        RuntimeGraphEdge(
            edge_id=f"{gate_id}:{relation}",
            source=gate_id,
            target=outcome_node_id,
            relation=relation,
            stage_id=definition_stage_id,
            status=outcome_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"decision": decision_status, "next_action": decision.get("next_action")},
        )
    )
    return outcome_node_id


def _build_stage_observer(
    *,
    document_id: str,
    document_title: str,
    gate_id: str,
    first_rule_node_id: str,
    gate_status: RuntimeStatus,
    decision: dict[str, Any],
    metrics: dict[str, Any],
    rule_hits: list[dict[str, Any]],
    current_version: dict[str, Any] | None,
    trace_events: list[RuntimeEvent],
    trace_sections: list[RuntimeSummarySection],
) -> RuntimeObserverPayload:
    decision_status = str(decision.get("status") or gate_status.value)
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="阶段视角 · 质量门禁",
        subtitle=document_title,
        status=gate_status,
        stream=merge_runtime_events(
            [
                RuntimeEvent(
                    event_id=f"{document_id}:quality-gate:policy-summary",
                    kind="rule",
                    level="danger" if decision_status == "blocked" else ("warning" if decision_status != "passed" else "success"),
                    message=f"Quality gate evaluated {len(rule_hits)} executable policy rules and decided {decision_status}.",
                    object_id=gate_id,
                    object_kind="node",
                )
            ],
            trace_events,
        ),
        sections=merge_runtime_sections(
            [
                RuntimeSummarySection(
                    section_id="gate-summary",
                    title="Gate Summary",
                    fields=[
                        RuntimeSummaryField(key="decision", label="decision", value=decision_status, tone=_decision_tone(decision_status)),
                        RuntimeSummaryField(key="failed_rule_count", label="failed_rule_count", value=str(decision.get("failed_rule_count", 0)), tone="warning" if decision.get("failed_rule_count") else "success"),
                        RuntimeSummaryField(key="reason", label="reason", value=str(decision.get("reason") or "none"), tone=_decision_tone(decision_status)),
                        RuntimeSummaryField(key="current_version", label="current_version", value=(current_version or {}).get("version_label") or "unpublished", tone="info"),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="gate-metrics",
                    title="Gate Metrics",
                    fields=[
                        RuntimeSummaryField(key=key, label=key, value=str(value), tone="info")
                        for key, value in metrics.items()
                    ],
                ),
            ],
            trace_sections,
        ),
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(action_id="view-rule-hits", label="View Rule Hits", target_kind="node", target_id=first_rule_node_id),
        ],
    )


def _build_candidate_set_observer(
    *,
    document_id: str,
    document_title: str,
    candidate_set_id: str,
    first_rule_node_id: str,
    status: RuntimeStatus,
    metrics: dict[str, Any],
) -> RuntimeObserverPayload:
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title="Candidate Knowledge Set",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:candidate-set",
                kind="info",
                level="warning" if status == RuntimeStatus.WARNING else "success",
                message=(
                    "Canonical knowledge candidates are batched as the gate input before executable "
                    "policy rules are evaluated."
                ),
                object_id=candidate_set_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="candidate-set",
                title="Candidate Set",
                fields=[
                    RuntimeSummaryField(key=key, label=key, value=str(value), tone="info")
                    for key, value in metrics.items()
                ],
            )
        ],
        actions=[
            RuntimeAction(
                action_id="view-first-rule",
                label="View First Policy Rule",
                target_kind="node",
                target_id=first_rule_node_id,
            )
        ],
    )


def _build_policy_set_observer(
    *,
    document_id: str,
    document_title: str,
    policy_set_id: str,
    rule_hit_set_id: str,
    status: RuntimeStatus,
    decision: dict[str, Any],
    rule_hits: list[dict[str, Any]],
) -> RuntimeObserverPayload:
    decision_status = str(decision.get("status") or status.value)
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title="质量策略集合",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:policy-set",
                kind="rule",
                level=_event_level(decision_status),
                message=f"质量策略集合收口 {len(rule_hits)} 条可执行规则，先形成规则命中集合，再汇总为 Gate 决策。",
                object_id=policy_set_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="policy-set",
                title="策略集合",
                fields=[
                    RuntimeSummaryField(key="rule_count", label="规则数量", value=str(len(rule_hits)), tone="info"),
                    RuntimeSummaryField(
                        key="failed_rule_count",
                        label="未通过规则",
                        value=str(decision.get("failed_rule_count", 0)),
                        tone="warning" if decision.get("failed_rule_count") else "success",
                    ),
                    RuntimeSummaryField(key="decision", label="门禁决策", value=decision_status, tone=_decision_tone(decision_status)),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-rule-hit-set", label="查看规则命中集合", target_kind="node", target_id=rule_hit_set_id)
        ],
    )


def _build_rule_hit_set_observer(
    *,
    document_id: str,
    document_title: str,
    rule_hit_set_id: str,
    first_rule_node_id: str,
    gate_id: str,
    status: RuntimeStatus,
    decision: dict[str, Any],
    rule_hits: list[dict[str, Any]],
) -> RuntimeObserverPayload:
    failed_hits = [hit for hit in rule_hits if hit.get("outcome") != "passed"]
    decision_status = str(decision.get("status") or status.value)
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title="规则命中集合",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:rule-hit-set",
                kind="rule",
                level=_event_level(decision_status),
                message=f"规则命中集合包含 {len(rule_hits)} 条命中结果，其中 {len(failed_hits)} 条导致告警或阻断。",
                object_id=rule_hit_set_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="rule-hit-set",
                title="规则命中摘要",
                fields=[
                    RuntimeSummaryField(key="rule_count", label="规则数量", value=str(len(rule_hits)), tone="info"),
                    RuntimeSummaryField(key="failed_rule_count", label="未通过规则", value=str(len(failed_hits)), tone="warning" if failed_hits else "success"),
                    RuntimeSummaryField(key="decision", label="门禁决策", value=decision_status, tone=_decision_tone(decision_status)),
                    RuntimeSummaryField(key="reason", label="原因", value=str(decision.get("reason") or "none"), tone=_decision_tone(decision_status)),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-first-rule", label="展开单条规则", target_kind="node", target_id=first_rule_node_id),
            RuntimeAction(action_id="view-gate", label="查看 Gate 决策", target_kind="node", target_id=gate_id),
        ],
    )


def _build_rule_observer(
    *,
    document_id: str,
    document_title: str,
    rule_node_id: str,
    gate_id: str,
    rule_hit: dict[str, Any],
    status: RuntimeStatus,
) -> RuntimeObserverPayload:
    outcome = str(rule_hit.get("outcome") or "not_evaluated")
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title=str(rule_hit.get("label") or rule_hit.get("key") or "Rule Hit"),
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:rule-node:{rule_hit.get('key')}",
                kind="rule",
                level="success" if outcome == "passed" else "warning",
                message=f"Rule {rule_hit.get('key')} outcome={outcome}; action={rule_hit.get('action')}.",
                object_id=rule_node_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="rule",
                title="Rule Information",
                fields=[
                    RuntimeSummaryField(key="rule_key", label="rule_key", value=str(rule_hit.get("key"))),
                    RuntimeSummaryField(key="threshold", label="threshold", value=str(rule_hit.get("threshold"))),
                    RuntimeSummaryField(key="action", label="action", value=str(rule_hit.get("action")), tone="info"),
                    RuntimeSummaryField(key="outcome", label="outcome", value=outcome, tone="success" if outcome == "passed" else "warning"),
                    RuntimeSummaryField(key="actual", label="actual", value=str(rule_hit.get("actual"))),
                    RuntimeSummaryField(key="detail", label="detail", value=str(rule_hit.get("detail"))),
                ],
            )
        ],
        actions=[RuntimeAction(action_id="view-gate", label="View Gate Decision", target_kind="node", target_id=gate_id)],
    )


def _build_gate_observer(
    *,
    document_id: str,
    document_title: str,
    gate_id: str,
    first_rule_node_id: str,
    gate_status: RuntimeStatus,
    decision: dict[str, Any],
    metrics: dict[str, Any],
) -> RuntimeObserverPayload:
    decision_status = str(decision.get("status") or gate_status.value)
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title="Gate Decision",
        subtitle=document_title,
        status=gate_status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:gate-node",
                kind="decision",
                level=_event_level(decision_status),
                message=f"Gate decision is {decision_status}: {decision.get('reason')}.",
                object_id=gate_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="decision",
                title="Decision Summary",
                fields=[
                    RuntimeSummaryField(key="gate_status", label="gate_status", value=gate_status.value, tone=_decision_tone(decision_status)),
                    RuntimeSummaryField(key="decision", label="decision", value=decision_status, tone=_decision_tone(decision_status)),
                    RuntimeSummaryField(key="reason", label="reason", value=str(decision.get("reason") or "none")),
                    RuntimeSummaryField(key="risk_score", label="risk_score", value=str(metrics.get("risk_score")), tone="info"),
                    RuntimeSummaryField(key="supporting_documents", label="supporting_documents", value=str(metrics.get("supporting_documents")), tone="info"),
                ],
            )
        ],
        actions=[RuntimeAction(action_id="view-rule-hit", label="View Rule Hit", target_kind="node", target_id=first_rule_node_id)],
    )


def _build_outcome_observer(
    *,
    document_id: str,
    document_title: str,
    outcome_node_id: str,
    gate_id: str,
    decision: dict[str, Any],
    status: RuntimeStatus,
    current_version: dict[str, Any] | None,
    document_published: bool,
) -> RuntimeObserverPayload:
    decision_status = str(decision.get("status") or status.value)
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title="Gate Outcome",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:outcome-node",
                kind="decision",
                level=_event_level(decision_status),
                message=f"Quality gate outcome is {decision_status}; next action is {decision.get('next_action')}.",
                object_id=outcome_node_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="outcome",
                title="Outcome",
                fields=[
                    RuntimeSummaryField(key="decision", label="decision", value=decision_status, tone=_decision_tone(decision_status)),
                    RuntimeSummaryField(key="next_action", label="next_action", value=str(decision.get("next_action") or "none"), tone="info"),
                    RuntimeSummaryField(key="version_label", label="version_label", value=(current_version or {}).get("version_label") or "pending", tone="info"),
                    RuntimeSummaryField(key="document_published", label="document_published", value="true" if document_published else "false", tone="success" if document_published else "warning"),
                ],
            )
        ],
        actions=[RuntimeAction(action_id="view-gate", label="View Gate Decision", target_kind="node", target_id=gate_id)],
    )


def _build_candidate_rule_edge_observer(
    *,
    document_id: str,
    document_title: str,
    edge_id: str,
    candidate_set_id: str,
    rule_node_id: str,
    rule_hit: dict[str, Any],
    status: RuntimeStatus,
) -> RuntimeObserverPayload:
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.EDGE,
        title="evaluated_by",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:candidate-rule-edge:{rule_hit.get('key')}",
                kind="rule",
                level="danger" if status == RuntimeStatus.BLOCKED else "info",
                message=(
                    f"Candidate set is evaluated by policy rule {rule_hit.get('key')}; "
                    f"action={rule_hit.get('action')}."
                ),
                object_id=edge_id,
                object_kind="edge",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="relation",
                title="Relation Summary",
                fields=[
                    RuntimeSummaryField(key="relation", label="relation", value="evaluated_by"),
                    RuntimeSummaryField(key="source", label="source", value="Candidate Knowledge Set"),
                    RuntimeSummaryField(key="target", label="target", value=str(rule_hit.get("label") or rule_hit.get("key"))),
                    RuntimeSummaryField(key="threshold", label="threshold", value=str(rule_hit.get("threshold"))),
                    RuntimeSummaryField(key="action", label="action", value=str(rule_hit.get("action")), tone="info"),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-source-node", label="View Candidate Set", target_kind="node", target_id=candidate_set_id),
            RuntimeAction(action_id="view-target-node", label="View Policy Rule", target_kind="node", target_id=rule_node_id),
        ],
    )


def _build_rule_edge_observer(
    *,
    document_id: str,
    document_title: str,
    edge_id: str,
    rule_node_id: str,
    gate_id: str,
    status: RuntimeStatus,
) -> RuntimeObserverPayload:
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.EDGE,
        title="results_in",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:quality-gate:edge:{edge_id}",
                kind="result",
                level="danger" if status == RuntimeStatus.BLOCKED else "info",
                message="Rule evaluation result is folded into the gate decision.",
                object_id=edge_id,
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
            RuntimeAction(action_id="view-source-node", label="View Source Node", target_kind="node", target_id=rule_node_id),
            RuntimeAction(action_id="view-target-node", label="View Target Node", target_kind="node", target_id=gate_id),
        ],
    )


def _stable_runtime_hash(payload: Any) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item) != ""]


def _build_rule_execution_records(
    *,
    archive_id: str,
    document_id: str,
    stage_id: str,
    rule_hits: list[dict[str, Any]],
    knowledge_items: list[dict[str, Any]],
    decision: dict[str, Any],
    trace: dict[str, Any],
) -> list[dict[str, Any]]:
    policy = trace.get("policy") if isinstance(trace.get("policy"), dict) else {}
    snapshot_id = str(policy.get("snapshot_id") or trace.get("snapshot_id") or "")
    default_affected_ids = [
        str(item.get("id"))
        for item in knowledge_items[:8]
        if item.get("id") is not None and str(item.get("id")) != ""
    ]
    records: list[dict[str, Any]] = []

    for index, rule_hit in enumerate(rule_hits, start=1):
        rule_id = str(rule_hit.get("rule_id") or rule_hit.get("key") or f"rule-{index}")
        rule_version = str(rule_hit.get("rule_version") or "r1.0")
        affected_object_ids = _as_string_list(rule_hit.get("affected_object_ids")) or default_affected_ids
        affected_relation_ids = _as_string_list(rule_hit.get("affected_relation_ids"))
        input_artifact_refs = _as_string_list(rule_hit.get("input_artifact_refs")) or [
            "canonical_knowledge_items",
            "quality_metrics",
            "policy_snapshot",
        ]
        output_artifact_refs = _as_string_list(rule_hit.get("output_artifact_refs")) or [
            "rule_hit_set",
            "quality_gate_decision",
        ]
        input_payload = {
            "archive_id": archive_id,
            "document_id": document_id,
            "stage_id": stage_id,
            "rule_id": rule_id,
            "actual": rule_hit.get("actual"),
            "threshold": rule_hit.get("threshold"),
            "input_artifact_refs": input_artifact_refs,
        }
        output_payload = {
            "rule_id": rule_id,
            "outcome": rule_hit.get("outcome"),
            "action": rule_hit.get("action"),
            "affected_object_ids": affected_object_ids,
            "decision": decision.get("status"),
        }
        records.append(
            {
                "execution_id": str(rule_hit.get("execution_id") or f"rex-{document_id}-{stage_id}-{rule_id}"),
                "archive_id": archive_id,
                "document_id": document_id,
                "stage_id": stage_id,
                "rule_id": rule_id,
                "rule_version": rule_version,
                "rule_hash": str(rule_hit.get("rule_hash") or _stable_runtime_hash({"rule_id": rule_id, "rule_version": rule_version, "threshold": rule_hit.get("threshold")})),
                "snapshot_id": snapshot_id or None,
                "input_artifact_refs": input_artifact_refs,
                "input_hash": str(rule_hit.get("input_hash") or _stable_runtime_hash(input_payload)),
                "output_artifact_refs": output_artifact_refs,
                "output_hash": str(rule_hit.get("output_hash") or _stable_runtime_hash(output_payload)),
                "affected_object_ids": affected_object_ids,
                "affected_relation_ids": affected_relation_ids,
                "decision": str(rule_hit.get("action") or decision.get("status") or "not_evaluated"),
                "metrics": {
                    "actual": rule_hit.get("actual"),
                    "threshold": rule_hit.get("threshold"),
                    "outcome": rule_hit.get("outcome"),
                    "passed": bool(rule_hit.get("passed")),
                },
                "executed_at": rule_hit.get("executed_at") or trace.get("executed_at"),
                "source": "runtime_trace" if trace.get("rule_hits") else "derived",
            }
        )

    return records


def _normalize_rule_hits(runtime_trace: dict[str, Any], contribution: dict[str, Any]) -> list[dict[str, Any]]:
    rule_hits = [item for item in runtime_trace.get("rule_hits", []) if isinstance(item, dict)]
    if rule_hits:
        return [_normalize_quality_gate_rule_hit(hit) for hit in rule_hits]
    evidence_count = _count_evidence(contribution)
    outcome = "failed" if evidence_count == 0 else "passed"
    return [
        {
            "key": "min_supporting_documents",
            "label": "minimum supporting documents",
            "threshold": "evidence_count > 0",
            "action": "block_return",
            "outcome": outcome,
            "passed": outcome == "passed",
            "actual": evidence_count,
            "detail": f"evidence_count actual={evidence_count} expected > 0",
        }
    ]


def _normalize_decision(
    runtime_trace: dict[str, Any],
    contribution: dict[str, Any],
    pending_items: list[dict[str, Any]],
    rejected_items: list[dict[str, Any]],
) -> dict[str, Any]:
    decision = runtime_trace.get("decision")
    if isinstance(decision, dict) and decision.get("status"):
        return _normalize_quality_gate_decision(decision)

    evidence_count = _count_evidence(contribution)
    should_block = evidence_count == 0 or bool(rejected_items)
    should_warn = not should_block and bool(pending_items)
    status = "blocked" if should_block else "warning" if should_warn else "passed"
    return {
        "status": status,
        "reason": _block_reason(evidence_count, pending_items, rejected_items),
        "next_action": "blocked_result" if should_block else "continue_with_warning" if should_warn else "publish_target",
        "failed_rule_count": 1 if should_block else 0,
    }


def _normalize_metrics(
    runtime_trace: dict[str, Any],
    contribution: dict[str, Any],
    knowledge_items: list[dict[str, Any]],
) -> dict[str, Any]:
    metrics = runtime_trace.get("metrics")
    if isinstance(metrics, dict):
        return metrics
    return {
        "knowledge_item_count": len(knowledge_items),
        "evidence_count": _count_evidence(contribution),
        "supporting_documents": len(
            {
                document_id
                for item in knowledge_items
                for document_id in item.get("document_ids", [])
            }
        ),
        "pending_review_count": sum(1 for item in knowledge_items if item.get("review_status", "pending") == "pending"),
        "rejected_count": sum(1 for item in knowledge_items if item.get("review_status") == "rejected"),
        "hard_conflict": 0,
        "risk_score": 1.0,
    }


def _decision_runtime_status(decision_status: Any, *, document_published: bool) -> RuntimeStatus:
    if decision_status == "blocked":
        return RuntimeStatus.BLOCKED
    if decision_status in {"manual_review", "warning", "deferred"}:
        return RuntimeStatus.WARNING
    if decision_status == "passed":
        return RuntimeStatus.COMPLETED if document_published else RuntimeStatus.COMPLETED
    return RuntimeStatus.BLOCKED


def _rule_hit_runtime_status(rule_hit: dict[str, Any]) -> RuntimeStatus:
    if rule_hit.get("outcome") == "failed":
        return RuntimeStatus.BLOCKED if rule_hit.get("action") == "block_return" else RuntimeStatus.WARNING
    if rule_hit.get("outcome") == "not_evaluated":
        return RuntimeStatus.WARNING
    return RuntimeStatus.COMPLETED


def _rule_node_id(document_id: str, rule_hit: dict[str, Any]) -> str:
    key = str(rule_hit.get("key") or "rule").replace(" ", "-")
    return f"{document_id}:quality-gate:rule-hit:{key}"


def _decision_tone(decision_status: str) -> str:
    if decision_status == "blocked":
        return "danger"
    if decision_status in {"manual_review", "warning", "deferred"}:
        return "warning"
    return "success"


def _event_level(decision_status: str) -> str:
    if decision_status == "blocked":
        return "danger"
    if decision_status in {"manual_review", "warning", "deferred"}:
        return "warning"
    return "success"


def _normalize_quality_gate_action(action: Any) -> str:
    if action == "manual_review":
        return "warn_continue"
    return str(action or "block_return")


def _normalize_quality_gate_status(status: Any) -> str:
    if status == "manual_review":
        return "warning"
    return str(status or "blocked")


def _normalize_quality_gate_rule_hit(rule_hit: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(rule_hit)
    normalized["action"] = _normalize_quality_gate_action(normalized.get("action"))
    return normalized


def _normalize_quality_gate_decision(decision: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(decision)
    status = _normalize_quality_gate_status(normalized.get("status"))
    normalized["status"] = status
    if normalized.get("next_action") == "manual_review":
        normalized["next_action"] = "continue_with_warning"
    elif status == "warning" and not normalized.get("next_action"):
        normalized["next_action"] = "continue_with_warning"
    return normalized


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
                    "document_ids": item.get("document_ids", []),
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
    if rejected_items:
        return "rejected knowledge items remain in the candidate set"
    if pending_items:
        return "items remain pending for post-publication review"
    return "no blocking condition"
