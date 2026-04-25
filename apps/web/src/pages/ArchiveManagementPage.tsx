import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  List,
  message,
  Modal,
  Progress,
  Row,
  Select,
  Segmented,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import cytoscape from "cytoscape";
import ReactFlow, {
  Background,
  ConnectionLineType,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "react-flow-renderer";
import type { Edge as FlowEdge, Node as FlowNode } from "react-flow-renderer";
import "react-flow-renderer/dist/style.css";
import "./archiveManagementGraph.css";

import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { WorkspaceOverviewStrip } from "../components/WorkspaceOverviewStrip";
import { useArchiveContext } from "../context/ArchiveContext";
import { getArchiveDocumentRuntime, subscribeArchiveDocumentRuntime } from "../lib/archiveKnowledge";
import {
  createKnowledgeArchive,
  extractKnowledgeArchive,
  getArchivePolicyConfig,
  updateArchivePolicyConfig,
} from "../lib/archives";
import type {
  ArchivePolicyAction,
  ArchivePolicyConfig,
  ArchivePolicyRuntimeSnapshot,
  ArchiveStagePolicyConfig,
  ArchiveStagePolicyRule,
  ArchiveDocumentRuntimeContract,
  ArchiveDocumentRuntimeGraphNode,
  ArchiveDocumentRuntimeMode,
  ArchiveDocumentRuntimeObserverPayload,
  ArchiveDocumentRuntimeStageSnapshot,
  ArchiveDocumentRuntimeStatus,
  CreateKnowledgeArchiveInput,
  KnowledgeArchive,
  KnowledgeArchiveBuildStateDocument,
} from "../lib/api";

const { Paragraph, Text, Title } = Typography;

type WorkspaceView = "overview" | "global" | "archive" | "document" | "policy";
type ObserverMode = "stage" | "node" | "edge";
type GraphLens = "primary" | "all";
type RuntimeTransportState = "snapshot" | "stream_connecting" | "stream_connected" | "polling_fallback";

type PendingItem = {
  id: string;
  archiveId: string;
  title: string;
  severity: "critical" | "warning" | "info";
  description: string;
};

type NodePosition = { x: number; y: number };
type RuntimeNodeLayout = {
  width: number;
  height: number;
  summary: string | null;
  primary: boolean;
};
type StageNodeRole = "input" | "policy" | "output";
type StageRoleLayoutBuckets = {
  inputs: ArchiveDocumentRuntimeGraphNode[];
  policies: ArchiveDocumentRuntimeGraphNode[];
  outputs: ArchiveDocumentRuntimeGraphNode[];
};

const archiveStatusMeta: Record<KnowledgeArchive["status"], { color: string; label: string }> = {
  empty: { color: "default", label: "未抽取" },
  extracting: { color: "processing", label: "运行中" },
  ready: { color: "success", label: "可用" },
  error: { color: "error", label: "阻断" },
};

const documentStateMeta: Record<KnowledgeArchiveBuildStateDocument["state"], { color: string; label: string }> = {
  pending: { color: "default", label: "待处理" },
  running: { color: "processing", label: "运行中" },
  completed: { color: "success", label: "已完成" },
  failed: { color: "error", label: "失败" },
  skipped: { color: "warning", label: "已跳过" },
};

function runtimeNeedsLiveUpdates(
  documentState: KnowledgeArchiveBuildStateDocument["state"] | null | undefined,
  runtime: ArchiveDocumentRuntimeContract | null | undefined,
) {
  if (runtime) {
    return runtime.status === "running" || runtime.stages.some((stage) => stage.status === "running");
  }

  return documentState === "running";
}

const runtimeStatusMeta: Record<ArchiveDocumentRuntimeStatus, { color: string; label: string }> = {
  pending: { color: "default", label: "待处理" },
  running: { color: "processing", label: "运行中" },
  completed: { color: "success", label: "已完成" },
  blocked: { color: "error", label: "已阻断" },
  warning: { color: "warning", label: "告警" },
  unavailable: { color: "default", label: "不可用" },
};

const runtimeModeMeta: Record<ArchiveDocumentRuntimeMode, { color: string; label: string; hint: string }> = {
  persisted: { color: "success", label: "持久化运行态", hint: "当前文档主要阶段来自真实持久化快照。" },
  hybrid: { color: "processing", label: "混合运行态", hint: "部分阶段来自真实快照，部分阶段来自兼容映射。" },
  derived: { color: "warning", label: "派生运行态", hint: "当前阶段仍以已提取产物派生映射为主。" },
  legacy_fallback: { color: "default", label: "旧库兼容态", hint: "当前知识库通过旧产物兼容路径构建运行态。" },
};

const runtimeTransportMeta: Record<RuntimeTransportState, { color: string; label: string; hint: string }> = {
  snapshot: { color: "default", label: "静态快照", hint: "当前页展示最新快照，不保持实时连接" },
  stream_connecting: { color: "processing", label: "连接 Stream 中", hint: "正在等待后端 runtime stream 首包" },
  stream_connected: { color: "success", label: "已连接 Stream", hint: "流程与图谱正在通过服务端推流实时刷新" },
  polling_fallback: { color: "warning", label: "已回退轮询", hint: "Stream 不可用，当前以定时快照拉取兜底" },
};

const policyActionMeta: Record<ArchivePolicyAction, { label: string; color: string }> = {
  auto_pass: { label: "自动放行", color: "success" },
  warn_continue: { label: "告警继续", color: "warning" },
  manual_review: { label: "转人工复核", color: "processing" },
  block_return: { label: "阻断并回退", color: "error" },
  defer_publish: { label: "延迟发布", color: "default" },
};

const policyActionOptions: Array<{ value: ArchivePolicyAction; label: string; color: string }> = [
  { value: "auto_pass", ...policyActionMeta.auto_pass },
  { value: "warn_continue", ...policyActionMeta.warn_continue },
  { value: "manual_review", ...policyActionMeta.manual_review },
  { value: "block_return", ...policyActionMeta.block_return },
  { value: "defer_publish", ...policyActionMeta.defer_publish },
];

const runtimeRelationLabelMap: Record<string, string> = {
  located_in: "归档到",
  submitted_to: "送入",
  hashed_to: "校验为",
  results_in: "形成",
  classified_as: "识别为",
  evaluated_by: "由此评估",
  selects: "选择",
  considered: "候选考虑",
  warned_by: "产生告警",
  normalized_to: "规范为",
  summarizes: "概括为",
  contains: "包含",
  anchored_at: "锚定到",
  spans: "切出片段",
  evidence_from: "证据来自",
  grouped_into: "汇入",
  connects: "接入图层",
  adjusted_by: "边界修正",
  supports: "支撑",
  proposes: "提出",
  categorized_as: "归类为",
  aliased_as: "别名映射",
  normalized_by: "归一到",
  belongs_to_family: "归属家族",
  resolved_by: "由此整合",
  conflicts_with: "发生冲突",
  reviewed_by: "转人工复核",
  blocked_by: "阻断为",
  publishes_to: "进入发布",
};

const stageGroupMeta: Record<string, { tone: string; background: string; border: string }> = {
  摄取与统一: { tone: "#1d7a64", background: "rgba(225, 246, 240, 0.92)", border: "rgba(29, 122, 100, 0.22)" },
  证据与知识生成: { tone: "#9a6700", background: "rgba(255, 247, 229, 0.94)", border: "rgba(154, 103, 0, 0.22)" },
  规范化与发布: { tone: "#8c4b3a", background: "rgba(255, 241, 239, 0.94)", border: "rgba(140, 75, 58, 0.22)" },
};

type FlowLaneId = "intake" | "evidence" | "publication";
type FlowNodeState = "completed" | "current" | "pending";

const flowLaneMeta: Record<
  FlowLaneId,
  {
    title: string;
    fill: string;
    border: string;
    titleColor: string;
    rect: { x: number; y: number; width: number; height: number };
  }
> = {
  intake: {
    title: "摄取与统一",
    fill: "#edf8f4",
    border: "#d8eee4",
    titleColor: "#447c67",
    rect: { x: 18, y: 18, width: 555, height: 204 },
  },
  evidence: {
    title: "证据与知识生成",
    fill: "#fbf4e8",
    border: "#eedfbd",
    titleColor: "#8b6b2f",
    rect: { x: 590, y: 18, width: 705, height: 204 },
  },
  publication: {
    title: "规范化与发布",
    fill: "#fcf1ef",
    border: "#efddd8",
    titleColor: "#94625a",
    rect: { x: 1312, y: 18, width: 420, height: 204 },
  },
};

const flowLaneStageIds: Record<FlowLaneId, string[]> = {
  intake: ["asset_intake", "parser_router", "parser_execution", "unified_document_object"],
  evidence: [
    "evidence_constructor",
    "evidence_graph_chunk_layer",
    "evidence_pack",
    "concept_candidate_review",
    "relation_review_family_normalization",
    "definition_summary_conflict_consolidation",
  ],
  publication: [
    "canonical_knowledge",
    "quality_policy_evaluation_governance_gate",
    "indexes_snapshots_apis",
  ],
};

const stageDisplayNameMap: Record<string, string> = {
  asset_intake: "素材接入",
  parser_router: "解析路由",
  parser_execution: "解析执行",
  unified_document_object: "统一文档",
  evidence_constructor: "证据构造",
  evidence_graph_chunk_layer: "证据图谱/切块",
  evidence_pack: "证据包",
  concept_candidate_review: "概念审查",
  relation_review_family_normalization: "关系/家族",
  definition_summary_conflict_consolidation: "定义/冲突",
  canonical_knowledge: "规范知识",
  quality_policy_evaluation_governance_gate: "质量门禁",
  indexes_snapshots_apis: "发布/API",
};

const stageGroupDisplayNameMap: Record<string, string> = {
  "Asset Intake and Normalization": "摄取与统一",
  "Evidence and Knowledge Generation": "证据与知识生成",
  "Canonicalization and Publication": "规范化与发布",
  摄取与统一: "摄取与统一",
  证据与知识生成: "证据与知识生成",
  规范化与发布: "规范化与发布",
};

const flowNodeLayout: Record<string, { x: number; y: number; width: number; height: number }> = {
  asset_intake: { x: 40, y: 113, width: 98, height: 36 },
  parser_router: { x: 154, y: 113, width: 98, height: 36 },
  parser_execution: { x: 268, y: 113, width: 98, height: 36 },
  unified_document_object: { x: 382, y: 113, width: 110, height: 36 },
  evidence_constructor: { x: 622, y: 113, width: 104, height: 36 },
  evidence_graph_chunk_layer: { x: 756, y: 113, width: 132, height: 36 },
  evidence_pack: { x: 918, y: 113, width: 92, height: 36 },
  concept_candidate_review: { x: 1076, y: 48, width: 110, height: 34 },
  relation_review_family_normalization: { x: 1076, y: 113, width: 110, height: 34 },
  definition_summary_conflict_consolidation: { x: 1076, y: 178, width: 110, height: 34 },
  canonical_knowledge: { x: 1380, y: 113, width: 100, height: 36 },
  quality_policy_evaluation_governance_gate: { x: 1510, y: 105, width: 102, height: 36 },
  indexes_snapshots_apis: { x: 1670, y: 113, width: 100, height: 36 },
};

const flowEdges: Array<{ from: string; to: string; mode?: "line" | "curve"; via?: { x: number; y: number }[] }> = [
  { from: "asset_intake", to: "parser_router" },
  { from: "parser_router", to: "parser_execution" },
  { from: "parser_execution", to: "unified_document_object" },
  { from: "unified_document_object", to: "evidence_constructor" },
  { from: "evidence_constructor", to: "evidence_graph_chunk_layer" },
  { from: "evidence_graph_chunk_layer", to: "evidence_pack" },
  { from: "evidence_pack", to: "concept_candidate_review" },
  { from: "evidence_pack", to: "relation_review_family_normalization" },
  { from: "evidence_pack", to: "definition_summary_conflict_consolidation" },
  { from: "concept_candidate_review", to: "canonical_knowledge" },
  { from: "relation_review_family_normalization", to: "canonical_knowledge" },
  { from: "definition_summary_conflict_consolidation", to: "canonical_knowledge" },
  { from: "canonical_knowledge", to: "quality_policy_evaluation_governance_gate" },
  { from: "quality_policy_evaluation_governance_gate", to: "indexes_snapshots_apis" },
];

function getFlowLaneId(stageId: string): FlowLaneId {
  if (flowLaneStageIds.intake.includes(stageId)) return "intake";
  if (flowLaneStageIds.evidence.includes(stageId)) return "evidence";
  return "publication";
}

function getStageDisplayLabel(stageId: string, fallback?: string | null) {
  return stageDisplayNameMap[stageId] ?? fallback ?? stageId;
}

function getStageGroupDisplayLabel(stage: Pick<ArchiveDocumentRuntimeStageSnapshot, "stage_id" | "group">) {
  return stageGroupDisplayNameMap[stage.group] ?? flowLaneMeta[getFlowLaneId(stage.stage_id)].title;
}

function getLiveCurrentStage(runtime: ArchiveDocumentRuntimeContract) {
  return (
    runtime.stages.find((stage) => stage.stage_id === runtime.current_stage_id) ??
    runtime.stages.find((stage) => stage.is_current) ??
    runtime.stages[0]
  );
}

function getInspectedStage(runtime: ArchiveDocumentRuntimeContract, inspectedStageId: string | null) {
  if (inspectedStageId) {
    const inspectedStage = runtime.stages.find((stage) => stage.stage_id === inspectedStageId);
    if (inspectedStage) {
      return inspectedStage;
    }
  }
  return getLiveCurrentStage(runtime);
}

function isStageInspectable(stage: ArchiveDocumentRuntimeStageSnapshot, liveCurrentStage: ArchiveDocumentRuntimeStageSnapshot) {
  if (stage.stage_id === liveCurrentStage.stage_id) return true;
  if (stage.status !== "pending") return true;
  return stage.order < liveCurrentStage.order;
}

function getFlowNodeState(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  liveCurrentStage: ArchiveDocumentRuntimeStageSnapshot,
): FlowNodeState {
  if (stage.stage_id === liveCurrentStage.stage_id) return "current";
  if (stage.status !== "pending" || stage.order < liveCurrentStage.order) return "completed";
  return "pending";
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatPolicySnapshotHeadline(policySnapshot?: ArchivePolicyRuntimeSnapshot | null) {
  if (!policySnapshot) {
    return "未冻结策略快照";
  }
  return `${policySnapshot.version_label} · ${policySnapshot.scope_label}`;
}

function formatPolicySnapshotHint(policySnapshot?: ArchivePolicyRuntimeSnapshot | null) {
  if (!policySnapshot) {
    return "当前运行还没有携带策略快照";
  }
  const stageCount = policySnapshot.stages.length || policySnapshot.stage_order.length;
  return `冻结于 ${formatDateTime(policySnapshot.captured_at)} · ${stageCount} 个阶段 · ${policySnapshot.snapshot_id}`;
}

function formatPolicyActionLabel(action?: ArchivePolicyAction | null) {
  if (!action) return "未配置";
  return policyActionMeta[action]?.label ?? action;
}

function formatRuntimeRelationLabel(relation: string) {
  return runtimeRelationLabelMap[relation] ?? relation.split("_").join(" ");
}

function truncateGraphText(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 1))}…`;
}

function getStagePolicyConfig(
  policyConfig: ArchivePolicyConfig | null | undefined,
  stageId: string,
) {
  return policyConfig?.stages[stageId] ?? null;
}

function buildStagePolicyRuleDigest(stagePolicyConfig: ArchiveStagePolicyConfig | null | undefined, limit = 3) {
  if (!stagePolicyConfig || stagePolicyConfig.rules.length === 0) {
    return [];
  }
  return stagePolicyConfig.rules.slice(0, limit).map((rule) => ({
    key: rule.key,
    label: rule.name,
    meaning: rule.meaning,
    threshold: rule.threshold,
    actionLabel: formatPolicyActionLabel(rule.action),
  }));
}

function buildGraphEdgeDecisionLabel(
  edge: ArchiveDocumentRuntimeContract["stages"][number]["graph"]["edges"][number],
  sourceNode: ArchiveDocumentRuntimeGraphNode | undefined,
  targetNode: ArchiveDocumentRuntimeGraphNode | undefined,
  stagePolicyConfig: ArchiveStagePolicyConfig | null | undefined,
  primary: boolean,
) {
  const relationLabel = formatRuntimeRelationLabel(edge.relation);
  const edgeAttributes = edge.attributes ?? {};
  const targetAttributes = targetNode?.attributes ?? {};
  const sourceAttributes = sourceNode?.attributes ?? {};
  const ruleLabel =
    String(edgeAttributes.rule_label ?? targetAttributes.rule_label ?? sourceAttributes.rule_label ?? "").trim() ||
    String(edgeAttributes.rule_key ?? targetAttributes.rule_key ?? sourceAttributes.rule_key ?? "").trim();
  const reason =
    String(edgeAttributes.reason ?? targetAttributes.reason ?? sourceAttributes.reason ?? edgeAttributes.message ?? "").trim();
  const reviewStatus = String(edgeAttributes.review_status ?? targetAttributes.review_status ?? "").trim();
  const orderHint =
    edgeAttributes.section_order ?? edgeAttributes.paragraph_order ?? targetAttributes.section_order ?? targetAttributes.paragraph_order;
  const policyBasis = stagePolicyConfig?.rules[0]?.name ?? stagePolicyConfig?.ai_mode ?? "";
  const defaultActionLabel = formatPolicyActionLabel(stagePolicyConfig?.default_action ?? null);

  const basis = ruleLabel || reason || reviewStatus || (orderHint !== undefined ? `顺序 ${orderHint}` : "") || policyBasis;
  if (!primary && !ruleLabel && !reason && !reviewStatus) {
    return relationLabel;
  }

  const actionBasis = primary ? defaultActionLabel : relationLabel;
  return basis ? truncateGraphText(`${actionBasis} · ${basis}`, 30) : truncateGraphText(actionBasis, 24);
}

function buildPendingItems(archives: KnowledgeArchive[]): PendingItem[] {
  const items: PendingItem[] = [];
  archives.forEach((archive) => {
    if (archive.status === "error") {
      items.push({
        id: `${archive.archive_id}-blocked`,
        archiveId: archive.archive_id,
        title: `${archive.name} 已阻断`,
        severity: "critical",
        description: archive.last_error ?? "存在需要优先处理的阻断项",
      });
    }
    const warningCount = archive.build_state?.warning_count ?? 0;
    if (warningCount > 0) {
      items.push({
        id: `${archive.archive_id}-warning`,
        archiveId: archive.archive_id,
        title: `${archive.name} 待治理`,
        severity: "warning",
        description: `当前存在 ${warningCount} 条待治理告警`,
      });
    }
  });
  return items;
}

function getArchiveStageLabel(archive: KnowledgeArchive) {
  const buildState = archive.build_state;
  if (!buildState) return archiveStatusMeta[archive.status].label;
  if (buildState.failed_message) return "运行阻断";
  if (buildState.current_document_title) return `处理中：${buildState.current_document_title}`;
  if (buildState.pending_document_ids.length > 0) return `待处理 ${buildState.pending_document_ids.length} 篇`;
  if (archive.status === "ready") return "完成待治理";
  return archiveStatusMeta[archive.status].label;
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function estimateWrappedLineCount(text: string, maxCharsPerLine: number) {
  const normalized = Array.from(text.replace(/\s+/g, " ").trim());
  if (!normalized.length) return 1;
  return Math.max(1, Math.ceil(normalized.length / maxCharsPerLine));
}

function statusPriority(status: ArchiveDocumentRuntimeStatus) {
  if (status === "blocked") return 0;
  if (status === "running") return 1;
  if (status === "warning") return 2;
  if (status === "completed") return 3;
  if (status === "pending") return 4;
  return 5;
}

function buildRuntimeNodeLayouts(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const primaryNodeIds = new Set(
    stage.graph.primary_node_ids.length
      ? stage.graph.primary_node_ids
      : stage.graph.nodes.filter((node) => node.is_primary).map((node) => node.node_id),
  );

  return new Map(
    stage.graph.nodes.map((node) => {
      const primary = primaryNodeIds.has(node.node_id) || node.is_primary;
      const summary = summarizeRecord(node.metrics) ?? summarizeRecord(node.attributes);
      const labelLines = estimateWrappedLineCount(node.label, primary ? 11 : 10);
      const summaryLines = summary ? Math.min(primary ? 3 : 2, estimateWrappedLineCount(summary, primary ? 18 : 14)) : 0;
      const width = clampNumber(
        (primary ? 188 : 146) + Math.max(0, Array.from(node.label).length - (primary ? 10 : 8)) * (primary ? 4 : 3),
        primary ? 188 : 146,
        primary ? 268 : 214,
      );
      const height =
        (primary ? 76 : 54) +
        Math.max(0, labelLines - 1) * (primary ? 18 : 16) +
        summaryLines * (primary ? 15 : 13);

      return [
        node.node_id,
        {
          width,
          height,
          summary,
          primary,
        } satisfies RuntimeNodeLayout,
      ] as const;
    }),
  );
}

function buildStageAttachmentGroups(stage: ArchiveDocumentRuntimeStageSnapshot, primaryNodes: ArchiveDocumentRuntimeGraphNode[]) {
  const attachments = new Map<string, ArchiveDocumentRuntimeGraphNode[]>();
  primaryNodes.forEach((node) => {
    attachments.set(node.node_id, []);
  });

  if (!primaryNodes.length) {
    return attachments;
  }

  const primaryNodeIds = new Set(primaryNodes.map((node) => node.node_id));
  const anchorByNode = new Map(primaryNodes.map((node) => [node.node_id, node.node_id] as const));
  let unresolved = stage.graph.nodes.filter((node) => !primaryNodeIds.has(node.node_id));

  while (unresolved.length > 0) {
    let resolvedAny = false;
    unresolved = unresolved.filter((node) => {
      const directInbound = stage.graph.edges.find((edge) => edge.target === node.node_id && primaryNodeIds.has(edge.source));
      const directOutbound = stage.graph.edges.find((edge) => edge.source === node.node_id && primaryNodeIds.has(edge.target));
      const inheritedInbound = stage.graph.edges.find((edge) => edge.target === node.node_id && anchorByNode.has(edge.source));
      const inheritedOutbound = stage.graph.edges.find((edge) => edge.source === node.node_id && anchorByNode.has(edge.target));
      const inheritedAnchorId = inheritedInbound
        ? anchorByNode.get(inheritedInbound.source)
        : inheritedOutbound
          ? anchorByNode.get(inheritedOutbound.target)
          : null;
      const anchorId = directInbound?.source ?? directOutbound?.target ?? inheritedAnchorId ?? null;

      if (!anchorId) {
        return true;
      }

      anchorByNode.set(node.node_id, anchorId);
      const bucket = attachments.get(anchorId) ?? [];
      bucket.push(node);
      attachments.set(anchorId, bucket);
      resolvedAny = true;
      return false;
    });

    if (!resolvedAny) {
      unresolved.forEach((node, index) => {
        const anchorId = primaryNodes[index % primaryNodes.length]?.node_id;
        if (!anchorId) return;
        const bucket = attachments.get(anchorId) ?? [];
        bucket.push(node);
        attachments.set(anchorId, bucket);
      });
      break;
    }
  }

  attachments.forEach((nodes, anchorId) => {
    attachments.set(
      anchorId,
      [...nodes].sort((left, right) => {
        const priorityDelta = statusPriority(left.status) - statusPriority(right.status);
        if (priorityDelta !== 0) return priorityDelta;
        if (left.is_focus !== right.is_focus) return left.is_focus ? -1 : 1;
        return left.label.localeCompare(right.label, "zh-Hans-CN");
      }),
    );
  });

  return attachments;
}

function makeStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  width: number,
  height: number,
  nodeLayouts = buildRuntimeNodeLayouts(stage),
) {
  const positions = new Map<string, NodePosition>();
  const primaryNodes = getPrimaryGraphNodes(stage);

  if (!primaryNodes.length) {
    let fallbackX = 110;
    let fallbackY = 110;
    let rowHeight = 0;
    stage.graph.nodes.forEach((node) => {
      const layout = nodeLayouts.get(node.node_id) ?? { width: 180, height: 72, summary: null, primary: false };
      if (fallbackX + layout.width / 2 > width - 80) {
        fallbackX = 110;
        fallbackY += rowHeight + 28;
        rowHeight = 0;
      }
      positions.set(node.node_id, { x: fallbackX, y: fallbackY });
      fallbackX += layout.width + 42;
      rowHeight = Math.max(rowHeight, layout.height);
    });
    return positions;
  }

  const attachments = buildStageAttachmentGroups(stage, primaryNodes);
  const leftPad = 72;
  const rightPad = 72;
  const primaryGap = 92;
  const baseY = height / 2 + 8;
  const topPad = 34;
  const bottomPad = 34;
  const attachmentGap = 22;
  const primaryFootprints = primaryNodes.map((node) => {
    const primaryLayout = nodeLayouts.get(node.node_id) ?? { width: 188, height: 76, summary: null, primary: true };
    const attachmentWidth = Math.max(
      0,
      ...(attachments.get(node.node_id) ?? []).map((attachment) => nodeLayouts.get(attachment.node_id)?.width ?? 150),
    );
    return Math.max(primaryLayout.width, attachmentWidth) + 72;
  });

  const totalPrimaryWidth =
    primaryFootprints.reduce((sum, footprint) => sum + footprint, 0) + Math.max(0, primaryNodes.length - 1) * primaryGap;
  let cursorX = Math.max(leftPad, (width - totalPrimaryWidth) / 2);

  primaryNodes.forEach((node, index) => {
    const footprint = primaryFootprints[index];
    const primaryLayout = nodeLayouts.get(node.node_id) ?? { width: 188, height: 76, summary: null, primary: true };
    const centerX = cursorX + footprint / 2;
    positions.set(node.node_id, { x: centerX, y: baseY });
    cursorX += footprint + primaryGap;

    const relatedNodes = attachments.get(node.node_id) ?? [];
    const upperNodes = relatedNodes.filter((_relatedNode, relatedIndex) => relatedIndex % 2 === 0);
    const lowerNodes = relatedNodes.filter((_relatedNode, relatedIndex) => relatedIndex % 2 === 1);

    const placeStack = (nodes: ArchiveDocumentRuntimeGraphNode[], direction: "up" | "down") => {
      if (!nodes.length) return;
      const totalHeight =
        nodes.reduce((sum, relatedNode) => sum + (nodeLayouts.get(relatedNode.node_id)?.height ?? 64), 0) +
        Math.max(0, nodes.length - 1) * attachmentGap;

      let currentTop =
        direction === "up"
          ? Math.max(topPad, baseY - primaryLayout.height / 2 - 36 - totalHeight)
          : Math.min(height - bottomPad - totalHeight, baseY + primaryLayout.height / 2 + 36);

      nodes.forEach((relatedNode, stackIndex) => {
        const layout = nodeLayouts.get(relatedNode.node_id) ?? { width: 150, height: 64, summary: null, primary: false };
        const xShift = nodes.length > 1 ? (stackIndex % 2 === 0 ? -22 : 22) : 0;
        positions.set(relatedNode.node_id, {
          x: centerX + xShift,
          y: currentTop + layout.height / 2,
        });
        currentTop += layout.height + attachmentGap;
      });
    };

    placeStack(upperNodes, "up");
    placeStack(lowerNodes, "down");
  });

  stage.graph.nodes.forEach((node, index) => {
    if (!positions.has(node.node_id)) {
      const layout = nodeLayouts.get(node.node_id) ?? { width: 150, height: 64, summary: null, primary: false };
      positions.set(node.node_id, {
        x: 110 + (index % 4) * (layout.width + 32),
        y: 110 + Math.floor(index / 4) * (layout.height + 28),
      });
    }
  });

  return positions;
}

function chunkItems<T>(items: T[], size: number) {
  if (size <= 0) return [items];
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

function buildUndirectedStageAdjacency(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const adjacency = new Map<string, Set<string>>();
  stage.graph.nodes.forEach((node) => {
    adjacency.set(node.node_id, new Set<string>());
  });
  stage.graph.edges.forEach((edge) => {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  });
  return adjacency;
}

function buildDirectedStageAdjacency(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const outgoing = new Map<string, Set<string>>();
  const incoming = new Map<string, Set<string>>();
  stage.graph.nodes.forEach((node) => {
    outgoing.set(node.node_id, new Set<string>());
    incoming.set(node.node_id, new Set<string>());
  });
  stage.graph.edges.forEach((edge) => {
    outgoing.get(edge.source)?.add(edge.target);
    incoming.get(edge.target)?.add(edge.source);
  });
  return { outgoing, incoming };
}

function buildOrderedPrimaryGraphNodes(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const primaryNodes = getPrimaryGraphNodes(stage);
  if (primaryNodes.length <= 1) {
    return primaryNodes;
  }

  const primaryNodeIds = new Set(primaryNodes.map((node) => node.node_id));
  const indegree = new Map(primaryNodes.map((node) => [node.node_id, 0]));
  const outgoing = new Map(primaryNodes.map((node) => [node.node_id, [] as string[]]));

  stage.graph.edges.forEach((edge) => {
    if (!primaryNodeIds.has(edge.source) || !primaryNodeIds.has(edge.target)) {
      return;
    }
    outgoing.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  });

  const queue = primaryNodes.filter((node) => (indegree.get(node.node_id) ?? 0) === 0);
  const ordered: ArchiveDocumentRuntimeGraphNode[] = [];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || visited.has(current.node_id)) continue;
    visited.add(current.node_id);
    ordered.push(current);
    (outgoing.get(current.node_id) ?? []).forEach((targetId) => {
      const nextDegree = (indegree.get(targetId) ?? 0) - 1;
      indegree.set(targetId, nextDegree);
      if (nextDegree <= 0) {
        const nextNode = primaryNodes.find((node) => node.node_id === targetId);
        if (nextNode && !visited.has(nextNode.node_id)) {
          queue.push(nextNode);
        }
      }
    });
  }

  primaryNodes.forEach((node) => {
    if (!visited.has(node.node_id)) {
      ordered.push(node);
    }
  });

  return ordered;
}

function buildStageAnchorDistanceMap(
  primaryNodes: ArchiveDocumentRuntimeGraphNode[],
  neighborMap: Map<string, Set<string>>,
) {
  const queue = primaryNodes.map((node, index) => ({
    nodeId: node.node_id,
    anchorId: node.node_id,
    distance: 0,
    priority: index,
  }));
  const anchorByNode = new Map<string, { anchorId: string; distance: number; priority: number }>();

  queue.forEach((entry) => {
    anchorByNode.set(entry.nodeId, { anchorId: entry.anchorId, distance: 0, priority: entry.priority });
  });

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) continue;
    neighborMap.get(current.nodeId)?.forEach((neighborId) => {
      const nextDistance = current.distance + 1;
      const existing = anchorByNode.get(neighborId);
      if (
        existing &&
        (existing.distance < nextDistance ||
          (existing.distance === nextDistance && existing.priority <= current.priority))
      ) {
        return;
      }
      anchorByNode.set(neighborId, {
        anchorId: current.anchorId,
        distance: nextDistance,
        priority: current.priority,
      });
      queue.push({
        nodeId: neighborId,
        anchorId: current.anchorId,
        distance: nextDistance,
        priority: current.priority,
      });
    });
  }

  return anchorByNode;
}

function isPolicySupportNode(node: ArchiveDocumentRuntimeGraphNode) {
  const nodeType = node.node_type.toLowerCase();
  if (
    nodeType.includes("warning") ||
    nodeType.includes("rule_hit") ||
    nodeType.includes("manual_review") ||
    nodeType.includes("boundary_adjustment") ||
    nodeType.includes("parser_candidate")
  ) {
    return true;
  }
  return "rule_key" in node.attributes;
}

function buildStageRoleLayoutPlan(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const primaryNodes = buildOrderedPrimaryGraphNodes(stage);
  const { outgoing, incoming } = buildDirectedStageAdjacency(stage);
  const upstreamAnchors = buildStageAnchorDistanceMap(primaryNodes, incoming);
  const downstreamAnchors = buildStageAnchorDistanceMap(primaryNodes, outgoing);
  const buckets = new Map<string, StageRoleLayoutBuckets>(
    primaryNodes.map((node) => [
      node.node_id,
      {
        inputs: [],
        policies: [],
        outputs: [],
      },
    ]),
  );
  const roleByNode = new Map<string, StageNodeRole>();
  const anchorByNode = new Map<string, string>();

  stage.graph.nodes.forEach((node) => {
    if (node.is_primary || primaryNodes.some((primaryNode) => primaryNode.node_id === node.node_id)) {
      return;
    }
    const upstreamAnchor = upstreamAnchors.get(node.node_id);
    const downstreamAnchor = downstreamAnchors.get(node.node_id);
    const role: StageNodeRole = isPolicySupportNode(node)
      ? "policy"
      : upstreamAnchor && (!downstreamAnchor || upstreamAnchor.distance <= downstreamAnchor.distance)
        ? "input"
        : "output";
    const anchorId =
      role === "input"
        ? upstreamAnchor?.anchorId ?? downstreamAnchor?.anchorId ?? primaryNodes[0]?.node_id
        : downstreamAnchor?.anchorId ?? upstreamAnchor?.anchorId ?? primaryNodes[0]?.node_id;
    if (!anchorId) {
      return;
    }
    roleByNode.set(node.node_id, role);
    anchorByNode.set(node.node_id, anchorId);
    const anchorBuckets = buckets.get(anchorId);
    if (!anchorBuckets) {
      return;
    }
    if (role === "input") {
      anchorBuckets.inputs.push(node);
    } else if (role === "policy") {
      anchorBuckets.policies.push(node);
    } else {
      anchorBuckets.outputs.push(node);
    }
  });

  const sortNodes = (nodes: ArchiveDocumentRuntimeGraphNode[], anchorMap: Map<string, { distance: number }>) =>
    [...nodes].sort((left, right) => {
      const distanceDelta = (anchorMap.get(left.node_id)?.distance ?? 99) - (anchorMap.get(right.node_id)?.distance ?? 99);
      if (distanceDelta !== 0) return distanceDelta;
      const priorityDelta = statusPriority(left.status) - statusPriority(right.status);
      if (priorityDelta !== 0) return priorityDelta;
      return left.label.localeCompare(right.label, "zh-Hans-CN");
    });

  buckets.forEach((value, anchorId) => {
    value.inputs = sortNodes(value.inputs, upstreamAnchors).map((node) => ({ ...node }));
    value.policies = sortNodes(value.policies, downstreamAnchors).map((node) => ({ ...node }));
    value.outputs = sortNodes(value.outputs, downstreamAnchors).map((node) => ({ ...node }));
    buckets.set(anchorId, value);
  });

  return {
    primaryNodes,
    buckets,
    roleByNode,
    anchorByNode,
  };
}

function buildAnchorDistanceIndex(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  anchorId: string,
  allowedNodeIds: Set<string>,
) {
  const adjacency = buildUndirectedStageAdjacency(stage);
  const distanceById = new Map<string, number>([[anchorId, 0]]);
  const queue = [anchorId];

  while (queue.length > 0) {
    const currentId = queue.shift();
    if (!currentId) continue;
    const currentDistance = distanceById.get(currentId) ?? 0;
    adjacency.get(currentId)?.forEach((neighborId) => {
      if (!allowedNodeIds.has(neighborId) && neighborId !== anchorId) return;
      if (distanceById.has(neighborId)) return;
      distanceById.set(neighborId, currentDistance + 1);
      queue.push(neighborId);
    });
  }

  return distanceById;
}

function resolveStagePositionCollisions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const primaryNodeIds = new Set(
    stage.graph.primary_node_ids.length
      ? stage.graph.primary_node_ids
      : stage.graph.nodes.filter((node) => node.is_primary).map((node) => node.node_id),
  );
  const nextPositions = new Map<string, NodePosition>(
    [...positions.entries()].map(([nodeId, position]) => [nodeId, { ...position }]),
  );
  const minGapX = 34;
  const minGapY = 28;

  for (let iteration = 0; iteration < 40; iteration += 1) {
    let moved = false;

    for (let leftIndex = 0; leftIndex < stage.graph.nodes.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < stage.graph.nodes.length; rightIndex += 1) {
        const leftNode = stage.graph.nodes[leftIndex];
        const rightNode = stage.graph.nodes[rightIndex];
        const leftPosition = nextPositions.get(leftNode.node_id);
        const rightPosition = nextPositions.get(rightNode.node_id);
        if (!leftPosition || !rightPosition) continue;

        const leftLayout = nodeLayouts.get(leftNode.node_id) ?? { width: 180, height: 72, summary: null, primary: false };
        const rightLayout = nodeLayouts.get(rightNode.node_id) ?? { width: 180, height: 72, summary: null, primary: false };
        const overlapX =
          Math.min(leftPosition.x + leftLayout.width / 2, rightPosition.x + rightLayout.width / 2) -
          Math.max(leftPosition.x - leftLayout.width / 2, rightPosition.x - rightLayout.width / 2);
        const overlapY =
          Math.min(leftPosition.y + leftLayout.height / 2, rightPosition.y + rightLayout.height / 2) -
          Math.max(leftPosition.y - leftLayout.height / 2, rightPosition.y - rightLayout.height / 2);

        if (overlapX <= -minGapX || overlapY <= -minGapY) {
          continue;
        }

        const pushAlongX = overlapX + minGapX;
        const pushAlongY = overlapY + minGapY;
        const moveAxis = pushAlongX < pushAlongY ? "x" : "y";
        const leftIsPrimary = primaryNodeIds.has(leftNode.node_id);
        const rightIsPrimary = primaryNodeIds.has(rightNode.node_id);
        if (leftIsPrimary && rightIsPrimary) {
          continue;
        }

        const direction =
          moveAxis === "x"
            ? Math.sign(rightPosition.x - leftPosition.x) || 1
            : Math.sign(rightPosition.y - leftPosition.y) || 1;
        const push = (moveAxis === "x" ? pushAlongX : pushAlongY) / (leftIsPrimary || rightIsPrimary ? 1 : 2);

        if (moveAxis === "x") {
          if (!leftIsPrimary) {
            leftPosition.x -= direction * push;
          }
          if (!rightIsPrimary) {
            rightPosition.x += direction * push;
          }
        } else {
          if (!leftIsPrimary) {
            leftPosition.y -= direction * push;
          }
          if (!rightIsPrimary) {
            rightPosition.y += direction * push;
          }
        }

        moved = true;
      }
    }

    if (!moved) {
      break;
    }
  }

  return nextPositions;
}

function getStageLayoutRootIds(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  primaryNodes: ArchiveDocumentRuntimeGraphNode[],
) {
  const primaryNodeIds = new Set(primaryNodes.map((node) => node.node_id));
  const primaryRoots = primaryNodes
    .filter(
      (node) =>
        !stage.graph.edges.some((edge) => edge.target === node.node_id && primaryNodeIds.has(edge.source)),
    )
    .map((node) => node.node_id);
  if (primaryRoots.length > 0) {
    return primaryRoots;
  }

  const inboundCount = new Map(stage.graph.nodes.map((node) => [node.node_id, 0]));
  stage.graph.edges.forEach((edge) => {
    inboundCount.set(edge.target, (inboundCount.get(edge.target) ?? 0) + 1);
  });

  const zeroInbound = stage.graph.nodes
    .filter((node) => (inboundCount.get(node.node_id) ?? 0) === 0)
    .map((node) => node.node_id);
  return zeroInbound.length > 0 ? zeroInbound : stage.graph.nodes.slice(0, 1).map((node) => node.node_id);
}

function normalizeStageLayoutPositions(
  rawPositions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  if (rawPositions.size === 0) {
    return new Map<string, NodePosition>();
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;

  rawPositions.forEach((position, nodeId) => {
    const layout = nodeLayouts.get(nodeId) ?? { width: 180, height: 72, summary: null, primary: false };
    minX = Math.min(minX, position.x - layout.width / 2);
    minY = Math.min(minY, position.y - layout.height / 2);
  });

  const offsetX = 160 - minX;
  const offsetY = 160 - minY;
  return new Map(
    [...rawPositions.entries()].map(([nodeId, position]) => [
      nodeId,
      {
        x: position.x + offsetX,
        y: position.y + offsetY,
      },
    ]),
  );
}

function enforcePrimaryNodeSpacing(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  minGap = 160,
) {
  const primaryNodes = getPrimaryGraphNodes(stage);
  if (primaryNodes.length <= 1) {
    return positions;
  }

  const nextPositions = new Map<string, NodePosition>(
    [...positions.entries()].map(([nodeId, position]) => [nodeId, { ...position }]),
  );
  const orderedPrimaryNodes = primaryNodes.filter((node) => nextPositions.has(node.node_id));
  const primaryY =
    orderedPrimaryNodes.reduce((sum, node) => sum + (nextPositions.get(node.node_id)?.y ?? 0), 0) /
    Math.max(orderedPrimaryNodes.length, 1);

  orderedPrimaryNodes.forEach((node) => {
    const position = nextPositions.get(node.node_id);
    if (position) {
      position.y = primaryY;
    }
  });

  for (let index = 1; index < orderedPrimaryNodes.length; index += 1) {
    const leftNode = orderedPrimaryNodes[index - 1];
    const rightNode = orderedPrimaryNodes[index];
    const leftPosition = nextPositions.get(leftNode.node_id);
    const rightPosition = nextPositions.get(rightNode.node_id);
    if (!leftPosition || !rightPosition) continue;

    const leftLayout = nodeLayouts.get(leftNode.node_id) ?? { width: 188, height: 76, summary: null, primary: true };
    const rightLayout = nodeLayouts.get(rightNode.node_id) ?? { width: 188, height: 76, summary: null, primary: true };
    const currentGap = rightPosition.x - leftPosition.x - (leftLayout.width / 2 + rightLayout.width / 2);
    if (currentGap >= minGap) {
      continue;
    }

    const delta = minGap - currentGap;
    nextPositions.forEach((position) => {
      if (position.x >= rightPosition.x - 1) {
        position.x += delta;
      }
    });
  }

  return nextPositions;
}

function buildCytoscapeStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const primaryNodes = getPrimaryGraphNodes(stage);
  const useBreadthfirst = primaryNodes.length > 1 || stage.graph.nodes.length > 18;
  const cy = cytoscape({
    headless: true,
    elements: [
      ...stage.graph.nodes.map((node) => {
        const layout = nodeLayouts.get(node.node_id) ?? { width: 180, height: 72, summary: null, primary: false };
        return {
          data: {
            id: node.node_id,
            width: layout.width,
            height: layout.height,
          },
        };
      }),
      ...stage.graph.edges.map((edge) => ({
        data: {
          id: edge.edge_id,
          source: edge.source,
          target: edge.target,
        },
      })),
    ],
    style: [
      {
        selector: "node",
        style: {
          width: "data(width)",
          height: "data(height)",
        },
      },
    ],
  });

  const layoutOptions = useBreadthfirst
    ? ({
        name: "breadthfirst",
        fit: false,
        padding: 80,
        animate: false,
        directed: true,
        avoidOverlap: true,
        nodeDimensionsIncludeLabels: true,
        spacingFactor: stage.graph.nodes.length > 120 ? 2.4 : 2,
        roots: getStageLayoutRootIds(stage, primaryNodes),
      } as cytoscape.LayoutOptions)
    : ({
        name: "cose",
        fit: false,
        padding: 80,
        animate: false,
        randomize: true,
        componentSpacing: 160,
        nodeOverlap: 48,
        nodeRepulsion: stage.graph.nodes.length > 120 ? 260000 : 180000,
        idealEdgeLength: stage.graph.nodes.length > 120 ? 220 : 180,
      } as cytoscape.LayoutOptions);

  cy.layout(layoutOptions).run();

  const rawPositions = new Map<string, NodePosition>();
  cy.nodes().forEach((node) => {
    const position = node.position();
    rawPositions.set(node.id(), useBreadthfirst ? { x: position.y, y: position.x } : position);
  });
  cy.destroy();

  return normalizeStageLayoutPositions(rawPositions, nodeLayouts);
}

function measureRoleColumnsWidth(
  columns: ArchiveDocumentRuntimeGraphNode[][],
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  gap: number,
) {
  if (!columns.length) return 0;
  return (
    columns.reduce(
      (sum, column) =>
        sum + Math.max(...column.map((node) => nodeLayouts.get(node.node_id)?.width ?? 160), 0),
      0,
    ) +
    Math.max(0, columns.length - 1) * gap
  );
}

function measureRoleRowsWidth(
  rows: ArchiveDocumentRuntimeGraphNode[][],
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  gap: number,
) {
  return Math.max(
    0,
    ...rows.map(
      (row) =>
        row.reduce((sum, node) => sum + (nodeLayouts.get(node.node_id)?.width ?? 160), 0) +
        Math.max(0, row.length - 1) * gap,
    ),
  );
}

function getRuntimeNodeLayout(
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  nodeId: string,
  primary = false,
): RuntimeNodeLayout {
  return nodeLayouts.get(nodeId) ?? {
    width: primary ? 188 : 160,
    height: primary ? 76 : 64,
    summary: null,
    primary,
  };
}

function getStageNodeOrder(node: ArchiveDocumentRuntimeGraphNode) {
  const numericKeys = ["section_order", "paragraph_order", "chunk_index", "segment_index", "rank"];
  for (const key of numericKeys) {
    const value = node.attributes[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }
  const trailingMatch = node.node_id.match(/(\d+)(?!.*\d)/);
  return trailingMatch ? Number(trailingMatch[1]) : Number.POSITIVE_INFINITY;
}

function sortStageNodesForLayout(nodes: ArchiveDocumentRuntimeGraphNode[]) {
  return [...nodes].sort((left, right) => {
    const orderDelta = getStageNodeOrder(left) - getStageNodeOrder(right);
    if (orderDelta !== 0) return orderDelta;
    const statusDelta = statusPriority(left.status) - statusPriority(right.status);
    if (statusDelta !== 0) return statusDelta;
    return left.label.localeCompare(right.label, "zh-Hans-CN");
  });
}

function placeNodeColumns(
  positions: Map<string, NodePosition>,
  columns: ArchiveDocumentRuntimeGraphNode[][],
  startX: number,
  topY: number,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  columnGap = 32,
  rowGap = 24,
) {
  let cursorX = startX;
  let maxBottom = topY;

  columns.forEach((column) => {
    if (!column.length) return;
    const columnWidth = Math.max(...column.map((node) => getRuntimeNodeLayout(nodeLayouts, node.node_id).width));
    let cursorY = topY;

    column.forEach((node) => {
      const layout = getRuntimeNodeLayout(nodeLayouts, node.node_id, node.is_primary);
      positions.set(node.node_id, {
        x: cursorX + columnWidth / 2,
        y: cursorY + layout.height / 2,
      });
      cursorY += layout.height + rowGap;
    });

    maxBottom = Math.max(maxBottom, cursorY - rowGap);
    cursorX += columnWidth + columnGap;
  });

  return {
    rightX: cursorX - columnGap,
    bottomY: maxBottom,
  };
}

function placeUnassignedStageNodes(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  let maxPlacedX = 220;
  let minPlacedY = Number.POSITIVE_INFINITY;

  positions.forEach((position, nodeId) => {
    const layout = getRuntimeNodeLayout(nodeLayouts, nodeId);
    maxPlacedX = Math.max(maxPlacedX, position.x + layout.width / 2);
    minPlacedY = Math.min(minPlacedY, position.y - layout.height / 2);
  });

  let fallbackX = maxPlacedX + 120;
  let fallbackY = Number.isFinite(minPlacedY) ? Math.max(140, minPlacedY) : 220;
  let rowHeight = 0;

  stage.graph.nodes.forEach((node) => {
    if (positions.has(node.node_id)) return;
    const layout = getRuntimeNodeLayout(nodeLayouts, node.node_id, node.is_primary);
    if (fallbackX + layout.width > maxPlacedX + 780) {
      fallbackX = maxPlacedX + 120;
      fallbackY += rowHeight + 36;
      rowHeight = 0;
    }
    positions.set(node.node_id, {
      x: fallbackX + layout.width / 2,
      y: fallbackY + layout.height / 2,
    });
    fallbackX += layout.width + 44;
    rowHeight = Math.max(rowHeight, layout.height);
  });
}

function buildStageNodeTypeMap(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const typeMap = new Map<string, ArchiveDocumentRuntimeGraphNode[]>();
  stage.graph.nodes.forEach((node) => {
    const nodes = typeMap.get(node.node_type) ?? [];
    nodes.push(node);
    typeMap.set(node.node_type, nodes);
  });
  return typeMap;
}

function buildUnifiedDocumentStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const positions = new Map<string, NodePosition>();
  const typeMap = buildStageNodeTypeMap(stage);
  const decisionNode = typeMap.get("normalization_decision")?.[0] ?? null;
  const documentNode = typeMap.get("unified_document")?.[0] ?? null;
  const sectionGroupNode = typeMap.get("unified_section_group")?.[0] ?? null;
  const paragraphGroupNode = typeMap.get("unified_paragraph_group")?.[0] ?? null;
  const warningNodes = sortStageNodesForLayout(typeMap.get("normalization_warning") ?? []);
  const sectionNodes = sortStageNodesForLayout(typeMap.get("unified_section") ?? []);
  const paragraphNodes = sortStageNodesForLayout(typeMap.get("unified_paragraph") ?? []);

  if (decisionNode) positions.set(decisionNode.node_id, { x: 260, y: 420 });
  if (documentNode) positions.set(documentNode.node_id, { x: 620, y: 420 });
  if (sectionGroupNode) positions.set(sectionGroupNode.node_id, { x: 980, y: 220 });
  if (paragraphGroupNode) positions.set(paragraphGroupNode.node_id, { x: 980, y: 560 });

  if (warningNodes.length) {
    const totalWidth =
      warningNodes.reduce((sum, node) => sum + getRuntimeNodeLayout(nodeLayouts, node.node_id).width, 0) +
      Math.max(0, warningNodes.length - 1) * 24;
    let cursorX = 620 - totalWidth / 2;
    warningNodes.forEach((node) => {
      const layout = getRuntimeNodeLayout(nodeLayouts, node.node_id);
      positions.set(node.node_id, { x: cursorX + layout.width / 2, y: 110 });
      cursorX += layout.width + 24;
    });
  }

  const paragraphsBySection = new Map<string, ArchiveDocumentRuntimeGraphNode[]>();
  paragraphNodes.forEach((node) => {
    const sectionLabel = String(node.attributes.section_label ?? "__orphan__");
    const nodes = paragraphsBySection.get(sectionLabel) ?? [];
    nodes.push(node);
    paragraphsBySection.set(sectionLabel, nodes);
  });

  const sectionsPerRow = 3;
  const laneWidth = 380;
  const laneGap = 56;
  const rowGap = 120;
  const paragraphsPerColumn = 7;
  let rowTopY = 180;

  chunkItems(sectionNodes, sectionsPerRow).forEach((sectionRow) => {
    let rowBottom = rowTopY;
    sectionRow.forEach((sectionNode, index) => {
      const laneLeftX = 1220 + index * (laneWidth + laneGap);
      const laneCenterX = laneLeftX + laneWidth / 2;
      const sectionLayout = getRuntimeNodeLayout(nodeLayouts, sectionNode.node_id);
      positions.set(sectionNode.node_id, {
        x: laneCenterX,
        y: rowTopY + sectionLayout.height / 2,
      });

      const sectionParagraphs = sortStageNodesForLayout(
        paragraphsBySection.get(String(sectionNode.attributes.section_label ?? sectionNode.label)) ?? [],
      );
      const paragraphColumns = chunkItems(sectionParagraphs, paragraphsPerColumn);
      const columnsWidth = measureRoleColumnsWidth(paragraphColumns, nodeLayouts, 24);
      const paragraphTop = rowTopY + sectionLayout.height + 40;
      const columnStartX = laneLeftX + Math.max((laneWidth - columnsWidth) / 2, 0);
      const paragraphPlacement = placeNodeColumns(
        positions,
        paragraphColumns,
        columnStartX,
        paragraphTop,
        nodeLayouts,
        24,
        20,
      );
      rowBottom = Math.max(rowBottom, paragraphPlacement.bottomY);
    });
    rowTopY = rowBottom + rowGap;
  });

  placeUnassignedStageNodes(stage, positions, nodeLayouts);
  return positions;
}

function buildEvidenceConstructorStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const positions = new Map<string, NodePosition>();
  const typeMap = buildStageNodeTypeMap(stage);
  const taskNode = typeMap.get("evidence_constructor_task")?.[0] ?? null;
  const paragraphGroupNode = typeMap.get("source_paragraph_group")?.[0] ?? null;
  const unitGroupNode = typeMap.get("evidence_unit_group")?.[0] ?? null;
  const anchorGroupNode = typeMap.get("evidence_anchor_group")?.[0] ?? null;
  const spanGroupNode = typeMap.get("evidence_span_group")?.[0] ?? null;
  const paragraphNodes = sortStageNodesForLayout(typeMap.get("source_paragraph") ?? []);
  const unitNodes = sortStageNodesForLayout(typeMap.get("evidence_unit") ?? []);
  const anchorNodes = sortStageNodesForLayout(typeMap.get("evidence_anchor") ?? []);
  const spanNodes = sortStageNodesForLayout(typeMap.get("evidence_span") ?? []);
  const warningNodes = sortStageNodesForLayout(typeMap.get("evidence_warning") ?? []);

  if (paragraphGroupNode) positions.set(paragraphGroupNode.node_id, { x: 220, y: 520 });
  if (taskNode) positions.set(taskNode.node_id, { x: 620, y: 520 });
  if (unitGroupNode) positions.set(unitGroupNode.node_id, { x: 980, y: 520 });
  if (anchorGroupNode) positions.set(anchorGroupNode.node_id, { x: 1200, y: 170 });
  if (spanGroupNode) positions.set(spanGroupNode.node_id, { x: 1200, y: 870 });

  placeNodeColumns(positions, chunkItems(paragraphNodes, 6), 20, 260, nodeLayouts, 28, 22);
  placeNodeColumns(positions, chunkItems(unitNodes, 5), 1180, 300, nodeLayouts, 28, 22);
  placeNodeColumns(positions, chunkItems(anchorNodes, 4), 1180, 30, nodeLayouts, 24, 18);
  placeNodeColumns(positions, chunkItems(spanNodes, 4), 1180, 940, nodeLayouts, 24, 18);

  if (warningNodes.length) {
    const warningStartX = 540;
    placeNodeColumns(positions, [warningNodes], warningStartX, 90, nodeLayouts, 24, 20);
  }

  placeUnassignedStageNodes(stage, positions, nodeLayouts);
  return positions;
}

function buildEvidenceGraphChunkLayerStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const positions = new Map<string, NodePosition>();
  const typeMap = buildStageNodeTypeMap(stage);
  const evidenceGroupNode = typeMap.get("evidence_unit_group")?.[0] ?? null;
  const planningNode = typeMap.get("chunk_planning_task")?.[0] ?? null;
  const chunkGroupNode = typeMap.get("chunk_group")?.[0] ?? null;
  const graphLayerNode = typeMap.get("evidence_graph_layer")?.[0] ?? null;
  const adjustmentGroupNode = typeMap.get("boundary_adjustment_group")?.[0] ?? null;
  const evidenceNodes = sortStageNodesForLayout(typeMap.get("evidence_unit") ?? []);
  const chunkNodes = sortStageNodesForLayout(typeMap.get("chunk") ?? []);
  const adjustmentNodes = sortStageNodesForLayout(typeMap.get("boundary_adjustment") ?? []);
  const warningNodes = sortStageNodesForLayout(typeMap.get("chunk_warning") ?? []);

  if (evidenceGroupNode) positions.set(evidenceGroupNode.node_id, { x: 220, y: 520 });
  if (planningNode) positions.set(planningNode.node_id, { x: 620, y: 520 });
  if (chunkGroupNode) positions.set(chunkGroupNode.node_id, { x: 980, y: 520 });
  if (graphLayerNode) positions.set(graphLayerNode.node_id, { x: 1600, y: 520 });
  if (adjustmentGroupNode) positions.set(adjustmentGroupNode.node_id, { x: 980, y: 180 });

  placeNodeColumns(positions, chunkItems(evidenceNodes, 6), 20, 260, nodeLayouts, 28, 22);
  placeNodeColumns(positions, chunkItems(chunkNodes, 5), 1220, 300, nodeLayouts, 28, 22);
  placeNodeColumns(positions, chunkItems(adjustmentNodes, 4), 1220, 40, nodeLayouts, 24, 18);

  if (warningNodes.length) {
    placeNodeColumns(positions, [warningNodes], 520, 90, nodeLayouts, 24, 18);
  }

  placeUnassignedStageNodes(stage, positions, nodeLayouts);
  return positions;
}

function buildQualityGateStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const positions = new Map<string, NodePosition>();
  const typeMap = buildStageNodeTypeMap(stage);
  const ruleHitNode = typeMap.get("rule_hit")?.[0] ?? null;
  const gateNode = typeMap.get("gate_decision")?.[0] ?? null;
  const manualReviewNode = typeMap.get("manual_review")?.[0] ?? null;
  const blockedNode = typeMap.get("blocked_result")?.[0] ?? null;
  const publishTargetNode = typeMap.get("publish_target")?.[0] ?? null;
  const candidateNodes = sortStageNodesForLayout(
    stage.graph.nodes.filter((node) => node.node_type.startsWith("canonical_")),
  );
  const approvedNodes = candidateNodes.filter((node) => node.attributes.review_status === "approved");
  const pendingNodes = candidateNodes.filter((node) => node.attributes.review_status === "pending");
  const rejectedNodes = candidateNodes.filter((node) => node.attributes.review_status === "rejected");
  const remainingNodes = candidateNodes.filter(
    (node) =>
      node.attributes.review_status !== "approved" &&
      node.attributes.review_status !== "pending" &&
      node.attributes.review_status !== "rejected",
  );

  if (ruleHitNode) positions.set(ruleHitNode.node_id, { x: 700, y: 520 });
  if (gateNode) positions.set(gateNode.node_id, { x: 1040, y: 520 });
  if (manualReviewNode) positions.set(manualReviewNode.node_id, { x: 1420, y: 280 });
  if (blockedNode) positions.set(blockedNode.node_id, { x: 1420, y: 620 });
  if (publishTargetNode) positions.set(publishTargetNode.node_id, { x: 1420, y: 620 });

  placeNodeColumns(positions, chunkItems(approvedNodes, 5), 20, 120, nodeLayouts, 26, 18);
  placeNodeColumns(positions, chunkItems(pendingNodes, 5), 20, 400, nodeLayouts, 26, 18);
  placeNodeColumns(positions, chunkItems(rejectedNodes, 5), 20, 720, nodeLayouts, 26, 18);
  if (remainingNodes.length) {
    placeNodeColumns(positions, chunkItems(remainingNodes, 5), 360, 400, nodeLayouts, 24, 18);
  }

  placeUnassignedStageNodes(stage, positions, nodeLayouts);
  return positions;
}

function buildGenericStageTransformationPositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  const layoutPlan = buildStageRoleLayoutPlan(stage);
  if (!layoutPlan.primaryNodes.length) {
    return makeStagePositions(stage, 1440, 920, nodeLayouts);
  }

  const positions = new Map<string, NodePosition>();
  const centerY = 480;
  const sideGap = 72;
  const columnGap = 28;
  const stackGap = 24;
  const policyGapY = 104;
  const primaryGap = 180;
  const minZoneWidth = 420;

  const anchorSpecs = layoutPlan.primaryNodes.map((primaryNode) => {
    const primaryLayout = nodeLayouts.get(primaryNode.node_id) ?? { width: 188, height: 76, summary: null, primary: true };
    const anchorBuckets = layoutPlan.buckets.get(primaryNode.node_id) ?? {
      inputs: [],
      policies: [],
      outputs: [],
    };
    const inputColumns = chunkItems(anchorBuckets.inputs, 4);
    const outputColumns = chunkItems(anchorBuckets.outputs, 4);
    const policyRows = chunkItems(anchorBuckets.policies, 3);
    const leftWidth = measureRoleColumnsWidth(inputColumns, nodeLayouts, columnGap);
    const rightWidth = measureRoleColumnsWidth(outputColumns, nodeLayouts, columnGap);
    const policyWidth = measureRoleRowsWidth(policyRows, nodeLayouts, columnGap);
    const zoneWidth = Math.max(
      minZoneWidth,
      leftWidth + rightWidth + primaryLayout.width + sideGap * 2 + 80,
      policyWidth + 80,
    );

    return {
      primaryNode,
      primaryLayout,
      anchorBuckets,
      inputColumns,
      outputColumns,
      policyRows,
      leftWidth,
      rightWidth,
      zoneWidth,
    };
  });

  let cursorX = 180;
  anchorSpecs.forEach((spec) => {
    const centerX = cursorX + spec.leftWidth + sideGap + spec.primaryLayout.width / 2;
    positions.set(spec.primaryNode.node_id, { x: centerX, y: centerY });

    let inputBoundaryX = centerX - spec.primaryLayout.width / 2 - sideGap;
    spec.inputColumns.forEach((column) => {
      const columnWidth = Math.max(...column.map((node) => nodeLayouts.get(node.node_id)?.width ?? 160), 0);
      const columnHeight =
        column.reduce((sum, node) => sum + (nodeLayouts.get(node.node_id)?.height ?? 64), 0) +
        Math.max(0, column.length - 1) * stackGap;
      const columnX = inputBoundaryX - columnWidth / 2;
      let columnY = centerY - columnHeight / 2;
      column.forEach((node) => {
        const layout = nodeLayouts.get(node.node_id) ?? { width: 160, height: 64, summary: null, primary: false };
        positions.set(node.node_id, {
          x: columnX,
          y: columnY + layout.height / 2,
        });
        columnY += layout.height + stackGap;
      });
      inputBoundaryX -= columnWidth + columnGap;
    });

    let outputBoundaryX = centerX + spec.primaryLayout.width / 2 + sideGap;
    spec.outputColumns.forEach((column) => {
      const columnWidth = Math.max(...column.map((node) => nodeLayouts.get(node.node_id)?.width ?? 160), 0);
      const columnHeight =
        column.reduce((sum, node) => sum + (nodeLayouts.get(node.node_id)?.height ?? 64), 0) +
        Math.max(0, column.length - 1) * stackGap;
      const columnX = outputBoundaryX + columnWidth / 2;
      let columnY = centerY - columnHeight / 2;
      column.forEach((node) => {
        const layout = nodeLayouts.get(node.node_id) ?? { width: 160, height: 64, summary: null, primary: false };
        positions.set(node.node_id, {
          x: columnX,
          y: columnY + layout.height / 2,
        });
        columnY += layout.height + stackGap;
      });
      outputBoundaryX += columnWidth + columnGap;
    });

    spec.policyRows.forEach((row, rowIndex) => {
      const rowWidth =
        row.reduce((sum, node) => sum + (nodeLayouts.get(node.node_id)?.width ?? 160), 0) +
        Math.max(0, row.length - 1) * columnGap;
      const rowHeight = Math.max(...row.map((node) => nodeLayouts.get(node.node_id)?.height ?? 64), 64);
      let rowCursorX = centerX - rowWidth / 2;
      const rowCenterY = centerY - spec.primaryLayout.height / 2 - policyGapY - rowIndex * (rowHeight + stackGap);
      row.forEach((node) => {
        const layout = nodeLayouts.get(node.node_id) ?? { width: 160, height: 64, summary: null, primary: false };
        positions.set(node.node_id, {
          x: rowCursorX + layout.width / 2,
          y: rowCenterY,
        });
        rowCursorX += layout.width + columnGap;
      });
    });

    cursorX += spec.zoneWidth + primaryGap;
  });

  stage.graph.nodes.forEach((node, index) => {
    if (!positions.has(node.node_id)) {
      const layout = nodeLayouts.get(node.node_id) ?? { width: 160, height: 64, summary: null, primary: false };
      positions.set(node.node_id, {
        x: 220 + (index % 4) * (layout.width + 56),
        y: 220 + Math.floor(index / 4) * (layout.height + 48),
      });
    }
  });

  return positions;
}

function buildStageTransformationPositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
) {
  if (stage.stage_id === "unified_document_object") {
    return buildUnifiedDocumentStagePositions(stage, nodeLayouts);
  }
  if (stage.stage_id === "evidence_constructor") {
    return buildEvidenceConstructorStagePositions(stage, nodeLayouts);
  }
  if (stage.stage_id === "evidence_graph_chunk_layer") {
    return buildEvidenceGraphChunkLayerStagePositions(stage, nodeLayouts);
  }
  if (stage.stage_id === "quality_policy_evaluation_governance_gate") {
    return buildQualityGateStagePositions(stage, nodeLayouts);
  }
  return buildGenericStageTransformationPositions(stage, nodeLayouts);
}

function buildAdaptiveStagePositions(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  _width: number,
  _height: number,
  nodeLayouts = buildRuntimeNodeLayouts(stage),
) {
  if (stage.graph.nodes.length === 0) {
    return new Map<string, NodePosition>();
  }

  try {
    const autoPositions = buildStageTransformationPositions(stage, nodeLayouts);
    const spacedPrimaryPositions = enforcePrimaryNodeSpacing(stage, autoPositions, nodeLayouts, 220);
    return normalizeStageLayoutPositions(
      resolveStagePositionCollisions(stage, spacedPrimaryPositions, nodeLayouts),
      nodeLayouts,
    );
  } catch {
    const fallbackPositions = makeStagePositions(stage, 1440, 920, nodeLayouts);
    return resolveStagePositionCollisions(stage, fallbackPositions, nodeLayouts);
  }
}

function statusStroke(status: ArchiveDocumentRuntimeStatus) {
  if (status === "blocked") return "#d4380d";
  if (status === "warning") return "#d48806";
  if (status === "completed") return "#389e0d";
  if (status === "running") return "#1677ff";
  return "#94a3b8";
}

function groupStages(stages: ArchiveDocumentRuntimeStageSnapshot[]) {
  return stages.reduce<Record<string, ArchiveDocumentRuntimeStageSnapshot[]>>((acc, stage) => {
    if (!acc[stage.group]) acc[stage.group] = [];
    acc[stage.group].push(stage);
    return acc;
  }, {});
}

function formatPersistedStages(runtime: ArchiveDocumentRuntimeContract) {
  const persistedStageIds = Array.isArray(runtime.persisted_stage_ids) ? runtime.persisted_stage_ids : [];
  return persistedStageIds.map((stageId) => ({
    id: stageId,
    label: getStageDisplayLabel(stageId, runtime.stages.find((stage) => stage.stage_id === stageId)?.label),
  }));
}

function formatObserverModeLabel(mode: ObserverMode) {
  if (mode === "node") return "节点观察";
  if (mode === "edge") return "边观察";
  return "阶段观察";
}

function eventLevelColor(level: ArchiveDocumentRuntimeObserverPayload["stream"][number]["level"]) {
  if (level === "danger") return "#d4380d";
  if (level === "warning") return "#d48806";
  if (level === "success") return "#389e0d";
  if (level === "info") return "#1677ff";
  return "#94a3b8";
}

function summaryToneColor(tone: "neutral" | "success" | "warning" | "danger" | "info") {
  if (tone === "danger") return "#d4380d";
  if (tone === "warning") return "#d48806";
  if (tone === "success") return "#389e0d";
  if (tone === "info") return "#1677ff";
  return "#64748b";
}

function summarizeRecord(record: Record<string, unknown> | undefined, limit = 2) {
  if (!record) return null;
  const entries = Object.entries(record).filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "");
  if (!entries.length) return null;
  return entries
    .slice(0, limit)
    .map(([key, value]) => `${key} = ${String(value)}`)
    .join(" / ");
}

function getPrimaryGraphNodes(stage: ArchiveDocumentRuntimeStageSnapshot) {
  const primaryNodeIds = stage.graph.primary_node_ids.length
    ? stage.graph.primary_node_ids
    : stage.graph.nodes.filter((node) => node.is_primary).map((node) => node.node_id);
  return primaryNodeIds
    .map((nodeId) => stage.graph.nodes.find((node) => node.node_id === nodeId))
    .filter((node): node is ArchiveDocumentRuntimeGraphNode => Boolean(node));
}

function buildPrimaryTrail(stage: ArchiveDocumentRuntimeStageSnapshot) {
  return getPrimaryGraphNodes(stage)
    .map((node) => node.label)
    .join(" → ");
}

function buildStageGraphClusters(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
) {
  const layoutPlan = buildStageRoleLayoutPlan(stage);

  const palette = [
    { fill: "rgba(245, 221, 136, 0.22)", stroke: "#d8b74d", title: "#9a7a14" },
    { fill: "rgba(247, 214, 194, 0.22)", stroke: "#df9b72", title: "#b86d45" },
    { fill: "rgba(246, 183, 156, 0.22)", stroke: "#df7f58", title: "#bc5b36" },
    { fill: "rgba(247, 214, 194, 0.22)", stroke: "#df9b72", title: "#b86d45" },
    { fill: "rgba(238, 229, 204, 0.22)", stroke: "#d0b26d", title: "#9a7a14" },
  ];

  return layoutPlan.primaryNodes.map((node, index) => {
    const anchor = positions.get(node.node_id) ?? { x: 220 + index * 180, y: 310 };
    const anchorBuckets = layoutPlan.buckets.get(node.node_id) ?? { inputs: [], policies: [], outputs: [] };
    const relatedNodes = [...anchorBuckets.inputs, ...anchorBuckets.policies, ...anchorBuckets.outputs];
    const paletteEntry = palette[index % palette.length];
    const isFocusCluster = node.is_focus || node.status === "blocked" || node.status === "warning";
    const rx = 96 + Math.max(0, relatedNodes.length - 1) * 18 + (isFocusCluster ? 28 : 0);
    const ry = 66 + relatedNodes.length * 12 + (isFocusCluster ? 14 : 0);
    return {
      anchorId: node.node_id,
      label: node.label,
      anchor,
      nodes: [node, ...relatedNodes],
      fill: isFocusCluster ? "rgba(247, 193, 169, 0.26)" : paletteEntry.fill,
      stroke: isFocusCluster ? "#df7f58" : paletteEntry.stroke,
      titleColor: isFocusCluster ? "#bc5b36" : paletteEntry.title,
      rx,
      ry,
    };
  });
}

type GraphSelectionState = {
  focusNodeId: string | null;
  activeNodeIds: Set<string>;
  relatedNodeIds: Set<string>;
  activeEdgeIds: Set<string>;
  relatedEdgeIds: Set<string>;
  nodeBadges: Map<string, string>;
  hasExplicitSelection: boolean;
};

type GraphHandleSide = "left" | "right" | "top" | "bottom";

function buildGraphSelectionState(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  selectedNodeId: string | null,
  selectedEdgeId: string | null,
): GraphSelectionState {
  const edgeById = new Map(stage.graph.edges.map((edge) => [edge.edge_id, edge] as const));
  const explicitEdge = selectedEdgeId ? edgeById.get(selectedEdgeId) ?? null : null;
  const explicitNode =
    selectedNodeId && stage.graph.nodes.some((node) => node.node_id === selectedNodeId) ? selectedNodeId : null;
  const focusNodeId =
    explicitNode ??
    stage.graph.nodes.find((node) => node.is_focus)?.node_id ??
    getPrimaryGraphNodes(stage)[Math.floor(getPrimaryGraphNodes(stage).length / 2)]?.node_id ??
    null;

  const activeNodeIds = new Set<string>();
  const relatedNodeIds = new Set<string>();
  const activeEdgeIds = new Set<string>();
  const relatedEdgeIds = new Set<string>();
  const nodeBadges = new Map<string, string>();

  function collectAdjacent(nodeId: string, edgeSet: Set<string>, nodeSet: Set<string>) {
    stage.graph.edges.forEach((edge) => {
      if (edge.source !== nodeId && edge.target !== nodeId) return;
      edgeSet.add(edge.edge_id);
      const siblingId = edge.source === nodeId ? edge.target : edge.source;
      if (siblingId !== nodeId) {
        nodeSet.add(siblingId);
      }
    });
  }

  if (explicitNode) {
    activeNodeIds.add(explicitNode);
    nodeBadges.set(explicitNode, "已选中");
    collectAdjacent(explicitNode, relatedEdgeIds, relatedNodeIds);
  } else if (explicitEdge) {
    activeEdgeIds.add(explicitEdge.edge_id);
    activeNodeIds.add(explicitEdge.source);
    activeNodeIds.add(explicitEdge.target);
    nodeBadges.set(explicitEdge.source, "端点");
    nodeBadges.set(explicitEdge.target, "端点");
    collectAdjacent(explicitEdge.source, relatedEdgeIds, relatedNodeIds);
    collectAdjacent(explicitEdge.target, relatedEdgeIds, relatedNodeIds);
    relatedEdgeIds.delete(explicitEdge.edge_id);
    relatedNodeIds.delete(explicitEdge.source);
    relatedNodeIds.delete(explicitEdge.target);
  } else if (focusNodeId) {
    activeNodeIds.add(focusNodeId);
    nodeBadges.set(focusNodeId, "焦点");
    collectAdjacent(focusNodeId, relatedEdgeIds, relatedNodeIds);
  }

  relatedNodeIds.forEach((nodeId) => {
    if (!nodeBadges.has(nodeId)) {
      nodeBadges.set(nodeId, "关联");
    }
  });

  return {
    focusNodeId,
    activeNodeIds,
    relatedNodeIds,
    activeEdgeIds,
    relatedEdgeIds,
    nodeBadges,
    hasExplicitSelection: Boolean(explicitNode || explicitEdge),
  };
}

function getHandlePosition(side: GraphHandleSide) {
  if (side === "left") return Position.Left;
  if (side === "right") return Position.Right;
  if (side === "top") return Position.Top;
  return Position.Bottom;
}

function getDirectionalHandlePair(source: NodePosition, target: NodePosition) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const horizontal = Math.abs(dx) >= Math.abs(dy) * 0.92;
  const sourceSide: GraphHandleSide = horizontal ? (dx >= 0 ? "right" : "left") : dy >= 0 ? "bottom" : "top";
  const targetSide: GraphHandleSide =
    sourceSide === "left"
      ? "right"
      : sourceSide === "right"
        ? "left"
        : sourceSide === "top"
          ? "bottom"
          : "top";

  return {
    sourceHandle: `source-${sourceSide}`,
    targetHandle: `target-${targetSide}`,
  };
}

type RuntimeFlowNodeData = {
  label: string;
  status: ArchiveDocumentRuntimeStatus;
  primary: boolean;
  highlightLevel: "selected" | "related" | "default" | "muted";
  selectionBadge?: string | null;
  animationKind?: "enter" | "status-change" | "reflow" | null;
  summary?: string | null;
};

type RuntimeClusterNodeData = {
  label: string;
  stroke: string;
  fill: string;
  titleColor: string;
};

function RuntimeGraphNodeView({ data }: { data: RuntimeFlowNodeData }) {
  const borderColor = statusStroke(data.status);
  const background = data.highlightLevel === "selected"
    ? "linear-gradient(180deg, rgba(255,248,242,0.98) 0%, rgba(255,255,255,1) 100%)"
    : data.primary
      ? "linear-gradient(180deg, rgba(255,251,247,0.98) 0%, rgba(255,255,255,1) 100%)"
      : "rgba(255,255,255,0.98)";
  const shellClassName = [
    "runtime-graph-node-shell",
    `is-highlight-${data.highlightLevel}`,
    `is-status-${data.status}`,
    data.animationKind === "enter" ? "is-entering" : "",
    data.animationKind === "status-change" ? "is-status-change" : "",
    data.animationKind === "reflow" ? "is-reflowing" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const isSelected = data.highlightLevel === "selected";
  const isRelated = data.highlightLevel === "related";
  const backgroundTone = isSelected ? "#8a4327" : data.primary ? "#8a4327" : "#475569";
  const summaryTone = isSelected ? "#7c5a4a" : data.primary ? "#7c5a4a" : "#94a3b8";

  return (
    <div className={shellClassName}>
      {(["left", "right", "top", "bottom"] as GraphHandleSide[]).map((side) => (
        <Handle
          key={`target-${side}`}
          id={`target-${side}`}
          type="target"
          position={getHandlePosition(side)}
          style={{ opacity: 0, width: 10, height: 10, border: 0, background: "transparent" }}
        />
      ))}
      <div
        className="runtime-graph-node-card"
        style={{
          width: "100%",
          height: "100%",
          borderRadius: data.primary ? 24 : 18,
          border: `${data.primary ? 3 : 2}px solid ${borderColor}`,
          background,
          padding: data.primary ? "14px 16px" : "10px 12px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          boxShadow: isSelected
            ? "0 18px 34px rgba(217,93,57,0.18)"
            : isRelated
              ? "0 12px 28px rgba(222,106,66,0.12)"
              : data.primary
              ? "0 12px 28px rgba(15,23,42,0.10)"
              : "0 6px 18px rgba(15,23,42,0.08)",
          transition: "border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease",
          transform: isSelected ? "translateY(-2px)" : "translateY(0)",
          overflow: "visible",
        }}
      >
        {data.selectionBadge ? <div className="runtime-graph-selection-badge">{data.selectionBadge}</div> : null}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, width: "100%" }}>
          <div
            className="runtime-graph-node-status-dot"
            style={{
              width: data.primary ? 12 : 10,
              height: data.primary ? 12 : 10,
              borderRadius: 999,
              background: borderColor,
              flexShrink: 0,
              marginTop: 5,
              boxShadow: isSelected ? "0 0 0 5px rgba(222,106,66,0.16)" : isRelated ? "0 0 0 4px rgba(222,106,66,0.1)" : "none",
            }}
          />
          <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: data.summary ? 6 : 0 }}>
            <div
              style={{
                color: backgroundTone,
                fontSize: data.primary ? 15 : 13,
                fontWeight: data.primary ? 700 : 600,
                lineHeight: 1.35,
                wordBreak: "break-word",
              }}
            >
              {data.label}
            </div>
            {data.summary ? (
              <div
                style={{
                  color: summaryTone,
                  fontSize: data.primary ? 11.5 : 10.5,
                  lineHeight: 1.45,
                  wordBreak: "break-word",
                }}
              >
                {data.summary}
              </div>
            ) : null}
          </div>
        </div>
      </div>
      {(["left", "right", "top", "bottom"] as GraphHandleSide[]).map((side) => (
        <Handle
          key={`source-${side}`}
          id={`source-${side}`}
          type="source"
          position={getHandlePosition(side)}
          style={{ opacity: 0, width: 10, height: 10, border: 0, background: "transparent" }}
        />
      ))}
    </div>
  );
}

function RuntimeClusterNodeView({ data }: { data: RuntimeClusterNodeData }) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        borderRadius: 999,
        border: `2px solid ${data.stroke}`,
        background: data.fill,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 14,
          left: 0,
          width: "100%",
          textAlign: "center",
          color: data.titleColor,
          fontSize: 15,
          fontWeight: 700,
        }}
      >
        {data.label}
      </div>
    </div>
  );
}

function GraphViewportSync({ layoutSignature }: { layoutSignature: string }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    const frameId = window.requestAnimationFrame(() => {
      void fitView({ padding: 0.18 });
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [fitView, layoutSignature]);

  return null;
}

function buildStageFlowNodes(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
  graphLens: GraphLens,
  selectionState: GraphSelectionState,
  nodeAnimationFlags: Record<string, "enter" | "status-change" | "reflow">,
): FlowNode[] {
  const primaryNodeSet = new Set(
    stage.graph.primary_node_ids.length
      ? stage.graph.primary_node_ids
      : stage.graph.nodes.filter((node) => node.is_primary).map((node) => node.node_id),
  );

  const graphNodes: FlowNode[] = stage.graph.nodes.map((node) => {
    const pos = positions.get(node.node_id) ?? { x: 320, y: 280 };
    const primary = primaryNodeSet.has(node.node_id) || node.is_primary;
    const layout = nodeLayouts.get(node.node_id) ?? {
      width: primary ? 188 : 146,
      height: primary ? 76 : 54,
      summary: null,
      primary,
    };
    const isSelected = selectionState.activeNodeIds.has(node.node_id);
    const isRelated = selectionState.relatedNodeIds.has(node.node_id);
    const highlightLevel =
      isSelected
        ? "selected"
        : isRelated
          ? "related"
          : selectionState.hasExplicitSelection || (graphLens === "primary" && !primary)
            ? "muted"
            : "default";

    return {
      id: node.node_id,
      type: "runtimeNode",
      position: {
        x: pos.x - layout.width / 2,
        y: pos.y - layout.height / 2,
      },
      draggable: true,
      selectable: true,
      data: {
        label: node.label,
        status: node.status,
        primary,
        highlightLevel,
        selectionBadge: selectionState.nodeBadges.get(node.node_id) ?? null,
        animationKind: nodeAnimationFlags[node.node_id] ?? null,
        summary: layout.summary,
      },
      style: {
        width: layout.width,
        height: layout.height,
        border: "none",
        background: "transparent",
        transition: "transform 260ms cubic-bezier(0.2, 0.8, 0.2, 1)",
        zIndex: highlightLevel === "selected" ? 6 : highlightLevel === "related" ? 5 : primary ? 4 : 2,
      },
    };
  });

  return graphNodes;
}

function buildStageClusterFlowNodes(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  positions: Map<string, NodePosition>,
  nodeLayouts: Map<string, RuntimeNodeLayout>,
): FlowNode[] {
  return buildStageGraphClusters(stage, positions)
    .filter((cluster) => cluster.nodes.length >= 3)
    .map((cluster) => {
      let minX = Number.POSITIVE_INFINITY;
      let maxX = Number.NEGATIVE_INFINITY;
      let minY = Number.POSITIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;

      cluster.nodes.forEach((node) => {
        const position = positions.get(node.node_id);
        const layout = nodeLayouts.get(node.node_id) ?? { width: 180, height: 72, summary: null, primary: false };
        if (!position) return;
        minX = Math.min(minX, position.x - layout.width / 2);
        maxX = Math.max(maxX, position.x + layout.width / 2);
        minY = Math.min(minY, position.y - layout.height / 2);
        maxY = Math.max(maxY, position.y + layout.height / 2);
      });

      if (!Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) {
        minX = cluster.anchor.x - cluster.rx;
        maxX = cluster.anchor.x + cluster.rx;
        minY = cluster.anchor.y - cluster.ry;
        maxY = cluster.anchor.y + cluster.ry;
      }

      const paddingX = 42;
      const paddingY = 36;
      const width = Math.max(maxX - minX + paddingX * 2, cluster.rx * 2);
      const height = Math.max(maxY - minY + paddingY * 2, cluster.ry * 2);

      return {
        id: `cluster:${cluster.anchorId}`,
        type: "runtimeCluster",
        position: {
          x: minX - paddingX,
          y: minY - paddingY,
        },
        draggable: false,
        selectable: false,
        data: {
          label: cluster.label,
          stroke: cluster.stroke,
          fill: cluster.fill,
          titleColor: cluster.titleColor,
        } satisfies RuntimeClusterNodeData,
        style: {
          width,
          height,
          border: "none",
          background: "transparent",
          pointerEvents: "none",
          zIndex: 0,
        },
      } satisfies FlowNode;
    });
}

function buildStageFlowEdges(
  stage: ArchiveDocumentRuntimeStageSnapshot,
  graphLens: GraphLens,
  selectionState: GraphSelectionState,
  positions: Map<string, NodePosition>,
  stagePolicyConfig: ArchiveStagePolicyConfig | null | undefined,
): FlowEdge[] {
  const primaryEdgeSet = new Set(
    stage.graph.primary_edge_ids.length
      ? stage.graph.primary_edge_ids
      : stage.graph.edges.filter((edge) => edge.is_primary).map((edge) => edge.edge_id),
  );
  const nodeById = new Map(stage.graph.nodes.map((node) => [node.node_id, node] as const));

  return stage.graph.edges.map((edge) => {
    const primary = primaryEdgeSet.has(edge.edge_id) || edge.is_primary;
    const isSelected = selectionState.activeEdgeIds.has(edge.edge_id);
    const isRelated = selectionState.relatedEdgeIds.has(edge.edge_id);
    const faded =
      (!isSelected && !isRelated && selectionState.hasExplicitSelection) ||
      (graphLens === "primary" && !primary && !isSelected && !isRelated);
    const sourcePosition = positions.get(edge.source) ?? { x: 0, y: 0 };
    const targetPosition = positions.get(edge.target) ?? { x: 0, y: 0 };
    const handlePair = getDirectionalHandlePair(sourcePosition, targetPosition);
    const highlightClassName = isSelected
      ? "runtime-flow-edge runtime-flow-edge--selected"
      : isRelated
        ? "runtime-flow-edge runtime-flow-edge--related"
        : faded
          ? "runtime-flow-edge runtime-flow-edge--muted"
          : "runtime-flow-edge";
    const label =
      isSelected || isRelated || primary
        ? buildGraphEdgeDecisionLabel(
            edge,
            nodeById.get(edge.source),
            nodeById.get(edge.target),
            stagePolicyConfig,
            primary,
          )
        : undefined;
    return {
      id: edge.edge_id,
      source: edge.source,
      target: edge.target,
      sourceHandle: handlePair.sourceHandle,
      targetHandle: handlePair.targetHandle,
      type: ConnectionLineType.Straight,
      className: highlightClassName,
      label,
      labelShowBg: Boolean(label),
      labelBgBorderRadius: 12,
      labelBgPadding: [8, 4],
      labelStyle: {
        fill: primary ? "#9a3412" : "#7c2d12",
        fontWeight: primary ? 700 : 600,
        fontSize: primary ? 11.5 : 10.5,
      },
      style: {
        stroke: isSelected ? "#d95d39" : isRelated ? "#de6a42" : primary ? "#de6a42" : "#cbd5e1",
        strokeWidth: isSelected ? 4 : isRelated ? 3.2 : primary ? 3 : 2,
        opacity: isSelected ? 1 : isRelated ? 0.92 : faded ? 0.12 : primary ? 0.86 : 0.56,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: isSelected ? "#d95d39" : isRelated ? "#de6a42" : primary ? "#de6a42" : "#cbd5e1",
      },
      selectable: true,
      zIndex: isSelected ? 4 : isRelated ? 3 : primary ? 2 : 1,
    };
  });
}

function SummaryMetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div
      style={{
        borderRadius: 14,
        border: "1px solid rgba(148,163,184,0.22)",
        background: "linear-gradient(180deg, rgba(248,250,252,0.95) 0%, #fff 100%)",
        padding: "14px 16px",
        minHeight: 96,
      }}
    >
      <Space direction="vertical" size={6} style={{ display: "flex" }}>
        <Text type="secondary">{label}</Text>
        <Text strong style={{ fontSize: 16 }}>
          {value}
        </Text>
        {hint ? <Text type="secondary">{hint}</Text> : null}
      </Space>
    </div>
  );
}

function RuntimeContractCard({ runtime }: { runtime: ArchiveDocumentRuntimeContract }) {
  const modeKey = runtime.runtime_mode ?? "legacy_fallback";
  const modeMeta = runtimeModeMeta[modeKey] ?? runtimeModeMeta.legacy_fallback;
  const persistedStages = formatPersistedStages(runtime);
  const currentStageLabel = getStageDisplayLabel(runtime.current_stage_id, runtime.current_stage_label);
  return (
    <Card
      size="small"
      styles={{ body: { display: "flex", flexDirection: "column", gap: 16, padding: 20 } }}
    >
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} xl={9}>
          <Space direction="vertical" size={8} style={{ display: "flex" }}>
            <Space wrap size={8}>
              <Text strong style={{ fontSize: 18 }}>
                运行契约
              </Text>
              <Tag color={modeMeta.color}>{modeMeta.label}</Tag>
              <Tag color="blue">已持久化 {persistedStages.length}</Tag>
            </Space>
            <Text type="secondary">{modeMeta.hint}</Text>
          </Space>
        </Col>
        <Col xs={24} xl={15}>
          <Space wrap size={[8, 8]} style={{ justifyContent: "flex-end", width: "100%" }}>
            {persistedStages.map((stage) => (
              <Tag key={stage.id} color="blue">
                {stage.label}
              </Tag>
            ))}
          </Space>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <SummaryMetricTile label="运行模式" value={modeMeta.label} hint={modeKey} />
        </Col>
        <Col xs={24} md={6}>
          <SummaryMetricTile label="当前活跃阶段" value={currentStageLabel} hint={runtime.current_stage_id} />
        </Col>
        <Col xs={24} md={6}>
          <SummaryMetricTile label="已持久化阶段" value={`${persistedStages.length} / ${runtime.stages.length}`} hint="可直接回看运行快照" />
        </Col>
        <Col xs={24} md={6}>
          <SummaryMetricTile
            label="源文档"
            value={String(runtime.source_document?.title ?? runtime.document_title)}
            hint={String(runtime.source_document?.file_type ?? "未知类型").toUpperCase()}
          />
        </Col>
      </Row>
    </Card>
  );
}

function DocumentFlowNavigation({
  runtime,
  inspectedStageId,
  onSelectStage,
}: {
  runtime: ArchiveDocumentRuntimeContract;
  inspectedStageId: string | null;
  onSelectStage: (stageId: string | null) => void;
}) {
  const grouped = groupStages(runtime.stages);
  const liveCurrentStage = getLiveCurrentStage(runtime);
  return (
    <Card title="13 阶段流程导航" styles={{ body: { display: "flex", flexDirection: "column", gap: 14, padding: 18 } }}>
      <Text type="secondary">实时当前阶段始终跟随后端运行状态；已完成阶段可点击回看快照，未进入阶段保持灰色并禁用。</Text>
      {Object.entries(grouped).map(([group, stages]) => {
        const groupStyle = stageGroupMeta[group] ?? stageGroupMeta["证据与知识生成"];
        return (
          <div
            key={group}
            style={{
              borderRadius: 14,
              border: `1px solid ${groupStyle.border}`,
              background: groupStyle.background,
              padding: 16,
            }}
          >
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                <Text strong style={{ color: groupStyle.tone }}>
                  {stageGroupDisplayNameMap[group] ?? group}
                </Text>
                <Tag color="default">{stages.length} 个阶段</Tag>
              </div>
              <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                {stages.map((stage, index) => {
                  const isCurrent = stage.stage_id === liveCurrentStage.stage_id;
                  const isSnapshot = inspectedStageId === stage.stage_id && !isCurrent;
                  const inspectable = isStageInspectable(stage, liveCurrentStage);
                  const meta = runtimeStatusMeta[stage.status];
                  const stageLabel = getStageDisplayLabel(stage.stage_id, stage.label);
                  return (
                    <div key={stage.stage_id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <button
                        type="button"
                        disabled={!inspectable}
                        onClick={() => onSelectStage(isCurrent ? null : stage.stage_id)}
                        style={{
                          minWidth: 148,
                          borderRadius: 999,
                          border: `1px solid ${
                            isCurrent ? "#d97706" : isSnapshot ? "#1677ff" : stage.status === "blocked" ? "#d4380d" : groupStyle.border
                          }`,
                          background: isCurrent ? "rgba(255, 247, 237, 0.96)" : isSnapshot ? "#eff6ff" : inspectable ? "#fff" : "#f7f9fc",
                          color: isCurrent ? "#b45309" : !inspectable ? "#94a3b8" : "#1f2937",
                          padding: "10px 14px",
                          fontWeight: isCurrent || isSnapshot ? 700 : 600,
                          cursor: inspectable ? "pointer" : "not-allowed",
                          boxShadow: isCurrent
                            ? "0 8px 24px rgba(217,119,6,0.18)"
                            : isSnapshot
                              ? "0 8px 24px rgba(22,119,255,0.12)"
                              : "none",
                          opacity: inspectable ? 1 : 0.74,
                        }}
                      >
                        <Space size={8}>
                          <span
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: 999,
                              background:
                                stage.status === "blocked"
                                  ? "#d4380d"
                                    : stage.status === "completed"
                                      ? "#389e0d"
                                      : stage.status === "running"
                                        ? "#d97706"
                                        : "#94a3b8",
                              display: "inline-block",
                            }}
                          />
                          <span>{stageLabel}</span>
                        </Space>
                      </button>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {isCurrent ? "当前阶段" : isSnapshot ? "查看快照" : inspectable ? meta.label : "未进入"}
                      </Text>
                      {index < stages.length - 1 ? <Text type="secondary">→</Text> : null}
                    </div>
                  );
                })}
              </div>
            </Space>
          </div>
        );
      })}
    </Card>
  );
}

function DocumentFlowFigureNavigation({
  runtime,
  inspectedStageId,
  onSelectStage,
}: {
  runtime: ArchiveDocumentRuntimeContract;
  inspectedStageId: string | null;
  onSelectStage: (stageId: string | null) => void;
}) {
  const stageMap = new Map(runtime.stages.map((stage) => [stage.stage_id, stage]));
  const liveCurrentStage = getLiveCurrentStage(runtime);

  function edgeColor(fromStageId: string, toStageId: string) {
    const fromStage = stageMap.get(fromStageId);
    const toStage = stageMap.get(toStageId);
    if (!fromStage || !toStage) return "#cbd5e1";
    const fromState = getFlowNodeState(fromStage, liveCurrentStage);
    const toState = getFlowNodeState(toStage, liveCurrentStage);
    if (fromState === "pending" || toState === "pending") return "#cbd5e1";
    if (fromState === "current" || toState === "current") return "#d97706";
    return getFlowLaneId(fromStageId) === "intake" ? "#67b88e" : getFlowLaneId(fromStageId) === "evidence" ? "#d0a748" : "#de7c63";
  }

  function buildEdgePath(fromStageId: string, toStageId: string) {
    const fromNode = flowNodeLayout[fromStageId];
    const toNode = flowNodeLayout[toStageId];
    if (!fromNode || !toNode) return "";

    const startX = fromNode.x + fromNode.width;
    const startY = fromNode.y + fromNode.height / 2;
    const endX = toNode.x;
    const endY = toNode.y + toNode.height / 2;

    if (fromStageId === "evidence_pack" && toStageId !== "relation_review_family_normalization") {
      return `M ${startX} ${startY} L ${endX - 16} ${endY} L ${endX} ${endY}`;
    }
    if (toStageId === "canonical_knowledge" && fromStageId !== "relation_review_family_normalization") {
      return `M ${startX} ${startY} L ${endX - 16} ${endY} L ${endX} ${endY}`;
    }

    return `M ${startX} ${startY} L ${endX} ${endY}`;
  }

  function renderStageNode(stageId: string) {
    const stage = stageMap.get(stageId);
    const layout = flowNodeLayout[stageId];
    if (!stage || !layout) return null;
    const stageLabel = getStageDisplayLabel(stage.stage_id, stage.label);

    const laneId = getFlowLaneId(stageId);
    const nodeState = getFlowNodeState(stage, liveCurrentStage);
    const inspectable = isStageInspectable(stage, liveCurrentStage);
    const isSnapshot = inspectedStageId === stage.stage_id && stage.stage_id !== liveCurrentStage.stage_id;
    const laneColor =
      laneId === "intake" ? "#67b88e" : laneId === "evidence" ? "#d0a748" : "#de7c63";
    const borderColor =
      nodeState === "current" ? "#de7c63" : isSnapshot ? "#1677ff" : nodeState === "pending" ? "#b8c1cf" : laneColor;
    const textColor =
      nodeState === "pending" ? "#7b8794" : nodeState === "current" ? "#b45309" : isSnapshot ? "#1677ff" : laneColor;

    return (
      <div
        key={stage.stage_id}
        style={{
          position: "absolute",
          left: layout.x,
          top: nodeState === "current" ? layout.y - 8 : layout.y,
          width: layout.width,
          height: nodeState === "current" ? layout.height + 28 : layout.height,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          zIndex: 2,
        }}
      >
        <div
          style={{
            padding: nodeState === "current" ? "6px 8px 8px" : 0,
            borderRadius: 14,
            background: nodeState === "current" ? "rgba(255, 239, 198, 0.95)" : isSnapshot ? "rgba(239, 246, 255, 0.95)" : "transparent",
            boxShadow:
              nodeState === "current"
                ? "0 10px 24px rgba(217,119,6,0.16)"
                : isSnapshot
                  ? "0 10px 24px rgba(22,119,255,0.12)"
                  : "none",
          }}
        >
          <button
            type="button"
            disabled={!inspectable}
            onClick={() => onSelectStage(stage.stage_id === liveCurrentStage.stage_id ? null : stage.stage_id)}
            data-stage-id={stage.stage_id}
            data-stage-state={nodeState}
            data-stage-view={isSnapshot ? "snapshot" : nodeState === "current" ? "live" : inspectable ? "completed" : "pending"}
            aria-label={stageLabel}
            style={{
              width: layout.width,
              height: layout.height,
              borderRadius: 18,
              border: `3px solid ${borderColor}`,
              background: nodeState === "pending" ? "#f7f9fc" : "#fff",
              color: textColor,
              fontSize: 14,
              fontWeight: 700,
              cursor: inspectable ? "pointer" : "not-allowed",
              lineHeight: 1.15,
              opacity: inspectable ? 1 : 0.72,
            }}
          >
            {stageLabel}
          </button>
        </div>
        {nodeState === "current" ? (
          <Text style={{ color: "#b45309", fontSize: 12, fontWeight: 700, marginTop: 6 }}>当前阶段</Text>
        ) : isSnapshot ? (
          <Text style={{ color: "#1677ff", fontSize: 12, fontWeight: 700, marginTop: 6 }}>查看快照</Text>
        ) : null}
      </div>
    );
  }

  return (
    <Card
      title="流程导航"
      extra={
        <Text type="secondary">
          上层展示真实阶段流，证据包之后进入三条并行分支，点击任一阶段可回看当时的状态图谱。
        </Text>
      }
      styles={{ body: { padding: 10 } }}
    >
      <div
        style={{
          border: "1px solid rgba(148,163,184,0.2)",
          background: "#fff",
          padding: 14,
          overflowX: "auto",
        }}
      >
        <div style={{ position: "relative", width: 1750, height: 240 }}>
          {Object.values(flowLaneMeta).map((lane) => (
            <div
              key={lane.title}
              style={{
                position: "absolute",
                left: lane.rect.x,
                top: lane.rect.y,
                width: lane.rect.width,
                height: lane.rect.height,
                background: lane.fill,
                border: `1px solid ${lane.border}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "10px 12px 0",
                }}
              >
                <Text strong style={{ color: lane.titleColor, fontSize: 13 }}>
                  {lane.title}
                </Text>
                {lane.title === "规范化与发布" ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    绿色：已完成 橙色：当前阶段 灰色：未进入
                  </Text>
                ) : null}
              </div>
            </div>
          ))}

          <svg
            viewBox="0 0 1750 240"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 1 }}
          >
            <defs>
              <marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#cbd5e1" />
              </marker>
              <marker id="flow-arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#67b88e" />
              </marker>
              <marker id="flow-arrow-amber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#d0a748" />
              </marker>
              <marker id="flow-arrow-rose" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#de7c63" />
              </marker>
              <marker id="flow-arrow-current" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#d97706" />
              </marker>
            </defs>
            {flowEdges.map((edge) => {
              const stroke = edgeColor(edge.from, edge.to);
              const markerId =
                stroke === "#67b88e"
                  ? "flow-arrow-green"
                  : stroke === "#d0a748"
                    ? "flow-arrow-amber"
                    : stroke === "#de7c63"
                      ? "flow-arrow-rose"
                      : stroke === "#d97706"
                        ? "flow-arrow-current"
                        : "flow-arrow";
              return (
                <path
                  key={`${edge.from}:${edge.to}`}
                  d={buildEdgePath(edge.from, edge.to)}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={3}
                  markerEnd={`url(#${markerId})`}
                />
              );
            })}
          </svg>

          {runtime.stages.map((stage) => renderStageNode(stage.stage_id))}
        </div>
      </div>
    </Card>
  );
}

