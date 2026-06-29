import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const putMock = vi.fn();
const deleteMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    put: (...args: unknown[]) => putMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

beforeEach(() => {
  vi.useRealTimers();
  getMock.mockReset();
  postMock.mockReset();
  putMock.mockReset();
  deleteMock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

test("renders P3 Design Lab with a unified software design morph workspace", async () => {
  const inputPackage = buildInputPackage();
  const newDesignTitle = "空域协同规划软件设计说明（设计方案 01）";
  const newVersionLabel = "v0.1";
  const createdSession = buildSession(inputPackage, "created", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    status: "created",
    conversion: null,
  });
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    conversion: buildConversion("draft_ready", "component_first"),
  });
  const savedSession = buildSession(inputPackage, "draft_saved", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    runtime_events: [
      { event_id: "evt-1", event_type: "generate", message: "生成软件设计说明", created_at: "2026-05-13T10:20:00Z" },
      { event_id: "evt-2", event_type: "save", message: "保存软件设计说明草稿", created_at: "2026-05-13T10:22:00Z" },
    ],
  });
  const projectedSession = buildSession(inputPackage, "projection_ready", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    runtime_events: [
      { event_id: "evt-1", event_type: "generate", message: "生成软件设计说明", created_at: "2026-05-13T10:20:00Z" },
      { event_id: "evt-3", event_type: "projection", message: "生成 P4 工单投影候选", created_at: "2026-05-13T10:23:00Z" },
    ],
  });
  const turnedSession = buildSession(inputPackage, "patch_ready", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
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
  const scopedTurn = {
    turn_id: "p3turn-scoped-1",
    turn_type: "scoped_design_edit",
    user_input: "这一段写得太散，拆成两段，并补充接口边界。",
    normalized_intent: "scoped_design_edit",
    assistant_message: "已生成局部补丁提案：建议将当前段落拆分为职责边界和接口约束两段。",
    scope_anchor: {
      anchor_type: "design_block",
      section_id: "goal",
      block_id: "goal-body",
      design_revision_id: newVersionLabel,
    },
    patch_proposal: {
      proposal_id: "patch-scoped-1",
      base_revision_id: newVersionLabel,
      target_anchor: { section_id: "goal", block_id: "goal-body" },
      operations: [
        {
          op: "split_block",
          target_block_id: "goal-body",
          new_blocks: [
            { title: "职责边界", content: "围绕当前段落重新组织职责边界。" },
            { title: "接口约束", content: "补充接口边界、输入输出和检查约束。" },
          ],
        },
      ],
      quality_notes: ["补丁应用后需要重新运行设计完整性检查。"],
      status: "proposed",
    },
  };
  const scopedTurnSession = buildSession(inputPackage, "patch_ready", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    turns: [scopedTurn],
  });
  const appliedScopedSession = buildSession(inputPackage, "patched", {
    design_title: newDesignTitle,
    version_label: "v0.1-patch-1",
    design_document: {
      title: newDesignTitle,
      version_label: "v0.1-patch-1",
      sections: [
        {
          section_id: "goal",
          title: "1. 设计目标与范围",
          content: "围绕当前段落重新组织职责边界。\n补充接口边界、输入输出和检查约束。",
          status: "generated",
          source_refs: ["REQ-3.2"],
          blocks: [
            {
              block_id: "goal-body-split-1",
              kind: "paragraph",
              title: "职责边界",
              content: "围绕当前段落重新组织职责边界。",
              source_refs: ["REQ-3.2"],
            },
            {
              block_id: "goal-body-split-2",
              kind: "paragraph",
              title: "接口约束",
              content: "补充接口边界、输入输出和检查约束。",
              source_refs: ["REQ-3.2"],
            },
          ],
        },
        {
          section_id: "architecture",
          title: "2. 总体架构",
          content: "采用统一服务架构。",
          status: "generated",
          source_refs: ["REQ-3.2"],
        },
      ],
    },
    turns: [
      {
        ...scopedTurn,
        patch_proposal: {
          ...scopedTurn.patch_proposal,
          status: "applied",
        },
      },
      {
        turn_id: "p3turn-apply-1",
        turn_type: "patch_application",
        normalized_intent: "apply_patch_proposal",
        assistant_message: "已应用补丁提案 patch-scoped-1 到软件设计说明正文。",
        patch_application: {
          application_id: "patch-app-1",
          proposal_id: "patch-scoped-1",
          base_revision_id: "v0.1",
          result_revision_id: "v0.1-patch-1",
          updated_targets: [{ target_type: "design_block", section_id: "goal", block_id: "goal-body-split-1" }],
          warnings: ["补丁应用后需要重新运行设计完整性检查。"],
        },
      },
    ],
  });
  const checkedSession = buildSession(inputPackage, "patch_ready", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    check_result: {
      blocking_count: 0,
      warning_count: 1,
      passed_count: 4,
      items: [{ severity: "passed", message: "软件设计说明正文已生成。" }],
    },
  });
  const frozenSession = buildSession(inputPackage, "frozen", {
    design_title: newDesignTitle,
    version_label: newVersionLabel,
    check_result: checkedSession.check_result,
    frozen_package: {
      package_id: "sdp-p3dl-1",
      version_label: newVersionLabel,
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

  postMock.mockImplementation((url: string, payload?: { turn_type?: string }) => {
    if (url === "/software-design-v2/sessions") {
      return Promise.resolve({ data: createdSession });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/conversion") {
      return Promise.resolve({ data: convertedSession });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      if (payload?.turn_type === "scoped_design_edit") {
        return Promise.resolve({ data: { turn: scopedTurn, session: scopedTurnSession } });
      }
      return Promise.resolve({ data: { turn: turnedSession.turns[0], session: turnedSession } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1/patch-proposals/patch-scoped-1/apply") {
      return Promise.resolve({
        data: {
          application_id: "patch-app-1",
          status: "applied",
          application: {
            application_id: "patch-app-1",
            proposal_id: "patch-scoped-1",
            base_revision_id: "v0.1",
            result_revision_id: "v0.1-patch-1",
            updated_targets: [{ target_type: "design_block", section_id: "goal", block_id: "goal-body-split-1" }],
            warnings: ["补丁应用后需要重新运行设计完整性检查。"],
          },
          updated_targets: [{ target_type: "design_block", section_id: "goal", block_id: "goal-body-split-1" }],
          warnings: ["补丁应用后需要重新运行设计完整性检查。"],
          updated_session: appliedScopedSession,
        },
      });
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
      return Promise.resolve({ data: convertedSession });
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
  expect(within(navigation).getByRole("tab", { name: /需规输入/ })).toHaveAttribute("aria-selected", "true");
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /当前 Turn/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /检查评审/ })).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /运行日志/ })).toBeInTheDocument();
  expect(within(navigation).queryByRole("tab", { name: /需规转软设/ })).not.toBeInTheDocument();
  expect(within(navigation).queryByRole("tab", { name: /P4 投影/ })).not.toBeInTheDocument();

  const workspace = screen.getByTestId("p3-design-lab-workspace");
  expect(within(workspace).getByTestId("p3-design-lab-input-view")).toBeInTheDocument();
  fireEvent.click(within(workspace).getByRole("button", { name: "新建软设" }));
  expect(screen.getByRole("dialog", { name: "新建软件设计说明" })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("软设名称"), { target: { value: newDesignTitle } });
  fireEvent.change(screen.getByLabelText("版本标识"), { target: { value: newVersionLabel } });
  fireEvent.click(screen.getByRole("button", { name: "创建软设会话" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-design-v2/sessions",
      expect.objectContaining({
        design_title: newDesignTitle,
        version_label: newVersionLabel,
      }),
    ),
  );
  expect(postMock).not.toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/generate");
  expect(postMock.mock.calls.filter(([url]) => url === "/software-design-v2/sessions/p3dl-1/conversion")).toHaveLength(0);
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toHaveAttribute("aria-selected", "true");
  expect(within(workspace).getByRole("heading", { name: "软设工作区" })).toBeInTheDocument();
  expect(within(workspace).getByTestId("p3-design-morph-workspace")).toBeInTheDocument();
  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  expect(morphPlatform).toBeInTheDocument();
  expect(within(morphPlatform).getByTestId("design-morph-track-canvas")).toHaveAttribute("aria-label", "软设形态滑窗 Canvas");
  expect(within(morphPlatform).getByTestId("design-morph-main-canvas")).toHaveAttribute("aria-label", "软设工作区 Canvas");
  expect(within(morphPlatform).queryByTestId("design-morph-html-overlay")).not.toBeInTheDocument();
  expect(within(morphPlatform).queryByRole("button", { name: "需规文档 -> 软设文档" })).not.toBeInTheDocument();
  expect(within(morphPlatform).getByText("Canvas 窗口：需规文档 -> 软设文档")).toBeInTheDocument();
  expect(within(morphPlatform).getByText("缩放 90%")).toBeInTheDocument();
  expect(within(morphPlatform).getByText(/^平移 /)).toBeInTheDocument();
  expectCanvasWorkspaceColumnsToStretch();
  expectWorkspaceFullscreenToCoverViewport();
  expect(within(workspace).getByRole("combobox", { name: "转换策略" })).toBeInTheDocument();
  expect(within(workspace).getAllByText("标准软设草稿生成").length).toBeGreaterThanOrEqual(1);
  fireEvent.mouseDown(within(workspace).getByRole("combobox", { name: "转换策略" }));
  fireEvent.click(await screen.findByText("组件优先拆解"));
  expect(within(workspace).getByText("读取需规冻结包")).toBeInTheDocument();
  expect(within(workspace).getByText("抽取设计对象")).toBeInTheDocument();
  expect(within(workspace).getByText("生成软设草稿")).toBeInTheDocument();
  expect(within(workspace).getByText("建立追溯映射")).toBeInTheDocument();
  const conversionControl = within(workspace).getByTestId("p3-design-lab-conversion-control");
  expect(within(conversionControl).getByText("转换控制")).toBeInTheDocument();
  expect(conversionControl).toContainElement(within(workspace).getByRole("button", { name: "执行基础转换" }));
  expect(within(conversionControl).getByText("当前进展")).toBeInTheDocument();
  expect(within(conversionControl).getByText(/已识别/)).toBeInTheDocument();
  expect(within(conversionControl).getByText("输出结果")).toBeInTheDocument();
  expect(within(conversionControl).getByText(/自动切换到软设文档/)).toBeInTheDocument();
  expect(within(conversionControl).getByRole("button", { name: "预览参数" })).toBeInTheDocument();
  expect(within(conversionControl).getByRole("button", { name: "查看转换日志" })).toBeInTheDocument();
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  expect(within(inspector).getByRole("tab", { name: "能力" })).toHaveAttribute("aria-selected", "true");
  expect(within(inspector).getByRole("tab", { name: "共性信息" })).toHaveAttribute("aria-selected", "false");
  expect(within(inspector).getByText("转换反馈")).toBeInTheDocument();
  expect(within(inspector).getByText("当前对象追溯")).toBeInTheDocument();
  expect(within(inspector).queryByText("结构化摘要")).not.toBeInTheDocument();
  expect(within(inspector).queryByText("投影树")).not.toBeInTheDocument();
  expect(within(inspector).queryByRole("tree", { name: "P4 工单投影树" })).not.toBeInTheDocument();
  expect(within(inspector).queryByText("基类字段：标识信息")).not.toBeInTheDocument();
  fireEvent.click(within(inspector).getByRole("tab", { name: "共性信息" }));
  expect(within(inspector).getByRole("tab", { name: "共性信息" })).toHaveAttribute("aria-selected", "true");
  expect(within(inspector).getByText("基类字段：标识信息")).toBeInTheDocument();
  expect(within(inspector).getByText("基类字段：布局变换")).toBeInTheDocument();
  expect(within(inspector).getByText("基类字段：追溯关系")).toBeInTheDocument();
  expect(within(inspector).getByText("基类字段：生命周期")).toBeInTheDocument();
  expect(within(inspector).getByText("分型扩展：连接关系")).toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "执行基础转换" })).not.toBeInTheDocument();
  fireEvent.click(within(inspector).getByRole("tab", { name: "能力" }));
  expect(within(inspector).getByRole("tab", { name: "能力" })).toHaveAttribute("aria-selected", "true");
  expect(within(inspector).getByRole("button", { name: "执行基础转换" })).toBeInTheDocument();
  expect(within(conversionControl).queryByRole("button", { name: "进入软设工作区微调" })).not.toBeInTheDocument();
  const relationFacts = within(workspace).getByTestId("p3-design-morph-relation-facts");
  expect(within(relationFacts).getByText("需规转软设")).toBeInTheDocument();
  expect(within(workspace).queryByText("从 P2 冻结需规生成软件设计说明草稿，并建立正文、结构化事实和追溯映射。")).not.toBeInTheDocument();
  expect(relationFacts.querySelector(".p3-design-lab-metric")).toBeNull();
  expect(within(workspace).getByRole("button", { name: "网页全屏" })).toBeInTheDocument();
  fireEvent.click(within(workspace).getByRole("button", { name: "网页全屏" }));
  expect(within(workspace).getByTestId("p3-workspace-panel")).toHaveClass("is-web-fullscreen");
  expect(within(workspace).getByTestId("p3-workspace-panel")).toHaveClass("is-compact-head");
  expect(within(workspace).queryByText("需规、软设文档、功能树、分层架构、技术实现、展示形态和 P4 投影在同一个 Canvas 工作区中传递。")).not.toBeInTheDocument();
  expect(within(workspace).getByRole("button", { name: "缩回工作区" })).toBeInTheDocument();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(within(workspace).getByTestId("p3-workspace-panel")).not.toHaveClass("is-web-fullscreen");
  fireEvent.click(within(workspace).getByRole("button", { name: "网页全屏" }));
  fireEvent.click(within(workspace).getByRole("button", { name: "缩回工作区" }));
  expect(within(workspace).getByTestId("p3-workspace-panel")).not.toHaveClass("is-web-fullscreen");
  expect(within(conversionControl).queryByText("加载正文、结构化条款和冻结快照。")).not.toBeInTheDocument();
  expect(within(conversionControl).queryByText("执行基础转换后生成软设草稿、结构化设计事实和追溯摘要。")).not.toBeInTheDocument();
  expect(within(conversionControl).queryByText("转换完成后进入软设工作区微调。")).not.toBeInTheDocument();
  expect(within(conversionControl).queryByText("当前策略")).not.toBeInTheDocument();
  expect(within(conversionControl).queryByText("转换状态")).not.toBeInTheDocument();
  expect(within(conversionControl).queryByText("待执行")).not.toBeInTheDocument();
  expect(within(conversionControl).getByTestId("p3-design-lab-conversion-step-read_requirement")).toHaveClass("is-current");
  fireEvent.click(within(workspace).getByRole("button", { name: "执行基础转换" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/conversion", {
      strategy: "component_first",
    }),
  );
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toHaveAttribute("aria-selected", "true");
  expect(within(morphPlatform).getByText("Canvas 窗口：软设文档 -> 功能树")).toBeInTheDocument();
  expect(within(workspace).queryByRole("button", { name: "进入软设工作区微调" })).not.toBeInTheDocument();
  expect(within(workspace).getByText("关系：软设文档 -> 功能树")).toBeInTheDocument();
  expect(within(navigation).getByRole("tab", { name: /软设工作区/ })).toHaveAttribute("aria-selected", "true");
  expect(within(workspace).getByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  await waitFor(() => expect(screen.getAllByText(newDesignTitle).length).toBeGreaterThanOrEqual(1));
  expect(within(workspace).getByTestId("design-morph-inspector")).toBeInTheDocument();
  expect(within(workspace).getByText("当前选中对象")).toBeInTheDocument();
  expect(within(workspace).getByText("当前对象追溯")).toBeInTheDocument();
  expect(within(workspace).getByText("关系：软设文档 -> 功能树")).toBeInTheDocument();
  expect(within(workspace).getAllByText(new RegExp(newVersionLabel)).length).toBeGreaterThanOrEqual(1);
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  expect(within(inspector).getByText("对象：1. 设计目标与范围")).toBeInTheDocument();
  expect(within(inspector).getByText("覆盖协同规划核心能力。")).toBeInTheDocument();
  expect(within(inspector).getByText("扩写本段")).toBeInTheDocument();
  expect(within(inspector).getByText("局部提案工作区")).toBeInTheDocument();
  fireEvent.change(within(inspector).getByLabelText("局部 AI 沟通输入"), {
    target: { value: "这一段写得太散，拆成两段，并补充接口边界。" },
  });
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/turns", {
      turn_type: "scoped_design_edit",
      interaction_mode: "propose_patch",
      user_input: "这一段写得太散，拆成两段，并补充接口边界。",
      expected_output: ["document_patch", "traceability_update", "quality_note"],
      scope_anchor: {
        anchor_type: "design_block",
        document_id: "p3dl-1",
        design_revision_id: newVersionLabel,
        section_id: "goal",
        block_id: "goal-body",
        selection_snapshot: {
          title: "1. 设计目标与范围",
          excerpt: "覆盖协同规划核心能力。",
        },
        source_refs: ["REQ-3.2"],
      },
    }),
  );
  expect(await within(inspector).findByText("补丁提案")).toBeInTheDocument();
  expect(within(inspector).getByText("职责边界")).toBeInTheDocument();
  expect(within(inspector).getByText("接口约束")).toBeInTheDocument();
  expect(within(inspector).getByText("补丁应用后需要重新运行设计完整性检查。")).toBeInTheDocument();
  expect(within(inspector).getByRole("button", { name: "应用到文档" })).toBeInTheDocument();
  fireEvent.click(within(inspector).getByRole("button", { name: "应用到文档" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/patch-proposals/patch-scoped-1/apply", {
      turn_id: "p3turn-scoped-1",
      base_revision_id: "v0.1",
      apply_scope: "document_only",
    }),
  );
  expect(await within(inspector).findByText("补丁已应用到文档")).toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "应用到文档" })).not.toBeInTheDocument();
  expect(within(designDocumentObject).getByText("围绕当前段落重新组织职责边界。")).toBeInTheDocument();
  expect(within(designDocumentObject).getByText("补充接口边界、输入输出和检查约束。")).toBeInTheDocument();
  expect(within(inspector).getByText("当前对象追溯")).toBeInTheDocument();
  expect(within(inspector).queryByText("结构化摘要")).not.toBeInTheDocument();
  expect(within(inspector).queryByText("投影树")).not.toBeInTheDocument();
  const functionTreeObject = within(morphPlatform).getByTestId("stage-object-functionTree");
  expect(functionTreeObject).toHaveClass("is-function-tree-stage-object");
  expect(within(functionTreeObject).getByText("规划任务管理")).toBeInTheDocument();
  expect(within(functionTreeObject).queryByText("功能节点")).not.toBeInTheDocument();
  expect(within(functionTreeObject).queryByText("已追溯")).not.toBeInTheDocument();
  expect(within(functionTreeObject).queryByText("待确认")).not.toBeInTheDocument();
  expect(within(functionTreeObject).queryByText("最大层级")).not.toBeInTheDocument();
  expect(within(functionTreeObject).queryByText("由当前设计基线派生")).not.toBeInTheDocument();
  fireEvent.click(within(functionTreeObject).getByText("规划任务管理"));
  expect(within(inspector).getByText("对象：规划任务管理")).toBeInTheDocument();
  expect(within(inspector).getByText("功能树概览")).toBeInTheDocument();
  expect(within(inspector).getByText("功能节点")).toBeInTheDocument();
  expect(within(inspector).getByText("已追溯")).toBeInTheDocument();
  expect(within(inspector).getByText("待确认")).toBeInTheDocument();
  expect(within(inspector).getByText("最大层级")).toBeInTheDocument();
  expect(within(inspector).getByText("由转换器输出")).toBeInTheDocument();
  expect(within(inspector).getByText("查看来源需规")).toBeInTheDocument();
  expect(within(inspector).getByText("查看软设章节")).toBeInTheDocument();
  expect(within(inspector).getByText("只看当前子树")).toBeInTheDocument();
  expect(within(inspector).getByText("只看未追溯")).toBeInTheDocument();
  expect(within(inspector).getByText("只看待确认")).toBeInTheDocument();
  expect(within(inspector).getByText("当前对象追溯")).toBeInTheDocument();
  expect(within(inspector).getByText("支撑设计信息")).toBeInTheDocument();
  expect(within(inspector).getByText("接口")).toBeInTheDocument();
  expect(within(inspector).getByText("POST /planning-tasks")).toBeInTheDocument();
  expect(within(inspector).getByText("数据对象")).toBeInTheDocument();
  expect(within(inspector).getByText("PlanningTask")).toBeInTheDocument();
  expect(within(inspector).getAllByText("状态").length).toBeGreaterThanOrEqual(1);
  expect(within(inspector).getByText("draft")).toBeInTheDocument();
  expect(within(inspector).getByText("质量约束")).toBeInTheDocument();
  expect(within(inspector).getByText("规划任务状态变化必须保留留痕记录")).toBeInTheDocument();
  expect(within(inspector).queryByText("结构化摘要")).not.toBeInTheDocument();
  expect(within(inspector).queryByText("投影树")).not.toBeInTheDocument();
  expect(within(workspace).queryByTestId("p3-design-lab-conversion-control")).not.toBeInTheDocument();
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "上一窗口" }));
  expect(within(morphPlatform).getByText("Canvas 窗口：需规文档 -> 软设文档")).toBeInTheDocument();
  expect(within(workspace).getByTestId("p3-design-lab-conversion-control")).toBeInTheDocument();
  fireEvent.click(within(workspace).getByRole("button", { name: "保存草稿" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/save"));
  expect(await screen.findByText("设计会话：draft_saved")).toBeInTheDocument();

  expect(within(workspace).getAllByText("规划任务管理").length).toBeGreaterThanOrEqual(1);
  expect(within(workspace).getAllByText("unified_service").length).toBeGreaterThanOrEqual(1);
  fireEvent.click(within(workspace).getByRole("button", { name: "生成投影候选" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/projection"));
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  expect(within(workspace).getByTestId("design-morph-canvas-platform")).toBeInTheDocument();
  expect(within(morphPlatform).getByText("Canvas 窗口：展示形态 -> P4 投影")).toBeInTheDocument();
  expect(within(workspace).getAllByText("P4-WO-StageLab-Workbench").length).toBeGreaterThanOrEqual(1);
  expect(within(workspace).getAllByText("B. P3 适配工具包").length).toBeGreaterThanOrEqual(1);
  expect(within(morphPlatform).getByText("P4 投影")).toBeInTheDocument();
  expect(within(inspector).queryByText("投影树")).not.toBeInTheDocument();

  fireEvent.click(within(navigation).getByRole("tab", { name: /需规输入/ }));
  const inputView = screen.getByTestId("p3-design-lab-input-view");
  expect(inputView).toBeInTheDocument();
  expect(within(inputView).getByText("需规列表")).toBeInTheDocument();
  expect(within(inputView).getByText("关联软设")).toBeInTheDocument();
  expect(within(inputView).getAllByText("空域协同规划软件需求规格说明").length).toBeGreaterThan(0);
  expect(within(inputView).getByText("2026-05-13 10:20")).toBeInTheDocument();
  expect(within(inputView).getByText("projection_ready")).toBeInTheDocument();
  expect(within(inputView).getByText(`版本：${newVersionLabel}`)).toBeInTheDocument();

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

test("keeps the canvas carrier stretched to the same bottom edge as the inspector", () => {
  expectCanvasWorkspaceColumnsToStretch();
});

test("uses a compact inline title and subtitle treatment for all morph stage frames", () => {
  expectDesignMorphStageFrameHeaderToBeInline();
});

test("stretches layered architecture swimlanes instead of leaving a blank tail", () => {
  expectLayeredArchitectureSwimlanesToFillStage();
});

test("keeps architecture view relation chips attached to the node grid", () => {
  expectArchitectureViewRelationsToFollowContent();
});

test("keeps architecture view stage height controlled by the saved canvas layout", () => {
  expectArchitectureViewStageHeightToFollowSavedLayout();
});

test("links function tree selection to layered architecture mapping details", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
    design_baseline: {
      baseline_id: "sdb2-1",
      architecture_mode: "business_module_oriented_layered_architecture",
      modules: [{ module_id: "planning-task", name: "规划任务管理" }],
      function_tree: buildFunctionTreeFixture(),
      layered_architecture: buildLayeredArchitectureFixture(),
    },
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  expect(within(morphPlatform).getByText("Canvas 窗口：软设文档 -> 功能树")).toBeInTheDocument();

  const functionTreeObject = within(morphPlatform).getByTestId("stage-object-functionTree");
  fireEvent.click(within(functionTreeObject).getByText("创建规划任务"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  expect(within(inspector).getByText("对象：创建规划任务")).toBeInTheDocument();
  expect(within(inspector).getByText("分层架构映射")).toBeInTheDocument();
  expect(within(inspector).getByText("展示层")).toBeInTheDocument();
  expect(within(inspector).getByText("服务层")).toBeInTheDocument();
  expect(within(inspector).getByText("规划任务工作台")).toBeInTheDocument();
  expect(within(inspector).getByText("规划任务服务")).toBeInTheDocument();

  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  expect(within(morphPlatform).getByText("Canvas 窗口：功能树 -> 分层架构")).toBeInTheDocument();
  const layeredArchitectureObject = within(morphPlatform).getByTestId("stage-object-layeredArchitecture");
  expect(within(layeredArchitectureObject).getByText("五层分层架构")).toBeInTheDocument();
  expect(within(layeredArchitectureObject).getByTestId("architecture-component-cmp-task-workbench")).toHaveClass(
    "is-linked-to-selection",
  );
  expect(within(layeredArchitectureObject).getByTestId("architecture-component-cmp-task-service")).toHaveClass(
    "is-linked-to-selection",
  );

  fireEvent.click(within(layeredArchitectureObject).getByTestId("architecture-component-cmp-task-service"));
  expect(within(inspector).getByText("对象：规划任务服务")).toBeInTheDocument();
  expect(within(inspector).getByText("承载功能")).toBeInTheDocument();
  expect(within(inspector).getByText("创建规划任务")).toBeInTheDocument();
  expect(within(inspector).getByText("映射状态")).toBeInTheDocument();
  expect(within(inspector).getAllByText("confirmed").length).toBeGreaterThanOrEqual(1);
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

test("restores persisted P3 design session from the URL query on page load", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "projection_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:23:00Z",
      },
    ],
  };
  const persistedSession = buildSession(inputPackage, "projection_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    status: "projection_ready",
    updated_at: "2026-05-13T10:23:00Z",
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: persistedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter
      initialEntries={["/p3-design-lab?session_id=p3dl-1"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <App />
    </MemoryRouter>,
  );

  await waitFor(() => expect(getMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1"));
  const workspace = await screen.findByTestId("p3-design-lab-workspace");
  expect(within(workspace).getByRole("heading", { name: "软设工作区" })).toBeInTheDocument();
  expect(screen.getByText("设计会话：projection_ready")).toBeInTheDocument();
  expect(within(workspace).getByText("P4 投影")).toBeInTheDocument();
  expect(within(workspace).getByText("Canvas 窗口：软设文档 -> 功能树")).toBeInTheDocument();
});

test("prefills new software design metadata from the selected requirement and existing related designs", async () => {
  const inputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-existing",
        title: "空域协同规划软件设计说明（设计方案 01）",
        version_label: "v0.1",
        status: "draft_saved",
        created_at: "2026-05-13T09:00:00Z",
        updated_at: "2026-05-13T09:20:00Z",
      },
    ],
  };

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  const workspace = await screen.findByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "新建软设" }));

  expect(screen.getByRole("dialog", { name: "新建软件设计说明" })).toBeInTheDocument();
  expect(screen.getByLabelText("软设名称")).toHaveValue("空域协同规划软件设计说明（设计方案 02）");
  expect(screen.getByLabelText("版本标识")).toHaveValue("v0.2");
});

test("shows a persistent conversion waiting state and locks the conversion trigger while Dify is running", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const inputPackage = buildInputPackage();
  const createdSession = buildSession(inputPackage, "created", {
    status: "created",
    conversion: buildConversion("conversion_pending", "standard_sdd_draft"),
  });
  let resolveConversion: (value: { data: ReturnType<typeof buildSession> }) => void = () => {};
  const conversionPromise = new Promise<{ data: ReturnType<typeof buildSession> }>((resolve) => {
    resolveConversion = resolve;
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
    if (url === "/software-design-v2/sessions/p3dl-1/conversion") {
      return conversionPromise;
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "生成软件设计说明" })).not.toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "新建软设" }));
  fireEvent.click(screen.getByRole("button", { name: "创建软设会话" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions", expect.any(Object)));

  const conversionButton = await within(workspace).findByRole("button", { name: "执行基础转换" });
  expect(conversionButton).toBeEnabled();
  fireEvent.click(conversionButton);

  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions/p3dl-1/conversion", expect.any(Object)));
  expect(within(workspace).getByRole("button", { name: "正在生成软设" })).toBeDisabled();
  expect(within(workspace).getByText("正在调用 Dify 生成软件设计说明")).toBeInTheDocument();
  expect(within(workspace).getByText("一般耗时约 200 秒，请保持本页打开。")).toBeInTheDocument();
  expect(within(workspace).getByText("已等待 00:00")).toBeInTheDocument();
  expect(within(workspace).getByTestId("p3-design-conversion-waiting-document")).toBeInTheDocument();
  const conversionControl = within(workspace).getByTestId("p3-design-lab-conversion-control");
  expect(within(conversionControl).getByText("预计进度，Dify 返回后以实际结果为准")).toBeInTheDocument();
  expect(within(conversionControl).getByTestId("p3-design-lab-conversion-step-read_requirement")).toHaveClass("is-done");
  expect(within(conversionControl).getByTestId("p3-design-lab-conversion-step-extract_design_objects")).toHaveClass("is-current");

  await act(async () => {
    vi.advanceTimersByTime(65_000);
  });
  expect(within(workspace).getByText("已等待 01:05")).toBeInTheDocument();
  expect(within(conversionControl).getByTestId("p3-design-lab-conversion-step-extract_design_objects")).toHaveClass("is-done");
  expect(within(conversionControl).getByTestId("p3-design-lab-conversion-step-generate_design_draft")).toHaveClass("is-current");

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "下一窗口" }));
  expect(within(workspace).queryByTestId("p3-design-lab-conversion-control")).not.toBeInTheDocument();
  fireEvent.click(within(morphPlatform).getByRole("button", { name: "上一窗口" }));
  expect(await within(workspace).findByRole("button", { name: "正在生成软设" })).toBeDisabled();
  expect(postMock.mock.calls.filter(([url]) => url === "/software-design-v2/sessions/p3dl-1/conversion")).toHaveLength(1);

  await act(async () => {
    resolveConversion({
      data: buildSession(inputPackage, "draft_ready", {
        conversion: buildConversion("draft_ready", "standard_sdd_draft"),
      }),
    });
  });

  await waitFor(() => expect(within(workspace).queryByText("正在调用 Dify 生成软件设计说明")).not.toBeInTheDocument());
});

