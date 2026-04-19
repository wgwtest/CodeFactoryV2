import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

function buildAttempt(sequence = 1) {
  return {
    attempt_id: `attempt-${sequence}`,
    delivery_order_id: "p5-order-1",
    sequence,
    export_config: {
      export_root: "/tmp/exports",
      build_profile: "baseline",
      attempt_note: `attempt-${sequence}`,
    },
    input_snapshot: {
      design_input: {
        source_kind: "demo_p3_baseline",
        order_id: "p3-order-demo-001",
        baseline_id: "baseline-p5-demo-001",
        module_count: 2,
        module_names: ["构建任务编排", "构建缺口回流"],
      },
      supply_input: {
        source_kind: "demo_p4_supply",
        tool_count: 1,
        tool_names: ["工作流引擎"],
        matched_tool_count: 1,
      },
    },
    assembly_plan: {
      modules: [
        {
          module_id: "module-assembly-board",
          name: "构建任务编排",
          objective: "驱动主单到 attempt 的最小装配与执行流。",
          target_directories: ["frontend", "backend", "docs"],
          binding_status: "bound",
          bound_tool_id: "tool-workflow-engine",
          bound_tool_name: "工作流引擎",
          gap_reason: null,
        },
        {
          module_id: "module-gap-feedback",
          name: "构建缺口回流",
          objective: "沉淀缺口、反馈任务和回流建议。",
          target_directories: ["frontend", "backend", "docs"],
          binding_status: "placeholder",
          bound_tool_id: null,
          bound_tool_name: null,
          gap_reason: "未命中 P4 已供给资产，当前按缺口占位继续导出。",
        },
      ],
    },
    runtime_snapshot: {
      executor_name: "p5-mvp-executor",
      executor_status: "completed",
      attempt_status: "exported_with_gaps",
      progress_percent: 100,
      stages: [
        {
          stage_id: "intake",
          label: "接收输入",
          status: "completed",
          detail: "已装载冻结 P3 基线与 P4 供给快照。",
        },
        {
          stage_id: "projection",
          label: "装配投影",
          status: "warning",
          detail: "已绑定 1 个模块，保留 1 个占位模块。",
        },
      ],
      recent_logs: [
        {
          timestamp: "2026-04-19T10:00:00Z",
          level: "info",
          message: "p5-order-1 已接收 P3/P4 输入快照。",
        },
        {
          timestamp: "2026-04-19T10:01:00Z",
          level: "warning",
          message: "发现 1 个供给缺口，已按占位目录继续导出。",
        },
      ],
      block_reason: "构建缺口回流 未命中已供给资产",
    },
    validation_report: {
      module_closure_status: "warning",
      structure_status: "passed",
      build_status: "warning",
      summary: "存在缺口，占位导出已完成。",
    },
    output_preview: {
      root_directory: "/tmp/exports/p5-order-1/attempt-001",
      directories: ["frontend", "backend", "deploy", "docs"],
      key_files: [
        {
          path: "build-manifest.json",
          kind: "file",
          status: "generated",
          summary: "导出目录元数据与 attempt 快照。",
        },
        {
          path: "docs/delivery-report.md",
          kind: "file",
          status: "generated",
          summary: "说明本次交付模块投影与构建结论。",
        },
        {
          path: "docs/gap-list.md",
          kind: "file",
          status: "generated_with_gaps",
          summary: "说明当前缺口、占位模块和回流建议。",
        },
      ],
    },
    gaps: [
      {
        gap_id: "gap-1",
        kind: "supply_gap",
        module_id: "module-gap-feedback",
        module_name: "构建缺口回流",
        summary: "构建缺口回流 未命中已供给资产",
        detail: "当前模块没有绑定到 P4 已审定 / 已供给资产。",
      },
    ],
    feedback_tasks: [
      {
        task_id: "feedback-1",
        gap_id: "gap-1",
        kind: "supply_gap",
        title: "回流确认：构建缺口回流 未命中已供给资产",
        detail: "当前模块没有绑定到 P4 已审定 / 已供给资产。默认回流到 P3 仲裁。",
        status: "pending_confirmation",
      },
    ],
    export_directory: "/tmp/exports/p5-order-1/attempt-001",
    created_at: "2026-04-19T10:01:00Z",
    updated_at: "2026-04-19T10:01:00Z",
  };
}

