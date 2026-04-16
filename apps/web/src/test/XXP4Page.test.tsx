import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const putMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    put: (...args: unknown[]) => putMock(...args),
  },
}));

function buildReadEnvelope<T>(data: T, snapshotId = "snapshot-1") {
  return {
    meta: {
      snapshot_id: snapshotId,
      generated_at: "2026-04-16T09:00:00Z",
      state_version: "v0",
    },
    data,
  };
}

function buildOverview() {
  return {
    metrics: {
      tool_count: 4,
      verified_tool_count: 2,
      active_tool_count: 3,
      active_chain_count: 1,
      overlap_candidate_count: 2,
      pending_suggestion_count: 5,
      recent_success_rate: 100,
    },
    coverage_matrix: {
      stages: [
        { id: "archive_intake", label: "资料接入", description: "" },
        { id: "modeling", label: "应用建模", description: "" },
        { id: "validation", label: "验证工作台", description: "" },
      ],
      rows: [
        {
          category_id: "application_modeling",
          category_label: "应用建模",
          cells: [
            { stage_id: "archive_intake", value: 0 },
            { stage_id: "modeling", value: 2 },
            { stage_id: "validation", value: 1 },
          ],
        },
        {
          category_id: "validation_support",
          category_label: "验证支撑",
          cells: [
            { stage_id: "archive_intake", value: 0 },
            { stage_id: "modeling", value: 1 },
            { stage_id: "validation", value: 2 },
          ],
        },
      ],
    },
    risk_summary: [
      {
        kind: "overlap_risk",
        title: "流程验证器与流程候选解释器疑似重叠",
        description: "两者在阶段和输入上存在高相似度。",
        severity: "warning",
      },
    ],
    recent_match_runs: [
      {
        run_id: "match-1",
        run_type: "match",
        title: "流程验证场景",
        status: "completed",
        created_at: "2026-04-15T10:00:00Z",
        summary: "2 个候选工具",
      },
    ],
    recent_evolution_runs: [
      {
        run_id: "evolution-1",
        run_type: "evolution",
        title: "工具池巡检",
        status: "completed",
        created_at: "2026-04-15T09:00:00Z",
        summary: "3 项发现",
      },
    ],
    catalogs: {
      categories: [
        { id: "application_modeling", label: "应用建模", description: "" },
        { id: "validation_support", label: "验证支撑", description: "" },
      ],
      stages: [
        { id: "modeling", label: "应用建模", description: "" },
        { id: "validation", label: "验证工作台", description: "" },
      ],
      input_types: [
        { id: "process_list", label: "流程列表", description: "" },
        { id: "manual_text", label: "人工文本", description: "" },
      ],
      output_types: [
        { id: "validation_report", label: "验证报告", description: "" },
        { id: "review_suggestion", label: "审核建议", description: "" },
      ],
      supported_sources: [
        { id: "manual_input", label: "人工输入", description: "" },
      ],
      verification_statuses: [
        { id: "verified", label: "已验证", description: "" },
        { id: "warning", label: "需复核", description: "" },
      ],
      tag_namespaces: [
        { id: "stage", label: "阶段标签", description: "" },
        { id: "capability", label: "能力标签", description: "" },
      ],
    },
  };
}

function buildTools() {
  return {
    items: [
      {
        tool_id: "tool-process-validator",
        name: "流程验证器",
        slug: "process-validator",
        status: "active",
        summary: "针对流程清单生成结构化验证建议",
        problem_statement: "降低流程建模前期人工比对成本",
        primary_category_id: "application_modeling",
        tags: ["stage:modeling", "capability:process-analysis"],
        applicable_stages: ["modeling", "validation"],
        input_types: ["process_list"],
        output_types: ["validation_report"],
        supported_sources: ["manual_input"],
        usage_notes: "用于流程验证",
        keywords: ["流程", "验证"],
        verification: {
          status: "verified",
          last_verified_at: null,
          last_verified_result: "样例通过",
          sample_case_ids: ["sample-1"],
        },
        created_at: "2026-04-15T08:00:00Z",
        updated_at: "2026-04-15T08:00:00Z",
      },
    ],
  };
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  putMock.mockReset();
});

