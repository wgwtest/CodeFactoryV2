import { describe, expect, test } from "vitest";

import type { P3DesignLabInputPackage, P3DesignLabSession } from "../lib/api";
import { buildP3DesignLabWorkbenchViewModel } from "../pages/adapters/p3DesignLabWorkbenchAdapter";

describe("P3 design lab workbench adapter", () => {
  test("normalizes layered architecture from converter design package", () => {
    const inputPackage = buildInputPackage();
    const session: P3DesignLabSession = {
      session_id: "p3dl-1",
      input_package: inputPackage,
      design_title: "空域协同规划软件设计说明",
      version_label: "v0.1",
      generation_policy: {},
      status: "draft_ready",
      conversion: null,
      design_document: {
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        sections: [{ section_id: "sdd-03", title: "3. 设计总览、模块划分与分层架构", content: "分层架构设计。", status: "generated" }],
      },
      design_baseline: {
        baseline_id: "sdb2-1",
        architecture_mode: "unified_service",
        modules: [{ module_id: "module-planning", name: "规划任务管理" }],
        design_package: {
          layered_architecture: {
            architecture_id: "layered-architecture",
            title: "分层架构设计",
            pattern: "business-module-oriented-layered-architecture",
            source_refs: ["REQ-3.2"],
            design_refs: ["sdd-03"],
            layers: [
              {
                layer_id: "presentation",
                name: "展示交互层",
                responsibility: "承载用户操作入口。",
                inputs: ["用户操作"],
                outputs: ["业务请求"],
                components: [
                  {
                    component_id: "cmp-planning-task-workbench",
                    name: "规划任务工作台",
                    component_type: "ui_workspace",
                    module_refs: ["module-planning"],
                    function_refs: ["fn-create-task"],
                  },
                ],
              },
            ],
            module_layer_mappings: [
              {
                mapping_id: "map-planning-task-presentation",
                module_id: "module-planning",
                module_name: "规划任务管理",
                layer_id: "presentation",
                layer_name: "展示交互层",
                component_refs: ["cmp-planning-task-workbench"],
                function_refs: ["fn-create-task"],
                source_refs: ["REQ-3.2"],
              },
            ],
            diagrams: [{ diagram_id: "D1", title: "分层架构与模块映射图", diagram_type: "mermaid", content: "flowchart TB" }],
          },
        },
      },
      workorder_projection: null,
      turns: [],
      runtime_events: [],
    };

    const workbench = buildP3DesignLabWorkbenchViewModel({ inputPackage, session, policy: {} });

    expect(workbench.outline.baseline?.layeredArchitecture).toEqual(
      expect.objectContaining({
        architectureId: "layered-architecture",
        title: "分层架构设计",
        sourceRefs: ["REQ-3.2"],
        designRefs: ["sdd-03"],
        layers: [
          expect.objectContaining({
            layerId: "presentation",
            name: "展示交互层",
            components: [
              expect.objectContaining({
                componentId: "cmp-planning-task-workbench",
                name: "规划任务工作台",
                moduleRefs: ["module-planning"],
                functionRefs: ["fn-create-task"],
              }),
            ],
          }),
        ],
        moduleLayerMappings: [
          expect.objectContaining({
            mappingId: "map-planning-task-presentation",
            moduleName: "规划任务管理",
            layerName: "展示交互层",
          }),
        ],
        diagrams: [expect.objectContaining({ diagramId: "D1", title: "分层架构与模块映射图" })],
      }),
    );
  });

  test("normalizes C4 architecture view group from converter design package", () => {
    const inputPackage = buildInputPackage();
    const session: P3DesignLabSession = {
      session_id: "p3dl-1",
      input_package: inputPackage,
      design_title: "空域协同规划软件设计说明",
      version_label: "v0.1",
      generation_policy: {},
      status: "draft_ready",
      conversion: null,
      design_document: {
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        sections: [{ section_id: "sdd-03", title: "3. 架构视图组", content: "C4 架构视图组。", status: "generated" }],
      },
      design_baseline: {
        baseline_id: "sdb2-1",
        architecture_mode: "c4_architecture_views",
        modules: [{ module_id: "module-planning", name: "规划任务管理" }],
        design_package: {
          architecture_views: {
            view_group_id: "architecture-views",
            title: "架构视图组",
            default_view_id: "view-c4-structure",
            tabs: [
              { view_id: "view-business-boundary", title: "业务边界", view_type: "business_boundary", order: 1 },
              { view_id: "view-c4-structure", title: "系统结构", view_type: "c4_component", order: 2 },
              { view_id: "view-runtime-main", title: "运行链路", view_type: "runtime_scenario", order: 3 },
              { view_id: "view-layer-roles", title: "职责层", view_type: "layer_roles", order: 4 },
            ],
            views: [
              {
                view_id: "view-c4-structure",
                view_type: "c4_component",
                title: "系统结构",
                description: "展示系统容器、核心组件、数据存储和外部系统之间的结构关系。",
                node_refs: ["container-planning-workbench", "component-task-command-service"],
                relation_refs: ["rel-workbench-call-command-service"],
                source_refs: ["REQ-3.2"],
                design_refs: ["sdd-03"],
              },
            ],
            c4_containers: [
              {
                node_id: "container-planning-workbench",
                node_type: "container",
                title: "规划任务工作台",
                description: "承载规划任务的用户操作入口。",
                layer_roles: ["presentation"],
                function_refs: ["fn-create-task"],
                source_refs: ["REQ-3.2"],
                design_refs: ["sdd-03"],
              },
            ],
            c4_components: [
              {
                node_id: "component-task-command-service",
                node_type: "component",
                title: "规划任务命令服务",
                description: "接收创建规划任务命令并编排领域规则。",
                container_id: "container-planning-service",
                component_id: "component-task-command-service",
                layer_roles: ["application_orchestration"],
                function_refs: ["fn-create-task"],
                source_refs: ["REQ-3.2"],
                design_refs: ["sdd-03"],
              },
            ],
            architecture_relations: [
              {
                relation_id: "rel-workbench-call-command-service",
                from_node_id: "container-planning-workbench",
                to_node_id: "component-task-command-service",
                relation_type: "calls",
                title: "提交创建任务命令",
                function_refs: ["fn-create-task"],
                source_refs: ["REQ-3.2"],
                design_refs: ["sdd-03"],
              },
            ],
            runtime_scenarios: [
              {
                scenario_id: "scenario-create-task",
                title: "创建规划任务运行链路",
                trigger: "用户提交创建规划任务。",
                function_refs: ["fn-create-task"],
                steps: [
                  {
                    step_id: "step-create-task-01",
                    order: 1,
                    actor_node_id: "container-planning-workbench",
                    target_node_id: "component-task-command-service",
                    action: "提交创建任务命令。",
                    relation_refs: ["rel-workbench-call-command-service"],
                  },
                ],
              },
            ],
            layer_roles: [
              {
                role_id: "role-application",
                role_type: "application_orchestration",
                title: "应用编排职责",
                description: "负责命令编排、事务边界和调用协调。",
                component_refs: ["component-task-command-service"],
                function_refs: ["fn-create-task"],
              },
            ],
            function_architecture_mappings: [
              {
                mapping_id: "map-fn-create-task-to-architecture",
                function_node_id: "fn-create-task",
                architecture_view_ids: ["view-c4-structure", "view-runtime-main"],
                container_ids: ["container-planning-workbench"],
                component_ids: ["component-task-command-service"],
                runtime_scenario_ids: ["scenario-create-task"],
                layer_roles: ["presentation", "application_orchestration"],
                role: "primary",
                mapping_status: "confirmed",
                source_refs: ["REQ-3.2"],
                design_refs: ["sdd-03"],
              },
            ],
            mapping_quality: {
              mapped_function_count: 1,
              unmapped_function_count: 0,
              pending_confirmation_count: 0,
            },
          },
        },
      },
      workorder_projection: null,
      turns: [],
      runtime_events: [],
    };

    const workbench = buildP3DesignLabWorkbenchViewModel({ inputPackage, session, policy: {} });
    const architectureViews = (workbench.outline.baseline as Record<string, unknown> | undefined)?.architectureViews;

    expect(architectureViews).toEqual(
      expect.objectContaining({
        viewGroupId: "architecture-views",
        title: "架构视图组",
        defaultViewId: "view-c4-structure",
        tabs: [
          expect.objectContaining({ viewId: "view-business-boundary", title: "业务边界", viewType: "business_boundary" }),
          expect.objectContaining({ viewId: "view-c4-structure", title: "系统结构", viewType: "c4_component" }),
          expect.objectContaining({ viewId: "view-runtime-main", title: "运行链路", viewType: "runtime_scenario" }),
          expect.objectContaining({ viewId: "view-layer-roles", title: "职责层", viewType: "layer_roles" }),
        ],
        nodes: expect.arrayContaining([
          expect.objectContaining({
            nodeId: "container-planning-workbench",
            nodeType: "container",
            title: "规划任务工作台",
            functionRefs: ["fn-create-task"],
          }),
          expect.objectContaining({
            nodeId: "component-task-command-service",
            nodeType: "component",
            title: "规划任务命令服务",
            layerRoles: ["application_orchestration"],
          }),
        ]),
        architectureRelations: [
          expect.objectContaining({
            relationId: "rel-workbench-call-command-service",
            fromNodeId: "container-planning-workbench",
            toNodeId: "component-task-command-service",
            relationType: "calls",
          }),
        ],
        runtimeScenarios: [
          expect.objectContaining({
            scenarioId: "scenario-create-task",
            steps: [expect.objectContaining({ stepId: "step-create-task-01", order: 1 })],
          }),
        ],
        functionArchitectureMappings: [
          expect.objectContaining({
            mappingId: "map-fn-create-task-to-architecture",
            functionNodeId: "fn-create-task",
            componentIds: ["component-task-command-service"],
          }),
        ],
      }),
    );
  });
});

function buildInputPackage(): P3DesignLabInputPackage {
  return {
    input_package_id: "pkg-1",
    source_document_id: "req-1",
    source_title: "P2 冻结包",
    p3_consumable: true,
    standard_document: {
      title: "空域协同规划软件需求规格说明",
      sections: [
        {
          section_id: "req-section-1",
          title: "功能需求",
          clauses: [{ clause_id: "REQ-3.2", title: "规划任务", content: "支持规划任务管理。", status: "approved" }],
        },
      ],
    },
    structured_spec: {},
    annotations: [],
  };
}