test("shows converter readiness feedback and blocks conversion when Dify API key is missing", async () => {
  const inputPackage = buildInputPackage();
  const createdSession = buildSession(inputPackage, "created", {
    status: "created",
    conversion: buildConversion("conversion_pending", "standard_sdd_draft", {
      converter: buildConverter({
        readiness: {
          ready: false,
          status: "missing_configuration",
          message: "DIFY_API_KEY is not configured for requirement-to-sdd-dify-workflow",
          required_config_keys: ["CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"],
          missing_config_keys: ["CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"],
          configured: { dify_api_key: false },
          operator_hint: "请在本地或部署环境配置 CODEFACTORY_P3_DIFY_API_KEY，或兼容配置 DIFY_API_KEY。",
        },
      }),
    }),
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
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "新建软设" }));
  fireEvent.click(screen.getByRole("button", { name: "创建软设会话" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design-v2/sessions", expect.any(Object)));

  const readiness = await within(workspace).findByTestId("p3-design-lab-converter-readiness");
  expect(within(readiness).getByText("转换器未就绪")).toBeInTheDocument();
  expect(within(readiness).getByText(/CODEFACTORY_P3_DIFY_API_KEY/)).toBeInTheDocument();

  const conversionButton = within(workspace).getByRole("button", { name: "执行基础转换" });
  expect(conversionButton).toBeDisabled();
  fireEvent.click(conversionButton);
  expect(postMock.mock.calls.filter(([url]) => url === "/software-design-v2/sessions/p3dl-1/conversion")).toHaveLength(0);
});

test("shows scoped patch waiting and local failure feedback inside the inspector", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
  });
  let rejectScopedTurn: (reason?: unknown) => void = () => {};
  const scopedTurnPromise = new Promise<never>((_, reject) => {
    rejectScopedTurn = reject;
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return scopedTurnPromise;
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  const input = within(inspector).getByLabelText("局部 AI 沟通输入");
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));
  expect(await within(inspector).findByText("请先填写局部调整要求。")).toBeInTheDocument();
  fireEvent.change(input, { target: { value: "扩写接口边界和异常处理。" } });
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));

  expect(await within(inspector).findByText("正在生成局部补丁提案")).toBeInTheDocument();
  expect(within(inspector).getByText("远端工作流通常约 180 秒，本地回退会更快。")).toBeInTheDocument();
  expect(input).toBeDisabled();
  expect(within(inspector).getByRole("button", { name: "生成局部补丁提案" })).toBeDisabled();
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));
  expect(postMock.mock.calls.filter(([url]) => url === "/software-design-v2/sessions/p3dl-1/turns")).toHaveLength(1);

  await act(async () => {
    rejectScopedTurn(new Error("remote scoped dify workflow request failed: scoped_context_json is required in input form"));
  });

  expect(await within(inspector).findByText("局部补丁提案生成失败")).toBeInTheDocument();
  expect(within(inspector).getByText(/scoped_context_json is required in input form/)).toBeInTheDocument();
  expect(input).toBeEnabled();
});

