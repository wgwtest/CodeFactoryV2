import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { ProcessViewPage } from "../pages/ProcessViewPage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args)
  }
}));

test("renders process list, filters results, and opens process chain details", async () => {
  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/processes")) {
      return Promise.resolve({
        data: [
          {
            id: "process-interoperability",
            name: "服务互操作流程",
            category: "domain_process",
            document_ids: ["doc-1"],
            evidence: [{ document_id: "doc-1", excerpt: "NAS 远期需求文档的服务互操作性过程流。" }]
          },
          {
            id: "process-roadmap",
            name: "服务演进路线图规划",
            category: "domain_process",
            document_ids: ["doc-2", "doc-3"],
            evidence: [{ document_id: "doc-2", excerpt: "该流程用于形成 NAS 服务演进路线图。" }]
          }
        ]
      });
    }

    if (url.endsWith("/items/process-roadmap")) {
      return Promise.resolve({
        data: {
          id: "process-roadmap",
          name: "服务演进路线图规划",
          item_type: "process",
          category: "domain_process",
          aliases: ["路线图规划流程"],
          review_status: "approved",
          document_count: 2,
          interpretation: {
            kind_label: "流程",
            family_code: null,
            family_label: null,
            display_name: "服务演进路线图规划",
            standard_name: null,
            summary: "用于识别能力缺口、规划迁移顺序并形成阶段性服务演进路线图。",
            producer_hint: "通常由架构规划活动结合能力缺口分析共同产出。"
          },
          documents: [
            {
              id: "doc-2",
              title: "NAS-EA-OV-2 As Is",
              file_type: "docx",
              source_archive: "20161116体系结构文献翻译汇总"
            }
          ],
          evidence: [
            {
              document_id: "doc-2",
              document_title: "NAS-EA-OV-2 As Is",
              excerpt: "该流程用于形成 NAS 服务演进路线图。"
            }
          ],
          related_items: [
            { id: "entity-nas", name: "国家空域体系", item_type: "entity", relation_type: "scoped_by" },
            { id: "event-gap", name: "能力缺口识别", item_type: "event", relation_type: "describes" }
          ],
          relationship_sections: [
            {
              key: "upstream_inputs",
              title: "流程输入与约束",
              items: [
                {
                  id: "entity-nas",
                  name: "国家空域体系",
                  item_type: "entity",
                  relation_type: "scoped_by",
                  relation_label: "阶段约束",
                  direction: "incoming",
                  evidence: "路线图规划受到国家空域体系阶段目标约束。"
                }
              ]
            },
            {
              key: "downstream_outputs",
              title: "流程产出与关联事件",
              items: [
                {
                  id: "event-gap",
                  name: "能力缺口识别",
                  item_type: "event",
                  relation_type: "describes",
                  relation_label: "触发",
                  direction: "outgoing",
                  evidence: "能力缺口识别结果进入路线图规划。"
                }
              ]
            }
          ]
        }
      });
    }

    if (url.endsWith("/items/process-roadmap/graph")) {
      return Promise.resolve({
        data: {
          focus_item_id: "process-roadmap",
          nodes: [
            { id: "process-roadmap", label: "服务演进路线图规划", item_type: "process", category: "domain_process", is_focus: true },
            { id: "entity-nas", label: "国家空域体系", item_type: "entity", category: "system_or_service", is_focus: false },
            { id: "event-gap", label: "能力缺口识别", item_type: "event", category: "timeline_event", is_focus: false }
          ],
          edges: [
            { source: "entity-nas", target: "process-roadmap", label: "process_scoped_by" },
            { source: "event-gap", target: "process-roadmap", label: "describes" }
          ]
        }
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <ProcessViewPage />
    </MemoryRouter>,
  );

  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();
  expect(await screen.findByText("服务演进路线图规划")).toBeInTheDocument();
  expect(await screen.findByText("1 份文档")).toBeInTheDocument();
  expect(await screen.findByText("2 份文档")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索流程名称或证据摘录"), { target: { value: "路线图" } });
  expect(await screen.findByDisplayValue("路线图")).toBeInTheDocument();
  expect(screen.queryByText("服务互操作流程")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "查看链路" }));

  expect(await screen.findByText("流程详情")).toBeInTheDocument();
  expect(await screen.findByText("这是什么")).toBeInTheDocument();
  expect(await screen.findByText("业务关系结构")).toBeInTheDocument();
  expect(await screen.findByText("流程输入与约束")).toBeInTheDocument();
  expect(await screen.findByText("流程产出与关联事件")).toBeInTheDocument();
  expect(await screen.findByText("关系邻域")).toBeInTheDocument();
  expect((await screen.findAllByText("NAS-EA-OV-2 As Is")).length).toBeGreaterThan(0);
  expect(
    (
      await screen.findAllByText("用于识别能力缺口、规划迁移顺序并形成阶段性服务演进路线图。")
    ).length,
  ).toBeGreaterThan(0);
  expect((await screen.findAllByText("路线图规划流程")).length).toBeGreaterThan(0);

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/process-roadmap/graph")
  );
});
