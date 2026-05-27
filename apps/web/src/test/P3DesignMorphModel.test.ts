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
    const functionTreeStage = model.stages.find((stage) => stage.id === "functionTree");

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
    expect(functionTreeStage?.functionTree).toEqual(
      expect.objectContaining({
        treeId: "function-tree-p3dl-1",
        title: "空域协同规划软件设计说明功能树",
        origin: "derived",
        summary: expect.objectContaining({
          nodeCount: 3,
          tracedNodeCount: 3,
          pendingNodeCount: 0,
          maxDepth: 2,
        }),
        root: expect.objectContaining({
          nodeId: "function-tree-root",
          title: "空域协同规划软件设计说明功能树",
          children: expect.arrayContaining([
            expect.objectContaining({
              nodeId: "function-node-module-planning",
              title: "规划任务管理",
              nodeType: "module",
              status: "derived",
              sourceRefs: ["REQ-1"],
              designRefs: ["sdd-1"],
              children: [],
            }),
            expect.objectContaining({
              nodeId: "function-node-module-collaboration",
              title: "协同确认",
              children: [],
            }),
          ]),
        }),
      }),
    );
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

  test("does not turn software design document sections into fallback function tree nodes", () => {
    const workbench = buildWorkbench();
    workbench.product.sections = [
      {
        sectionId: "purpose",
        title: "文档目的与设计口径",
        status: "generated",
        blocks: [
          {
            blockId: "purpose-body",
            kind: "paragraph",
            content: "说明本文档目的。",
            sourceRefs: ["REQ-1"],
            qualityRefs: [],
          },
        ],
      },
      {
        sectionId: "runtime-flow",
        title: "关键运行流程",
        status: "generated",
        blocks: [
          {
            blockId: "runtime-flow-body",
            kind: "paragraph",
            content: "说明运行流程。",
            sourceRefs: ["REQ-1"],
            qualityRefs: [],
          },
        ],
      },
    ];

    const model = buildP3DesignMorphModel(workbench);
    const functionTree = model.stages.find((stage) => stage.id === "functionTree")?.functionTree;
    const titles = collectFunctionTreeTitles(functionTree?.root ?? null);

    expect(titles).toContain("规划任务管理");
    expect(titles).not.toContain("文档目的与设计口径");
    expect(titles).not.toContain("关键运行流程");
    expect(functionTree?.root?.children[0]).toEqual(
      expect.objectContaining({
        title: "规划任务管理",
        designRefs: ["purpose", "runtime-flow"],
        children: [],
      }),
    );
  });

  test("projects converter function tree as business hierarchy while preserving support nodes for inspector", () => {
    const workbench = buildWorkbench();
    workbench.outline.baseline!.functionTree = {
      treeId: "function-tree-converter",
      title: "空域协同规划软件功能树",
      root: {
        node_id: "ft-root",
        title: "空域协同规划软件",
        node_type: "root",
        children: [
          {
            node_id: "module-planning",
            title: "规划任务管理模块",
            node_type: "module",
            source_refs: ["REQ-3.2"],
            design_refs: ["sdd-module-planning"],
            children: [
              {
                node_id: "cap-planning-task",
                title: "规划任务管理能力",
                node_type: "capability",
                children: [
                  { node_id: "fn-create-task", title: "创建规划任务", node_type: "function", source_refs: ["REQ-3.2"] },
                  { node_id: "fn-maintain-scope", title: "维护任务范围", node_type: "function", source_refs: ["REQ-3.2"] },
                  { node_id: "fn-track-state", title: "跟踪任务状态", node_type: "function", source_refs: ["REQ-3.2"] },
                  { node_id: "api-create-task", title: "POST /planning-tasks", node_type: "interface" },
                  { node_id: "api-get-task", title: "GET /planning-tasks/{id}", node_type: "interface" },
                  { node_id: "state-draft", title: "draft", node_type: "state" },
                  { node_id: "state-submitted", title: "submitted", node_type: "state" },
                ],
              },
              { node_id: "data-task", title: "PlanningTask", node_type: "data" },
              { node_id: "data-scope", title: "TaskScope", node_type: "data" },
              { node_id: "quality-task-trace", title: "规划任务状态变化必须保留留痕记录", node_type: "quality" },
            ],
          },
        ],
      },
    };

    const model = buildP3DesignMorphModel(workbench);
    const functionTree = model.stages.find((stage) => stage.id === "functionTree")?.functionTree;
    const root = functionTree?.root ?? null;
    const visibleTitles = collectFunctionTreeTitles(root);
    const moduleNode = root?.children[0] ?? null;
    const capabilityNode = moduleNode?.children[0] ?? null;

    expect(functionTree).toEqual(
      expect.objectContaining({
        origin: "converter",
        summary: expect.objectContaining({
          nodeCount: 6,
          maxDepth: 4,
        }),
      }),
    );
    expect(visibleTitles).toEqual([
      "空域协同规划软件",
      "规划任务管理模块",
      "规划任务管理能力",
      "创建规划任务",
      "维护任务范围",
      "跟踪任务状态",
    ]);
    expect(visibleTitles).not.toContain("POST /planning-tasks");
    expect(visibleTitles).not.toContain("PlanningTask");
    expect(visibleTitles).not.toContain("draft");
    expect(visibleTitles).not.toContain("规划任务状态变化必须保留留痕记录");
    expect(collectSupportingNodeTitles(capabilityNode)).toEqual(
      expect.arrayContaining(["POST /planning-tasks", "GET /planning-tasks/{id}", "draft", "submitted"]),
    );
    expect(collectSupportingNodeTitles(moduleNode)).toEqual(
      expect.arrayContaining(["PlanningTask", "TaskScope", "规划任务状态变化必须保留留痕记录"]),
    );
  });

  test("uses structured layered architecture output for the architecture stage", () => {
    const workbench = buildWorkbench();
    workbench.outline.baseline!.layeredArchitecture = {
      architectureId: "layered-architecture",
      title: "分层架构设计",
      pattern: "business-module-oriented-layered-architecture",
      description: "按业务模块纵切片组织功能，按分层架构承载交互、编排、领域服务、数据与集成。",
      sourceRefs: ["REQ-3.2"],
      designRefs: ["sdd-03"],
      layers: [
        {
          layerId: "presentation",
          name: "展示交互层",
          responsibility: "承载用户操作入口、状态展示和交互反馈。",
          inputs: ["用户操作"],
          outputs: ["业务请求"],
          components: [{ componentId: "cmp-planning-task-workbench", name: "规划任务工作台", moduleRefs: ["module-planning"], functionRefs: ["fn-create-task"] }],
        },
        {
          layerId: "domain-service",
          name: "领域服务层",
          responsibility: "承载规划任务创建、范围维护和状态流转规则。",
          inputs: ["业务命令"],
          outputs: ["领域结果"],
          components: [{ componentId: "svc-planning-task-domain", name: "规划任务领域服务", moduleRefs: ["module-planning"], functionRefs: ["fn-create-task"] }],
        },
      ],
      moduleLayerMappings: [
        {
          mappingId: "map-planning-task-domain",
          moduleId: "module-planning",
          moduleName: "规划任务管理",
          layerId: "domain-service",
          layerName: "领域服务层",
          responsibility: "承载规划任务核心规则。",
          componentRefs: ["svc-planning-task-domain"],
          functionRefs: ["fn-create-task"],
          sourceRefs: ["REQ-3.2"],
        },
      ],
      functionLayerMappings: [],
      crossLayerRelations: [],
      diagrams: [{ diagramId: "D1", title: "分层架构与模块映射图", diagramType: "mermaid", content: "flowchart TB" }],
    };

    const model = buildP3DesignMorphModel(workbench);
    const architectureStage = model.stages.find((stage) => stage.id === "layeredArchitecture");

    expect(architectureStage).toEqual(
      expect.objectContaining({
        summary: "分层架构设计：business-module-oriented-layered-architecture",
        items: ["展示交互层", "领域服务层", "规划任务管理 -> 领域服务层"],
        sourceRefs: ["REQ-3.2", "sdd-03"],
        constraintSummary: "2 个架构层；0 条功能-层映射；1 张架构图",
      }),
    );
  });

  test("prefers C4 architecture view group output for the architecture stage", () => {
    const workbench = buildWorkbench();
    workbench.outline.baseline = {
      ...workbench.outline.baseline!,
      architectureViews: {
        viewGroupId: "architecture-views",
        title: "架构视图组",
        defaultViewId: "view-c4-structure",
        tabs: [
          { viewId: "view-business-boundary", title: "业务边界", viewType: "business_boundary", order: 1 },
          { viewId: "view-c4-structure", title: "系统结构", viewType: "c4_component", order: 2 },
          { viewId: "view-runtime-main", title: "运行链路", viewType: "runtime_scenario", order: 3 },
          { viewId: "view-layer-roles", title: "职责层", viewType: "layer_roles", order: 4 },
        ],
        views: [
          {
            viewId: "view-c4-structure",
            viewType: "c4_component",
            title: "系统结构",
            description: "展示系统容器、核心组件、数据存储和外部系统之间的结构关系。",
            nodeRefs: ["container-planning-workbench", "component-task-command-service"],
            relationRefs: ["rel-workbench-call-command-service"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-03"],
          },
        ],
        nodes: [
          {
            nodeId: "container-planning-workbench",
            nodeType: "container",
            title: "规划任务工作台",
            description: "承载规划任务的用户操作入口。",
            layerRoles: ["presentation"],
            moduleRefs: ["module-planning"],
            functionRefs: ["fn-create-task"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-03"],
          },
          {
            nodeId: "component-task-command-service",
            nodeType: "component",
            title: "规划任务命令服务",
            description: "接收创建规划任务命令并编排领域规则。",
            layerRoles: ["application_orchestration"],
            moduleRefs: ["module-planning"],
            functionRefs: ["fn-create-task"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-03"],
          },
        ],
        architectureRelations: [
          {
            relationId: "rel-workbench-call-command-service",
            fromNodeId: "container-planning-workbench",
            toNodeId: "component-task-command-service",
            relationType: "calls",
            title: "提交创建任务命令",
            functionRefs: ["fn-create-task"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-03"],
          },
        ],
        runtimeScenarios: [
          {
            scenarioId: "scenario-create-task",
            title: "创建规划任务运行链路",
            trigger: "用户提交创建规划任务。",
            functionRefs: ["fn-create-task"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-04"],
            steps: [
              {
                stepId: "step-create-task-01",
                order: 1,
                actorNodeId: "container-planning-workbench",
                targetNodeId: "component-task-command-service",
                action: "提交创建任务命令。",
                dataRefs: [],
                relationRefs: ["rel-workbench-call-command-service"],
              },
            ],
          },
        ],
        layerRoles: [
          {
            roleId: "role-application",
            roleType: "application_orchestration",
            title: "应用编排职责",
            description: "负责命令编排、事务边界和调用协调。",
            componentRefs: ["component-task-command-service"],
            functionRefs: ["fn-create-task"],
            designRefs: ["sdd-03"],
          },
        ],
        functionArchitectureMappings: [
          {
            mappingId: "map-fn-create-task-to-architecture",
            functionNodeId: "fn-create-task",
            architectureViewIds: ["view-c4-structure", "view-runtime-main"],
            containerIds: ["container-planning-workbench"],
            componentIds: ["component-task-command-service"],
            runtimeScenarioIds: ["scenario-create-task"],
            layerRoles: ["presentation", "application_orchestration"],
            role: "primary",
            mappingStatus: "confirmed",
            moduleRefs: ["module-planning"],
            sourceRefs: ["REQ-3.2"],
            designRefs: ["sdd-03"],
          },
        ],
        mappingQuality: {
          mappedFunctionCount: 1,
          unmappedFunctionCount: 0,
          pendingConfirmationCount: 0,
        },
        reviewFindings: [],
      },
    };

    const model = buildP3DesignMorphModel(workbench);
    const architectureStage = model.stages.find((stage) => stage.id === "layeredArchitecture");

    expect(architectureStage).toEqual(
      expect.objectContaining({
        title: "架构视图组",
        subtitle: "业务边界 / C4 / 运行链路",
        summary: "架构视图组：4 个视图；2 个架构节点；1 条功能-架构映射",
        items: ["业务边界", "系统结构", "运行链路", "职责层", "规划任务工作台", "规划任务命令服务"],
        sourceRefs: ["REQ-3.2", "sdd-03"],
        constraintSummary: "4 个架构视图；2 个节点；1 条关系；1 个运行场景",
        architectureViews: expect.objectContaining({
          viewGroupId: "architecture-views",
          tabs: expect.arrayContaining([expect.objectContaining({ title: "系统结构" })]),
          nodes: expect.arrayContaining([expect.objectContaining({ nodeId: "component-task-command-service" })]),
        }),
      }),
    );
    expect(architectureStage?.layeredArchitecture).toBeUndefined();
  });
});

function collectFunctionTreeTitles(node: FunctionTreeNode | null): string[] {
  if (!node) {
    return [];
  }
  return [node.title, ...node.children.flatMap((child) => collectFunctionTreeTitles(child))];
}

function collectSupportingNodeTitles(node: FunctionTreeNode | null): string[] {
  if (!node) {
    return [];
  }
  const supportingNodes = ((node as FunctionTreeNode & { supportingNodes?: SupportFunctionTreeNode[] }).supportingNodes ?? []);
  return supportingNodes.flatMap((supportNode) => [
    supportNode.title,
    ...collectNestedSupportingNodeTitles(supportNode.children ?? []),
  ]);
}

function collectNestedSupportingNodeTitles(nodes: SupportFunctionTreeNode[]): string[] {
  return nodes.flatMap((node) => [node.title, ...collectNestedSupportingNodeTitles(node.children ?? [])]);
}

type FunctionTreeNode = NonNullable<
  NonNullable<ReturnType<typeof buildP3DesignMorphModel>["stages"][number]["functionTree"]>["root"]
>;

type SupportFunctionTreeNode = {
  title: string;
  children?: SupportFunctionTreeNode[];
};

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
      running: false,
      elapsedSeconds: 0,
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
