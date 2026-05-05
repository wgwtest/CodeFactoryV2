import "@testing-library/jest-dom/vitest";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { buildPortalDataViewEnvelope } from "./p6TestData";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  getMock.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/p6/portal-data") {
      return Promise.resolve({
        data: buildPortalDataViewEnvelope({
          history: config?.params?.scenario === "simulator-latest",
          selectedStageId: config?.params?.selected_stage_id ?? "P3",
        }),
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });
});

test("renders five-stage portal data table and empty simulator-history chart state", async () => {
  render(
    <MemoryRouter initialEntries={["/portal-data?scenario=baseline"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "五阶段同源数据精确观察" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "返回语义画布" })).toHaveAttribute("href", "/portal?scenario=baseline");
  expect(screen.getByRole("link", { name: "模拟发生器" })).toHaveAttribute("href", "/xx-p6-sim");

  ["P1", "P2", "P3", "P4", "P5"].forEach((stageId) => {
    expect(screen.getByRole("row", { name: new RegExp(stageId) })).toBeInTheDocument();
  });
  expect(screen.getByText("P3 下钻区")).toBeInTheDocument();
  expect(screen.getByText("暂无历史样本")).toBeInTheDocument();
  expect(screen.getByText("P3 -> P5")).toBeInTheDocument();

  expect(getMock).toHaveBeenCalledWith(
    "/p6/portal-data",
    expect.objectContaining({
      params: expect.objectContaining({ source: "mock", scenario: "baseline", selected_stage_id: "P3" }),
    }),
  );
});

test("renders simulator history points and refetches drilldown when a stage row is selected", async () => {
  render(
    <MemoryRouter
      initialEntries={["/portal-data?scenario=simulator-latest"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "五阶段同源数据精确观察" })).toBeInTheDocument();
  expect(screen.getByText("发布态知识")).toBeInTheDocument();
  expect(screen.getByText("5 条/小时")).toBeInTheDocument();
  expect(screen.queryByText("暂无历史样本")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("row", { name: /P5/ }));

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith(
      "/p6/portal-data",
      expect.objectContaining({
        params: expect.objectContaining({ source: "mock", scenario: "simulator-latest", selected_stage_id: "P5" }),
      }),
    ),
  );
  expect(await screen.findByText("P5 下钻区")).toBeInTheDocument();
});
