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
from app.archive_knowledge.runtime_trace_utils import (
    build_runtime_events,
    build_runtime_sections,
    merge_runtime_events,
    merge_runtime_sections,
)
from app.parsing.models import ParsedDocument, ParsedSegment


@dataclass(slots=True)
class EvidenceRow:
    source_item_id: str
    source_item_name: str
    source_kind: str
    excerpt: str
    document_id: str
    matched_segment_index: int | None
    matched_segment: ParsedSegment | None


def build_evidence_constructor_snapshot(
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
    definition = STAGE_DEFINITION_MAP["evidence_constructor"]
    evidence_rows = _collect_evidence_rows_from_trace(document_id=document_id, runtime_trace=runtime_trace, parsed_document=parsed_document)
    if not evidence_rows:
        evidence_rows = _collect_evidence_rows(document_id=document_id, contribution=contribution, parsed_document=parsed_document)
    evidence_count = len(evidence_rows)
    anchor_count = len({_anchor_key(row) for row in evidence_rows if row.matched_segment is not None})
    span_count = evidence_count
    status = status_override or (RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING)
    trace_events = build_runtime_events(runtime_trace)
    trace_sections = build_runtime_sections(runtime_trace)

    task_id = f"{document_id}:evidence-constructor:task"
    unit_group_id = f"{document_id}:evidence-constructor:units"
    anchor_group_id = f"{document_id}:evidence-constructor:anchors"
    span_group_id = f"{document_id}:evidence-constructor:spans"
    paragraph_group_id = f"{document_id}:evidence-constructor:paragraphs"
    warning_id = f"{document_id}:evidence-constructor:warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=task_id,
            label="Evidence Constructor",
            node_type="evidence_constructor_task",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "evidence_count": evidence_count,
                "anchor_count": anchor_count,
                "span_count": span_count,
            },
            attributes={"document_title": document_title},
        ),
        RuntimeGraphNode(
            node_id=unit_group_id,
            label="Evidence Units",
            node_type="evidence_unit_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={"evidence_count": evidence_count},
            attributes={"evidence_count": evidence_count},
        ),
        RuntimeGraphNode(
            node_id=anchor_group_id,
            label="Evidence Anchors",
            node_type="evidence_anchor_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"anchor_count": anchor_count},
            attributes={"anchor_count": anchor_count},
        ),
        RuntimeGraphNode(
            node_id=span_group_id,
            label="Evidence Spans",
            node_type="evidence_span_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"span_count": span_count},
            attributes={"span_count": span_count},
        ),
        RuntimeGraphNode(
            node_id=paragraph_group_id,
            label="Source Paragraphs",
            node_type="source_paragraph_group",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            metrics={"matched_segment_count": len({row.matched_segment_index for row in evidence_rows if row.matched_segment_index is not None})},
            attributes={"matched_segment_count": len({row.matched_segment_index for row in evidence_rows if row.matched_segment_index is not None})},
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{task_id}:results_in",
            source=task_id,
            target=unit_group_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{unit_group_id}:anchors",
            source=unit_group_id,
            target=anchor_group_id,
            relation="anchored_at",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{unit_group_id}:spans",
            source=unit_group_id,
            target=span_group_id,
            relation="spans",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{paragraph_group_id}:supports",
            source=paragraph_group_id,
            target=unit_group_id,
            relation="evidence_from",
            stage_id=definition.stage_id,
            status=status,
            origin=RuntimeOrigin.DERIVED,
        ),
    ]

    paragraph_node_ids: dict[int, str] = {}
    anchor_node_ids: dict[str, str] = {}
    unit_node_ids: list[str] = []
    span_node_ids: list[str] = []

    for index, row in enumerate(evidence_rows, start=1):
        unit_id = f"{document_id}:evidence-unit:{index}"
        span_id = f"{document_id}:evidence-span:{index}"
        unit_node_ids.append(unit_id)
        span_node_ids.append(span_id)

        nodes.append(
            RuntimeGraphNode(
                node_id=unit_id,
                label=f"{row.source_kind.title()} Evidence {index}",
                node_type="evidence_unit",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                is_primary=index <= 2,
                attributes={
                    "source_item_id": row.source_item_id,
                    "source_item_name": row.source_item_name,
                    "source_kind": row.source_kind,
                    "excerpt": row.excerpt[:240],
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{unit_group_id}:unit:{index}",
                source=unit_group_id,
                target=unit_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.SOURCE,
                attributes={"rank": index},
            )
        )

        nodes.append(
            RuntimeGraphNode(
                node_id=span_id,
                label=f"Span {index}",
                node_type="evidence_span",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                attributes={
                    "excerpt": row.excerpt[:240],
                    "character_count": len(row.excerpt),
                },
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{span_group_id}:span:{index}",
                source=span_group_id,
                target=span_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{unit_id}:spans:{index}",
                source=unit_id,
                target=span_id,
                relation="spans",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                is_primary=index <= 2,
            )
        )

        if row.matched_segment is not None and row.matched_segment_index is not None:
            paragraph_id = paragraph_node_ids.get(row.matched_segment_index)
            if paragraph_id is None:
                paragraph_id = f"{document_id}:source-paragraph:{row.matched_segment_index + 1}"
                paragraph_node_ids[row.matched_segment_index] = paragraph_id
                nodes.append(
                    RuntimeGraphNode(
                        node_id=paragraph_id,
                        label=_paragraph_label(row.matched_segment_index + 1, row.matched_segment),
                        node_type="source_paragraph",
                        stage_id=definition.stage_id,
                        status=RuntimeStatus.COMPLETED,
                        origin=RuntimeOrigin.DERIVED,
                        attributes={
                            "heading": row.matched_segment.heading,
                            "anchor": row.matched_segment.anchor,
                            "content_excerpt": (row.matched_segment.content or "")[:240],
                        },
                    )
                )
                edges.append(
                    RuntimeGraphEdge(
                        edge_id=f"{paragraph_group_id}:paragraph:{row.matched_segment_index + 1}",
                        source=paragraph_group_id,
                        target=paragraph_id,
                        relation="contains",
                        stage_id=definition.stage_id,
                        status=RuntimeStatus.COMPLETED,
                        origin=RuntimeOrigin.DERIVED,
                    )
                )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{paragraph_id}:evidence:{index}",
                    source=paragraph_id,
                    target=unit_id,
                    relation="evidence_from",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                )
            )

            anchor_key = _anchor_key(row)
            anchor_id = anchor_node_ids.get(anchor_key)
            if anchor_id is None:
                anchor_id = f"{document_id}:evidence-anchor:{len(anchor_node_ids) + 1}"
                anchor_node_ids[anchor_key] = anchor_id
                nodes.append(
                    RuntimeGraphNode(
                        node_id=anchor_id,
                        label=_anchor_label(row.matched_segment.anchor),
                        node_type="evidence_anchor",
                        stage_id=definition.stage_id,
                        status=RuntimeStatus.COMPLETED,
                        origin=RuntimeOrigin.DERIVED,
                        attributes={"anchor": row.matched_segment.anchor},
                    )
                )
                edges.append(
                    RuntimeGraphEdge(
                        edge_id=f"{anchor_group_id}:anchor:{len(anchor_node_ids)}",
                        source=anchor_group_id,
                        target=anchor_id,
                        relation="contains",
                        stage_id=definition.stage_id,
                        status=RuntimeStatus.COMPLETED,
                        origin=RuntimeOrigin.DERIVED,
                    )
                )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{unit_id}:anchor:{index}",
                    source=unit_id,
                    target=anchor_id,
                    relation="anchored_at",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    is_primary=index <= 2,
                )
            )

    if not evidence_count:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Evidence Warning",
                node_type="evidence_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"message": "No evidence excerpts were available for evidence construction."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{task_id}:warned_by",
                source=task_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Evidence Constructor",
        subtitle=document_title,
        status=status,
        stream=merge_runtime_events([
            RuntimeEvent(
                event_id=f"{document_id}:evidence-constructor:start",
                kind="progress",
                level="info",
                message="Unified document paragraphs are being converted into traceable evidence units.",
                object_id=task_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:evidence-constructor:result",
                kind="result",
                level="success" if evidence_count else "warning",
                message=(
                    f"Constructed {evidence_count} evidence units, {anchor_count} anchors, and {span_count} spans."
                    if evidence_count
                    else "No evidence units could be constructed because the contribution did not expose evidence excerpts."
                ),
                object_id=unit_group_id,
                object_kind="node",
            ),
        ], trace_events),
        sections=merge_runtime_sections([
            RuntimeSummarySection(
                section_id="evidence-constructor-summary",
                title="Evidence Constructor Summary",
                fields=[
                    RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count), tone="success" if evidence_count else "warning"),
                    RuntimeSummaryField(key="anchor_count", label="anchor_count", value=str(anchor_count), tone="info"),
                    RuntimeSummaryField(key="span_count", label="span_count", value=str(span_count), tone="info"),
                ],
            ),
            RuntimeSummarySection(
                section_id="evidence-constructor-source",
                title="Constructor Source",
                fields=[
                    RuntimeSummaryField(key="parser_name", label="parser_name", value=parsed_document.parser_name or "unknown"),
                    RuntimeSummaryField(key="segment_count", label="segment_count", value=str(len(parsed_document.segments or []))),
                    RuntimeSummaryField(key="source_items", label="source_items", value=str(_source_item_count(contribution))),
                ],
            ),
        ], trace_sections),
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(action_id="view-evidence-units", label="View Evidence Units", target_kind="node", target_id=unit_group_id),
        ],
    )

    node_observers: dict[str, RuntimeObserverPayload] = {
        unit_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Evidence Units",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-constructor:units",
                    kind="result",
                    level="success" if evidence_count else "warning",
                    message=f"Evidence unit group currently contains {evidence_count} evidence objects.",
                    object_id=unit_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="units-summary",
                    title="Unit Summary",
                    fields=[
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count)),
                        RuntimeSummaryField(key="anchor_count", label="anchor_count", value=str(anchor_count)),
                        RuntimeSummaryField(key="span_count", label="span_count", value=str(span_count)),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        anchor_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Evidence Anchors",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-constructor:anchors",
                    kind="result",
                    level="success" if anchor_count else "warning",
                    message=f"Anchor group currently exposes {anchor_count} distinct traceability anchors.",
                    object_id=anchor_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="anchors-summary",
                    title="Anchor Summary",
                    fields=[
                        RuntimeSummaryField(key="anchor_count", label="anchor_count", value=str(anchor_count)),
                        RuntimeSummaryField(key="matched_segments", label="matched_segments", value=str(len(paragraph_node_ids))),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
    }

    for index, unit_id in enumerate(unit_node_ids, start=1):
        row = evidence_rows[index - 1]
        node_observers[unit_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title=f"Evidence Unit {index}",
            subtitle=row.source_item_name,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{unit_id}:constructed",
                    kind="evidence",
                    level="success",
                    message=f"Evidence unit {index} was constructed from {row.source_kind} evidence and attached to downstream traceability objects.",
                    object_id=unit_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id=f"{unit_id}:identity",
                    title="Evidence Identity",
                    fields=[
                        RuntimeSummaryField(key="source_item_id", label="source_item_id", value=row.source_item_id),
                        RuntimeSummaryField(key="source_item_name", label="source_item_name", value=row.source_item_name),
                        RuntimeSummaryField(key="source_kind", label="source_kind", value=row.source_kind),
                    ],
                ),
                RuntimeSummarySection(
                    section_id=f"{unit_id}:content",
                    title="Evidence Content",
                    fields=[
                        RuntimeSummaryField(key="excerpt", label="excerpt", value=row.excerpt[:240] or "not available"),
                        RuntimeSummaryField(
                            key="anchor",
                            label="anchor",
                            value=_anchor_label(row.matched_segment.anchor) if row.matched_segment is not None else "unanchored",
                        ),
                    ],
                ),
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    edge_observers = {
        f"{task_id}:results_in": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="results_in",
            subtitle=document_title,
            status=status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:evidence-constructor:results-in",
                    kind="result",
                    level="success" if evidence_count else "warning",
                    message="Evidence constructor task emitted the current evidence unit collection.",
                    object_id=f"{task_id}:results_in",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="results-in-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="results_in"),
                        RuntimeSummaryField(key="evidence_count", label="evidence_count", value=str(evidence_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source", label="View Source", target_kind="node", target_id=task_id),
                RuntimeAction(action_id="view-target", label="View Target", target_kind="node", target_id=unit_group_id),
            ],
        )
    }
    if unit_node_ids:
        first_anchor_edge = f"{unit_node_ids[0]}:anchor:1"
        edge_observers[first_anchor_edge] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="anchored_at",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{first_anchor_edge}:anchored",
                    kind="evidence",
                    level="info",
                    message="Evidence unit has been anchored to a concrete document location.",
                    object_id=first_anchor_edge,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="anchored-at-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="anchored_at"),
                        RuntimeSummaryField(key="source", label="source", value=unit_node_ids[0]),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    primary_node_ids = [
        task_id,
        unit_group_id,
        anchor_group_id,
        span_group_id,
        *unit_node_ids[:2],
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


def _collect_evidence_rows(
    *,
    document_id: str,
    contribution: dict[str, Any],
    parsed_document: ParsedDocument,
) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    segments = list(parsed_document.segments or [])
    for collection_name in ("entities", "events", "processes"):
        source_kind = collection_name[:-1]
        for item in contribution.get(collection_name, []):
            for evidence in item.get("evidence", []):
                excerpt = (evidence.get("excerpt") or "").strip()
                matched_index, matched_segment = _match_segment(excerpt, segments, len(rows))
                rows.append(
                    EvidenceRow(
                        source_item_id=item.get("id") or "unknown",
                        source_item_name=item.get("name") or "unknown",
                        source_kind=source_kind,
                        excerpt=excerpt or "not available",
                        document_id=evidence.get("document_id") or document_id,
                        matched_segment_index=matched_index,
                        matched_segment=matched_segment,
                    )
                )
    return rows


def _collect_evidence_rows_from_trace(
    *,
    document_id: str,
    runtime_trace: dict[str, Any] | None,
    parsed_document: ParsedDocument,
) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    segments = list(parsed_document.segments or [])
    for item in (runtime_trace or {}).get("evidence_units", []):
        if not isinstance(item, dict):
            continue
        excerpt = str(item.get("excerpt") or "").strip()
        matched_index, matched_segment = _match_segment(excerpt, segments, len(rows))
        rows.append(
            EvidenceRow(
                source_item_id=str(item.get("source_item_id") or f"{document_id}:trace-source"),
                source_item_name=str(item.get("source_item_name") or "trace evidence"),
                source_kind=str(item.get("source_kind") or "entity"),
                excerpt=excerpt or "not available",
                document_id=document_id,
                matched_segment_index=matched_index,
                matched_segment=matched_segment,
            )
        )
    return rows


def _match_segment(excerpt: str, segments: list[ParsedSegment], fallback_index: int) -> tuple[int | None, ParsedSegment | None]:
    if not segments:
        return None, None
    normalized_excerpt = " ".join(excerpt.split()).lower()
    for index, segment in enumerate(segments):
        content = " ".join((segment.content or "").split()).lower()
        if normalized_excerpt and (normalized_excerpt in content or content[:80] in normalized_excerpt):
            return index, segment
    index = min(fallback_index, len(segments) - 1)
    return index, segments[index]


def _paragraph_label(index: int, segment: ParsedSegment) -> str:
    heading = (segment.heading or "").strip()
    if heading:
        return f"P{index} · {heading}"
    content = " ".join((segment.content or "").split())
    if len(content) > 36:
        content = f"{content[:33]}..."
    return f"P{index} · {content or 'paragraph'}"


def _anchor_key(row: EvidenceRow) -> str:
    if row.matched_segment is None:
        return "unanchored"
    return _anchor_label(row.matched_segment.anchor)


def _anchor_label(anchor: dict[str, Any] | None) -> str:
    anchor = anchor or {}
    page = anchor.get("page")
    paragraph = anchor.get("paragraph")
    block = anchor.get("block")
    parts = []
    if page is not None:
        parts.append(f"p.{page}")
    if paragraph is not None:
        parts.append(f"para.{paragraph}")
    if block is not None:
        parts.append(f"block.{block}")
    return " / ".join(parts) or "unanchored"


def _source_item_count(contribution: dict[str, Any]) -> int:
    return sum(len(contribution.get(name, [])) for name in ("entities", "events", "processes"))
