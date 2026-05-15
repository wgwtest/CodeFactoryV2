import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();
const deleteMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  deleteMock.mockReset();
  getMock.mockImplementation((url: string) => {
    if (url === "/platform-exchange/monitor") {
      return Promise.resolve({ data: buildMonitorSnapshot() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
});

test("renders Base Platform monitor as a read-only six-panel log console", async () => {
  render(
    <MemoryRouter initialEntries={["/base-platform-monitor"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Base Platform Monitor" })).toBeInTheDocument();
  expect(screen.getByText("基础平台全阶段监控日志台")).toBeInTheDocument();
  await waitFor(() => expect(getMock).toHaveBeenCalledWith("/platform-exchange/monitor"));

  for (const stage of ["P1", "P2", "P3", "P4", "P5"]) {
    expect(screen.getByTestId(`base-platform-stage-${stage}`)).toBeInTheDocument();
  }
  expect(screen.getByTestId("base-platform-ledger")).toBeInTheDocument();

  const p1Panel = screen.getByTestId("base-platform-stage-P1");
  const p2Panel = screen.getByTestId("base-platform-stage-P2");
  const p3Panel = screen.getByTestId("base-platform-stage-P3");
  const p4Panel = screen.getByTestId("base-platform-stage-P4");
  const p5Panel = screen.getByTestId("base-platform-stage-P5");
  const ledger = screen.getByTestId("base-platform-ledger");

  expect(within(p1Panel).getByText("暂无平台资源 / 暂无消费记录 / 未接入首版链路")).toBeInTheDocument();
  expect(within(p4Panel).getByText("暂无平台资源 / 暂无消费记录 / 未接入首版链路")).toBeInTheDocument();
  expect(within(p5Panel).getByText("暂无平台资源 / 暂无消费记录 / 未接入首版链路")).toBeInTheDocument();

  expect(within(p2Panel).getByText(/发布 requirement_spec_package/)).toBeInTheDocument();
  expect(within(p2Panel).getByText(/artifact=art-001/)).toBeInTheDocument();
  expect(within(p2Panel).getByText(/hash=abc123/)).toBeInTheDocument();

  expect(within(p3Panel).getByText(/消费 artifact=art-001/)).toBeInTheDocument();
  expect(within(p3Panel).getByText(/session=p3-session-001/)).toBeInTheDocument();
  expect(within(p3Panel).getByText(/status=accepted/)).toBeInTheDocument();

  expect(within(ledger).getByText("requirement_spec_package: 1")).toBeInTheDocument();
  expect(within(ledger).getByText("P2: 1")).toBeInTheDocument();
  expect(within(ledger).getByText("published: 1")).toBeInTheDocument();
  expect(within(ledger).getByText("P3: 1")).toBeInTheDocument();

  expect(screen.queryByRole("button", { name: /发布|撤销|保存|消费|删除|编辑/ })).not.toBeInTheDocument();
  expect(postMock).not.toHaveBeenCalled();
  expect(patchMock).not.toHaveBeenCalled();
  expect(deleteMock).not.toHaveBeenCalled();
});

function buildMonitorSnapshot() {
  return {
    stages: [
      {
        stage: "P1",
        published: [],
        consumed: [],
        empty_state: "暂无平台资源 / 暂无消费记录 / 未接入首版链路",
      },
      {
        stage: "P2",
        published: [
          {
            artifact_id: "art-001",
            artifact_type: "requirement_spec_package",
            artifact_version: "1",
            schema_version: "requirement_spec_package.v1",
            producer_stage: "P2",
            producer_ref_id: "spec-item-001",
            producer_ref_type: "RequirementSpecWorkItem",
            lifecycle_status: "published",
            payload_mode: "inline",
            payload_hash: "abc123",
            parent_artifact_ids: [],
            source_trace: { title: "空域协同规划软件需求规格说明" },
            idempotency_key: "P2:requirement_spec_package:spec-item-001:1:abc123",
            frozen_at: "2026-05-15T10:00:00Z",
            published_at: "2026-05-15T10:01:00Z",
            published_by: "system",
            created_at: "2026-05-15T10:01:00Z",
          },
        ],
        consumed: [],
        empty_state: null,
      },
      {
        stage: "P3",
        published: [],
        consumed: [
          {
            consumption_id: "con-001",
            artifact_id: "art-001",
            consumer_stage: "P3",
            consumer_ref_id: "p3-session-001",
            consumer_ref_type: "P3DesignLabSession",
            consumption_mode: "snapshot",
            accepted_schema_version: "requirement_spec_package.v1",
            result_status: "accepted",
            result_message: null,
            consumed_at: "2026-05-15T10:05:00Z",
          },
        ],
        empty_state: null,
      },
      {
        stage: "P4",
        published: [],
        consumed: [],
        empty_state: "暂无平台资源 / 暂无消费记录 / 未接入首版链路",
      },
      {
        stage: "P5",
        published: [],
        consumed: [],
        empty_state: "暂无平台资源 / 暂无消费记录 / 未接入首版链路",
      },
    ],
    base_platform: {
      artifact_totals: {
        by_type: { requirement_spec_package: 1 },
        by_producer_stage: { P2: 1 },
        by_lifecycle_status: { published: 1 },
      },
      consumption_totals: {
        by_consumer_stage: { P3: 1 },
        by_result_status: { accepted: 1 },
      },
      latest_artifacts: [],
      latest_consumptions: [],
    },
  };
}
