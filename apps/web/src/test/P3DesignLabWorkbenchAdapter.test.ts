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
