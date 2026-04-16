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
      title: "业务域 × 工具形态",
      x_axis_label: "工具形态",
      y_axis_label: "业务能力域",
      columns: [
        { id: "skill", label: "Skill", description: "" },
        { id: "template", label: "模板", description: "" },
        { id: "service_endpoint", label: "服务接口", description: "" },
      ],
      rows: [
        {
          row_id: "workflow_approval",
          row_label: "审批流转",
          cells: [
            { column_id: "skill", value: 2 },
            { column_id: "template", value: 0 },
            { column_id: "service_endpoint", value: 0 },
          ],
        },
        {
          row_id: "master_data",
          row_label: "主数据维护",
          cells: [
            { column_id: "skill", value: 0 },
            { column_id: "template", value: 0 },
            { column_id: "service_endpoint", value: 1 },
          ],
        },
      ],
    },
    risk_summary: [
      {
        kind: "overlap_risk",
        title: "审批规则校验器与审批路径解释器疑似重叠",
        description: "两者在业务域、生命周期和输入上存在高相似度。",
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
    recent_demand_sheets: [
      {
        sheet_id: "tds-001",
        sheet_name: "模拟蓝军一期工具需求单",
        status: "accepted",
        business_case: "simulated_blue_force",
        source: {
          phase: "p3_simulator",
          producer: "mock_blue_force_generator",
          business_case: "simulated_blue_force",
          scenario_id: "blue-force-sim-001",
          scenario_name: "模拟蓝军对抗推演一期",
        },
        requested_by: "P3",
        root_node: {
          node_id: "sys-blue-force",
          node_type: "system",
          node_name: "模拟蓝军系统",
          node_code: "SYS-BLUE-FORCE",
          business_domain_id: "simulated_blue_force",
          children: [],
        },
        item_ids: ["tdi-001"],
        item_count: 1,
        matched_existing_count: 0,
        manufacturing_count: 1,
        ready_for_fetch_count: 0,
        failed_count: 0,
        submitted_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    ],
    catalogs: {
      domains: [
        { id: "simulated_blue_force", label: "模拟蓝军", description: "" },
        { id: "workflow_approval", label: "审批流转", description: "" },
        { id: "master_data", label: "主数据维护", description: "" },
      ],
      lifecycle_stages: [
        { id: "solution_design", label: "方案设计", description: "" },
        { id: "verification_release", label: "验证发布", description: "" },
      ],
      tool_forms: [
        { id: "skill", label: "Skill", description: "" },
        { id: "service_endpoint", label: "服务接口", description: "" },
      ],
      runtime_platforms: [
        { id: "agent_runtime", label: "Agent 运行时", description: "" },
        { id: "backend_service", label: "后端服务", description: "" },
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
        { id: "domain", label: "业务域标签", description: "" },
        { id: "form", label: "工具形态标签", description: "" },
      ],
    },
  };
}

function buildTools() {
  return {
    items: [
      {
        tool_id: "tool-approval-rule-validator",
        name: "审批规则校验器",
        slug: "approval-rule-validator",
        status: "active",
        summary: "针对审批流程生成结构化验证建议",
        problem_statement: "降低审批设计前期人工比对成本",
        primary_domain_id: "workflow_approval",
        tool_form_id: "skill",
        runtime_platform_ids: ["agent_runtime"],
        tags: ["domain:workflow_approval", "form:skill", "runtime:agent_runtime", "lifecycle:solution_design"],
        lifecycle_stage_ids: ["solution_design", "verification_release"],
        input_types: ["process_list"],
        output_types: ["validation_report"],
        supported_sources: ["manual_input"],
        usage_notes: "用于审批验证",
        keywords: ["审批", "验证"],
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

function buildDemandSheetDetail() {
  return {
    sheet_id: "tds-001",
    sheet_name: "模拟蓝军一期工具需求单",
    status: "accepted",
    business_case: "simulated_blue_force",
    source: {
      phase: "p3_simulator",
      producer: "mock_blue_force_generator",
      business_case: "simulated_blue_force",
      scenario_id: "blue-force-sim-001",
      scenario_name: "模拟蓝军对抗推演一期",
    },
    requested_by: "P3",
    root_node: {
      node_id: "sys-blue-force",
      node_type: "system",
      node_name: "模拟蓝军系统",
      node_code: "SYS-BLUE-FORCE",
      business_domain_id: "simulated_blue_force",
      children: [
        {
          node_id: "subsys-blue-force",
          node_type: "subsystem",
          node_name: "蓝军编组",
          node_code: "SUBSYS-BLUE-FORCE",
          business_domain_id: "simulated_blue_force",
          children: [
            {
              node_id: "subsub-blue-force-structure",
              node_type: "sub_subsystem",
              node_name: "兵力结构编组",
              node_code: "SUBSUB-BLUE-FORCE-STRUCTURE",
              business_domain_id: "simulated_blue_force",
              children: [
                {
                  node_id: "module-blue-force-tree",
                  node_type: "module",
                  node_name: "编制树生成",
                  node_code: "MODULE-BLUE-FORCE-TREE",
                  business_domain_id: "simulated_blue_force",
                  children: [
                    {
                      node_id: "component-blue-force-tree-builder",
                      node_type: "component",
                      node_name: "蓝军编组树构造器",
                      node_code: "COMP-BLUE-FORCE-TREE-BUILDER",
                      business_domain_id: "simulated_blue_force",
                      children: [],
                      component_spec: {
                        component_name: "蓝军编组树构造器",
                        component_code: "COMP-BLUE-FORCE-TREE-BUILDER",
                        problem_statement: "生成蓝军编组树并输出结构化结果",
                        required_input_types: ["force_definition"],
                        expected_output_types: ["force_tree"],
                        preferred_tool_forms: ["skill"],
                        preferred_runtime_platforms: ["agent_runtime"],
                        lifecycle_stage_ids: ["solution_design"],
                        keywords: ["蓝军", "编组", "树"],
                        acceptance_notes: "输出结构化蓝军编组树",
                      },
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    item_ids: ["tdi-001"],
    item_count: 1,
    matched_existing_count: 0,
    manufacturing_count: 1,
    ready_for_fetch_count: 0,
    failed_count: 0,
    items: [
      {
        item_id: "tdi-001",
        sheet_id: "tds-001",
        source_node_id: "component-blue-force-tree-builder",
        ancestry: ["模拟蓝军系统", "蓝军编组", "兵力结构编组", "编制树生成", "蓝军编组树构造器"],
        business_domain_id: "simulated_blue_force",
        component_name: "蓝军编组树构造器",
        component_code: "COMP-BLUE-FORCE-TREE-BUILDER",
        problem_statement: "生成蓝军编组树并输出结构化结果",
        required_input_types: ["force_definition"],
        expected_output_types: ["force_tree"],
        preferred_tool_forms: ["skill"],
        preferred_runtime_platforms: ["agent_runtime"],
        lifecycle_stage_ids: ["solution_design"],
        keywords: ["蓝军", "编组", "树"],
        acceptance_notes: "输出结构化蓝军编组树",
        status: "manufacturing_pending",
        analysis_result: "已受理组件需求",
        check_result: "树型层级校验通过",
        match_result: "未命中现有工具，已进入模拟制造排期。",
        supply_result: {
          result_type: "pending_manufacture",
          summary: "未命中现有工具，等待模拟制造。",
          progress_query_path: "/api/tool-hub/demand-items/tdi-001/progress",
          estimated_ready_at: "2026-04-16T18:00:00Z",
          estimated_ready_in_hours: 8,
        },
        submitted_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    ],
    submitted_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
  };
}

function buildDemandSheets() {
  const detail = buildDemandSheetDetail();
  return {
    items: [
      {
        ...detail,
        items: undefined,
      },
    ],
  };
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  putMock.mockReset();
});

test("renders XX-P4 cockpit route with input demand chain and evolution workspaces", async () => {
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
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheets() });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: buildDemandSheetDetail() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/mock-generators/blue-force-demand-sheets") {
      return Promise.resolve({
        data: buildDemandSheetDetail(),
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
              title: "审批规则校验器与审批路径解释器疑似重叠",
              description: "两者在业务域、生命周期和输入上存在高相似度。",
              severity: "warning",
              tool_ids: ["tool-approval-rule-validator", "tool-approval-path-explainer"],
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
  expect(screen.getByText("总单到供给")).toBeInTheDocument();
  expect(screen.getByText("工具池体检")).toBeInTheDocument();
  expect(screen.getByText("资产与覆盖")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "总览" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "输入工序链" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "自演进巡检" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "工具仓库" })).toBeInTheDocument();
  expect(screen.queryByText("P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。")).not.toBeInTheDocument();
  expect(document.querySelector("#xx-p4-overview-metrics")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-metrics-strip")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-metric-tool_count")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-overview-run-monitor")).toBeInTheDocument();
  expect(screen.getByText("运行监视")).toBeInTheDocument();
  expect(screen.queryByText("业务域 × 工具形态")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "输入工序链" }));
  expect(await screen.findByText("P3 模拟发生区")).toBeInTheDocument();
  expect(screen.getByText("总单树审查区")).toBeInTheDocument();
  expect(screen.getByText("叶子项处理流水区")).toBeInTheDocument();
  expect(screen.getByText("P5 输出预览区")).toBeInTheDocument();
  expect(screen.getByText("模拟蓝军一期工具需求单")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "生成模拟蓝军需求总单" }));
  expect(postMock).toHaveBeenCalledWith("/tool-hub/mock-generators/blue-force-demand-sheets");

  fireEvent.click(screen.getByRole("tab", { name: "自演进巡检" }));
  fireEvent.click(await screen.findByRole("button", { name: "触发巡检" }));
  expect((await screen.findAllByText("审批规则校验器与审批路径解释器疑似重叠")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("业务域 × 工具形态")).toBeInTheDocument();
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
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheets() });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: buildDemandSheetDetail() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body: unknown) => {
    if (url === "/tool-hub/tools") {
      const payload = body as {
        name: string;
        summary: string;
        primary_domain_id: string;
        tool_form_id: string;
        runtime_platform_ids: string[];
        lifecycle_stage_ids: string[];
      };
      const created = {
        tool_id: "tool-new",
        slug: "new-tool",
        status: "draft",
        problem_statement: "",
        tags: ["domain:workflow_approval", "form:skill", "runtime:agent_runtime", "lifecycle:solution_design"],
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
  fireEvent.mouseDown(within(dialog).getAllByLabelText("主业务域")[0]);
  {
    const options = await screen.findAllByText("审批流转");
    fireEvent.click(options[options.length - 1]);
  }
  fireEvent.mouseDown(within(dialog).getAllByLabelText("工具形态")[0]);
  {
    const options = await screen.findAllByText("Skill");
    fireEvent.click(options[options.length - 1]);
  }
  fireEvent.mouseDown(within(dialog).getAllByLabelText("运行平台")[0]);
  {
    const options = await screen.findAllByText("Agent 运行时");
    fireEvent.click(options[options.length - 1]);
  }
  fireEvent.mouseDown(within(dialog).getAllByLabelText("适用生命周期环节")[0]);
  {
    const options = await screen.findAllByText("方案设计");
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
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheets() });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: buildDemandSheetDetail() });
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