function GraphCanvas({
  stage,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
}: {
  stage: ArchiveDocumentRuntimeStageSnapshot;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  onSelectNode: (id: string) => void;
  onSelectEdge: (id: string) => void;
}) {
  const width = 860;
  const height = 470;
  const positions = useMemo(() => makeStagePositions(stage, width, height), [stage]);
  const primaryCount = stage.graph.primary_node_ids.length || stage.graph.nodes.filter((node) => node.is_primary).length;
  const stageLabel = getStageDisplayLabel(stage.stage_id, stage.label);
  const stageGroupLabel = getStageGroupDisplayLabel(stage);

  return (
    <Card
      title={`当前阶段图谱 · ${stageLabel}`}
      extra={
        <Space size={8} wrap>
          <Tag color={runtimeStatusMeta[stage.status].color}>{runtimeStatusMeta[stage.status].label}</Tag>
          <Text type="secondary">可拖动画布 · 滚轮缩放 · 节点实时变化</Text>
        </Space>
      }
      styles={{ body: { padding: 16 } }}
    >
      <div
        style={{
          marginBottom: 14,
          borderRadius: 12,
          border: "1px solid rgba(148,163,184,0.2)",
          background: "linear-gradient(180deg, rgba(248,250,252,0.96) 0%, #fff 100%)",
          padding: "12px 14px",
        }}
      >
        <Row gutter={[16, 10]} align="middle">
          <Col xs={24} md={10}>
            <Space direction="vertical" size={2} style={{ display: "flex" }}>
              <Text type="secondary">阶段导览</Text>
              <Text strong>{stageGroupLabel}</Text>
            </Space>
          </Col>
          <Col xs={12} md={5}>
            <Space direction="vertical" size={2} style={{ display: "flex" }}>
              <Text type="secondary">主路径节点</Text>
              <Text strong>{primaryCount}</Text>
            </Space>
          </Col>
          <Col xs={12} md={5}>
            <Space direction="vertical" size={2} style={{ display: "flex" }}>
              <Text type="secondary">节点 / 边</Text>
              <Text strong>
                {stage.graph.nodes.length} / {stage.graph.edges.length}
              </Text>
            </Space>
          </Col>
          <Col xs={24} md={4}>
              <Text type="secondary">默认展开全部节点，可切回主路径聚焦主干</Text>
          </Col>
        </Row>
      </div>
      <div
        style={{
          position: "relative",
          minHeight: height,
          overflow: "hidden",
          borderRadius: 12,
          border: "1px solid rgba(148,163,184,0.24)",
          background:
            "linear-gradient(180deg, rgba(248,250,252,0.98) 0%, rgba(255,255,255,1) 100%), repeating-linear-gradient(0deg, transparent 0 39px, rgba(15,23,42,0.025) 39px 40px), repeating-linear-gradient(90deg, transparent 0 39px, rgba(15,23,42,0.025) 39px 40px)",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            display: "flex",
            gap: 8,
            zIndex: 2,
            padding: 6,
            borderRadius: 999,
            background: "rgba(255,255,255,0.9)",
            boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
          }}
        >
          {["主路径", "全部", "跟随", "暂停"].map((label) => (
            <Button
              key={label}
              size="small"
              type={label === "主路径" ? "primary" : "default"}
              style={{ borderRadius: 999 }}
            >
              {label}
            </Button>
          ))}
        </div>
        <div
          style={{
            position: "absolute",
            right: 12,
            bottom: 12,
            display: "flex",
            flexDirection: "column",
            gap: 6,
            zIndex: 2,
            padding: 6,
            borderRadius: 20,
            background: "rgba(255,255,255,0.92)",
            boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
          }}
        >
          {["全", "+", "-", "中", "重"].map((label) => (
            <Button key={label} size="small" shape="circle">
              {label}
            </Button>
          ))}
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }}>
          <defs>
            <marker id="runtime-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
            </marker>
            <marker id="runtime-arrow-primary" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#d4380d" />
            </marker>
          </defs>
          {stage.graph.edges.map((edge) => {
            const source = positions.get(edge.source);
            const target = positions.get(edge.target);
            if (!source || !target) return null;
            const active = selectedEdgeId === edge.edge_id;
            const primary = stage.graph.primary_edge_ids.includes(edge.edge_id) || edge.is_primary;
            return (
              <g key={edge.edge_id} onClick={() => onSelectEdge(edge.edge_id)} style={{ cursor: "pointer" }}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={primary ? "#d4380d" : "#cbd5e1"}
                  strokeWidth={active ? 4 : primary ? 3 : 2}
                  markerEnd={`url(#${primary ? "runtime-arrow-primary" : "runtime-arrow"})`}
                  opacity={active ? 1 : primary ? 0.96 : 0.82}
                />
                <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="transparent" strokeWidth={18} />
              </g>
            );
          })}
        </svg>
        {stage.graph.nodes.map((node) => {
          const pos = positions.get(node.node_id) ?? { x: width / 2, y: height / 2 };
          const active = selectedNodeId === node.node_id;
          const primary = stage.graph.primary_node_ids.includes(node.node_id) || node.is_primary;
          const nodeWidth = primary ? 156 : 128;
          const nodeHeight = primary ? 64 : 52;
          return (
            <button
              key={node.node_id}
              type="button"
              onClick={() => onSelectNode(node.node_id)}
              style={{
                position: "absolute",
                left: pos.x - nodeWidth / 2,
                top: pos.y - nodeHeight / 2,
                width: nodeWidth,
                height: nodeHeight,
                borderRadius: 999,
                border: `3px solid ${statusStroke(node.status)}`,
                background: active ? "rgba(255,255,255,0.98)" : "rgba(255,255,255,0.92)",
                boxShadow: active ? "0 0 0 6px rgba(212,56,13,0.10)" : primary ? "0 8px 20px rgba(15,23,42,0.06)" : "none",
                color: "#1f2937",
                fontWeight: primary ? 700 : 600,
                fontSize: primary ? 16 : 14,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                lineHeight: 1.2,
                padding: "0 14px",
                cursor: "pointer",
              }}
            >
              {node.label}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

function ObserverPanel({
  observer,
  mode,
  onChangeMode,
}: {
  observer: ArchiveDocumentRuntimeObserverPayload | null;
  mode: ObserverMode;
  onChangeMode: (mode: ObserverMode) => void;
}) {
  if (!observer) {
    return (
      <Card title="对象观察窗">
        <Empty description="点击节点或边，右侧查看对象内容、证据与状态流" />
      </Card>
    );
  }
  return (
    <Card
      title="对象观察窗"
      extra={<Tag color={runtimeStatusMeta[observer.status].color}>{runtimeStatusMeta[observer.status].label}</Tag>}
      styles={{ body: { display: "flex", flexDirection: "column", gap: 16, padding: 18 } }}
    >
      <Space direction="vertical" size={4} style={{ display: "flex" }}>
        <Title level={5} style={{ margin: 0 }}>
          {observer.title}
        </Title>
        {observer.subtitle ? <Text type="secondary">{observer.subtitle}</Text> : null}
      </Space>
      <Card
        size="small"
        styles={{ body: { padding: 14 } }}
      >
        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <Text type="secondary">支持阶段、节点、边三种视角；流式事件与结构化状态会同时更新。</Text>
          <Segmented
            block
            value={mode}
            onChange={(value) => onChangeMode(value as ObserverMode)}
            options={[
              { label: "阶段视角", value: "stage" },
              { label: "节点视角", value: "node" },
              { label: "边视角", value: "edge" },
            ]}
          />
        </Space>
      </Card>
      <Card
        size="small"
        title="实时处理信息流"
        extra={<Text type="secondary">滚动查看对象内容、证据与状态流</Text>}
        styles={{ body: { maxHeight: 220, overflow: "auto", paddingTop: 8 } }}
      >
        <List
          size="small"
          dataSource={observer.stream}
          renderItem={(event) => (
            <List.Item style={{ paddingInline: 0 }}>
              <Space direction="vertical" size={2} style={{ display: "flex" }}>
                <Space size={8} wrap>
                  <Tag>{event.kind}</Tag>
                  {event.timestamp ? <Text type="secondary">{formatDateTime(event.timestamp)}</Text> : null}
                </Space>
                <Text>{event.message}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
      <Space direction="vertical" size={12} style={{ display: "flex" }}>
        {observer.sections.map((section) => (
          <Card key={section.section_id} size="small" title={section.title}>
            <Descriptions size="small" column={1} colon={false}>
              {section.fields.map((field) => (
                <Descriptions.Item key={field.key} label={field.label}>
                  <Text>{field.value}</Text>
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        ))}
      </Space>
      {observer.actions.length > 0 ? (
        <Space wrap>
          {observer.actions.map((action) => (
            <Button key={action.action_id} type={action.target_kind === "graph" ? "primary" : "default"}>
              {action.label}
            </Button>
          ))}
        </Space>
      ) : null}
    </Card>
  );
}

function DocumentRuntimeSummaryStrip({
  runtime,
  liveCurrentStage,
  inspectedStage,
  focusLabel,
  focusHint,
  transportState,
}: {
  runtime: ArchiveDocumentRuntimeContract;
  liveCurrentStage: ArchiveDocumentRuntimeStageSnapshot;
  inspectedStage: ArchiveDocumentRuntimeStageSnapshot;
  focusLabel: string;
  focusHint?: string;
  transportState: RuntimeTransportState;
}) {
  const modeKey = runtime.runtime_mode ?? "legacy_fallback";
  const modeMeta = runtimeModeMeta[modeKey] ?? runtimeModeMeta.legacy_fallback;
  const transportMeta = runtimeTransportMeta[transportState];
  const persistedStages = formatPersistedStages(runtime);
  const liveCurrentStageLabel = getStageDisplayLabel(liveCurrentStage.stage_id, liveCurrentStage.label);
  const inspectedStageLabel = getStageDisplayLabel(inspectedStage.stage_id, inspectedStage.label);
  const isViewingSnapshot = inspectedStage.stage_id !== liveCurrentStage.stage_id;
  const policySnapshot = runtime.policy_snapshot ?? null;

  return (
    <div data-testid="document-runtime-summary-strip">
      <Card
        size="small"
        styles={{ body: { display: "flex", flexDirection: "column", gap: 16, padding: 20 } }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} xl={12}>
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Space wrap size={8}>
                <Text strong style={{ fontSize: 18 }}>
                  单文档运行摘要链
                </Text>
                <Tag color={modeMeta.color}>{modeMeta.label}</Tag>
                <Tag color={runtimeStatusMeta[runtime.status].color}>{runtimeStatusMeta[runtime.status].label}</Tag>
                <Tag color={transportMeta.color}>{transportMeta.label}</Tag>
                <Tag color="blue">已持久化 {persistedStages.length}</Tag>
              </Space>
              <Text type="secondary">
                把 runtime 契约嵌进页头摘要，先交代当前文档、运行模式、活跃阶段和观察焦点，再进入流程导航、图谱控制和对象观察窗。
              </Text>
            </Space>
          </Col>
          <Col xs={24} xl={12}>
            <Space wrap size={[8, 8]} style={{ justifyContent: "flex-end", width: "100%" }}>
              {persistedStages.slice(0, 6).map((stage) => (
                <Tag key={stage.id} color="blue">
                  {stage.label}
                </Tag>
              ))}
              {persistedStages.length > 6 ? <Tag color="default">+{persistedStages.length - 6} 个阶段</Tag> : null}
            </Space>
          </Col>
        </Row>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8} xl={4}>
            <SummaryMetricTile
              label="源文档"
              value={String(runtime.source_document?.title ?? runtime.document_title)}
              hint={String(runtime.source_document?.file_type ?? "未知类型").toUpperCase()}
            />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <SummaryMetricTile label="运行模式" value={modeMeta.label} hint={modeKey} />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <SummaryMetricTile label="实时通道" value={transportMeta.label} hint={transportMeta.hint} />
          </Col>
          <Col xs={24} md={8} xl={5}>
            <SummaryMetricTile
              label="策略版本"
              value={policySnapshot?.version_label ?? "未冻结"}
              hint={
                policySnapshot
                  ? `${policySnapshot.snapshot_id} · ${formatDateTime(policySnapshot.captured_at)}`
                  : "抽取启动后写入运行快照"
              }
            />
          </Col>
          <Col xs={24} md={8} xl={5}>
            <div data-testid="runtime-live-current-stage">
              <SummaryMetricTile label="实时当前阶段" value={liveCurrentStageLabel} hint={liveCurrentStage.stage_id} />
            </div>
          </Col>
          <Col xs={24} md={8} xl={5}>
            <div data-testid="runtime-inspected-stage">
              <SummaryMetricTile
                label="当前查看内容"
                value={isViewingSnapshot ? `${inspectedStageLabel} 快照` : "实时阶段"}
                hint={isViewingSnapshot ? inspectedStage.stage_id : liveCurrentStage.stage_id}
              />
            </div>
          </Col>
          <Col xs={24} md={8} xl={5}>
            <SummaryMetricTile label="观察焦点" value={focusLabel} hint={focusHint} />
          </Col>
          <Col xs={24} md={8} xl={2}>
            <SummaryMetricTile
              label="已持久化阶段"
              value={`${persistedStages.length} / ${runtime.stages.length}`}
              hint="可直接回看运行快照"
            />
          </Col>
          <Col xs={24} md={8} xl={2}>
            <SummaryMetricTile label="当前状态" value={runtimeStatusMeta[runtime.status].label} hint={runtime.current_stage_id} />
          </Col>
        </Row>
      </Card>
    </div>
  );
}

function DocumentGraphControlPanel({
  stage,
  stagePolicyConfig,
  graphLens,
  onChangeGraphLens,
  observerMode,
  focusLabel,
  focusHint,
  focusSummary,
  selectionInsight,
  onResetFocus,
}: {
  stage: ArchiveDocumentRuntimeStageSnapshot;
  stagePolicyConfig: ArchiveStagePolicyConfig | null;
  graphLens: GraphLens;
  onChangeGraphLens: (lens: GraphLens) => void;
  observerMode: ObserverMode;
  focusLabel: string;
  focusHint?: string;
  focusSummary?: string | null;
  selectionInsight: { headline: string; detail: string; tags: string[] };
  onResetFocus: () => void;
}) {
  const primaryNodeCount =
    stage.graph.primary_node_ids.length || stage.graph.nodes.filter((node) => node.is_primary).length;
  const primaryEdgeCount =
    stage.graph.primary_edge_ids.length || stage.graph.edges.filter((edge) => edge.is_primary).length;
  const stageLabel = getStageDisplayLabel(stage.stage_id, stage.label);
  const stageGroupLabel = getStageGroupDisplayLabel(stage);
  const primaryTrail = buildPrimaryTrail(stage);
  const stageRuleDigest = buildStagePolicyRuleDigest(stagePolicyConfig, 3);

  return (
    <div data-testid="document-graph-control-panel">
      <div
        style={{
          padding: "22px 22px 18px",
          borderBottom: "1px solid rgba(37, 99, 235, 0.14)",
          background: "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%)",
        }}
      >
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <div>
            <Space wrap size={[8, 8]}>
              <Tag color={runtimeStatusMeta[stage.status].color}>{runtimeStatusMeta[stage.status].label}</Tag>
              <Tag color="blue">{stageGroupLabel}</Tag>
              <Tag color="default">
                主路径 {primaryNodeCount} 节点 / {primaryEdgeCount} 边
              </Tag>
            </Space>
            <Title level={4} style={{ margin: "10px 0 6px" }}>
              当前阶段图谱 · {stageLabel}
            </Title>
            <Text type="secondary">
              当前激活阶段为“{stageLabel}”，默认展示该阶段的动态因果图谱；点击上方流程中的任一阶段，可切换到对应快照。
            </Text>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "120px minmax(0, 1fr)",
              gap: 12,
              padding: "12px 14px",
              border: "1px solid rgba(148,163,184,0.2)",
              borderRadius: 14,
              background: "#fff",
            }}
          >
            <Text strong>阶段导览</Text>
            <Text>{primaryTrail || "当前阶段主路径将在这里串联显示。"}</Text>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(220px, 1.05fr) minmax(220px, 1fr) minmax(260px, 1.2fr) minmax(260px, 1.15fr)",
              gap: 0,
              border: "1px solid rgba(148,163,184,0.2)",
              borderRadius: 14,
              overflow: "hidden",
              background: "#fff",
            }}
          >
            <div style={{ padding: "12px 14px", borderRight: "1px solid rgba(148,163,184,0.14)" }}>
              <Text type="secondary">已选对象</Text>
              <div style={{ fontWeight: 700, marginTop: 6, color: "#9a5a1d" }}>{focusLabel}</div>
            </div>
            <div style={{ padding: "12px 14px", borderRight: "1px solid rgba(148,163,184,0.14)", background: "rgba(249,115,22,0.06)" }}>
              <Text type="secondary">当前视角</Text>
              <div style={{ fontWeight: 700, marginTop: 6 }}>{formatObserverModeLabel(observerMode)}</div>
              <Text type="secondary">{focusHint ?? "点击节点或关系后这里会显示对象类型或上下游关系。"}</Text>
            </div>
            <div style={{ padding: "12px 14px", borderRight: "1px solid rgba(148,163,184,0.14)" }}>
              <Text type="secondary">当前值 / 说明</Text>
              <div style={{ marginTop: 6, color: "#475569" }}>
                {focusSummary ?? "点击节点或关系，右侧查看对象内容、证据摘录与处理流；节点状态会实时变化。"}
              </div>
            </div>
            <div style={{ padding: "12px 14px", background: "rgba(255,250,240,0.78)" }}>
              <Text type="secondary">阶段策略 / 图谱模式</Text>
              <Space direction="vertical" size={10} style={{ display: "flex", marginTop: 8 }}>
                <Space wrap size={[8, 8]}>
                  <Tag color={policyActionMeta[stagePolicyConfig?.default_action ?? "auto_pass"].color}>
                    默认动作：{formatPolicyActionLabel(stagePolicyConfig?.default_action ?? null)}
                  </Tag>
                  <Tag color="blue">AI：{stagePolicyConfig?.ai_mode ?? "未加载"}</Tag>
                  <Tag color="default">规则：{stagePolicyConfig?.rules.length ?? 0}</Tag>
                </Space>
                <Text type="secondary">
                  {stagePolicyConfig?.objective ?? "当前阶段的策略目标、筛选规则与动作会在这里展示。"}
                </Text>
                {stageRuleDigest.length > 0 ? (
                  <Space wrap size={[8, 8]}>
                    {stageRuleDigest.map((rule) => (
                      <Tag key={rule.key} color="gold">
                        {rule.label}
                      </Tag>
                    ))}
                  </Space>
                ) : null}
                <Segmented
                  block
                  value={graphLens}
                  onChange={(value) => onChangeGraphLens(value as GraphLens)}
                  options={[
                    { label: "主路径", value: "primary" },
                    { label: "全部", value: "all" },
                  ]}
                />
                <Space wrap size={[8, 8]}>
                  {observerMode !== "stage" ? <Button size="small" onClick={onResetFocus}>回到阶段视角</Button> : null}
                  <Tag color="success">完成</Tag>
                  <Tag color="processing">运行中</Tag>
                  <Tag color="error">阻断</Tag>
                </Space>
              </Space>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "120px minmax(0, 1fr) auto",
              gap: 12,
              padding: "12px 14px",
              border: "1px solid rgba(249,115,22,0.14)",
              borderRadius: 14,
              background: "rgba(255,247,237,0.88)",
              alignItems: "center",
            }}
          >
            <Text strong>图谱联动</Text>
            <div>
              <div style={{ fontWeight: 700, color: "#9a4e25" }}>{selectionInsight.headline}</div>
              <Text type="secondary">{selectionInsight.detail}</Text>
            </div>
            <Space wrap size={[8, 8]} style={{ justifyContent: "flex-end" }}>
              {selectionInsight.tags.map((tag) => (
                <Tag key={tag} color="orange">
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>

          <div
            style={{
              padding: "12px 14px",
              border: "1px solid rgba(245,158,11,0.18)",
              borderRadius: 14,
              background: "rgba(255,251,235,0.88)",
            }}
          >
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Text strong>动作依据说明</Text>
              <Text type="secondary">
                主路径上的连线会直接显示当前阶段默认动作与主要判断依据；规则命中、阻断原因或 AI 路由依据会优先出现在连线标签里，点击后右侧再展开完整上下文。
              </Text>
            </Space>
          </div>
        </Space>
      </div>
    </div>
  );
}

function DocumentStageGraphCanvas({
  stage,
  stagePolicyConfig,
  graphLens,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  onChangeGraphLens,
  onResetFocus,
}: {
  stage: ArchiveDocumentRuntimeStageSnapshot;
  stagePolicyConfig: ArchiveStagePolicyConfig | null;
  graphLens: GraphLens;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  onSelectNode: (id: string) => void;
  onSelectEdge: (id: string) => void;
  onChangeGraphLens: (lens: GraphLens) => void;
  onResetFocus: () => void;
}) {
  const width = 1080;
  const height = 640;
  const nodeLayouts = useMemo(() => buildRuntimeNodeLayouts(stage), [stage]);
  const positions = useMemo(
    () => buildAdaptiveStagePositions(stage, width, height, nodeLayouts),
    [height, nodeLayouts, stage, width],
  );
  const selectionState = useMemo(
    () => buildGraphSelectionState(stage, selectedNodeId, selectedEdgeId),
    [selectedEdgeId, selectedNodeId, stage],
  );
  const nodeTypes = useMemo(
    () => ({
      runtimeNode: RuntimeGraphNodeView,
      runtimeCluster: RuntimeClusterNodeView,
    }),
    [],
  );
  const [nodeAnimationFlags, setNodeAnimationFlags] = useState<Record<string, "enter" | "status-change" | "reflow">>({});
  const animationTimerIdsRef = useRef<number[]>([]);
  const previousNodeStatusRef = useRef<Map<string, ArchiveDocumentRuntimeStatus>>(new Map());
  const clusterFlowNodes = useMemo(() => buildStageClusterFlowNodes(stage, positions, nodeLayouts), [nodeLayouts, positions, stage]);
  const flowNodeBlueprint = useMemo(
    () => [
      ...clusterFlowNodes,
      ...buildStageFlowNodes(stage, positions, nodeLayouts, graphLens, selectionState, nodeAnimationFlags),
    ],
    [clusterFlowNodes, graphLens, nodeAnimationFlags, nodeLayouts, positions, selectionState, stage],
  );
  const initialFlowEdges = useMemo(
    () => buildStageFlowEdges(stage, graphLens, selectionState, positions, stagePolicyConfig),
    [graphLens, positions, selectionState, stage, stagePolicyConfig],
  );
  const layoutSignature = useMemo(
    () =>
      JSON.stringify({
        stageId: stage.stage_id,
        nodes: stage.graph.nodes.map((node) => {
          const layout = nodeLayouts.get(node.node_id);
          return [node.node_id, node.label, node.status, layout?.width ?? 0, layout?.height ?? 0, layout?.summary ?? ""];
        }),
        edges: stage.graph.edges.map((edge) => [edge.edge_id, edge.source, edge.target, edge.status]),
      }),
    [nodeLayouts, stage],
  );
  const [flowNodes, setFlowNodes, onFlowNodesChange] = useNodesState(flowNodeBlueprint);
  const [flowEdges, setFlowEdges, onFlowEdgesChange] = useEdgesState(initialFlowEdges);
  const lastLayoutSignatureRef = useRef(layoutSignature);

  function queueNodeAnimations(animationEntries: Record<string, "enter" | "status-change" | "reflow">, ttlMs: number) {
    const nodeIds = Object.keys(animationEntries);
    if (!nodeIds.length) return;

    setNodeAnimationFlags((current) => ({ ...current, ...animationEntries }));
    const timerId = window.setTimeout(() => {
      setNodeAnimationFlags((current) => {
        const next = { ...current };
        nodeIds.forEach((nodeId) => {
          if (next[nodeId] === animationEntries[nodeId]) {
            delete next[nodeId];
          }
        });
        return next;
      });
      animationTimerIdsRef.current = animationTimerIdsRef.current.filter((entry) => entry !== timerId);
    }, ttlMs);
    animationTimerIdsRef.current.push(timerId);
  }

  useEffect(() => {
    return () => {
      animationTimerIdsRef.current.forEach((timerId) => window.clearTimeout(timerId));
      animationTimerIdsRef.current = [];
    };
  }, []);

  useEffect(() => {
    const previousStatuses = previousNodeStatusRef.current;
    const nextStatuses = new Map(stage.graph.nodes.map((node) => [node.node_id, node.status] as const));
    const nextAnimations: Record<string, "enter" | "status-change"> = {};

    stage.graph.nodes.forEach((node) => {
      const previousStatus = previousStatuses.get(node.node_id);
      if (!previousStatus) {
        nextAnimations[node.node_id] = "enter";
      } else if (previousStatus !== node.status) {
        nextAnimations[node.node_id] = "status-change";
      }
    });

    previousNodeStatusRef.current = nextStatuses;
    if (Object.keys(nextAnimations).length) {
      queueNodeAnimations(nextAnimations, 820);
    }
  }, [stage]);

  useEffect(() => {
    const layoutChanged = lastLayoutSignatureRef.current !== layoutSignature;
    lastLayoutSignatureRef.current = layoutSignature;

    setFlowNodes((currentNodes) => {
      if (layoutChanged) {
        return flowNodeBlueprint;
      }

      const positionMap = new Map(currentNodes.map((node) => [node.id, node.position] as const));
      return flowNodeBlueprint.map((node) =>
        !positionMap.has(node.id)
          ? node
          : {
              ...node,
              position: positionMap.get(node.id) ?? node.position,
            },
      );
    });
  }, [flowNodeBlueprint, layoutSignature, setFlowNodes]);

  useEffect(() => {
    setFlowEdges(initialFlowEdges);
  }, [initialFlowEdges, setFlowEdges]);

  return (
    <div data-testid="document-graph-canvas">
      <div style={{ padding: "18px 20px 24px" }}>
        <div
          style={{
            position: "relative",
            minHeight: height,
            overflow: "hidden",
            borderRadius: 18,
            border: "1px solid rgba(148,163,184,0.18)",
            background:
              "radial-gradient(circle at top, rgba(251,246,238,0.96) 0%, rgba(255,255,255,0.98) 52%, rgba(255,255,255,1) 100%)",
          }}
        >
          <div
            style={{
              position: "absolute",
              right: 18,
              top: 22,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              zIndex: 3,
            }}
          >
            <Button
              type={graphLens === "primary" ? "primary" : "default"}
              style={{ borderRadius: 999, minWidth: 112 }}
              onClick={() => onChangeGraphLens("primary")}
            >
              主路径
            </Button>
            <Button
              type={graphLens === "all" ? "primary" : "default"}
              style={{ borderRadius: 999, minWidth: 112 }}
              onClick={() => onChangeGraphLens("all")}
            >
              全部
            </Button>
            <Button style={{ borderRadius: 999, minWidth: 112 }} onClick={onResetFocus}>
              复位
            </Button>
          </div>

          <ReactFlowProvider>
            <div style={{ width: "100%", height }}>
              <ReactFlow
                key={stage.stage_id}
                nodes={flowNodes}
                edges={flowEdges}
                onNodesChange={onFlowNodesChange}
                onEdgesChange={onFlowEdgesChange}
                onNodeClick={(_event, node) => {
                  if (!node.id.startsWith("cluster:")) onSelectNode(node.id);
                }}
                onEdgeClick={(_event, edge) => onSelectEdge(edge.id)}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.45}
                maxZoom={1.8}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable
                zoomOnScroll
                zoomOnPinch
                panOnDrag
                panOnScroll
                selectNodesOnDrag={false}
                connectionLineType={ConnectionLineType.Straight}
                defaultEdgeOptions={{ type: ConnectionLineType.Straight }}
                attributionPosition="bottom-left"
              >
                <GraphViewportSync layoutSignature={layoutSignature} />
                <Background gap={28} color="rgba(148,163,184,0.18)" />
                <MiniMap
                  nodeColor={(node) =>
                    node.type === "runtimeCluster"
                      ? "rgba(255,255,255,0)"
                      : (node.data as RuntimeFlowNodeData)?.primary
                        ? "#de6a42"
                        : "#cbd5e1"
                  }
                  nodeStrokeColor={(node) =>
                    node.type === "runtimeCluster"
                      ? "rgba(255,255,255,0)"
                      : statusStroke((node.data as RuntimeFlowNodeData)?.status ?? "unavailable")
                  }
                  maskColor="rgba(15,23,42,0.08)"
                  style={{
                    background: "rgba(255,255,255,0.94)",
                    border: "1px solid rgba(148,163,184,0.2)",
                    borderRadius: 12,
                  }}
                />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
          </ReactFlowProvider>

          <div
            className="runtime-graph-canvas-hint"
            style={{
              position: "absolute",
              left: 18,
              bottom: 18,
              zIndex: 3,
              padding: "8px 12px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.92)",
              border: "1px solid rgba(148,163,184,0.18)",
              color: "#64748b",
              fontSize: 12,
            }}
          >
            滚轮可缩放，拖动画布可平移；默认展示当前阶段的全部节点与关系。
          </div>
        </div>
      </div>
    </div>
  );
}

function DocumentObserverPanel({
  observer,
  mode,
  onChangeMode,
  focusLabel,
  focusHint,
  focusSummary,
  scopeLabel,
}: {
  observer: ArchiveDocumentRuntimeObserverPayload | null;
  mode: ObserverMode;
  onChangeMode: (mode: ObserverMode) => void;
  focusLabel: string;
  focusHint?: string;
  focusSummary?: string | null;
  scopeLabel: string;
}) {
  if (!observer) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={4} style={{ marginTop: 0 }}>
          对象观察窗
        </Title>
        <Empty description="点击节点或边，右侧查看该对象的上下文、证据与状态流。" />
      </div>
    );
  }

  const usedSectionIds = new Set<string>();
  const payloadSection =
    observer.sections.find((section) => /载荷|payload|对象/i.test(section.title)) ??
    observer.sections.find((section) => !/证据|原文|快照|状态/i.test(section.title)) ??
    observer.sections[0] ??
    null;
  if (payloadSection) usedSectionIds.add(payloadSection.section_id);

  const evidenceSection =
    observer.sections.find((section) => !usedSectionIds.has(section.section_id) && /证据|原文|evidence/i.test(section.title)) ??
    null;
  if (evidenceSection) usedSectionIds.add(evidenceSection.section_id);

  const snapshotSections = observer.sections.filter((section) => !usedSectionIds.has(section.section_id));
  const focusPrefix = mode === "edge" ? "已选边" : mode === "node" ? "已选对象" : "当前阶段";

  function renderSectionFields(section: ArchiveDocumentRuntimeObserverPayload["sections"][number] | null) {
    if (!section) return <Text type="secondary">当前没有可展示的结构化字段。</Text>;
    return (
      <Space direction="vertical" size={10} style={{ display: "flex" }}>
        {section.fields.map((field) => (
          <div
            key={field.key}
            style={{
              display: "grid",
              gridTemplateColumns: "110px minmax(0, 1fr)",
              gap: 10,
            }}
          >
            <Text type="secondary">{field.label}</Text>
            <Text style={{ color: summaryToneColor(field.tone) }}>{field.value}</Text>
          </div>
        ))}
      </Space>
    );
  }

  return (
    <div style={{ height: "100%", padding: "22px 22px 24px", background: "#fff" }}>
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <div>
          <Title level={4} style={{ margin: "0 0 14px" }}>
            对象观察窗
          </Title>
          <Space direction="vertical" size={6} style={{ display: "flex" }}>
            <Text strong style={{ fontSize: 18, color: "#8a4b2d" }}>
              {focusPrefix}：{focusLabel}
            </Text>
            <Text type="secondary">{focusSummary ?? observer.subtitle ?? "滚动查看对象内容、证据摘录与状态流。"}</Text>
          </Space>
          <Space wrap size={[8, 8]} style={{ marginTop: 12 }}>
            <Tag color="blue">{formatObserverModeLabel(mode)}</Tag>
            <Tag color={runtimeStatusMeta[observer.status].color}>{runtimeStatusMeta[observer.status].label}</Tag>
            <Tag color="default">{scopeLabel}</Tag>
            {focusHint ? <Tag>{focusHint}</Tag> : null}
          </Space>
        </div>

        <div
          style={{
            padding: 14,
            border: "1px solid rgba(148,163,184,0.2)",
            borderRadius: 14,
            background: "#fff",
          }}
        >
          <Space direction="vertical" size={10} style={{ display: "flex" }}>
            <Text type="secondary">可滚动查看完整对象内容、证据与状态流。</Text>
            <Segmented
              block
              value={mode}
              onChange={(value) => onChangeMode(value as ObserverMode)}
              options={[
                { label: "阶段视角", value: "stage" },
                { label: "节点视角", value: "node" },
                { label: "边视角", value: "edge" },
              ]}
            />
          </Space>
        </div>

        <div
          style={{
            padding: 16,
            border: "1px solid rgba(148,163,184,0.2)",
            borderRadius: 14,
            background: "linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(250,250,249,0.98) 100%)",
          }}
        >
          <Text strong style={{ display: "block", marginBottom: 12 }}>
            对象载荷
          </Text>
          {renderSectionFields(payloadSection)}
        </div>

        <div
          style={{
            padding: 16,
            border: "1px solid rgba(234,179,8,0.28)",
            borderRadius: 14,
            background: "rgba(255,251,235,0.78)",
          }}
        >
          <Text strong style={{ display: "block", marginBottom: 12 }}>
            原文与证据
          </Text>
          {evidenceSection ? (
            renderSectionFields(evidenceSection)
          ) : (
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Text>{observer.subtitle ?? "当前对象暂无单独证据区块，先展示观察窗摘要。"}</Text>
              <Text type="secondary">{focusHint ?? "点击节点或边后，这里会优先承接原文摘录和证据路径。"}</Text>
            </Space>
          )}
        </div>

        <div
          style={{
            padding: 16,
            border: "1px solid rgba(234,179,8,0.24)",
            borderRadius: 14,
            background: "rgba(254,252,232,0.8)",
          }}
        >
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
              <Text strong>该对象的实时处理流</Text>
              <Text type="secondary">{observer.stream.length} 条事件</Text>
            </Space>
            {observer.stream.length > 0 ? (
              <Space direction="vertical" size={10} style={{ display: "flex" }}>
                {observer.stream.map((event) => (
                  <div key={event.event_id} style={{ display: "grid", gridTemplateColumns: "72px minmax(0, 1fr)", gap: 12 }}>
                    <Text type="secondary">{event.timestamp ? formatDateTime(event.timestamp) : event.kind}</Text>
                    <Text style={{ color: eventLevelColor(event.level) }}>{event.message}</Text>
                  </div>
                ))}
              </Space>
            ) : (
              <Text type="secondary">当前对象还没有可展示的处理流。</Text>
            )}
          </Space>
        </div>

        <div
          style={{
            padding: 16,
            border: "1px solid rgba(148,163,184,0.2)",
            borderRadius: 14,
            background: "#fff",
          }}
        >
          <Text strong style={{ display: "block", marginBottom: 12 }}>
            对象状态快照
          </Text>
          {snapshotSections.length > 0 ? (
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              {snapshotSections.map((section) => (
                <div key={section.section_id}>
                  <Text strong style={{ display: "block", marginBottom: 8 }}>
                    {section.title}
                  </Text>
                  {renderSectionFields(section)}
                </div>
              ))}
            </Space>
          ) : (
            <Text type="secondary">当前对象没有额外快照，已在上方展示主摘要。</Text>
          )}
        </div>

        {observer.actions.length > 0 ? (
          <div
            style={{
              padding: 16,
              border: "1px solid rgba(148,163,184,0.2)",
              borderRadius: 14,
              background: "#fff",
            }}
          >
            <Text strong style={{ display: "block", marginBottom: 12 }}>
              动作入口
            </Text>
            <Space wrap>
              {observer.actions.map((action) => (
                <Button key={action.action_id} type={action.target_kind === "graph" ? "primary" : "default"}>
                  {action.label}
                </Button>
              ))}
            </Space>
          </div>
        ) : null}
      </Space>
    </div>
  );
}

function OverviewView(props: {
  archives: KnowledgeArchive[];
  activeArchiveId: string | null;
  pendingItems: PendingItem[];
  onOpenArchive: (archiveId: string) => void;
  onOpenGlobal: () => void;
  onOpenPolicy: () => void;
  onExtract: (archiveId: string) => void;
  onSetCurrent: (archiveId: string) => void;
  onShowCreate: () => void;
  extractingArchiveId: string | null;
}) {
  const activeArchive =
    props.archives.find((archive) => archive.archive_id === props.activeArchiveId) ?? props.archives[0] ?? null;
  const readyCount = props.archives.filter((archive) => archive.status === "ready").length;
  const blockedCount = props.archives.filter((archive) => archive.status === "error").length;

  const columns: ColumnsType<KnowledgeArchive> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.name}</Text>
          <Text type="secondary">{record.archive_id}</Text>
        </Space>
      ),
    },
    {
      title: "状态",
      key: "status",
      render: (_value, record) => (
        <Space wrap>
          <Tag color={archiveStatusMeta[record.status].color}>{archiveStatusMeta[record.status].label}</Tag>
          <Tag color={record.is_active ? "blue" : "default"}>{record.is_active ? "当前激活" : "未激活"}</Tag>
        </Space>
      ),
    },
    {
      title: "源目录",
      dataIndex: "source_dir",
      key: "source_dir",
      ellipsis: true,
    },
    {
      title: "最近运行",
      key: "latest",
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Text>{formatDateTime(record.last_built_at)}</Text>
          <Text type="secondary">{getArchiveStageLabel(record)}</Text>
        </Space>
      ),
    },
    {
      title: "结果摘要",
      key: "summary",
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Text>
            文档 {record.summary?.document_count ?? 0} / 实体 {record.summary?.entity_count ?? 0} / 流程 {record.summary?.process_count ?? 0}
          </Text>
          {record.build_state?.warning_count ? (
            <Text type="warning">待治理 {record.build_state.warning_count} 条</Text>
          ) : record.last_error ? (
            <Text type="danger">{record.last_error}</Text>
          ) : (
            <Text type="secondary">当前无额外告警</Text>
          )}
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_value, record) => (
        <Space wrap>
          <Button onClick={() => props.onOpenArchive(record.archive_id)}>进入单知识库</Button>
          {!record.is_active ? <Button onClick={() => props.onSetCurrent(record.archive_id)}>设为当前</Button> : null}
          <Button
            loading={props.extractingArchiveId === record.archive_id || record.status === "extracting"}
            onClick={() => props.onExtract(record.archive_id)}
          >
            立即抽取
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <ValidationWorkspace
      title="知识库运行总览"
      description="这里统一查看知识库状态、待处理事项，并从总览进入全局并行、单知识库运行和策略/质量页面。"
      actions={
        <Space wrap>
          <Button onClick={props.onOpenGlobal}>全局并行</Button>
          <Button onClick={props.onOpenPolicy}>策略与配置</Button>
          <Button type="primary" onClick={props.onShowCreate}>
            新建知识库
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <WorkspaceOverviewStrip
          badgeLabel="知识库管理"
          title="知识库运行总览"
          tags={
            activeArchive
              ? [
                  { label: `当前知识库：${activeArchive.name}` },
                  { label: `当前状态：${archiveStatusMeta[activeArchive.status].label}` },
                  { label: `待处理：${props.pendingItems.length}` },
                ]
              : []
          }
          metrics={[
            { title: "知识库数量", value: props.archives.length },
            { title: "可用知识库", value: readyCount },
            { title: "异常知识库", value: blockedCount },
            { title: "待处理事项", value: props.pendingItems.length },
          ]}
        />
        {props.pendingItems.length > 0 ? (
          <Alert
            type="warning"
            showIcon
            message={`当前有 ${props.pendingItems.length} 条待处理事项`}
            description={props.pendingItems.map((item) => item.title).join("；")}
          />
        ) : null}
        <Table rowKey="archive_id" columns={columns} dataSource={props.archives} pagination={false} />
      </Space>
    </ValidationWorkspace>
  );
}

