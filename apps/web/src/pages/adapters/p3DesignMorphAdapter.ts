import type {
  DesignMorphDocumentViewModel,
  DesignMorphStageViewModel,
  DesignMorphWindowViewModel,
  FunctionTreeNodeViewModel,
  FunctionTreeViewModel,
} from "../../components/stageWorkbench/DesignMorphCanvasPlatform";
import type { DesignMorphCanvasStageKind } from "../../components/stageWorkbench/designMorphRenderers";
import type { StageDocumentWorkbenchViewModel } from "../../components/stageWorkbench/models";
import { buildRequirementDocumentSections } from "./p3DesignLabWorkbenchAdapter";

type P3MorphStageSeed = {
  id: string;
  entityType: DesignMorphStageViewModel["entityType"];
  layoutKind: DesignMorphCanvasStageKind;
  title: string;
  subtitle: string;
  summary: (workbench: StageDocumentWorkbenchViewModel) => string;
  items: (workbench: StageDocumentWorkbenchViewModel) => string[];
  sourceRefs: (workbench: StageDocumentWorkbenchViewModel) => string[];
  constraintSummary: (workbench: StageDocumentWorkbenchViewModel) => string;
  document?: (workbench: StageDocumentWorkbenchViewModel) => DesignMorphDocumentViewModel;
  functionTree?: (workbench: StageDocumentWorkbenchViewModel) => FunctionTreeViewModel;
};

const P3_MORPH_STAGE_SEEDS: P3MorphStageSeed[] = [
  {
    id: "requirement",
    entityType: "requirement_specification",
    layoutKind: "paper",
    title: "需规文档",
    subtitle: "P2 冻结输入",
    summary: (workbench) => workbench.inputFacts.title || "等待选择已发布的需求规格说明。",
    items: (workbench) => {
      const clauses = workbench.inputFacts.sections.flatMap((section) => section.clauses.map((clause) => clause.title));
      return clauses.length ? clauses : ["需规正文", "结构化条款", "冻结快照"];
    },
    sourceRefs: () => ["P2:frozen_requirement_specification"],
    constraintSummary: (workbench) => `${workbench.inputFacts.sections.length} 个需规章节；P3 只读消费`,
    document: (workbench) =>
      buildRequirementDocumentViewModel(workbench),
  },
  {
    id: "document",
    entityType: "software_design_document",
    layoutKind: "paper",
    title: "软设文档",
    subtitle: "A4 正文形态",
    summary: (workbench) => workbench.product.title || "基础转换完成后生成软件设计说明正文草稿。",
    items: (workbench) => {
      const sections = workbench.product.sections.map((section) => section.title);
      return sections.length ? sections : ["设计目标与范围", "总体架构", "模块划分"];
    },
    sourceRefs: (workbench) => [workbench.product.documentId],
    constraintSummary: (workbench) => `${workbench.product.sections.length} 个正文小节；版本 ${workbench.product.versionLabel}`,
    document: (workbench) =>
      buildSoftwareDesignDocumentViewModel(workbench),
  },
  {
    id: "functionTree",
    entityType: "software_function_tree",
    layoutKind: "tree",
    title: "功能树",
    subtitle: "从正文拆解功能项",
    summary: () => "把需规功能拆成可追溯的树形设计对象，保持与文档章节一一对应。",
    items: (workbench) => {
      const modules = workbench.outline.baseline?.modules.map((module) => module.name) ?? [];
      return modules.length ? modules : ["规划任务管理", "冲突识别", "协同确认", "处置记录"];
    },
    sourceRefs: (workbench) => workbench.outline.baseline?.modules.map((module) => module.moduleId) ?? ["SoftwareDesignBaseline.modules"],
    constraintSummary: (workbench) => `${workbench.outline.baseline?.moduleCount ?? 0} 个设计模块；与正文和需规追溯`,
    functionTree: (workbench) =>
      buildFunctionTreeViewModel(workbench),
  },
  {
    id: "layeredArchitecture",
    entityType: "software_layered_architecture",
    layoutKind: "architecture",
    title: "分层架构",
    subtitle: "按层次放置设计对象",
    summary: (workbench) => `当前架构模式：${workbench.outline.baseline?.architectureMode ?? "待生成"}`,
    items: () => ["展示层", "功能层", "服务层", "数据层"],
    sourceRefs: (workbench) => [workbench.outline.baseline?.label ?? "SoftwareDesignBaseline.architecture"],
    constraintSummary: (workbench) => `架构模式 ${workbench.outline.baseline?.architectureMode ?? "待生成"}；允许跨层承载`,
  },
  {
    id: "technicalImplementation",
    entityType: "technical_implementation",
    layoutKind: "table",
    title: "技术实现",
    subtitle: "映射框架与真实模块",
    summary: () => "把理论模块落到框架、组件、服务和数据对象，允许一个框架覆盖多个理论层次。",
    items: () => ["unified_service", "StageLabShell", "Adapter", "Provider"],
    sourceRefs: () => ["SoftwareDesignPackage.technicalImplementation"],
    constraintSummary: () => "技术实现承载理论模块，可横跨展示层、服务层和数据层",
  },
  {
    id: "presentationShape",
    entityType: "presentation_shape",
    layoutKind: "cards",
    title: "展示形态",
    subtitle: "表达 UI 呈现方式",
    summary: () => "说明关键模块在界面上的布局位置、交互形式和可替换呈现方式。",
    items: () => ["A4 文档", "Canvas 长卷", "右侧 Inspector", "CLI 微调"],
    sourceRefs: () => ["SoftwareDesignPackage.presentationShape"],
    constraintSummary: () => "展示形态只表达候选呈现，不反向改写业务事实",
  },
  {
    id: "p4Projection",
    entityType: "module_workorder_projection",
    layoutKind: "tree",
    title: "P4 投影",
    subtitle: "下游工具包树",
    summary: (workbench) =>
      workbench.projection.status === "empty" ? "生成投影候选后显示 P4 工单组织树。" : "P3 设计基线已投影为 P4 工单候选。",
    items: (workbench) => {
      const projectionItems = collectProjectionTitles(workbench.projection.tree).slice(0, 5);
      return projectionItems.length ? projectionItems : ["P4-WO-StageLab-Workbench", "共性工作台工具包", "P3 适配工具包"];
    },
    sourceRefs: (workbench) => [workbench.projection.sourceStateId ?? "SoftwareDesignPackage.p4Projection"],
    constraintSummary: (workbench) => `${countProjectionNodes(workbench.projection.tree)} 个投影节点；从设计包派生`,
  },
];