test("keeps scoped patch job visible and locked when switching away from the design block", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
  });
  let resolveScopedTurn: (value: unknown) => void = () => {};
  const scopedTurnPromise = new Promise((resolve) => {
    resolveScopedTurn = resolve;
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return scopedTurnPromise;
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  fireEvent.change(within(inspector).getByLabelText("局部 AI 沟通输入"), {
    target: { value: "扩写接口边界和异常处理。" },
  });
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));

  const jobStatus = await within(workspace).findByTestId("p3-design-workspace-job-status");
  expect(jobStatus).toHaveTextContent("正在片段修改");
  expect(jobStatus).toHaveClass("p3-design-workspace-job-status");
  expect(within(jobStatus).getByText("1. 设计目标与范围")).toBeInTheDocument();
  expect(within(jobStatus).getByRole("button", { name: "定位当前工作" })).toBeInTheDocument();
  await act(async () => {
    vi.advanceTimersByTime(42_000);
  });
  expect(within(jobStatus).getByText("已等待 00:42 / 通常约 180 秒")).toBeInTheDocument();

  const requirementDocumentObject = within(morphPlatform).getByTestId("stage-object-requirement");
  fireEvent.click(within(requirementDocumentObject).getByText("系统应支持创建规划任务、识别冲突、协同确认、形成处置记录。"));
  expect(within(inspector).getByText("对象：核心业务流程")).toBeInTheDocument();
  expect(within(workspace).getByTestId("p3-design-workspace-job-status")).toHaveTextContent("正在片段修改");

  fireEvent.click(within(jobStatus).getByRole("button", { name: "定位当前工作" }));
  expect(within(inspector).getByText("对象：1. 设计目标与范围")).toBeInTheDocument();
  expect(within(inspector).getByRole("button", { name: "生成局部补丁提案" })).toBeDisabled();
  expect(within(inspector).getByText("正在处理本段")).toBeInTheDocument();
  expect(postMock.mock.calls.filter(([url]) => url === "/software-design-v2/sessions/p3dl-1/turns")).toHaveLength(1);

  await act(async () => {
    resolveScopedTurn({
      data: {
        turn: {
          turn_id: "p3turn-scoped-running-1",
          turn_type: "scoped_design_edit",
          user_input: "扩写接口边界和异常处理。",
          normalized_intent: "scoped_design_edit",
          assistant_message: "已生成局部补丁提案：建议扩写当前段落。",
          scope_anchor: {
            anchor_type: "design_block",
            section_id: "goal",
            block_id: "goal-body",
            design_revision_id: "v0.1",
          },
          patch_proposal: {
            proposal_id: "patch-scoped-running-1",
            base_revision_id: "v0.1",
            target_anchor: { section_id: "goal", block_id: "goal-body" },
            operations: [],
            proposal_type: "advice_only",
            applicability: {
              can_apply: false,
              reason: "operations_empty",
            },
            quality_notes: ["需要人工确认扩写内容。"],
            status: "proposed",
          },
        },
        session: buildSession(inputPackage, "patch_ready", {
          design_title: "空域协同规划软件设计说明",
          version_label: "v0.1",
        }),
      },
    });
  });

  expect(await within(workspace).findByText("当前工作已完成")).toBeInTheDocument();
  fireEvent.click(within(jobStatus).getByRole("button", { name: "定位当前工作" }));
  expect(within(inspector).getByText("对象：1. 设计目标与范围")).toBeInTheDocument();
  expect(await within(inspector).findByText("修改建议")).toBeInTheDocument();
});