function GlobalView(props: {
  archives: KnowledgeArchive[];
  onBack: () => void;
  onOpenArchive: (archiveId: string) => void;
  onOpenPolicy: () => void;
}) {
  return (
    <ValidationWorkspace
      title="全局并行运行"
      description="这里看多个知识库在接入、解析、证据、规范、门禁和发布等维度上的整体运行态。"
      actions={
        <Space wrap>
          <Button onClick={props.onBack}>返回总览</Button>
          <Button onClick={props.onOpenPolicy}>查看策略/质量</Button>
        </Space>
      }
    >
      <Row gutter={[16, 16]}>
        {props.archives.map((archive) => {
          const done = archive.build_state?.completed_document_ids.length ?? 0;
          const pending = archive.build_state?.pending_document_ids.length ?? 0;
          const warnings = archive.build_state?.warning_count ?? 0;
          const total = archive.summary?.document_count ?? Math.max(done + pending, 0);
          return (
            <Col key={archive.archive_id} xs={24} lg={12}>
              <Card
                title={archive.name}
                extra={<Tag color={archiveStatusMeta[archive.status].color}>{archiveStatusMeta[archive.status].label}</Tag>}
              >
                <Space direction="vertical" size={12} style={{ display: "flex" }}>
                  <Row gutter={12}>
                    <Col span={8}><Statistic title="已完成" value={done} /></Col>
                    <Col span={8}><Statistic title="待处理" value={pending} /></Col>
                    <Col span={8}><Statistic title="告警" value={warnings} /></Col>
                  </Row>
                  <Progress percent={total > 0 ? Math.round((done / total) * 100) : 0} status={archive.status === "error" ? "exception" : archive.status === "ready" ? "success" : "active"} />
                  <Descriptions size="small" column={1} colon={false}>
                    <Descriptions.Item label="当前阶段">{getArchiveStageLabel(archive)}</Descriptions.Item>
                    <Descriptions.Item label="最近运行">{formatDateTime(archive.last_built_at)}</Descriptions.Item>
                  </Descriptions>
                  <Button onClick={() => props.onOpenArchive(archive.archive_id)}>进入单知识库</Button>
                </Space>
              </Card>
            </Col>
          );
        })}
      </Row>
    </ValidationWorkspace>
  );
}

