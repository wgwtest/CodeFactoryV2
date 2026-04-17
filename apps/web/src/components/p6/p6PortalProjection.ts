import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  p6PortalArtifacts,
  p6PortalFlows,
  p6PortalNodes,
  readP6PortalLayout,
  type P6PortalArtifact,
  type P6PortalNodeId,
  type P6PortalPosition,
} from "./p6PortalData";

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

export function buildPortalNodeRelationSnapshots(): Record<P6PortalNodeId, P6PortalNodeRelationSnapshot> {
  const snapshots = Object.fromEntries(
    p6PortalNodes.map((node) => [
      node.id,
      {
        nodeId: node.id,
        incoming: 0,
        outgoing: 0,
        artifacts: 0,
        label: "",
      },
    ]),
  ) as Record<P6PortalNodeId, P6PortalNodeRelationSnapshot>;

  p6PortalFlows.forEach((flow) => {
    snapshots[flow.from].outgoing += 1;
    snapshots[flow.to].incoming += 1;
  });

  p6PortalArtifacts.forEach((artifact) => {
    artifact.linkedNodeIds.forEach((nodeId) => {
      snapshots[nodeId].artifacts += 1;
    });
  });

  Object.values(snapshots).forEach((snapshot) => {
    snapshot.label = `入${snapshot.incoming} / 出${snapshot.outgoing} / 产物${snapshot.artifacts}`;
  });

  return snapshots;
}

export function buildPortalProjectionSummary(
  archiveName: string,
  layoutMode: P6PortalLayoutMode,
  relationshipMode: P6PortalRelationshipViewMode,
) {
  const manualCount =
    p6PortalNodes.filter((node) => node.projectionMode === "manual").length +
    p6PortalArtifacts.filter((artifact) => artifact.projectionMode === "manual").length;
  const autoCount = p6PortalNodes.length + p6PortalArtifacts.length - manualCount;

  return {
    moduleCount: p6PortalNodes.filter((node) => node.kind === "module").length,
    userCount: p6PortalNodes.filter((node) => node.kind === "user").length,
    artifactCount: p6PortalArtifacts.length,
    flowCount: p6PortalFlows.length,
    autoProjectionCount: autoCount,
    manualProjectionCount: manualCount,
    archiveName,
    layoutModeLabel: layoutMode === "system" ? "推荐布局" : "个人布局",
    relationshipModeLabel: relationshipMode === "semantic" ? "语义线" : "投影聚合",
  } satisfies P6PortalProjectionSummary;
}

export function getArtifactsForRelationshipView(
  relationshipMode: P6PortalRelationshipViewMode,
  focusedNodeId: P6PortalNodeId | null,
): P6PortalArtifact[] {
  if (relationshipMode === "semantic" || !focusedNodeId) {
    return p6PortalArtifacts;
  }

  return p6PortalArtifacts.filter((artifact) => artifact.linkedNodeIds.includes(focusedNodeId));
}
