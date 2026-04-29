import type {
  P6DisplayExperimentCreateRequest,
  P6DisplayWidgetBinding,
  P6DisplayWidgetLayout,
  P6DisplayWidgetTemplate,
} from "../../lib/p6";
import type { P6PortalNodeId, P6PortalViewNode } from "./p6PortalData";

export type P6ExperimentTargetId = "shared-modules" | P6PortalNodeId;
export type P6PromotionDecision = "hold" | "candidate";

export type P6ModuleCardProfile = {
  templateId: string;
  bindingPresetId: string;
};

export type P6UserCardProfile = {
  templateId: string;
};

export type P6ExperimentDraft = {
  selectedTargetId: P6ExperimentTargetId;
  sharedModuleProfile: P6ModuleCardProfile;
  moduleOverrides: Partial<Record<Exclude<P6PortalNodeId, "user">, P6ModuleCardProfile>>;
  userProfile: P6UserCardProfile;
  layoutPresetId: string;
  promotionDecision: P6PromotionDecision;
  targetStages: string[];
  experimentGoal: string;
};

export type P6TargetOption = {
  id: P6ExperimentTargetId;
  label: string;
  detail: string;
};

export type P6OptionItem<T extends string> = {
  id: T;
  label: string;
  description: string;
};

export type P6ResolvedNodeCard = {
  templateId: string;
  bindingPresetId: string | null;
  summary: string;
  metricsCount: number;
  showMetrics: boolean;
  showTimestamp: boolean;
  showDescription: boolean;
  showFreshness: boolean;
  showUserContext: boolean;
  showUserHints: boolean;
  showUserAvailability: boolean;
  showDegraded: boolean;
};

export type P6ExperimentRecord = {
  title: string;
  summary: string;
  issues: string[];
  evidenceRefs: string[];
  recommendation: string;
};

const DEFAULT_MODULE_TEMPLATE_ID = "template-module-status";
const DEFAULT_BINDING_ID = "binding-portal-full";
const DEFAULT_USER_TEMPLATE_ID = "template-user-capsule";
const DEFAULT_LAYOUT_ID = "layout-single";

function isModuleTarget(targetId: P6ExperimentTargetId): targetId is Exclude<P6ExperimentTargetId, "user"> {
  return targetId !== "user";
}

function isCompactTemplate(templateId: string) {
  return templateId.includes("compact");
}

function isOverviewTemplate(templateId: string) {
  return templateId.includes("overview");
}

function isDetailedUserTemplate(templateId: string) {
  return templateId.includes("user-card");
}

function isAlertBinding(bindingId: string) {
  return bindingId.includes("alert");
}

function isSummaryBinding(bindingId: string) {
  return bindingId.includes("summary");
}

function describeTemplate(template: P6DisplayWidgetTemplate) {
  if (template.template_id.includes("compact")) {
    return "压缩内容密度，只保留核心状态和少量指标。";
  }
  if (template.template_id.includes("overview")) {
    return "强调对象说明和当前判断，弱化指标堆叠。";
  }
  if (template.template_id.includes("user-card")) {
    return "改为更完整的参与用户卡片，展示上下文和可用性。";
  }
  if (template.template_id.includes("capsule")) {
    return "保持参与用户轻量展示，突出接入动作。";
  }
  return "保留状态、摘要、指标和时间戳，适合首屏观察。";
}

function describeBinding(binding: P6DisplayWidgetBinding) {
  if (binding.binding_id.includes("alert")) {
    return "优先暴露健康提示和降级说明。";
  }
  if (binding.binding_id.includes("summary")) {
    return "保留摘要和核心指标，降低信息密度。";
  }
  return "显示摘要、指标、状态和时间戳。";
}

function describeLayout(layout: P6DisplayWidgetLayout) {
  if (layout.layout_id.includes("compare")) {
    return "并排对比当前配置与标准基线。";
  }
  return "聚焦当前节点，直接观察实际效果。";
}

export function buildModuleTemplateOptions(templates: P6DisplayWidgetTemplate[]) {
  return templates
    .filter((item) => item.template_kind === "module_card")
    .map((item) => ({
      id: item.template_id,
      label: item.template_name,
      description: describeTemplate(item),
    }));
}

export function buildUserTemplateOptions(templates: P6DisplayWidgetTemplate[]) {
  return templates
    .filter((item) => item.template_kind === "participant_card")
    .map((item) => ({
      id: item.template_id,
      label: item.template_name,
      description: describeTemplate(item),
    }));
}

export function buildBindingPresetOptions(bindings: P6DisplayWidgetBinding[]) {
  return bindings.map((item) => ({
    id: item.binding_id,
    label: item.binding_id.includes("alert")
      ? "告警优先绑定"
      : item.binding_id.includes("summary")
        ? "摘要优先绑定"
        : "完整状态绑定",
    description: describeBinding(item),
  }));
}

