import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const SAMPLE_SUPPLY_SNAPSHOT_NAME = "通视分析软件供给样例快照";
const SAMPLE_SUPPLY_NOTES = "供通视分析软件样例命中使用";

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  let supplyItems: Array<Record<string, unknown>> = [];
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/supply-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: supplyItems,
          },
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/supply-inputs/sim") {
      supplyItems = [
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
      ];
      return Promise.resolve({
        data: {
          supply_input_id: "supply-input-1",
          snapshot_name: SAMPLE_SUPPLY_SNAPSHOT_NAME,
        },
      });
    }
    throw new Error(`unexpected post url: ${url}`);
  });
});

test("renders the xx-p4-supply-sim page and only creates a simulated supply snapshot on the same page", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p4-supply-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P4 供给模拟输出台")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成供给模拟输出" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/supply-inputs/sim",
      expect.objectContaining({
        snapshot_name: SAMPLE_SUPPLY_SNAPSHOT_NAME,
      }),
    ),
  );

  expect(await screen.findByText("已生成供给模拟输出 supply-input-1")).toBeInTheDocument();
  expect(await screen.findByText(SAMPLE_SUPPLY_SNAPSHOT_NAME)).toBeInTheDocument();
  expect(screen.getByText("P4 供给模拟输出台")).toBeInTheDocument();
});

test("renders the xx-p4-sim alias to the same supply simulator page", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p4-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P4 供给模拟输出台")).toBeInTheDocument();
});
