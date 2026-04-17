import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

function mockDocumentsApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/documents") {
      return Promise.resolve({ data: [] });
    }

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
}

function mockP4WorkspaceApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: {
          meta: {
            snapshot_id: "snapshot-1",
            generated_at: "2026-04-17T09:00:00Z",
            state_version: "v1",
          },
          data: {
            metrics: {
              tool_count: 0,
              verified_tool_count: 0,
              active_tool_count: 0,
              draft_tool_count: 0,
              archived_tool_count: 0,
              match_run_count: 0,
              evolution_run_count: 0,
              active_chain_count: 0,
              overlap_candidate_count: 0,
              pending_suggestion_count: 0,
              recent_success_rate: 100,
            },
            coverage_matrix: {
              title: "业务域 × 工具形态",
              x_axis_label: "工具形态",
              y_axis_label: "业务能力域",
              columns: [],
              rows: [],
            },
            risk_summary: [],
            pending_suggestions: [],
            recent_match_runs: [],
            recent_evolution_runs: [],
            recent_demand_sheets: [],
            catalogs: {
              domains: [],
              lifecycle_stages: [],
              tool_forms: [],
              runtime_platforms: [],
              input_types: [],
              output_types: [],
              supported_sources: [],
              verification_statuses: [],
              tag_namespaces: [],
            },
          },
        },
      });
    }

    if (url === "/tool-hub/tools") {
      return Promise.resolve({
        data: {
          meta: {
            snapshot_id: "snapshot-1",
            generated_at: "2026-04-17T09:00:00Z",
            state_version: "v1",
          },
          data: {
            items: [],
          },
        },
      });
    }

    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({
        data: {
          meta: {
            snapshot_id: "snapshot-1",
            generated_at: "2026-04-17T09:00:00Z",
            state_version: "v1",
          },
          data: {
            items: [],
          },
        },
      });
    }

    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({
        data: {
          items: [],
        },
      });
    }

    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({
        data: {
          items: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

test("renders documents page on /documents route", async () => {
  mockDocumentsApis();

  render(
    <MemoryRouter initialEntries={["/documents"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("已建库档案文档")).toBeInTheDocument();
  expect((await screen.findAllByText("10002024_NAS-EA-OV-2-As-Is-V1.0-091311")).length).toBeGreaterThan(0);
});

test("redirects / to the main default page", async () => {
  mockDocumentsApis();

  render(
    <MemoryRouter initialEntries={["/"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("已建库档案文档")).toBeInTheDocument();
  expect(screen.getByText("知识仓库")).toBeInTheDocument();
  expect(screen.queryByText("XX-P4")).not.toBeInTheDocument();
});

test("renders xx-p4 route outside the main shell", async () => {
  mockP4WorkspaceApis();

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("XX-P4")).toBeInTheDocument();
  expect(await screen.findByText("工具中台 / Tool Hub")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});

test("renders xx simulator routes outside the main shell", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p3-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 模拟发生器")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});
