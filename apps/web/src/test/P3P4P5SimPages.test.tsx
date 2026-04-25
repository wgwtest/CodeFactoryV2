import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

function buildPendingSheet(sheetId: string) {
  return {
    sheet_id: sheetId,
    sheet_name: "模拟蓝军一期工具需求单",
    lifecycle_status: "accepted",
    review_status: "pending_review",
    delivery_status: "not_delivered",
    processing_status: "processing",
    business_case: "simulated_blue_force",
    item_ids: ["tdi-001"],
    item_count: 1,
    pending_review_count: 1,
    approved_delivery_count: 0,
    approved_manufacture_count: 0,
    rejected_item_count: 0,
    matched_existing_count: 0,
    manufacturing_count: 0,
    ready_for_fetch_count: 0,
    failed_count: 0,
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
    items: [
      {
        item_id: "tdi-001",
        sheet_id: sheetId,
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
        recommendation_type: "manufacture_candidate",
        recommendation_summary: "当前未命中现有工具，建议审定通过后进入研制名单。",
        recommended_tool_id: null,
        recommended_tool_name: null,
        review_status: "pending_review",
        importance_score: null,
        urgency_score: null,
        rationality_verdict: "",
        review_comment: "",
        reviewed_by: null,
        reviewed_at: null,
        processing_status: "checking",
        analysis_result: "已受理组件需求",
        check_result: "树型层级校验通过",
        match_result: "未命中现有工具，当前仅生成进入研制的推荐结论，待人工审定。",
        supply_result: null,
        submitted_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    ],
    lifecycle_events: [],
    submitted_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
  };
}

function buildNavigationPlanningSheet(sheetId: string) {
  return {
    ...buildPendingSheet(sheetId),
    sheet_id: sheetId,
    sheet_name: "导航规划一期工具需求单",
    business_case: "navigation_planning",
    source: {
      phase: "p3_simulator",
      producer: "mock_navigation_planning_generator",
      business_case: "navigation_planning",
      scenario_id: "navigation-planning-sim-001",
      scenario_name: "导航规划协同推演一期",
    },
    root_node: {
      node_id: "sys-navigation-planning",
      node_type: "system",
      node_name: "导航规划系统",
      node_code: "SYS-NAVIGATION-PLANNING",
      business_domain_id: "navigation_planning",
      children: [],
    },
    items: [
      {
        ...buildPendingSheet(sheetId).items[0],
        item_id: "tdi-nav-001",
        sheet_id: sheetId,
        source_node_id: "component-route-plan-compiler",
        ancestry: ["导航规划系统", "航路设计", "路径规划", "航路装配", "航路规划编译器"],
        business_domain_id: "navigation_planning",
        component_name: "航路规划编译器",
        component_code: "COMP-ROUTE-PLAN-COMPILER",
        problem_statement: "根据任务区域和约束条件生成可执行航路方案。",
        required_input_types: ["manual_text"],
        expected_output_types: ["structured_json"],
        keywords: ["导航", "航路", "规划"],
        acceptance_notes: "输出航路方案与关键约束解释。",
      },
    ],
  };
}

function buildDeliveredSheet() {
  return {
    ...buildPendingSheet("tds-002"),
    sheet_id: "tds-002",
    sheet_name: "模拟蓝军二期工具需求单",
    review_status: "reviewed",
    delivery_status: "delivered",
    pending_review_count: 0,
    approved_delivery_count: 1,
    matched_existing_count: 1,
    ready_for_fetch_count: 1,
    items: [
      {
        ...buildPendingSheet("tds-002").items[0],
        item_id: "tdi-002",
        sheet_id: "tds-002",
        recommendation_type: "existing_tool",
        recommendation_summary: "建议直接交付现有工具：蓝军编组树构造器（匹配得分 85）。",
        recommended_tool_id: "tool-blue-force-tree-builder",
        recommended_tool_name: "蓝军编组树构造器",
        review_status: "approved_delivery",
        importance_score: 5,
        urgency_score: 4,
        rationality_verdict: "合理",
        review_comment: "已有合适工具，直接交付。",
        reviewed_by: "p4-reviewer",
        reviewed_at: "2026-04-16T10:00:00Z",
        processing_status: "matched_existing",
        match_result: "命中现有工具：蓝军编组树构造器（得分 85），待人工审定。",
        supply_result: {
          result_type: "existing_tool",
          item_id: "tdi-002",
          tool_ref: "tool-blue-force-tree-builder",
          fetch_interface: {
            tool_id: "tool-blue-force-tree-builder",
            tool_name: "蓝军编组树构造器",
            tool_version: "v1",
            tool_form_id: "skill",
            packaging_type: "descriptor_only",
            integration_mode: "manual",
            dependency_policy: "external",
            runtime_dependencies: [],
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
      },
    ],
  };
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

test("renders P3 simulator lifecycle actions and P5 query views with sheet statuses", async () => {
  const detailById: Record<string, Record<string, unknown>> = {
    "tds-000": buildPendingSheet("tds-000"),
    "tds-002": buildDeliveredSheet(),
  };
  let sheetOrder = ["tds-000", "tds-002"];

  function buildSheetEnvelope() {
    return {
      items: sheetOrder.map((sheetId) => {
        const detail = detailById[sheetId];
        return {
          ...detail,
          items: undefined,
        };
      }),
    };
  }

  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/demand-sheets") {
      return Promise.resolve({ data: buildSheetEnvelope() });
    }
    if (url === "/tool-hub/demand-sheets/tds-000" || url === "/tool-hub/demand-sheets/tds-001" || url === "/tool-hub/demand-sheets/tds-002") {
      const sheetId = url.split("/").at(-1) ?? "";
      return Promise.resolve({ data: detailById[sheetId] });
    }
    if (url === "/tool-hub/demand-items/tdi-002") {
      return Promise.resolve({ data: buildDeliveredSheet().items[0] });
    }
    if (url === "/tool-hub/demand-items/tdi-002/progress") {
      return Promise.resolve({
        data: {
          item_id: "tdi-002",
          sheet_id: "tds-002",
          status: "matched_existing",
          sheet_lifecycle_status: "accepted",
          sheet_review_status: "reviewed",
          sheet_delivery_status: "delivered",
          review_status: "approved_delivery",
          result_type: "existing_tool",
          progress_percent: 100,
          estimated_ready_at: null,
          suggested_poll_after_seconds: null,
          fetch_interface: buildDeliveredSheet().items[0].supply_result.fetch_interface,
          last_message: "已批准直接交付现有工具：蓝军编组树构造器",
          updated_at: "2026-04-16T10:00:00Z",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/mock-generators/demand-sheets/navigation_planning") {
      detailById["tds-001"] = buildNavigationPlanningSheet("tds-001");
      sheetOrder = ["tds-001", "tds-000", "tds-002"];
      return Promise.resolve({ data: detailById["tds-001"] });
    }
    if (url === "/tool-hub/demand-sheets/tds-000/withdraw" || url === "/tool-hub/demand-sheets/tds-001/withdraw") {
      const sheetId = url.split("/")[3];
      detailById[sheetId] = {
        ...detailById[sheetId],
        lifecycle_status: "withdrawn",
      };
      return Promise.resolve({ data: detailById[sheetId] });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p3-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 模拟发生器")).toBeInTheDocument();
  expect(await screen.findByText("模拟蓝军一期工具需求单")).toBeInTheDocument();
  expect(screen.getByText("模拟蓝军")).toBeInTheDocument();
  expect(screen.getByText("导航规划")).toBeInTheDocument();
  expect(screen.getByText("数据治理")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "查看工单 tds-000" }));
  expect(document.querySelector("#xx-p3-selected-sheet-card")).toHaveTextContent("pending_review");
  expect(document.querySelector("#xx-p3-selected-sheet-card")).toHaveTextContent("not_delivered");

  fireEvent.click(screen.getByRole("button", { name: "撤销当前工单" }));
  expect(postMock).toHaveBeenCalledWith(
    "/tool-hub/demand-sheets/tds-000/withdraw",
    expect.objectContaining({
      actor_id: "p3-sim",
      reason_code: "manual_withdraw",
    }),
  );

  fireEvent.click(screen.getByRole("radio", { name: "导航规划" }));
  fireEvent.click(screen.getByRole("button", { name: "生成模拟工单" }));
  expect(postMock).toHaveBeenCalledWith("/tool-hub/mock-generators/demand-sheets/navigation_planning");
  expect(await screen.findByText("tds-001")).toBeInTheDocument();
  expect(await screen.findByText("导航规划一期工具需求单")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "查看工单 tds-001" }));
  fireEvent.click(screen.getByRole("button", { name: "撤销当前工单" }));
  expect(postMock).toHaveBeenCalledWith(
    "/tool-hub/demand-sheets/tds-001/withdraw",
    expect.objectContaining({
      actor_id: "p3-sim",
      reason_code: "manual_withdraw",
    }),
  );
  expect(document.querySelector("#xx-p3-selected-sheet-card")).toHaveTextContent("withdrawn");

  render(
    <MemoryRouter initialEntries={["/xx-p5-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P5 模拟消费器")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("工具需求单 ID"), { target: { value: "tds-002" } });
  fireEvent.click(screen.getByRole("button", { name: "查询整单" }));
  expect(await screen.findByText("reviewed")).toBeInTheDocument();
  expect((await screen.findAllByText("delivered")).length).toBeGreaterThan(0);

  fireEvent.change(screen.getByLabelText("叶子项 ID"), { target: { value: "tdi-002" } });
  fireEvent.click(screen.getByRole("button", { name: "查询叶子项" }));
  fireEvent.click(await screen.findByRole("button", { name: /刷新进度/ }));
  expect(await screen.findByText("已批准直接交付现有工具：蓝军编组树构造器")).toBeInTheDocument();
  expect(document.querySelector("#xx-p5-progress-card")).toHaveTextContent(
    "/api/tool-hub/tools/tool-blue-force-tree-builder/fetch",
  );
});