export function buildLayoutPresetOptions(layouts: P6DisplayWidgetLayout[]) {
  return layouts.map((item) => ({
    id: item.layout_id,
    label: item.layout_id.includes("compare") ? "双卡对比" : "单卡预览",
    description: describeLayout(item),
  }));
}

export function createDefaultExperimentDraft(): P6ExperimentDraft {
  return {
    selectedTargetId: "shared-modules",
    sharedModuleProfile: {
      templateId: DEFAULT_MODULE_TEMPLATE_ID,
      bindingPresetId: DEFAULT_BINDING_ID,
    },
    moduleOverrides: {},
    userProfile: {
      templateId: DEFAULT_USER_TEMPLATE_ID,
    },
    layoutPresetId: DEFAULT_LAYOUT_ID,
    promotionDecision: "hold",
    targetStages: ["P3", "P4", "P5"],
    experimentGoal: "验证门户节点卡片是否可以在不改写阶段事实的前提下被选择性配置。",
  };
}

export function buildExperimentTargetOptions(nodes: P6PortalViewNode[]): P6TargetOption[] {
  const options: P6TargetOption[] = [
    {
      id: "shared-modules",
      label: "共享系统卡片",
      detail: "对全部系统节点使用统一样式。",
    },
  ];

  nodes.forEach((node) => {
    if (node.kind === "module") {
      options.push({
        id: node.id,
        label: `${node.stage} ${node.title}`,
        detail: "只覆盖当前系统节点。",
      });
      return;
    }

    options.push({
      id: "user",
      label: node.title,
      detail: "参与用户节点展示样式。",
    });
  });

  return options;
}

export function resolveModuleProfile(
  draft: P6ExperimentDraft,
  nodeId: Exclude<P6PortalNodeId, "user">,
): P6ModuleCardProfile {
  return draft.moduleOverrides[nodeId] ?? draft.sharedModuleProfile;
}

export function setModuleTemplate(
  draft: P6ExperimentDraft,
  targetId: P6ExperimentTargetId,
  templateId: string,
): P6ExperimentDraft {
  if (!isModuleTarget(targetId)) {
    return draft;
  }

  if (targetId === "shared-modules") {
    return {
      ...draft,
      sharedModuleProfile: {
        ...draft.sharedModuleProfile,
        templateId,
      },
    };
  }

  return {
    ...draft,
    moduleOverrides: {
      ...draft.moduleOverrides,
      [targetId]: {
        ...resolveModuleProfile(draft, targetId),
        templateId,
      },
    },
  };
}

export function setBindingPreset(
  draft: P6ExperimentDraft,
  targetId: P6ExperimentTargetId,
  bindingPresetId: string,
): P6ExperimentDraft {
  if (!isModuleTarget(targetId)) {
    return draft;
  }

  if (targetId === "shared-modules") {
    return {
      ...draft,
      sharedModuleProfile: {
        ...draft.sharedModuleProfile,
        bindingPresetId,
      },
    };
  }

  return {
    ...draft,
    moduleOverrides: {
      ...draft.moduleOverrides,
      [targetId]: {
        ...resolveModuleProfile(draft, targetId),
        bindingPresetId,
      },
    },
  };
}

export function setUserTemplate(draft: P6ExperimentDraft, templateId: string): P6ExperimentDraft {
  return {
    ...draft,
    userProfile: {
      templateId,
    },
  };
}

export function resolveNodeCard(node: P6PortalViewNode, draft: P6ExperimentDraft): P6ResolvedNodeCard {
  if (node.kind === "user") {
    return {
      templateId: draft.userProfile.templateId,
      bindingPresetId: null,
      summary: node.summary,
      metricsCount: 0,
      showMetrics: false,
      showTimestamp: false,
      showDescription: isDetailedUserTemplate(draft.userProfile.templateId),
      showFreshness: false,
      showUserContext: true,
      showUserHints: true,
      showUserAvailability: true,
      showDegraded: false,
    };
  }

  const profile = resolveModuleProfile(draft, node.id);
  const fallbackSummary = node.stageCard.degraded_hint ?? node.stageCard.health_badge.detail ?? node.stageCard.summary_line;

  if (isAlertBinding(profile.bindingPresetId)) {
    return {
      templateId: profile.templateId,
      bindingPresetId: profile.bindingPresetId,
      summary: fallbackSummary,
      metricsCount: 1,
      showMetrics: true,
      showTimestamp: false,
      showDescription: isOverviewTemplate(profile.templateId),
      showFreshness: true,
      showUserContext: false,
      showUserHints: false,
      showUserAvailability: false,
      showDegraded: Boolean(node.stageCard.degraded_hint),
    };
  }

  if (isSummaryBinding(profile.bindingPresetId)) {
    return {
      templateId: profile.templateId,
      bindingPresetId: profile.bindingPresetId,
      summary: node.stageCard.summary_line,
      metricsCount: 1,
      showMetrics: true,
      showTimestamp: true,
      showDescription: isOverviewTemplate(profile.templateId),
      showFreshness: !isCompactTemplate(profile.templateId),
      showUserContext: false,
      showUserHints: false,
      showUserAvailability: false,
      showDegraded: false,
    };
  }

  return {
    templateId: profile.templateId,
    bindingPresetId: profile.bindingPresetId,
    summary: node.stageCard.summary_line,
    metricsCount: isCompactTemplate(profile.templateId) ? 1 : 2,
    showMetrics: true,
    showTimestamp: true,
    showDescription: isOverviewTemplate(profile.templateId),
    showFreshness: true,
    showUserContext: false,
    showUserHints: false,
    showUserAvailability: false,
    showDegraded: Boolean(node.stageCard.degraded_hint),
  };
}

