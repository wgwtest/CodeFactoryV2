from __future__ import annotations

from collections import OrderedDict

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


def build_unified_document_object_snapshot(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    file_type: str | None,
    parsed_document: ParsedDocument,
    runtime_trace: dict | None = None,
    status_override: RuntimeStatus | None = None,
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["unified_document_object"]
    segments = list(parsed_document.segments or [])
    segment_count = len(segments)
    section_groups = _group_segments_by_section(segments)
    section_labels = list(section_groups.keys())
    stage_status = status_override or (RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING)
    trace_events = build_runtime_events(runtime_trace)
    trace_sections = build_runtime_sections(runtime_trace)

    unified_document_id = f"{document_id}:unified-document"
    parsed_segment_group_id = f"{document_id}:parsed-segments"
    normalization_decision_id = f"{document_id}:normalization-decision"
    normalization_policy_id = f"{document_id}:normalization-policy"
    section_group_id = f"{document_id}:unified-sections"
    paragraph_group_id = f"{document_id}:unified-paragraphs"
    warning_id = f"{document_id}:unified-warning"

    nodes: list[RuntimeGraphNode] = [
        RuntimeGraphNode(
            node_id=parsed_segment_group_id,
            label="Parsed Segment Input",
            node_type="parsed_segment_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            metrics={"segment_count": segment_count},
            attributes={
                "input_object": "parser_segments",
                "segment_count": segment_count,
                "parser_name": parsed_document.parser_name,
                "coverage": "full_parser_output" if segment_count else "empty_parser_output",
            },
        ),
        RuntimeGraphNode(
            node_id=normalization_policy_id,
            label="Normalization Policy",
            node_type="normalization_policy",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            metrics={
                "input_count": (runtime_trace or {}).get("input_count", segment_count),
                "output_count": (runtime_trace or {}).get("output_count", segment_count),
            },
            attributes={
                "decision_summary": (runtime_trace or {}).get(
                    "decision_summary",
                    "normalize parser segments into stable document objects",
                ),
                "ai_summary": (runtime_trace or {}).get(
                    "ai_summary",
                    "field alignment and heading normalization",
                ),
                "rule_key": "unified-document-normalization",
            },
        ),
        RuntimeGraphNode(
            node_id=unified_document_id,
            label="Unified Document",
            node_type="unified_document",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={
                "section_count": len(section_labels),
                "paragraph_count": segment_count,
            },
            attributes={
                "document_title": document_title,
                "file_type": file_type or "unknown",
                "coverage": "all_segments_included" if segment_count else "empty_document",
            },
        ),
        RuntimeGraphNode(
            node_id=normalization_decision_id,
            label="Normalization Decision",
            node_type="normalization_decision",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={
                "parser_name": parsed_document.parser_name,
                "parser_version": parsed_document.parser_version,
                "segment_count": segment_count,
            },
        ),
        RuntimeGraphNode(
            node_id=section_group_id,
            label="Unified Sections",
            node_type="unified_section_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"section_count": len(section_labels)},
            attributes={
                "section_count": len(section_labels),
                "sample_sections": ", ".join(section_labels[:5]) if section_labels else "not available",
            },
        ),
        RuntimeGraphNode(
            node_id=paragraph_group_id,
            label="Unified Paragraphs",
            node_type="unified_paragraph_group",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            metrics={"paragraph_count": segment_count},
            attributes={
                "paragraph_count": segment_count,
                "coverage": "full_document" if segment_count else "empty_document",
            },
        ),
    ]

    edges: list[RuntimeGraphEdge] = [
        RuntimeGraphEdge(
            edge_id=f"{parsed_segment_group_id}:normalized_by",
            source=parsed_segment_group_id,
            target=normalization_decision_id,
            relation="normalized_by",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={
                "rule_key": "unified-document-normalization",
                "reason": "all parser segments enter normalization before downstream evidence stages",
            },
        ),
        RuntimeGraphEdge(
            edge_id=f"{normalization_policy_id}:governs",
            source=normalization_policy_id,
            target=normalization_decision_id,
            relation="governs",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            attributes={"rule_key": "unified-document-normalization"},
        ),
        RuntimeGraphEdge(
            edge_id=f"{normalization_decision_id}:normalized_to",
            source=normalization_decision_id,
            target=unified_document_id,
            relation="normalized_to",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{unified_document_id}:sections",
            source=unified_document_id,
            target=section_group_id,
            relation="contains",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{unified_document_id}:paragraphs",
            source=unified_document_id,
            target=paragraph_group_id,
            relation="summarizes",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    section_node_ids: list[str] = []
    paragraph_node_ids: list[str] = []
    section_node_ids_by_label: dict[str, str] = {}
    paragraph_attributes_by_id: dict[str, dict[str, object]] = {}

    for section_index, (section_label, section_segments) in enumerate(section_groups.items(), start=1):
        section_id = f"{document_id}:unified-section:{section_index}"
        section_node_ids.append(section_id)
        section_node_ids_by_label[section_label] = section_id
        nodes.append(
            RuntimeGraphNode(
                node_id=section_id,
                label=section_label,
                node_type="unified_section",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                attributes={
                    "section_label": section_label,
                    "section_order": section_index,
                    "paragraph_count": len(section_segments),
                },
                metrics={"paragraph_count": len(section_segments)},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{section_group_id}:section:{section_index}",
                source=section_group_id,
                target=section_id,
                relation="contains",
                stage_id=definition.stage_id,
                status=RuntimeStatus.COMPLETED,
                origin=RuntimeOrigin.DERIVED,
                attributes={"section_order": section_index},
            )
        )

        for paragraph_index, segment in section_segments:
            paragraph_id = f"{document_id}:unified-paragraph:{paragraph_index}"
            paragraph_node_ids.append(paragraph_id)
            paragraph_attributes = {
                "section_label": section_label,
                "paragraph_order": paragraph_index,
                "block_type": segment.block_type or "section",
                "anchor": segment.anchor,
                "content_excerpt": (segment.content or "")[:240],
            }
            paragraph_attributes_by_id[paragraph_id] = paragraph_attributes
            nodes.append(
                RuntimeGraphNode(
                    node_id=paragraph_id,
                    label=_paragraph_label(paragraph_index, segment),
                    node_type="unified_paragraph",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    attributes=paragraph_attributes,
                )
            )
            edges.append(
                RuntimeGraphEdge(
                    edge_id=f"{section_id}:paragraph:{paragraph_index}",
                    source=section_id,
                    target=paragraph_id,
                    relation="contains",
                    stage_id=definition.stage_id,
                    status=RuntimeStatus.COMPLETED,
                    origin=RuntimeOrigin.DERIVED,
                    attributes={"paragraph_order": paragraph_index},
                )
            )

    if not segment_count:
        nodes.append(
            RuntimeGraphNode(
                node_id=warning_id,
                label="Normalization Warning",
                node_type="normalization_warning",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
                attributes={"message": "No parser segments were available for unified document construction."},
            )
        )
        edges.append(
            RuntimeGraphEdge(
                edge_id=f"{normalization_decision_id}:warned_by",
                source=normalization_decision_id,
                target=warning_id,
                relation="warned_by",
                stage_id=definition.stage_id,
                status=RuntimeStatus.WARNING,
                origin=RuntimeOrigin.DERIVED,
            )
        )

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Unified Document Object",
        subtitle=document_title,
        status=stage_status,
        stream=merge_runtime_events([
            RuntimeEvent(
                event_id=f"{document_id}:unified:start",
                kind="progress",
                level="info",
                message="Parser output is being normalized into a stable document object.",
                object_id=normalization_decision_id,
                object_kind="node",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:unified:result",
                kind="result",
                level="success" if segment_count else "warning",
                message=(
                    f"Unified document now covers all {segment_count} parsed segments across {len(section_labels)} sections."
                    if segment_count
                    else "Unified document object could not be materialized because no parser segments were available."
                ),
                object_id=unified_document_id,
                object_kind="node",
            ),
        ], trace_events),
        sections=merge_runtime_sections([
            RuntimeSummarySection(
                section_id="unified-summary",
                title="Unified Summary",
                fields=[
                    RuntimeSummaryField(key="document_title", label="document_title", value=document_title),
                    RuntimeSummaryField(key="section_count", label="section_count", value=str(len(section_labels))),
                    RuntimeSummaryField(
                        key="paragraph_count",
                        label="paragraph_count",
                        value=str(segment_count),
                        tone="success" if segment_count else "warning",
                    ),
                    RuntimeSummaryField(
                        key="coverage",
                        label="coverage",
                        value="all parsed segments are represented" if segment_count else "no parsed segments available",
                    ),
                ],
            ),
            RuntimeSummarySection(
                section_id="normalization-source",
                title="Normalization Source",
                fields=[
                    RuntimeSummaryField(key="parser_name", label="parser_name", value=parsed_document.parser_name or "unknown"),
                    RuntimeSummaryField(
                        key="parser_version",
                        label="parser_version",
                        value=parsed_document.parser_version or "unknown",
                    ),
                    RuntimeSummaryField(key="file_type", label="file_type", value=file_type or "unknown"),
                ],
            ),
        ], trace_sections),
        actions=[
            RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph"),
            RuntimeAction(
                action_id="view-normalization",
                label="View Normalization Decision",
                target_kind="node",
                target_id=normalization_decision_id,
            ),
        ],
    )

    node_observers = {
        parsed_segment_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Parsed Segment Input",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:parsed-segments",
                    kind="progress",
                    level="info",
                    message=f"{segment_count} parsed segments entered the unified document stage.",
                    object_id=parsed_segment_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="parsed-segment-input",
                    title="Input Objects",
                    fields=[
                        RuntimeSummaryField(key="input_object", label="input_object", value="parser_segments"),
                        RuntimeSummaryField(key="segment_count", label="segment_count", value=str(segment_count)),
                        RuntimeSummaryField(
                            key="parser_name",
                            label="parser_name",
                            value=parsed_document.parser_name or "unknown",
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-normalization", label="View Normalization", target_kind="node", target_id=normalization_decision_id)],
        ),
        normalization_policy_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Normalization Policy",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:policy",
                    kind="rule",
                    level="info",
                    message=str((runtime_trace or {}).get("decision_summary") or "Parser segments are normalized with heading and field alignment."),
                    object_id=normalization_policy_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="normalization-policy",
                    title="Policy Basis",
                    fields=[
                        RuntimeSummaryField(
                            key="decision_summary",
                            label="decision_summary",
                            value=str((runtime_trace or {}).get("decision_summary") or "normalize parser segments"),
                        ),
                        RuntimeSummaryField(
                            key="ai_summary",
                            label="ai_summary",
                            value=str((runtime_trace or {}).get("ai_summary") or "field alignment and heading normalization"),
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-normalization", label="View Normalization", target_kind="node", target_id=normalization_decision_id)],
        ),
        unified_document_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Unified Document",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:document",
                    kind="result",
                    level="success" if segment_count else "warning",
                    message=(
                        f"Unified document object is ready with full coverage of {segment_count} paragraphs."
                        if segment_count
                        else "Unified document object remains incomplete because no parser segments were available."
                    ),
                    object_id=unified_document_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="document-identity",
                    title="Document Identity",
                    fields=[
                        RuntimeSummaryField(key="title", label="title", value=document_title),
                        RuntimeSummaryField(key="file_type", label="file_type", value=file_type or "unknown"),
                        RuntimeSummaryField(key="section_count", label="section_count", value=str(len(section_labels))),
                        RuntimeSummaryField(key="paragraph_count", label="paragraph_count", value=str(segment_count)),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        normalization_decision_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Normalization Decision",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:decision",
                    kind="decision",
                    level="info",
                    message="Section headings and parser segments are being consolidated into stable unified objects.",
                    object_id=normalization_decision_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="decision-summary",
                    title="Decision Summary",
                    fields=[
                        RuntimeSummaryField(key="parser_name", label="parser_name", value=parsed_document.parser_name or "unknown"),
                        RuntimeSummaryField(
                            key="parser_version",
                            label="parser_version",
                            value=parsed_document.parser_version or "unknown",
                        ),
                        RuntimeSummaryField(key="segment_count", label="segment_count", value=str(segment_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(
                    action_id="view-unified-document",
                    label="View Unified Document",
                    target_kind="node",
                    target_id=unified_document_id,
                )
            ],
        ),
        section_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Unified Sections",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:sections",
                    kind="result",
                    level="success" if section_labels else "warning",
                    message=(
                        f"Section grouping produced {len(section_labels)} normalized sections with full paragraph coverage."
                        if section_labels
                        else "No section grouping could be established from parser output."
                    ),
                    object_id=section_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="section-group-summary",
                    title="Section Group Summary",
                    fields=[
                        RuntimeSummaryField(key="section_count", label="section_count", value=str(len(section_labels))),
                        RuntimeSummaryField(
                            key="sample_sections",
                            label="sample_sections",
                            value=", ".join(section_labels[:5]) if section_labels else "not available",
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        paragraph_group_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Unified Paragraphs",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:paragraphs",
                    kind="result",
                    level="success" if segment_count else "warning",
                    message=(
                        f"All {segment_count} parsed segments have been promoted to paragraph-level unified objects."
                        if segment_count
                        else "No paragraph-level unified objects could be created."
                    ),
                    object_id=paragraph_group_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="paragraph-group-summary",
                    title="Paragraph Group Summary",
                    fields=[
                        RuntimeSummaryField(key="paragraph_count", label="paragraph_count", value=str(segment_count)),
                        RuntimeSummaryField(
                            key="coverage",
                            label="coverage",
                            value="full_document" if segment_count else "empty_document",
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
    }

    for section_index, section_id in enumerate(section_node_ids, start=1):
        section_node = nodes_by_id(nodes, section_id)
        node_observers[section_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Unified Section",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{section_id}:created",
                    kind="result",
                    level="info",
                    message=f"Section {section_index} was normalized with full paragraph membership preserved.",
                    object_id=section_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id=f"{section_id}:summary",
                    title="Section Summary",
                    fields=[
                        RuntimeSummaryField(
                            key="section_label",
                            label="section_label",
                            value=str(section_node.attributes.get("section_label") or "unknown"),
                        ),
                        RuntimeSummaryField(key="section_order", label="section_order", value=str(section_index)),
                        RuntimeSummaryField(
                            key="paragraph_count",
                            label="paragraph_count",
                            value=str(section_node.attributes.get("paragraph_count") or 0),
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    for paragraph_id in paragraph_node_ids:
        paragraph_attributes = paragraph_attributes_by_id[paragraph_id]
        paragraph_order = int(paragraph_attributes["paragraph_order"])
        node_observers[paragraph_id] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Unified Paragraph",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{paragraph_id}:created",
                    kind="result",
                    level="info",
                    message=f"Paragraph {paragraph_order} is fully represented in the unified document graph.",
                    object_id=paragraph_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id=f"{paragraph_id}:summary",
                    title="Paragraph Summary",
                    fields=[
                        RuntimeSummaryField(
                            key="section_label",
                            label="section_label",
                            value=str(paragraph_attributes.get("section_label") or "unknown"),
                        ),
                        RuntimeSummaryField(
                            key="block_type",
                            label="block_type",
                            value=str(paragraph_attributes.get("block_type") or "section"),
                        ),
                        RuntimeSummaryField(
                            key="anchor",
                            label="anchor",
                            value=_format_anchor(paragraph_attributes.get("anchor")),
                        ),
                        RuntimeSummaryField(
                            key="content_excerpt",
                            label="content_excerpt",
                            value=str(paragraph_attributes.get("content_excerpt") or ""),
                        ),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    edge_observers = {
        f"{parsed_segment_group_id}:normalized_by": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="normalized_by",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:input-to-decision",
                    kind="progress",
                    level="info",
                    message="Parser segment input is routed into the normalization decision.",
                    object_id=f"{parsed_segment_group_id}:normalized_by",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="input-to-decision",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="normalized_by"),
                        RuntimeSummaryField(key="input_count", label="input_count", value=str(segment_count)),
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="unified-document-normalization"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        f"{normalization_policy_id}:governs": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="governs",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:policy-governs",
                    kind="rule",
                    level="info",
                    message="Normalization policy governs how parser output becomes stable document objects.",
                    object_id=f"{normalization_policy_id}:governs",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="policy-governs",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="governs"),
                        RuntimeSummaryField(key="rule_key", label="rule_key", value="unified-document-normalization"),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        f"{normalization_decision_id}:normalized_to": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="normalized_to",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:unified:normalized-to",
                    kind="result",
                    level="success" if segment_count else "warning",
                    message="Normalization decision materialized the unified document object.",
                    object_id=f"{normalization_decision_id}:normalized_to",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="normalized-to-summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="normalized_to"),
                        RuntimeSummaryField(key="section_count", label="section_count", value=str(len(section_labels))),
                        RuntimeSummaryField(key="paragraph_count", label="paragraph_count", value=str(segment_count)),
                    ],
                )
            ],
            actions=[
                RuntimeAction(
                    action_id="view-source",
                    label="View Source",
                    target_kind="node",
                    target_id=normalization_decision_id,
                ),
                RuntimeAction(
                    action_id="view-target",
                    label="View Target",
                    target_kind="node",
                    target_id=unified_document_id,
                ),
            ],
        )
    }

    if section_node_ids:
        first_section_edge = next(
            edge.edge_id
            for edge in edges
            if edge.source == section_group_id and edge.target == section_node_ids[0]
        )
        edge_observers[first_section_edge] = RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="contains",
            subtitle=document_title,
            status=RuntimeStatus.COMPLETED,
            stream=[
                RuntimeEvent(
                    event_id=f"{first_section_edge}:result",
                    kind="result",
                    level="info",
                    message="Unified section group now contains the first normalized section object.",
                    object_id=first_section_edge,
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id=f"{first_section_edge}:summary",
                    title="Relation Summary",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="contains"),
                        RuntimeSummaryField(key="section_label", label="section_label", value=section_labels[0]),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        )

    primary_node_ids = [
        parsed_segment_group_id,
        normalization_policy_id,
        normalization_decision_id,
        unified_document_id,
        section_group_id,
        paragraph_group_id,
        *section_node_ids[:3],
        *paragraph_node_ids[:6],
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


def _group_segments_by_section(segments: list[ParsedSegment]) -> OrderedDict[str, list[tuple[int, ParsedSegment]]]:
    grouped: OrderedDict[str, list[tuple[int, ParsedSegment]]] = OrderedDict()
    for paragraph_index, segment in enumerate(segments, start=1):
        grouped.setdefault(_segment_section_label(segment), []).append((paragraph_index, segment))
    return grouped


def _segment_section_label(segment: ParsedSegment) -> str:
    value = (segment.heading or "").strip()
    if value:
        return value
    block_type = (segment.block_type or "section").replace("_", " ").strip()
    return f"{block_type.title()} Section"


def _paragraph_label(index: int, segment: ParsedSegment) -> str:
    base = (segment.content or "").strip()
    if not base:
        return f"Paragraph {index}"
    compact = " ".join(base.split())
    if len(compact) > 42:
        compact = f"{compact[:39]}..."
    return compact


def _format_anchor(anchor: object) -> str:
    if not isinstance(anchor, dict) or not anchor:
        return "not available"
    return ", ".join(f"{key}={value}" for key, value in anchor.items())


def nodes_by_id(nodes: list[RuntimeGraphNode], node_id: str) -> RuntimeGraphNode:
    for node in nodes:
        if node.node_id == node_id:
            return node
    raise KeyError(node_id)
