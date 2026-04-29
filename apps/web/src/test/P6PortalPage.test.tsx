import { readFileSync } from "node:fs";
import "@testing-library/jest-dom/vitest";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { P6_PORTAL_LAYOUT_STORAGE_KEY } from "../components/p6/p6PortalData";
import {
  buildDisplayBaseline,
  buildPlatformLegend,
  buildPlatformRoutes,
  buildPortalProjectionEnvelope,
  buildScenarioCatalog,
  buildWorkbenchBootstrap,
} from "./p6TestData";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  window.localStorage.clear();
  getMock.mockReset();
  postMock.mockReset();

  getMock.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/p6/mock-scenarios") {
      return Promise.resolve({ data: buildScenarioCatalog() });
    }

    if (url === "/p6/portal-projection") {
      return Promise.resolve({ data: buildPortalProjectionEnvelope(config?.params?.scenario ?? "baseline") });
    }

    if (url === "/platform-config/display-baseline") {
      return Promise.resolve({ data: buildDisplayBaseline() });
    }

    if (url === "/platform-config/routes") {
      return Promise.resolve({ data: buildPlatformRoutes() });
    }

    if (url === "/platform-config/legend") {
      return Promise.resolve({ data: buildPlatformLegend() });
    }

    if (url === "/platform-display/workbench") {
      return Promise.resolve({ data: buildWorkbenchBootstrap() });
    }

    if (url === "/platform-display/experiments") {
      return Promise.resolve({ data: { items: buildWorkbenchBootstrap().experiments } });
    }

    if (url === "/platform-display/promotion-candidates") {
      return Promise.resolve({ data: { items: buildWorkbenchBootstrap().promotion_candidates } });
    }

    if (url === "/software-build/overview") {
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

    if (url === "/software-build/orders" || url === "/software-build/design-inputs" || url === "/software-build/supply-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: [],
          },
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/platform-display/experiments") {
      return Promise.resolve({
        data: {
          experiment_id: "exp-0002",
          goal: "验证 P5 卡片在观察页中的告警优先展示。",
          projection_scope: "PortalProjection",
          template_refs: ["template-module-compact"],
          binding_refs: ["binding-observation-alert"],
          layout_refs: ["layout-compare"],
          preset_refs: [],
          result_summary: "P5 阻塞态在观察页中更易被识别。",
          issues: ["P4 与 P5 的视觉区分还需要增强。"],
          promotion_recommendation: "candidate",
          target_stage_ids: ["P4", "P5"],
          evidence_refs: ["portal:delivery-gap"],
          created_at: "2026-04-21T10:28:00Z",
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });
});

test("renders P6 portal blueprint outside MainShell on /portal route and loads formal config dependencies", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("图例")).toBeInTheDocument();
  expect(screen.getByText("模拟源")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "基线通畅" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.getByTestId("p6-portal-legend")).toBeInTheDocument();
  expect(screen.getByText("统一登录接入")).toBeInTheDocument();
  expect(screen.getByText("权限与角色控制")).toBeInTheDocument();
  expect(screen.getByText(/双击节点即可进入对应模块/)).toBeInTheDocument();
  expect(screen.getByText("NAS 战术知识库 v3")).toBeInTheDocument();

  expect(getMock).toHaveBeenCalledWith("/p6/mock-scenarios");
  expect(getMock).toHaveBeenCalledWith("/platform-config/display-baseline");
  expect(getMock).toHaveBeenCalledWith("/platform-config/routes");
  expect(getMock).toHaveBeenCalledWith("/platform-config/legend");
  expect(getMock).toHaveBeenCalledWith(
    "/p6/portal-projection",
    expect.objectContaining({
      params: expect.objectContaining({ source: "mock", scenario: "baseline" }),
    }),
  );
});

test("legend styles anchor it to the portal bottom-right corner", () => {
  const css = readFileSync("src/pages/P6PortalPage.css", "utf8");

  expect(css).toMatch(/\.p6-blueprint-legend\s*\{[^}]*position:\s*absolute;/s);
  expect(css).toMatch(/\.p6-blueprint-legend\s*\{[^}]*right:\s*26px;/s);
  expect(css).toMatch(/\.p6-blueprint-legend\s*\{[^}]*bottom:\s*24px;/s);
});

