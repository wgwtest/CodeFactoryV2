import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const SAMPLE_APPLICATION_NAME = "基于地理信息系统的通视分析软件";
const SAMPLE_REQUIREMENT_SPEC_ID = "spec-gis-los-analysis-001";
const SAMPLE_BASELINE_ID = "baseline-gis-los-analysis-001";
const SAMPLE_DESIGN_NOTES = "基于地理信息系统的通视分析软件冻结设计样例";
const SAMPLE_SUPPLY_SNAPSHOT_NAME = "通视分析软件供给样例快照";
const SAMPLE_SUPPLY_NOTES = "供通视分析软件样例命中使用";

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

function buildDesignInputs() {
  return [
    {
      design_input_id: "design-input-1",
      source_kind: "xx_p3_doc_sim",
      source_ref_id: "xx/P3/DOC/sim:design-input-1",
      p3_order_id: null,
      application_name: SAMPLE_APPLICATION_NAME,
      requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
      baseline_id: SAMPLE_BASELINE_ID,
      notes: SAMPLE_DESIGN_NOTES,
      module_count: 3,
      module_names: ["构建工作台", "构建运行监控", "缺口回流"],
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
  ];
}

function buildSupplyInputs() {
  return [
    {
      supply_input_id: "supply-input-1",
      source_kind: "xx_p4_supply_sim",
      source_ref_id: "xx/P4/sim:supply-input-1",
      snapshot_name: SAMPLE_SUPPLY_SNAPSHOT_NAME,
      notes: SAMPLE_SUPPLY_NOTES,
      tool_count: 2,
      tool_names: ["UI Shell", "Runtime Board"],
      tools: [
        {
          tool_id: "tool-ui-shell",
          tool_name: "UI Shell",
          tool_slug: "ui-shell",
          verification_status: "verified",
          keywords: ["ui_shell", "workspace", "frontend"],
        },
        {
          tool_id: "tool-runtime-board",
          tool_name: "Runtime Board",
          tool_slug: "runtime-board",
          verification_status: "verified",
          keywords: ["runtime_board", "log"],
        },
      ],
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
  ];
}

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
        source_kind: "xx_p3_doc_sim",
        design_input_id: "design-input-1",
        order_id: "xx/P3/DOC/sim:design-input-1",
        baseline_id: SAMPLE_BASELINE_ID,
        module_count: 3,
        module_names: ["构建工作台", "构建运行监控", "缺口回流"],
      },
      supply_input: {
        source_kind: "xx_p4_supply_sim",
        supply_input_id: "supply-input-1",
        tool_count: 2,
        tool_names: ["UI Shell", "Runtime Board"],
        matched_tool_count: 2,
      },
    },
    assembly_plan: {
      modules: [
        {
          module_id: "module-workspace",
          name: "构建工作台",
          objective: "渲染 P5 工作台前端。",
          target_directories: ["frontend", "backend", "docs"],
          binding_status: "bound",
          binding_source: "heuristic",
          bound_tool_id: "tool-ui-shell",
          bound_tool_name: "UI Shell",
          gap_reason: null,
        },
        {
          module_id: "module-runtime",
          name: "构建运行监控",
          objective: "渲染运行态与日志。",
          target_directories: ["frontend", "backend", "docs"],
          binding_status: "bound",
          binding_source: "manual",
          bound_tool_id: "tool-runtime-board",
          bound_tool_name: "Runtime Board",
          gap_reason: null,
        },
        {
          module_id: "module-feedback",
          name: "缺口回流",
          objective: "沉淀反馈任务。",
          target_directories: ["frontend", "backend", "docs"],
          binding_status: "placeholder",
          binding_source: "empty",
          bound_tool_id: null,
          bound_tool_name: null,
          gap_reason: "未命中当前供给快照资产，当前按缺口占位继续导出。",
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
          detail: "已冻结当前设计输入与供给输入快照。",
        },
        {
          stage_id: "projection",
          label: "装配投影",
          status: "warning",
          detail: "已绑定 2 个模块，保留 1 个占位模块。",
        },
      ],
      recent_logs: [
        {
          timestamp: "2026-04-20T00:00:00Z",
          level: "info",
          message: "p5-order-1 已接收当前输入绑定快照。",
        },
        {
          timestamp: "2026-04-20T00:01:00Z",
          level: "warning",
          message: "发现 1 个供给缺口，已按占位目录继续导出。",
        },
      ],
      block_reason: "缺口回流 未命中已供给资产",
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
        module_id: "module-feedback",
        module_name: "缺口回流",
        summary: "缺口回流 未命中已供给资产",
        detail: "当前模块没有绑定到 P4 已审定 / 已供给资产。",
      },
    ],
    feedback_tasks: [
      {
        task_id: "feedback-1",
        gap_id: "gap-1",
        kind: "supply_gap",
        title: "回流确认：缺口回流 未命中已供给资产",
        detail: "当前模块没有绑定到 P4 已审定 / 已供给资产。默认回流到 P3 仲裁。",
        status: "pending_confirmation",
        reviewed_by: null,
        reviewed_at: null,
        review_note: null,
      },
    ],
    export_directory: "/tmp/exports/p5-order-1/attempt-001",
    created_at: "2026-04-20T00:01:00Z",
    updated_at: "2026-04-20T00:01:00Z",
  };
}

