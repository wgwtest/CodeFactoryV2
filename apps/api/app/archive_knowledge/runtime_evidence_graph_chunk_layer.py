from __future__ import annotations

from dataclasses import dataclass
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
from app.archive_knowledge.runtime_evidence_constructor import (
    EvidenceRow,
    _anchor_label,
    _collect_evidence_rows,
    _collect_evidence_rows_from_trace,
    _paragraph_label,
)
from app.archive_knowledge.runtime_trace_utils import (
    build_runtime_events,
    build_runtime_sections,
    merge_runtime_events,
    merge_runtime_sections,
)
from app.parsing.models import ParsedDocument, ParsedSegment


@dataclass(slots=True)
class ChunkRow:
    chunk_index: int
    segment_index: int | None
    segment: ParsedSegment | None
    evidence_rows: list[EvidenceRow]
    chunk_label: str
    boundary_adjusted: bool


def build_evidence_graph_chunk_layer_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    parsed_document: ParsedDocument,
    runtime_trace: dict[str, Any] | None = None,
    status_override: RuntimeStatus | None = None,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["evidence_graph_chunk_layer"]
    evidence_rows = _collect_evidence_rows_from_trace(
        document_id=document_id,
        runtime_trace=runtime_trace,
        parsed_document=parsed_document,
    )
    if not evidence_rows:
        evidence_rows = _collect_evidence_rows(
            document_id=document_id,
            contribution=contribution,
            parsed_document=parsed_document,
        )
    chunk_rows = _build_chunk_rows_from_trace(runtime_trace=runtime_trace, evidence_rows=evidence_rows, parsed_document=parsed_document)
    if not chunk_rows:
        chunk_rows = _build_chunk_rows(evidence_rows=evidence_rows, parsed_document=parsed_document)
    chunk_count = len(chunk_rows)
    evidence_count = len(evidence_rows)
    adjusted_chunks = [row for row in chunk_rows if row.boundary_adjusted]
    graph_link_count = max(chunk_count - 1, 0)
    status = status_override or (RuntimeStatus.COMPLETED if chunk_rows else RuntimeStatus.WARNING)
    trace_events = build_runtime_events(runtime_trace)
    trace_sections = build_runtime_sections(runtime_trace)

    planning_id = f"{document_id}:chunk-planning"
    evidence_unit_group_id = f"{document_id}:evidence-units"
    chunk_group_id = f"{document_id}:chunk-group"
    graph_layer_id = f"{document_id}:evidence-graph-layer"
    adjustment_group_id = f"{document_id}:boundary-adjustments"
    warning_id = f"{document_id}:chunk-warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=planning_id,
            label="Chunk Planning",
            node_type="chunk_planning_task",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "evidence_unit_count": evidence_count,
                "chunk_count": chunk_count,
                "graph_link_count": graph_link_count,
            },
            attributes={"document_title": document_title},
        ),
        RuntimeGraphNode(
            node_id=evidence_unit_group_id,
            label="Evidence Unit Set",
            node_type="evidence_unit_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={"evidence_unit_count": evidence_count},
            attributes={"evidence_unit_count": evidence_count},
        ),
        RuntimeGraphNode(
            node_id=chunk_group_id,
            label="Chunk Group",
            node_type="chunk_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"chunk_count": chunk_count},
            attributes={"chunk_count": chunk_count},
        ),
        RuntimeGraphNode(
            node_id=graph_layer_id,
            label="Evidence Graph Layer",
            node_type="evidence_graph_layer",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"graph_link_count": graph_link_count},
            attributes={"graph_link_count": graph_link_count},
        ),
        RuntimeGraphNode(
            node_id=adjustment_group_id,
            label="Boundary Adjustments",
            node_type="boundary_adjustment_group",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if adjusted_chunks else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
            metrics={"adjusted_chunk_count": len(adjusted_chunks)},
            attributes={"adjusted_chunk_count": len(adjusted_chunks)},
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{planning_id}:results_in",
            source=planning_id,
            target=chunk_group_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{evidence_unit_group_id}:grouped_into",
            source=evidence_unit_group_id,
            target=chunk_group_id,
            relation="grouped_into",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{chunk_group_id}:connects",
            source=chunk_group_id,
            target=graph_layer_id,
            relation="connects",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{chunk_group_id}:adjusted_by",
            source=chunk_group_id,
            target=adjustment_group_id,
            relation="adjusted_by",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if adjusted_chunks else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.DERIVED,
        ),
    ]

    evidence_node_ids: list[str] = []
    chunk_node_ids: list[str] = []
    adjustment_node_ids: list[str] = []

    for index, row in enumerate(evidence_rows, start=1):
        evidence_node_id = f"{document_id}:evidence-graph:evidence:{index}"
        evidence_node_ids.append(evidence_node_id)
        nodes.append(
            RuntimeGraphNode(
                node_id=evidence_node_id,
                label=f"Evidence Unit {index}",
                node_type="evidence_unit",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 2,
                attributes={
                    "source_item_id": row.source_item_id,
                    "source_item_name": row.source_item_name,
                    "source_kind": row.source_kind,
                    "anchor": _anchor_label(row.matched_segment.anchor) if row.matched_segment is not None else "unanchored",
                    "excerpt": row.excerpt[:240],
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{evidence_unit_group_id}:evidence:{index}",
                source=evidence_unit_group_id,
                target=evidence_node_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
            )
        )

    evidence_index_by_key = {
        (
            row.source_item_id,
            row.source_item_name,
            row.excerpt[:120],
        ): evidence_node_ids[index]
        for index, row in enumerate(evidence_rows[: len(evidence_node_ids)])
    }

    for chunk_row in chunk_rows:
        chunk_id = f"{document_id}:chunk:{chunk_row.chunk_index}"
        chunk_node_ids.append(chunk_id)
        nodes.append(
            RuntimeGraphNode(
                node_id=chunk_id,
                label=chunk_row.chunk_label,
                node_type="chunk",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                is_primary=chunk_row.chunk_index <= 3,
                metrics={"evidence_unit_count": len(chunk_row.evidence_rows)},
                attributes={
                    "chunk_index": chunk_row.chunk_index,
                    "segment_index": chunk_row.segment_index,
                    "anchor": _anchor_label(chunk_row.segment.anchor) if chunk_row.segment is not None else "unanchored",
                    "boundary_adjusted": chunk_row.boundary_adjusted,
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{chunk_group_id}:chunk:{chunk_row.chunk_index}",
                source=chunk_group_id,
                target=chunk_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{chunk_id}:graph-layer",
                source=chunk_id,
                target=graph_layer_id,
                relation="connects",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
            )
        )

        for evidence_row in chunk_row.evidence_rows:
            evidence_key = (evidence_row.source_item_id, evidence_row.source_item_name, evidence_row.excerpt[:120])
            evidence_node_id = evidence_index_by_key.get(evidence_key)
            if evidence_node_id:
                edges.append(
                    RuntimeGraphEdge(
                        edge_id=f"{evidence_node_id}:chunk:{chunk_row.chunk_index}",
                        source=evidence_node_id,
                        target=chunk_id,
                        relation="grouped_into",
                        stage_id=definition.stage_id,
                        status=RuntimeStatus.COMPLETED,
                        origin=RuntimeOrigin.DERIVED,
                        is_primary=chunk_row.chunk_index <= 2,
                    )
                )

        if chunk_row.boundary_adjusted:
            adjustment_id = f"{document_id}:boundary-adjustment:{chunk_row.chunk_index}"
            adjustment_node_ids.append(adjustment_id)
            nodes.append(
                RuntimeGraphNode(
                    node_id=adjustment_id,
                    label=f"Boundary Fix {chunk_row.chunk_index}",
                    node_type="boundary_adjustment",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    attributes={
                        "chunk_index": chunk_row.chunk_index,
                        "reason": _adjustment_reason(chunk_row),
                    },
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{adjustment_group_id}:adjustment:{chunk_row.chunk_index}",
                    source=adjustment_group_id,
                    target=adjustment_id,
                    relation="contains",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{chunk_id}:adjusted_by",
                    source=chunk_id,
                    target=adjustment_id,
                    relation="adjusted_by",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    is_primary=chunk_row.chunk_index <= 2,
                )
            )

    for index in range(len(chunk_node_ids) - 1):
        source_id = chunk_node_ids[index]
        target_id = chunk_node_ids[index + 1]
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{source_id}:linked_to:{target_id}",
                source=source_id,
                target=target_id,
                relation="linked_to",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index < 2,
                attributes={"link_order": index + 1},
            )
        )

    if not chunk_rows:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Chunk Warning",
                node_type="chunk_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"message": "No parsed segments or evidence rows were available to build chunk state."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{planning_id}:warned_by",
                source=planning_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Evidence Graph / Chunk Layer",
        subtitle=document_title,
        status=status,
        stream=merge_runtime_events([
            RuntimeEvent(
                event_id=f"{document_id}:chunk-layer:start",
                kind="progress",
                level="info",
                message="Evidence units are being aligned to parser segments and grouped into chunk windows.",
                object_id=planning_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:chunk-layer:grouped",
                kind="result",
                level="success" if chunk_count else "warning",
                message=(
                    f"Built {chunk_count} chunks from {evidence_count} evidence units with {graph_link_count} graph links."
                    if chunk_count
                    else "Chunk layer could not be materialized because neither segments nor evidence units were available."
                ),
                object_id=chunk_group_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:chunk-layer:adjustments",
                kind="decision",
                level="info" if adjusted_chunks else "neutral",
                message=f"Boundary adjustment count: {len(adjusted_chunks)}.",
                object_id=adjustment_group_id,
                object_kind="node",
            ),
        ], trace_events),
        sections=merge_runtime_sections([
            RuntimeSummarySection(
                section_id="chunk-layer-summary",
                title="Chunk Layer Summary",
                fields=[
                    RuntimeSummaryField(key="evidence_unit_count", label="evidence_unit_count", value=str(evidence_count), tone="info"),
                    RuntimeSummaryField(key="chunk_count", label="chunk_count", value=str(chunk_count), tone="success" if chunk_count else "warning"),
                    RuntimeSummaryField(key="graph_link_count", label="graph_link_count", value=str(graph_link_count), tone="info"),
                    RuntimeSummaryField(key="adjusted_chunk_count", label="adjusted_chunk_count", value=str(len(adjusted_chunks)), tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="chunk-layer-strategy",
                title="Chunking Strategy",
                fields=[
                    RuntimeSummaryField(key="strategy", label="strategy", value="segment_evidence_alignment"),
                    RuntimeSummaryField(key="parser_name", label="parser_name", value=parsed_document.parser_name or "unknown"),
                    RuntimeSummaryField(key="segment_count", label="segment_count", value=str(len(parsed_document.segments or []))),
                ],
            ),
        ], trace_sections),
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(action_id="view-chunk-group", label="View Chunk Group", target_kind="node", target_id=chunk_group_id),
        ],
    )

    node_observers: dict[str, RuntimeObserverPayload] = {
        chunk_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Chunk Group",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:chunk-layer:chunk-group",
                    kind="result",
                    level="success" if chunk_count else "warning",
                    message=f"Chunk group currently contains {chunk_count} chunk windows built from document evidence.",
                    object_id=chunk_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="chunk-group-summary",
                    title="Chunk Group Summary",
                    fields=[
                        RuntimeSummaryField(key="chunk_count", label="chunk_count", value=str(chunk_count)),
                        RuntimeSummaryField(key="evidence_unit_count", label="evidence_unit_count", value=str(evidence_count)),
                        RuntimeSummaryField(key="adjusted_chunk_count", label="adjusted_chunk_count", value=str(len(adjusted_chunks))),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        graph_layer_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Evidence Graph Layer",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:chunk-layer:graph-layer",
                    kind="result",
                    level="success" if graph_link_count else "warning",
                    message=f"Evidence graph layer currently exposes {graph_link_count} chunk-to-chunk links.",
                    object_id=graph_layer_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="graph-layer-summary",
                    title="Graph Layer Summary",
                    fields=[
                        RuntimeSummaryField(key="graph_link_count", label="graph_link_count", value=str(graph_link_count)),
                        RuntimeSummaryField(key="chunk_count", label="chunk_count", value=str(chunk_count)),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
    }

    for chunk_row in chunk_rows:
        chunk_id = f"{document_id}:chunk:{chunk_row.chunk_index}"
        node_observers[chunk_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title=f"Chunk {chunk_row.chunk_index}",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{chunk_id}:created",
                    kind="result",
                    level="success",
                    message=f"Chunk {chunk_row.chunk_index} was assembled from {len(chunk_row.evidence_rows)} evidence units.",
                    object_id=chunk_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id=f"{chunk_id}:identity",
                    title="Chunk Identity",
                    fields=[
                        RuntimeSummaryField(key="chunk_index", label="chunk_index", value=str(chunk_row.chunk_index)),
                        RuntimeSummaryField(key="segment_index", label="segment_index", value=str(chunk_row.segment_index or "n/a")),
                        RuntimeSummaryField(key="evidence_unit_count", label="evidence_unit_count", value=str(len(chunk_row.evidence_rows))),
                    ],
                ),
                RuntimeSummarySection(
                    section_id=f"{chunk_id}:context",
                    title="Chunk Context",
                    fields=[
                        RuntimeSummaryField(
                            key="anchor",
                            label="anchor",
                            value=_anchor_label(chunk_row.segment.anchor) if chunk_row.segment is not None else "unanchored",
                        ),
                        RuntimeSummaryField(
                            key="boundary_adjusted",
                            label="boundary_adjusted",
                            value="true" if chunk_row.boundary_adjusted else "false",
                        ),
                    ],
                ),
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    edge_observers: dict[str, RuntimeObserverPayload] = {
        f"{planning_id}:results_in": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="results_in",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{planning_id}:results-in",
                    kind="result",
                    level="success" if chunk_count else "warning",
                    message="Chunk planning emitted the current chunk group object.",
                    object_id=f"{planning_id}:results_in",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="results-in-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="results_in"),
                        RuntimeSummaryField(key="chunk_count", label="chunk_count", value=str(chunk_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source", label="View Source", target_kind="node", target_id=planning_id),
                RuntimeAction(action_id="view-target", label="View Target", target_kind="node", target_id=chunk_group_id),
            ],
        ),
        f"{chunk_group_id}:connects": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="connects",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{chunk_group_id}:connects",
                    kind="result",
                    level="success" if graph_link_count else "warning",
                    message="Chunk group is connected to the evidence graph layer for downstream pack assembly.",
                    object_id=f"{chunk_group_id}:connects",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="connects-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="connects"),
                        RuntimeSummaryField(key="graph_link_count", label="graph_link_count", value=str(graph_link_count)),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
    }

    if chunk_node_ids:
        first_chunk_edge = f"{chunk_node_ids[0]}:graph-layer"
        edge_observers[first_chunk_edge] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="connects",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{first_chunk_edge}:connects",
                    kind="progress",
                    level="info",
                    message="Chunk now participates in the active evidence graph layer.",
                    object_id=first_chunk_edge,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="chunk-connects-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="connects"),
                        RuntimeSummaryField(key="source", label="source", value=chunk_node_ids[0]),
                        RuntimeSummaryField(key="target", label="target", value=graph_layer_id),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    if len(chunk_node_ids) >= 2:
        linked_edge_id = f"{chunk_node_ids[0]}:linked_to:{chunk_node_ids[1]}"
        edge_observers[linked_edge_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="linked_to",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{linked_edge_id}:linked",
                    kind="decision",
                    level="info",
                    message="Adjacent chunk windows were linked to preserve evidence continuity.",
                    object_id=linked_edge_id,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="linked-to-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="linked_to"),
                        RuntimeSummaryField(key="source", label="source", value=chunk_node_ids[0]),
                        RuntimeSummaryField(key="target", label="target", value=chunk_node_ids[1]),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    primary_node_ids = [
        planning_id,
        chunk_group_id,
        graph_layer_id,
        *chunk_node_ids[:3],
        *adjustment_node_ids[:1],
    ]
    primary_edge_ids = [edge.edge_id for edge in edges if edge.is_primary]

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=primary_node_ids,
            primary_edge_ids=primary_edge_ids,
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )


def _build_chunk_rows(*, evidence_rows: list[EvidenceRow], parsed_document: ParsedDocument) -> list[ChunkRow]:
    segments = list(parsed_document.segments or [])
    grouped: dict[int | None, list[EvidenceRow]] = {}
    for row in evidence_rows:
        grouped.setdefault(row.matched_segment_index, []).append(row)

    chunk_rows: list[ChunkRow] = []
    for chunk_index, segment_index in enumerate(sorted(index for index in grouped if index is not None), start=1):
        segment = segments[segment_index] if segment_index is not None and segment_index < len(segments) else None
        rows = grouped.get(segment_index, [])
        chunk_rows.append(
            ChunkRow(
                chunk_index=chunk_index,
                segment_index=segment_index,
                segment=segment,
                evidence_rows=rows,
                chunk_label=_chunk_label(chunk_index, segment),
                boundary_adjusted=_needs_boundary_adjustment(rows, segment),
            )
        )

    if not chunk_rows and segments:
        for chunk_index, segment in enumerate(segments, start=1):
            chunk_rows.append(
                ChunkRow(
                    chunk_index=chunk_index,
                    segment_index=chunk_index - 1,
                    segment=segment,
                    evidence_rows=[],
                    chunk_label=_chunk_label(chunk_index, segment),
                    boundary_adjusted=_needs_boundary_adjustment([], segment),
                )
            )

    return chunk_rows


def _build_chunk_rows_from_trace(
    *,
    runtime_trace: dict[str, Any] | None,
    evidence_rows: list[EvidenceRow],
    parsed_document: ParsedDocument,
) -> list[ChunkRow]:
    trace_chunks = (runtime_trace or {}).get("chunks", [])
    if not isinstance(trace_chunks, list) or not trace_chunks:
        return []

    segments = list(parsed_document.segments or [])
    rows_by_chunk_id: dict[str, list[EvidenceRow]] = {}
    for row in evidence_rows:
        if row.matched_segment is None:
            continue
        row_chunk_key = row.matched_segment.anchor.get("chunk_id") if isinstance(row.matched_segment.anchor, dict) else None
        if row_chunk_key:
            rows_by_chunk_id.setdefault(str(row_chunk_key), []).append(row)

    chunk_rows: list[ChunkRow] = []
    for index, trace_chunk in enumerate(trace_chunks, start=1):
        if not isinstance(trace_chunk, dict):
            continue
        segment_index = index - 1
        segment = segments[segment_index] if segment_index < len(segments) else None
        chunk_id = str(trace_chunk.get("chunk_id") or f"trace-chunk-{index}")
        chunk_rows.append(
            ChunkRow(
                chunk_index=int(trace_chunk.get("chunk_position") or index),
                segment_index=segment_index if segment is not None else None,
                segment=segment,
                evidence_rows=rows_by_chunk_id.get(chunk_id, []),
                chunk_label=str(trace_chunk.get("chunk_label") or trace_chunk.get("chunk_heading") or f"Chunk {index}"),
                boundary_adjusted=bool(trace_chunk.get("boundary_adjusted")),
            )
        )
    return chunk_rows


def _chunk_label(chunk_index: int, segment: ParsedSegment | None) -> str:
    if segment is None:
        return f"Chunk {chunk_index}"
    return _paragraph_label(chunk_index, segment).replace("P", "Chunk ", 1)


def _needs_boundary_adjustment(rows: list[EvidenceRow], segment: ParsedSegment | None) -> bool:
    if len(rows) > 1:
        return True
    content = (segment.content or "") if segment is not None else ""
    return len(content) > 280


def _adjustment_reason(chunk_row: ChunkRow) -> str:
    if len(chunk_row.evidence_rows) > 1:
        return "multiple_evidence_units"
    return "long_segment_window"
