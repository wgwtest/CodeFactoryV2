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

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/design-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: [
              {
                design_input_id: "design-input-1",
                source_kind: "xx_p3_doc_sim",
                source_ref_id: "xx/P3/DOC/sim:design-input-1",
                p3_order_id: null,
                application_name: SAMPLE_APPLICATION_NAME,
                requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
                baseline_id: SAMPLE_BASELINE_ID,
                notes: SAMPLE_DESIGN_NOTES,
                module_count: 2,
                module_names: ["构建工作台", "构建运行监控"],
                created_at: "2026-04-20T00:00:00Z",
                updated_at: "2026-04-20T00:00:00Z",
              },
            ],
          },
        },
      });
    }
    if (url === "/software-build/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: 1,
              draft_count: 1,
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
            items: [
              {
                delivery_order_id: "p5-order-1",
                p3_order_id: "xx/P3/DOC/sim:design-input-1",
                application_name: SAMPLE_APPLICATION_NAME,
                status: "draft",
                current_attempt_count: 0,
                updated_at: "2026-04-20T00:00:00Z",
              },
            ],
          },
        },
      });
    }
    if (url === "/software-build/supply-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: [
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
                    keywords: ["ui_shell", "workspace"],
                  },
                  {
                    tool_id: "tool-runtime-board",
                    tool_name: "Runtime Board",
                    tool_slug: "runtime-board",
                    verification_status: "verified",
                    keywords: ["runtime_board", "monitor"],
                  },
                ],
                created_at: "2026-04-20T00:00:00Z",
                updated_at: "2026-04-20T00:00:00Z",
              },
            ],
          },
        },
      });
    }
    if (url === "/software-build/orders/p5-order-1") {
      return Promise.resolve({
        data: {
          delivery_order_id: "p5-order-1",
          p3_order_id: "xx/P3/DOC/sim:design-input-1",
          requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
          application_name: SAMPLE_APPLICATION_NAME,
          requested_by: "xx-p3-doc-sim",
          notes: "由 xx-p3-doc-sim 创建，等待 P5 输入绑定确认。",
          status: "draft",
          current_attempt_count: 0,
          formal_result_ready: false,
          active_input_binding: {
            binding_id: "binding-1",
            delivery_order_id: "p5-order-1",
            design_input_id: "design-input-1",
            supply_input_id: null,
            supply_mode: "empty",
            module_bindings: [],
            is_confirmed: false,
            confirmed_by: null,
            confirmed_at: null,
            updated_at: "2026-04-20T00:00:00Z",
          },
          attempts: [],
          created_at: "2026-04-20T00:00:00Z",
          updated_at: "2026-04-20T00:00:00Z",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/design-inputs/sim") {
      return Promise.resolve({
        data: {
          design_input_id: "design-input-1",
          application_name: SAMPLE_APPLICATION_NAME,
        },
      });
    }
    if (url === "/software-build/orders") {
      return Promise.resolve({
        data: {
          delivery_order_id: "p5-order-1",
          p3_order_id: "xx/P3/DOC/sim:design-input-1",
          requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
          application_name: SAMPLE_APPLICATION_NAME,
          requested_by: "xx-p3-doc-sim",
          notes: "由 xx-p3-doc-sim 创建，等待 P5 输入绑定确认。",
          status: "draft",
          current_attempt_count: 0,
          formal_result_ready: false,
          active_input_binding: {
            binding_id: "binding-1",
            delivery_order_id: "p5-order-1",
            design_input_id: "design-input-1",
            supply_input_id: null,
            supply_mode: "empty",
            module_bindings: [],
            is_confirmed: false,
            confirmed_by: null,
            confirmed_at: null,
            updated_at: "2026-04-20T00:00:00Z",
          },
          created_at: "2026-04-20T00:00:00Z",
          updated_at: "2026-04-20T00:00:00Z",
        },
      });
    }
    throw new Error(`unexpected post url: ${url}`);
  });
});

test("renders the xx-p3-doc-sim page, creates a simulated design input, and opens a draft P5 order", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p3-doc-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 文档模拟输出台")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成设计输出并创建 P5 主单" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/design-inputs/sim",
      expect.objectContaining({
        application_name: SAMPLE_APPLICATION_NAME,
      }),
    ),
  );

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/orders",
      expect.objectContaining({
        design_input_id: "design-input-1",
        requested_by: "xx-p3-doc-sim",
      }),
    ),
  );

  expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
});