function ArchiveView(props: {
  archive: KnowledgeArchive;
  onBackOverview: () => void;
  onBackGlobal: () => void;
  onOpenDocument: (documentId: string) => void;
  onOpenPolicy: () => void;
}) {
  const documents = props.archive.build_state?.documents ?? [];
  const policySnapshot = props.archive.build_state?.policy_snapshot ?? null;
  const columns: ColumnsType<KnowledgeArchiveBuildStateDocument> = [
    {
      title: "文档",
      dataIndex: "title",
      key: "title",
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.title}</Text>
          <Text type="secondary">{record.file_type.toUpperCase()}</Text>
        </Space>
      ),
    },
    {
      title: "当前状态",
      key: "state",
      render: (_value, record) => <Tag color={documentStateMeta[record.state].color}>{documentStateMeta[record.state].label}</Tag>,
    },
    {
      title: "处理阶段",
      key: "phase",
      render: (_value, record) => <Text>{record.document_id === props.archive.build_state?.current_document_id ? "当前处理中" : "等待调度"}</Text>,
    },
    {
      title: "风险摘要",
      key: "risk",
      render: (_value, record) => {
        if (record.state === "failed") return <Text type="danger">处理失败</Text>;
        if (record.state === "skipped") return <Text type="warning">已跳过</Text>;
        if (record.document_id === props.archive.build_state?.current_document_id) return <Text type="warning">当前焦点文档</Text>;
        return <Text type="secondary">无额外风险</Text>;
      },
    },
    {
      title: "操作",
      key: "action",
      render: (_value, record) => <Button onClick={() => props.onOpenDocument(record.document_id)}>进入单文档</Button>,
    },
  ];

  return (
    <ValidationWorkspace
      title={`单知识库运行 · ${props.archive.name}`}
      description="这里看一个知识库内部的多文档流转、堆积、失败、待补证据和待治理状态。"
      actions={
        <Space wrap>
          <Button onClick={props.onBackOverview}>返回总览</Button>
          <Button onClick={props.onBackGlobal}>返回全局并行</Button>
          <Button onClick={props.onOpenPolicy}>查看策略/质量</Button>
        </Space>
      }
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Row gutter={16}>
          <Col span={6}><Card><Statistic title="文档总数" value={props.archive.summary?.document_count ?? documents.length} /></Card></Col>
          <Col span={6}><Card><Statistic title="已完成" value={props.archive.build_state?.completed_document_ids.length ?? 0} /></Card></Col>
          <Col span={6}><Card><Statistic title="待处理" value={props.archive.build_state?.pending_document_ids.length ?? 0} /></Card></Col>
          <Col span={6}><Card><Statistic title="告警" value={props.archive.build_state?.warning_count ?? 0} /></Card></Col>
        </Row>
        <Alert
          type={props.archive.status === "error" ? "error" : "info"}
          showIcon
          message={getArchiveStageLabel(props.archive)}
          description={props.archive.last_error ?? `当前文档群共 ${documents.length} 篇，点进单文档可查看对象级运行态。`}
        />
        {policySnapshot ? (
          <Card size="small">
            <Space wrap size={[8, 8]}>
              <Tag color="blue">当前运行策略</Tag>
              <Text strong>{formatPolicySnapshotHeadline(policySnapshot)}</Text>
              <Text type="secondary">{formatPolicySnapshotHint(policySnapshot)}</Text>
            </Space>
          </Card>
        ) : null}
        <Table rowKey="document_id" columns={columns} dataSource={documents} pagination={false} />
      </Space>
    </ValidationWorkspace>
  );
}

