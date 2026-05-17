import { describe, expect, test } from "vitest";

import {
  DESIGN_MORPH_STAGE_RENDERERS,
  resolveCanvasStageRenderer,
} from "../components/stageWorkbench/designMorphRenderers";
import type { StageDocumentWorkbenchViewModel } from "../components/stageWorkbench/models";
import { buildP3DesignMorphModel } from "../pages/adapters/p3DesignMorphAdapter";

describe("P3 design morph model", () => {
  test("builds the canonical software design morph chain from decoupled workbench projections", () => {
    const model = buildP3DesignMorphModel(buildWorkbench());

    expect(model.stages.map((stage) => stage.id)).toEqual([
      "requirement",
      "document",
      "functionTree",
      "layeredArchitecture",
      "technicalImplementation",
      "presentationShape",
      "p4Projection",
    ]);
    expect(model.stages.map((stage) => stage.entityType)).toEqual([
      "requirement_specification",
      "software_design_document",
      "software_function_tree",
      "software_layered_architecture",
      "technical_implementation",
      "presentation_shape",
      "module_workorder_projection",
    ]);
    expect(model.stages.map((stage) => stage.layoutKind)).toEqual([
      "paper",
      "paper",
      "tree",
      "architecture",
      "table",
      "cards",
      "tree",
    ]);
    expect(model.stages[0].sourceRefs).toContain("P2:frozen_requirement_specification");
    expect(model.stages[2].constraintSummary).toContain("2 个设计模块");
    expect(model.stages[6].constraintSummary).toContain("2 个投影节点");
    expect(model.windows.map((window) => `${window.fromStageId}->${window.toStageId}`)).toEqual([
      "requirement->document",
      "document->functionTree",
      "functionTree->layeredArchitecture",
      "layeredArchitecture->technicalImplementation",
      "technicalImplementation->presentationShape",
      "presentationShape->p4Projection",
    ]);
  });

  test("registers canvas stage renderers by presentation kind instead of P3 business stage id", () => {
    expect(Object.keys(DESIGN_MORPH_STAGE_RENDERERS).sort()).toEqual([
      "architecture",
      "cards",
      "paper",
      "table",
      "tree",
    ]);
    expect(resolveCanvasStageRenderer("architecture")).toBe(DESIGN_MORPH_STAGE_RENDERERS.architecture);
    expect(resolveCanvasStageRenderer("unknown-renderer")).toBe(DESIGN_MORPH_STAGE_RENDERERS.paper);
  });
});

function buildWorkbench(): StageDocumentWorkbenchViewModel {
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
      statusLabel: "状态：draft_ready",
    },
    layout: {
      defaultActiveProductTab: "document",
    },
    inputFacts: {
      title: "空域协同规划软件需求规格说明",
      sourceTitle: "P2 冻结包",
      readonly: true,
      sections: [
        {
          sectionId: "req-1",
          title: "功能需求",
          clauses: [
            { clauseId: "REQ-1", title: "规划任务", content: "支持规划任务管理。" },
            { clauseId: "REQ-2", title: "协同确认", content: "支持协同确认。" },
          ],
        },
      ],
      relatedDesigns: [],
      emptyDescription: "没有 P2 新版冻结包",
    },
    interaction: {
      mode: "cli",
      title: "自然语言配置 / CLI",
      description: "用于控制转换策略和校正输出",
      runline: [
        { key: "input", label: "P2 冻结包", state: "done" },
        { key: "generation", label: "基础转换", state: "done" },
        { key: "baseline", label: "基线固化", state: "done" },
        { key: "projection", label: "P4 投影", state: "done" },
      ],
      policies: [],
      message: "已生成软件设计说明和设计基线。",
      feed: [],
      composer: {
        ariaLabel: "P3 Design Lab CLI",
        disabled: false,
        submitLabel: "提交",
      },
    },
    product: {
      documentId: "p3dl-1",
      documentType: "software_design_description",
      title: "空域协同规划软件设计说明",
      subtitle: "基于 P2 需求规格冻结包生成",
      versionLabel: "v0.1",
      status: "generated",
      page: {
        ariaLabel: "A4 软件设计说明预览",
        headerLeft: "CodeFactoryV2 / P3",
        headerRight: "Software Design Description",
        footerLeft: "v0.1",
        footerRight: "Page 1",
        emptyDescription: "尚未生成软件设计说明",
      },
      sections: [
        {
          sectionId: "sdd-1",
          title: "总体架构",
          status: "generated",
          blocks: [
            {
              blockId: "sdd-1-body",
              kind: "paragraph",
              content: "采用统一服务优先。",
              sourceRefs: ["REQ-1"],
              qualityRefs: [],
            },
          ],
        },
      ],
      annotations: [],
      traceLinks: [{ source: "REQ-1", target: "module-planning" }],
    },
    outline: {
      sections: [{ sectionId: "sdd-1", title: "总体架构" }],
      baseline: {
        label: "v0.1",
        architectureMode: "unified_service",
        moduleCount: 2,
        traceabilityCount: 1,
        modules: [
          { moduleId: "module-planning", name: "规划任务管理" },
          { moduleId: "module-collaboration", name: "协同确认" },
        ],
      },
      emptyDescription: "生成软件设计说明后显示目录和模块映射",
    },
    conversion: {
      status: "draft_ready",
      strategy: "standard_sdd_draft",
      strategyOptions: [],
      steps: [],
      draftPreview: null,
      traceabilitySummary: {
        mappedClauseCount: 1,
        targetCount: 2,
        pendingConfirmationCount: 0,
      },
      emptyDescription: "待转换",
    },
    quality: {
      status: "not_run",
      summary: {
        blockingCount: 0,
        warningCount: 0,
        passedCount: 0,
      },
      gates: [],
      emptyDescription: "尚未运行设计完整性检查",
    },
    projection: {
      targetStage: "P4",
      packageName: "P4 工单投影",
      status: "ready",
      sourceDocumentId: "空域协同规划软件设计说明",
      sourceStateId: "v0.1",
      tree: {
        nodeId: "p4-root",
        title: "P4-WO-StageLab-Workbench",
        nodeType: "batch",
        readiness: "ready",
        sourceRefs: ["SoftwareDesignPackage"],
        children: [
          {
            nodeId: "p4-child",
            title: "A. 共性工作台工具包",
            nodeType: "package",
            readiness: "ready",
            sourceRefs: ["SoftwareDesign.modules.commonWorkbench"],
          },
        ],
      },
      items: [
        {
          itemId: "wo-1",
          title: "共性工作台工具包",
          itemType: "module_workorder",
          traceRefs: ["module-planning"],
          readiness: "ready",
        },
      ],
      emptyDescription: "生成软件设计说明后显示 P4 投影预览。",
    },
    freeze: {
      status: "candidate",
      gates: [],
      candidateOutputs: ["软件设计说明", "v0.1", "P4 模块工单投影"],
    },
    runtimeEvents: [],
    actions: [],
  };
}
