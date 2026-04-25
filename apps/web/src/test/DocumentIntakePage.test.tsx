import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { DocumentIntakePage } from "../pages/DocumentIntakePage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: vi.fn(),
  },
}));

vi.mock("../components/DocumentUploadForm", () => ({
  DocumentUploadForm: () => <div data-testid="document-upload-form">upload-form</div>,
}));

test("renders intake validation workspace and opens parse detail drawer", async () => {
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
                segment_count: 2,
              },
            },
          },
        ],
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
              created_at: "2026-04-12T00:00:00Z",
            },
            parse_runs: [
              {
                id: "parse-run-1",
                status: "succeeded",
                parser_name: "plain_text",
                parser_version: "v2",
                failure_reason: null,
                segment_count: 2,
                created_at: "2026-04-12T00:00:00Z",
              },
            ],
            segments_preview: [
              {
                id: "segment-1",
                block_type: "section",
                heading: "Section 1",
                content: "Policy overview.",
                anchor: { page: 1, section: "Section 1", line_start: 1, line_end: 2 },
              },
              {
                id: "segment-2",
                block_type: "section",
                heading: "Section 2",
                content: "Every incident report must be submitted within 2 hours.",
                anchor: { page: 1, section: "Section 2", line_start: 3, line_end: 4 },
              },
            ],
          },
          versions: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter>
      <DocumentIntakePage />
    </MemoryRouter>,
  );

  expect(await screen.findByText("这是独立的接入验证链")).toBeInTheDocument();
  expect(await screen.findByTestId("document-upload-form")).toBeInTheDocument();
  expect(await screen.findByText("Incident Policy")).toBeInTheDocument();
  expect((await screen.findAllByText("已解析")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "查看解析" }));

  expect(await screen.findByText("解析详情")).toBeInTheDocument();
  expect((await screen.findAllByText("plain_text")).length).toBeGreaterThan(0);
  expect(await screen.findByText("Section 1")).toBeInTheDocument();
  expect(await screen.findByText("Every incident report must be submitted within 2 hours.")).toBeInTheDocument();
});