function DocumentView(props: {
  document: KnowledgeArchiveBuildStateDocument;
  runtime: ArchiveDocumentRuntimeContract | null;
  policyConfig: ArchivePolicyConfig | null;
  runtimeTransportState: RuntimeTransportState;
  loading: boolean;
  error: string | null;
  inspectedStageId: string | null;
  setInspectedStageId: (value: string | null) => void;
  selectedNodeId: string | null;
  setSelectedNodeId: (value: string | null) => void;
  selectedEdgeId: string | null;
  setSelectedEdgeId: (value: string | null) => void;
  observerMode: ObserverMode;
  setObserverMode: (mode: ObserverMode) => void;
  onBackArchive: () => void;
  onBackGlobal: () => void;
  onOpenPolicy: () => void;
}) {
  const [graphLens, setGraphLens] = useState<GraphLens>("all");
  const liveCurrentStage = props.runtime ? getLiveCurrentStage(props.runtime) : null;
  const inspectedStage = props.runtime ? getInspectedStage(props.runtime, props.inspectedStageId) : null;
  const inspectedStagePolicyConfig = inspectedStage ? getStagePolicyConfig(props.policyConfig, inspectedStage.stage_id) : null;
  const selectedNode =
    inspectedStage && props.selectedNodeId
      ? inspectedStage.graph.nodes.find((node) => node.node_id === props.selectedNodeId) ?? null
      : null;
  const selectedEdge =
    inspectedStage && props.selectedEdgeId
      ? inspectedStage.graph.edges.find((edge) => edge.edge_id === props.selectedEdgeId) ?? null
      : null;
  const graphSelectionState = useMemo(
    () => (inspectedStage ? buildGraphSelectionState(inspectedStage, props.selectedNodeId, props.selectedEdgeId) : null),
    [inspectedStage, props.selectedEdgeId, props.selectedNodeId],
  );

  const observer = useMemo(() => {
    if (!inspectedStage) return null;
    if (props.observerMode === "node" && props.selectedNodeId) return inspectedStage.node_observers[props.selectedNodeId] ?? inspectedStage.stage_observer;
    if (props.observerMode === "edge" && props.selectedEdgeId) return inspectedStage.edge_observers[props.selectedEdgeId] ?? inspectedStage.stage_observer;
    return inspectedStage.stage_observer;
  }, [inspectedStage, props.observerMode, props.selectedEdgeId, props.selectedNodeId]);
  const selectedNodeLabelMap = new Map(inspectedStage?.graph.nodes.map((node) => [node.node_id, node.label]) ?? []);
  const inspectedStageLabel = inspectedStage ? getStageDisplayLabel(inspectedStage.stage_id, inspectedStage.label) : null;
  const currentStageLabel = props.runtime
    ? getStageDisplayLabel(props.runtime.current_stage_id, props.runtime.current_stage_label)
      : "运行中";
  const transportMeta = runtimeTransportMeta[props.runtimeTransportState];
  const focusLabel =
    props.observerMode === "node" && selectedNode
      ? selectedNode.label
      : props.observerMode === "edge" && selectedEdge
        ? `${selectedEdge.relation} #${selectedEdge.edge_id}`
        : inspectedStageLabel ?? "当前阶段";
  const focusHint =
    props.observerMode === "node" && selectedNode
      ? selectedNode.node_type
      : props.observerMode === "edge" && selectedEdge
        ? `${selectedNodeLabelMap.get(selectedEdge.source) ?? selectedEdge.source} → ${selectedNodeLabelMap.get(selectedEdge.target) ?? selectedEdge.target}`
        : inspectedStage
          ? getStageGroupDisplayLabel(inspectedStage)
          : undefined;
  const focusSummary =
    props.observerMode === "node" && selectedNode
      ? summarizeRecord(selectedNode.metrics) ?? summarizeRecord(selectedNode.attributes) ?? `对象类型：${selectedNode.node_type}`
      : props.observerMode === "edge" && selectedEdge
        ? summarizeRecord(selectedEdge.attributes) ??
          `${selectedNodeLabelMap.get(selectedEdge.source) ?? selectedEdge.source} → ${selectedNodeLabelMap.get(selectedEdge.target) ?? selectedEdge.target}`
        : inspectedStage
          ? `当前查看：${inspectedStageLabel} / 阶段状态：${runtimeStatusMeta[inspectedStage.status].label} / 节点 ${inspectedStage.graph.nodes.length} / 边 ${inspectedStage.graph.edges.length}`
          : null;
  const selectionInsight = useMemo(() => {
    if (!inspectedStage || !graphSelectionState) {
      return {
        headline: "当前没有可联动的图谱对象",
        detail: "进入某个阶段后，继续点击节点或边即可查看上下游联动。",
        tags: ["等待选择"],
      };
    }

    if (selectedNode) {
      return {
        headline: `已高亮“${selectedNode.label}”及其直接关系`,
        detail: "主选中节点保持最高亮度，邻接节点和相连边作为第二层上下文同步联动右侧观察窗。",
        tags: [
          `关联节点 ${graphSelectionState.relatedNodeIds.size}`,
          `关联边 ${graphSelectionState.relatedEdgeIds.size}`,
          `节点类型 ${selectedNode.node_type}`,
          inspectedStagePolicyConfig ? `默认动作 ${formatPolicyActionLabel(inspectedStagePolicyConfig.default_action)}` : "策略待加载",
        ],
      };
    }

    if (selectedEdge) {
      return {
        headline: `已高亮边“${selectedEdge.relation}”的两端对象`,
        detail: "当前边保持主高亮，两端节点和相邻关系会被带亮，便于顺着因果链继续追踪。",
        tags: [
          `端点 ${graphSelectionState.activeNodeIds.size}`,
          `邻接节点 ${graphSelectionState.relatedNodeIds.size}`,
          `邻接边 ${graphSelectionState.relatedEdgeIds.size}`,
          inspectedStagePolicyConfig ? `规则 ${inspectedStagePolicyConfig.rules.length}` : "策略待加载",
        ],
      };
    }

    return {
      headline: "当前处于阶段总览焦点",
      detail: "默认高亮当前阶段的焦点节点与直接上下游；点击节点或边后会切换到更强的对象联动层级。",
      tags: [
        `焦点节点 ${graphSelectionState.activeNodeIds.size}`,
        `上下游节点 ${graphSelectionState.relatedNodeIds.size}`,
        `主链边 ${inspectedStage.graph.primary_edge_ids.length || inspectedStage.graph.edges.filter((edge) => edge.is_primary).length}`,
        inspectedStagePolicyConfig ? `AI ${inspectedStagePolicyConfig.ai_mode}` : "策略待加载",
      ],
    };
  }, [graphSelectionState, inspectedStage, inspectedStageLabel, inspectedStagePolicyConfig, selectedEdge, selectedNode]);

  return (
    <ValidationWorkspace
      title={`${props.document.title} · 单文档下钻 · ${currentStageLabel} ${liveCurrentStage ? runtimeStatusMeta[liveCurrentStage.status].label : ""}`.trim()}
      description="当前视图展示：13 阶段切换 + 当前阶段图谱 + 对象观察窗。"
      actions={
        <Space wrap>
          <Button onClick={props.onOpenPolicy}>查看规则</Button>
          <Button onClick={props.onBackArchive}>返回单知识库</Button>
          <Button onClick={props.onBackGlobal}>返回全局并行</Button>
        </Space>
      }
    >
      {props.loading ? (
        <Card loading />
      ) : props.error ? (
        <Alert type="error" showIcon message="单文档运行数据加载失败" description={props.error} />
      ) : !props.runtime || !liveCurrentStage || !inspectedStage ? (
        <Empty description="当前没有可展示的单文档运行数据" />
      ) : (
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <DocumentFlowFigureNavigation
            runtime={props.runtime}
            inspectedStageId={props.inspectedStageId}
            onSelectStage={(stageId) => {
              props.setInspectedStageId(stageId);
              props.setSelectedNodeId(null);
              props.setSelectedEdgeId(null);
              props.setObserverMode("stage");
            }}
          />
          <DocumentRuntimeSummaryStrip
            runtime={props.runtime}
            liveCurrentStage={liveCurrentStage}
            inspectedStage={inspectedStage}
            focusLabel={focusLabel}
            focusHint={focusHint}
            transportState={props.runtimeTransportState}
          />
          {inspectedStage.stage_id !== liveCurrentStage.stage_id ? (
            <Alert
              type="info"
              showIcon
              message={`当前正在查看 ${inspectedStageLabel} 的阶段快照`}
              description={`实时当前阶段仍为 ${currentStageLabel}，流程导航会持续跟随后端进度更新。`}
            />
          ) : null}
          <Card size="small">
            <Space wrap size={[8, 8]}>
              <Tag color={props.runtime.policy_snapshot ? "gold" : "default"}>运行策略快照</Tag>
              <Text strong>{formatPolicySnapshotHeadline(props.runtime.policy_snapshot)}</Text>
              <Text type="secondary">{formatPolicySnapshotHint(props.runtime.policy_snapshot)}</Text>
            </Space>
          </Card>
          <Alert
            showIcon
            type={
              props.runtimeTransportState === "stream_connected"
                ? "success"
                : props.runtimeTransportState === "polling_fallback"
                  ? "warning"
                  : "info"
            }
            message={`实时运行通道：${transportMeta.label}`}
            description={
              props.runtimeTransportState === "stream_connected"
                ? `${transportMeta.hint}；如果链路中断，页面会自动回退到快照轮询。`
                : props.runtimeTransportState === "polling_fallback"
                  ? `${transportMeta.hint}；当前仍会持续刷新流程、图谱和观察窗。`
                  : transportMeta.hint
            }
          />
          <div
            style={{
              border: "2px solid rgba(59,130,246,0.72)",
              borderRadius: 22,
              background: "#fff",
              overflow: "hidden",
              boxShadow: "0 18px 36px rgba(59,130,246,0.08)",
            }}
          >
            <Row gutter={0} align="stretch">
              <Col xs={24} xl={16} style={{ borderRight: "1px dashed rgba(59,130,246,0.56)" }}>
                <DocumentGraphControlPanel
                  stage={inspectedStage}
                  stagePolicyConfig={inspectedStagePolicyConfig}
                  graphLens={graphLens}
                  onChangeGraphLens={setGraphLens}
                  observerMode={props.observerMode}
                  focusLabel={focusLabel}
                  focusHint={focusHint}
                  focusSummary={focusSummary}
                  selectionInsight={selectionInsight}
                  onResetFocus={() => {
                    props.setSelectedNodeId(null);
                    props.setSelectedEdgeId(null);
                    props.setObserverMode("stage");
                  }}
                />
                <DocumentStageGraphCanvas
                  stage={inspectedStage}
                  stagePolicyConfig={inspectedStagePolicyConfig}
                  graphLens={graphLens}
                  selectedNodeId={props.selectedNodeId}
                  selectedEdgeId={props.selectedEdgeId}
                  onSelectNode={(id) => {
                    props.setSelectedNodeId(id);
                    props.setSelectedEdgeId(null);
                    props.setObserverMode("node");
                  }}
                  onSelectEdge={(id) => {
                    props.setSelectedEdgeId(id);
                    props.setSelectedNodeId(null);
                    props.setObserverMode("edge");
                  }}
                  onChangeGraphLens={setGraphLens}
                  onResetFocus={() => {
                    props.setSelectedNodeId(null);
                    props.setSelectedEdgeId(null);
                    props.setObserverMode("stage");
                  }}
                />
              </Col>
              <Col xs={24} xl={8}>
                <DocumentObserverPanel
                  observer={observer}
                  mode={props.observerMode}
                  onChangeMode={props.setObserverMode}
                  focusLabel={focusLabel}
                  focusHint={focusHint}
                  focusSummary={focusSummary}
                  scopeLabel={`单文档 · ${props.document.title}`}
                />
              </Col>
            </Row>
          </div>
        </Space>
      )}
    </ValidationWorkspace>
  );
}

