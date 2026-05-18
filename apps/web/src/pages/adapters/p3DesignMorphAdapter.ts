import type {
  DesignMorphDocumentViewModel,
  DesignMorphStageViewModel,
  DesignMorphStageViewMode,
  DesignMorphWindowViewModel,
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
  viewModes?: (workbench: StageDocumentWorkbenchViewModel) => DesignMorphStageViewMode[];
};

const P3_MORPH_STAGE_SEEDS: P3MorphStageSeed[] = [
  {
    id: "requirement",
    entityType: "requirement_specification",
    layoutKind: "paper",
    title: "需规",
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
    viewModes: () => buildDocumentViewModes(),
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
    viewModes: () => buildDocumentViewModes(),
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
      viewModes: seed.viewModes?.(workbench),
    })),
    windows: [
      { id: "reqdoc", title: "需规 -> 软设文档", fromStageId: "requirement", toStageId: "document" },
      { id: "docfunc", title: "软设文档 -> 功能树", fromStageId: "document", toStageId: "functionTree" },
      { id: "funcarch", title: "功能树 -> 分层架构", fromStageId: "functionTree", toStageId: "layeredArchitecture" },
      { id: "archtech", title: "分层架构 -> 技术实现", fromStageId: "layeredArchitecture", toStageId: "technicalImplementation" },
      { id: "techshape", title: "技术实现 -> 展示形态", fromStageId: "technicalImplementation", toStageId: "presentationShape" },
      { id: "shapep4", title: "展示形态 -> P4 投影", fromStageId: "presentationShape", toStageId: "p4Projection" },
    ],
  };
}

function buildDocumentViewModes(): DesignMorphStageViewMode[] {
  return [
    { id: "a4", label: "A4" },
    { id: "edit", label: "编辑区" },
  ];
}

function buildRequirementDocumentViewModel(workbench: StageDocumentWorkbenchViewModel): DesignMorphDocumentViewModel {
  return {
    title: workbench.inputFacts.title || "需求规格说明",
    subtitle: "P2 冻结输入 / 只读消费",
    headerLeft: "CodeFactoryV2 / P2",
    headerRight: "Requirement Specification",
    footerLeft: workbench.inputFacts.sourceTitle || "P2 Frozen Package",
    footerRight: "Page 1",
    ariaLabel: "需规 A4 预览",
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
