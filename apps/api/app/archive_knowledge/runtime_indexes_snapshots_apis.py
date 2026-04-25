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
) -> RuntimeStageSnapshot:
    del archive_id
    definition = STAGE_DEFINITION_MAP["indexes_snapshots_apis"]
    stage_status = RuntimeStatus.COMPLETED if document_published else RuntimeStatus.PENDING

    snapshot_id = f"{document_id}:publish-layer:snapshot"
    index_id = f"{document_id}:publish-layer:index"
    api_id = f"{document_id}:publish-layer:api-payload"
    version_label = (current_version or {}).get("version_label") or "not_published"

    nodes = [
        RuntimeGraphNode(
            node_id=snapshot_id,
            label="Publication Snapshot",
            node_type="publication_snapshot",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"version_label": version_label},
        ),
        RuntimeGraphNode(
            node_id=index_id,
            label="Search / Graph Index",
            node_type="index_write",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"version_label": version_label},
        ),
        RuntimeGraphNode(
            node_id=api_id,
            label="API Payload",
            node_type="api_payload",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
            attributes={"version_label": version_label},
        ),
    ]

    edges = [
        RuntimeGraphEdge(
            edge_id=f"{snapshot_id}:indexed_as",
            source=snapshot_id,
            target=index_id,
            relation="indexed_as",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
        RuntimeGraphEdge(
            edge_id=f"{snapshot_id}:served_by",
            source=snapshot_id,
            target=api_id,
            relation="served_by",
            stage_id=definition.stage_id,
            status=stage_status,
            origin=RuntimeOrigin.DERIVED,
            is_primary=True,
        ),
    ]

    stage_observer = RuntimeObserverPayload(
        mode=RuntimeObserverMode.STAGE,
        title="Indexes / Snapshots / APIs",
        subtitle=document_title,
        status=stage_status,
        stream=[
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:start",
                kind="progress",
                level="info",
                message=(
                    "Publication snapshot is propagating into index and API layers."
                    if document_published
                    else "Publication snapshot has not been materialized for the current document yet."
                ),
                object_id=snapshot_id,
                object_kind="stage",
            ),
            RuntimeEvent(
                event_id=f"{document_id}:publish-layer:result",
                kind="result",
                level="success" if document_published else "warning",
                message=f"Current publication version: {version_label}",
                object_id=api_id,
                object_kind="stage",
            ),
        ],
        sections=[
            RuntimeSummarySection(
                section_id="publish-layer-summary",
                title="Publish Layer Summary",
                fields=[
                    RuntimeSummaryField(key="document_published", label="document_published", value=str(document_published).lower(), tone="success" if document_published else "warning"),
                    RuntimeSummaryField(key="version_label", label="version_label", value=version_label, tone="info"),
                    RuntimeSummaryField(key="snapshot_status", label="snapshot_status", value=stage_status.value, tone="success" if document_published else "warning"),
                ],
            )
        ],
        actions=[
            RuntimeAction(action_id="view-snapshot", label="View snapshot node", target_kind="node", target_id=snapshot_id),
            RuntimeAction(action_id="view-api-payload", label="View API payload", target_kind="node", target_id=api_id),
        ],
    )

    node_observers = {
        snapshot_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Publication Snapshot",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:snapshot",
                    kind="result",
                    level="success" if document_published else "warning",
                    message=(
                        f"Publication snapshot is available under version {version_label}."
                        if document_published
                        else "Publication snapshot has not been generated for the current document."
                    ),
                    object_id=snapshot_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="snapshot-summary",
                    title="Snapshot Summary",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="publication_snapshot"),
                        RuntimeSummaryField(key="version_label", label="version_label", value=version_label),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-index", label="View index node", target_kind="node", target_id=index_id),
                RuntimeAction(action_id="view-api", label="View API payload", target_kind="node", target_id=api_id),
            ],
        ),
        index_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="Search / Graph Index",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:index",
                    kind="result",
                    level="success" if document_published else "warning",
                    message=(
                        "Publication snapshot has been written into index layers."
                        if document_published
                        else "Index write is waiting for a published snapshot."
                    ),
                    object_id=index_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="index-summary",
                    title="Index Summary",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="index_write"),
                        RuntimeSummaryField(key="version_label", label="version_label", value=version_label),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-snapshot", label="View snapshot node", target_kind="node", target_id=snapshot_id)],
        ),
        api_id: RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title="API Payload",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:api",
                    kind="result",
                    level="success" if document_published else "warning",
                    message=(
                        "API payload is ready to serve the published snapshot."
                        if document_published
                        else "API payload is waiting for a published snapshot."
                    ),
                    object_id=api_id,
                    object_kind="node",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="api-summary",
                    title="API Summary",
                    fields=[
                        RuntimeSummaryField(key="node_type", label="node_type", value="api_payload"),
                        RuntimeSummaryField(key="version_label", label="version_label", value=version_label),
                    ],
                )
            ],
            actions=[RuntimeAction(action_id="view-snapshot", label="View snapshot node", target_kind="node", target_id=snapshot_id)],
        ),
    }

    edge_observers = {
        f"{snapshot_id}:indexed_as": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="indexed_as",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:indexed-as",
                    kind="result",
                    level="success" if document_published else "warning",
                    message=(
                        "Snapshot is now represented in search and graph indexes."
                        if document_published
                        else "Index relation is pending until a publication snapshot exists."
                    ),
                    object_id=f"{snapshot_id}:indexed_as",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="indexed-as-summary",
                    title="Index Relation",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="indexed_as"),
                        RuntimeSummaryField(key="version_label", label="version_label", value=version_label),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=snapshot_id),
                RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=index_id),
            ],
        ),
        f"{snapshot_id}:served_by": RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title="served_by",
            subtitle=document_title,
            status=stage_status,
            stream=[
                RuntimeEvent(
                    event_id=f"{document_id}:publish-layer:served-by",
                    kind="result",
                    level="success" if document_published else "warning",
                    message=(
                        "Snapshot is exposed through the API payload."
                        if document_published
                        else "API relation is pending until a publication snapshot exists."
                    ),
                    object_id=f"{snapshot_id}:served_by",
                    object_kind="edge",
                )
            ],
            sections=[
                RuntimeSummarySection(
                    section_id="served-by-summary",
                    title="API Relation",
                    fields=[
                        RuntimeSummaryField(key="relation", label="relation", value="served_by"),
                        RuntimeSummaryField(key="version_label", label="version_label", value=version_label),
                    ],
                )
            ],
            actions=[
                RuntimeAction(action_id="view-source-node", label="View source node", target_kind="node", target_id=snapshot_id),
                RuntimeAction(action_id="view-target-node", label="View target node", target_kind="node", target_id=api_id),
            ],
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
            primary_node_ids=[snapshot_id, index_id, api_id],
            primary_edge_ids=[f"{snapshot_id}:indexed_as", f"{snapshot_id}:served_by"],
        ),
        stage_observer=stage_observer,
        node_observers=node_observers,
        edge_observers=edge_observers,
    )
