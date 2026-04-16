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

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

test("renders P3 simulator, creates a mock demand sheet, and renders P5 simulator route", async () => {
  postMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/mock-generators/blue-force-demand-sheets") {
      return Promise.resolve({
        data: {
          sheet_id: "tds-001",
          sheet_name: "模拟蓝军一期工具需求单",
          status: "accepted",
          business_case: "simulated_blue_force",
          item_ids: ["tdi-001"],
          item_count: 1,
          matched_existing_count: 0,
          manufacturing_count: 1,
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
              match_result: "未命中现有工具",
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
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p3-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 模拟发生器")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "生成模拟蓝军需求总单" }));
  expect(await screen.findByText("模拟蓝军一期工具需求单")).toBeInTheDocument();
  expect(await screen.findByText("tds-001")).toBeInTheDocument();

  render(
    <MemoryRouter initialEntries={["/xx-p5-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P5 模拟消费器")).toBeInTheDocument();
  expect(screen.getByText("整单查询")).toBeInTheDocument();
  expect(screen.getByText("叶子项进度")).toBeInTheDocument();
});
