import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { GovernancePage } from "../pages/GovernancePage";

const getMock = vi.fn();
const patchMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
    post: (...args: unknown[]) => postMock(...args)
  }
}));

test("renders knowledge review workspace, supports filtering, editing, batch approval, and merge", async () => {
  getMock.mockImplementation((url: string) => {
    if (url.includes("/review-candidates")) {
      return Promise.resolve({
        data: [
          {
            id: "entity-ov1",
            item_type: "entity",
            canonical_name: "OV-1",
            category: "architecture_artifact",
            document_count: 2,
            confidence: 0.85,
            review_status: "pending",
            evidence_excerpt: "OV-1",
            evidence_document_title: "NAS AV-1"
          },
          {
            id: "entity-ov1-duplicate",
            item_type: "entity",
            canonical_name: "OV-1 运行概念图",
            category: "architecture_artifact",
            document_count: 1,
            confidence: 0.8,
            review_status: "pending",
            evidence_excerpt: "Duplicate OV-1",
            evidence_document_title: "NAS Roadmap"
          },
          {
            id: "event-far-term",
            item_type: "event",
            canonical_name: "远期目标（Far Term）",
            category: "timeline_event",
            document_count: 2,
            confidence: 0.75,
            review_status: "approved",
            evidence_excerpt: "Far Term",
            evidence_document_title: "NAS AV-1"
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
          review_status: "pending",
          document_count: 2,
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
          evidence: [
            {
              document_id: "doc-1",
              document_title: "NAS AV-1",
              excerpt: "OV-1 excerpt"
            }
          ],
          related_items: [
            {
              id: "process-service-interoperability",
              name: "服务互操作流程",
              item_type: "process",
              relation_type: "supports"
            }
          ]
        }
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  patchMock.mockResolvedValue({
    data: {
      id: "entity-ov1",
      name: "OV-1 修正版",
      item_type: "entity",
      category: "architecture_concept",
      aliases: ["运行概念图", "OV-1"],
      review_status: "pending",
      document_count: 2,
      interpretation: {
        kind_label: "架构概念",
        family_code: null,
        family_label: null,
        display_name: null,
        standard_name: null,
        summary: "OV-1 修正版 是架构概念类实体。",
        producer_hint: null
      },
      documents: [],
      evidence: [],
      related_items: []
    }
  });

  postMock.mockImplementation((url: string) => {
    if (url.endsWith("/reviews/batch-approve")) {
      return Promise.resolve({ data: { updated_count: 1 } });
    }
    if (url.endsWith("/items/entity-ov1/review")) {
      return Promise.resolve({
        data: {
          id: "entity-ov1",
          review_status: "approved"
        }
      });
    }
    if (url.endsWith("/items/merge")) {
      return Promise.resolve({
        data: {
          id: "entity-ov1",
          name: "OV-1 修正版",
          item_type: "entity",
          category: "architecture_concept",
          aliases: ["运行概念图", "OV-1", "OV-1 运行概念图"],
          review_status: "approved",
          document_count: 2,
          interpretation: {
            kind_label: "架构概念",
            family_code: null,
            family_label: null,
            display_name: null,
            standard_name: null,
            summary: "OV-1 修正版 是架构概念类实体。",
            producer_hint: null
          },
          documents: [],
          evidence: [],
          related_items: []
        }
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(<GovernancePage />);

  expect(await screen.findByText("知识审核发布")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("搜索名称或别名")).toBeInTheDocument();
  expect(await screen.findByText("OV-1")).toBeInTheDocument();
  expect(screen.queryByText("远期目标（Far Term）")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("radio", { name: "全部" }));
  expect(await screen.findByText("远期目标（Far Term）")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索名称或别名"), { target: { value: "OV-1" } });
  expect(await screen.findByDisplayValue("OV-1")).toBeInTheDocument();

  fireEvent.click(screen.getAllByRole("button", { name: "查看 / 编辑" })[0]);

  expect(await screen.findByText("应用修改")).toBeInTheDocument();
  expect(await screen.findByText("证据摘录")).toBeInTheDocument();
  expect(await screen.findByText("OV-1 excerpt")).toBeInTheDocument();
  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("知识名称"), { target: { value: "OV-1 修正版" } });
  fireEvent.change(screen.getByPlaceholderText("别名，按回车确认"), { target: { value: "运行概念图,OV-1" } });
  fireEvent.click(screen.getByRole("button", { name: "应用修改" }));

  await waitFor(() =>
    expect(patchMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/entity-ov1", {
      name: "OV-1 修正版",
      category: "architecture_artifact",
      aliases: ["运行概念图", "OV-1"]
    })
  );

  fireEvent.click(screen.getAllByRole("button", { name: "直接通过" })[0]);
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/entity-ov1/review", {
      review_status: "approved"
    })
  );

  const checkboxes = await screen.findAllByRole("checkbox");
  fireEvent.click(checkboxes[1]);
  fireEvent.click(screen.getByRole("button", { name: "批量通过" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/reviews/batch-approve", {
      item_ids: ["entity-ov1"]
    })
  );

  fireEvent.click(screen.getByRole("button", { name: "合并到当前项" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/items/merge", {
      primary_item_id: "entity-ov1",
      secondary_item_id: "entity-ov1-duplicate"
    })
  );
});
