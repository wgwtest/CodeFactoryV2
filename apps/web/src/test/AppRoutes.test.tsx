import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: vi.fn(),
  },
}));

test("renders archive-focused documents page on /documents route", async () => {
  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 66,
          entity_count: 751,
          event_count: 4,
          process_count: 6,
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "10002024_NAS-EA-OV-2-As-Is-V1.0-091311",
            file_type: "docx",
            source_archive: "20161116-chinese",
            character_count: 23271,
            entity_count: 52,
            event_count: 1,
            process_count: 0,
            knowledge_item_count: 53,
          },
        ],
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/documents"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("当前知识库文档")).toBeInTheDocument();
  expect((await screen.findAllByText("10002024_NAS-EA-OV-2-As-Is-V1.0-091311")).length).toBeGreaterThan(0);
});

test("renders intake validation page on /documents/intake route", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/documents") {
      return Promise.resolve({ data: [] });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/documents/intake"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("这是独立的接入验证链")).toBeInTheDocument();
});
