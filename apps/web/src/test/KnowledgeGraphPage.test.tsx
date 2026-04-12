import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { KnowledgeGraphPage } from "../pages/KnowledgeGraphPage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args)
  }
}));

test("renders entity list and opens entity details", async () => {
  getMock.mockImplementation((url: string) => {
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
              process_count: 6
            }
          },
          versions: [
            {
              version_label: "v1",
              publisher: "architect",
              published_at: "2026-04-12T00:00:00Z",
              summary: {
                document_count: 65,
                entity_count: 586,
                event_count: 4,
                process_count: 6
              }
            }
          ],
          working_summary: {
            document_count: 65,
            entity_count: 586,
            event_count: 4,
            process_count: 6
          }
        }
      });
    }

    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 65,
          entity_count: 586,
          event_count: 4,
          process_count: 6
        }
      });
    }

    if (url.endsWith("/graph")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          nodes: [
            { id: "entity-nas", label: "国家空域系统", type: "system_or_service", document_count: 11 },
            { id: "entity-ov1", label: "OV-1", type: "architecture_artifact", document_count: 10 }
          ],
          edges: [{ source: "entity-nas", target: "entity-ov1", label: "supports" }],
          summary: {
            document_count: 65,
            entity_count: 586,
            event_count: 4,
            process_count: 6
          }
        }
      });
    }

    if (url.endsWith("/entities")) {
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
              producer_hint: null
            }
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
              producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。"
            }
          }
        ]
      });
    }

    if (url.endsWith("/items/entity-ov1")) {
      return Promise.resolve({
        data: {
          id: "entity-ov1",
          name: "OV-1",
          item_type: "entity",
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
            producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。"
          },
          documents: [
            {
              id: "doc-1",
              title: "NAS AV-1",
              file_type: "pdf",
              source_archive: "20161116体系结构文献翻译汇总"
            }
          ],
          evidence: [{ document_id: "doc-1", excerpt: "OV-1" }],
          related_items: [
            { id: "entity-nas", name: "国家空域系统", item_type: "entity", relation_type: "supports" }
          ],
          relationship_sections: [
            {
              key: "outgoing_describes",
              title: "它描述的对象",
              items: [
                {
                  id: "entity-nas",
                  name: "国家空域系统",
                  item_type: "entity",
                  relation_type: "describes",
                  relation_label: "描述",
                  direction: "outgoing",
                  evidence: "OV-1 描述国家空域系统高层运行概念。"
                }
              ]
            }
          ]
        }
      });
    }

    if (url.endsWith("/items/entity-ov1/graph")) {
      return Promise.resolve({
        data: {
          focus_item_id: "entity-ov1",
          nodes: [
            { id: "entity-ov1", label: "OV-1", item_type: "entity", category: "architecture_artifact", is_focus: true },
            { id: "entity-nas", label: "国家空域系统", item_type: "entity", category: "system_or_service", is_focus: false },
            { id: "process-service-interoperability", label: "服务互操作流程", item_type: "process", category: "domain_process", is_focus: false }
          ],
          edges: [
            { source: "entity-nas", target: "entity-ov1", label: "supports" },
            { source: "entity-ov1", target: "process-service-interoperability", label: "supports" }
          ]
        }
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <KnowledgeGraphPage />
    </MemoryRouter>,
  );

  expect(await screen.findByText("档案知识总览")).toBeInTheDocument();
  expect(await screen.findByText("版本：v1")).toBeInTheDocument();
  expect(await screen.findByText("节点：2")).toBeInTheDocument();
  expect(await screen.findByText("关系：1")).toBeInTheDocument();
  expect(await screen.findByRole("radio", { name: "列表视图" })).toBeChecked();
  expect(await screen.findByRole("radio", { name: "图谱视图" })).toBeInTheDocument();
  expect(screen.getAllByText(/^文档$/)).toHaveLength(1);
  expect(screen.getAllByText(/^实体$/)).toHaveLength(1);
  expect(screen.getAllByText(/^事件$/)).toHaveLength(1);
  expect(screen.getAllByText(/^流程$/)).toHaveLength(1);
  expect(await screen.findByText("实体列表")).toBeInTheDocument();
  expect(await screen.findByText("国家空域系统")).toBeInTheDocument();
  expect(await screen.findByText("OV-1")).toBeInTheDocument();
  expect(await screen.findByText("高层运行概念图")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索实体名称或别名"), { target: { value: "OV-1" } });
  expect(await screen.findByDisplayValue("OV-1")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("radio", { name: "图谱视图" }));
  expect(await screen.findByText("全局拓扑图")).toBeInTheDocument();
  expect(await screen.findByText("命中节点：2")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("radio", { name: "列表视图" }));
  expect(await screen.findByText("实体列表")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "查看详情" }));

  expect(await screen.findByText("实体详情")).toBeInTheDocument();
  expect(await screen.findByText("这是什么")).toBeInTheDocument();
  expect(await screen.findByText("业务关系结构")).toBeInTheDocument();
  expect(await screen.findByText("它描述的对象")).toBeInTheDocument();
  expect(await screen.findByText("关系邻域")).toBeInTheDocument();
  expect(
    (
      await screen.findAllByText("OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。")
    ).length,
  ).toBeGreaterThan(0);
  expect(await screen.findByText("High-Level Operational Concept Graphic")).toBeInTheDocument();
  expect((await screen.findAllByText("远期顶层运行概念图")).length).toBeGreaterThan(0);
  expect(await screen.findByText("NAS AV-1")).toBeInTheDocument();
  expect((await screen.findAllByText("国家空域系统")).length).toBeGreaterThan(0);
  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/entity-ov1/graph")
  );
});
