import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";
import type { ToolDemandItem, ToolDemandSheet } from "../lib/api";

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();
const putMock = vi.fn();
const deleteMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
    put: (...args: unknown[]) => putMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
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

function buildTools() {
  return {
    items: [
      {
        tool_id: "tool-blue-force-tree-builder",
        name: "蓝军编组树构造器",
        slug: "blue-force-tree-builder",
        status: "active",
        summary: "根据兵力定义生成蓝军编组树",
        problem_statement: "支撑蓝军编组设计阶段的工具匹配",
        primary_domain_id: "simulated_blue_force",
        tool_form_id: "skill",
        runtime_platform_ids: ["agent_runtime"],
        tags: ["domain:simulated_blue_force", "form:skill", "runtime:agent_runtime", "lifecycle:solution_design"],
        lifecycle_stage_ids: ["solution_design"],
        input_types: ["force_definition"],
        output_types: ["force_tree"],
        supported_sources: ["manual_input"],
        usage_notes: "命中模拟蓝军编组树生成场景",
        keywords: ["蓝军", "编组", "树"],
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

function buildPendingDemandItem(): ToolDemandItem {
  return {
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
    recommendation_type: "existing_tool",
    recommendation_summary: "建议直接交付现有工具：蓝军编组树构造器（匹配得分 85）。",
    recommended_tool_id: "tool-blue-force-tree-builder",
    recommended_tool_name: "蓝军编组树构造器",
    review_status: "pending_review",
    importance_score: null,
    urgency_score: null,
    rationality_verdict: "",
    review_comment: "",
    reviewed_by: null,
    reviewed_at: null,
    processing_status: "matched_existing",
    analysis_result: "已受理组件需求：模拟蓝军系统 / 蓝军编组 / 兵力结构编组 / 编制树生成 / 蓝军编组树构造器",
    check_result: "树型层级校验通过，组件叶子项结构完整。",
    match_result: "命中现有工具：蓝军编组树构造器（得分 85），待人工审定。",
    supply_result: null,
    submitted_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
  };
}

function buildApprovedDemandItem(): ToolDemandItem {
  return {
    ...buildPendingDemandItem(),
    review_status: "approved_delivery",
    importance_score: 5,
    urgency_score: 4,
    rationality_verdict: "合理",
    review_comment: "已有合适工具，直接交付。",
    reviewed_by: "p4-reviewer",
    reviewed_at: "2026-04-16T10:00:00Z",
    supply_result: {
      result_type: "existing_tool",
      item_id: "tdi-001",
      tool_ref: "tool-blue-force-tree-builder",
      fetch_interface: {
        tool_id: "tool-blue-force-tree-builder",
        tool_name: "蓝军编组树构造器",
        tool_version: "v1",
        tool_form_id: "skill",
        runtime_platform_ids: ["agent_runtime"],
        fetch_mode: "descriptor",
        entrypoint_type: "http",
        entrypoint_locator: "/api/tool-hub/tools/tool-blue-force-tree-builder/fetch",
        contract_version: "p4.fetch.v1",
        updated_at: "2026-04-15T08:00:00Z",
      },
      progress_query_interface: null,
      estimated_ready_at: null,
      suggested_poll_after_seconds: null,
      available_at: "2026-04-16T10:00:00Z",
      last_message: "已批准直接交付现有工具：蓝军编组树构造器",
    },
  };
}

function buildPendingDemandSheetDetail(overrides: Partial<ToolDemandSheet> = {}): ToolDemandSheet {
  return {
    sheet_id: "tds-001",
    sheet_name: "模拟蓝军一期工具需求单",
    lifecycle_status: "accepted",
    review_status: "pending_review",
    delivery_status: "not_delivered",
    processing_status: "processing",
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
    pending_review_count: 1,
    approved_delivery_count: 0,
    approved_manufacture_count: 0,
    rejected_item_count: 0,
    matched_existing_count: 1,
    manufacturing_count: 0,
    ready_for_fetch_count: 0,
    failed_count: 0,
    items: [buildPendingDemandItem()],
    lifecycle_events: [],
    submitted_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
    ...overrides,
  };
}

function buildApprovedDemandSheetDetail(): ToolDemandSheet {
  return buildPendingDemandSheetDetail({
    review_status: "reviewed",
    delivery_status: "delivered",
    processing_status: "ready",
    pending_review_count: 0,
    approved_delivery_count: 1,
    ready_for_fetch_count: 1,
    items: [buildApprovedDemandItem()],
  });
}

function buildDemandSheetSummaries(pendingDetail: ToolDemandSheet, approvedDetail: ToolDemandSheet) {
  return {
    items: [
      { ...pendingDetail, items: undefined },
      { ...approvedDetail, items: undefined, sheet_id: "tds-002", sheet_name: "模拟蓝军二期工具需求单" },
    ],
  };
}

function buildOverview(recentDemandSheets: unknown[]) {
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
      ],
      rows: [
        {
          row_id: "simulated_blue_force",
          row_label: "模拟蓝军",
          cells: [
            { column_id: "skill", value: 1 },
            { column_id: "template", value: 0 },
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
    pending_suggestions: [],
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
    recent_demand_sheets: recentDemandSheets,
    catalogs: {
      domains: [
        { id: "simulated_blue_force", label: "模拟蓝军", description: "" },
        { id: "workflow_approval", label: "审批流转", description: "" },
      ],
      lifecycle_stages: [{ id: "solution_design", label: "方案设计", description: "" }],
      tool_forms: [
        { id: "skill", label: "Skill", description: "" },
        { id: "service_endpoint", label: "服务接口", description: "" },
      ],
      runtime_platforms: [{ id: "agent_runtime", label: "Agent 运行时", description: "" }],
      input_types: [{ id: "force_definition", label: "兵力定义", description: "" }],
      output_types: [{ id: "force_tree", label: "兵力树", description: "" }],
      supported_sources: [{ id: "manual_input", label: "人工输入", description: "" }],
      verification_statuses: [{ id: "verified", label: "已验证", description: "" }],
      tag_namespaces: [{ id: "domain", label: "业务域标签", description: "" }],
    },
  };
}

function buildManufacturePlans() {
  return {
    items: [
      {
        plan_id: "tmp-001",
        item_id: "tdi-003",
        sheet_id: "tds-003",
        component_name: "蓝军战术推演器",
        planned_tool_name: "蓝军战术推演器",
        status: "manufacturing_in_progress",
        progress_percent: 62,
        simulation_profile: "normal",
        target_duration_seconds: 18,
        estimated_ready_at: "2026-04-16T10:18:00Z",
        started_at: "2026-04-16T10:00:00Z",
        completed_at: null,
        last_progress_message: "模拟研制进行中，已完成 62%。",
      },
    ],
  };
}

function buildEvolutionConfig() {
  return {
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
  };
}

function buildEvolutionRuns() {
  return {
    items: [
      {
        run_id: "evolution-2",
        status: "completed",
        trigger_type: "manual",
        triggered_by: "p4-workspace",
        created_at: "2026-04-15T11:05:00Z",
        updated_at: "2026-04-15T11:05:00Z",
        started_at: "2026-04-15T11:05:00Z",
        completed_at: "2026-04-15T11:05:00Z",
        failed_at: null,
        snapshot_id: "snapshot-1",
        error_message: "",
        summary: {
          tool_count: 1,
          finding_count: 1,
          missing_description_count: 1,
          taxonomy_issue_count: 0,
          overlap_risk_count: 0,
          coverage_gap_count: 0,
          accepted_count: 0,
          ignored_count: 0,
          generated_task_count: 0,
        },
        findings: [
          {
            finding_id: "finding-1",
            run_id: "evolution-2",
            kind: "missing_description",
            title: "案例标签修复器描述缺失",
            description: "工具摘要或问题定义为空，影响匹配和验证解释。",
            severity: "warning",
            tool_ids: ["tool-case-tag-fixer"],
            evidence: {},
            decision_status: "pending",
            decision_by: null,
            decision_at: null,
            decision_note: "",
            linked_task_id: null,
            updated_at: "2026-04-15T11:05:00Z",
          },
        ],
      },
    ],
  };
}

function buildEvolutionTasks() {
  return {
    items: [
      {
        task_id: "evolution-task-1",
        source_run_id: "evolution-1",
        source_finding_id: "finding-legacy",
        task_type: "auto_apply",
        task_status: "completed",
        priority: "medium",
        planned_action: "normalize_metadata",
        target_tool_ids: ["tool-blue-force-tree-builder"],
        result_summary: "已自动改写 1 个工具定义。",
        change_count: 1,
        rollback_available: true,
        created_by: "p4-workspace",
        created_at: "2026-04-15T09:30:00Z",
        started_at: "2026-04-15T09:31:00Z",
        completed_at: "2026-04-15T09:32:00Z",
        updated_at: "2026-04-15T09:32:00Z",
      },
    ],
  };
}

function buildEvolutionReadResponse(url: string) {
  if (url === "/tool-hub/evolution/config") {
    return Promise.resolve({ data: buildReadEnvelope(buildEvolutionConfig()) });
  }
  if (url === "/tool-hub/evolution/runs") {
    return Promise.resolve({ data: buildReadEnvelope(buildEvolutionRuns()) });
  }
  if (url === "/tool-hub/evolution/tasks") {
    return Promise.resolve({ data: buildReadEnvelope(buildEvolutionTasks()) });
  }
  return null;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  putMock.mockReset();
  deleteMock.mockReset();
});

test("renders XX-P4 review-first input chain and can approve an existing tool demand item", async () => {
  let cleared = false;
  let pendingDetail: ToolDemandSheet = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools()) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({
        data: cleared ? { items: [] } : buildDemandSheetSummaries(pendingDetail, approvedDetail),
      });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
    }
    if (url === "/tool-hub/demand-sheets/tds-002") {
      return Promise.resolve({ data: approvedDetail });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/tool-hub/demand-items/tdi-001/review") {
      const payload = body as Record<string, unknown>;
      pendingDetail = buildApprovedDemandSheetDetail();
      return Promise.resolve({
        data: {
          ...buildApprovedDemandItem(),
          importance_score: payload.importance_score,
          urgency_score: payload.urgency_score,
          rationality_verdict: payload.rationality_verdict,
          review_comment: payload.review_comment,
          reviewed_by: payload.reviewed_by,
        },
      });
    }
    if (url === "/tool-hub/demand-sheets/tds-001/reject") {
      pendingDetail = {
        ...pendingDetail,
        lifecycle_status: "rejected",
        terminal_reason_code: "manual_reject",
        terminal_reason_message: "P4 工作台人工驳回当前工单。",
        lifecycle_events: [
          {
            event_id: "evt-1",
            event_type: "rejected",
            actor_phase: "P4",
            actor_id: "p4-workspace",
            from_status: "accepted",
            to_status: "rejected",
            reason_code: "manual_reject",
            reason_message: "P4 工作台人工驳回当前工单。",
            occurred_at: "2026-04-16T10:00:00Z",
          },
        ],
      };
      return Promise.resolve({ data: pendingDetail });
    }
    if (url === "/tool-hub/testing/clear-demand-sheets") {
      cleared = true;
      return Promise.resolve({
        data: {
          cleared_sheet_count: 2,
          cleared_item_count: 2,
          cleared_manufacture_plan_count: 0,
        },
      });
    }
    if (url === "/tool-hub/evolution/runs") {
      return Promise.resolve({
        data: {
          run_id: "evolution-2",
          status: "completed",
          trigger_type: "manual",
          triggered_by: "p4-workspace",
          created_at: "2026-04-15T11:05:00Z",
          updated_at: "2026-04-15T11:05:00Z",
          started_at: "2026-04-15T11:05:00Z",
          completed_at: "2026-04-15T11:05:00Z",
          failed_at: null,
          snapshot_id: "snapshot-1",
          error_message: "",
          summary: {
            tool_count: 1,
            finding_count: 1,
            missing_description_count: 0,
            taxonomy_issue_count: 0,
            overlap_risk_count: 1,
            coverage_gap_count: 0,
            accepted_count: 0,
            ignored_count: 0,
            generated_task_count: 0,
          },
          findings: [
            {
              finding_id: "finding-1",
              run_id: "evolution-2",
              kind: "overlap_risk",
              title: "审批规则校验器与审批路径解释器疑似重叠",
              description: "两者在业务域、生命周期和输入上存在高相似度。",
              severity: "warning",
              tool_ids: ["tool-approval-rule-validator", "tool-approval-path-explainer"],
              evidence: {},
              decision_status: "pending",
              decision_by: null,
              decision_at: null,
              decision_note: "",
              linked_task_id: null,
              updated_at: "2026-04-15T11:05:00Z",
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
  expect(screen.queryByText(/当前知识库：/)).not.toBeInTheDocument();
  expect(screen.queryByText(/待演进建议：/)).not.toBeInTheDocument();
  expect(screen.queryByText(/最近成功率：/)).not.toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "输入工序链" })).toBeInTheDocument();
  expect(document.querySelectorAll('#xx-p4-workspace-nav [data-nav-variant="segmented"]').length).toBe(4);

  fireEvent.click(screen.getByRole("tab", { name: "输入工序链" }));
  expect(await screen.findByText("工序单受理区")).toBeInTheDocument();
  expect(screen.getByText("工具需求列表")).toBeInTheDocument();
  expect(screen.getByText("需求审批与处置面板")).toBeInTheDocument();
  expect(screen.queryByText("总单树审查区")).not.toBeInTheDocument();
  expect(screen.queryByText("供给结果输出区")).not.toBeInTheDocument();
  expect(document.querySelector("#xx-p4-review-panel")).toHaveTextContent(
    "建议直接交付现有工具：蓝军编组树构造器（匹配得分 85）。",
  );

  fireEvent.change(screen.getByLabelText("重要性评分"), { target: { value: "5" } });
  fireEvent.change(screen.getByLabelText("紧急性评分"), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("合理性判断"), { target: { value: "合理" } });
  fireEvent.change(screen.getByLabelText("审定备注"), { target: { value: "已有合适工具，直接交付。" } });
  fireEvent.click(screen.getByRole("button", { name: "批准并直接交付" }));

  expect(postMock).toHaveBeenCalledWith(
    "/tool-hub/demand-items/tdi-001/review",
    expect.objectContaining({
      decision: "approve_delivery",
      importance_score: 5,
      urgency_score: 4,
      rationality_verdict: "合理",
      review_comment: "已有合适工具，直接交付。",
    }),
  );
  await waitFor(() => {
    expect(document.querySelector("#xx-p4-review-panel")).toHaveTextContent("approved_delivery");
  });
  await waitFor(() => {
    expect(document.querySelector("#xx-p4-review-supply-result")).toHaveTextContent(
      "/api/tool-hub/tools/tool-blue-force-tree-builder/fetch",
    );
  });

  fireEvent.click(screen.getByRole("button", { name: "驳回当前工单" }));
  await waitFor(() => {
    expect(document.querySelector("#xx-p4-demand-sheet-intake-card")).toHaveTextContent("rejected");
  });
  expect(postMock).toHaveBeenCalledWith(
    "/tool-hub/demand-sheets/tds-001/reject",
    expect.objectContaining({
      actor_id: "p4-workspace",
      reason_code: "manual_reject",
    }),
  );

  fireEvent.click(screen.getByRole("button", { name: "测试一键清理全部工单" }));
  expect(postMock).toHaveBeenCalledWith("/tool-hub/testing/clear-demand-sheets");
  expect(await screen.findByText("当前没有工具需求单")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "自演进巡检" }));
  fireEvent.click(await screen.findByRole("button", { name: "触发巡检" }));
  expect((await screen.findAllByText("案例标签修复器描述缺失")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("业务域 × 工具形态")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-registry-coverage-matrix")).toBeInTheDocument();
});

test("creates a tool from registry workspace", async () => {
  let tools = buildTools();
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(tools) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
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

test("renders evolution workspace as decoupled cards", async () => {
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools()) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({
        data: buildReadEnvelope({
          items: [
            {
              run_id: "evolution-2",
              status: "completed",
              created_at: "2026-04-15T11:05:00Z",
              summary: {
                tool_count: 1,
                finding_count: 1,
                missing_description_count: 1,
                taxonomy_issue_count: 0,
                overlap_risk_count: 0,
                coverage_gap_count: 0,
              },
              findings: [
                {
                  finding_id: "finding-1",
                  kind: "missing_description",
                  title: "案例标签修复器描述缺失",
                  description: "工具摘要或问题定义为空，影响匹配和验证解释。",
                  severity: "warning",
                  tool_ids: ["tool-case-tag-fixer"],
                },
              ],
            },
          ],
        }),
      });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/evolution/runs") {
      return Promise.resolve({
        data: {
          run_id: "evolution-3",
          status: "completed",
          trigger_type: "manual",
          triggered_by: "p4-workspace",
          created_at: "2026-04-16T11:05:00Z",
          updated_at: "2026-04-16T11:05:00Z",
          started_at: "2026-04-16T11:05:00Z",
          completed_at: "2026-04-16T11:05:00Z",
          failed_at: null,
          snapshot_id: "snapshot-1",
          error_message: "",
          summary: {
            tool_count: 1,
            finding_count: 1,
            missing_description_count: 1,
            taxonomy_issue_count: 0,
            overlap_risk_count: 0,
            coverage_gap_count: 0,
            accepted_count: 0,
            ignored_count: 0,
            generated_task_count: 0,
          },
          findings: [],
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

  fireEvent.click(await screen.findByRole("tab", { name: "自演进巡检" }));

  expect(document.querySelector("#xx-p4-evolution-config-card")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-evolution-run-list-card")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-evolution-summary-card")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-evolution-findings-card")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-evolution-task-queue-card")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-evolution-completed-card")).toBeInTheDocument();
});

test("removes a single tool from registry workspace", async () => {
  let tools = buildTools();
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(tools) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  deleteMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/tools/tool-blue-force-tree-builder") {
      tools = { items: [] };
      return Promise.resolve({
        data: {
          removed_tool_id: "tool-blue-force-tree-builder",
          remaining_tool_count: 0,
        },
      });
    }
    throw new Error(`unexpected delete url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  fireEvent.click(await screen.findByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("蓝军编组树构造器")).toBeInTheDocument();

  fireEvent.click(screen.getByLabelText("移除工具 蓝军编组树构造器"));

  expect(deleteMock).toHaveBeenCalledWith("/tool-hub/tools/tool-blue-force-tree-builder");
  await waitFor(() => {
    expect(screen.queryByText("蓝军编组树构造器")).not.toBeInTheDocument();
  });
});

test("clears all tools from registry workspace for testing", async () => {
  let tools = buildTools();
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(tools) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/testing/clear-tools") {
      tools = { items: [] };
      return Promise.resolve({
        data: {
          cleared_tool_count: 1,
          cleared_match_run_count: 0,
          cleared_evolution_run_count: 0,
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

  fireEvent.click(await screen.findByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("蓝军编组树构造器")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "测试清空全部工具" }));

  expect(postMock).toHaveBeenCalledWith("/tool-hub/testing/clear-tools");
  await waitFor(() => {
    expect(screen.queryByText("蓝军编组树构造器")).not.toBeInTheDocument();
  });
});

test("shows simulated manufacture queue in registry workspace", async () => {
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools()) });
    }
    const evolutionResponse = buildEvolutionReadResponse(url);
    if (evolutionResponse) {
      return evolutionResponse;
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }) });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: buildManufacturePlans() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p4"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  fireEvent.click(await screen.findByRole("tab", { name: "工具仓库" }));
  expect(await screen.findByText("模拟研制队列")).toBeInTheDocument();
  expect(document.querySelector("#xx-p4-registry-manufacture-queue")).toHaveTextContent("蓝军战术推演器");
  expect(document.querySelector("#xx-p4-registry-manufacture-queue")).toHaveTextContent("manufacturing_in_progress");
  expect(getMock).toHaveBeenCalledWith("/tool-hub/manufacture-plans");
});

test("shows snapshot consistency warning when tool hub read models are out of sync", async () => {
  const pendingDetail = buildPendingDemandSheetDetail();
  const approvedDetail = {
    ...buildApprovedDemandSheetDetail(),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/overview") {
      return Promise.resolve({
        data: buildReadEnvelope(
          buildOverview(buildDemandSheetSummaries(pendingDetail, approvedDetail).items),
          "snapshot-overview",
        ),
      });
    }
    if (url === "/tool-hub/tools") {
      return Promise.resolve({ data: buildReadEnvelope(buildTools(), "snapshot-tools") });
    }
    if (url === "/tool-hub/evolution/config") {
      return Promise.resolve({ data: buildReadEnvelope(buildEvolutionConfig(), "snapshot-tools") });
    }
    if (url === "/tool-hub/evolution/runs") {
      return Promise.resolve({ data: buildReadEnvelope(buildEvolutionRuns(), "snapshot-tools") });
    }
    if (url === "/tool-hub/evolution/tasks") {
      return Promise.resolve({ data: buildReadEnvelope(buildEvolutionTasks(), "snapshot-tools") });
    }
    if (url === "/tool-hub/evolution-runs") {
      return Promise.resolve({ data: buildReadEnvelope({ items: [] }, "snapshot-tools") });
    }
    if (url === "/tool-hub/manufacture-plans") {
      return Promise.resolve({ data: { items: [] } });
    }
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildDemandSheetSummaries(pendingDetail, approvedDetail) });
    }
    if (url === "/tool-hub/demand-sheets/tds-001") {
      return Promise.resolve({ data: pendingDetail });
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
