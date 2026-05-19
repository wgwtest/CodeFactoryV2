import type {
  P3DesignLabDocumentBlock,
  P3DesignLabDocumentSection,
  P3DesignLabInputPackage,
  P3DesignLabSession,
  RequirementAuthoringCheckResult,
} from "../../lib/api";
import type {
  StageDocumentWorkbenchViewModel,
  StandardDocumentBlockKind,
  StandardDocumentBlockViewModel,
  StandardDocumentSectionViewModel,
} from "../../components/stageWorkbench/models";

type BuildP3DesignLabWorkbenchViewModelInput = {
  inputPackage: P3DesignLabInputPackage | null;
  session: P3DesignLabSession | null;
  policy: Record<string, string>;
  conversionRunning?: boolean;
  conversionElapsedSeconds?: number;
};

export function buildP3DesignLabWorkbenchViewModel({
  inputPackage,
  session,
  policy,
  conversionRunning = false,
  conversionElapsedSeconds = 0,
}: BuildP3DesignLabWorkbenchViewModelInput): StageDocumentWorkbenchViewModel {
  const visiblePackage = session?.input_package ?? inputPackage;
  const designDocument = session?.design_document ?? null;
  const designBaseline = session?.design_baseline ?? null;
  const projection = session?.workorder_projection ?? null;
  const conversion = session?.conversion ?? null;

  return {
    identity: {
      stage: "P3",
      documentType: "软件设计说明",
      upstreamStage: "P2",
      downstreamStage: "P4",
    },
    header: {
      title: "P3 Software Design Lab",
      subtitle: "从 P2 需求规格冻结包生成软件设计说明、设计基线和 P4 投影",
      statusLabel: session ? `状态：${session.status}` : "状态：待生成",
      sourceLabel: "输入：P2 authoring frozen_package",
      providerLabel: "Provider：Mock Design Provider",
    },
    layout: {
      defaultActiveProductTab: "document",
    },
    inputFacts: {
      title: visiblePackage?.standard_document.title ?? "",
      sourceTitle: visiblePackage?.source_title ?? "没有可用的 P2 冻结包",
      readonly: true,
      sections:
        visiblePackage?.standard_document.sections.map((section) => ({
          sectionId: section.section_id,
          title: section.title,
          clauses: section.clauses.map((clause) => ({
            clauseId: clause.clause_id,
            title: clause.title,
            content: clause.content,
          })),
        })) ?? [],
      relatedDesigns: visiblePackage?.related_designs ?? [],
      emptyDescription: "没有 P2 新版冻结包",
    },
    interaction: {
      mode: "cli",
      title: "自然语言配置 / CLI",
      description: "用于控制转换策略和校正输出，不替代需规输入",
      runline: [
        { key: "input", label: "P2 冻结包", state: visiblePackage ? "done" : "idle" },
        { key: "generation", label: "基础转换", state: designDocument ? "done" : session ? "active" : "idle" },
        { key: "baseline", label: "基线固化", state: designBaseline ? "done" : "idle" },
        { key: "projection", label: "P4 投影", state: projection ? "done" : "idle" },
      ],
      policies: [
        { key: "architecture_preference", label: "架构偏好", value: policy.architecture_preference ?? "" },
        { key: "module_granularity", label: "模块粒度", value: policy.module_granularity ?? "" },
        { key: "output_style", label: "输出风格", value: policy.output_style ?? "" },
      ],
      message: session
        ? designDocument
          ? "已生成软件设计说明和设计基线。可继续输入：细化模块 / 重生成接口 / 增加状态机 / 保守一点。"
          : "已创建待转换软设，请先在需规转软设视图执行基础转换。"
        : "选择 P2 冻结包后，新建软件设计说明并进入需规转软设基础转换。",
      feed: [
        {
          id: "input-facts",
          speaker: "P3",
          content: "读取需规正文、结构化字段和标注，保持只读。",
        },
        {
          id: "system-status",
          speaker: "SYS",
          content: session
            ? designDocument
              ? "设计基线已就绪，等待下一轮自然语言配置。"
              : "待执行需规转软设基础转换。"
            : "等待创建软件设计说明。",
        },
        ...(session?.turns.map((turn, index) => ({
          id: toDisplayString(turn.turn_id, `turn-${index + 1}`),
          speaker: toDisplayString(turn.normalized_intent, "TURN"),
          content: toDisplayString(turn.assistant_message, toDisplayString(turn.user_input, "设计回合已记录。")),
        })) ?? []),
      ],
      composer: {
        ariaLabel: "P3 Design Lab CLI",
        disabled: !session || !designDocument,
        submitLabel: "提交",
      },
    },
    product: {
      documentId: session?.session_id ?? "p3-design-lab-draft",
      documentType: "software_design_description",
      title: designDocument?.title,
      subtitle: "基于 P2 需求规格冻结包生成",
      versionLabel: session?.version_label ?? designDocument?.version_label ?? "SoftwareDesignBaseline v2",
      status: designDocument ? "generated" : conversionRunning ? "draft" : "empty",
      page: {
        ariaLabel: "A4 软件设计说明预览",
        headerLeft: "CodeFactoryV2 / P3",
        headerRight: "Software Design Description",
        footerLeft: session?.version_label ?? designDocument?.version_label ?? "SoftwareDesignBaseline v2",
        footerRight: "Page 1",
        emptyDescription: conversionRunning ? "正在调用 Dify 生成软件设计说明" : "尚未生成软件设计说明",
      },
      sections:
        designDocument?.sections.map((section) => buildSoftwareDesignDocumentSection(section)) ?? [],
      annotations: [],
      traceLinks: designBaseline?.traceability ?? [],
    },
    outline: {
      sections:
        designDocument?.sections.map((section) => buildDocumentOutlineSection(section)) ?? [],
      baseline: designBaseline
          ? {
            label: session?.version_label ?? designDocument?.version_label ?? "SoftwareDesignBaseline v2",
            architectureMode: designBaseline.architecture_mode,
            moduleCount: designBaseline.modules.length,
            traceabilityCount: designBaseline.traceability?.length ?? 0,
            modules: designBaseline.modules.map((module) => ({
              moduleId: module.module_id,
              name: module.name,
            })),
            functionTree: normalizeBaselineFunctionTree(designBaseline.function_tree ?? designBaseline.functionTree),
          }
        : undefined,
      emptyDescription: "生成软件设计说明后显示目录和模块映射",
    },
    conversion: buildConversionViewModel(conversion, Boolean(session && !designDocument), conversionRunning, conversionElapsedSeconds),
    quality: buildQualityGateViewModel(session?.check_result ?? null),
    projection: {
      targetStage: "P4",
      packageName: "P4 工单投影",
      status: projection ? "ready" : "empty",
      sourceDocumentId: designDocument?.title,
      sourceStateId: designBaseline?.baseline_id,
      tree: projection?.tree ? buildProjectionTreeNode(projection.tree) : undefined,
      items:
        projection?.items.map((item) => ({
          itemId: item.item_id,
          title: item.title,
          itemType: "module_workorder",
          description: item.description,
          traceRefs: item.module_id ? [item.module_id] : [],
          readiness: item.readiness ?? "ready",
        })) ?? [],
      emptyDescription: "生成软件设计说明后显示 P4 投影预览。",
    },
    freeze: {
      status: session?.status === "frozen" ? "frozen" : designDocument && designBaseline && projection ? "candidate" : "not_ready",
      gates: [],
      candidateOutputs: ["软件设计说明", session?.version_label ?? "SoftwareDesignBaseline v2", "P4 模块工单投影"],
      frozenRecord: session?.frozen_package
        ? {
            recordId: session.frozen_package.package_id,
            frozenAt: session.frozen_package.frozen_at,
          }
        : undefined,
    },
    runtimeEvents:
      session?.runtime_events?.map((event) => ({
        eventId: event.event_id,
        event_type: event.event_type,
        eventType: event.event_type,
        message: event.message,
        created_at: event.created_at,
        createdAt: event.created_at,
      })) ?? [],
    actions: [
      {
        key: "generate",
        label: "生成软件设计说明",
        disabled: !inputPackage,
        loading: false,
      },
    ],
  };
}