function buildOrderDetail() {
  return {
    delivery_order_id: "p5-order-1",
    p3_order_id: "xx/P3/DOC/sim:design-input-1",
    requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
    application_name: SAMPLE_APPLICATION_NAME,
    requested_by: "P5",
    notes: "首轮组装",
    status: "exported_with_gaps",
    current_attempt_count: 1,
    formal_result_ready: false,
    active_input_binding: {
      binding_id: "binding-1",
      delivery_order_id: "p5-order-1",
      design_input_id: "design-input-1",
      supply_input_id: "supply-input-1",
      supply_mode: "snapshot",
      module_bindings: [
        {
          module_id: "module-runtime",
          tool_id: "tool-runtime-board",
          tool_name: "Runtime Board",
          source: "manual",
          updated_by: "p5-workbench",
          updated_at: "2026-04-20T00:00:00Z",
        },
      ],
      is_confirmed: true,
      confirmed_by: "p5-workbench",
      confirmed_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
    created_at: "2026-04-20T00:00:00Z",
    updated_at: "2026-04-20T00:01:00Z",
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
                p3_order_id: "xx/P3/DOC/sim:design-input-1",
                application_name: SAMPLE_APPLICATION_NAME,
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-20T00:01:00Z",
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
                p3_order_id: "xx/P3/DOC/sim:design-input-1",
                application_name: SAMPLE_APPLICATION_NAME,
                status: "exported_with_gaps",
                current_attempt_count: 1,
                updated_at: "2026-04-20T00:01:00Z",
              },
            ],
          },
        },
      });
    }

    if (url === "/software-build/design-inputs") {
      return Promise.resolve({ data: { data: { items: buildDesignInputs() } } });
    }

    if (url === "/software-build/supply-inputs") {
      return Promise.resolve({ data: { data: { items: buildSupplyInputs() } } });
    }

    if (url === "/software-build/orders/p5-order-1") {
      return Promise.resolve({ data: buildOrderDetail() });
    }

    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/orders/p5-order-1/binding/confirm") {
      return Promise.resolve({ data: buildOrderDetail().active_input_binding });
    }

    if (url === "/software-build/orders/p5-order-1/attempts") {
      return Promise.resolve({ data: buildAttempt(2) });
    }

    if (url === "/software-build/orders/p5-order-1/attempts/attempt-1/feedback-tasks/feedback-1/review") {
      return Promise.resolve({
        data: {
          ...buildAttempt().feedback_tasks[0],
          status: "confirmed",
          reviewed_by: "p5-workbench",
          reviewed_at: "2026-04-20T00:02:00Z",
          review_note: "工作台确认进入回流队列",
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

test("renders the approved p5 workbench and wires binding and review actions", async () => {
  installLoadedWorkspaceMocks();

  render(
    <MemoryRouter initialEntries={["/build"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(await screen.findByText("交付主单队列")).toBeInTheDocument();
  expect(await screen.findByText("输入绑定与确认")).toBeInTheDocument();
  expect(await screen.findByText("装配流程主视图")).toBeInTheDocument();
  expect(await screen.findByText("构建运行与监控")).toBeInTheDocument();
  expect(await screen.findByText("输出结果预览")).toBeInTheDocument();
  expect(await screen.findByText("缺口与反馈")).toBeInTheDocument();
  expect(await screen.findByText("P3 文档模拟输出台")).toBeInTheDocument();
  expect(await screen.findByText("P4 供给模拟输出台")).toBeInTheDocument();
  expect(await screen.findByText("UI Shell")).toBeInTheDocument();
  expect(await screen.findByText("Runtime Board")).toBeInTheDocument();
  expect(await screen.findByText("build-manifest.json")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "确认当前输入绑定" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/orders/p5-order-1/binding/confirm",
      expect.objectContaining({
        design_input_id: "design-input-1",
        supply_input_id: "supply-input-1",
        supply_mode: "snapshot",
      }),
    ),
  );

  fireEvent.click(screen.getByRole("button", { name: "发起构建尝试" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/orders/p5-order-1/attempts",
      expect.objectContaining({
        build_profile: "baseline",
      }),
    ),
  );

  fireEvent.click(screen.getByRole("button", { name: "确认反馈任务" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/orders/p5-order-1/attempts/attempt-1/feedback-tasks/feedback-1/review",
      expect.objectContaining({
        decision: "confirmed",
      }),
    ),
  );
});

test("bootstraps the demo loop from the empty workspace state", async () => {
  let mode: "empty" | "loaded" = "empty";
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics:
              mode === "empty"
                ? {
                    order_count: 0,
                    draft_count: 0,
                    exported_with_gaps_count: 0,
                    completed_count: 0,
                    failed_count: 0,
                  }
                : {
                    order_count: 1,
                    draft_count: 0,
                    exported_with_gaps_count: 1,
                    completed_count: 0,
                    failed_count: 0,
                  },
            recent_orders: mode === "empty" ? [] : installLoadedOverview().recent_orders,
          },
        },
      });
    }

    if (url === "/software-build/orders") {
      return Promise.resolve({
        data: {
          data: {
            items:
              mode === "empty"
                ? []
                : [
                    {
                      delivery_order_id: "p5-order-1",
                      p3_order_id: "xx/P3/DOC/sim:design-input-1",
                      application_name: SAMPLE_APPLICATION_NAME,
                      status: "exported_with_gaps",
                      current_attempt_count: 1,
                      updated_at: "2026-04-20T00:01:00Z",
                    },
                  ],
          },
        },
      });
    }

    if (url === "/software-build/design-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: mode === "empty" ? [] : buildDesignInputs(),
          },
        },
      });
    }

    if (url === "/software-build/supply-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: mode === "empty" ? [] : buildSupplyInputs(),
          },
        },
      });
    }

    if (url === "/software-build/orders/p5-order-1") {
      return Promise.resolve({ data: buildOrderDetail() });
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

  expect(await screen.findByText("当前暂无 P5 交付主单。")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "装载演示闭环" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/workspace/bootstrap-demo",
      expect.objectContaining({
        build_profile: "demo",
      }),
    ),
  );

  expect(await screen.findByText("已装载 P5.1 演示闭环输入。")).toBeInTheDocument();
  expect((await screen.findAllByText(SAMPLE_APPLICATION_NAME)).length).toBeGreaterThan(0);
});

