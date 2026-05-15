import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const deleteMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

beforeEach(() => {
  vi.useRealTimers();
  getMock.mockReset();
  postMock.mockReset();
  deleteMock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

test("renders P3 Design Lab as a Lab workspace with software design document, structured data, and P4 projection tree", async () => {
  const inputPackage = buildInputPackage();
  const createdSession = buildSession(inputPackage, "created");
  const generatedSession = buildSession(inputPackage, "baseline_ready");
  const savedSession = buildSession(inputPackage, "draft_saved", {
    runtime_events: [
      { event_id: "evt-1", event_type: "generate", message: "生成软件设计说明", created_at: "2026-05-13T10:20:00Z" },
      { event_id: "evt-2", event_type: "save", message: "保存软件设计说明草稿", created_at: "2026-05-13T10:22:00Z" },
    ],
  });
  const projectedSession = buildSession(inputPackage, "projection_ready", {
    runtime_events: [
      { event_id: "evt-1", event_type: "generate", message: "生成软件设计说明", created_at: "2026-05-13T10:20:00Z" },
      { event_id: "evt-3", event_type: "projection", message: "生成 P4 工单投影候选", created_at: "2026-05-13T10:23:00Z" },
    ],
  });
  const turnedSession = buildSession(inputPackage, "patch_ready", {
    turns: [
      {
        turn_id: "p3turn-1",
        user_input: "按保守方案，增加状态机说明",
        normalized_intent: "add_state_machine",
        assistant_message: "已补入状态机说明，并将告警反馈时间保留为待确认项。",
        created_at: "2026-05-13T10:24:00Z",
      },
    ],
  });
  const checkedSession = buildSession(inputPackage, "patch_ready", {
    check_result: {
      blocking_count: 0,
      warning_count: 1,
      passed_count: 4,
      items: [{ severity: "passed", message: "软件设计说明正文已生成。" }],
    },
  });
  const frozenSession = buildSession(inputPackage, "frozen", {
    check_result: checkedSession.check_result,
    frozen_package: {
      package_id: "sdp-p3dl-1",
      version_label: "SoftwareDesignBaseline v2",
      status: "frozen",
      frozen_at: "2026-05-13T10:30:00Z",
    },
  });

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
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return Promise.resolve({ data: { turn: turnedSession.turns[0], session: turnedSession } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/save") {
      return Promise.resolve({ data: savedSession });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/projection") {
      return Promise.resolve({ data: projectedSession });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/check") {
      return Promise.resolve({
        data: { session_id: "p3dl-1", check_result: checkedSession.check_result, session: checkedSession },
      });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/freeze") {
      return Promise.resolve({ data: frozenSession });
    }
    throw new Error(`unexpected post url: ${url}`);
  });
  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: generatedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  deleteMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: { deleted_session_id: "p3dl-1" } });
    }
    throw new Error(`unexpected delete url: ${url}`);
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
  fireEvent.click(within(workspace).getByRole("button", { name: "保存草稿" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/save"));
  expect(await screen.findByText("设计会话：draft_saved")).toBeInTheDocument();

  fireEvent.click(within(workspace).getByRole("button", { name: "结构化数据" }));
  expect(within(workspace).getByTestId("p3-design-structured-data-view")).toBeInTheDocument();
  expect(within(workspace).getByText("规划任务管理")).toBeInTheDocument();
  expect(within(workspace).getByText("unified_service")).toBeInTheDocument();
  fireEvent.click(within(workspace).getByRole("button", { name: "生成投影候选" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/projection"));

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
  expect(within(inputView).getByText("2026-05-13 10:20")).toBeInTheDocument();
  expect(within(inputView).getByText("baseline_ready")).toBeInTheDocument();

  fireEvent.click(within(inputView).getByRole("button", { name: "进入编辑" }));
  await waitFor(() => expect(getMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1"));
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toHaveAttribute("aria-selected", "true");

  fireEvent.click(within(navigation).getByRole("tab", { name: /当前 Turn/ }));
  fireEvent.change(screen.getByLabelText("P3 Design Lab CLI"), { target: { value: "按保守方案，增加状态机说明" } });
  fireEvent.click(screen.getByRole("button", { name: "提交" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/turns", {
      user_input: "按保守方案，增加状态机说明",
    }),
  );
  expect(await screen.findByText("已补入状态机说明，并将告警反馈时间保留为待确认项。")).toBeInTheDocument();

  fireEvent.click(within(navigation).getByRole("tab", { name: /检查评审/ }));
  fireEvent.click(screen.getByRole("button", { name: "运行检查" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/check"));
  expect(await screen.findByText("通过项：4")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "冻结设计包" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/freeze"));
  expect(await screen.findByText("设计会话：frozen")).toBeInTheDocument();

  fireEvent.click(within(navigation).getByRole("tab", { name: /需规输入/ }));
  fireEvent.click(screen.getByRole("button", { name: "删除" }));
  await waitFor(() => expect(deleteMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1"));
});

test("refreshes P3 input packages while the page stays open", async () => {
  vi.useFakeTimers();
  const firstPackage = buildInputPackage();
  const secondPackage = {
    ...buildInputPackage(),
    input_package_id: "p2frozen-doc-2",
    source_document_id: "doc-2",
    source_title: "低空通航协同软件需求规格说明",
    frozen_at: "2026-05-14T00:00:00Z",
    standard_document: {
      title: "低空通航协同软件需求规格说明",
      sections: [],
    },
    structured_spec: {
      application: { name: "低空通航协同软件" },
    },
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      const items = getMock.mock.calls.length === 1 ? [firstPackage] : [firstPackage, secondPackage];
      return Promise.resolve({ data: { items } });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  await act(async () => {
    await Promise.resolve();
  });

  expect(screen.getByText("P3 Software Design Lab")).toBeInTheDocument();
  expect(screen.getByText("1 份需规输入")).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(1000);
  });

  expect(getMock).toHaveBeenCalledTimes(2);
  expect(screen.getByText("2 份需规输入")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /需规输入/ }));
  const inputView = screen.getByTestId("p3-design-lab-input-view");
  expect(within(inputView).getByText("低空通航协同软件需求规格说明")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "刷新输入包" })).toBeInTheDocument();
});

function buildInputPackage() {
  return {
    input_package_id: "p2frozen-doc-1",
    source_document_id: "doc-1",
    source_title: "空域协同规划软件需求规格说明",
    p3_consumable: true,
    frozen_at: "2026-05-01T00:00:00Z",
    related_designs: [],
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

function buildSession(
  inputPackage: ReturnType<typeof buildInputPackage>,
  status: string,
  overrides: Record<string, unknown> = {},
) {
  const session = {
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
            tree: {
              node_id: "p4-projection-root",
              title: "P4 模块工单投影包",
              node_type: "projection_package",
              children: [
                {
                  node_id: "branch-core-service",
                  title: "统一服务实现分支",
                  node_type: "module_branch",
                  children: [{ node_id: "wo-1", title: "规划任务管理模块实现", node_type: "module_workorder" }],
                },
              ],
            },
            items: [{ item_id: "wo-1", title: "规划任务管理模块实现" }],
          },
    turns: [],
    check_result: null,
    frozen_package: null,
    runtime_events: [{ event_id: "evt-1", event_type: "generate", message: "生成软件设计说明", created_at: "2026-05-13T10:20:00Z" }],
    created_at: "2026-05-13T10:00:00Z",
    updated_at: status === "created" ? "2026-05-13T10:00:00Z" : "2026-05-13T10:20:00Z",
    ...overrides,
  };
  return {
    ...session,
    input_package:
      status === "created"
        ? inputPackage
        : {
            ...inputPackage,
            related_designs: [
              {
                software_design_id: session.session_id,
                title: "空域协同规划软件设计说明",
                version_label: "SoftwareDesignBaseline v2",
                status: "baseline_ready",
                created_at: "2026-05-13T10:00:00Z",
                updated_at: "2026-05-13T10:20:00Z",
              },
            ],
          },
  };
}