test("executes design block quick actions through the scoped patch workflow", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
  });
  let resolveScopedTurn: (value: unknown) => void = () => {};
  const scopedTurnPromise = new Promise((resolve) => {
    resolveScopedTurn = resolve;
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return scopedTurnPromise;
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  const scopedInput = within(inspector).getByLabelText("局部 AI 沟通输入");
  fireEvent.click(within(inspector).getByRole("button", { name: "填入扩写本段" }));
  expect(scopedInput).toHaveValue("扩写当前段落，补充模块边界和设计理由。");
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));

  expect(await within(inspector).findByText("正在生成局部补丁提案")).toBeInTheDocument();
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-design-v2/sessions/p3dl-1/turns",
      expect.objectContaining({
        turn_type: "scoped_design_edit",
        interaction_mode: "propose_patch",
        user_input: "扩写当前段落，补充模块边界和设计理由。",
      }),
    ),
  );
  expect(within(inspector).getByRole("button", { name: "填入扩写本段" })).toBeDisabled();

  await act(async () => {
    resolveScopedTurn({
      data: {
        turn: {
          turn_id: "p3turn-scoped-action-1",
          turn_type: "scoped_design_edit",
          user_input: "扩写当前段落，补充模块边界和设计理由。",
          normalized_intent: "scoped_design_edit",
          assistant_message: "已生成局部补丁提案：建议扩写当前段落。",
          scope_anchor: {
            anchor_type: "design_block",
            section_id: "goal",
            block_id: "goal-body",
            design_revision_id: "v0.1",
          },
          patch_proposal: {
            proposal_id: "patch-scoped-action-1",
            base_revision_id: "v0.1",
            target_anchor: { section_id: "goal", block_id: "goal-body" },
            operations: [],
            proposal_type: "advice_only",
            applicability: {
              can_apply: false,
              reason: "operations_empty",
            },
            quality_notes: ["需要人工确认扩写内容。"],
            status: "proposed",
          },
        },
        session: buildSession(inputPackage, "patch_ready", {
          design_title: "空域协同规划软件设计说明",
          version_label: "v0.1",
        }),
      },
    });
  });

  expect(await within(inspector).findByText("修改建议")).toBeInTheDocument();
  expect(within(inspector).getByText("未形成可应用补丁")).toBeInTheDocument();
  expect(within(inspector).getByText("当前结果缺少可执行 operations，不能写入正文。")).toBeInTheDocument();
  expect(within(inspector).getByText("需要人工确认扩写内容。")).toBeInTheDocument();
  expect(within(inspector).queryByText("不可自动应用")).not.toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "应用到文档" })).not.toBeInTheDocument();
});

