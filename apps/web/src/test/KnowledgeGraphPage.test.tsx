import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { KnowledgeGraphPage } from "../pages/KnowledgeGraphPage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

test("renders unified knowledge browser, filters by type, and reuses the common detail drawer", async () => {
  getMock.mockImplementation((url: string, config?: { params?: { document_ids?: string } }) => {
    const sourceFilter = config?.params?.document_ids ?? null;

    if (url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116体系结构文献翻译汇总",
            character_count: 2200,
            entity_count: 3,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 5,
          },
          {
            id: "doc-2",
            title: "NAS Roadmap",
            file_type: "docx",
            source_archive: "20161116体系结构文献翻译汇总",
            character_count: 1800,
            entity_count: 2,
            event_count: 1,
            process_count: 0,
            knowledge_item_count: 3,
          },
        ],
      });
    }

    if (url.endsWith("/publication")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          current_version: {
            version_label: "v1",
            publisher: "architect",
            published_at: "2026-04-12T00:00:00Z",
            summary: {
              document_count: 65,
              entity_count: 586,
              event_count: 4,
              process_count: 6,
            },
          },
          versions: [],
          working_summary: {
            document_count: 65,
            entity_count: 586,
            event_count: 4,
            process_count: 6,
          },
        },
      });
    }

    if (url.endsWith("/summary")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: {
            archive_id: "20161116-nas",
            document_count: 1,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
          },
        });
      }

      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 65,
          entity_count: 587,
          event_count: 4,
          process_count: 6,
        },
      });
    }

    if (url.endsWith("/graph")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: {
            archive_id: "20161116-nas",
            nodes: [
              {
                id: "entity-nas",
                label: "国家空域系统",
                type: "system_or_service",
                item_type: "entity",
                document_count: 1,
              },
              {
                id: "entity-ov1",
                label: "OV-1",
                type: "architecture_artifact",
                item_type: "entity",
                document_count: 1,
              },
              {
                id: "event-far-term",
                label: "远期目标（Far Term）",
                type: "timeline_event",
                item_type: "event",
                document_count: 1,
              },
              {
                id: "process-service-interoperability",
                label: "服务互操作流程",
                type: "domain_process",
                item_type: "process",
                document_count: 1,
              },
            ],
            edges: [
              { source: "entity-ov1", target: "entity-nas", label: "describes" },
              { source: "entity-ov1", target: "process-service-interoperability", label: "supports" },
              { source: "process-service-interoperability", target: "event-far-term", label: "process_scoped_by" },
            ],
            summary: {
              document_count: 1,
              entity_count: 2,
              event_count: 1,
              process_count: 1,
            },
          },
        });
      }

      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          nodes: [
            {
              id: "entity-nas",
              label: "国家空域系统",
              type: "system_or_service",
              item_type: "entity",
              document_count: 11,
            },
            {
              id: "entity-ov1",
              label: "OV-1",
              type: "architecture_artifact",
              item_type: "entity",
              document_count: 10,
            },
            {
              id: "entity-ov1-duplicate",
              label: "OV-1 运行概念图",
              type: "architecture_artifact",
              item_type: "entity",
              document_count: 3,
            },
            {
              id: "event-far-term",
              label: "远期目标（Far Term）",
              type: "timeline_event",
              item_type: "event",
              document_count: 6,
            },
            {
              id: "process-service-interoperability",
              label: "服务互操作流程",
              type: "domain_process",
              item_type: "process",
              document_count: 5,
            },
          ],
          edges: [
            { source: "entity-ov1", target: "entity-nas", label: "describes" },
            { source: "process-service-interoperability", target: "event-far-term", label: "process_scoped_by" },
            { source: "entity-ov1-duplicate", target: "process-service-interoperability", label: "supports" },
          ],
          summary: {
            document_count: 65,
            entity_count: 587,
            event_count: 4,
            process_count: 6,
          },
        },
      });
    }

    if (url.endsWith("/entities")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: [
            {
              id: "entity-nas",
              name: "国家空域系统",
              category: "system_or_service",
              aliases: ["NAS"],
              document_count: 1,
              interpretation: {
                kind_label: "系统/服务",
                family_code: null,
                family_label: null,
                display_name: null,
                standard_name: null,
                summary: "国家空域系统 是系统/服务类实体。",
                producer_hint: null,
              },
            },
            {
              id: "entity-ov1",
              name: "OV-1",
              category: "architecture_artifact",
              aliases: ["远期顶层运行概念图"],
              document_count: 1,
              interpretation: {
                kind_label: "架构工件",
                family_code: "OV",
                family_label: "运行视图",
                display_name: "高层运行概念图",
                standard_name: "High-Level Operational Concept Graphic",
                summary: "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
                producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
              },
            },
          ],
        });
      }

      return Promise.resolve({
        data: [
          {
            id: "entity-nas",
            name: "国家空域系统",
            category: "system_or_service",
            aliases: ["NAS"],
            document_count: 11,
            interpretation: {
              kind_label: "系统/服务",
              family_code: null,
              family_label: null,
              display_name: null,
              standard_name: null,
              summary: "国家空域系统 是系统/服务类实体。",
              producer_hint: null,
            },
          },
          {
            id: "entity-ov1",
            name: "OV-1",
            category: "architecture_artifact",
            aliases: ["远期顶层运行概念图"],
            document_count: 10,
            interpretation: {
              kind_label: "架构工件",
              family_code: "OV",
              family_label: "运行视图",
              display_name: "高层运行概念图",
              standard_name: "High-Level Operational Concept Graphic",
              summary: "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
              producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
            },
          },
          {
            id: "entity-ov1-duplicate",
            name: "OV-1 运行概念图",
            category: "architecture_artifact",
            aliases: ["运行概念图"],
            document_count: 3,
            interpretation: {
              kind_label: "架构工件",
              family_code: "OV",
              family_label: "运行视图",
              display_name: null,
              standard_name: null,
              summary: "OV-1 运行概念图 是架构工件，用于描述业务运行概念、活动和信息交换需求。",
              producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
            },
          },
        ],
      });
    }

    if (url.endsWith("/events")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: [
            {
              id: "event-far-term",
              item_type: "event",
              name: "远期目标（Far Term）",
              category: "timeline_event",
              aliases: ["Far Term"],
              document_count: 1,
              interpretation: {
                kind_label: "时间事件",
                family_code: null,
                family_label: null,
                display_name: "远期目标",
                standard_name: null,
                summary: "用于界定远期阶段目标和演进边界。",
                producer_hint: "通常由规划或路线图类架构活动定义。",
              },
              document_ids: ["doc-1"],
              evidence: [{ document_id: "doc-1", excerpt: "Far Term excerpt" }],
            },
          ],
        });
      }

      return Promise.resolve({
        data: [
          {
            id: "event-far-term",
            item_type: "event",
            name: "远期目标（Far Term）",
            category: "timeline_event",
            aliases: ["Far Term"],
            document_count: 6,
            interpretation: {
              kind_label: "时间事件",
              family_code: null,
              family_label: null,
              display_name: "远期目标",
              standard_name: null,
              summary: "用于界定远期阶段目标和演进边界。",
              producer_hint: "通常由规划或路线图类架构活动定义。",
            },
            document_ids: ["doc-1"],
            evidence: [{ document_id: "doc-1", excerpt: "Far Term excerpt" }],
          },
        ],
      });
    }

    if (url.endsWith("/processes")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: [
            {
              id: "process-service-interoperability",
              item_type: "process",
              name: "服务互操作流程",
              category: "domain_process",
              aliases: ["互操作流程"],
              document_count: 1,
              interpretation: {
                kind_label: "流程",
                family_code: null,
                family_label: null,
                display_name: "服务互操作流程",
                standard_name: null,
                summary: "用于串接服务协同、接口对齐与阶段发布的领域流程。",
                producer_hint: "通常由业务流程分析与架构设计共同形成。",
              },
              document_ids: ["doc-1"],
              evidence: [{ document_id: "doc-1", excerpt: "Service interoperability excerpt" }],
            },
          ],
        });
      }

      return Promise.resolve({
        data: [
          {
            id: "process-service-interoperability",
            item_type: "process",
            name: "服务互操作流程",
            category: "domain_process",
            aliases: ["互操作流程"],
            document_count: 5,
            interpretation: {
              kind_label: "流程",
              family_code: null,
              family_label: null,
              display_name: "服务互操作流程",
              standard_name: null,
              summary: "用于串接服务协同、接口对齐与阶段发布的领域流程。",
              producer_hint: "通常由业务流程分析与架构设计共同形成。",
            },
            document_ids: ["doc-2"],
            evidence: [{ document_id: "doc-2", excerpt: "Service interoperability excerpt" }],
          },
        ],
      });
    }

    if (url.endsWith("/items/process-service-interoperability")) {
      return Promise.resolve({
        data: {
          id: "process-service-interoperability",
          name: "服务互操作流程",
          item_type: "process",
          category: "domain_process",
          aliases: ["互操作流程"],
          review_status: "approved",
          document_count: 5,
          interpretation: {
            kind_label: "流程",
            family_code: null,
            family_label: null,
            display_name: "服务互操作流程",
            standard_name: null,
            summary: "用于串接服务协同、接口对齐与阶段发布的领域流程。",
            producer_hint: "通常由业务流程分析与架构设计共同形成。",
          },
          documents: [
            {
              id: "doc-2",
              title: "NAS Roadmap",
              file_type: "docx",
              source_archive: "20161116体系结构文献翻译汇总",
            },
          ],
          evidence: [{ document_id: "doc-2", document_title: "NAS Roadmap", excerpt: "Service interoperability excerpt" }],
          related_items: [
            { id: "event-far-term", name: "远期目标（Far Term）", item_type: "event", relation_type: "process_scoped_by" },
          ],
          relationship_sections: [
            {
              key: "outgoing_scoped_by",
              title: "相关阶段/约束",
              items: [
                {
                  id: "event-far-term",
                  name: "远期目标（Far Term）",
                  item_type: "event",
                  relation_type: "process_scoped_by",
                  relation_label: "受约束于",
                  direction: "outgoing",
                  evidence: "服务互操作流程受远期目标约束。",
                },
              ],
            },
          ],
        },
      });
    }

    if (url.endsWith("/items/entity-ov1")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: {
            id: "entity-ov1",
            name: "OV-1",
            item_type: "entity",
            category: "architecture_artifact",
            aliases: ["远期顶层运行概念图"],
            review_status: "approved",
            document_count: 1,
            interpretation: {
              kind_label: "架构工件",
              family_code: "OV",
              family_label: "运行视图",
              display_name: "高层运行概念图",
              standard_name: "High-Level Operational Concept Graphic",
              summary: "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
              producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
            },
            documents: [
              {
                id: "doc-1",
                title: "NAS AV-1",
                file_type: "pdf",
                source_archive: "20161116体系结构文献翻译汇总",
              },
            ],
            evidence: [{ document_id: "doc-1", document_title: "NAS AV-1", excerpt: "OV-1 excerpt" }],
            related_items: [
              { id: "entity-nas", name: "国家空域系统", item_type: "entity", relation_type: "describes" },
              {
                id: "process-service-interoperability",
                name: "服务互操作流程",
                item_type: "process",
                relation_type: "supports",
              },
            ],
            relationship_sections: [
              {
                key: "other",
                title: "其他直接关联",
                items: [
                  {
                    id: "entity-nas",
                    name: "国家空域系统",
                    item_type: "entity",
                    relation_type: "describes",
                    relation_label: "describes",
                    direction: "outgoing",
                    evidence: "OV-1 描述国家空域系统。",
                  },
                ],
              },
            ],
          },
        });
      }
    }

    if (url.endsWith("/items/process-service-interoperability/graph")) {
      return Promise.resolve({
        data: {
          focus_item_id: "process-service-interoperability",
          nodes: [
            {
              id: "process-service-interoperability",
              label: "服务互操作流程",
              item_type: "process",
              category: "domain_process",
              is_focus: true,
            },
            {
              id: "event-far-term",
              label: "远期目标（Far Term）",
              item_type: "event",
              category: "timeline_event",
              is_focus: false,
            },
          ],
          edges: [{ source: "process-service-interoperability", target: "event-far-term", label: "process_scoped_by" }],
        },
      });
    }

    if (url.endsWith("/items/entity-ov1/graph")) {
      if (sourceFilter === "doc-1") {
        return Promise.resolve({
          data: {
            focus_item_id: "entity-ov1",
            nodes: [
              {
                id: "entity-ov1",
                label: "OV-1",
                item_type: "entity",
                category: "architecture_artifact",
                is_focus: true,
              },
              {
                id: "entity-nas",
                label: "国家空域系统",
                item_type: "entity",
                category: "system_or_service",
                is_focus: false,
              },
              {
                id: "process-service-interoperability",
                label: "服务互操作流程",
                item_type: "process",
                category: "domain_process",
                is_focus: false,
              },
            ],
            edges: [
              { source: "entity-ov1", target: "entity-nas", label: "describes" },
              { source: "entity-ov1", target: "process-service-interoperability", label: "supports" },
            ],
          },
        });
      }
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <KnowledgeGraphPage />
    </MemoryRouter>,
  );

  expect(await screen.findByTestId("workspace-overview-strip")).toBeInTheDocument();
  expect(await screen.findByText("档案知识总览")).toBeInTheDocument();
  expect(await screen.findByText("版本：v1")).toBeInTheDocument();
  expect(await screen.findByText("节点：5")).toBeInTheDocument();
  expect(await screen.findByText("关系：3")).toBeInTheDocument();

  expect(await screen.findByRole("checkbox", { name: "实体" })).toBeChecked();
  expect(await screen.findByRole("checkbox", { name: "事件" })).toBeChecked();
  expect(await screen.findByRole("checkbox", { name: "流程" })).toBeChecked();
  expect(await screen.findByRole("radio", { name: "列表视图" })).toBeChecked();
  expect(await screen.findByRole("radio", { name: "图谱视图" })).toBeInTheDocument();
  expect(await screen.findByTestId("knowledge-source-documents-select")).toBeInTheDocument();

  expect(await screen.findByText("知识列表")).toBeInTheDocument();
  expect(await screen.findByText("国家空域系统")).toBeInTheDocument();
  expect(await screen.findByText("远期目标（Far Term）")).toBeInTheDocument();
  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();
  expect(await screen.findByText("OV-1 运行概念图")).toBeInTheDocument();

  const sourceDocumentSelect = screen.getByTestId("knowledge-source-documents-select");
  const sourceDocumentSelector = sourceDocumentSelect.querySelector(".ant-select-selector");
  if (!sourceDocumentSelector) {
    throw new Error("来源文档选择器未渲染");
  }

  fireEvent.mouseDown(sourceDocumentSelector);
  expect(await screen.findByRole("button", { name: "全选" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "清空" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "全选" }));
  expect(await screen.findByText("当前来源：已选 2 / 2 份")).toBeInTheDocument();
  expect(sourceDocumentSelect).toHaveTextContent("已选 2 / 2 份");

  fireEvent.click(screen.getByRole("button", { name: "清空" }));
  expect(await screen.findByText("当前来源：全部 2 份")).toBeInTheDocument();
  expect(sourceDocumentSelect).toHaveTextContent("全部素材文档");

  fireEvent.mouseDown(sourceDocumentSelector);
  fireEvent.click(await screen.findByText("NAS AV-1"));

  expect(await screen.findByText("当前来源：已选 1 / 2 份")).toBeInTheDocument();
  expect(sourceDocumentSelect).toHaveTextContent("已选 1 份：NAS AV-1");
  expect(sourceDocumentSelect.querySelector(".ant-select-clear")).toBeNull();
  await waitFor(() => expect(screen.queryByText("OV-1 运行概念图")).not.toBeInTheDocument());

  fireEvent.mouseDown(sourceDocumentSelector);
  expect(screen.getByText("当前来源：已选 1 / 2 份")).toBeInTheDocument();
  expect(sourceDocumentSelect).toHaveTextContent("已选 1 份：NAS AV-1");

  fireEvent.click(screen.getByRole("checkbox", { name: "实体" }));
  expect(screen.getByRole("checkbox", { name: "实体" })).not.toBeChecked();
  await waitFor(() => expect(screen.queryByText("国家空域系统")).not.toBeInTheDocument());
  expect(await screen.findByText("远期目标（Far Term）")).toBeInTheDocument();
  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索名称、别名或释义"), { target: { value: "互操作" } });
  expect(await screen.findByDisplayValue("互操作")).toBeInTheDocument();
  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();
  expect(screen.queryByText("远期目标（Far Term）")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("checkbox", { name: "实体" }));
  fireEvent.change(screen.getByPlaceholderText("搜索名称、别名或释义"), { target: { value: "" } });

  fireEvent.click((await screen.findAllByRole("button", { name: "查看详情" }))[1]);

  expect(await screen.findByText("知识详情")).toBeInTheDocument();
  expect(await screen.findByText("这是什么")).toBeInTheDocument();
  expect(await screen.findByText("业务关系结构")).toBeInTheDocument();
  expect(await screen.findByText("关系邻域")).toBeInTheDocument();
  expect((await screen.findAllByText("NAS AV-1")).length).toBeGreaterThan(0);
  expect(screen.queryByText("Roadmap OV-1 excerpt")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("radio", { name: "图谱视图" }));
  expect(await screen.findByText("全局拓扑图")).toBeInTheDocument();
  expect(await screen.findByText("已展示关联节点：4")).toBeInTheDocument();

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/entity-ov1/graph", {
      params: { document_ids: "doc-1" },
    }),
  );

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/graph", {
      params: { document_ids: "doc-1" },
    }),
  );
});