function normalizeBaselineFunctionTree(value: unknown): NonNullable<StageDocumentWorkbenchViewModel["outline"]["baseline"]>["functionTree"] | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  return {
    treeId: toDisplayString(value.tree_id ?? value.treeId, ""),
    title: toDisplayString(value.title, ""),
    root: value.root,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function buildQualityGateViewModel(checkResult: RequirementAuthoringCheckResult | null): StageDocumentWorkbenchViewModel["quality"] {
  if (!checkResult) {
    return {
      status: "not_run",
      summary: {
        blockingCount: 0,
        warningCount: 0,
        passedCount: 0,
      },
      gates: [],
      emptyDescription: "尚未运行设计完整性检查",
    };
  }

  return {
    status: checkResult.blocking_count > 0 ? "blocked" : checkResult.warning_count > 0 ? "warning" : "passed",
    summary: {
      blockingCount: checkResult.blocking_count,
      warningCount: checkResult.warning_count,
      passedCount: checkResult.passed_count,
    },
    gates: checkResult.items.map((item, index) => ({
      itemId: toDisplayString(item.item_id, `gate-${index + 1}`),
      severity: toDisplayString(item.severity, "info"),
      title: toDisplayString(item.title, `检查项 ${index + 1}`),
      description: toDisplayString(item.description, "没有补充说明"),
      scope: toDisplayString(item.scope, "document"),
      anchorId: toOptionalDisplayString(item.anchor_id),
      suggestedAction: toOptionalDisplayString(item.suggested_action),
    })),
    emptyDescription: "尚未运行设计完整性检查",
  };
}

function buildConversionViewModel(
  conversion: P3DesignLabSession["conversion"],
  conversionSessionPending = false,
  conversionRunning = false,
  conversionElapsedSeconds = 0,
): StageDocumentWorkbenchViewModel["conversion"] {
  const elapsedSeconds = conversionRunning ? conversionElapsedSeconds : 0;
  if (!conversion) {
    const steps = buildDefaultConversionSteps();
    return {
      status: conversionRunning ? "conversion_running" : conversionSessionPending ? "conversion_pending" : "empty",
      running: conversionRunning,
      elapsedSeconds,
      progressNote: conversionRunning ? "预计进度，Dify 返回后以实际结果为准" : undefined,
      strategy: "standard_sdd_draft",
      strategyOptions: [
        {
          value: "standard_sdd_draft",
          label: "标准软设草稿生成",
          description: "按标准软设章节生成初稿。",
        },
        {
          value: "component_first",
          label: "组件优先拆解",
          description: "优先抽取组件、接口和可复用工作台对象。",
        },
        {
          value: "p4_projection_first",
          label: "P4 投影优先",
          description: "优先组织下游工具包和工单分支。",
        },
      ],
      steps: conversionRunning ? buildEstimatedConversionSteps(steps, elapsedSeconds) : steps,
      draftPreview: null,
      traceabilitySummary: null,
      processOutput: undefined,
      emptyDescription: "新建软件设计说明后显示基础转换过程。",
    };
  }

  const running = conversionRunning || conversion.status === "conversion_running";
  const steps = conversion.steps.map((step) => ({
    stepId: step.step_id,
    title: step.title,
    description: step.description,
    status: step.status,
  }));

  return {
    status: conversionRunning ? "conversion_running" : conversion.status,
    running,
    elapsedSeconds,
    progressNote: running ? "预计进度，Dify 返回后以实际结果为准" : undefined,
    strategy: conversion.strategy,
    strategyOptions: conversion.strategy_options,
    steps: running ? buildEstimatedConversionSteps(steps, elapsedSeconds) : steps,
    draftPreview: conversion.draft_preview
      ? {
          title: conversion.draft_preview.title,
          versionLabel: conversion.draft_preview.version_label,
          sections: conversion.draft_preview.sections,
        }
      : null,
    traceabilitySummary: conversion.traceability_summary
      ? {
          mappedClauseCount: conversion.traceability_summary.mapped_clause_count,
          targetCount: conversion.traceability_summary.target_count,
          pendingConfirmationCount: conversion.traceability_summary.pending_confirmation_count,
        }
      : null,
    processOutput: conversion.process_output,
    emptyDescription: "新建软件设计说明后显示基础转换过程。",
  };
}

function buildDefaultConversionSteps(): StageDocumentWorkbenchViewModel["conversion"]["steps"] {
  return [
    {
      stepId: "read_requirement",
      title: "读取需规冻结包",
      description: "加载正文、结构化条款和冻结快照。",
      status: "pending",
    },
    {
      stepId: "extract_design_objects",
      title: "抽取设计对象",
      description: "抽取模块、接口、数据对象和质量属性候选。",
      status: "pending",
    },
    {
      stepId: "generate_design_draft",
      title: "生成软设草稿",
      description: "生成 A4 正文草稿和结构化设计事实初稿。",
      status: "pending",
    },
    {
      stepId: "map_traceability",
      title: "建立追溯映射",
      description: "建立需规条款到章节、模块和接口的追溯。",
      status: "pending",
    },
  ];
}

function buildEstimatedConversionSteps(
  steps: StageDocumentWorkbenchViewModel["conversion"]["steps"],
  elapsedSeconds: number,
): StageDocumentWorkbenchViewModel["conversion"]["steps"] {
  const currentIndex = elapsedSeconds < 60 ? 1 : elapsedSeconds < 180 ? 2 : 3;

  return steps.map((step, index) => ({
    ...step,
    status: index < currentIndex ? "done" : index === currentIndex ? "running" : "pending",
  }));
}

function toDisplayString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function toOptionalDisplayString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value : undefined;
}