test("shows section replacement candidates with explicit confirmation before applying", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
  });
  const replacementTurn = {
    turn_id: "p3turn-section-1",
    turn_type: "scoped_design_edit",
    user_input: "把本节改成分层架构可映射的结构。",
    normalized_intent: "scoped_design_edit",
    assistant_message: "已生成整节替换候选。",
    scope_anchor: {
      anchor_type: "design_block",
      section_id: "goal",
      block_id: "goal-body",
      design_revision_id: "v0.1",
    },
    patch_proposal: {
      proposal_id: "patch-section-1",
      base_revision_id: "v0.1",
      proposal_type: "section_replacement_candidate",
      target_anchor: { section_id: "goal", block_id: "goal-body" },
      operations: [
        {
          op: "replace_section_blocks",
          section_id: "goal",
          blocks: [
            {
              block_id: "goal-layer-boundary",
              title: "分层职责边界",
              content: "明确展示层、应用层和数据层在规划任务管理中的职责。",
              kind: "paragraph",
              source_refs: ["REQ-3.2"],
            },
            {
              block_id: "goal-trace-map",
              title: "追溯映射入口",
              content: "将需规条款映射到模块、能力和接口约束。",
              kind: "paragraph",
              source_refs: ["REQ-3.2"],
            },
          ],
        },
      ],
      applicability: {
        can_apply: true,
        reason: "ready",
      },
      quality_notes: ["替换本节后需要检查功能树映射。"],
      status: "proposed",
    },
  };
  const scopedSession = buildSession(inputPackage, "patch_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    turns: [replacementTurn],
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return Promise.resolve({ data: { turn: replacementTurn, session: scopedSession } });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  fireEvent.change(within(inspector).getByLabelText("局部 AI 沟通输入"), {
    target: { value: "把本节改成分层架构可映射的结构。" },
  });
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));

  expect(await within(inspector).findByText("整节替换候选")).toBeInTheDocument();
  expect(within(inspector).getByText("待确认")).toBeInTheDocument();
  expect(within(inspector).getByText("分层职责边界")).toBeInTheDocument();
  expect(within(inspector).getByText("明确展示层、应用层和数据层在规划任务管理中的职责。")).toBeInTheDocument();
  expect(within(inspector).getByRole("button", { name: "确认替换本节" })).toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "应用到文档" })).not.toBeInTheDocument();
});

