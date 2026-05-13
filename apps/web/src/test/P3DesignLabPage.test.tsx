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

test("renders P3 Design Lab as a Lab workspace with software design document, structured data, and P4 projection tree", async () => {
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

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  expect(screen.getByText("从 P2 需求规格冻结包生成软件设计说明、设计基线和 P4 投影")).toBeInTheDocument();
  const navigation = screen.getByTestId("p3-design-lab-navigation");
  expect(within(navigation).getByRole("tab", { name: /需规输入/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toHaveAttribute("aria-selected", "true");
  expect(within(navigation).getByRole("tab", { name: /P4 投影/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /当前 Turn/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /检查评审/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /运行日志/ })).toBeInTheDocument();

  const workspace = screen.getByTestId("p3-design-lab-workspace");
  expect(within(workspace).getByRole("heading", { name: "软设工作区" })).toBeInTheDocument();
  expect(within(workspace).getByRole("button", { name: "文档视图" })).toHaveAttribute("aria-pressed", "true");
  expect(within(workspace).getByRole("button", { name: "结构化数据" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成软件设计说明" }));

  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions", expect.any(Object)));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/generate"));
  expect(await screen.findByText("空域协同规划软件设计说明")).toBeInTheDocument();
  expect(within(workspace).getByTestId("document-body-panel")).toBeInTheDocument();
  expect(within(workspace).getByLabelText("A4 软件设计说明预览")).toBeInTheDocument();
  expect(within(workspace).getAllByText("SoftwareDesignBaseline v2").length).toBeGreaterThanOrEqual(1);

  fireEvent.click(within(workspace).getByRole("button", { name: "结构化数据" }));
  expect(within(workspace).getByTestId("p3-design-structured-data-view")).toBeInTheDocument();
  expect(within(workspace).getByText("规划任务管理")).toBeInTheDocument();
  expect(within(workspace).getByText("unified_service")).toBeInTheDocument();

  fireEvent.click(within(navigation).getByRole("tab", { name: /P4 投影/ }));
  expect(screen.getByTestId("p3-design-lab-projection-tree")).toBeInTheDocument();
  expect(screen.getByRole("tree", { name: "P4 工单投影树" })).toBeInTheDocument();
  expect(screen.getByText("规划任务管理模块实现")).toBeInTheDocument();

  fireEvent.click(within(navigation).getByRole("tab", { name: /需规输入/ }));
  const inputView = screen.getByTestId("p3-design-lab-input-view");
  expect(inputView).toBeInTheDocument();
  expect(within(inputView).getByText("需规列表")).toBeInTheDocument();
  expect(within(inputView).getByText("关联软设")).toBeInTheDocument();
  expect(within(inputView).getAllByText("空域协同规划软件需求规格说明").length).toBeGreaterThan(0);
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
