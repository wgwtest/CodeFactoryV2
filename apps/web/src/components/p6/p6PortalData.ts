import type {
  P6ParticipantNodePayload,
  P6PortalArtifact,
  P6PortalFlow,
  P6PortalNode,
  P6ProjectionMode,
  P6StageNodeStatusPayload,
} from "../../lib/p6";

export type P6PortalNodeId = "user" | "p1" | "p2" | "p3" | "p4" | "p5";
export type P6PortalArtifactId = "spec" | "design" | "tooling";
export type P6PortalAnchorSide = "left" | "right" | "top" | "bottom";

export type P6PortalPosition = {
  x: number;
  y: number;
};

export type P6PortalViewNode =
  | {
      id: "user";
      kind: "user";
      title: string;
      summary: string;
      projectionMode: P6ProjectionMode;
      accent: string;
      width: number;
      height: number;
      categoryLabel: string;
      description: string;
      participantPayload: P6ParticipantNodePayload;
    }
  | {
      id: Exclude<P6PortalNodeId, "user">;
      kind: "module";
      title: string;
      stage: string;
      route?: string;
      summary: string;
      primaryStatus: string;
      freshness: string;
      projectionMode: P6ProjectionMode;
      accent: string;
      width: number;
      height: number;
      categoryLabel: string;
      description: string;
      stageCard: P6StageNodeStatusPayload;
    };

export type P6PortalViewFlow = {
  id: string;
  from: P6PortalNodeId;
  to: P6PortalNodeId;
  fromSide: P6PortalAnchorSide;
  toSide: P6PortalAnchorSide;
  label: string;
  tone: "knowledge" | "analysis" | "design" | "tooling" | "delivery";
  renderStyle: "solid" | "dashed";
  semanticLabel: string;
};

export type P6PortalViewArtifact = {
  id: P6PortalArtifactId;
  title: string;
  summary: string;
  x: number;
  y: number;
  tone: "analysis" | "design" | "tooling";
  categoryLabel: string;
  projectionMode: P6ProjectionMode;
  linkedNodeIds: P6PortalNodeId[];
};

type P6PortalNodePreset = {
  width: number;
  height: number;
  accent: string;
  categoryLabel: string;
};

type P6PortalArtifactPreset = {
  x: number;
  y: number;
  categoryLabel: string;
};

const P6_PORTAL_NODE_PRESETS: Record<P6PortalNodeId, P6PortalNodePreset> = {
  user: {
    width: 220,
    height: 150,
    accent: "#2563eb",
    categoryLabel: "角色节点",
  },
  p1: {
    width: 330,
    height: 208,
    accent: "#0f766e",
    categoryLabel: "系统节点",
  },
  p2: {
    width: 340,
    height: 208,
    accent: "#2563eb",
    categoryLabel: "系统节点",
  },
  p3: {
    width: 340,
    height: 208,
    accent: "#4f46e5",
    categoryLabel: "系统节点",
  },
  p4: {
    width: 360,
    height: 208,
    accent: "#ca8a04",
    categoryLabel: "系统节点",
  },
  p5: {
    width: 350,
    height: 208,
    accent: "#dc2626",
    categoryLabel: "系统节点",
  },
};

const P6_PORTAL_ARTIFACT_PRESETS: Record<P6PortalArtifactId, P6PortalArtifactPreset> = {
  spec: {
    x: 745,
    y: 300,
    categoryLabel: "数据产物",
  },
  design: {
    x: 1180,
    y: 330,
    categoryLabel: "数据产物",
  },
  tooling: {
    x: 1350,
    y: 610,
    categoryLabel: "数据产物",
  },
};

export const P6_PORTAL_LAYOUT_STORAGE_KEY = "code-factory.p6.portal.layout";

export const P6_PORTAL_WORLD = {
  width: 1920,
  height: 1080,
};

export const defaultP6PortalLayout: Record<P6PortalNodeId, P6PortalPosition> = {
  user: { x: 110, y: 430 },
  p1: { x: 400, y: 660 },
  p2: { x: 410, y: 210 },
  p3: { x: 960, y: 200 },
  p4: { x: 1040, y: 650 },
  p5: { x: 1500, y: 410 },
};

