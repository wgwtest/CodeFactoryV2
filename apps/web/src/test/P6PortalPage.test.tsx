import "@testing-library/jest-dom/vitest";
import { beforeEach, expect, test } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { P6_PORTAL_LAYOUT_STORAGE_KEY } from "../components/p6/p6PortalData";

beforeEach(() => {
  window.localStorage.clear();
});

test("renders P6 portal blueprint outside MainShell on /portal route", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P6.1 门户蓝图画布")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.queryByText("固定五阶段蓝图")).not.toBeInTheDocument();
  expect(screen.getByTestId("p6-portal-legend")).toBeInTheDocument();
  expect(screen.getByText("P6.2 登录接入")).toBeInTheDocument();
  expect(screen.getByText("P6.3 权限与角色控制")).toBeInTheDocument();
});

test("clicking a module only highlights it and does not open a summary popup", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const node = await screen.findByRole("button", { name: /业务知识库/i });
  fireEvent.click(node);

  expect(screen.queryByText("模块作用")).not.toBeInTheDocument();
  expect(node).toHaveAttribute("data-active", "true");
});

test("restores saved blueprint node layout from localStorage", async () => {
  window.localStorage.setItem(
    P6_PORTAL_LAYOUT_STORAGE_KEY,
    JSON.stringify({
      p1: { x: 520, y: 600 },
    }),
  );

  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const node = await screen.findByTestId("p6-portal-node-p1");
  expect(node).toHaveStyle({ left: "520px", top: "600px" });
});

test("persists blueprint node layout after dragging", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const node = await screen.findByTestId("p6-portal-node-p1");
  fireEvent.mouseDown(node, { button: 0, clientX: 420, clientY: 540 });
  fireEvent.mouseMove(window, { clientX: 500, clientY: 620 });
  fireEvent.mouseUp(window);

  const savedLayout = JSON.parse(window.localStorage.getItem(P6_PORTAL_LAYOUT_STORAGE_KEY) ?? "{}") as {
    p1?: { x: number; y: number };
  };

  expect(savedLayout.p1).toBeDefined();
  expect(savedLayout.p1?.x).toBeGreaterThan(420);
  expect(savedLayout.p1?.y).toBeGreaterThan(540);
});

test("double clicking a module navigates to its target workspace", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const node = await screen.findByRole("button", { name: /软件构建系统/i });
  fireEvent.doubleClick(node);

  expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
  expect(await screen.findByText(/当前入口已可从门户页进入/)).toBeInTheDocument();
});
