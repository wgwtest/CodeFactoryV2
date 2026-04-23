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


def build_asset_intake_snapshot(
    *,
    archive_id: str,
    archive_name: str,
    document_id: str,
    document_title: str,
    document_path: str | None,
    source_dir: Path,
    source_file_path: str | None,
    file_type: str | None,
    source_archive: str | None,
    source_digest: str | None,
    included_in_archive: bool,
    mode: str,
    intake_timestamp: str,
) -> RuntimeStageSnapshot:
    definition = STAGE_DEFINITION_MAP["asset_intake"]
    stage_status = RuntimeStatus.COMPLETED if included_in_archive else RuntimeStatus.WARNING
    resolved_source_dir = str(source_dir.expanduser().resolve())
    source_path = source_file_path or document_path or "unknown"
    file_node_id = f"{document_id}:asset-intake:file"
    directory_node_id = f"{document_id}:asset-intake:directory"
    intake_task_node_id = f"{document_id}:asset-intake:task"
    digest_node_id = f"{document_id}:asset-intake:digest"
    result_node_id = f"{document_id}:asset-intake:result"

    nodes = [
        RuntimeGraphNode(
            node_id=file_node_id,
            label=document_title,
            node_type="source_file",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={
                "document_id": document_id,
                "file_type": file_type or "unknown",
                "path": source_path,
                "source_archive": source_archive or archive_name,
            },
        ),
        RuntimeGraphNode(
            node_id=directory_node_id,
            label="Source Directory",
            node_type="source_directory",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.SOURCE,
            attributes={"path": resolved_source_dir},
        ),
        RuntimeGraphNode(
            node_id=intake_task_node_id,
            label="Asset Intake Task",
            node_type="intake_task",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={"mode": mode, "archive_name": archive_name, "started_at": intake_timestamp},
        ),
        RuntimeGraphNode(
            node_id=digest_node_id,
            label="File Digest",
            node_type="file_digest",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if source_digest else RuntimeStatus.UNAVAILABLE,
            origin=RuntimeOrigin.SOURCE if source_digest else RuntimeOrigin.UNAVAILABLE,
            attributes={"source_digest": source_digest or "missing"},
        ),
        RuntimeGraphNode(
            node_id=result_node_id,
            label="Intake Result",
            node_type="intake_result",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={
                "included_in_archive": included_in_archive,
                "document_path": document_path or "unknown",
                "mode": mode,
            },
        ),
    ]
    edges = [
        RuntimeGraphEdge(
            edge_id=f"{file_node_id}:located_in",
            source=file_node_id,
            target=directory_node_id,
            relation="located_in",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{file_node_id}:submitted_to",
            source=file_node_id,
            target=intake_task_node_id,
            relation="submitted_to",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{file_node_id}:hashed_to",
            source=file_node_id,
            target=digest_node_id,
            relation="hashed_to",
            stage_id=definition.stage_id,
            status=RuntimeStatus.COMPLETED if source_digest else RuntimeStatus.UNAVAILABLE,
            origin=RuntimeOrigin.SOURCE if source_digest else RuntimeOrigin.UNAVAILABLE,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{intake_task_node_id}:results_in",
            source=intake_task_node_id,
            target=result_node_id,
            relation="results_in",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.SOURCE,
            is_primary=True,
            attributes={"included_in_archive": included_in_archive},
        ),
    ]

    return RuntimeStageSnapshot(
        stage_id=definition.stage_id,
        label=definition.label,
        group=definition.group,
        order=definition.order,
        status=stage_status,
        graph=RuntimeStageGraph(
            nodes=nodes,
            edges=edges,
            primary_node_ids=[file_node_id, intake_task_node_id, result_node_id],
            primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
        ),
        stage_observer=RuntimeObserverPayload(
            mode=RuntimeObserverMode.STAGE,
            title="Asset Intake",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:asset-intake:file",
                    kind="progress",
                    level="info",
                    message=f"Registered source file {document_title}",
                    object_id=file_node_id,
                    object_kind="node",
                    timestamp=intake_timestamp,
                ),
                RuntimeEvent(
                    event_id=f"{document_id}:asset-intake:digest",
                    kind="result",
                    level="success" if source_digest else "warning",
                    message=(
                        f"Computed file digest {source_digest}"
                        if source_digest
                        else "File digest was not available during intake"
                    ),
                    object_id=digest_node_id,
                    object_kind="node",
                    timestamp=intake_timestamp,
                ),
                RuntimeEvent(
                    event_id=f"{document_id}:asset-intake:result",
                    kind="result",
                    level="success" if included_in_archive else "warning",
                    message=(
                        "Document entered archive processing"
                        if included_in_archive
                        else "Document was retained but excluded from archive processing"
                    ),
                    object_id=result_node_id,
                    object_kind="node",
                    timestamp=intake_timestamp,
                ),
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="input",
                    title="Input",
                    fields=[
                        RuntimeSummaryField(key="document_title", label="document_title", value=document_title),
                        RuntimeSummaryField(key="source_path", label="source_path", value=source_path),
                        RuntimeSummaryField(key="file_type", label="file_type", value=file_type or "unknown"),
                    ],
                ),
                RuntimeSummarySection(
                    section_id="result",
                    title="Result",
                    fields=[
                        RuntimeSummaryField(key="mode", label="mode", value=mode, tone="info"),
                        RuntimeSummaryField(
                            key="included_in_archive",
                            label="included_in_archive",
                            value="true" if included_in_archive else "false",
                            tone="success" if included_in_archive else "warning",
                        ),
                        RuntimeSummaryField(
                            key="source_digest",
                            label="source_digest",
                            value=source_digest or "missing",
                            tone="success" if source_digest else "warning",
                        ),
                    ],
                ),
            ],
            actions=[RuntimeAction(action_id="view-stage-graph", label="View Stage Graph", target_kind="graph")],
        ),
        node_observers={
            file_node_id: RuntimeObserverPayload(
                mode=RuntimeObserverMode.NODE,
                title="Source File",
                subtitle=document_title,
                status=RuntimeStatus.COMPLETED,
                stream=[
                    RuntimeEvent(
                        event_id=f"{document_id}:asset-intake:file-node",
                        kind="info",
                        level="info",
                        message=f"Source file path: {source_path}",
                        object_id=file_node_id,
                        object_kind="node",
                        timestamp=intake_timestamp,
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="identity",
                        title="Identity",
                        fields=[
                            RuntimeSummaryField(key="title", label="title", value=document_title),
                            RuntimeSummaryField(key="file_type", label="file_type", value=file_type or "unknown"),
                            RuntimeSummaryField(
                                key="source_archive",
                                label="source_archive",
                                value=source_archive or archive_name,
                            ),
                        ],
                    ),
                    RuntimeSummarySection(
                        section_id="traceability",
                        title="Traceability",
                        fields=[
                            RuntimeSummaryField(key="path", label="path", value=source_path),
                            RuntimeSummaryField(key="document_id", label="document_id", value=document_id),
                        ],
                    ),
                ],
                actions=[
                    RuntimeAction(action_id="view-upstream", label="View Upstream", target_kind="graph"),
                    RuntimeAction(action_id="view-evidence", label="View Evidence", target_kind="evidence"),
                ],
            ),
            result_node_id: RuntimeObserverPayload(
                mode=RuntimeObserverMode.NODE,
                title="Intake Result",
                subtitle=document_title,
                status=stage_status,
                stream=[
                    RuntimeEvent(
                        event_id=f"{document_id}:asset-intake:result-node",
                        kind="decision",
                        level="success" if included_in_archive else "warning",
                        message=(
                            "Archive intake marked the document as ready for processing"
                            if included_in_archive
                            else "Archive intake marked the document as excluded"
                        ),
                        object_id=result_node_id,
                        object_kind="node",
                        timestamp=intake_timestamp,
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="result",
                        title="Result",
                        fields=[
                            RuntimeSummaryField(
                                key="included_in_archive",
                                label="included_in_archive",
                                value="true" if included_in_archive else "false",
                                tone="success" if included_in_archive else "warning",
                            ),
                            RuntimeSummaryField(key="mode", label="mode", value=mode),
                            RuntimeSummaryField(key="archive_name", label="archive_name", value=archive_name),
                        ],
                    )
                ],
                actions=[
                    RuntimeAction(action_id="view-upstream", label="View Upstream", target_kind="graph"),
                    RuntimeAction(action_id="view-evidence", label="View Evidence", target_kind="evidence"),
                ],
            ),
        },
        edge_observers={
            f"{intake_task_node_id}:results_in": RuntimeObserverPayload(
                mode=RuntimeObserverMode.EDGE,
                title="results_in",
                subtitle="Asset Intake Task -> Intake Result",
                status=stage_status,
                stream=[
                    RuntimeEvent(
                        event_id=f"{document_id}:asset-intake:results-in-edge",
                        kind="result",
                        level="success" if included_in_archive else "warning",
                        message="Asset intake completed and produced an intake result",
                        object_id=f"{intake_task_node_id}:results_in",
                        object_kind="edge",
                        timestamp=intake_timestamp,
                    )
                ],
                sections=[
                    RuntimeSummarySection(
                        section_id="relation",
                        title="Relation",
                        fields=[
                            RuntimeSummaryField(key="relation", label="relation", value="results_in"),
                            RuntimeSummaryField(key="source", label="source", value="Asset Intake Task"),
                            RuntimeSummaryField(key="target", label="target", value="Intake Result"),
                        ],
                    )
                ],
                actions=[
                    RuntimeAction(action_id="view-source-node", label="View Source Node", target_kind="node"),
                    RuntimeAction(action_id="view-target-node", label="View Target Node", target_kind="node"),
                ],
            )
        },
    )
