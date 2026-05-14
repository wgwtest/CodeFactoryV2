import "@testing-library/jest-dom/vitest";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";

const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  postMock.mockReset();
  postMock.mockResolvedValue({
    data: {
      scenario: {
        scenario_id: "simulator-latest",
        label: "合同模拟器",
        description: "由 P6 合同模拟器发送的五阶段展示输出合同。",
        source_mode: "mock",
        recommended_focus_stage: "P3",
      },
      accepted_contract_count: 5,
      portal_projection_path: "/portal?scenario=simulator-latest",
      portal_data_path: "/portal-data?scenario=simulator-latest",
    },
  });
});

test("renders the P6 contract simulator and submits five display contracts", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p6-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P6 合同模拟器")).toBeInTheDocument();
  expect(screen.getByText("P6DisplayExportContract.v2")).toBeInTheDocument();
  expect(screen.getByText("业务知识库")).toBeInTheDocument();
  expect(screen.getByText("交付目录")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "发送模拟合同" }));

  await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1));

  const [url, payload] = postMock.mock.calls[0] as [string, { contracts: Array<Record<string, unknown>> }];
  expect(url).toBe("/p6/simulator/contracts");
  expect(payload.contracts).toHaveLength(5);
  expect(payload.contracts.every((item) => item.contract_version === "P6DisplayExportContract.v2")).toBe(true);

  const p1Contract = payload.contracts.find((item) => {
    const overview = item.stage_overview as { stage_id: string };
    return overview.stage_id === "P1";
  }) as {
    flow_ports: Array<{ direction: string; connected_target: string; label: string }>;
    system_overall_metrics: Array<{ key: string }>;
  };
  const p3Contract = payload.contracts.find((item) => {
    const overview = item.stage_overview as { stage_id: string };
    return overview.stage_id === "P3";
  }) as { flow_ports: Array<{ direction: string; connected_target: string; label: string }> };
  const p5Contract = payload.contracts.find((item) => {
    const overview = item.stage_overview as { stage_id: string };
    return overview.stage_id === "P5";
  }) as { flow_ports: Array<{ direction: string; connected_target: string; terminal: boolean }> };

  expect(p1Contract.flow_ports.filter((port) => port.direction === "output")).toEqual([
    expect.objectContaining({ connected_target: "P2" }),
  ]);
  expect(p1Contract.flow_ports.filter((port) => port.direction === "input")).toEqual([]);
  expect((p1Contract as unknown as { entry_projection: { entry_route: string } }).entry_projection.entry_route).toBe("/p1");
  expect(p1Contract.system_overall_metrics.map((metric) => metric.key)).toEqual([
    "knowledge_repository_count",
    "published_knowledge_count",
    "domain_directory_count",
    "contributor_count",
  ]);
  expect(p3Contract.flow_ports.filter((port) => port.direction === "output")).toEqual([
    expect.objectContaining({ connected_target: "P4", label: "模块工单包" }),
    expect.objectContaining({ connected_target: "P5", label: "设计基线" }),
  ]);
  expect(p5Contract.flow_ports.filter((port) => port.direction === "output")).toEqual([
    expect.objectContaining({ connected_target: "交付目录", terminal: true }),
  ]);
  const p2Contract = payload.contracts.find((item) => {
    const overview = item.stage_overview as { stage_id: string };
    return overview.stage_id === "P2";
  }) as { queue_projection: { label: string; items: Array<{ label: string }> } };
  const p4Contract = payload.contracts.find((item) => {
    const overview = item.stage_overview as { stage_id: string };
    return overview.stage_id === "P4";
  }) as { queue_projection: { label: string; items: Array<{ label: string }> } };

  expect(p2Contract.queue_projection.label).toBe("需规发布队列");
  expect(p2Contract.queue_projection.items.map((item) => item.label)).toEqual([
    "需求规格说明对象",
    "组织器配置",
    "发布到 P3",
  ]);
  expect(p4Contract.queue_projection.label).toBe("工具工单处理队列");
  expect(p4Contract.queue_projection.items.map((item) => item.label)).toEqual([
    "工单处理",
    "工具构建",
    "取用驾驶舱",
    "覆盖知识图谱",
  ]);

  expect(await screen.findByText("已发送 5 个阶段合同")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "打开 P6 门户" })).toHaveAttribute(
    "href",
    "/portal?scenario=simulator-latest",
  );
  expect(screen.getByRole("link", { name: "打开图表视图" })).toHaveAttribute(
    "href",
    "/portal-data?scenario=simulator-latest",
  );
});