function PolicyWorkbenchView({
  onBackOverview,
  onOpenGlobal,
}: {
  onBackOverview: () => void;
  onOpenGlobal: () => void;
}) {
  const policyActionColorMap = {
    自动放行: "success",
    告警继续: "warning",
    转人工复核: "processing",
    阻断并回退: "error",
    延迟发布: "default",
  } as const;

  type PolicyActionLabel = keyof typeof policyActionColorMap;
  type PolicyStageRule = {
    key: string;
    name: string;
    meaning: string;
    threshold: string;
    action: PolicyActionLabel;
  };
  type PolicyStageConfig = {
    objective: string;
    aiMode: string;
    defaultAction: PolicyActionLabel;
    inputs: string[];
    aiAdaptation: string;
    rules: PolicyStageRule[];
    branches: string[];
    outputs: string[];
    observability: string[];
  };

  const policyStageConfigs: Record<string, PolicyStageConfig> = {
    asset_intake: {
      objective: "确认素材可被接入，并在第一时间给出格式、语种、来源和结构风险画像。",
      aiMode: "轻量识别 + 规则兜底",
      defaultAction: "阻断并回退",
      inputs: ["原始文件流", "归档接入白名单", "文档元数据与命名约定"],
      aiAdaptation: "AI 负责识别文档形态、语言与潜在扫描质量，自动决定是否进入 OCR 增强或直接进入解析路由。",
      rules: [
        { key: "asset-1", name: "接入格式完整性", meaning: "文件必须可读取且存在稳定 MIME 类型", threshold: "mime_type in allowlist && size > 0", action: "阻断并回退" },
        { key: "asset-2", name: "来源可信度标签", meaning: "缺少来源标签时先降级接入并标记告警", threshold: "source_label missing -> warn", action: "告警继续" },
        { key: "asset-3", name: "扫描件预处理分流", meaning: "扫描件优先切入 OCR 强化链路", threshold: "scan_score >= 0.6", action: "自动放行" },
      ],
      branches: ["扫描件 -> OCR 预处理", "结构完整 -> 进入解析路由", "格式损坏 -> 直接阻断并回退素材池"],
      outputs: ["接入质量标签", "文档类型初判", "语言/版式提示", "解析前预处理决策"],
      observability: ["mime_type", "language_hint", "scan_score", "source_label", "intake_risk"],
    },
    parser_router: {
      objective: "为当前文档挑选最合适的解析器组合，避免模板、版式、语种选错。",
      aiMode: "解析器路由建议",
      defaultAction: "自动放行",
      inputs: ["接入质量标签", "文档类型初判", "解析器能力矩阵"],
      aiAdaptation: "AI 结合文件结构、文本密度和图文比例，为版式解析、表格增强、OCR 复核等能力自动排序。",
      rules: [
        { key: "router-1", name: "主解析器命中率", meaning: "优先选择历史命中率最高的解析器", threshold: "top_parser_confidence >= 0.75", action: "自动放行" },
        { key: "router-2", name: "多语种切换", meaning: "检测到双语或术语集时补挂语言模型", threshold: "language_mix >= 2", action: "告警继续" },
        { key: "router-3", name: "未知版式", meaning: "未知模板先退回保守解析链", threshold: "template_match < 0.45", action: "转人工复核" },
      ],
      branches: ["已知模板 -> 高速解析链", "双语文档 -> 多语解析链", "未知版式 -> 保守解析链 + 人工复核候选"],
      outputs: ["解析器选择结果", "模板匹配结果", "增强能力挂载列表"],
      observability: ["parser_choice", "template_match", "language_mix", "router_confidence"],
    },
    parser_execution: {
      objective: "稳定产出结构化解析结果，并对缺页、乱码、表格裂解等问题做补偿。",
      aiMode: "结构修复辅助",
      defaultAction: "告警继续",
      inputs: ["解析器选择结果", "原始文件流", "预处理增强配置"],
      aiAdaptation: "AI 对表格断裂、段落连缀和标题层级错乱进行结构修复，尽量把解析结果拉回统一对象契约。",
      rules: [
        { key: "exec-1", name: "正文提取覆盖率", meaning: "正文覆盖率过低时直接阻断", threshold: "body_coverage >= 0.7", action: "阻断并回退" },
        { key: "exec-2", name: "表格裂解修复", meaning: "表格字段裂解时自动调用结构修复", threshold: "table_split_score >= 0.5", action: "自动放行" },
        { key: "exec-3", name: "乱码恢复", meaning: "乱码比例超阈值则进入告警并保留原文比对", threshold: "garbled_ratio > 0.08", action: "告警继续" },
      ],
      branches: ["解析稳定 -> 统一文档对象", "表格裂解 -> 结构修复后继续", "正文缺失 -> 阻断并回退路由"],
      outputs: ["结构化正文", "表格与附件提取物", "修复日志", "段落层级结果"],
      observability: ["body_coverage", "table_split_score", "garbled_ratio", "repair_count"],
    },
    unified_document_object: {
      objective: "把多来源解析结果压成统一文档对象，为后续证据构造提供稳定输入契约。",
      aiMode: "对象整编与字段对齐",
      defaultAction: "自动放行",
      inputs: ["结构化正文", "表格与附件提取物", "文档对象 schema"],
      aiAdaptation: "AI 把标题、段落、表格、注释和附件引用统一到标准字段，并给出字段缺失补全建议。",
      rules: [
        { key: "udo-1", name: "统一对象完整度", meaning: "核心字段不齐全时不进入证据层", threshold: "required_fields >= 95%", action: "阻断并回退" },
        { key: "udo-2", name: "段落层级修正", meaning: "层级冲突时按标准目录结构重排", threshold: "heading_conflict > 0", action: "自动放行" },
        { key: "udo-3", name: "附件引用绑定", meaning: "附件无法绑定正文时发出告警", threshold: "attachment_bind_rate < 0.85", action: "告警继续" },
      ],
      branches: ["对象完整 -> 证据构造", "字段缺失 -> 阻断回退解析执行", "附件弱绑定 -> 告警继续"],
      outputs: ["统一文档对象", "结构完整度评分", "字段缺失清单"],
      observability: ["schema_score", "heading_conflict", "attachment_bind_rate", "missing_fields"],
    },
    evidence_constructor: {
      objective: "从统一文档对象中切出可追溯的证据段、证据块和原文锚点。",
      aiMode: "证据片段定位",
      defaultAction: "自动放行",
      inputs: ["统一文档对象", "证据抽取模板", "锚点定位策略"],
      aiAdaptation: "AI 按语义边界和章节结构切出证据片段，并为每个片段补上原文坐标与上下文摘要。",
      rules: [
        { key: "evi-1", name: "证据片段最小上下文", meaning: "证据必须保留前后文窗口", threshold: "context_window >= 2", action: "自动放行" },
        { key: "evi-2", name: "锚点可回溯性", meaning: "没有原文锚点的证据不能进入图谱", threshold: "anchor_present = true", action: "阻断并回退" },
        { key: "evi-3", name: "重复证据折叠", meaning: "重复证据先折叠后再进入图谱层", threshold: "duplicate_ratio > 0.2", action: "告警继续" },
      ],
      branches: ["证据稳定 -> 图谱/切块层", "锚点缺失 -> 回退统一对象修复", "重复率过高 -> 折叠后告警继续"],
      outputs: ["证据片段集", "原文锚点", "证据上下文摘要"],
      observability: ["evidence_count", "anchor_present_rate", "duplicate_ratio", "context_window"],
    },
    evidence_graph_chunk_layer: {
      objective: "把证据片段组织成图谱节点和切块单元，为候选知识生成准备结构化上下文。",
      aiMode: "图谱切块编排",
      defaultAction: "自动放行",
      inputs: ["证据片段集", "图谱建模模板", "切块窗口策略"],
      aiAdaptation: "AI 依据实体密度、关系紧密度和章节边界自动生成图谱节点与 chunk 分层。",
      rules: [
        { key: "graph-1", name: "切块密度控制", meaning: "单块证据过密时自动拆块", threshold: "chunk_token <= 1200", action: "自动放行" },
        { key: "graph-2", name: "跨章混块保护", meaning: "跨章证据默认不直接混块", threshold: "cross_section_ratio <= 0.25", action: "告警继续" },
        { key: "graph-3", name: "节点孤立率", meaning: "孤立节点过高时要求回看证据构造", threshold: "orphan_node_ratio <= 0.18", action: "转人工复核" },
      ],
      branches: ["切块稳定 -> 证据包", "跨章混块 -> 保守拆分继续", "孤立率过高 -> 标记人工复核"],
      outputs: ["证据图谱节点", "chunk 分层结果", "关系候选边"],
      observability: ["chunk_token", "cross_section_ratio", "orphan_node_ratio", "relation_density"],
    },
    evidence_pack: {
      objective: "把图谱节点、chunk 与原文证据打包成可供后续 AI 审查的标准证据包。",
      aiMode: "证据包编排与压缩",
      defaultAction: "自动放行",
      inputs: ["证据图谱节点", "chunk 分层结果", "关系候选边"],
      aiAdaptation: "AI 根据审查阶段需要，自动裁剪主证据、补证据和风险说明，生成紧凑可读的证据包。",
      rules: [
        { key: "pack-1", name: "主证据齐备", meaning: "每个候选对象至少携带主证据与补充证据", threshold: "support_doc_count >= 2", action: "告警继续" },
        { key: "pack-2", name: "证据包长度", meaning: "过长的证据包自动摘要压缩", threshold: "pack_token <= 1800", action: "自动放行" },
        { key: "pack-3", name: "引用闭环", meaning: "引用链必须能回到原文锚点", threshold: "citation_closed = true", action: "阻断并回退" },
      ],
      branches: ["证据包稳定 -> 三条审查支路", "证据过长 -> 摘要压缩继续", "引用断裂 -> 回退图谱层"],
      outputs: ["标准证据包", "主证据 / 补证据集合", "风险说明摘要"],
      observability: ["support_doc_count", "pack_token", "citation_closed", "pack_risk_score"],
    },
    concept_candidate_review: {
      objective: "筛出概念候选、术语候选和对象候选，决定哪些值得进入规范知识层。",
      aiMode: "概念候选判断",
      defaultAction: "转人工复核",
      inputs: ["标准证据包", "概念抽取提示词", "术语白名单 / 黑名单"],
      aiAdaptation: "AI 结合证据包和术语策略自动生成概念候选，并判断是否达到进入规范知识的最低可信门槛。",
      rules: [
        { key: "concept-1", name: "候选可信度", meaning: "可信度不足不进入规范知识", threshold: "confidence >= 0.78", action: "转人工复核" },
        { key: "concept-2", name: "术语黑名单", meaning: "黑名单术语直接剔除", threshold: "term not in blacklist", action: "阻断并回退" },
        { key: "concept-3", name: "别名折叠", meaning: "别名候选优先折叠到主概念", threshold: "alias_overlap >= 0.65", action: "自动放行" },
      ],
      branches: ["可信度高 -> 规范知识汇流", "别名重合 -> 折叠后继续", "可信度低 -> 人工复核候选池"],
      outputs: ["概念候选集", "别名映射", "可信度评分"],
      observability: ["confidence", "alias_overlap", "blacklist_hit", "candidate_count"],
    },
    relation_review_family_normalization: {
      objective: "识别关系、家族归属和继承路径，把关系表达归一到统一 schema。",
      aiMode: "关系归一与家族推断",
      defaultAction: "告警继续",
      inputs: ["标准证据包", "关系 schema", "关系家族词表"],
      aiAdaptation: "AI 自动判断关系方向、关系家族和归一化名称，尽量避免一条关系在不同文档中多套表达。",
      rules: [
        { key: "relation-1", name: "关系方向一致性", meaning: "方向不一致时先按 schema 重写", threshold: "direction_match = true", action: "自动放行" },
        { key: "relation-2", name: "关系证据充分性", meaning: "缺少支撑证据的关系不进入发布链", threshold: "evidence_span >= 2", action: "阻断并回退" },
        { key: "relation-3", name: "家族归一置信度", meaning: "归一置信度不足时保留告警", threshold: "family_confidence >= 0.7", action: "告警继续" },
      ],
      branches: ["关系稳定 -> 规范知识汇流", "方向冲突 -> schema 重写继续", "证据不足 -> 阻断并回退"],
      outputs: ["归一关系候选", "关系家族标签", "方向修正日志"],
      observability: ["direction_match", "evidence_span", "family_confidence", "relation_count"],
    },
    definition_summary_conflict_consolidation: {
      objective: "为定义、摘要和冲突项生成统一结论，并提前清理可见冲突。",
      aiMode: "定义整合与冲突诊断",
      defaultAction: "转人工复核",
      inputs: ["标准证据包", "定义模板", "冲突检测策略"],
      aiAdaptation: "AI 自动汇总定义候选、摘要和冲突说明，对冲突项给出合并、保留或阻断建议。",
      rules: [
        { key: "definition-1", name: "定义字段完整性", meaning: "缺失核心定义字段时不进入规范知识", threshold: "definition_core_present = true", action: "阻断并回退" },
        { key: "definition-2", name: "冲突密度控制", meaning: "冲突密度过高时直接转人工复核", threshold: "conflict_density <= 0.25", action: "转人工复核" },
        { key: "definition-3", name: "摘要可追溯性", meaning: "摘要必须能反查到至少一个主证据", threshold: "summary_traceable = true", action: "告警继续" },
      ],
      branches: ["冲突可收敛 -> 规范知识汇流", "冲突过高 -> 人工复核", "定义缺失 -> 回退证据包"],
      outputs: ["定义候选", "摘要候选", "冲突说明与合并建议"],
      observability: ["definition_core_present", "conflict_density", "summary_traceable", "conflict_count"],
    },
    canonical_knowledge: {
      objective: "汇总三条审查支路，形成可治理、可发布、可追溯的规范知识对象。",
      aiMode: "规范对象整编",
      defaultAction: "自动放行",
      inputs: ["概念候选集", "归一关系候选", "定义/摘要/冲突结论"],
      aiAdaptation: "AI 自动拼装规范知识对象，补齐标准字段、引用索引和历史版本差异摘要。",
      rules: [
        { key: "canonical-1", name: "规范名称存在", meaning: "没有规范名称不允许进入质量门禁", threshold: "canonical_name present", action: "阻断并回退" },
        { key: "canonical-2", name: "引用索引完整", meaning: "引用索引缺失时保留告警继续", threshold: "citation_index >= 0.9", action: "告警继续" },
        { key: "canonical-3", name: "对象合并阈值", meaning: "高重合对象优先合并而不是重复入库", threshold: "merge_similarity >= 0.82", action: "自动放行" },
      ],
      branches: ["对象稳定 -> 质量门禁", "索引缺失 -> 告警继续", "名称缺失 -> 回退三支路复查"],
      outputs: ["规范知识对象", "引用索引", "版本差异摘要"],
      observability: ["canonical_name", "citation_index", "merge_similarity", "canonical_object_score"],
    },
    quality_policy_evaluation_governance_gate: {
      objective: "集中执行质量门禁，决定当前对象是直接进入发布、告警继续还是阻断。",
      aiMode: "质量门禁决策辅助",
      defaultAction: "阻断并回退",
      inputs: ["规范知识对象", "质量策略集", "阶段级风险信号"],
      aiAdaptation: "AI 根据前序阶段风险信号给出门禁建议，但最终仍由策略阈值决定阻断、告警或延迟发布。",
      rules: [
        { key: "gate-1", name: "支撑文档下限", meaning: "支撑证据不足时直接阻断", threshold: "supporting_documents >= 2", action: "阻断并回退" },
        { key: "gate-2", name: "风险信号汇总", meaning: "风险分过高则转人工复核或延迟发布", threshold: "risk_score < 0.65", action: "转人工复核" },
        { key: "gate-3", name: "发布前冲突清零", meaning: "存在未解决硬冲突则禁止进入发布链", threshold: "hard_conflict = 0", action: "阻断并回退" },
      ],
      branches: ["门禁通过 -> 发布/API", "风险中等 -> 人工复核", "硬冲突或支撑不足 -> 阻断并回退规范知识"],
      outputs: ["Gate 决策", "阻断/告警原因", "人工复核转交建议"],
      observability: ["supporting_documents", "risk_score", "hard_conflict", "gate_decision"],
    },
    indexes_snapshots_apis: {
      objective: "控制索引、快照和 API 发布的时机、范围与降级策略。",
      aiMode: "发布策略建议",
      defaultAction: "延迟发布",
      inputs: ["Gate 决策", "发布通道配置", "索引/快照策略"],
      aiAdaptation: "AI 根据对象类型、变更幅度和风险等级建议发布到哪些索引、快照和 API 通道。",
      rules: [
        { key: "publish-1", name: "仅门禁通过对象可发布", meaning: "未通过门禁的对象不能落入发布通道", threshold: "gate_decision = pass", action: "阻断并回退" },
        { key: "publish-2", name: "高风险对象延迟发布", meaning: "高风险对象先保留快照，不直接开放 API", threshold: "risk_score < 0.45", action: "延迟发布" },
        { key: "publish-3", name: "索引一致性检查", meaning: "索引版本不一致时只保存快照", threshold: "index_schema_match = true", action: "告警继续" },
      ],
      branches: ["门禁通过 -> 正式发布", "风险偏高 -> 延迟发布并保留快照", "索引不一致 -> 只保留快照"],
      outputs: ["索引发布决策", "快照策略", "API 暴露范围"],
      observability: ["gate_decision", "risk_score", "index_schema_match", "publish_scope"],
    },
  };

  const stageLaneDescriptions: Record<FlowLaneId, string> = {
    intake: "前四个阶段负责让原始文档进入可解析、可追溯、可统一的标准输入形态。",
    evidence: "中六个阶段负责把证据转成图谱、证据包与三条知识候选支路，为规范知识准备材料。",
    publication: "后三个阶段负责规范对象汇总、质量门禁判断，以及索引 / 快照 / API 发布策略。",
  };

  const [selectedStageId, setSelectedStageId] = useState<string>("asset_intake");
  const selectedStageKey = policyStageConfigs[selectedStageId] ? selectedStageId : flowLaneStageIds.intake[0];
  const selectedStageConfig = policyStageConfigs[selectedStageKey];
  const selectedLaneId = getFlowLaneId(selectedStageKey);
  const selectedStageLabel = getStageDisplayLabel(selectedStageKey);
  const totalRuleCount = Object.values(policyStageConfigs).reduce((count, stage) => count + stage.rules.length, 0);
  const aiEnabledCount = Object.values(policyStageConfigs).filter((stage) => !stage.aiMode.includes("纯规则")).length;
  const selectedActionColor = policyActionColorMap[selectedStageConfig.defaultAction];
  const ruleColumns: ColumnsType<PolicyStageRule> = [
    { title: "规则", dataIndex: "name", key: "name", width: 180 },
    { title: "含义", dataIndex: "meaning", key: "meaning" },
    { title: "阈值/条件", dataIndex: "threshold", key: "threshold", width: 220 },
    {
      title: "默认动作",
      dataIndex: "action",
      key: "action",
      width: 128,
      render: (value: PolicyActionLabel) => <Tag color={policyActionColorMap[value]}>{value}</Tag>,
    },
  ];

  return (
    <ValidationWorkspace
      title="策略与配置工作台"
      description="按 13 个阶段编排单文档知识抽取策略、AI 自动适配、阈值、分支回退和输出契约；这里不承载人工入库审核。"
      actions={
        <Space wrap>
          <Button onClick={onBackOverview}>返回总览</Button>
          <Button onClick={onOpenGlobal}>进入运行中心</Button>
          <Button>比较策略版本</Button>
          <Button type="primary">保存草稿</Button>
        </Space>
      }
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Alert
          type="info"
          showIcon
          message="这是一张抽取前 / 抽取中的策略编排台"
          description="这里定义单文档在 13 个阶段中如何由策略与 AI 自动适配驱动筛选、判断、分流与回退。抽取完成后的人工确认、合并、入库审核仍然保留在 /governance。"
        />
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12} xl={6}>
            <SummaryMetricTile label="抽取蓝图" value="13 阶段抽取蓝图 v1" hint="单文档抽取过程" />
          </Col>
          <Col xs={24} md={12} xl={6}>
            <SummaryMetricTile label="AI 自动适配" value={`已接入 ${aiEnabledCount} / 13 阶段`} hint="按阶段决定分流、筛选与回退" />
          </Col>
          <Col xs={24} md={12} xl={6}>
            <SummaryMetricTile label="策略规则" value={`${totalRuleCount} 条`} hint="覆盖阈值、分支、阻断与告警动作" />
          </Col>
          <Col xs={24} md={12} xl={6}>
            <SummaryMetricTile label="当前组织方式" value="按阶段组织" hint="与 /governance 的人工审核职责分离" />
          </Col>
        </Row>
        <Row gutter={[16, 16]} align="stretch">
          <Col xs={24} xl={7}>
            <Card
              title="13 阶段策略导航"
              extra={<Tag color="blue">策略配置</Tag>}
              styles={{ body: { display: "flex", flexDirection: "column", gap: 16, padding: 20 } }}
            >
              {(["intake", "evidence", "publication"] as FlowLaneId[]).map((laneId) => (
                <div
                  key={laneId}
                  style={{
                    borderRadius: 16,
                    border: "1px solid rgba(148,163,184,0.18)",
                    background: laneId === selectedLaneId ? "rgba(248,250,252,0.95)" : "#fff",
                    padding: 14,
                    marginBottom: 14,
                  }}
                >
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    <Space align="start" style={{ justifyContent: "space-between", width: "100%" }}>
                      <Space direction="vertical" size={2}>
                        <Text strong style={{ color: flowLaneMeta[laneId].titleColor }}>
                          {flowLaneMeta[laneId].title}
                        </Text>
                        <Text type="secondary">{stageLaneDescriptions[laneId]}</Text>
                      </Space>
                      <Tag color="default">{flowLaneStageIds[laneId].length} 阶段</Tag>
                    </Space>
                    <Space direction="vertical" size={8} style={{ display: "flex" }}>
                      {flowLaneStageIds[laneId].map((stageId) => {
                        const stageConfig = policyStageConfigs[stageId];
                        const active = stageId === selectedStageKey;
                        return (
                          <Button
                            key={stageId}
                            block
                            type={active ? "primary" : "default"}
                            onClick={() => setSelectedStageId(stageId)}
                            style={{ height: "auto", textAlign: "left", paddingBlock: 10, paddingInline: 12 }}
                          >
                            <Space direction="vertical" size={4} style={{ display: "flex", alignItems: "flex-start" }}>
                              <Text strong style={{ color: active ? "#fff" : undefined }}>
                                {getStageDisplayLabel(stageId)}
                              </Text>
                              <Text style={{ color: active ? "rgba(255,255,255,0.88)" : "rgba(71,85,105,0.86)" }}>
                                {stageConfig.objective}
                              </Text>
                              <Space size={8} wrap>
                                <Tag color={active ? "gold" : policyActionColorMap[stageConfig.defaultAction]}>
                                  {stageConfig.defaultAction}
                                </Tag>
                                <Text style={{ color: active ? "rgba(255,255,255,0.88)" : "rgba(100,116,139,0.92)" }}>
                                  {stageConfig.rules.length} 条筛选规则
                                </Text>
                              </Space>
                            </Space>
                          </Button>
                        );
                      })}
                    </Space>
                  </Space>
                </div>
              ))}
            </Card>
          </Col>
          <Col xs={24} xl={17}>
            <Card
              title={`当前阶段配置 · ${selectedStageLabel}`}
              extra={
                <Space wrap>
                  <Tag color="default">{flowLaneMeta[selectedLaneId].title}</Tag>
                  <Tag color="processing">{selectedStageConfig.aiMode}</Tag>
                  <Tag color={selectedActionColor}>{selectedStageConfig.defaultAction}</Tag>
                </Space>
              }
              styles={{ body: { display: "flex", flexDirection: "column", gap: 16, padding: 20 } }}
            >
              <Card
                type="inner"
                title="阶段目标与编排原则"
                styles={{ body: { display: "flex", flexDirection: "column", gap: 12 } }}
              >
                <Paragraph style={{ marginBottom: 0 }}>{selectedStageConfig.objective}</Paragraph>
                <Descriptions size="small" column={2} colon={false}>
                  <Descriptions.Item label="组织方式">按 13 阶段配置，不混入人工审核动作</Descriptions.Item>
                  <Descriptions.Item label="当前阶段默认动作">{selectedStageConfig.defaultAction}</Descriptions.Item>
                  <Descriptions.Item label="AI 角色">{selectedStageConfig.aiMode}</Descriptions.Item>
                  <Descriptions.Item label="生效范围">单文档抽取过程</Descriptions.Item>
                </Descriptions>
                <Text type="secondary">{selectedStageConfig.aiAdaptation}</Text>
              </Card>
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  <Card type="inner" title="输入与触发">
                    <List
                      size="small"
                      dataSource={selectedStageConfig.inputs}
                      renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card type="inner" title="分支与回退">
                    <List
                      size="small"
                      dataSource={selectedStageConfig.branches}
                      renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                  </Card>
                </Col>
              </Row>
              <Card type="inner" title="自动筛选规则">
                <Table rowKey="key" pagination={false} size="small" columns={ruleColumns} dataSource={selectedStageConfig.rules} />
              </Card>
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  <Card type="inner" title="输出契约">
                    <Space wrap size={[8, 8]}>
                      {selectedStageConfig.outputs.map((item) => (
                        <Tag key={item} color="blue">
                          {item}
                        </Tag>
                      ))}
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card type="inner" title="运行观测字段">
                    <Space wrap size={[8, 8]}>
                      {selectedStageConfig.observability.map((item) => (
                        <Tag key={item}>{item}</Tag>
                      ))}
                    </Space>
                  </Card>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      </Space>
    </ValidationWorkspace>
  );
}

