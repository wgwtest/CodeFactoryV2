import "@testing-library/jest-dom/vitest";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import {
  buildDisplayBaseline,
  buildObservationProjectionEnvelope,
  buildPlatformRoutes,
  buildScenarioCatalog,
} from "./p6TestData";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  getMock.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/p6/mock-scenarios") {
      return Promise.resolve({ data: buildScenarioCatalog() });
    }

    if (url === "/p6/observation-projection") {
      return Promise.resolve({ data: buildObservationProjectionEnvelope(config?.params?.scenario ?? "baseline") });
    }

    if (url === "/platform-config/display-baseline") {
      return Promise.resolve({ data: buildDisplayBaseline() });
    }

    if (url === "/platform-config/routes") {
      return Promise.resolve({ data: buildPlatformRoutes() });
    }

    throw new Error(`unexpected url: ${url}`);
  });
});

test("renders the observation page outside MainShell and shows the required consumption blocks", async () => {
  render(
    <MemoryRouter initialEntries={["/observation"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P6 串行观察页")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.getByText("平台总览条")).toBeInTheDocument();
  expect(screen.getByText("阶段告警区")).toBeInTheDocument();
  expect(screen.getByText("降级说明区")).toBeInTheDocument();
  expect(screen.getByText("跨阶段对比区")).toBeInTheDocument();
  expect(screen.getByTestId("p6-observation-stage-card-P2")).toBeInTheDocument();
  expect(screen.getByText("可用入口")).toBeInTheDocument();
  expect(screen.getByText("进入 软件设计系统")).toBeInTheDocument();

  expect(getMock).toHaveBeenCalledWith("/p6/mock-scenarios");
  expect(getMock).toHaveBeenCalledWith("/platform-config/display-baseline");
  expect(getMock).toHaveBeenCalledWith("/platform-config/routes");
  expect(getMock).toHaveBeenCalledWith(
    "/p6/observation-projection",
    expect.objectContaining({
      params: expect.objectContaining({ source: "mock", scenario: "baseline" }),
    }),
  );
});

test("switches focus stage and scenario in the observation page", async () => {
  render(
    <MemoryRouter initialEntries={["/observation"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("支持软件 24 个，需求规格 86 份，业务对象 430 个")).toBeInTheDocument();
  expect(screen.getByTestId("p6-observation-stage-card-P2")).toHaveAttribute("data-active", "true");

  fireEvent.click(screen.getByRole("button", { name: "交付缺口" }));

  expect(await screen.findByText("目录输出受阻，需人工确认缺口与回补路径。")).toBeInTheDocument();
  expect(screen.getByText("需人工确认缺口与回补路径。")).toBeInTheDocument();

  fireEvent.click(screen.getByTestId("p6-observation-stage-card-P5"));

  expect(screen.getByTestId("p6-observation-stage-card-P5")).toHaveAttribute("data-active", "true");

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith(
      "/p6/observation-projection",
      expect.objectContaining({
        params: expect.objectContaining({ source: "mock", scenario: "delivery-gap" }),
      }),
    ),
  );
});