test("clears current p5 deliveries and returns the workspace to the empty state", async () => {
  let mode: "loaded" | "cleared" = "loaded";
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics:
              mode === "loaded"
                ? {
                    order_count: 1,
                    draft_count: 0,
                    exported_with_gaps_count: 1,
                    completed_count: 0,
                    failed_count: 0,
                  }
                : {
                    order_count: 0,
                    draft_count: 0,
                    exported_with_gaps_count: 0,
                    completed_count: 0,
                    failed_count: 0,
                  },
            recent_orders: mode === "loaded" ? installLoadedOverview().recent_orders : [],
          },
        },
      });
    }

    if (url === "/software-build/orders") {
      return Promise.resolve({
        data: {
          data: {
            items:
              mode === "loaded"
                ? [
                    {
                      delivery_order_id: "p5-order-1",
                      p3_order_id: "xx/P3/DOC/sim:design-input-1",
                      application_name: SAMPLE_APPLICATION_NAME,
                      status: "exported_with_gaps",
                      current_attempt_count: 1,
                      updated_at: "2026-04-20T00:01:00Z",
                    },
                  ]
                : [],
          },
        },
      });
    }

    if (url === "/software-build/design-inputs") {
      return Promise.resolve({ data: { data: { items: buildDesignInputs() } } });
    }

    if (url === "/software-build/supply-inputs") {
      return Promise.resolve({ data: { data: { items: buildSupplyInputs() } } });
    }

    if (url === "/software-build/orders/p5-order-1" && mode === "loaded") {
      return Promise.resolve({ data: buildOrderDetail() });
    }

    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/testing/clear-deliveries") {
      mode = "cleared";
      return Promise.resolve({
        data: {
          cleared_order_count: 1,
          cleared_attempt_count: 1,
          cleared_export_directory_count: 1,
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

  expect((await screen.findAllByText(SAMPLE_APPLICATION_NAME)).length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "清空当前 P5 交付" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "清空当前 P5 交付" }));

  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-build/testing/clear-deliveries"));
  expect(await screen.findByText("当前暂无 P5 交付主单。")).toBeInTheDocument();
  expect(screen.queryByText("基于地理信息系统的通视分析软件")).not.toBeInTheDocument();
});

function installLoadedOverview() {
  return {
    recent_orders: [
      {
        delivery_order_id: "p5-order-1",
        p3_order_id: "xx/P3/DOC/sim:design-input-1",
        application_name: SAMPLE_APPLICATION_NAME,
        status: "exported_with_gaps",
        current_attempt_count: 1,
        updated_at: "2026-04-20T00:01:00Z",
      },
    ],
  };
}
