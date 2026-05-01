import "@testing-library/jest-dom/vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";
import {
  buildDisplayBaseline,
  buildPlatformLegend,
  buildPlatformRoutes,
  buildPortalProjectionEnvelope,
  buildScenarioCatalog,
} from "./p6TestData";

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
});

function mockPortalApis() {
  getMock.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/p6/mock-scenarios") {
      return Promise.resolve({ data: buildScenarioCatalog() });
    }

    if (url === "/p6/portal-projection") {
      return Promise.resolve({ data: buildPortalProjectionEnvelope(config?.params?.scenario ?? "baseline") });
    }

    if (url === "/platform-config/display-baseline") {
      return Promise.resolve({ data: buildDisplayBaseline() });
    }

    if (url === "/platform-config/routes") {
      return Promise.resolve({ data: buildPlatformRoutes() });
    }

    if (url === "/platform-config/legend") {
      return Promise.resolve({ data: buildPlatformLegend() });
    }

    if (url === "/platform-display/workbench") {
      return Promise.resolve({
        data: {
          version: "p6.4-v1",
          templates: [],
          bindings: [],
          layouts: [],
          presets: [],
          experiments: [],
          promotion_candidates: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

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

function mockDocumentIntakeApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/documents") {
      return Promise.resolve({ data: [] });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

function mockRequirementsApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/requirements/specs") {
      return Promise.resolve({ data: [] });
    }

    if (url === "/requirements/formal-elements?item_type=entity&archive_id=20161116-nas") {
      return Promise.resolve({
        data: [
          {
            id: "entity-nas",
            name: "国家空域系统",
            item_type: "entity",
            category: "system_or_service",
            aliases: ["NAS"],
            document_count: 11,
            summary: "国家空域系统 是系统/服务类实体。",
            source_archive_id: "20161116-nas",
          },
        ],
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

function mockModelingApis() {
  postMock.mockImplementation((url: string) => {
    if (url === "/modeling/requirement-drafts") {
      return Promise.resolve({
        data: {
          draft: {
            draft_id: "draft-1",
            archive_id: "20161116-nas",
            status: "draft",
            current_step: "goal",
            application_name: "",
            application_goal: {
              problem_statement: "",
              target_outcome: "",
              success_criteria: [],
            },
            audiences: [],
            roles: [],
            business_flows: [],
            business_objects: [],
            key_events: [],
            application_structure: {
              workspaces: [],
              pages: [],
              permission_intents: [],
            },
            knowledge_references: [],
            manual_additions: [],
            created_at: "2026-04-13T00:00:00Z",
            updated_at: "2026-04-13T00:00:00Z",
          },
          recommendations: {
            goal: [],
            audience: [],
            flow: [],
            object_event: [],
            structure: [],
          },
        },
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

    if (url === "/tool-hub/evolution/config") {
      return Promise.resolve({
        data: {
          meta: {
            snapshot_id: "snapshot-1",
            generated_at: "2026-04-17T09:00:00Z",
            state_version: "v1",
          },
          data: {
            config_id: "default",
            enabled: true,
            schedule_mode: "manual_and_scheduled",
            interval_minutes: 60,
            include_draft_tools: true,
            focus_rule_ids: ["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"],
            overlap_threshold: 3,
            max_run_history: 50,
            auto_apply_rule_ids: ["missing_description", "taxonomy_issue"],
            updated_by: "p4-workspace",
            updated_at: "2026-04-18T08:00:00Z",
          },
        },
      });
    }

    if (url === "/tool-hub/evolution/runs") {
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

    if (url === "/tool-hub/evolution/tasks") {
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

function mockSoftwareBuildApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 0,
              draft_count: 0,
              exported_with_gaps_count: 0,
              completed_count: 0,
              failed_count: 0,
            },
            recent_orders: [],
          },
        },
      });
    }

    if (url === "/software-build/orders") {
      return Promise.resolve({
        data: {
          data: {
            items: [],
          },
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

function mockXXP1SimApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/xx-p1-sim/domains") {
      return Promise.resolve({
        data: {
          provider: {
            provider_id: "xx-p1-sim",
            provider_name: "XX-P1-Sim",
            provider_kind: "p1_knowledge_provider",
            status: "online",
            capabilities: ["domain_catalog", "knowledge_archive"],
            version: "v1.0",
            seed: "xx-p1-sim-fixed-v1",
          },
          items: [
            {
              domain_id: "airspace-planning",
              domain_name: "空域规划领域知识",
              domain_summary: "包含空域对象、冲突窗口、协同规划流程、会签约束和证据片段。",
              archive_version: "v1.0",
              concept_count: 12,
              rule_count: 8,
              process_count: 3,
              evidence_count: 18,
            },
          ],
        },
      });
    }

    if (url === "/xx-p1-sim/domains/airspace-planning/knowledge") {
      return Promise.resolve({
        data: {
          provider_id: "xx-p1-sim",
          domain_id: "airspace-planning",
          archive_id: "archive-airspace-planning-v1",
          archive_version: "v1.0",
          published_at: "2026-04-30T00:00:00+00:00",
          concepts: [
            { concept_id: "concept-airspace-cell", name: "空域单元", definition: "用于表达可规划的空域范围。" },
          ],
          entities: [],
          rules: [
            {
              rule_id: "rule-confirm-conflict-window",
              name: "冲突窗口确认规则",
              description: "冲突窗口未确认时，不得直接发布规划结果。",
            },
          ],
          processes: [
            {
              process_id: "process-airspace-coordination",
              name: "空域规划协同流程",
              steps: ["任务创建", "冲突识别", "协同会签", "结果发布"],
            },
          ],
          constraints: [
            {
              constraint_id: "constraint-audit-trace",
              category: "traceability",
              description: "关键状态变化需要保留责任人、时间和依据。",
            },
          ],
          evidence_refs: [
            {
              evidence_id: "evidence-airspace-term",
              source: "P1 发布态领域知识",
              excerpt: "空域规划过程应形成可追溯记录。",
            },
          ],
        },
      });
    }

    if (url === "/xx-p1-sim/logs") {
      return Promise.resolve({
        data: {
          items: [
            {
              call_id: "p1-sim-call-0001",
              called_at: "2026-04-30T21:45:08+00:00",
              method: "GET",
              path: "/api/xx-p1-sim/domains",
              domain_id: null,
              status_code: 200,
              archive_version: "v1.0",
            },
          ],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

function mockBrainstormLabApis() {
  getMock.mockImplementation((url: string) => {
    if (url === "/brainstorm/orchestrators") {
      return Promise.resolve({
        data: {
          items: [
            {
              orchestrator_id: "brainstorming",
              name: "BrainstormingOrchestrator",
              status: "active",
              description: "连续问答、主动追问、轻量选项、结构化 patch。",
            },
          ],
          stable_contract: {
            formal_document: true,
            template_object: true,
            knowledge_binding: true,
            draft_persistence: true,
            check_and_freeze: true,
            p2_to_p3_output: true,
          },
          output_protocol: [
            "previous_interaction",
            "input_relation",
            "spec_execution",
            "post_update_review",
            "closure_decision",
            "next_interaction",
            "decision_trace",
          ],
        },
      });
    }

    if (url === "/brainstorm/providers") {
      return Promise.resolve({ data: { items: [{ provider_id: "mock", name: "Mock Provider", status: "active" }] } });
    }

    throw new Error(`unexpected url: ${url}`);
  });
}

function parseEnvFile(filePath: string) {
  if (!existsSync(filePath)) {
    return {} as Record<string, string>;
  }

  return readFileSync(filePath, "utf8")
    .split(/\r?\n/)
    .reduce<Record<string, string>>((result, line) => {
      const trimmedLine = line.trim();
      if (!trimmedLine || trimmedLine.startsWith("#")) {
        return result;
      }

      const separatorIndex = trimmedLine.indexOf("=");
      if (separatorIndex < 0) {
        return result;
      }

      const key = trimmedLine.slice(0, separatorIndex).trim();
      const value = trimmedLine.slice(separatorIndex + 1).trim();
      result[key] = value;
      return result;
    }, {});
}

function getRepositoryDefaultRoute() {
  const repoRoot = resolve(process.cwd(), "../..");
  const repoEnv = {
    ...parseEnvFile(resolve(repoRoot, ".env")),
    ...parseEnvFile(resolve(repoRoot, ".env.local")),
    ...process.env,
  };
  return repoEnv.VITE_DEFAULT_ROUTE ?? "/documents";
}

test("renders documents page on /documents route", async () => {
  mockDocumentsApis();

  render(
    <MemoryRouter initialEntries={["/documents"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("当前知识库文档")).toBeInTheDocument();
  expect((await screen.findAllByText("10002024_NAS-EA-OV-2-As-Is-V1.0-091311")).length).toBeGreaterThan(0);
});

test("renders intake validation page on /documents/intake route", async () => {
  mockDocumentIntakeApis();

  render(
    <MemoryRouter initialEntries={["/documents/intake"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("这是独立的接入验证链")).toBeInTheDocument();
});

test("redirects / to the main default page", async () => {
  const defaultRoute = getRepositoryDefaultRoute();

  switch (defaultRoute) {
    case "/documents":
      mockDocumentsApis();
      break;
    case "/documents/intake":
      mockDocumentIntakeApis();
      break;
    case "/requirements":
      mockRequirementsApis();
      break;
    case "/modeling":
      mockModelingApis();
      break;
    case "/portal":
      mockPortalApis();
      break;
    case "/build":
      mockSoftwareBuildApis();
      break;
    case "/xx-p3":
      mockP3WorkspaceApis();
      break;
    case "/xx-p4":
      mockP4WorkspaceApis();
      break;
    case "/xx-p2-sim":
      break;
    case "/xx-p1-sim":
      mockXXP1SimApis();
      break;
    default:
      throw new Error(`unsupported default route for AppRoutes.test.tsx: ${defaultRoute}`);
  }

  render(
    <MemoryRouter initialEntries={["/"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  switch (defaultRoute) {
    case "/documents":
      expect(await screen.findByText("当前知识库文档")).toBeInTheDocument();
      expect(screen.getByText("知识仓库")).toBeInTheDocument();
      expect(screen.queryByText("软件设计编制与模块工单下发系统")).not.toBeInTheDocument();
      break;
    case "/documents/intake":
      expect(await screen.findByText("这是独立的接入验证链")).toBeInTheDocument();
      expect(screen.getByText("知识仓库")).toBeInTheDocument();
      expect(screen.queryByText("软件设计编制与模块工单下发系统")).not.toBeInTheDocument();
      break;
    case "/requirements":
      expect(await screen.findByRole("heading", { name: "应用需求建模" })).toBeInTheDocument();
      expect(screen.getByText("知识仓库")).toBeInTheDocument();
      expect(screen.queryByText("软件设计编制与模块工单下发系统")).not.toBeInTheDocument();
      break;
    case "/modeling":
      expect(await screen.findByText("应用需求建模器")).toBeInTheDocument();
      expect(screen.getByText("知识仓库")).toBeInTheDocument();
      expect(screen.queryByText("软件设计编制与模块工单下发系统")).not.toBeInTheDocument();
      break;
    case "/portal":
      expect(await screen.findByText("图例")).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    case "/build":
      expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
      expect(screen.getByText("P5 交付主单")).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    case "/xx-p3":
      expect(await screen.findByText("软件设计编制与模块工单下发系统")).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    case "/xx-p4":
      expect(await screen.findByText("XX-P4")).toBeInTheDocument();
      expect(await screen.findByText("工具中台 / Tool Hub")).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    case "/xx-p2-sim":
      expect(await screen.findByText("P3 上游模拟输入台")).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    case "/xx-p1-sim":
      expect(await screen.findByRole("heading", { name: "XX-P1-Sim" })).toBeInTheDocument();
      expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
      break;
    default:
      throw new Error(`unsupported default route for AppRoutes.test.tsx: ${defaultRoute}`);
  }
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

test("renders xx-p1-sim route outside the main shell", async () => {
  mockXXP1SimApis();

  render(
    <MemoryRouter initialEntries={["/xx-p1-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "XX-P1-Sim" })).toBeInTheDocument();
expect(screen.getByText("P1 服务接口")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});

test("renders requirement authoring route outside the main shell", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-authoring/templates") {
      return Promise.resolve({ data: [] });
    }
    if (url === "/requirement-authoring/documents") {
      return Promise.resolve({ data: [] });
    }
    if (url === "/requirement-authoring/knowledge-providers") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/archives") {
      return Promise.resolve({ data: [] });
    }
    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/requirement-authoring"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 专家需求规格编写工作台" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});

test("renders P2 Brainstorming Lab route outside the main shell", async () => {
  mockBrainstormLabApis();

  render(
    <MemoryRouter initialEntries={["/p2-brainstorm-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 Brainstorming Lab" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /组织器配置/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
});
