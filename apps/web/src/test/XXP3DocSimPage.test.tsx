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
  let designItems: Array<Record<string, unknown>> = [];
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockImplementation((url: string) => {
    if (url === "/software-build/design-inputs") {
      return Promise.resolve({
        data: {
          data: {
            items: designItems,
          },
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-build/design-inputs/sim") {
      designItems = [
        {
          design_input_id: "design-input-1",
          source_kind: "xx_p3_doc_sim",
          source_ref_id: "xx/P3/DOC/sim:design-input-1",
          p3_order_id: null,
          application_name: SAMPLE_APPLICATION_NAME,
          requirement_spec_id: SAMPLE_REQUIREMENT_SPEC_ID,
          baseline_id: SAMPLE_BASELINE_ID,
          notes: SAMPLE_DESIGN_NOTES,
          module_count: 3,
          module_names: ["构建工作台", "构建运行监控", "缺口回流"],
          created_at: "2026-04-20T00:00:00Z",
          updated_at: "2026-04-20T00:00:00Z",
        },
      ];
      return Promise.resolve({
        data: {
          design_input_id: "design-input-1",
          application_name: SAMPLE_APPLICATION_NAME,
        },
      });
    }
    throw new Error(`unexpected post url: ${url}`);
  });
});

test("renders the xx-p3-doc-sim page and only creates a simulated design input on the same page", async () => {
  render(
    <MemoryRouter initialEntries={["/xx-p3-doc-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 文档模拟输出台")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成设计模拟输出" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-build/design-inputs/sim",
      expect.objectContaining({
        application_name: SAMPLE_APPLICATION_NAME,
      }),
    ),
  );

  expect(postMock).not.toHaveBeenCalledWith("/software-build/orders", expect.anything());
  expect(await screen.findByText("已生成设计模拟输出 design-input-1")).toBeInTheDocument();
  expect(await screen.findByText(SAMPLE_APPLICATION_NAME)).toBeInTheDocument();
  expect(screen.getByText("P3 文档模拟输出台")).toBeInTheDocument();
});