export function buildP3DesignMorphModel(workbench: StageDocumentWorkbenchViewModel): {
  stages: DesignMorphStageViewModel[];
  windows: DesignMorphWindowViewModel[];
} {
  return {
    stages: P3_MORPH_STAGE_SEEDS.map((seed) => ({
      id: seed.id,
      entityType: seed.entityType,
      layoutKind: seed.layoutKind,
      title: seed.title,
      subtitle: seed.subtitle,
      summary: seed.summary(workbench),
      items: seed.items(workbench),
      sourceRefs: seed.sourceRefs(workbench).filter(Boolean),
      constraintSummary: seed.constraintSummary(workbench),
      document: seed.document?.(workbench),
      functionTree: seed.functionTree?.(workbench),
    })),
    windows: [
      { id: "reqdoc", title: "需规文档 -> 软设文档", fromStageId: "requirement", toStageId: "document" },
      { id: "docfunc", title: "软设文档 -> 功能树", fromStageId: "document", toStageId: "functionTree" },
      { id: "funcarch", title: "功能树 -> 分层架构", fromStageId: "functionTree", toStageId: "layeredArchitecture" },
      { id: "archtech", title: "分层架构 -> 技术实现", fromStageId: "layeredArchitecture", toStageId: "technicalImplementation" },
      { id: "techshape", title: "技术实现 -> 展示形态", fromStageId: "technicalImplementation", toStageId: "presentationShape" },
      { id: "shapep4", title: "展示形态 -> P4 投影", fromStageId: "presentationShape", toStageId: "p4Projection" },
    ],
  };
}

function buildRequirementDocumentViewModel(workbench: StageDocumentWorkbenchViewModel): DesignMorphDocumentViewModel {
  return {
    title: workbench.inputFacts.title || "需求规格说明",
    subtitle: "P2 冻结输入 / 只读消费",
    headerLeft: "CodeFactoryV2 / P2",
    headerRight: "Requirement Specification",
    footerLeft: workbench.inputFacts.sourceTitle || "P2 Frozen Package",
    footerRight: "Page 1",
    ariaLabel: "需规文档 A4 预览",
    emptyDescription: "没有可用的 P2 冻结包",
    structuredSections: buildRequirementDocumentSections(workbench.inputFacts.sections),
    sections: workbench.inputFacts.sections.flatMap((section) =>
      section.clauses.map((clause) => ({
        sectionId: clause.clauseId,
        title: clause.title,
        content: clause.content,
        status: "generated",
      })),
    ),
  };
}