function buildSoftwareDesignDocumentSection(section: P3DesignLabDocumentSection): StandardDocumentSectionViewModel {
  const blocks = Array.isArray(section.blocks) && section.blocks.length
    ? section.blocks.map((block, index) => buildSoftwareDesignDocumentBlock(block, section, index))
    : [
        {
          blockId: `${section.section_id}-body`,
          kind: "paragraph" as const,
          content: section.content,
          anchorId: section.section_id,
          sourceRefs: section.source_refs ?? [],
          qualityRefs: [],
        },
      ];
  return {
    sectionId: section.section_id,
    title: section.title,
    status: section.status ?? "generated",
    blocks,
    children: collectDocumentChildSections(section).map((child) => buildSoftwareDesignDocumentSection(child)),
  };
}

function buildSoftwareDesignDocumentBlock(
  block: P3DesignLabDocumentBlock,
  section: P3DesignLabDocumentSection,
  index: number,
): StandardDocumentBlockViewModel {
  const kind = toStandardDocumentBlockKind(block.kind);
  return {
    blockId: toDisplayString(block.block_id ?? block.blockId, `${section.section_id}-block-${index + 1}`),
    kind,
    title: toOptionalDisplayString(block.title),
    content: toDisplayString(block.content, ""),
    diagramType: toOptionalDisplayString(block.diagram_type ?? block.diagramType),
    columns: Array.isArray(block.columns) ? block.columns.map((column) => toDisplayString(column, "")) : undefined,
    rows: Array.isArray(block.rows)
      ? block.rows.map((row) => Array.isArray(row) ? row.map((cell) => toDisplayString(cell, "")) : [])
      : undefined,
    anchorId: toOptionalDisplayString(block.anchor_id ?? block.anchorId),
    sourceRefs: Array.isArray(block.source_refs)
      ? block.source_refs
      : Array.isArray(block.sourceRefs)
        ? block.sourceRefs
        : section.source_refs ?? [],
    qualityRefs: Array.isArray(block.quality_refs) ? block.quality_refs : Array.isArray(block.qualityRefs) ? block.qualityRefs : [],
  };
}

