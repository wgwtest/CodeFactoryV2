from __future__ import annotations

from collections import Counter

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
from app.parsing.models import ParsedDocument


def build_parser_execution_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    file_type: str | None,
    parsed_document: ParsedDocument,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["parser_execution"]
    parser_name = parsed_document.parser_name or "unknown"
    parser_version = parsed_document.parser_version or "unknown"
    segments = list(parsed_document.segments or [])
    segment_count = len(segments)
    page_count = _estimate_page_count(segments)
    block_type_counter = Counter(segment.block_type or "section" for segment in segments)
    stage_status = RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING

    parser_task_id = f"{document_id}:parser-execution:task"
    parser_engine_id = f"{document_id}:parser-execution:engine"
    parsed_page_group_id = f"{document_id}:parser-execution:pages"
    parsed_block_group_id = f"{document_id}:parser-execution:blocks"
    structure_group_id = f"{document_id}:parser-execution:structure"
    warning_id = f"{document_id}:parser-execution:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=parser_task_id,
            label="Parser Task",
            node_type="parser_task",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={"page_count": page_count, "segment_count": segment_count},
            attributes={
                "document_title": document_title,
                "file_type": file_type or "unknown",
            },
        ),
        RuntimeGraphNode(
            node_id=parser_engine_id,
            label=f"{parser_name}@{parser_version}",
            node_type="parser_engine",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if parser_name != "unknown" else RuntimeStatus.WARNING,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={
                "parser_name": parser_name,
                "parser_version": parser_version,
            },
        ),
        RuntimeGraphNode(
            node_id=parsed_page_group_id,
            label="Parsed Pages",
            node_type="parsed_page_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"page_count": page_count},
            attributes={"page_count": page_count},
        ),
        RuntimeGraphNode(
            node_id=parsed_block_group_id,
            label="Parsed Blocks",
            node_type="parsed_block_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"segment_count": segment_count},
            attributes={"segment_count": segment_count},
        ),
        RuntimeGraphNode(
            node_id=structure_group_id,
            label="Structure Summary",
            node_type="parsed_structure_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            metrics=dict(block_type_counter),
            attributes=dict(block_type_counter),
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{parser_task_id}:executed_by",
            source=parser_task_id,
            target=parser_engine_id,
            relation="executed_by",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{parser_task_id}:parsed_to",
            source=parser_task_id,
            target=parsed_page_group_id,
            relation="parsed_to",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{parsed_page_group_id}:extracts",
            source=parsed_page_group_id,
            target=parsed_block_group_id,
            relation="extracts",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{parsed_block_group_id}:contains",
            source=parsed_block_group_id,
            target=structure_group_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
        ),
    ]

    primary_segment_ids: list[str] = []
    for index, segment in enumerate(segments, start=1):
        segment_id = f"{document_id}:parser-execution:segment:{index}"
        primary_segment_ids.append(segment_id)
        segment_label = _build_segment_label(index, segment.heading, segment.content)
        nodes.append(
            RuntimeGraphNode(
                node_id=segment_id,
                label=segment_label,
                node_type="parsed_segment",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={
                    "heading": segment.heading,
                    "block_type": segment.block_type,
                    "anchor": segment.anchor,
                    "content_excerpt": segment.content[:240],
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{structure_group_id}:segment:{index}",
                source=structure_group_id,
                target=segment_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={"segment_order": index},
            )
        )

    if not segment_count:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Parsing Warning",
                node_type="parsing_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"message": "Parser finished without producing structured segments."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{parser_task_id}:warned_by",
                source=parser_task_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Parser Execution",
        subtitle=document_title,
        status=stage_status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:parser-execution:start",
                kind="progress",
                level="info",
                message=f"Parser task started with {parser_name}/{parser_version}.",
                object_id=parser_task_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:parser-execution:parsed",
                kind="result",
                level="success" if segment_count else "warning",
                message=(
                    f"Parser produced {page_count} page objects and {segment_count} structured segments."
                    if segment_count
                    else "Parser finished, but no structured segments were produced."
                ),
                object_id=parsed_block_group_id,
                object_kind="node",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="execution-summary",
                title="Execution Summary",
                fields=[
                    RuntimeSummaryField(key="parser_name", label="parser_name", value=parser_name),
                    RuntimeSummaryField(key="parser_version", label="parser_version", value=parser_version),
                    RuntimeSummaryField(
                        key="page_count",
                        label="page_count",
                        value=str(page_count),
                        tone="success" if page_count else "warning",
                    ),
                    RuntimeSummaryField(
                        key="segment_count",
                        label="segment_count",
                        value=str(segment_count),
                        tone="success" if segment_count else "warning",
                    ),
                ],
            ),
            RuntimeSummarySection(
                section_id="structure-distribution",
                title="Structure Distribution",
                fields=[
                    RuntimeSummaryField(key=block_type, label=block_type, value=str(count), tone="info")
                    for block_type, count in sorted(block_type_counter.items())
                ]
                or [RuntimeSummaryField(key="none", label="none", value="0", tone="warning")],
            ),
        ],
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(
                action_id="view-parser-engine",
                label="View Parser Engine",
                target_kind="node",
                target_id=parser_engine_id,
            ),
        ],
    )

    node_observers = {
        parser_engine_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Parser Engine",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED if parser_name != "unknown" else RuntimeStatus.WARNING,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-execution:engine",
                    kind="info",
                    level="info",
                    message=f"Document parsed by {parser_name}/{parser_version}.",
                    object_id=parser_engine_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="engine-info",
                    title="Engine Information",
                    fields=[
                        RuntimeSummaryField(key="parser_name", label="parser_name", value=parser_name),
                        RuntimeSummaryField(key="parser_version", label="parser_version", value=parser_version),
                        RuntimeSummaryField(key="file_type", label="file_type", value=file_type or "unknown"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        parsed_block_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Parsed Blocks",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-execution:block-group",
                    kind="result",
                    level="success" if segment_count else "warning",
                    message=f"Current parsed block group contains {segment_count} structured segments.",
                    object_id=parsed_block_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="block-summary",
                    title="Block Summary",
                    fields=[
                        RuntimeSummaryField(key="segment_count", label="segment_count", value=str(segment_count)),
                        RuntimeSummaryField(key="page_count", label="page_count", value=str(page_count)),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="sample-segments",
                    title="Sample Segments",
                    fields=[
                        RuntimeSummaryField(
                            key=f"segment_{index}",
                            label=f"segment_{index}",
                            value=_build_segment_label(index, segment.heading, segment.content, max_length=72),
                            tone="info",
                        )
                        for index, segment in enumerate(segments[:3], start=1)
                    ]
                    or [RuntimeSummaryField(key="none", label="none", value="not available", tone="warning")],
                ),
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
    }

    edge_observers = {
        f"{parser_task_id}:parsed_to": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="parsed_to",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:parser-execution:parsed-to",
                    kind="result",
                    level="success" if segment_count else "warning",
                    message="Parser task completed and produced parsed page objects.",
                    object_id=f"{parser_task_id}:parsed_to",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="relation-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="parsed_to"),
                        RuntimeSummaryField(key="page_count", label="page_count", value=str(page_count)),
                        RuntimeSummaryField(key="segment_count", label="segment_count", value=str(segment_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source", label="View Source", target_kind="node", target_id=parser_task_id),
                RuntimeAction(
                    action_id="view-target",
                    label="View Target",
                    target_kind="node",
                    target_id=parsed_page_group_id,
                ),
            ],
        )
    }

    primary_node_ids = [
        parser_task_id,
        parser_engine_id,
        parsed_page_group_id,
        parsed_block_group_id,
        *primary_segment_ids[:2],
    ]
    primary_edge_ids = [edge.edge_id for edge in edges if edge.is_primary]

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=stage_status,
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


def parsed_document_from_source_document(
    *,
    parser_name: str | None,
    segment_count: int,
    segments: list | None,
    source_file_path: str | None,
    source_digest: str | None,
) -> ParsedDocument:
    parsed_segments = list(segments or [])
    metadata: dict[str, str | int | float | bool | None] = {}
    if source_file_path:
        metadata["source_file_path"] = source_file_path
    if source_digest:
        metadata["source_digest"] = source_digest
    metadata["declared_segment_count"] = segment_count
    return ParsedDocument(
        parser_name=parser_name or "unknown",
        parser_version="derived",
        segments=parsed_segments,
        metadata=metadata,
    )


def _build_segment_label(index: int, heading: str | None, content: str | None, *, max_length: int = 40) -> str:
    value = (heading or content or f"segment {index}").strip()
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


def _estimate_page_count(segments: list) -> int:
    page_values: list[int] = []
    for segment in segments:
        anchor = getattr(segment, "anchor", {}) or {}
        page = anchor.get("page")
        if isinstance(page, int):
            page_values.append(page)
    if page_values:
        return max(page_values)
    if segments:
        return 1
    return 0