test("shows unsupported scoped patch operations as non-protocol patch diagnostics", async () => {
  const inputPackage: P3DesignLabTestInputPackage = {
    ...buildInputPackage(),
    related_designs: [
      {
        software_design_id: "p3dl-1",
        title: "空域协同规划软件设计说明",
        version_label: "v0.1",
        status: "draft_ready",
        created_at: "2026-05-13T10:00:00Z",
        updated_at: "2026-05-13T10:20:00Z",
      },
    ],
  };
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    conversion: buildConversion("draft_ready", "standard_sdd_draft"),
  });
  const legacyTurn = {
    turn_id: "p3turn-legacy-op",
    turn_type: "scoped_design_edit",
    user_input: "替换当前段落。",
    normalized_intent: "scoped_design_edit",
    assistant_message: "已生成旧格式补丁。",
    scope_anchor: {
      anchor_type: "design_block",
      section_id: "goal",
      block_id: "goal-body",
      design_revision_id: "v0.1",
    },
    patch_proposal: {
      proposal_id: "patch-legacy-op",
      base_revision_id: "v0.1",
      proposal_type: "needs_manual_merge",
      target_anchor: { section_id: "goal", block_id: "goal-body" },
      operations: [{ op: "replace_paragraph", content: "旧格式补丁正文。" }],
      applicability: {
        can_apply: false,
        reason: "unsupported_operations",
        unsupported_ops: ["replace_paragraph"],
      },
      diagnostics: {
        protocol_status: "unsupported_operations",
        operation_count: 1,
        unsupported_ops: ["replace_paragraph"],
      },
      quality_notes: ["Dify 返回了旧格式操作。"],
      status: "proposed",
    },
  };
  const scopedSession = buildSession(inputPackage, "patch_ready", {
    design_title: "空域协同规划软件设计说明",
    version_label: "v0.1",
    turns: [legacyTurn],
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/input-packages") {
      return Promise.resolve({ data: { items: [inputPackage] } });
    }
    if (url === "/software-design-v2/sessions/p3dl-1") {
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
  postMock.mockImplementation((url: string) => {
    if (url === "/software-design-v2/sessions/p3dl-1/turns") {
      return Promise.resolve({ data: { turn: legacyTurn, session: scopedSession } });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "进入编辑" }));
  expect(await within(workspace).findByRole("heading", { name: "软设工作区" })).toBeInTheDocument();

  const morphPlatform = within(workspace).getByTestId("design-morph-canvas-platform");
  const designDocumentObject = within(morphPlatform).getByTestId("stage-object-document");
  fireEvent.click(within(designDocumentObject).getByText("覆盖协同规划核心能力。"));
  const inspector = within(workspace).getByTestId("design-morph-inspector");
  fireEvent.change(within(inspector).getByLabelText("局部 AI 沟通输入"), {
    target: { value: "替换当前段落。" },
  });
  fireEvent.click(within(inspector).getByRole("button", { name: "生成局部补丁提案" }));

  expect(await within(inspector).findByText("非协议补丁")).toBeInTheDocument();
  expect(within(inspector).getByText("不支持的操作：replace_paragraph")).toBeInTheDocument();
  expect(within(inspector).getByText("Dify 返回了旧格式操作。")).toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "应用到文档" })).not.toBeInTheDocument();
});