function buildOrderDetail() {
  return {
    delivery_order_id: "p5-order-1",
    p3_order_id: "p3-order-demo-001",
    requirement_spec_id: "spec-p5-demo-001",
    application_name: "P5 最小闭环演示系统",
    requested_by: "P5",
    notes: "首轮组装",
    status: "exported_with_gaps",
    current_attempt_count: 1,
    formal_result_ready: false,
    created_at: "2026-04-19T10:00:00Z",
    updated_at: "2026-04-19T10:01:00Z",
    attempts: [buildAttempt()],
  };
}

function installLoadedWorkspaceMocks() {
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 1,
              draft_count: 0,
              exported_with_gaps_count: 1,
              completed_count: 0,
              failed_count: 0,
            },
            recent_orders: [
              {
                delivery_order_id: "p5-order-1",
                p3_order_id: "p3-order-demo-001",
                application_name: "P5 最小闭环演示系统",
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-19T10:01:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-build/orders") {
      return Promise.resolve({
        data: {
          data: {
            items: [
              {
                delivery_order_id: "p5-order-1",
                p3_order_id: "p3-order-demo-001",
                application_name: "P5 最小闭环演示系统",
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-19T10:01:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-build/orders/p5-order-1") {
      return Promise.resolve({
        data: buildOrderDetail(),
      });
    }

    throw new Error(`unexpected get url: ${url}`);
  });
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

test("renders P5 workspace outside MainShell with the full MVP zones", async () => {
  installLoadedWorkspaceMocks();

  render(
    <MemoryRouter initialEntries={["/build"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(await screen.findByText("交付主单队列")).toBeInTheDocument();
  expect(await screen.findByText("联调输入快照")).toBeInTheDocument();
  expect(await screen.findByText("装配流程主视图")).toBeInTheDocument();
  expect(await screen.findByText("构建运行与监控")).toBeInTheDocument();
  expect(await screen.findByText("输出结果预览")).toBeInTheDocument();
  expect(await screen.findByText("缺口与反馈")).toBeInTheDocument();
  expect((await screen.findAllByText("P5 最小闭环演示系统")).length).toBeGreaterThan(0);
  expect(await screen.findByText("工作流引擎")).toBeInTheDocument();
  expect(await screen.findByText("p5-mvp-executor")).toBeInTheDocument();
  expect(await screen.findByText("build-manifest.json")).toBeInTheDocument();
});

test("bootstraps the demo loop from the empty workspace state", async () => {
  let mode: "empty" | "loaded" = "empty";
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/overview") {
      if (mode === "empty") {
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

      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 1,
              draft_count: 0,
              exported_with_gaps_count: 1,
              completed_count: 0,
              failed_count: 0,
            },
            recent_orders: [
              {
                delivery_order_id: "p5-order-1",
                p3_order_id: "p3-order-demo-001",
                application_name: "P5 最小闭环演示系统",
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-19T10:01:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-build/orders") {
      if (mode === "empty") {
        return Promise.resolve({
          data: {
            data: {
              items: [],
            },
          },
        });
      }

      return Promise.resolve({
        data: {
          data: {
            items: [
              {
                delivery_order_id: "p5-order-1",
                p3_order_id: "p3-order-demo-001",
                application_name: "P5 最小闭环演示系统",
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-19T10:01:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-build/orders/p5-order-1") {
      return Promise.resolve({
        data: buildOrderDetail(),
      });
    }

    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/workspace/bootstrap-demo") {
      mode = "loaded";
      return Promise.resolve({
        data: {
          delivery_order_id: "p5-order-1",
          attempt_id: "attempt-1",
          created_demo_inputs: true,
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/build"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  fireEvent.click(await screen.findByRole("button", { name: "装载演示闭环" }));

  await waitFor(() => {
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/workspace/bootstrap-demo",
      expect.objectContaining({
        build_profile: "demo",
      }),
    );
  });
  expect((await screen.findAllByText("P5 最小闭环演示系统")).length).toBeGreaterThan(0);
  expect((await screen.findAllByText("最近尝试 attempt-001")).length).toBeGreaterThan(0);
});