function buildSoftwareDesignDocumentViewModel(workbench: StageDocumentWorkbenchViewModel): DesignMorphDocumentViewModel {
  const isConversionRunning = workbench.conversion.running && workbench.product.status !== "generated";
  return {
    title: workbench.product.title || "软件设计说明",
    subtitle: workbench.product.subtitle || "基于 P2 需求规格冻结包生成",
    headerLeft: "CodeFactoryV2 / P3",
    headerRight: "Software Design Description",
    footerLeft: workbench.product.versionLabel,
    footerRight: "Page 1",
    ariaLabel: "软设文档 A4 预览",
    emptyDescription: "尚未生成软件设计说明",
    busyState: isConversionRunning
      ? {
          title: "正在调用 Dify 生成软件设计说明",
          description: "一般耗时约 200 秒，请保持本页打开。",
          elapsedLabel: `已等待 ${formatElapsedTime(workbench.conversion.elapsedSeconds)}`,
          estimateLabel: "通常约 03:20",
          detail: "完成后会自动载入软设正文、设计基线和 P4 投影候选。",
          testId: "p3-design-conversion-waiting-document",
        }
      : undefined,
    structuredSections: workbench.product.sections,
    sections: workbench.product.sections.flatMap((section) => ({
      sectionId: section.sectionId,
      title: section.title,
      content: section.blocks.map((block) => block.content).join("\n"),
      status: section.status,
    })),
  };
}