test("renders XX-P4 cockpit route and runs match/evolution workflows", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({ data: buildReadEnvelope(buildOverview()) });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools()) });
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/match-runs") {
      return Promise.resolve({
        data: {
          run_id: "match-2",
          status: "completed",
          created_at: "2026-04-15T11:00:00Z",
          context_summary: "关联知识库 20161116-nas，当前发布态包含 1 个实体、1 个流程。",
          request: {
            scenario_text: "需要针对协同处置流程挑选验证工具",
            target_stage: "modeling",
            required_input_types: ["process_list"],
            expected_output_types: ["validation_report"],
            preferred_tags: ["capability:process-analysis"],
            knowledge_context: {
              archive_id: "20161116-nas",
              entity_ids: [],
              process_ids: ["process-collaboration"],
              snapshot_version: "v1",
            },
          },
          candidates: [
            {
              tool_id: "tool-process-validator",
              name: "流程验证器",
              match_score: 88,
              matched_dimensions: ["stage", "input_type", "output_type", "tags"],
              reasons: ["覆盖目标阶段：modeling", "命中输入类型：process_list"],
              gaps: [],
              verification_status: "verified",
            },
          ],
        },
      });
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({
        data: {
          run_id: "evolution-2",
          status: "completed",
          created_at: "2026-04-15T11:05:00Z",
          summary: {
            tool_count: 1,
            finding_count: 1,
            missing_description_count: 0,
            taxonomy_issue_count: 0,
            overlap_risk_count: 1,
            coverage_gap_count: 0,
          },
          findings: [
            {
              finding_id: "finding-1",
              kind: "overlap_risk",
              title: "流程验证器与流程候选解释器疑似重叠",
              description: "两者在阶段和输入上存在高相似度。",
              severity: "warning",
              tool_ids: ["tool-process-validator", "tool-process-explainer"],
            },
          ],
        },
      });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("XX-P4")).toBeInTheDocument();
  expect(screen.getByText("工具中台 / Tool Hub")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-page")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-hero-shell")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-content-shell")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspaces")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspace-nav")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspace-tab-overview")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspace-tab-input-chain")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspace-tab-evolution")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-workspace-tab-registry")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-content-shell")).toHaveStyle({ margin: "0 auto 0" });
  expect(document.querySelector("#xx-p4-workspace-tab-overview")).toHaveAttribute("data-workspace-tone", "overview");
  expect(document.querySelector("#xx-p4-workspace-tab-input-chain")).toHaveAttribute("data-workspace-tone", "input");
  expect(document.querySelector("#xx-p4-workspace-tab-evolution")).toHaveAttribute("data-workspace-tone", "evolution");
  expect(document.querySelector("#xx-p4-workspace-tab-registry")).toHaveAttribute("data-workspace-tone", "registry");
  expect(screen.getByText("全局状态")).toBeInTheDocument();
  expect(screen.getByText("场景到匹配")).toBeInTheDocument();
  expect(screen.getByText("工具池体检")).toBeInTheDocument();
  expect(screen.getByText("资产与覆盖")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "总览" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "输入工具链" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "自演进巡检" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "工具仓库" })).toBeInTheDocument();
  expect(screen.queryByText("P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。")).not.toBeInTheDocument();
  expect(document.querySelector("#xx-p4-overview-metrics")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-metrics-strip")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-metric-tool_count")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-overview-run-monitor")).toBeInTheDocument();
  expect(screen.getByText("运行监视")).toBeInTheDocument();
  expect(screen.queryByText("覆盖热力矩阵")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "输入工具链" }));
  fireEvent.change(await screen.findByLabelText("输入场景"), {
    target: { value: "需要针对协同处置流程挑选验证工具" },
  });
  fireEvent.click(screen.getByRole("button", { name: "运行匹配" }));

  expect(await screen.findByText("流程验证器")).toBeInTheDocument();
  expect(await screen.findByText("关联知识库 20161116-nas，当前发布态包含 1 个实体、1 个流程。")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "自演进巡检" }));
  fireEvent.click(await screen.findByRole("button", { name: "触发巡检" }));
  expect((await screen.findAllByText("流程验证器与流程候选解释器疑似重叠")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("覆盖热力矩阵")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-registry-coverage-matrix")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-coverage-matrix")).toBeInTheDocument();
});

test("creates a tool from registry workspace", async () => {
  let tools = buildTools();

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({ data: buildReadEnvelope(buildOverview()) });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(tools) });
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body: unknown) => {
    if (url === "/tool-hub/tools") {
      const payload = body as {
        name: string;
        summary: string;
        primary_category_id: string;
        applicable_stages: string[];
      };
      const created = {
        tool_id: "tool-new",
        slug: "new-tool",
        status: "draft",
        problem_statement: "",
        tags: [],
        input_types: [],
        output_types: [],
        supported_sources: ["manual_input"],
        usage_notes: "",
        keywords: [],
        verification: {
          status: "unverified",
          last_verified_at: null,
          last_verified_result: "",
          sample_case_ids: [],
        },
        created_at: "2026-04-15T12:00:00Z",
        updated_at: "2026-04-15T12:00:00Z",
        ...payload,
      };
      tools = { items: [created, ...tools.items] };
      return Promise.resolve({ data: created });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  fireEvent.click(await screen.findByRole("tab", { name: "工具仓库" }));
  fireEvent.click(await screen.findByRole("button", { name: "新建工具" }));

  const dialog = await screen.findByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("工具名称"), { target: { value: "新建流程工具" } });
  fireEvent.change(within(dialog).getByLabelText("摘要"), { target: { value: "用于流程场景的验证辅助" } });
  fireEvent.mouseDown(within(dialog).getAllByLabelText("主分类")[0]);
  {
    const options = await screen.findAllByText("应用建模");
    fireEvent.click(options[options.length - 1]);
  }
  fireEvent.mouseDown(within(dialog).getAllByLabelText("适用阶段")[0]);
  {
    const options = await screen.findAllByText("应用建模");
    fireEvent.click(options[options.length - 1]);
  }
  fireEvent.click(screen.getByRole("button", { name: "保存工具" }));

  expect(await screen.findByText("新建流程工具")).toBeInTheDocument();
});

test("shows snapshot consistency warning when tool hub read models are out of sync", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({ data: buildReadEnvelope(buildOverview(), "snapshot-overview") });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools(), "snapshot-tools") });
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }, "snapshot-evolution") });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。")).toBeInTheDocument();
});
