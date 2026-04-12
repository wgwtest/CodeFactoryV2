import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { DocumentsPage } from "../pages/DocumentsPage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args)
  }
}));

test("renders searchable archive documents and opens document knowledge drawer", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/documents") {
      return Promise.resolve({
        data: [
          {
            id: "live-doc-1",
            title: "Incident Policy",
            source_name: "验证样例",
            document_key: "incident-policy",
            version_count: 1,
            latest_version: {
              id: "version-1",
              version_number: 1,
              status: "parsed",
              latest_parse_run: {
                id: "parse-run-1",
                status: "succeeded",
                parser_name: "plain_text",
                segment_count: 2
              }
            }
          }
        ]
      });
    }

    if (url === "/documents/live-doc-1") {
      return Promise.resolve({
        data: {
          id: "live-doc-1",
          title: "Incident Policy",
          source_name: "验证样例",
          document_key: "incident-policy",
          latest_version: {
            id: "version-1",
            version_number: 1,
            file_name: "policy.txt",
            mime_type: "application/octet-stream",
            status: "parsed",
            created_at: "2026-04-12T00:00:00Z",
            latest_parse_run: {
              id: "parse-run-1",
              status: "succeeded",
              parser_name: "plain_text",
              parser_version: "v2",
              failure_reason: null,
              segment_count: 2,
              created_at: "2026-04-12T00:00:00Z"
            },
            parse_runs: [
              {
                id: "parse-run-1",
                status: "succeeded",
                parser_name: "plain_text",
                parser_version: "v2",
                failure_reason: null,
                segment_count: 2,
                created_at: "2026-04-12T00:00:00Z"
              }
            ],
            segments_preview: [
              {
                id: "segment-1",
                block_type: "section",
                heading: "Section 1",
                content: "Policy overview.",
                anchor: { page: 1, section: "Section 1", line_start: 1, line_end: 2 }
              },
              {
                id: "segment-2",
                block_type: "section",
                heading: "Section 2",
                content: "Every incident report must be submitted within 2 hours.",
                anchor: { page: 1, section: "Section 2", line_start: 3, line_end: 4 }
              }
            ]
          },
          versions: []
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

    if (url.endsWith("/documents/doc-1")) {
      return Promise.resolve({
        data: {
          document: {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4
          },
          knowledge_items: [
            {
              id: "entity-ov1",
              name: "OV-1",
              item_type: "entity",
              category: "architecture_artifact",
              aliases: ["远期顶层运行概念图"],
              interpretation: {
                kind_label: "架构工件",
                family_code: "OV",
                family_label: "运行视图",
                display_name: "高层运行概念图",
                standard_name: "High-Level Operational Concept Graphic",
                summary: "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
                producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。"
              },
              evidence: [
                {
                  document_id: "doc-1",
                  document_title: "NAS AV-1",
                  excerpt: "OV-1 excerpt"
                }
              ]
            },
            {
              id: "event-far-term",
              name: "远期目标（Far Term）",
              item_type: "event",
              category: "timeline_event",
              aliases: [],
              interpretation: {
                kind_label: "时间事件",
                family_code: null,
                family_label: null,
                display_name: null,
                standard_name: null,
                summary: "远期目标（Far Term） 是时间事件类实体。",
                producer_hint: null
              },
              evidence: [
                {
                  document_id: "doc-1",
                  document_title: "NAS AV-1",
                  excerpt: "Far Term excerpt"
                }
              ]
            }
          ]
        }
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4
          },
          {
            id: "doc-2",
            title: "NAS Roadmap",
            file_type: "docx",
            source_archive: "20161116 路线图",
            character_count: 800,
            entity_count: 1,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 1
          }
        ]
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(<DocumentsPage />);

  expect(await screen.findByText("接入解析验证")).toBeInTheDocument();
  expect(await screen.findByText("Incident Policy")).toBeInTheDocument();
  expect(await screen.findByText("已解析")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "查看解析" }));
  expect(await screen.findByText("解析详情")).toBeInTheDocument();
  expect((await screen.findAllByText("plain_text")).length).toBeGreaterThan(0);
  expect(await screen.findByText("Section 1")).toBeInTheDocument();
  expect(await screen.findByText("Every incident report must be submitted within 2 hours.")).toBeInTheDocument();

  expect(await screen.findByText("已建库档案文档")).toBeInTheDocument();
  expect(await screen.findByText("NAS AV-1")).toBeInTheDocument();
  expect(await screen.findByText("NAS Roadmap")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜索文档标题、来源或类型"), { target: { value: "NAS AV-1" } });

  expect(await screen.findByDisplayValue("NAS AV-1")).toBeInTheDocument();
  expect(screen.queryByText("NAS Roadmap")).not.toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "查看" }));

  expect(await screen.findByText("文档详情")).toBeInTheDocument();
  expect(await screen.findByText("文档概览")).toBeInTheDocument();
  expect((await screen.findAllByText("实体")).length).toBeGreaterThan(0);
  expect((await screen.findAllByText("事件")).length).toBeGreaterThan(0);
  expect(await screen.findByText("高层运行概念图")).toBeInTheDocument();
  expect(
    await screen.findByText("OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。")
  ).toBeInTheDocument();
  expect(await screen.findByText("OV-1 excerpt")).toBeInTheDocument();
});
