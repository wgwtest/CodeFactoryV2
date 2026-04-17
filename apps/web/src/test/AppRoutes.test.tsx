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

function mockP3WorkspaceApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/requirements/specs") {
      return Promise.resolve({
        data: [
          {
            id: "spec-1",
            application_name: "空域协同规划软件",
            domain_name: "国家空域管理",
            status: "ready",
            archive_id: "20161116-nas",
            object_count: 5,
            formal_object_count: 4,
            temporary_object_count: 1,
            process_count: 2,
            updated_at: "2026-04-17T10:00:00Z",
          },
        ],
      });
    }

    if (url === "/software-design/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 1,
              pending_approval_count: 1,
              frozen_count: 0,
              package_ready_count: 0,
              pushed_count: 0,
            },
            recent_orders: [],
            recent_packages: [],
          },
        },
      });
    }

    if (url === "/software-design/orders") {
      return Promise.resolve({
        data: {
          data: {
            items: [
              {
                order_id: "p3-order-1",
                application_name: "空域协同规划软件",
                requirement_spec_id: "spec-1",
                status: "pending_approval",
                updated_at: "2026-04-17T10:00:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-design/reference-center") {
      return Promise.resolve({
        data: {
          templates: [
            {
              template_id: "template-sdd-82284",
              title: "DI-IPSC-82284A Software/Hardware Design Description",
              source_doc_id: "DI-IPSC-82284",
              document_type: "software_design_description",
              version: "A",
              format: "pdf",
              summary: "平台级软件工厂软设模板骨架。",
              recommendation: "适合平台级软件设计说明。",
              official_detail_url: "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
              pdf_asset_name: "template-sdd-82284.pdf",
              pdf_url: null,
              sections: [
                {
                  section_id: "scope",
                  title: "Architecture Overview",
                  summary: "说明平台级软件的总体架构、设计范围与关键约束。",
                },
              ],
            },
          ],
          standards: [
            {
              doc_id: "DI-IPSC-82284",
              title: "Software/Hardware Design Description",
              category: "dod-did",
              scope: "platform_or_system",
              summary: "用于软件/硬件设计说明编制的军标数据项描述。",
              official_detail_url: "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
              recommended_use: "用于平台级设计说明。",
              tags: ["design"],
              sections: [],
            },
          ],
          mappings: [
            {
              template_id: "template-sdd-82284",
              doc_id: "DI-IPSC-82284",
              rationale: "用于把 P3 软设章节与军标章节建立对应关系。",
              section_pairs: [
                {
                  template_section: "Architecture Overview",
                  standard_section: "Scope",
                },
              ],
            },
          ],
        },
      });
    }

    if (url === "/software-design/orders/p3-order-1") {
      return Promise.resolve({
        data: {
          order_id: "p3-order-1",
          requirement_spec_summary: {
            application_name: "空域协同规划软件",
            domain_name: "国家空域管理",
            status: "ready",
          },
          status: "pending_approval",
          design_description: null,
          review_threads: [],
          workorder_batch: null,
        },
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
  expect(screen.queryByText("软件设计编制与模块工单下发系统")).not.toBeInTheDocument();
});

test("renders XX-P3 route outside the main shell", async () => {
  mockP3WorkspaceApis();

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("软件设计编制与模块工单下发系统")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
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

test("renders dedicated template detail route outside the main shell", async () => {
  mockP3WorkspaceApis();

  render(
    <MemoryRouter
      initialEntries={["/xx-p3/templates/template-sdd-82284"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("软件设计说明模板细节")).toBeInTheDocument();
  expect(screen.getByText("模板骨架解析")).toBeInTheDocument();
  expect(screen.getByText("Architecture Overview")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});

test("renders xx-p2-sim route outside the main shell", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p2-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 上游模拟输入台")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});