function PolicyWorkbenchRuntimeView({
  archive,
  onBackOverview,
  onOpenGlobal,
}: {
  archive: KnowledgeArchive | null;
  onBackOverview: () => void;
  onOpenGlobal: () => void;
}) {
  type PolicyStageRuleFormValue = {
    key: string;
    name: string;
    meaning: string;
    threshold: string;
    action: ArchivePolicyAction;
  };

  type PolicyStageFormValues = {
    version_label: string;
    scope_label: string;
    ai_autoadapt_enabled: boolean;
    enabled: boolean;
    ai_mode: string;
    default_action: ArchivePolicyAction;
    objective: string;
    inputs_text: string;
    ai_adaptation: string;
    branches_text: string;
    outputs_text: string;
    observability_text: string;
    rules: PolicyStageRuleFormValue[];
  };

  const actionLabelMap: Record<ArchivePolicyAction, { label: string; color: string }> = {
    auto_pass: { label: "自动放行", color: "success" },
    warn_continue: { label: "告警继续", color: "warning" },
    manual_review: { label: "转人工复核", color: "processing" },
    block_return: { label: "阻断并回退", color: "error" },
    defer_publish: { label: "延迟发布", color: "default" },
  };
  const policyActionOptions: Array<{ value: ArchivePolicyAction; label: string; color: string }> = [
    { value: "auto_pass", ...actionLabelMap.auto_pass },
    { value: "warn_continue", ...actionLabelMap.warn_continue },
    { value: "manual_review", ...actionLabelMap.manual_review },
    { value: "block_return", ...actionLabelMap.block_return },
    { value: "defer_publish", ...actionLabelMap.defer_publish },
  ];

  const [messageApi, messageContextHolder] = message.useMessage();
  const [form] = Form.useForm<PolicyStageFormValues>();
  const [policyConfig, setPolicyConfig] = useState<ArchivePolicyConfig | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policySaving, setPolicySaving] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const archiveId = archive?.archive_id ?? null;

  const parseLines = (value: string | undefined) =>
    (value ?? "")
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);

  const joinLines = (items: string[]) => items.join("\n");

  const buildFormValues = (config: ArchivePolicyConfig, stageId: string): PolicyStageFormValues => {
    const stage = config.stages[stageId];
    return {
      version_label: config.version_label,
      scope_label: config.scope_label,
      ai_autoadapt_enabled: config.ai_autoadapt_enabled,
      enabled: stage.enabled,
      ai_mode: stage.ai_mode,
      default_action: stage.default_action,
      objective: stage.objective,
      inputs_text: joinLines(stage.inputs),
      ai_adaptation: stage.ai_adaptation,
      branches_text: joinLines(stage.branches),
      outputs_text: joinLines(stage.outputs),
      observability_text: joinLines(stage.observability),
      rules: stage.rules.map((rule) => ({ ...rule })),
    };
  };

  const mergeFormValuesIntoConfig = (
    config: ArchivePolicyConfig,
    stageId: string,
    values: Partial<PolicyStageFormValues>,
  ): ArchivePolicyConfig => {
    const currentStage = config.stages[stageId];
    if (!currentStage) {
      return config;
    }

    const nextStage: ArchiveStagePolicyConfig = {
      ...currentStage,
      enabled: values.enabled ?? currentStage.enabled,
      ai_mode: values.ai_mode ?? currentStage.ai_mode,
      default_action: values.default_action ?? currentStage.default_action,
      objective: values.objective ?? currentStage.objective,
      inputs: values.inputs_text === undefined ? currentStage.inputs : parseLines(values.inputs_text),
      ai_adaptation: values.ai_adaptation ?? currentStage.ai_adaptation,
      branches: values.branches_text === undefined ? currentStage.branches : parseLines(values.branches_text),
      outputs: values.outputs_text === undefined ? currentStage.outputs : parseLines(values.outputs_text),
      observability:
        values.observability_text === undefined ? currentStage.observability : parseLines(values.observability_text),
      rules:
        values.rules?.map((rule, index) => ({
          key: rule.key?.trim() || `${stageId}-rule-${index + 1}`,
          name: rule.name?.trim() || `规则 ${index + 1}`,
          meaning: rule.meaning?.trim() || "",
          threshold: rule.threshold?.trim() || "",
          action: rule.action,
        })) ?? currentStage.rules,
    };

    return {
      ...config,
      version_label: values.version_label ?? config.version_label,
      scope_label: values.scope_label ?? config.scope_label,
      ai_autoadapt_enabled: values.ai_autoadapt_enabled ?? config.ai_autoadapt_enabled,
      stages: {
        ...config.stages,
        [stageId]: nextStage,
      },
    };
  };

  const pushCurrentFormIntoDraft = (baseConfig: ArchivePolicyConfig | null) => {
    if (!baseConfig || !selectedStageId) {
      return baseConfig;
    }

    return mergeFormValuesIntoConfig(baseConfig, selectedStageId, form.getFieldsValue(true));
  };

  const hydrateForm = (config: ArchivePolicyConfig, stageId: string) => {
    form.setFieldsValue(buildFormValues(config, stageId));
  };

  const loadPolicyConfig = async (preservedStageId?: string | null) => {
    if (!archiveId) {
      setPolicyConfig(null);
      setSelectedStageId(null);
      form.resetFields();
      return;
    }

    setPolicyLoading(true);
    setPolicyError(null);

    try {
      const response = await getArchivePolicyConfig(archiveId);
      const nextConfig = response.data;
      const nextStageId =
        (preservedStageId && nextConfig.stages[preservedStageId] ? preservedStageId : nextConfig.stage_order[0]) ?? null;

      setPolicyConfig(nextConfig);
      setSelectedStageId(nextStageId);
      if (nextStageId) {
        hydrateForm(nextConfig, nextStageId);
      } else {
        form.resetFields();
      }
      setDirty(false);
    } catch (loadError) {
      setPolicyConfig(null);
      setSelectedStageId(null);
      setPolicyError(loadError instanceof Error ? loadError.message : "策略配置加载失败");
      form.resetFields();
    } finally {
      setPolicyLoading(false);
    }
  };

  useEffect(() => {
    void loadPolicyConfig();
  }, [archiveId]);

  const handleStageSelect = (stageId: string) => {
    if (!policyConfig) {
      return;
    }

    const nextConfig = pushCurrentFormIntoDraft(policyConfig);
    if (!nextConfig) {
      return;
    }

    setPolicyConfig(nextConfig);
    setSelectedStageId(stageId);
    hydrateForm(nextConfig, stageId);
  };

  const handleSave = async () => {
    if (!archiveId || !policyConfig || !selectedStageId) {
      return;
    }

    try {
      await form.validateFields();
      const draft = pushCurrentFormIntoDraft(policyConfig);
      if (!draft) {
        return;
      }

      setPolicySaving(true);
      const response = await updateArchivePolicyConfig(archiveId, {
        version_label: draft.version_label,
        scope_label: draft.scope_label,
        ai_autoadapt_enabled: draft.ai_autoadapt_enabled,
        stage_order: draft.stage_order,
        stages: draft.stages,
      });

      const saved = response.data;
      const nextStageId =
        (selectedStageId && saved.stages[selectedStageId] ? selectedStageId : saved.stage_order[0]) ?? null;
      setPolicyConfig(saved);
      setSelectedStageId(nextStageId);
      if (nextStageId) {
        hydrateForm(saved, nextStageId);
      }
      setDirty(false);
      messageApi.success("策略配置已保存");
    } catch (saveError) {
      messageApi.error(saveError instanceof Error ? saveError.message : "策略配置保存失败");
    } finally {
      setPolicySaving(false);
    }
  };

  const selectedStageConfig = selectedStageId ? policyConfig?.stages[selectedStageId] ?? null : null;
  const stageGroups = (Object.keys(flowLaneStageIds) as FlowLaneId[]).map((laneId) => ({
    laneId,
    title: flowLaneMeta[laneId].title,
    stageIds: (policyConfig?.stage_order ?? flowLaneStageIds[laneId]).filter((stageId) => flowLaneStageIds[laneId].includes(stageId)),
  }));

  return (
    <ValidationWorkspace
      title="策略与配置工作台"
      description="按 13 个抽取阶段组织策略配置，用于控制单文档抽取过程中的规则、阈值、AI 自动适配与分支回退。"
      actions={
        <Space wrap>
          <Button onClick={onBackOverview}>返回总览</Button>
          <Button onClick={onOpenGlobal}>进入运行中心</Button>
          <Button onClick={() => void loadPolicyConfig(selectedStageId)} disabled={!archiveId} loading={policyLoading}>
            刷新后端合同
          </Button>
          <Button type="primary" onClick={() => void handleSave()} loading={policySaving} disabled={!policyConfig}>
            保存草稿
          </Button>
        </Space>
      }
    >
      {messageContextHolder}
      {!archive ? (
        <Empty description="当前没有可配置的知识库" />
      ) : (
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          {policyError ? <Alert type="error" showIcon message="策略配置加载失败" description={policyError} /> : null}
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12} xl={6}>
              <SummaryMetricTile label="当前知识库" value={archive.name} hint={archive.archive_id} />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <SummaryMetricTile
                label="策略版本"
                value={policyConfig?.version_label ?? "加载中"}
                hint={dirty ? "存在未保存修改" : "已与后端合同对齐"}
              />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <SummaryMetricTile
                label="AI 自动适配"
                value={policyConfig?.ai_autoadapt_enabled ? "已开启" : "已关闭"}
                hint={policyConfig?.scope_label ?? "单文档抽取过程"}
              />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <SummaryMetricTile
                label="最近更新"
                value={policyConfig?.updated_at ? formatDateTime(policyConfig.updated_at) : "未保存"}
                hint="后端返回的最新策略时间戳"
              />
            </Col>
          </Row>

          <Card
            title="13 阶段策略导航"
            extra={dirty ? <Tag color="warning">未保存</Tag> : <Tag color="success">已同步</Tag>}
            loading={policyLoading}
          >
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              这是一张抽取前 / 抽取中的策略编排台。左侧按阶段切换，右侧只编辑当前阶段的真实配置表单。
            </Paragraph>
            <Row gutter={[16, 16]}>
              <Col xs={24} xl={7}>
                <Space direction="vertical" size={12} style={{ display: "flex" }}>
                  {stageGroups.map((group) => (
                    <Card key={group.laneId} size="small" title={group.title}>
                      <Space direction="vertical" size={8} style={{ display: "flex" }}>
                        {group.stageIds.map((stageId) => {
                          const stage = policyConfig?.stages[stageId];
                          if (!stage) {
                            return null;
                          }

                          const actionMeta = actionLabelMap[stage.default_action];
                          return (
                            <Button
                              key={stageId}
                              block
                              type={selectedStageId === stageId ? "primary" : "default"}
                              onClick={() => handleStageSelect(stageId)}
                              style={{ height: "auto", paddingBlock: 10 }}
                            >
                              <Space direction="vertical" size={4} style={{ display: "flex", alignItems: "flex-start" }}>
                                <Text strong>{stage.label}</Text>
                                <Space wrap size={[6, 6]}>
                                  <Tag color={stage.enabled ? "success" : "default"}>{stage.enabled ? "启用" : "停用"}</Tag>
                                  <Tag color={actionMeta.color}>{actionMeta.label}</Tag>
                                </Space>
                              </Space>
                            </Button>
                          );
                        })}
                      </Space>
                    </Card>
                  ))}
                </Space>
              </Col>

              <Col xs={24} xl={17}>
                {!selectedStageConfig || !policyConfig ? (
                  <Card>
                    <Empty description="当前没有可编辑的阶段配置" />
                  </Card>
                ) : (
                  <Form
                    form={form}
                    layout="vertical"
                    onValuesChange={() => {
                      setDirty(true);
                    }}
                  >
                    <Space direction="vertical" size={16} style={{ display: "flex" }}>
                      <Card title="蓝图元信息">
                        <Row gutter={16}>
                          <Col xs={24} lg={12}>
                            <Form.Item name="version_label" label="策略版本" rules={[{ required: true, message: "请输入策略版本" }]}>
                              <Input placeholder="例如：13 阶段抽取蓝图 v1" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} lg={12}>
                            <Form.Item name="scope_label" label="生效范围" rules={[{ required: true, message: "请输入生效范围" }]}>
                              <Input placeholder="例如：单文档抽取过程" />
                            </Form.Item>
                          </Col>
                        </Row>
                        <Form.Item name="ai_autoadapt_enabled" label="AI 自动适配" valuePropName="checked">
                          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                        </Form.Item>
                      </Card>

                      <Card
                        title={`当前阶段配置 · ${selectedStageConfig.label}`}
                        extra={
                          <Space wrap>
                            <Tag color={selectedStageConfig.enabled ? "success" : "default"}>
                              {selectedStageConfig.enabled ? "阶段已启用" : "阶段已停用"}
                            </Tag>
                            <Tag color={actionLabelMap[selectedStageConfig.default_action].color}>
                              默认动作：{actionLabelMap[selectedStageConfig.default_action].label}
                            </Tag>
                          </Space>
                        }
                      >
                        <Row gutter={16}>
                          <Col xs={24} md={8}>
                            <Form.Item name="enabled" label="启用当前阶段" valuePropName="checked">
                              <Switch checkedChildren="启用" unCheckedChildren="停用" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="ai_mode" label="AI 模式" rules={[{ required: true, message: "请输入 AI 模式" }]}>
                              <Input />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="default_action" label="默认动作" rules={[{ required: true, message: "请选择默认动作" }]}>
                              <Select
                                options={policyActionOptions.map((item) => ({
                                  value: item.value,
                                  label: item.label,
                                }))}
                              />
                            </Form.Item>
                          </Col>
                        </Row>

                        <Form.Item name="objective" label="阶段目标" rules={[{ required: true, message: "请输入阶段目标" }]}>
                          <Input.TextArea autoSize={{ minRows: 3, maxRows: 5 }} />
                        </Form.Item>

                        <Form.Item name="ai_adaptation" label="AI 自动适配策略" rules={[{ required: true, message: "请输入 AI 自动适配策略" }]}>
                          <Input.TextArea autoSize={{ minRows: 3, maxRows: 5 }} />
                        </Form.Item>

                        <Row gutter={[16, 16]}>
                          <Col xs={24} lg={12}>
                            <Form.Item name="inputs_text" label="输入触发条件">
                              <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} placeholder="每行一个输入来源或触发条件" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} lg={12}>
                            <Form.Item name="branches_text" label="分支与回退">
                              <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} placeholder="每行一个分支动作或回退条件" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} lg={12}>
                            <Form.Item name="outputs_text" label="输出契约">
                              <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} placeholder="每行一个阶段输出" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} lg={12}>
                            <Form.Item name="observability_text" label="观测字段">
                              <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} placeholder="每行一个运行观测字段" />
                            </Form.Item>
                          </Col>
                        </Row>
                      </Card>

                      <Card title="自动筛选规则">
                        <Form.List name="rules">
                          {(fields, { add, remove }) => (
                            <Space direction="vertical" size={12} style={{ display: "flex" }}>
                              {fields.map((field, index) => (
                                <Card
                                  key={field.key}
                                  size="small"
                                  title={`规则 ${index + 1}`}
                                  extra={
                                    <Button danger type="text" onClick={() => remove(field.name)}>
                                      删除
                                    </Button>
                                  }
                                >
                                  <Row gutter={16}>
                                    <Col xs={24} md={8}>
                                      <Form.Item
                                        name={[field.name, "key"]}
                                        label="规则键"
                                        rules={[{ required: true, message: "请输入规则键" }]}
                                      >
                                        <Input />
                                      </Form.Item>
                                    </Col>
                                    <Col xs={24} md={8}>
                                      <Form.Item
                                        name={[field.name, "name"]}
                                        label="规则名称"
                                        rules={[{ required: true, message: "请输入规则名称" }]}
                                      >
                                        <Input />
                                      </Form.Item>
                                    </Col>
                                    <Col xs={24} md={8}>
                                      <Form.Item
                                        name={[field.name, "action"]}
                                        label="命中动作"
                                        rules={[{ required: true, message: "请选择命中动作" }]}
                                      >
                                        <Select
                                          options={policyActionOptions.map((item) => ({
                                            value: item.value,
                                            label: item.label,
                                          }))}
                                        />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                  <Form.Item
                                    name={[field.name, "meaning"]}
                                    label="规则含义"
                                    rules={[{ required: true, message: "请输入规则含义" }]}
                                  >
                                    <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} />
                                  </Form.Item>
                                  <Form.Item
                                    name={[field.name, "threshold"]}
                                    label="阈值表达式"
                                    rules={[{ required: true, message: "请输入阈值表达式" }]}
                                  >
                                    <Input.TextArea autoSize={{ minRows: 2, maxRows: 3 }} />
                                  </Form.Item>
                                </Card>
                              ))}
                              <Button
                                onClick={() =>
                                  add({
                                    key: `${selectedStageId}-rule-${fields.length + 1}`,
                                    name: "新规则",
                                    meaning: "",
                                    threshold: "",
                                    action: selectedStageConfig.default_action,
                                  })
                                }
                              >
                                新增规则
                              </Button>
                            </Space>
                          )}
                        </Form.List>
                      </Card>
                    </Space>
                  </Form>
                )}
              </Col>
            </Row>
          </Card>
        </Space>
      )}
    </ValidationWorkspace>
  );
}