test("renders structured software design subsections, tables, and diagrams from converter output", async () => {
  const inputPackage = buildInputPackage();
  const convertedSession = buildSession(inputPackage, "draft_ready", {
    design_document: {
      title: "空域协同规划软件设计说明",
      version_label: "v0.1",
      sections: [
        {
          section_id: "architecture",
          title: "4. 总体架构",
          content: "总体采用统一服务优先。",
          status: "generated",
          source_refs: ["REQ-3.2"],
          children: [
            {
              section_id: "architecture-context",
              title: "4.1 架构上下文",
              content: "P2 冻结需规、P3 转换器和 Dify 工作流通过明确协议交接。",
              status: "generated",
              source_refs: ["REQ-3.2"],
            },
          ],
          blocks: [
            {
              block_id: "architecture-summary",
              kind: "paragraph",
              content: "总体采用统一服务优先。",
              source_refs: ["REQ-3.2"],
            },
            {
              block_id: "architecture-table",
              kind: "table",
              title: "表 4-1 总体分层表",
              columns: ["层次", "职责"],
              rows: [
                ["展示层", "承载软设文档和转换控制"],
                ["转换层", "调用 Dify 并规范化输出"],
              ],
              source_refs: ["REQ-3.2"],
            },
            {
              block_id: "architecture-diagram",
              kind: "diagram",
              title: "图 4-1 转换链路图",
              diagram_type: "mermaid",
              content: "flowchart LR\n  P2[P2 冻结需规] --> P3[P3 转换器]\n  P3 --> Dify[Dify 工作流]",
              source_refs: ["REQ-3.2"],
            },
          ],
        },
      ],
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
      return Promise.resolve({ data: convertedSession });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p3-design-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("P3 Software Design Lab")).toBeInTheDocument();
  const workspace = screen.getByTestId("p3-design-lab-workspace");
  fireEvent.click(within(workspace).getByRole("button", { name: "新建软设" }));
  fireEvent.click(screen.getByRole("button", { name: "创建软设会话" }));

  expect(await within(workspace).findByRole("heading", { name: "4.1 架构上下文" })).toBeInTheDocument();
  expect(within(workspace).getByRole("table", { name: "表 4-1 总体分层表" })).toBeInTheDocument();
  expect(within(workspace).getByText("转换层")).toBeInTheDocument();
  expect(within(workspace).getByText("图 4-1 转换链路图")).toBeInTheDocument();
  expect(within(workspace).getByText((content) => content.includes("flowchart LR"))).toBeInTheDocument();
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

function buildFunctionTreeFixture() {
  return {
    tree_id: "function-tree-p3dl-1",
    title: "空域协同规划软件功能树",
    root: {
      node_id: "function-tree-root",
      title: "空域协同规划软件",
      node_type: "root",
      children: [
        {
          node_id: "function-node-planning-task",
          title: "规划任务管理",
          node_type: "module",
          source_refs: ["REQ-3.2"],
          design_refs: ["goal"],
          children: [
            {
              node_id: "cap-planning-task",
              title: "规划任务管理能力",
              node_type: "capability",
              source_refs: ["REQ-3.2"],
              design_refs: ["goal"],
              children: [
                {
                  node_id: "fn-create-task",
                  title: "创建规划任务",
                  node_type: "function",
                  status: "confirmed",
                  source_refs: ["REQ-3.2"],
                  design_refs: ["goal"],
                  architecture_refs: ["cmp-task-workbench", "cmp-task-service"],
                },
              ],
            },
          ],
        },
      ],
    },
  };
}

function buildLayeredArchitectureFixture() {
  return {
    architecture_id: "layered-architecture",
    title: "五层分层架构",
    pattern: "business-module-oriented-layered-architecture",
    source_refs: ["REQ-3.2"],
    design_refs: ["goal"],
    layers: [
      {
        layer_id: "presentation",
        name: "展示层",
        responsibility: "承载规划任务创建入口和用户反馈。",
        inputs: ["规划任务创建指令"],
        outputs: ["创建请求"],
        components: [
          {
            component_id: "cmp-task-workbench",
            name: "规划任务工作台",
            component_type: "ui_workspace",
            module_refs: ["planning-task"],
            function_refs: ["fn-create-task"],
          },
        ],
      },
      {
        layer_id: "service",
        name: "服务层",
        responsibility: "承载规划任务规则、状态校验和提交编排。",
        inputs: ["创建请求"],
        outputs: ["任务状态"],
        components: [
          {
            component_id: "cmp-task-service",
            name: "规划任务服务",
            component_type: "domain_service",
            module_refs: ["planning-task"],
            function_refs: ["fn-create-task"],
          },
        ],
      },
    ],
    function_layer_mappings: [
      {
        mapping_id: "map-fn-create-task-ui",
        function_node_id: "fn-create-task",
        function_title: "创建规划任务",
        layer_id: "presentation",
        layer_name: "展示层",
        component_id: "cmp-task-workbench",
        component_name: "规划任务工作台",
        role: "ui_entry",
        mapping_status: "confirmed",
        module_refs: ["planning-task"],
        source_refs: ["REQ-3.2"],
        design_refs: ["goal"],
      },
      {
        mapping_id: "map-fn-create-task-service",
        function_node_id: "fn-create-task",
        function_title: "创建规划任务",
        layer_id: "service",
        layer_name: "服务层",
        component_id: "cmp-task-service",
        component_name: "规划任务服务",
        role: "domain_service",
        mapping_status: "confirmed",
        module_refs: ["planning-task"],
        source_refs: ["REQ-3.2"],
        design_refs: ["goal"],
      },
    ],
    cross_layer_relations: [
      {
        relation_id: "rel-create-task",
        title: "创建规划任务提交",
        from_layer_id: "presentation",
        from_component_id: "cmp-task-workbench",
        to_layer_id: "service",
        to_component_id: "cmp-task-service",
        relation_type: "command_call",
        function_refs: ["fn-create-task"],
        source_refs: ["REQ-3.2"],
      },
    ],
    mapping_quality: {
      mapped_function_count: 1,
      unmapped_function_count: 0,
      pending_confirmation_count: 0,
    },
  };
}

type P3DesignLabTestInputPackage = Omit<ReturnType<typeof buildInputPackage>, "related_designs"> & {
  related_designs: Array<{
    software_design_id: string;
    title: string;
    version_label: string;
    status: string;
    created_at: string;
    updated_at: string;
  }>;
};

function buildSession(
  inputPackage: ReturnType<typeof buildInputPackage> | P3DesignLabTestInputPackage,
  status: string,
  overrides: Record<string, unknown> = {},
) {
  const designTitle = typeof overrides.design_title === "string" ? overrides.design_title : "空域协同规划软件设计说明";
  const versionLabel = typeof overrides.version_label === "string" ? overrides.version_label : "SoftwareDesignBaseline v2";
  const session = {
    session_id: "p3dl-1",
    input_package: inputPackage,
    status: typeof overrides.status === "string" ? overrides.status : status,
    design_title: designTitle,
    version_label: versionLabel,
    generation_policy: {
      architecture_preference: "统一服务优先，保留拆分点",
      module_granularity: "3-5 个业务模块，不拆太细",
      output_style: "按标准软设正文写，不写聊天语气",
    },
    design_document:
      status === "created"
        ? null
        : {
            title: designTitle,
            version_label: versionLabel,
            sections: [{ section_id: "goal", title: "1. 设计目标与范围", content: "覆盖协同规划核心能力。" }],
          },
    design_baseline:
      status === "created"
        ? null
        : {
            baseline_id: "sdb2-1",
            architecture_mode: "unified_service",
            modules: [{ module_id: "planning-task", name: "规划任务管理" }],
            function_tree: {
              tree_id: "function-tree-p3dl-1",
              title: "空域协同规划软件功能树",
              root: {
                node_id: "function-tree-root",
                title: "空域协同规划软件",
                node_type: "root",
                children: [
                  {
                    node_id: "function-node-planning-task",
                    title: "规划任务管理",
                    node_type: "module",
                    source_refs: ["REQ-3.2"],
                    design_refs: ["goal"],
                    children: [
                      {
                        node_id: "cap-planning-task",
                        title: "规划任务管理能力",
                        node_type: "capability",
                        children: [
                          { node_id: "fn-create-task", title: "创建规划任务", node_type: "function", source_refs: ["REQ-3.2"] },
                          { node_id: "api-create-task", title: "POST /planning-tasks", node_type: "interface" },
                          { node_id: "state-draft", title: "draft", node_type: "state" },
                        ],
                      },
                      { node_id: "data-task", title: "PlanningTask", node_type: "data" },
                      { node_id: "quality-task-trace", title: "规划任务状态变化必须保留留痕记录", node_type: "quality" },
                    ],
                  },
                ],
              },
            },
          },
    workorder_projection:
      status === "created"
        ? null
        : {
            tree: {
              node_id: "p4-projection-root",
              title: "P4-WO-StageLab-Workbench",
              node_type: "projection_package",
              description: "P3 软件设计说明向 P4 研发工单的候选投影。",
              readiness: "preview_only",
              children: [
                {
                  node_id: "branch-common-workbench",
                  title: "A. 共性工作台工具包",
                  node_type: "toolkit_branch",
                  readiness: "ready",
                  children: [{ node_id: "wo-a1", title: "WO-A1 StageLabShell 组件生成器", node_type: "workorder", readiness: "ready" }],
                },
                {
                  node_id: "branch-p3-adapter",
                  title: "B. P3 适配工具包",
                  node_type: "toolkit_branch",
                  description: "该分支是 P4 工单投影的一部分，包含 P3 专属 Adapter、输入列表快照适配器和 ViewModel 组装脚本。",
                  readiness: "pending",
                  source_refs: ["SoftwareDesign.modules.p3Adapter"],
                  depends_on: ["A. 共性工作台工具包"],
                  acceptance: "能把需规列表和当前需规对象映射到工作台模型。",
                  children: [{ node_id: "wo-b1", title: "WO-B1 DTO -> ViewModel Adapter", node_type: "workorder", readiness: "ready" }],
                },
              ],
            },
            items: [{ item_id: "wo-b1", title: "WO-B1 DTO -> ViewModel Adapter", module_id: "p3-adapter", readiness: "ready" }],
          },
    turns: [],
    conversion:
      overrides.conversion ??
      (status === "created" ? buildConversion("conversion_pending", "standard_sdd_draft") : buildConversion("draft_ready", "standard_sdd_draft")),
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
      status === "created" || session.status === "conversion_pending"
        ? inputPackage
        : {
            ...inputPackage,
            related_designs: [
              {
                software_design_id: session.session_id,
                title: designTitle,
                version_label: versionLabel,
                status: session.status,
                created_at: "2026-05-13T10:00:00Z",
                updated_at: "2026-05-13T10:20:00Z",
              },
            ],
          },
  };
}

function buildConverter(overrides: Record<string, unknown> = {}) {
  return {
    converter_id: "requirement-to-sdd-dify-workflow",
    name: "P3 Requirement to SDD Dify Workflow",
    converter_type: "dify_workflow",
    protocol: "p3-design-converter-protocol@1",
    status: "active",
    requires: { dify_api: true, workflow_id: "external" },
    readiness: {
      ready: true,
      status: "ready",
      message: "P3 Dify 转换器已检测到 API Key，可执行需规转软设转换。",
      required_config_keys: ["CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"],
      missing_config_keys: [],
      configured: { dify_api_key: true },
    },
    ...overrides,
  };
}

function buildConversion(status: string, strategy: string, overrides: Record<string, unknown> = {}) {
  const done = status === "draft_ready";
  return {
    status,
    strategy,
    converter: buildConverter(),
    strategy_options: [
      { value: "standard_sdd_draft", label: "标准软设草稿生成", description: "按标准软设章节生成初稿。" },
      { value: "component_first", label: "组件优先拆解", description: "优先抽取组件、接口和可复用工作台对象。" },
      { value: "p4_projection_first", label: "P4 投影优先", description: "优先组织下游工具包和工单分支。" },
    ],
    steps: [
      { step_id: "read_requirement", title: "读取需规冻结包", description: "加载正文、结构化条款和冻结快照。", status: done ? "done" : "pending" },
      { step_id: "extract_design_objects", title: "抽取设计对象", description: "抽取模块、接口、数据对象和质量属性候选。", status: done ? "done" : "pending" },
      { step_id: "generate_design_draft", title: "生成软设草稿", description: "生成 A4 正文草稿和结构化设计事实初稿。", status: done ? "done" : "pending" },
      { step_id: "map_traceability", title: "建立追溯映射", description: "建立需规条款到章节、模块和接口的追溯。", status: done ? "done" : "pending" },
    ],
    draft_preview: done
      ? {
          title: "空域协同规划软件设计说明（设计方案 01）",
          sections: ["1. 设计目标与范围", "2. 总体架构", "3. 模块划分"],
        }
      : null,
    traceability_summary: done ? { mapped_clause_count: 2, target_count: 4, pending_confirmation_count: 0 } : null,
    ...overrides,
  };
}

function expectCanvasWorkspaceColumnsToStretch() {
  const pageCss = readFileSync(resolve(process.cwd(), "src/pages/P3DesignLabPage.css"), "utf8");
  const canvasCss = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/design-morph-canvas.css"), "utf8");

  expect(pageCss).toMatch(/\.p3-design-morph-workspace\s*{[^}]*align-items:\s*stretch;/s);
  expect(pageCss).toMatch(/\.p3-design-morph-main,\s*\.p3-design-morph-side\s*{[^}]*align-self:\s*stretch;/s);
  expect(pageCss).toMatch(/\.p3-design-morph-main\s*{[^}]*display:\s*grid;/s);
  expect(canvasCss).toMatch(/\.design-morph-platform\s*{[^}]*height:\s*100%;/s);
  expect(canvasCss).toMatch(/\.design-morph-canvas-shell\s*{[^}]*min-height:\s*0;/s);
}

function expectDesignMorphStageFrameHeaderToBeInline() {
  const canvasCss = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/design-morph-canvas.css"), "utf8");
  const platformSource = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/DesignMorphCanvasPlatform.tsx"), "utf8");

  expect(platformSource).toContain("design-morph-object-title-row");
  expect(canvasCss).toMatch(/\.design-morph-object-title-copy\s*{[^}]*display:\s*flex;/s);
  expect(canvasCss).toMatch(/\.design-morph-object-title-copy\s*{[^}]*align-items:\s*center;/s);
  expect(canvasCss).toMatch(/\.design-morph-object-title-meta\s*{[^}]*font-size:\s*10px;/s);
  expect(canvasCss).toMatch(/\.design-morph-object-title-meta\s*{[^}]*background:\s*rgba\(47,\s*119,\s*189,\s*0\.1\);/s);
  expect(canvasCss).not.toMatch(/\.design-morph-object-title-copy\s*{[^}]*display:\s*grid;/s);
}

function expectLayeredArchitectureSwimlanesToFillStage() {
  const canvasCss = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/design-morph-canvas.css"), "utf8");

  expect(canvasCss).toMatch(/\.design-morph-layered-architecture-body\s*{[^}]*align-content:\s*stretch;/s);
  expect(canvasCss).toMatch(/\.design-morph-layered-architecture-body\s*{[^}]*grid-auto-rows:\s*minmax\(104px,\s*1fr\);/s);
  expect(canvasCss).not.toMatch(/\.design-morph-layered-architecture-body\s*{[^}]*align-content:\s*start;/s);
}

function expectArchitectureViewRelationsToFollowContent() {
  const canvasCss = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/design-morph-canvas.css"), "utf8");

  expect(canvasCss).toMatch(/\.design-morph-architecture-structure\s*{[^}]*grid-template-rows:\s*auto auto;/s);
  expect(canvasCss).toMatch(/\.design-morph-architecture-structure\s*{[^}]*align-content:\s*start;/s);
  expect(canvasCss).not.toMatch(/\.design-morph-architecture-structure\s*{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s*auto;/s);
  expect(canvasCss).not.toMatch(/\.design-morph-architecture-structure\s*{[^}]*min-height:\s*100%;/s);
}

function expectArchitectureViewStageHeightToFollowSavedLayout() {
  const canvasCss = readFileSync(resolve(process.cwd(), "src/components/stageWorkbench/design-morph-canvas.css"), "utf8");

  expect(canvasCss).not.toMatch(/\.is-architecture-views-stage-object\s*{[^}]*max-height:/s);
  expect(canvasCss).not.toMatch(/\.is-architecture-views-stage-object\s+\.design-morph-object-body\s*{[^}]*max-height:/s);
}

function expectWorkspaceFullscreenToCoverViewport() {
  const pageCss = readFileSync(resolve(process.cwd(), "src/pages/P3DesignLabPage.css"), "utf8");

  expect(pageCss).toMatch(/\.p3-design-lab-workspace-panel\.is-web-fullscreen\s*{[^}]*inset:\s*0;/s);
}
