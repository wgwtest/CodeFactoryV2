import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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

  expect(await screen.findByText("实体列表")).toBeInTheDocument();
  expect(await screen.findByText("国家空域系统")).toBeInTheDocument();
  expect(await screen.findByText("OV-1")).toBeInTheDocument();
  expect(await screen.findByText("高层运行概念图")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索实体名称或别名"), { target: { value: "OV-1" } });
  expect(await screen.findByDisplayValue("OV-1")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "查看详情" }));

  expect(await screen.findByText("实体详情")).toBeInTheDocument();
  expect(await screen.findByText("这是什么")).toBeInTheDocument();
  expect(
    (
      await screen.findAllByText("OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。")
    ).length,
  ).toBeGreaterThan(0);
  expect(await screen.findByText("High-Level Operational Concept Graphic")).toBeInTheDocument();
  expect((await screen.findAllByText("远期顶层运行概念图")).length).toBeGreaterThan(0);
  expect(await screen.findByText("NAS AV-1")).toBeInTheDocument();
  expect(await screen.findByText("国家空域系统")).toBeInTheDocument();
});