export function buildExperimentRecord(
  nodes: P6PortalViewNode[],
  draft: P6ExperimentDraft,
  scenarioLabel: string,
): P6ExperimentRecord {
  const focusNode =
    nodes.find((node) => node.id === draft.selectedTargetId) ??
    nodes.find((node) => node.kind === "module" && node.stage === "P2") ??
    nodes[0];
  const resolvedCard = focusNode ? resolveNodeCard(focusNode, draft) : null;
  const targetLabel =
    draft.selectedTargetId === "shared-modules"
      ? "共享系统卡片"
      : focusNode?.kind === "module"
        ? `${focusNode.stage} ${focusNode.title}`
        : focusNode?.title ?? "未选择对象";
  const recommendation =
    draft.promotionDecision === "candidate"
      ? `建议将当前配置登记为候选，并优先反哺 ${draft.targetStages.join(" / ")}。`
      : "当前配置保留在实验层，暂不进入正式候选。";

  return {
    title: `实验记录 · ${targetLabel}`,
    summary: `场景 ${scenarioLabel} 下，当前模板为 ${resolvedCard?.templateId ?? "unknown"}，绑定为 ${resolvedCard?.bindingPresetId ?? "manual"}。`,
    issues:
      draft.selectedTargetId === "user"
        ? ["参与用户节点仍需与系统节点保持明显语义差异。"]
        : ["当前方案仍需验证在观察页承载面中的信息密度。"],
    evidenceRefs: [
      "PortalProjection.node_list",
      `scenario:${scenarioLabel}`,
      `layout:${draft.layoutPresetId}`,
    ],
    recommendation,
  };
}

export function buildPreviewEntries(nodes: P6PortalViewNode[], draft: P6ExperimentDraft) {
  const selectedNode =
    nodes.find((node) => node.id === draft.selectedTargetId) ??
    nodes.find((node) => node.kind === "module" && node.stage === "P2") ??
    nodes[0];

  if (!selectedNode) {
    return [];
  }

  if (draft.layoutPresetId.includes("compare") && selectedNode.kind === "module") {
    const baselineDraft: P6ExperimentDraft = {
      ...draft,
      moduleOverrides: {},
      sharedModuleProfile: {
        templateId: DEFAULT_MODULE_TEMPLATE_ID,
        bindingPresetId: DEFAULT_BINDING_ID,
      },
    };

    return [
      {
        id: "current",
        label: "当前配置",
        node: selectedNode,
        resolvedCard: resolveNodeCard(selectedNode, draft),
      },
      {
        id: "baseline",
        label: "标准基线",
        node: selectedNode,
        resolvedCard: resolveNodeCard(selectedNode, baselineDraft),
      },
    ];
  }

  return [
    {
      id: "current",
      label: "当前配置",
      node: selectedNode,
      resolvedCard: resolveNodeCard(selectedNode, draft),
    },
  ];
}

export function buildExperimentSavePayload(
  nodes: P6PortalViewNode[],
  draft: P6ExperimentDraft,
  scenarioLabel: string,
): P6DisplayExperimentCreateRequest {
  const focusNode =
    nodes.find((node) => node.id === draft.selectedTargetId) ??
    nodes.find((node) => node.kind === "module" && node.stage === "P2") ??
    nodes[0];
  const focusModuleProfile =
    focusNode && focusNode.kind === "module" ? resolveModuleProfile(draft, focusNode.id) : draft.sharedModuleProfile;

  return {
    goal: draft.experimentGoal,
    projection_scope: "PortalProjection",
    template_refs: focusNode?.kind === "user" ? [draft.userProfile.templateId] : [focusModuleProfile.templateId],
    binding_refs: focusNode?.kind === "user" ? [] : [focusModuleProfile.bindingPresetId],
    layout_refs: [draft.layoutPresetId],
    preset_refs: [],
    result_summary: buildExperimentRecord(nodes, draft, scenarioLabel).summary,
    issues: buildExperimentRecord(nodes, draft, scenarioLabel).issues,
    promotion_recommendation: draft.promotionDecision,
    target_stage_ids: draft.targetStages,
    evidence_refs: buildExperimentRecord(nodes, draft, scenarioLabel).evidenceRefs,
  };
}
