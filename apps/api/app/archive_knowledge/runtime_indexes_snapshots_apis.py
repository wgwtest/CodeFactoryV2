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


def build_indexes_snapshots_apis_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    current_version: dict[str, Any] | None,
    document_published: bool,
    contribution: dict[str, Any] | None = None,
    knowledge_items: list[dict[str, Any]] | None = None,
    status_override: RuntimeStatus | None = None,
    gate_decision_status: str | None = None,
    gate_decision_reason: str | None = None,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["indexes_snapshots_apis"]
    knowledge_items = list(knowledge_items or _derive_items_from_contribution(contribution or {}))
    item_count = len(knowledge_items)
    pending_count = sum(1 for item in knowledge_items if item.get("review_status", "pending") == "pending")
    approved_count = sum(1 for item in knowledge_items if item.get("review_status") == "approved")
    rejected_count = sum(1 for item in knowledge_items if item.get("review_status") == "rejected")
    evidence_count = _count_evidence(knowledge_items, contribution or {})
    gate_decision = _derive_gate_decision(
        item_count=item_count,
        evidence_count=evidence_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        gate_decision_status=gate_decision_status,
        gate_decision_reason=gate_decision_reason,
    )
    machine_candidate_published = document_published or (
        item_count > 0 and gate_decision["status"] != "blocked"
    )
    formally_admitted = document_published and bool(current_version)
    stage_status = status_override or _publication_stage_status(
        gate_decision["status"],
        machine_candidate_published=machine_candidate_published,
        formally_admitted=formally_admitted,
    )

    gate_id = f"{document_id}:publish-layer:gate-decision"
    snapshot_id = f"{document_id}:publish-layer:candidate-snapshot"
    exposure_id = f"{document_id}:publish-layer:exposure-scope"
    governance_id = f"{document_id}:publish-layer:governance-confirmation"
    version_label = (current_version or {}).get("version_label") or "not_published"
    machine_candidate_label = "机器已发布候选" if machine_candidate_published else "机器尚未发布候选"
    governance_label = (
        "治理已确认"
        if formally_admitted
        else "等待治理确认"
        if machine_candidate_published
        else "未进入治理确认"
    )
    formal_entry_label = "已正式入库" if formally_admitted else "尚未正式入库"
    exposure_scope = (
        "候选快照已暴露给搜索索引、图谱索引与运行态 API"
        if machine_candidate_published
        else "索引/API 暴露范围等待发布候选快照"
    )
    gate_status = _decision_runtime_status(gate_decision["status"])
    snapshot_status = RuntimeStatus.COMPLETED if machine_candidate_published else gate_status
    exposure_status = RuntimeStatus.COMPLETED if machine_candidate_published else gate_status
    governance_status = (
        RuntimeStatus.COMPLETED
        if formally_admitted
        else RuntimeStatus.WARNING
        if machine_candidate_published
        else gate_status
    )

    nodes = [
        RuntimeGraphNode(
            node_id=gate_id,
            label="门禁决策",
            node_type="gate_decision",
            stage_id=definition.stage_id,
            status=gate_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "candidate_count": item_count,
                "evidence_count": evidence_count,
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
            },
            attributes={
                "decision": gate_decision["status"],
                "reason": gate_decision["reason"],
                "next_action": gate_decision["next_action"],
            },
        ),
        RuntimeGraphNode(
            node_id=snapshot_id,
            label="发布候选快照",
            node_type="publication_candidate_snapshot",
            stage_id=definition.stage_id,
            status=snapshot_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "candidate_source": "publication_candidate_snapshot",
                "machine_candidate_status": machine_candidate_label,
                "version_label": version_label,
            },
        ),
        RuntimeGraphNode(
            node_id=exposure_id,
            label="索引/API 暴露范围",
            node_type="index_api_exposure_scope",
            stage_id=definition.stage_id,
            status=exposure_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "scope": exposure_scope,
                "search_index": machine_candidate_published,
                "graph_index": machine_candidate_published,
                "runtime_api": machine_candidate_published,
                "version_label": version_label,
            },
        ),
        RuntimeGraphNode(
            node_id=governance_id,
            label="待治理确认",
            node_type="governance_confirmation",
            stage_id=definition.stage_id,
            status=governance_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "governance_confirmation_status": governance_label,
                "formal_entry_status": formal_entry_label,
                "pending_review_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
            },
        ),
    ]

    edges = [
        RuntimeGraphEdge(
            edge_id=f"{gate_id}:authorizes_candidate_snapshot",
            source=gate_id,
            target=snapshot_id,
            relation="authorizes_candidate_snapshot",
            stage_id=definition.stage_id,
            status=snapshot_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"decision": gate_decision["status"]},
        ),
        RuntimeGraphEdge(
            edge_id=f"{snapshot_id}:exposes_scope",
            source=snapshot_id,
            target=exposure_id,
            relation="exposes_scope",
            stage_id=definition.stage_id,
            status=exposure_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"scope": exposure_scope},
        ),
        RuntimeGraphEdge(
            edge_id=f"{exposure_id}:awaits_governance_confirmation",
            source=exposure_id,
            target=governance_id,
            relation="awaits_governance_confirmation",
            stage_id=definition.stage_id,
            status=governance_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"formal_entry_status": formal_entry_label},
        ),
    ]

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="阶段视角 · 发布候选快照",
        subtitle=document_title,
        status=stage_status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:gate-decision",
                kind="decision",
                level=_decision_event_level(gate_decision["status"]),
                message=f"门禁决策为 {gate_decision['label']}：{gate_decision['reason']}",
                object_id=gate_id,
                object_kind="stage",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:candidate-snapshot",
                kind="progress",
                level="success" if machine_candidate_published else "warning",
                message=machine_candidate_label,
                object_id=snapshot_id,
                object_kind="stage",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:governance",
                kind="result",
                level="success" if formally_admitted else "warning",
                message=f"{governance_label}；正式入库状态：{formal_entry_label}",
                object_id=governance_id,
                object_kind="stage",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="publication-candidate-boundary",
                title="发布候选边界",
                fields=[
                    RuntimeSummaryField(key="gate_decision", label="门禁决策", value=gate_decision["label"], tone=_decision_tone(gate_decision["status"])),
                    RuntimeSummaryField(key="machine_candidate_status", label="机器发布候选", value=machine_candidate_label, tone="success" if machine_candidate_published else "warning"),
                    RuntimeSummaryField(key="governance_confirmation_status", label="治理确认", value=governance_label, tone="success" if formally_admitted else "warning"),
                    RuntimeSummaryField(key="formal_entry_status", label="正式入库状态", value=formal_entry_label, tone="success" if formally_admitted else "warning"),
                    RuntimeSummaryField(key="version_label", label="正式版本", value=version_label, tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="publication-candidate-scope",
                title="索引/API 暴露范围",
                fields=[
                    RuntimeSummaryField(key="candidate_count", label="候选对象数", value=str(item_count), tone="info"),
                    RuntimeSummaryField(key="pending_review_count", label="待治理确认", value=str(pending_count), tone="warning" if pending_count else "success"),
                    RuntimeSummaryField(key="approved_count", label="已确认", value=str(approved_count), tone="success"),
                    RuntimeSummaryField(key="rejected_count", label="已驳回", value=str(rejected_count), tone="danger" if rejected_count else "neutral"),
                    RuntimeSummaryField(key="exposure_scope", label="暴露范围", value=exposure_scope, tone="info"),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-gate-decision", label="查看门禁决策", target_kind="node", target_id=gate_id),
            RuntimeAction(action_id="view-candidate-snapshot", label="查看发布候选快照", target_kind="node", target_id=snapshot_id),
            RuntimeAction(action_id="view-governance-confirmation", label="查看治理确认", target_kind="node", target_id=governance_id),
        ],
    )

    node_observers = {
        gate_id: _node_observer(
            document_id=document_id,
            document_title=document_title,
            node_id=gate_id,
            title="节点视角 · 门禁决策",
            subtitle="质量门禁的规则结果决定是否生成发布候选快照。",
            status=gate_status,
            message=f"门禁决策：{gate_decision['label']}；下一步：{gate_decision['next_action']}",
            section_id="gate-decision-summary",
            section_title="门禁决策摘要",
            fields=[
                ("decision", "决策", gate_decision["label"], _decision_tone(gate_decision["status"])),
                ("reason", "原因", gate_decision["reason"], _decision_tone(gate_decision["status"])),
                ("candidate_count", "候选对象数", str(item_count), "info"),
                ("evidence_count", "证据数", str(evidence_count), "info"),
            ],
            actions=[
                RuntimeAction(action_id="view-candidate-snapshot", label="查看发布候选快照", target_kind="node", target_id=snapshot_id),
            ],
        ),
        snapshot_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 发布候选快照",
            subtitle=document_title,
            status=snapshot_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:snapshot",
                    kind="result",
                    level="success" if machine_candidate_published else "warning",
                    message=f"{machine_candidate_label}；这还不是正式入库版本。",
                    object_id=snapshot_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="candidate-snapshot-summary",
                    title="候选快照摘要",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="节点类型", value="publication_candidate_snapshot"),
                        RuntimeSummaryField(key="candidate_source", label="候选来源", value="publication_candidate_snapshot", tone="info"),
                        RuntimeSummaryField(key="machine_candidate_status", label="机器发布候选", value=machine_candidate_label, tone="success" if machine_candidate_published else "warning"),
                        RuntimeSummaryField(key="formal_entry_status", label="正式入库状态", value=formal_entry_label, tone="success" if formally_admitted else "warning"),
                        RuntimeSummaryField(key="version_label", label="正式版本", value=version_label),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-exposure-scope", label="查看索引/API 暴露范围", target_kind="node", target_id=exposure_id),
                RuntimeAction(action_id="view-governance", label="查看治理确认", target_kind="node", target_id=governance_id),
            ],
        ),
        exposure_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 索引/API 暴露范围",
            subtitle=document_title,
            status=exposure_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:exposure",
                    kind="result",
                    level="success" if machine_candidate_published else "warning",
                    message=exposure_scope,
                    object_id=exposure_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="exposure-summary",
                    title="暴露范围摘要",
                    fields=[
                        RuntimeSummaryField(key="search_index", label="搜索索引", value="候选可见" if machine_candidate_published else "未暴露", tone="success" if machine_candidate_published else "warning"),
                        RuntimeSummaryField(key="graph_index", label="图谱索引", value="候选可见" if machine_candidate_published else "未暴露", tone="success" if machine_candidate_published else "warning"),
                        RuntimeSummaryField(key="runtime_api", label="运行态 API", value="候选可见" if machine_candidate_published else "未暴露", tone="success" if machine_candidate_published else "warning"),
                        RuntimeSummaryField(key="version_label", label="正式版本", value=version_label),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-snapshot", label="查看发布候选快照", target_kind="node", target_id=snapshot_id)],
        ),
        governance_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 待治理确认",
            subtitle=document_title,
            status=governance_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:governance-node",
                    kind="result",
                    level="success" if formally_admitted else "warning",
                    message=f"{governance_label}；正式入库状态：{formal_entry_label}",
                    object_id=governance_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="governance-summary",
                    title="治理确认摘要",
                    fields=[
                        RuntimeSummaryField(key="governance_confirmation_status", label="治理确认", value=governance_label, tone="success" if formally_admitted else "warning"),
                        RuntimeSummaryField(key="formal_entry_status", label="正式入库状态", value=formal_entry_label, tone="success" if formally_admitted else "warning"),
                        RuntimeSummaryField(key="pending_review_count", label="待确认对象", value=str(pending_count), tone="warning" if pending_count else "success"),
                        RuntimeSummaryField(key="version_label", label="正式版本", value=version_label),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-exposure", label="查看索引/API 暴露范围", target_kind="node", target_id=exposure_id)],
        ),
    }

    edge_observers = {
        f"{gate_id}:authorizes_candidate_snapshot": _edge_observer(
            document_id=document_id,
            document_title=document_title,
            edge_id=f"{gate_id}:authorizes_candidate_snapshot",
            title="边视角 · 门禁决策 -> 发布候选快照",
            relation="authorizes_candidate_snapshot",
            status=snapshot_status,
            message=f"门禁决策 {gate_decision['label']} 后生成发布候选快照。",
            source_label="门禁决策",
            target_label="发布候选快照",
            source_id=gate_id,
            target_id=snapshot_id,
        ),
        f"{snapshot_id}:exposes_scope": _edge_observer(
            document_id=document_id,
            document_title=document_title,
            edge_id=f"{snapshot_id}:exposes_scope",
            title="边视角 · 发布候选快照 -> 索引/API 暴露范围",
            relation="exposes_scope",
            status=exposure_status,
            message=exposure_scope,
            source_label="发布候选快照",
            target_label="索引/API 暴露范围",
            source_id=snapshot_id,
            target_id=exposure_id,
        ),
        f"{exposure_id}:awaits_governance_confirmation": _edge_observer(
            document_id=document_id,
            document_title=document_title,
            edge_id=f"{exposure_id}:awaits_governance_confirmation",
            title="边视角 · 索引/API 暴露范围 -> 待治理确认",
            relation="awaits_governance_confirmation",
            status=governance_status,
            message=f"候选已对治理页可见，当前状态：{governance_label}。",
            source_label="索引/API 暴露范围",
            target_label="待治理确认",
            source_id=exposure_id,
            target_id=governance_id,
        ),
    }

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=stage_status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[gate_id, snapshot_id, exposure_id, governance_id],
            primary_edge_ids=[
                f"{gate_id}:authorizes_candidate_snapshot",
                f"{snapshot_id}:exposes_scope",
                f"{exposure_id}:awaits_governance_confirmation",
            ],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _derive_items_from_contribution(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for collection_name, item_type in (
        ("entities", "entity"),
        ("events", "event"),
        ("processes", "process"),
    ):
        for item in contribution.get(collection_name, []):
            items.append({"item_type": item_type, **item})
    return items


def _count_evidence(knowledge_items: list[dict[str, Any]], contribution: dict[str, Any]) -> int:
    count = sum(len(item.get("evidence", [])) for item in knowledge_items)
    if count:
        return count
    return sum(
        len(item.get("evidence", []))
        for collection_name in ("entities", "events", "processes")
        for item in contribution.get(collection_name, [])
    )


def _derive_gate_decision(
    *,
    item_count: int,
    evidence_count: int,
    pending_count: int,
    rejected_count: int,
    gate_decision_status: str | None = None,
    gate_decision_reason: str | None = None,
) -> dict[str, str]:
    if gate_decision_status:
        status = str(gate_decision_status)
        status_map = {
            "blocked": ("规则阻断", "block_candidate_snapshot"),
            "warning": ("告警继续", "publish_candidate_wait_governance"),
            "deferred": ("延迟发布", "publish_candidate_wait_governance"),
            "passed": ("规则放行", "publish_candidate_snapshot"),
            "pending": ("等待候选", "wait_for_candidate_snapshot"),
        }
        label, next_action = status_map.get(status, ("等待候选", "wait_for_candidate_snapshot"))
        return {
            "status": status,
            "label": label,
            "reason": gate_decision_reason or label,
            "next_action": next_action,
        }
    if item_count == 0:
        return {
            "status": "pending",
            "label": "等待候选",
            "reason": "尚未生成可发布的候选知识对象。",
            "next_action": "wait_for_candidate_snapshot",
        }
    if evidence_count == 0 or rejected_count > 0:
        return {
            "status": "blocked",
            "label": "规则阻断",
            "reason": "质量门禁发现证据不足或已驳回对象，不能生成发布候选。",
            "next_action": "block_candidate_snapshot",
        }
    if pending_count > 0:
        return {
            "status": "warning",
            "label": "告警继续",
            "reason": "质量门禁允许机器发布候选，但候选仍需治理确认后才能正式入库。",
            "next_action": "publish_candidate_wait_governance",
        }
    return {
        "status": "passed",
        "label": "规则放行",
        "reason": "质量门禁规则均已满足，候选可进入发布快照与索引/API 暴露。",
        "next_action": "publish_candidate_snapshot",
    }


def _publication_stage_status(
    decision_status: str,
    *,
    machine_candidate_published: bool,
    formally_admitted: bool,
) -> RuntimeStatus:
    if decision_status == "blocked":
        return RuntimeStatus.BLOCKED
    if formally_admitted:
        return RuntimeStatus.COMPLETED
    if machine_candidate_published:
        return RuntimeStatus.WARNING if decision_status == "warning" else RuntimeStatus.COMPLETED
    return RuntimeStatus.PENDING


def _decision_runtime_status(decision_status: str) -> RuntimeStatus:
    if decision_status == "blocked":
        return RuntimeStatus.BLOCKED
    if decision_status == "warning":
        return RuntimeStatus.WARNING
    if decision_status == "passed":
        return RuntimeStatus.COMPLETED
    return RuntimeStatus.PENDING


def _decision_tone(decision_status: str) -> str:
    if decision_status == "blocked":
        return "danger"
    if decision_status == "warning":
        return "warning"
    if decision_status == "passed":
        return "success"
    return "neutral"


def _decision_event_level(decision_status: str) -> str:
    if decision_status == "blocked":
        return "danger"
    if decision_status == "warning":
        return "warning"
    if decision_status == "passed":
        return "success"
    return "info"


def _node_observer(
    *,
    document_id: str,
    document_title: str,
    node_id: str,
    title: str,
    subtitle: str,
    status: RuntimeStatus,
    message: str,
    section_id: str,
    section_title: str,
    fields: list[tuple[str, str, str, str]],
    actions: list[RuntimeAction],
) -> RuntimeObserverPayload:
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.NODE,
        title=title,
        subtitle=subtitle or document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:{node_id}:observer",
                kind="result",
                level="danger" if status == RuntimeStatus.BLOCKED else "warning" if status == RuntimeStatus.WARNING else "success",
                message=message,
                object_id=node_id,
                object_kind="node",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id=section_id,
                title=section_title,
                fields=[
                    RuntimeSummaryField(key=key, label=label, value=value, tone=tone)
                    for key, label, value, tone in fields
                ],
            )
        ],
        actions=actions,
    )


def _edge_observer(
    *,
    document_id: str,
    document_title: str,
    edge_id: str,
    title: str,
    relation: str,
    status: RuntimeStatus,
    message: str,
    source_label: str,
    target_label: str,
    source_id: str,
    target_id: str,
) -> RuntimeObserverPayload:
    return RuntimeObserverPayload(
        mode=RuntimeObserverMode.EDGE,
        title=title,
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:{edge_id}",
                kind="result",
                level="danger" if status == RuntimeStatus.BLOCKED else "warning" if status == RuntimeStatus.WARNING else "success",
                message=message,
                object_id=edge_id,
                object_kind="edge",
            )
        ],
        sections=[
            RuntimeSummarySection(
                section_id="relation-summary",
                title="关系摘要",
                fields=[
                    RuntimeSummaryField(key="relation", label="关系类型", value=relation),
                    RuntimeSummaryField(key="source", label="源对象", value=source_label),
                    RuntimeSummaryField(key="target", label="目标对象", value=target_label),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=source_id),
            RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=target_id),
        ],
    )
