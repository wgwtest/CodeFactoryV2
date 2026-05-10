import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

test("renders P3 Design Lab using only P2 frozen packages and generates design baseline", async () => {
  const inputPackage = buildInputPackage();
  const createdSession = buildSession(inputPackage, "created");
  const generatedSession = buildSession(inputPackage, "baseline_ready");

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions") {
      return Promise.resolve({ data: createdSession });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/generate") {
      return Promise.resolve({ data: generatedSession });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Design Lab")).toBeInTheDocument();
  expect(screen.getByText("只消费 P2 新版冻结包，不兼容旧规格池")).toBeInTheDocument();
  expect(screen.getByTestId("stage-document-workbench")).toHaveAttribute("data-stage", "P3");
  const requirementPane = screen.getByTestId("p3-design-lab-requirement-pane");
  const designPane = screen.getByTestId("p3-design-lab-design-pane");
  expect(requirementPane).toBeInTheDocument();
  expect(screen.getByTestId("p3-design-lab-cli-pane")).toBeInTheDocument();
  expect(designPane).toBeInTheDocument();
  expect(within(requirementPane).getByRole("heading", { name: "空域协同规划软件需求规格说明" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成设计基线" }));

  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions", expect.any(Object)));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/generate"));
  expect(await screen.findByText("空域协同规划软件设计说明")).toBeInTheDocument();
  expect(within(designPane).getByRole("tab", { name: "正文" })).toBeInTheDocument();
  expect(within(designPane).getByRole("tab", { name: "目录" })).toBeInTheDocument();
  expect(within(designPane).getByRole("tab", { name: "检查" })).toBeInTheDocument();
  expect(within(designPane).getByRole("tab", { name: "投影" })).toBeInTheDocument();
  expect(within(designPane).getByTestId("document-body-panel")).toBeInTheDocument();
  expect(within(designPane).getByLabelText("A4 软件设计说明预览")).toBeInTheDocument();
  expect(within(designPane).getAllByText("SoftwareDesignBaseline v2")).toHaveLength(2);
  fireEvent.click(within(designPane).getByRole("tab", { name: "目录" }));
  expect(within(designPane).getByTestId("document-outline-panel")).toBeInTheDocument();
  expect(within(designPane).getByText("规划任务管理")).toBeInTheDocument();
  fireEvent.click(within(designPane).getByRole("tab", { name: "检查" }));
  expect(within(designPane).getByTestId("quality-check-panel")).toBeInTheDocument();
  expect(within(designPane).getByText("尚未运行设计完整性检查")).toBeInTheDocument();
  fireEvent.click(within(designPane).getByRole("tab", { name: "投影" }));
  expect(within(designPane).getByTestId("stage-projection-panel")).toBeInTheDocument();
  expect(screen.getByText("规划任务管理模块实现")).toBeInTheDocument();
});

function buildInputPackage() {
  return {
    input_package_id: "p2frozen-doc-1",
    source_document_id: "doc-1",
    source_title: "空域协同规划软件需求规格说明",
    p3_consumable: true,
    frozen_at: "2026-05-01T00:00:00Z",
    standard_document: {
      title: "空域协同规划软件需求规格说明",
      sections: [
        {
          section_id: "3",
          title: "3 功能需求",
          clauses: [
            {
              clause_id: "REQ-3.2",
              title: "核心业务流程",
              content: "系统应支持创建规划任务、识别冲突、协同确认、形成处置记录。",
            },
          ],
        },
      ],
    },
    structured_spec: {
      application: { name: "空域协同规划软件" },
    },
    annotations: [],
    knowledge_binding: null,
  };
}

function buildSession(inputPackage: ReturnType<typeof buildInputPackage>, status: string) {
  return {
    session_id: "p3dl-1",
    input_package: inputPackage,
    status,
    generation_policy: {
      architecture_preference: "统一服务优先，保留拆分点",
      module_granularity: "3-5 个业务模块，不拆太细",
      output_style: "按标准软设正文写，不写聊天语气",
    },
    design_document:
      status === "created"
        ? null
        : {
            title: "空域协同规划软件设计说明",
            sections: [{ section_id: "goal", title: "1. 设计目标与范围", content: "覆盖协同规划核心能力。" }],
          },
    design_baseline:
      status === "created"
        ? null
        : {
            baseline_id: "sdb2-1",
            architecture_mode: "unified_service",
            modules: [{ module_id: "planning-task", name: "规划任务管理" }],
          },
    workorder_projection:
      status === "created"
        ? null
        : {
            items: [{ item_id: "wo-1", title: "规划任务管理模块实现" }],
          },
    turns: [],
    check_result: null,
  };
}
