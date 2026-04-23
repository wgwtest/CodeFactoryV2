from __future__ import annotations

from pathlib import Path

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


def build_parser_router_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    file_type: str | None,
    source_file_path: str | None,
    parser_name: str | None,
    parser_version: str | None,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["parser_router"]
    normalized_file_type = (file_type or _infer_file_type(source_file_path) or "unknown").lower()
    route_status = RuntimeStatus.COMPLETED if parser_name else RuntimeStatus.WARNING
    selected_parser = parser_name or _preferred_parser_for_type(normalized_file_type)
    fallback_parsers = [candidate for candidate in _candidate_parsers(normalized_file_type) if candidate != selected_parser][:2]

    source_file_id = f"{document_id}:parser-router:file"
    routing_task_id = f"{document_id}:parser-router:task"
    document_type_id = f"{document_id}:parser-router:type"
    selected_parser_id = f"{document_id}:parser-router:selected"
    routing_decision_id = f"{document_id}:parser-router:decision"
    warning_id = f"{document_id}:parser-router:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=source_file_id,
            label=document_title,
            node_type="source_file",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={
                "file_type": normalized_file_type,
                "source_file_path": source_file_path or "unknown",
            },
        ),
        RuntimeGraphNode(
            node_id=routing_task_id,
            label="Routing Task",
            node_type="routing_task",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"stage": "parser_router"},
        ),
        RuntimeGraphNode(
            node_id=document_type_id,
            label=f"Type: {normalized_file_type}",
            node_type="document_type",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if normalized_file_type != "unknown" else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"file_type": normalized_file_type},
        ),
        RuntimeGraphNode(
            node_id=selected_parser_id,
            label=selected_parser,
            node_type="selected_parser",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED if parser_name else RuntimeOrigin.UNAVAILABLE,
            is_primary=True,
            attributes={
                "parser_name": parser_name or selected_parser,
                "parser_version": parser_version or "unknown",
            },
        ),
        RuntimeGraphNode(
            node_id=routing_decision_id,
            label="Routing Decision",
            node_type="routing_decision",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "selected_parser": selected_parser,
                "candidate_count": len(fallback_parsers) + 1,
            },
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{source_file_id}:classified_as",
            source=source_file_id,
            target=document_type_id,
            relation="classified_as",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{source_file_id}:evaluated_by",
            source=source_file_id,
            target=routing_task_id,
            relation="evaluated_by",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{routing_task_id}:selects",
            source=routing_task_id,
            target=selected_parser_id,
            relation="selects",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{selected_parser_id}:decision",
            source=selected_parser_id,
            target=routing_decision_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=route_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    fallback_node_ids: list[str] = []
    for index, candidate in enumerate(fallback_parsers, start=1):
        candidate_id = f"{document_id}:parser-router:fallback:{index}"
        fallback_node_ids.append(candidate_id)
        nodes.append(
            RuntimeGraphNode(
                node_id=candidate_id,
                label=candidate,
                node_type="parser_candidate",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"candidate_rank": index + 1},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{routing_task_id}:candidate:{index}",
                source=routing_task_id,
                target=candidate_id,
                relation="considered",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    if parser_name is None:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Routing Warning",
                node_type="routing_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"message": "No concrete parser metadata was available; route is inferred from file type."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{routing_decision_id}:warned_by",
                source=routing_decision_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Parser Router",
        subtitle=document_title,
        status=route_status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:parser-router:file-type",
                kind="progress",
                level="info",
                message=f"File classified as {normalized_file_type}.",
                object_id=document_type_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:parser-router:selected",
                kind="decision",
                level="success" if parser_name else "warning",
                message=(
                    f"Selected parser {selected_parser}."
                    if parser_name
                    else f"Selected parser {selected_parser} by fallback routing because parser metadata is unavailable."
                ),
                object_id=selected_parser_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="routing-input",
                title="Routing Input",
                fields=[
                    RuntimeSummaryField(key="document_title", label="document_title", value=document_title),
                    RuntimeSummaryField(key="file_type", label="file_type", value=normalized_file_type),
                    RuntimeSummaryField(
                        key="candidate_count",
                        label="candidate_count",
                        value=str(len(fallback_parsers) + 1),
                    ),
                ],
            ),
            RuntimeSummarySection(
                section_id="routing-result",
                title="Routing Result",
                fields=[
                    RuntimeSummaryField(key="selected_parser", label="selected_parser", value=selected_parser),
                    RuntimeSummaryField(
                        key="parser_version",
                        label="parser_version",
                        value=parser_version or "unknown",
                        tone="success" if parser_version else "warning",
                    ),
                ],
            ),
        ],
        actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
    )

    node_observers: dict[str, RuntimeObserverPayload] = {
        selected_parser_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Selected Parser",
            subtitle=selected_parser,
            status=route_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-router:selected-node",
                    kind="decision",
                    level="success" if parser_name else "warning",
                    message=(
                        f"Parser {selected_parser} is the active route for this document."
                        if parser_name
                        else f"Parser {selected_parser} is currently inferred by file type fallback."
                    ),
                    object_id=selected_parser_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="parser-identity",
                    title="Parser Identity",
                    fields=[
                        RuntimeSummaryField(key="parser_name", label="parser_name", value=selected_parser),
                        RuntimeSummaryField(
                            key="parser_version",
                            label="parser_version",
                            value=parser_version or "unknown",
                            tone="success" if parser_version else "warning",
                        ),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-upstream", label="View Upstream Objects", target_kind="graph"),
                RuntimeAction(action_id="view-routing-rule", label="View Routing Evidence", target_kind="evidence"),
            ],
        ),
        routing_decision_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Routing Decision",
            subtitle=document_title,
            status=route_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-router:decision-node",
                    kind="decision",
                    level="success" if parser_name else "warning",
                    message=f"Routing decision finalized with parser {selected_parser}.",
                    object_id=routing_decision_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="decision-summary",
                    title="Decision Summary",
                    fields=[
                        RuntimeSummaryField(key="selected_parser", label="selected_parser", value=selected_parser),
                        RuntimeSummaryField(key="candidate_count", label="candidate_count", value=str(len(fallback_parsers) + 1)),
                        RuntimeSummaryField(
                            key="decision_mode",
                            label="decision_mode",
                            value="metadata" if parser_name else "fallback",
                            tone="success" if parser_name else "warning",
                        ),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-upstream", label="View Upstream Objects", target_kind="graph"),
                RuntimeAction(action_id="view-evidence", label="View Routing Evidence", target_kind="evidence"),
            ],
        ),
    }

    edge_observers: dict[str, RuntimeObserverPayload] = {
        f"{routing_task_id}:selects": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="Edge View · selects",
            subtitle=f"{selected_parser} selected for {document_title}",
            status=route_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-router:selects-edge",
                    kind="decision",
                    level="success" if parser_name else "warning",
                    message=f"Routing task selected parser {selected_parser}.",
                    object_id=f"{routing_task_id}:selects",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="edge-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="selects"),
                        RuntimeSummaryField(key="source", label="source", value="Routing Task"),
                        RuntimeSummaryField(key="target", label="target", value=selected_parser),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View Source Node", target_kind="node"),
                RuntimeAction(action_id="view-target-node", label="View Target Node", target_kind="node"),
            ],
        )
    }

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=route_status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[source_file_id, routing_task_id, selected_parser_id, routing_decision_id],
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _infer_file_type(source_file_path: str | None) -> str | None:
    if not source_file_path:
        return None
    suffix = Path(source_file_path).suffix.lstrip(".").lower()
    return suffix or None


def _preferred_parser_for_type(file_type: str) -> str:
    if file_type in {"pdf"}:
        return "docling.pdf"
    if file_type in {"docx"}:
        return "docling.docx"
    if file_type in {"doc"}:
        return "soffice.doc"
    if file_type in {"txt", "md"}:
        return "plain_text"
    return "unknown_parser"


def _candidate_parsers(file_type: str) -> list[str]:
    if file_type == "pdf":
        return ["docling.pdf", "marker.pdf", "grobid.pdf"]
    if file_type == "docx":
        return ["docling.docx", "msoffice.docx"]
    if file_type == "doc":
        return ["soffice.doc", "msoffice.doc"]
    if file_type in {"txt", "md"}:
        return ["plain_text", "markdown"]
    return ["unknown_parser"]