function formatElapsedTime(totalSeconds: number): string {
  const normalized = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(normalized / 60);
  const seconds = normalized % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function buildFunctionTreeViewModel(workbench: StageDocumentWorkbenchViewModel): FunctionTreeViewModel {
  const title = `${workbench.product.title || workbench.inputFacts.title || "软件设计说明"}功能树`;
  const converterTree = buildConverterFunctionTreeViewModel(workbench, title);
  if (converterTree) {
    return converterTree;
  }

  const moduleNodes = (workbench.outline.baseline?.modules ?? []).map((module) => buildModuleFunctionTreeNode(module, workbench));
  const root: FunctionTreeNodeViewModel | null = moduleNodes.length
    ? {
        nodeId: "function-tree-root",
        title,
        nodeType: "root",
        status: "derived",
        sourceRefs: uniqueStrings(moduleNodes.flatMap((node) => node.sourceRefs)),
        designRefs: uniqueStrings(moduleNodes.flatMap((node) => node.designRefs)),
        architectureRefs: [],
        p4Refs: [],
        description: "转换器尚未返回完整功能树，当前按设计基线模块生成骨架。",
        children: moduleNodes,
      }
    : null;

  return {
    treeId: `function-tree-${workbench.product.documentId}`,
    title,
    origin: root ? "derived" : "empty",
    summary: root
      ? summarizeFunctionTree(root)
      : {
          nodeCount: 0,
          tracedNodeCount: 0,
          pendingNodeCount: 0,
          maxDepth: 0,
        },
    root,
  };
}

function buildConverterFunctionTreeViewModel(
  workbench: StageDocumentWorkbenchViewModel,
  fallbackTitle: string,
): FunctionTreeViewModel | null {
  const functionTree = workbench.outline.baseline?.functionTree;
  const root = normalizeConverterFunctionTreeNode(functionTree?.root, "function-tree-root");
  if (!root) {
    return null;
  }
  const title = functionTree?.title || fallbackTitle;
  return {
    treeId: functionTree?.treeId || `function-tree-${workbench.product.documentId}`,
    title,
    origin: "converter",
    summary: summarizeFunctionTree(root),
    root,
  };
}

function normalizeConverterFunctionTreeNode(value: unknown, fallbackNodeId: string): FunctionTreeNodeViewModel | null {
  if (!isRecord(value)) {
    return null;
  }
  const nodeId = toStringValue(value.node_id ?? value.nodeId ?? value.id) || fallbackNodeId;
  const title = toStringValue(value.title ?? value.name) || nodeId;
  const children = Array.isArray(value.children)
    ? value.children
        .map((child, index) => normalizeConverterFunctionTreeNode(child, `${nodeId}-${index + 1}`))
        .filter((node): node is FunctionTreeNodeViewModel => Boolean(node))
    : [];
  return {
    nodeId,
    title,
    nodeType: normalizeFunctionTreeNodeType(value.node_type ?? value.nodeType ?? value.type),
    status: toStringValue(value.status) || "derived",
    moduleId: toStringValue(value.module_id ?? value.moduleId) || undefined,
    sourceRefs: toStringList(value.source_refs ?? value.sourceRefs),
    designRefs: toStringList(value.design_refs ?? value.designRefs),
    architectureRefs: toStringList(value.architecture_refs ?? value.architectureRefs),
    p4Refs: toStringList(value.p4_refs ?? value.p4Refs),
    description: toStringValue(value.description) || undefined,
    children,
  };
}

function buildModuleFunctionTreeNode(
  module: NonNullable<StageDocumentWorkbenchViewModel["outline"]["baseline"]>["modules"][number],
  workbench: StageDocumentWorkbenchViewModel,
): FunctionTreeNodeViewModel {
  const traceSourceRefs = findTraceSourceRefs(module.moduleId, workbench.product.traceLinks);
  const sourceRefs = traceSourceRefs.length ? traceSourceRefs : collectFallbackSourceRefs(workbench);
  const designRefs = collectDesignRefsForSourceRefs(sourceRefs, workbench);

  return {
    nodeId: `function-node-${module.moduleId}`,
    title: module.name,
    nodeType: "module",
    status: hasFunctionTreeTrace(sourceRefs, designRefs) ? "derived" : "untraced",
    moduleId: module.moduleId,
    sourceRefs,
    designRefs,
    architectureRefs: [workbench.outline.baseline?.architectureMode ?? ""].filter(Boolean),
    p4Refs: collectP4Refs(module.moduleId, workbench),
    description: `承接“${module.name}”相关能力；详细状态、追溯和软设章节引用在 Inspector 中查看。`,
    children: [],
  };
}

function summarizeFunctionTree(root: FunctionTreeNodeViewModel): FunctionTreeViewModel["summary"] {
  const nodes = flattenFunctionTreeNodes(root);
  return {
    nodeCount: nodes.length,
    tracedNodeCount: nodes.filter((node) => hasFunctionTreeTrace(node.sourceRefs, node.designRefs)).length,
    pendingNodeCount: nodes.filter((node) => node.status === "pending_confirmation" || node.status === "untraced").length,
    maxDepth: getFunctionTreeMaxDepth(root),
  };
}

function flattenFunctionTreeNodes(root: FunctionTreeNodeViewModel): FunctionTreeNodeViewModel[] {
  return [root, ...root.children.flatMap((child) => flattenFunctionTreeNodes(child))];
}

function getFunctionTreeMaxDepth(node: FunctionTreeNodeViewModel): number {
  if (!node.children.length) {
    return 1;
  }
  return 1 + Math.max(...node.children.map((child) => getFunctionTreeMaxDepth(child)));
}

function hasFunctionTreeTrace(sourceRefs: string[], designRefs: string[]) {
  return sourceRefs.length > 0 || designRefs.length > 0;
}

function findTraceSourceRefs(moduleId: string, traceLinks: Array<Record<string, unknown>>): string[] {
  return uniqueStrings(
    traceLinks
      .filter((link) => Object.values(link).some((value) => value === moduleId))
      .flatMap((link) => Object.values(link))
      .filter((value): value is string => typeof value === "string" && value !== moduleId),
  );
}

function collectFallbackSourceRefs(workbench: StageDocumentWorkbenchViewModel): string[] {
  return uniqueStrings(workbench.product.sections.flatMap((section) => section.blocks.flatMap((block) => block.sourceRefs))).slice(0, 3);
}

function collectDesignRefsForSourceRefs(sourceRefs: string[], workbench: StageDocumentWorkbenchViewModel): string[] {
  const matchedSectionIds = workbench.product.sections
    .filter((section) => section.blocks.some((block) => block.sourceRefs.some((sourceRef) => sourceRefs.includes(sourceRef))))
    .map((section) => section.sectionId);
  return uniqueStrings(matchedSectionIds.length ? matchedSectionIds : workbench.product.sections.map((section) => section.sectionId).slice(0, 1));
}

function collectP4Refs(moduleId: string, workbench: StageDocumentWorkbenchViewModel): string[] {
  return workbench.projection.items
    .filter((item) => item.traceRefs.includes(moduleId))
    .map((item) => item.itemId);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function normalizeFunctionTreeNodeType(value: unknown): FunctionTreeNodeViewModel["nodeType"] {
  const nodeType = toStringValue(value);
  if (["root", "module", "capability", "function", "interface", "data", "state", "quality", "trace"].includes(nodeType)) {
    return nodeType as FunctionTreeNodeViewModel["nodeType"];
  }
  return "function";
}

function toStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return uniqueStrings(value.map((item) => toStringValue(item)));
}

function toStringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function collectProjectionTitles(tree: StageDocumentWorkbenchViewModel["projection"]["tree"]): string[] {
  if (!tree) {
    return [];
  }
  return [tree.title, ...(tree.children ?? []).flatMap((child) => collectProjectionTitles(child))];
}

function countProjectionNodes(tree: StageDocumentWorkbenchViewModel["projection"]["tree"]): number {
  if (!tree) {
    return 0;
  }
  return 1 + (tree.children ?? []).reduce((total, child) => total + countProjectionNodes(child), 0);
}