test("switching scenario reloads projection with the selected mock source", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("交付主单 DO-240421-01")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "交付缺口" }));

  expect(await screen.findByText("交付主单 DO-240421-04")).toBeInTheDocument();
  expect(screen.getByText("需人工确认缺口与回补路径。")).toBeInTheDocument();

  await waitFor(() =>
    expect(getMock).toHaveBeenCalledWith(
      "/p6/portal-projection",
      expect.objectContaining({
        params: expect.objectContaining({ source: "mock", scenario: "delivery-gap" }),
      }),
    ),
  );
});

test("renders distinct portal element types and a visible world boundary", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByTestId("p6-portal-node-user")).toHaveAttribute("data-node-kind", "user");
  expect(screen.getByTestId("p6-portal-node-p1")).toHaveAttribute("data-node-kind", "module");

  const artifact = screen.getByTestId("p6-portal-artifact-spec");
  expect(artifact).toHaveAttribute("data-artifact-kind", "artifact");
  expect(artifact).toHaveTextContent("自动投影");

  expect(screen.getByTestId("p6-portal-world-boundary")).toHaveTextContent("自动布局区");
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

test("switches between recommended layout and personal layout", async () => {
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

  fireEvent.click(screen.getByRole("button", { name: "推荐布局" }));
  expect(node).toHaveStyle({ left: "400px", top: "660px" });

  fireEvent.click(screen.getByRole("button", { name: "个人布局" }));
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

test("switches relationship view from semantic wires to projection aggregation", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByTestId("p6-flow-label-p2-p3")).toBeInTheDocument();
  expect(screen.queryByTestId("p6-node-relations-p3")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "投影聚合" }));

  expect(screen.queryByTestId("p6-flow-label-p2-p3")).not.toBeInTheDocument();
  expect(screen.getByTestId("p6-node-relations-p3")).toHaveTextContent(/入1/);
  expect(screen.getByTestId("p6-node-relations-p3")).toHaveTextContent(/出2/);
  expect(screen.getByTestId("p6-node-relations-p3")).toHaveTextContent(/产物3/);
});

test("double clicking a module navigates to its target workspace through route config", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const node = await screen.findByRole("button", { name: /软件构建系统/i });
  fireEvent.doubleClick(node);

  expect(await screen.findByText("软件构建系统")).toBeInTheDocument();
  expect(await screen.findByText("交付主单队列")).toBeInTheDocument();
});

test("opens the P6.4 card configurator from the portal and shows backend-driven experiment content", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("button", { name: "卡片配置" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "卡片配置" }));

  expect(await screen.findByText("模板选择区")).toBeInTheDocument();
  expect(screen.getByTestId("p6-experiment-workbench")).toBeInTheDocument();
  expect(screen.getByText("绑定配置区")).toBeInTheDocument();
  expect(screen.getByText("布局组合区")).toBeInTheDocument();
  expect(screen.getByText("实时预览区")).toBeInTheDocument();
  expect(screen.getByText("实验记录区")).toBeInTheDocument();
  expect(screen.getByText("晋升评估区")).toBeInTheDocument();
  expect(screen.getByText("系统状态卡适合门户首屏，能够稳定承载阶段识别、摘要和健康状态。")).toBeInTheDocument();
  expect(screen.getByText("门户系统状态卡已经具备可复用的模板、绑定和布局组合。")).toBeInTheDocument();

  expect(getMock).toHaveBeenCalledWith("/platform-display/workbench");
});

test("applies card style selectively to the chosen node and can save an experiment record", async () => {
  render(
    <MemoryRouter initialEntries={["/portal"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("button", { name: "卡片配置" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "卡片配置" }));
  await screen.findByTestId("p6-experiment-workbench");

  fireEvent.change(screen.getByLabelText("配置对象"), { target: { value: "p5" } });
  fireEvent.click(screen.getByRole("button", { name: /压缩/ }));

  expect(screen.getByTestId("p6-portal-node-p5")).toHaveAttribute("data-card-template", "template-module-compact");
  expect(screen.getByTestId("p6-portal-node-p2")).toHaveAttribute("data-card-template", "template-module-status");

  fireEvent.click(screen.getByRole("button", { name: /进入候选/ }));
  fireEvent.click(screen.getByRole("button", { name: "登记实验" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/platform-display/experiments",
      expect.objectContaining({
        goal: expect.any(String),
        projection_scope: "PortalProjection",
        target_stage_ids: expect.arrayContaining(["P4", "P5"]),
      }),
    ),
  );
});
