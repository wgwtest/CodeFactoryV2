import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

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

test("renders xx-p2-sim and submits the selected lightweight requirement template", async () => {
  postMock.mockImplementation((url: string, payload: { status: string; payload: { application: { name: string } } }) => {
    if (url === "/requirements/specs") {
      return Promise.resolve({
        data: {
          id: "spec-sim-1",
          application_name: payload.payload.application.name,
          domain_name: "流程审批",
          status: payload.status,
          archive_id: "20161116-nas",
          object_count: 3,
          formal_object_count: 0,
          temporary_object_count: 3,
          process_count: 2,
          created_at: "2026-04-17T10:00:00Z",
          updated_at: "2026-04-17T10:00:00Z",
          payload: payload.payload,
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p2-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 上游模拟输入台")).toBeInTheDocument();
  expect(screen.getByText("平台级业务系统")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /流程审批工具/ }));

  expect(await screen.findByText("研发立项审批工具")).toBeInTheDocument();
  expect(screen.getByText(/流程立项、部门会签和状态留痕/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "提交需求规格说明" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/requirements/specs",
      expect.objectContaining({
        status: "ready",
        payload: expect.objectContaining({
          application: expect.objectContaining({
            name: "研发立项审批工具",
          }),
        }),
      }),
    ),
  );

  expect(await screen.findByText("已提交需求规格说明")).toBeInTheDocument();
  expect(screen.getByText(/规格标识：spec-sim-1/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "前往 XX-P3" })).toHaveAttribute("href", "/xx-p3");
});

test("switches the selected lightweight template when the user clicks the template card content", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p2-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 上游模拟输入台")).toBeInTheDocument();
  expect(screen.getByText("空域协同指挥平台")).toBeInTheDocument();

  fireEvent.click(screen.getByText("流程审批工具"));

  expect(await screen.findByText("研发立项审批工具")).toBeInTheDocument();
  expect(screen.getByText(/流程立项、部门会签和状态留痕/)).toBeInTheDocument();

  fireEvent.click(screen.getByText("单体业务软件"));

  expect(await screen.findByText("值班排班管理软件")).toBeInTheDocument();
  expect(screen.getByText(/围绕单一业务域构造轻量需求输入/)).toBeInTheDocument();
});
