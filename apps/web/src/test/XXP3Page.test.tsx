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

test("renders XX-P3 cockpit route and drives order review workflow", async () => {
  getMock.mockImplementation((url: string) => {
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
    if (url === "/software-design/orders/p3-order-1") {
      return Promise.resolve({
        data: {
          order_id: "p3-order-1",
          requirement_spec_summary: {
            application_name: "空域协同规划软件",
            domain_name: "国家空域管理",
            status: "ready",
          },
          status: "draft_ready",
          design_description: {
            sections: [{ id: "goal", title: "1. 设计目标与范围", summary: "..." }],
          },
          review_threads: [],
          workorder_batch: null,
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url.endsWith("/approve")) {
      return Promise.resolve({ data: { status: "approved_for_generation" } });
    }
    if (url.endsWith("/generate-draft")) {
      return Promise.resolve({ data: { status: "draft_ready" } });
    }
    if (url.endsWith("/freeze")) {
      return Promise.resolve({ data: { status: "frozen" } });
    }
    if (url.endsWith("/workorder-batch")) {
      return Promise.resolve({
        data: {
          package_overview: {
            architecture_recommendation: "unified_service",
            interaction_mode: "bs",
          },
          items: [{ item_id: "item-1", title: "规划任务管理模块实现" }],
        },
      });
    }
    if (url.endsWith("/push-to-p4")) {
      return Promise.resolve({ data: { push_status: "pushed" } });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("XX-P3")).toBeInTheDocument();
  expect(screen.getByText("软件设计编制与模块工单下发系统")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "审批通过" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "设计编制" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "审批通过" }));
  fireEvent.click(screen.getByRole("button", { name: "生成软设草案" }));
  fireEvent.click(screen.getByRole("tab", { name: "模块工单包" }));
  fireEvent.click(screen.getByRole("button", { name: "生成批次工单包" }));

  expect(await screen.findByText("规划任务管理模块实现")).toBeInTheDocument();
  expect(screen.getByText("unified_service")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "推送到 P4" }));
  expect(postMock).toHaveBeenCalledWith("/software-design/orders/p3-order-1/push-to-p4");
});