export const p6PortalLegendRoadmap = [
  { id: "p6.2", label: "登录接入", status: "占位" },
  { id: "p6.3", label: "权限与角色控制", status: "占位" },
  { id: "p6.4", label: "入口与导航治理", status: "占位" },
];

function toPortalNodeId(nodeId: string): P6PortalNodeId {
  if (nodeId === "p1" || nodeId === "p2" || nodeId === "p3" || nodeId === "p4" || nodeId === "p5") {
    return nodeId;
  }
  return "user";
}

function toPortalArtifactId(artifactId: string): P6PortalArtifactId {
  if (artifactId === "design" || artifactId === "tooling") {
    return artifactId;
  }
  return "spec";
}

export function buildPortalViewNode(node: P6PortalNode): P6PortalViewNode {
  const nodeId = toPortalNodeId(node.node_id);
  const preset = P6_PORTAL_NODE_PRESETS[nodeId];

  if (node.node_kind === "user" && node.participant_payload) {
    return {
      id: "user",
      kind: "user",
      title: node.title,
      summary: node.summary,
      projectionMode: node.projection_mode,
      accent: preset.accent,
      width: preset.width,
      height: preset.height,
      categoryLabel: preset.categoryLabel,
      description: node.description,
      participantPayload: node.participant_payload,
    };
  }

  return {
    id: nodeId === "user" ? "p1" : nodeId,
    kind: "module",
    title: node.title,
    stage: node.stage_id ?? "",
    route: node.route ?? undefined,
    summary: node.summary,
    primaryStatus: node.primary_status ?? "",
    freshness: node.freshness ?? "unknown",
    projectionMode: node.projection_mode,
    accent: preset.accent,
    width: preset.width,
    height: preset.height,
    categoryLabel: preset.categoryLabel,
    description: node.description,
    stageCard: node.stage_card ?? {
      stage_id: node.stage_id ?? "",
      headline_value: node.title,
      summary_line: node.summary,
      metric_items: [],
      entry_badge: { label: "入口未知", tone: "neutral" },
      health_badge: { label: "未知", tone: "neutral" },
      timestamp_label: "时间未知",
      degraded_hint: null,
    },
  };
}

export function buildPortalViewFlow(flow: P6PortalFlow): P6PortalViewFlow {
  return {
    id: flow.flow_id,
    from: toPortalNodeId(flow.from_node_id),
    to: toPortalNodeId(flow.to_node_id),
    fromSide: flow.from_pin,
    toSide: flow.to_pin,
    label: flow.label,
    tone: flow.render_tone,
    renderStyle: flow.render_style,
    semanticLabel: flow.semantic_type,
  };
}

export function buildPortalViewArtifact(artifact: P6PortalArtifact): P6PortalViewArtifact {
  const artifactId = toPortalArtifactId(artifact.artifact_id);
  const preset = P6_PORTAL_ARTIFACT_PRESETS[artifactId];

  return {
    id: artifactId,
    title: artifact.title,
    summary: artifact.summary,
    x: preset.x,
    y: preset.y,
    tone: artifact.render_tone,
    categoryLabel: preset.categoryLabel,
    projectionMode: artifact.projection_mode,
    linkedNodeIds: artifact.linked_node_ids.map(toPortalNodeId),
  };
}

export function readP6PortalLayout() {
  if (typeof window === "undefined") {
    return defaultP6PortalLayout;
  }

  try {
    const raw = window.localStorage.getItem(P6_PORTAL_LAYOUT_STORAGE_KEY);
    if (!raw) {
      return defaultP6PortalLayout;
    }

    const parsed = JSON.parse(raw) as Partial<Record<P6PortalNodeId, P6PortalPosition>>;
    return {
      ...defaultP6PortalLayout,
      ...parsed,
    };
  } catch {
    return defaultP6PortalLayout;
  }
}