function PolicyView({ onBackOverview, onOpenGlobal }: { onBackOverview: () => void; onOpenGlobal: () => void }) {
  const data = [
    { key: "1", group: "知识项级", name: "canonical_name_present", meaning: "规范名称必须存在", threshold: "true", action: "阻断" },
    { key: "2", group: "知识项级", name: "definition_present", meaning: "定义字段不能为空", threshold: "true", action: "人工复核" },
    { key: "3", group: "关系级", name: "relation_evidence_required", meaning: "关系必须带证据", threshold: "true", action: "阻断" },
    { key: "4", group: "发布批次级", name: "approved_only", meaning: "发布态只允许已批准项", threshold: "true", action: "阻断" },
  ];
  return (
    <ValidationWorkspace
      title="规则与质量工作台"
      description="这里只讲抽取蓝图、质量策略、阈值和动作，不混入本次运行命中结果。"
      actions={
        <Space wrap>
          <Button onClick={onBackOverview}>返回总览</Button>
          <Button onClick={onOpenGlobal}>进入运行中心</Button>
          <Button>比较策略版本</Button>
        </Space>
      }
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Row gutter={16}>
          <Col span={6}><Card><Statistic title="抽取蓝图" value="知识抽取蓝图 v1" /></Card></Col>
          <Col span={6}><Card><Statistic title="质量策略" value="内容质量策略 v1" /></Card></Col>
          <Col span={6}><Card><Statistic title="规则覆盖层级" value="知识项 / 关系 / 发布" /></Card></Col>
          <Col span={6}><Card><Statistic title="模式" value="严格 · 默认动作：人工复核" /></Card></Col>
        </Row>
        <Row gutter={16}>
          <Col xs={24} xl={6}>
            <Card title="抽取蓝图">
              <List
                size="small"
                dataSource={["资产接入", "解析执行", "证据图谱 / 证据包", "候选知识 / 规范知识", "质量门禁 / 发布"]}
                renderItem={(item) => <List.Item>{item}</List.Item>}
              />
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card title="规则清单">
              <Table
                pagination={false}
                dataSource={data}
                columns={[
                  { title: "规则分组", dataIndex: "group", key: "group" },
                  { title: "规则键", dataIndex: "name", key: "name" },
                  { title: "含义", dataIndex: "meaning", key: "meaning" },
                  { title: "阈值", dataIndex: "threshold", key: "threshold" },
                  {
                    title: "动作",
                    dataIndex: "action",
                    key: "action",
                    render: (value: string) => <Tag color={value === "阻断" ? "error" : value === "人工复核" ? "warning" : "default"}>{value}</Tag>,
                  },
                ]}
              />
            </Card>
          </Col>
          <Col xs={24} xl={6}>
            <Card title="质量策略">
              <Descriptions size="small" column={1} colon={false}>
                <Descriptions.Item label="硬底线">阻断 4 项</Descriptions.Item>
                <Descriptions.Item label="人工复核">复核 3 项</Descriptions.Item>
                <Descriptions.Item label="仅告警">告警 2 项</Descriptions.Item>
                <Descriptions.Item label="最近变更">2026-04-21 · 补齐证据规则</Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        </Row>
      </Space>
    </ValidationWorkspace>
  );
}

export function ArchiveManagementPage() {
  const { archives, activeArchiveId, activeArchive, loading, error, refreshArchives, setActiveArchiveId } = useArchiveContext();
  const [messageApi, messageContextHolder] = message.useMessage();
  const [view, setView] = useState<WorkspaceView>("overview");
  const [selectedArchiveId, setSelectedArchiveId] = useState<string | null>(activeArchiveId);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<ArchiveDocumentRuntimeContract | null>(null);
  const [documentPolicyConfig, setDocumentPolicyConfig] = useState<ArchivePolicyConfig | null>(null);
  const [runtimeTransportState, setRuntimeTransportState] = useState<RuntimeTransportState>("snapshot");
  const [inspectedStageId, setInspectedStageId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [observerMode, setObserverMode] = useState<ObserverMode>("stage");
  const [createOpen, setCreateOpen] = useState(false);
  const [extractingArchiveId, setExtractingArchiveId] = useState<string | null>(null);
  const [createForm] = Form.useForm<CreateKnowledgeArchiveInput>();

  useEffect(() => {
    if (!selectedArchiveId) setSelectedArchiveId(activeArchiveId);
  }, [activeArchiveId, selectedArchiveId]);

  const pendingItems = useMemo(() => buildPendingItems(archives), [archives]);
  const selectedArchive = archives.find((archive) => archive.archive_id === selectedArchiveId) ?? activeArchive ?? archives[0] ?? null;
  const selectedDocument = selectedArchive?.build_state?.documents.find((item) => item.document_id === selectedDocumentId) ?? null;

  useEffect(() => {
    if (view !== "document" || !selectedArchiveId) {
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const response = await getArchivePolicyConfig(selectedArchiveId);
        if (!cancelled) {
          setDocumentPolicyConfig(response.data);
        }
      } catch {
        if (!cancelled) {
          setDocumentPolicyConfig(null);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedArchiveId, view]);

  useEffect(() => {
    if (view !== "document" || !selectedArchiveId || !selectedDocumentId) return;
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    let streamBootstrapTimer: ReturnType<typeof setTimeout> | null = null;
    let runtimeStream: { close: () => void } | null = null;
    let hasLoadedOnce = false;
    let latestRuntime: ArchiveDocumentRuntimeContract | null = null;

    const clearPollTimer = () => {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    };

    const clearStreamBootstrapTimer = () => {
      if (streamBootstrapTimer) {
        clearTimeout(streamBootstrapTimer);
        streamBootstrapTimer = null;
      }
    };

    const closeRuntimeStream = () => {
      if (runtimeStream) {
        runtimeStream.close();
        runtimeStream = null;
      }
    };

    const applyRuntime = (nextRuntime: ArchiveDocumentRuntimeContract) => {
      latestRuntime = nextRuntime;
      setRuntime(nextRuntime);
      setRuntimeError(null);
      setInspectedStageId((currentStageId) =>
        currentStageId
          ? (() => {
              const liveCurrentStage = getLiveCurrentStage(nextRuntime);
              const inspectedStage = nextRuntime.stages.find((stage) => stage.stage_id === currentStageId) ?? null;
              return inspectedStage && isStageInspectable(inspectedStage, liveCurrentStage) ? currentStageId : null;
            })()
          : null,
      );

      if (!hasLoadedOnce) {
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
        setObserverMode("stage");
        hasLoadedOnce = true;
      }

      setRuntimeLoading(false);
    };

    const schedulePoll = (delayMs = 4000) => {
      if (cancelled) return;
      setRuntimeTransportState("polling_fallback");
      clearPollTimer();
      pollTimer = setTimeout(() => {
        void loadRuntime({ allowStreamUpgrade: true });
      }, delayMs);
    };

    const handleStreamFallback = () => {
      closeRuntimeStream();
      clearStreamBootstrapTimer();
      if (cancelled) {
        return;
      }
      setRuntimeTransportState("polling_fallback");

      if (!hasLoadedOnce) {
        void loadRuntime({ allowStreamUpgrade: false });
        return;
      }

      if (runtimeNeedsLiveUpdates(selectedDocument?.state, latestRuntime)) {
        schedulePoll(0);
      }
    };

    const startRuntimeStream = () => {
      if (cancelled || runtimeStream) {
        return;
      }

      clearPollTimer();
      setRuntimeTransportState("stream_connecting");

      if (!hasLoadedOnce) {
        setRuntimeLoading(true);
        setRuntimeError(null);
      }

      try {
        runtimeStream = subscribeArchiveDocumentRuntime(
          selectedDocumentId,
          selectedArchiveId,
          {
            onRuntime: (nextRuntime) => {
              if (cancelled) return;

              clearStreamBootstrapTimer();
              setRuntimeTransportState("stream_connected");
              applyRuntime(nextRuntime);

              if (!runtimeNeedsLiveUpdates(selectedDocument?.state, nextRuntime)) {
                setRuntimeTransportState("snapshot");
                closeRuntimeStream();
                clearPollTimer();
              }
            },
            onError: () => {
              if (cancelled) return;
              handleStreamFallback();
            },
          },
          {
            intervalMs: 2000,
            heartbeatMs: 15000,
          },
        );
      } catch {
        handleStreamFallback();
        return;
      }

      clearStreamBootstrapTimer();
      streamBootstrapTimer = setTimeout(() => {
        if (cancelled || hasLoadedOnce) {
          return;
        }
        handleStreamFallback();
      }, 2500);
    };

    const loadRuntime = async ({ allowStreamUpgrade = true }: { allowStreamUpgrade?: boolean } = {}) => {
      const isFirstLoad = !hasLoadedOnce;

      if (isFirstLoad) {
        setRuntimeLoading(true);
        setRuntimeError(null);
      }

      try {
        const response = await getArchiveDocumentRuntime(selectedDocumentId, selectedArchiveId);
        if (cancelled) return;

        applyRuntime(response.data);

        if (allowStreamUpgrade && runtimeNeedsLiveUpdates(selectedDocument?.state, response.data)) {
          startRuntimeStream();
          return;
        }

        closeRuntimeStream();
        clearStreamBootstrapTimer();

        if (runtimeNeedsLiveUpdates(selectedDocument?.state, response.data)) {
          schedulePoll(4000);
        } else {
          setRuntimeTransportState("snapshot");
          clearPollTimer();
        }
      } catch (loadError) {
        if (cancelled) return;
        latestRuntime = null;
        closeRuntimeStream();
        clearStreamBootstrapTimer();
        setRuntime(null);
        setRuntimeError(loadError instanceof Error ? loadError.message : "单文档运行数据加载失败");
      } finally {
        if (!cancelled && isFirstLoad) {
          setRuntimeLoading(false);
        }
      }
    };

    if (selectedDocument?.state === "running") {
      startRuntimeStream();
    } else {
      setRuntimeTransportState("snapshot");
      void loadRuntime();
    }

    return () => {
      cancelled = true;
      clearPollTimer();
      clearStreamBootstrapTimer();
      closeRuntimeStream();
    };
  }, [selectedArchiveId, selectedDocumentId, selectedDocument?.state, view]);

  async function handleCreateArchive() {
    const values = await createForm.validateFields();
    const key = "archive-create";
    try {
      messageApi.open({ key, type: "loading", content: `正在创建「${values.name}」...`, duration: 0 });
      await createKnowledgeArchive(values);
      await setActiveArchiveId(values.archive_id);
      await refreshArchives(values.archive_id);
      setSelectedArchiveId(values.archive_id);
      setSelectedDocumentId(null);
      setView("archive");
      setCreateOpen(false);
      createForm.resetFields();
      messageApi.open({ key, type: "success", content: `已创建并切换到「${values.name}」` });
    } catch (createError) {
      const description =
        createError instanceof Error ? createError.message : "创建知识库失败，请检查标识、名称和源目录";
      messageApi.open({ key, type: "error", content: description });
    }
  }

  async function handleExtractArchive(archiveId: string) {
    const archive = archives.find((item) => item.archive_id === archiveId);
    const archiveName = archive?.name ?? archiveId;
    const key = `archive-extract-${archiveId}`;
    try {
      setExtractingArchiveId(archiveId);
      setSelectedArchiveId(archiveId);
      setSelectedDocumentId(null);
      setView("archive");
      messageApi.open({ key, type: "loading", content: `正在为「${archiveName}」启动抽取...`, duration: 0 });
      await extractKnowledgeArchive(archiveId);
      await refreshArchives(archiveId);
      messageApi.open({ key, type: "success", content: `「${archiveName}」抽取已触发，已切换到单知识库运行` });
    } catch (extractError) {
      const description =
        extractError instanceof Error ? extractError.message : `「${archiveName}」抽取失败，请检查源目录或当前运行状态`;
      messageApi.open({ key, type: "error", content: description });
    } finally {
      setExtractingArchiveId(null);
    }
  }

  async function handleSetCurrentArchive(archiveId: string) {
    const archive = archives.find((item) => item.archive_id === archiveId);
    const archiveName = archive?.name ?? archiveId;
    const key = `archive-activate-${archiveId}`;
    try {
      messageApi.open({ key, type: "loading", content: `正在切换到「${archiveName}」...`, duration: 0 });
      await setActiveArchiveId(archiveId);
      setSelectedArchiveId(archiveId);
      setSelectedDocumentId(null);
      messageApi.open({ key, type: "success", content: `当前知识库已切换为「${archiveName}」` });
    } catch (activateError) {
      const description =
        activateError instanceof Error ? activateError.message : `切换「${archiveName}」失败`;
      messageApi.open({ key, type: "error", content: description });
    }
  }

  const openArchive = (archiveId: string) => {
    setSelectedArchiveId(archiveId);
    setSelectedDocumentId(null);
    setView("archive");
  };

  const openDocument = (documentId: string) => {
    setSelectedDocumentId(documentId);
    setInspectedStageId(null);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setObserverMode("stage");
    setView("document");
  };

  if (loading) return <Card loading />;
  if (error) return <Alert type="error" showIcon message="知识库列表加载失败" description={error} />;

  return (
    <>
      {messageContextHolder}
      {view === "overview" && (
        <OverviewView
          archives={archives}
          activeArchiveId={activeArchiveId}
          pendingItems={pendingItems}
          onOpenArchive={openArchive}
          onOpenGlobal={() => setView("global")}
          onOpenPolicy={() => setView("policy")}
          onExtract={(archiveId) => void handleExtractArchive(archiveId)}
          onSetCurrent={(archiveId) => void handleSetCurrentArchive(archiveId)}
          onShowCreate={() => setCreateOpen(true)}
          extractingArchiveId={extractingArchiveId}
        />
      )}
      {view === "global" && (
        <GlobalView archives={archives} onBack={() => setView("overview")} onOpenArchive={openArchive} onOpenPolicy={() => setView("policy")} />
      )}
      {view === "archive" && selectedArchive && (
        <ArchiveView
          archive={selectedArchive}
          onBackOverview={() => setView("overview")}
          onBackGlobal={() => setView("global")}
          onOpenDocument={openDocument}
          onOpenPolicy={() => setView("policy")}
        />
      )}
      {view === "document" && selectedArchive && selectedDocument && (
        <DocumentView
          document={selectedDocument}
          runtime={runtime}
          policyConfig={documentPolicyConfig}
          runtimeTransportState={runtimeTransportState}
          loading={runtimeLoading}
          error={runtimeError}
          inspectedStageId={inspectedStageId}
          setInspectedStageId={setInspectedStageId}
          selectedNodeId={selectedNodeId}
          setSelectedNodeId={setSelectedNodeId}
          selectedEdgeId={selectedEdgeId}
          setSelectedEdgeId={setSelectedEdgeId}
          observerMode={observerMode}
          setObserverMode={setObserverMode}
          onBackArchive={() => setView("archive")}
          onBackGlobal={() => setView("global")}
          onOpenPolicy={() => setView("policy")}
        />
      )}
      {view === "policy" && (
        <PolicyWorkbenchRuntimeView
          archive={selectedArchive}
          onBackOverview={() => setView("overview")}
          onOpenGlobal={() => setView("global")}
        />
      )}

      <Modal
        open={createOpen}
        title="新建知识库"
        onCancel={() => setCreateOpen(false)}
        onOk={() => void handleCreateArchive()}
        okText="创建知识库"
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item name="archive_id" label="知识库标识" rules={[{ required: true, message: "请输入知识库标识" }]}>
            <Input placeholder="例如：nas-a" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：测试本地NAS数据库" />
          </Form.Item>
          <Form.Item name="source_dir" label="源目录" rules={[{ required: true, message: "请输入源目录" }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
