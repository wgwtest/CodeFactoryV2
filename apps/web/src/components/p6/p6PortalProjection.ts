import type { P6PortalProjection } from "../../lib/p6";
import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  buildPortalViewArtifact,
  buildPortalViewFlow,
  buildPortalViewNode,
  readP6PortalLayout,
  type P6PortalNodeId,
  type P6PortalPosition,
  type P6PortalViewArtifact,
  type P6PortalViewFlow,
  type P6PortalViewNode,
} from "./p6PortalData";

function isRelationNodeId(nodeId: string): nodeId is P6PortalNodeId {
  return nodeId === "user" || nodeId === "p1" || nodeId === "p2" || nodeId === "p3" || nodeId === "p4" || nodeId === "p5";
}

export type P6PortalLayoutMode = "system" | "personal";
export type P6PortalRelationshipViewMode = "semantic" | "projection";

export type P6PortalNodeRelationSnapshot = {
  nodeId: P6PortalNodeId;
  incoming: number;
  outgoing: number;
  artifacts: number;
  label: string;
};

export type P6PortalProjectionSummary = {
  moduleCount: number;
  userCount: number;
  artifactCount: number;
  flowCount: number;
  autoProjectionCount: number;
  manualProjectionCount: number;
  archiveName: string;
  layoutModeLabel: string;
  relationshipModeLabel: string;
  sourceLabel: string;
  scenarioLabel: string;
  focusHint: string;
  alertMessage: string;
  knowledgeBaseName: string;
  contextHint: string;
  freshnessLabel: string;
  degradedReason: string | null;
};

export function hasStoredP6PortalLayout() {
  if (typeof window === "undefined") {
    return false;
  }

  return Boolean(window.localStorage.getItem(P6_PORTAL_LAYOUT_STORAGE_KEY));
}

export function readPersonalPortalLayout(): Record<P6PortalNodeId, P6PortalPosition> {
  return readP6PortalLayout();
}

export function buildPortalViewModel(projection: P6PortalProjection) {
  return {
    nodes: projection.node_list.filter((node) => node.node_kind === "module").map(buildPortalViewNode),
    flows: projection.flow_list.map(buildPortalViewFlow),
    artifacts: projection.artifact_list.map(buildPortalViewArtifact),
  };
}

export function buildPortalNodeRelationSnapshots(
  nodes: P6PortalViewNode[],
  flows: P6PortalViewFlow[],
  artifacts: P6PortalViewArtifact[],
): Partial<Record<P6PortalNodeId, P6PortalNodeRelationSnapshot>> {
  const snapshots = Object.fromEntries(
    nodes.map((node) => [
      node.id,
      {
        nodeId: node.id,
        incoming: 0,
        outgoing: 0,
        artifacts: 0,
        label: "",
      },
    ]),
  ) as Partial<Record<P6PortalNodeId, P6PortalNodeRelationSnapshot>>;

  flows.forEach((flow) => {
    if (isRelationNodeId(flow.from)) {
      const fromSnapshot = snapshots[flow.from];
      if (fromSnapshot) {
        fromSnapshot.outgoing += 1;
      }
    }
    if (isRelationNodeId(flow.to)) {
      const toSnapshot = snapshots[flow.to];
      if (toSnapshot) {
        toSnapshot.incoming += 1;
      }
    }
  });

  artifacts.forEach((artifact) => {
    artifact.linkedNodeIds.forEach((nodeId) => {
      if (snapshots[nodeId]) {
        snapshots[nodeId].artifacts += 1;
      }
    });
  });

  Object.values(snapshots).forEach((snapshot) => {
    if (snapshot) {
      snapshot.label = `入${snapshot.incoming} / 出${snapshot.outgoing} / 产物${snapshot.artifacts}`;
    }
  });

  return snapshots;
}

export function buildPortalProjectionSummary(
  archiveName: string,
  layoutMode: P6PortalLayoutMode,
  relationshipMode: P6PortalRelationshipViewMode,
  projection: P6PortalProjection,
) {
  const manualCount =
    projection.node_list.filter((node) => node.projection_mode === "manual").length +
    projection.artifact_list.filter((artifact) => artifact.projection_mode === "manual").length;
  const autoCount = projection.node_list.length + projection.artifact_list.length - manualCount;

  return {
    moduleCount: projection.portal_summary.module_count,
    userCount: projection.portal_summary.user_count,
    artifactCount: projection.portal_summary.artifact_count,
    flowCount: projection.portal_summary.flow_count,
    autoProjectionCount: autoCount,
    manualProjectionCount: manualCount,
    archiveName,
    layoutModeLabel: layoutMode === "system" ? "推荐布局" : "个人布局",
    relationshipModeLabel: relationshipMode === "semantic" ? "语义线" : "投影聚合",
    sourceLabel: projection.portal_summary.source_label,
    scenarioLabel: projection.portal_summary.scenario_label,
    focusHint: projection.portal_summary.focus_hint,
    alertMessage: projection.portal_summary.alert_message,
    knowledgeBaseName: projection.knowledge_context.current_knowledge_base_name,
    contextHint: projection.knowledge_context.context_hint,
    freshnessLabel: projection.freshness === "fresh" ? "新鲜" : projection.freshness === "stale" ? "过期" : "未知",
    degradedReason: projection.degraded_reason ?? null,
  } satisfies P6PortalProjectionSummary;
}

export function getArtifactsForRelationshipView(
  relationshipMode: P6PortalRelationshipViewMode,
  focusedNodeId: P6PortalNodeId | null,
  artifacts: P6PortalViewArtifact[],
): P6PortalViewArtifact[] {
  if (relationshipMode === "semantic" || !focusedNodeId) {
    return artifacts;
  }

  return artifacts.filter((artifact) => artifact.linkedNodeIds.includes(focusedNodeId));
}
