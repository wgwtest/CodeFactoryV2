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


def build_evidence_pack_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
) -> RuntimeStageSnapshot:
    definition = STAGE_DEFINITION_MAP["evidence_pack"]
    extraction = contribution.get("extraction", {})
    evidence_rows = _collect_evidence_rows(contribution)
    selected_evidence = evidence_rows
    evidence_count = len(evidence_rows)
    chunking_used = bool(extraction.get("chunking_used"))
    candidate_count = int(extraction.get("candidate_count") or 0)
    relation_count = int(extraction.get("relation_count") or 0)
    llm_provider = extraction.get("llm_provider") or "unknown"
    llm_model = extraction.get("llm_model") or "unknown"
    status = RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING

    input_set_id = f"{document_id}:evidence-pack:evidence-input-set"
    policy_node_id = f"{document_id}:evidence-pack:pack-policy"
    query_node_id = f"{document_id}:evidence-pack:query"
    pack_node_id = f"{document_id}:evidence-pack:pack"
    rerank_node_id = f"{document_id}:evidence-pack:rerank"
    target_node_id = f"{document_id}:evidence-pack:targets"

    nodes = [
        RuntimeGraphNode(
            node_id=input_set_id,
            label="证据候选集合",
            node_type="evidence_unit_input_set",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "evidence_count": evidence_count,
                "candidate_count": candidate_count,
                "relation_count": relation_count,
            },
            attributes={
                "source_stage": "evidence_graph_chunk_layer",
                "aggregation": "semantic",
            },
        ),
        RuntimeGraphNode(
            node_id=policy_node_id,
            label="证据包策略",
            node_type="evidence_pack_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"top_k": evidence_count, "selected_evidence_count": evidence_count},
            attributes={
                "rule_key": "evidence_pack.selection_and_rerank",
                "default_action": "select_ranked_evidence",
                "strategy": extraction.get("strategy") or "unknown",
                "llm_provider": llm_provider,
                "llm_model": llm_model,
            },
        ),
        RuntimeGraphNode(
            node_id=query_node_id,
            label="检索请求",
            node_type="retrieval_query",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "chunking_used": chunking_used,
                "candidate_count": candidate_count,
                "relation_count": relation_count,
            },
        ),
        RuntimeGraphNode(
            node_id=pack_node_id,
            label="证据包",
            node_type="evidence_pack",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={
                "selected_evidence_count": evidence_count,
                "top_k": evidence_count,
            },
            attributes={
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "strategy": extraction.get("strategy") or "unknown",
            },
        ),
        RuntimeGraphNode(
            node_id=rerank_node_id,
            label="重排结果",
            node_type="rerank_result",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"top_k": evidence_count},
        ),
        RuntimeGraphNode(
            node_id=target_node_id,
            label="知识生成输入",
            node_type="pack_target",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"candidate_count": candidate_count, "relation_count": relation_count},
        ),
    ]

    edges = [
        RuntimeGraphEdge(
            edge_id=f"{input_set_id}:feeds-policy",
            source=input_set_id,
            target=policy_node_id,
            relation="feeds_policy",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "rankable evidence units from evidence graph"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{policy_node_id}:governs-query",
            source=policy_node_id,
            target=query_node_id,
            relation="governs",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"basis": "top-k selection and rerank policy"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{query_node_id}:selected_into",
            source=query_node_id,
            target=pack_node_id,
            relation="selected_into",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{pack_node_id}:reranked_to",
            source=pack_node_id,
            target=rerank_node_id,
            relation="reranked_to",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{rerank_node_id}:supports",
            source=rerank_node_id,
            target=target_node_id,
            relation="supports",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    for index, row in enumerate(selected_evidence, start=1):
        evidence_node_id = f"{document_id}:evidence-pack:evidence:{index}"
        nodes.append(
            RuntimeGraphNode(
                node_id=evidence_node_id,
                label=f"证据片段 {index}",
                node_type="evidence_unit",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={
                    "document_id": row["document_id"],
                    "source_item_id": row["source_item_id"],
                    "source_item_name": row["source_item_name"],
                    "excerpt": row["excerpt"],
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{evidence_node_id}:selected",
                source=evidence_node_id,
                target=input_set_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={"rank": str(index)},
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="阶段视角 · 证据包",
        subtitle=document_title,
        status=status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:evidence-pack:start",
                kind="progress",
                level="info",
                message="系统开始从证据图谱/切块层检索有效证据，准备组成当前阶段证据包。",
                object_id=query_node_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:evidence-pack:select",
                kind="evidence",
                level="success" if evidence_count else "warning",
                message=(
                    f"已选入 {evidence_count} 条证据，当前采用 {llm_provider}/{llm_model} 参与后续知识生成。"
                    if evidence_count
                    else "当前没有可用证据进入证据包，后续知识生成将被降级或阻断。"
                ),
                object_id=pack_node_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:evidence-pack:rerank",
                kind="result",
                level="success" if evidence_count else "warning",
                message=f"重排完成，当前 top_k = {evidence_count}，候选数 {candidate_count}，关系数 {relation_count}。",
                object_id=rerank_node_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="pack-summary",
                title="证据包摘要",
                fields=[
                    RuntimeSummaryField(key="selected_evidence_count", label="selected_evidence_count", value=str(evidence_count), tone="success" if evidence_count else "warning"),
                    RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(candidate_count), tone="info"),
                    RuntimeSummaryField(key="relation_count", label="relation_count", value=str(relation_count), tone="info"),
                    RuntimeSummaryField(key="chunking_used", label="chunking_used", value="true" if chunking_used else "false", tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="pack-model",
                title="模型与策略",
                fields=[
                    RuntimeSummaryField(key="strategy", label="strategy", value=str(extraction.get("strategy") or "unknown")),
                    RuntimeSummaryField(key="llm_provider", label="llm_provider", value=llm_provider),
                    RuntimeSummaryField(key="llm_model", label="llm_model", value=llm_model),
                ],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="查看阶段图谱", target_kind="graph"),
            RuntimeAction(action_id="view-selected-evidence", label="查看已选证据", target_kind="evidence"),
        ],
    )

    node_observers = {
        input_set_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="证据候选集合",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:input-set",
                    kind="evidence",
                    level="success" if evidence_count else "warning",
                    message=f"Evidence pack receives {evidence_count} evidence units as the candidate input set before policy selection.",
                    object_id=input_set_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="input-set",
                    title="Input Set",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="evidence_unit_input_set"),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="success" if evidence_count else "warning"),
                        RuntimeSummaryField(key="source_stage", label="source_stage", value="evidence_graph_chunk_layer", tone="info"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-policy", label="查看选择策略", target_kind="node", target_id=policy_node_id),
            ],
        ),
        policy_node_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="证据包策略",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:policy",
                    kind="decision",
                    level="success" if evidence_count else "warning",
                    message="证据包策略会对候选证据排序，选择进入证据包的载荷，并把结果送入下游候选生成。",
                    object_id=policy_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-basis",
                    title="Policy / Action Basis",
                    fields=[
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="evidence_pack.selection_and_rerank", tone="info"),
                        RuntimeSummaryField(key="default_action", label="default_action", value="select_ranked_evidence", tone="info"),
                        RuntimeSummaryField(key="top_k", label="top_k", value=str(evidence_count), tone="success" if evidence_count else "warning"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-input-set", label="查看证据输入集合", target_kind="node", target_id=input_set_id),
                RuntimeAction(action_id="view-pack", label="查看证据包", target_kind="node", target_id=pack_node_id),
            ],
        ),
        pack_node_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="节点视角 · 证据包",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:node-pack",
                    kind="result",
                    level="success" if evidence_count else "warning",
                    message=f"证据包当前包含 {evidence_count} 条证据，用于驱动概念、关系和定义候选生成。",
                    object_id=pack_node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="identity",
                    title="对象身份",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="evidence_pack"),
                        RuntimeSummaryField(key="selected_evidence_count", label="selected_evidence_count", value=str(evidence_count), tone="success" if evidence_count else "warning"),
                        RuntimeSummaryField(key="top_k", label="top_k", value=str(evidence_count)),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="context",
                    title="上下文与来源",
                    fields=[
                        RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(candidate_count)),
                        RuntimeSummaryField(key="relation_count", label="relation_count", value=str(relation_count)),
                        RuntimeSummaryField(key="chunking_used", label="chunking_used", value="true" if chunking_used else "false"),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-upstream", label="查看上游节点", target_kind="graph"),
                RuntimeAction(action_id="view-evidence", label="查看完整证据", target_kind="evidence"),
            ],
        )
    }

    for index, row in enumerate(selected_evidence, start=1):
        node_id = f"{document_id}:evidence-pack:evidence:{index}"
        node_observers[node_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title=f"节点视角 · 证据片段 {index}",
            subtitle=row["source_item_name"],
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{node_id}:selected",
                    kind="evidence",
                    level="success",
                    message=f"该证据片段已进入证据包，排名 {index}。",
                    object_id=node_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="identity",
                    title="对象身份",
                    fields=[
                        RuntimeSummaryField(key="source_item_id", label="source_item_id", value=row["source_item_id"]),
                        RuntimeSummaryField(key="source_item_name", label="source_item_name", value=row["source_item_name"]),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="content",
                    title="证据内容",
                    fields=[
                        RuntimeSummaryField(key="excerpt", label="excerpt", value=row["excerpt"]),
                        RuntimeSummaryField(key="document_id", label="document_id", value=row["document_id"]),
                    ],
                ),
            ],
            actions=[
                RuntimeAction(action_id="view-pack", label="查看证据包", target_kind="node", target_id=pack_node_id),
            ],
        )

    edge_observers = {
        f"{input_set_id}:feeds-policy": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="feeds_policy",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:feeds-policy",
                    kind="decision",
                    level="success" if evidence_count else "warning",
                    message="证据候选集合会先进入证据包策略，再触发检索与重排动作。",
                    object_id=f"{input_set_id}:feeds-policy",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-edge",
                    title="Action Basis",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="feeds_policy"),
                        RuntimeSummaryField(key="basis", label="basis", value="rankable evidence units from evidence graph"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=input_set_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=policy_node_id),
            ],
        ),
        f"{policy_node_id}:governs-query": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="governs",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:governs-query",
                    kind="decision",
                    level="success" if evidence_count else "warning",
                    message="Selection and rerank policy determines the query payload that becomes the evidence pack.",
                    object_id=f"{policy_node_id}:governs-query",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-edge",
                    title="Policy Decision",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="governs"),
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="evidence_pack.selection_and_rerank"),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=policy_node_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=query_node_id),
            ],
        ),
        f"{query_node_id}:selected_into": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="边视角 · selected_into",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-pack:selected-edge",
                    kind="decision",
                    level="success" if evidence_count else "warning",
                    message="检索请求返回的有效证据被选入当前证据包。",
                    object_id=f"{query_node_id}:selected_into",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation",
                    title="关系摘要",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="selected_into"),
                        RuntimeSummaryField(key="selected_count", label="selected_count", value=str(evidence_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node", target_id=query_node_id),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node", target_id=pack_node_id),
            ],
        )
    }

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[input_set_id, policy_node_id, query_node_id, pack_node_id, rerank_node_id, target_node_id],
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _collect_evidence_rows(contribution: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for collection_name in ("entities", "events", "processes"):
        for item in contribution.get(collection_name, []):
            for evidence in item.get("evidence", []):
                excerpt = (evidence.get("excerpt") or "").strip()
                rows.append(
                    {
                        "document_id": evidence.get("document_id") or contribution["document"]["id"],
                        "source_item_id": item.get("id") or "unknown",
                        "source_item_name": item.get("name") or "unknown",
                        "excerpt": excerpt or "无摘录",
                    }
                )
    return rows