function collectDocumentChildSections(section: P3DesignLabDocumentSection): P3DesignLabDocumentSection[] {
  if (Array.isArray(section.children) && section.children.length) {
    return section.children;
  }
  if (Array.isArray(section.subsections) && section.subsections.length) {
    return section.subsections;
  }
  return [];
}

function buildDocumentOutlineSection(section: P3DesignLabDocumentSection): StageDocumentWorkbenchViewModel["outline"]["sections"][number] {
  return {
    sectionId: section.section_id,
    title: section.title,
    children: collectDocumentChildSections(section).map((child) => buildDocumentOutlineSection(child)),
  };
}

function toStandardDocumentBlockKind(value: unknown): StandardDocumentBlockKind {
  if (
    value === "paragraph" ||
    value === "clause" ||
    value === "table" ||
    value === "list" ||
    value === "code" ||
    value === "diagram" ||
    value === "diagram_placeholder"
  ) {
    return value;
  }
  return "paragraph";
}

function buildProjectionTreeNode(
  node: NonNullable<P3DesignLabSession["workorder_projection"]>["tree"],
): StageDocumentWorkbenchViewModel["projection"]["tree"] {
  if (!node) {
    return undefined;
  }
  return {
    nodeId: node.node_id,
    title: node.title,
    nodeType: node.node_type,
    description: node.description,
    readiness: node.readiness,
    sourceRefs: node.source_refs,
    dependsOn: node.depends_on,
    acceptance: node.acceptance,
    children: node.children?.map((child) => buildProjectionTreeNode(child)).filter((child) => child !== undefined),
  };
}

export function buildRequirementDocumentSections(
  sections: StageDocumentWorkbenchViewModel["inputFacts"]["sections"],
): StandardDocumentSectionViewModel[] {
  return sections.map<StandardDocumentSectionViewModel>((section) => ({
    sectionId: section.sectionId,
    title: section.title,
    status: "generated",
    blocks: section.clauses.map((clause) => ({
      blockId: clause.clauseId,
      kind: "clause" as const,
      title: clause.title,
      content: clause.content,
      sourceRefs: [clause.clauseId],
      qualityRefs: [],
    })),
  }));
}
