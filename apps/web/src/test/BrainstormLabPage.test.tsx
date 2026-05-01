import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";
import type { BrainstormSession, BrainstormTurnEnvelope } from "../lib/api";

const getMock = vi.fn();
const postMock = vi.fn();
const scrollIntoViewMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  scrollIntoViewMock.mockReset();
  HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;
});

test("keeps Brainstorming Lab view tabs explicit while business state changes", async () => {
  let session = buildSession("created");
  const deferredTurn = createDeferred<{ data: BrainstormTurnEnvelope }>();

  getMock.mockImplementation((url: string) => {
    if (url === "/brainstorm/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/brainstorm/providers") {
      return Promise.resolve({
        data: {
          items: [
            { provider_id: "mock", name: "Mock Provider", status: "active" },
            { provider_id: "deepseek", name: "DeepSeek", status: "active" },
          ],
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/brainstorm/sessions") {
      expect(body).toMatchObject({
        topic: "空域运算软件需求规格探索",
        orchestrator_id: "xg-brainstorming-orchestrator",
        provider_id: "deepseek",
        write_policy: "patch_suggestion_only",
      });
      return Promise.resolve({ data: session });
    }
    if (url === "/brainstorm/sessions/bs-airspace-001/turns") {
      if ((body as { user_input?: string })?.user_input === "A，先按计算分析工具理解") {
        return deferredTurn.promise;
      }
      if ((body as { user_input?: string })?.user_input === "B，先确认输出") {
        return Promise.resolve({ data: buildTurnEnvelope() });
      }
      throw new Error(`unexpected turn body: ${JSON.stringify(body)}`);
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-brainstorm-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 Brainstorming Lab" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();

  expect(screen.getByRole("tab", { name: /组织器配置/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.getByRole("tab", { name: /当前 Turn/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.getByRole("tab", { name: /调用日志/ })).toHaveAttribute("aria-selected", "false");

  expect(screen.getByText("RequirementAnalysisOrchestrator 插槽")).toBeInTheDocument();
  expect(screen.getByText("可替换组织器")).toBeInTheDocument();
  expect(screen.getByText("启动参数")).toBeInTheDocument();
  expect(screen.getByText("稳定契约 / 输出协议")).toBeInTheDocument();
  expect(screen.getByText("XG Brainstorming Orchestrator")).toBeInTheDocument();
  expect(screen.getByText("XG Strong Rule Orchestrator")).toBeInTheDocument();
  expect(screen.getByText("DeepSeek")).toBeInTheDocument();
  expect(screen.getByText("替换组织器不能影响 P2 正式文档能力")).toBeInTheDocument();
  expect(screen.queryByText("CLI 式问答区")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/brainstorm/sessions", expect.any(Object)));

  expect(screen.getByRole("tab", { name: /组织器配置/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /会话管理.*已创建/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.getByText("会话已创建：bs-airspace-001")).toBeInTheDocument();
  expect(screen.queryByText("CLI 式问答区")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /会话管理/ }));

  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByRole("heading", { name: "会话管理" })).not.toBeInTheDocument();
  expect(await screen.findByText("会话 bs-airspace-001")).toBeInTheDocument();
  expect(screen.getByText("CLI 式问答区")).toBeInTheDocument();
  expect(screen.getAllByText("Provider deepseek").length).toBeGreaterThan(0);
  expect(screen.getByText("空域运算软件需求规格探索")).toBeInTheDocument();
  expect(screen.getByText("只生成 document_patch 建议")).toBeInTheDocument();

  const input = screen.getByPlaceholderText("输入 A / 继续 / 更正式 / 或直接描述需求...");
  expect(input.tagName).toBe("TEXTAREA");
  fireEvent.change(input, { target: { value: "第一行需求\n第二行补充" } });
  fireEvent.keyDown(input, { key: "Enter", code: "Enter", shiftKey: true });
  expect(input).toHaveValue("第一行需求\n第二行补充");

  fireEvent.change(input, { target: { value: "A，先按计算分析工具理解" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/brainstorm/sessions/bs-airspace-001/turns", {
      user_input: "A，先按计算分析工具理解",
    }),
  );

  expect(screen.getByText("A，先按计算分析工具理解")).toBeInTheDocument();
  expect(screen.getByText("正在生成回应...")).toBeInTheDocument();

  const envelope = buildTurnEnvelope();
  session = envelope.session;
  scrollIntoViewMock.mockClear();
  deferredTurn.resolve({ data: envelope });

  await screen.findByText("基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。");
  expect(scrollIntoViewMock).toHaveBeenCalled();

  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /当前 Turn.*turn-0001/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.queryByText("当前 Turn turn-0001")).not.toBeInTheDocument();
  expect(screen.getByText("需求规格完成度树")).toBeInTheDocument();
  expect(screen.queryByText("问题工作项")).not.toBeInTheDocument();
  expect(screen.queryByText("已确认事实")).not.toBeInTheDocument();
  expect(screen.queryByText("文档修补建议")).not.toBeInTheDocument();
  expect(screen.getByText("focus: SPEC-1.2")).toBeInTheDocument();
  expect(screen.getAllByText("1. 系统概述").length).toBeGreaterThan(0);
  expect(screen.getByText("系统要做什么？")).toBeInTheDocument();
  expect(screen.getByText("系统边界是什么？")).toBeInTheDocument();
  expect(screen.queryByText("回答摘要：系统初步定位为空域计算分析工具")).not.toBeInTheDocument();
  expect(screen.getByText("沟通路径")).toBeInTheDocument();
  expect(screen.getAllByText("turn-0001").length).toBeGreaterThan(0);
  expect(screen.getByText("SPEC-1.1")).toBeInTheDocument();
  expect(screen.getByText("推荐")).toBeInTheDocument();
  expect(screen.getByText("先确认输入")).toBeInTheDocument();
  expect(screen.getByText("先确认输出")).toBeInTheDocument();
  const quickOptions = screen.getByLabelText("快捷回复选项");
  const optionRows = within(quickOptions).getAllByTestId("brainstorm-quick-option");
  expect(optionRows).toHaveLength(3);
  fireEvent.click(optionRows[1]);
  expect(postMock).not.toHaveBeenCalledWith("/brainstorm/sessions/bs-airspace-001/turns", {
    user_input: "B，先确认输出",
  });

  fireEvent.click(within(optionRows[1]).getByRole("button", { name: "选择 B" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/brainstorm/sessions/bs-airspace-001/turns", {
      user_input: "B，先确认输出",
    }),
  );

  fireEvent.click(screen.getByRole("tab", { name: /当前 Turn/ }));

  expect(screen.getByText("当前 Turn 决策审计")).toBeInTheDocument();
  expect(screen.getByText("上轮系统留题")).toBeInTheDocument();
  expect(screen.getByText("本轮用户输入")).toBeInTheDocument();
  expect(screen.getByText("输入承接判断")).toBeInTheDocument();
  expect(screen.getByText("规格补充执行")).toBeInTheDocument();
  expect(screen.getByText("补充后状态回看")).toBeInTheDocument();
  expect(screen.getByText("本轮处理闭环")).toBeInTheDocument();
  expect(screen.getByText("下一轮交互设计")).toBeInTheDocument();
  expect(screen.getByText("决策依据")).toBeInTheDocument();
  expect(screen.queryByText("上一轮用户关注点（审计上下文）")).not.toBeInTheDocument();
  expect(screen.queryByText("系统理解与回应")).not.toBeInTheDocument();
  expect(screen.queryByText("影响的规格节点")).not.toBeInTheDocument();
  expect(screen.queryByText("本轮状态变化")).not.toBeInTheDocument();
  expect(screen.queryByText("下一轮建议话题")).not.toBeInTheDocument();
  expect(screen.getByText("SPEC-1.1")).toBeInTheDocument();
  expect(screen.getAllByText("quick_option_answer").length).toBeGreaterThan(0);
  expect(screen.getByText("系统初步定位为空域计算分析工具")).toBeInTheDocument();
  expect(screen.getAllByText("1.1 系统目标").length).toBeGreaterThan(0);
  expect(screen.getByText("系统目标已有可写入材料，当前节点可以关闭；输入数据章节仍需补齐。")).toBeInTheDocument();
  expect(screen.getByText("本轮输入已被吸收，并形成系统目标章节的正文建议；无需继续追问同一题。")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /调用日志/ }));

  expect(screen.getByRole("tab", { name: /调用日志.*2 条/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("Provider 调用日志")).toBeInTheDocument();
  expect(screen.getAllByText("call-0001").length).toBeGreaterThan(0);
  expect(screen.getByText(/deepseek-chat/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /组织器配置/ }));

  const stableContract = screen.getByTestId("brainstorm-stable-contract");
  expect(within(stableContract).getByText("正式需求规格文档")).toBeInTheDocument();
  expect(within(stableContract).getByText("P2 -> P3 输出")).toBeInTheDocument();
});

test("shows a protocol error instead of blanking when Current Turn misses required audit fields", async () => {
  const session = buildSession("created");
  const malformedEnvelope = buildMalformedTurnEnvelope();

  getMock.mockImplementation((url: string) => {
    if (url === "/brainstorm/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/brainstorm/providers") {
      return Promise.resolve({
        data: {
          items: [{ provider_id: "mock", name: "Mock Provider", status: "active" }],
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/brainstorm/sessions") {
      return Promise.resolve({ data: session });
    }
    if (url === "/brainstorm/sessions/bs-airspace-001/turns") {
      return Promise.resolve({ data: malformedEnvelope });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-brainstorm-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 Brainstorming Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/brainstorm/sessions", expect.any(Object)));

  fireEvent.click(screen.getByRole("tab", { name: /会话管理/ }));
  fireEvent.change(screen.getByPlaceholderText("输入 A / 继续 / 更正式 / 或直接描述需求..."), {
    target: { value: "A，先按计算分析工具理解" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));
  await screen.findByText("基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。");

  fireEvent.click(screen.getByRole("tab", { name: /当前 Turn/ }));

  expect(screen.getByText("当前 Turn 协议错误")).toBeInTheDocument();
  expect(screen.getByText(/previous_interaction/)).toBeInTheDocument();
  expect(screen.getByText(/spec_execution/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "重新开始验证" }));

  expect(screen.getByRole("tab", { name: /组织器配置/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /当前 Turn.*暂无/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.queryByText("当前 Turn 协议错误")).not.toBeInTheDocument();
});

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

function buildOrchestrators() {
  return {
    items: [
      {
        orchestrator_id: "xg-brainstorming-orchestrator",
        name: "XG Brainstorming Orchestrator",
        version: "0.1.0",
        stage: "P2",
        document_type: "xg",
        contract: "xg-orchestrator-contract@1",
        mode: "policy_interpreted",
        status: "active",
        description: "面向需求规格说明的开放式 Brainstorming 组织器。",
        entry: null,
        capabilities: ["free_text_input", "guided_question", "quick_options", "spec_tree_update", "document_patch", "turn_audit"],
        requires: { template: true, knowledge_binding: true, model_provider: "optional" },
        package_path: "orchestrators/xg/xg-brainstorming-orchestrator",
      },
      {
        orchestrator_id: "xg-strong-rule-orchestrator",
        name: "XG Strong Rule Orchestrator",
        version: "0.1.0",
        stage: "P2",
        document_type: "xg",
        contract: "xg-orchestrator-contract@1",
        mode: "local_runner",
        status: "active",
        description: "面向需求规格说明的强规则组织器。",
        entry: "runner.py",
        capabilities: ["rule_based_flow", "strict_turn_closure", "quick_options", "spec_tree_update", "document_patch", "turn_audit"],
        requires: { template: true, knowledge_binding: true, model_provider: "optional" },
        package_path: "orchestrators/xg/xg-strong-rule-orchestrator",
      },
    ] as const,
    stable_contract: buildStableContract(),
    output_protocol: [
      "previous_interaction",
      "input_relation",
      "spec_execution",
      "post_update_review",
      "closure_decision",
      "next_interaction",
      "decision_trace",
    ],
  };
}

function buildStableContract() {
  return {
    formal_document: true,
    template_object: true,
    knowledge_binding: true,
    draft_persistence: true,
    check_and_freeze: true,
    p2_to_p3_output: true,
  };
}

function buildSession(status: BrainstormSession["status"]): BrainstormSession {
  return {
    session_id: "bs-airspace-001",
    topic: "空域运算软件需求规格探索",
    status,
    orchestrator: buildOrchestrators().items[0],
    provider_id: "deepseek",
    model: "deepseek-chat",
    template_id: "81433号",
    knowledge_package_id: "airspace-domain-demo",
    write_policy: "patch_suggestion_only",
    stable_contract: buildStableContract(),
    messages: [
      {
        id: "msg-0001",
        role: "assistant",
        content: "我会先验证这个课题的需求边界。当前知识包只作为背景，不会自动写入正式规格。",
      },
    ],
    turns: [],
    confirmed_facts: [],
    open_questions: ["需要确认系统更偏向计算分析工具、协同规划平台，还是二者都有。"],
    document_patch: [],
    questions: [
      {
        question_id: "Q-001",
        content: "系统更偏向计算分析工具、协同规划平台，还是二者都有？",
        status: "open",
        target_section: "1.1 系统目标",
        source_turn_id: null,
        resolution_fact_ids: [],
      },
    ],
    facts: [],
    patches: [],
    spec_tree: buildSpecTree(),
    active_spec_node_id: "SPEC-1.1",
    turn_path: [],
    annotations: ["Lab 只生成 document_patch 建议，不直接写入正式需求规格草稿。"],
    risks: [],
    provider_logs: [],
    next_interaction: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  };
}

function buildTurnEnvelope(): BrainstormTurnEnvelope {
  const turn = {
    turn_id: "turn-0001",
    session_id: "bs-airspace-001",
    user_input: "A，先按计算分析工具理解",
    previous_interaction: {
      interaction_id: null,
      type: "none",
      prompt: "无，用户自由发起。",
      options: [],
      target_spec_node_ids: [],
      reason: "首轮没有上轮系统留题。",
    },
    input_relation: {
      relation: "none",
      reason: "首轮没有上轮系统留题。",
    },
    decision_trace: ["用户输入是本轮 Turn 起点。", "本轮影响 1.1 系统目标。"],
    normalized_input: {
      input_type: "quick_option_answer",
      matched_option: "A",
      matched_option_label: "先按计算分析工具理解",
      semantic: "系统初步定位为计算分析工具。",
    },
    spec_execution: {
      interpretation: {
        summary: "用户选择先按计算分析工具理解。",
        intent: "confirm_direction",
        confidence: "high",
      },
      assistant_message: "基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。",
      confirmed_facts: ["系统初步定位为空域计算分析工具"],
      affected_spec_nodes: [
        {
          node_id: "SPEC-1.1",
          title: "系统要做什么？",
          target_section: "1.1 系统目标",
          effect: "update",
          reason: "用户确认系统初步定位。",
        },
      ],
      document_patch: [
        {
          section: "1.1 系统目标",
          operation: "append_or_update",
          content: "本系统面向空域领域专家，支持围绕空域运算任务进行输入组织、计算分析与结果确认。",
        },
      ],
      state_changes: {
        closed_question_ids: ["Q-001"],
        created_question_ids: ["Q-002"],
        closed_spec_node_ids: ["SPEC-1.1"],
        next_active_spec_node_id: "SPEC-1.2",
      },
      annotations: ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
      risks: [],
    },
    post_update_review: {
      summary: "系统目标已有可写入材料，当前节点可以关闭；输入数据章节仍需补齐。",
      previous_interaction_resolved: true,
      current_spec_node_sufficient: true,
      needs_followup_on_same_topic: false,
      remaining_gaps: ["输入数据来源、计算结果形式、专家校核职责尚未确认。"],
    },
    closure_decision: {
      status: "closed",
      reason: "本轮输入已被吸收，并形成系统目标章节的正文建议；无需继续追问同一题。",
      next_action: "propose_next_interaction",
    },
    next_interaction: {
      interaction_id: "interaction-0001",
      type: "choice_question",
      prompt: "建议下一步确认输入数据来源和输出结果形式。",
      options: [
        { key: "A", label: "先确认输入" },
        { key: "B", label: "先确认输出" },
        { key: "C", label: "你来推进" },
      ],
      target_spec_node_ids: ["SPEC-1.2"],
      reason: "系统定位已确认，输入输出章节仍需补齐。",
    },
    confidence: "medium",
    service_steps: [
      { step: 1, title: "接收用户输入", status: "completed" },
      { step: 2, title: "读取会话状态", status: "completed" },
    ],
    raw_model_response: { mock: true },
    created_at: "2026-05-01T00:00:00Z",
  };
  return {
    session: {
      ...buildSession("waiting_user"),
      turns: [turn],
      messages: [
        ...buildSession("waiting_user").messages,
        { id: "msg-0002", role: "user", content: "A，先按计算分析工具理解", turn_id: "turn-0001" },
        {
          id: "msg-0003",
          role: "assistant",
          content: "基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。",
          turn_id: "turn-0001",
        },
      ],
      confirmed_facts: ["系统初步定位为空域计算分析工具"],
      open_questions: ["输入数据来源、计算结果形式、专家校核职责尚未确认。"],
      document_patch: turn.spec_execution.document_patch,
      questions: [
        {
          question_id: "Q-001",
          content: "系统更偏向计算分析工具、协同规划平台，还是二者都有？",
          status: "confirmed",
          target_section: "1.1 系统目标",
          source_turn_id: null,
          resolution_fact_ids: ["F-001"],
        },
        {
          question_id: "Q-002",
          content: "输入数据来源、计算结果形式、专家校核职责尚未确认。",
          status: "open",
          target_section: "2.1 输入数据",
          source_turn_id: "turn-0001",
          resolution_fact_ids: [],
        },
      ],
      facts: [
        {
          fact_id: "F-001",
          content: "系统初步定位为空域计算分析工具",
          source_turn_id: "turn-0001",
          source_question_ids: ["Q-001"],
          target_section: "1.1 系统目标",
        },
      ],
      patches: [
        {
          patch_id: "P-001",
          target_section: "1.1 系统目标",
          operation: "append_or_update",
          content: "本系统面向空域领域专家，支持围绕空域运算任务进行输入组织、计算分析与结果确认。",
          write_policy: "patch_suggestion_only",
          status: "proposed",
          source_fact_ids: ["F-001"],
          source_question_ids: ["Q-001"],
        },
      ],
      spec_tree: buildSpecTreeAfterFirstTurn(),
      active_spec_node_id: "SPEC-1.2",
      next_interaction: turn.next_interaction,
      turn_path: [
        {
          turn_id: "turn-0001",
          node_id: "SPEC-1.1",
          question_id: "Q-001",
          previous_interaction_id: null,
          input_relation: "none",
          affected_node_ids: ["SPEC-1.1"],
          next_interaction_id: "interaction-0001",
          closed_node_ids: ["SPEC-1.1"],
          answer_summary: "系统初步定位为空域计算分析工具",
        },
      ],
      annotations: turn.spec_execution.annotations,
      provider_logs: [
        {
          call_id: "call-0001",
          provider_id: "deepseek",
          model: "deepseek-chat",
          status: "completed",
          created_at: "2026-05-01T00:00:00Z",
        },
        {
          call_id: "call-0002",
          provider_id: "deepseek",
          model: "deepseek-chat",
          status: "completed",
          created_at: "2026-05-01T00:00:01Z",
        },
      ],
    },
    turn,
  };
}

function buildMalformedTurnEnvelope(): BrainstormTurnEnvelope {
  const envelope = buildTurnEnvelope();
  const malformedTurn = { ...envelope.turn } as Partial<BrainstormTurnEnvelope["turn"]>;
  delete malformedTurn.previous_interaction;
  delete malformedTurn.input_relation;
  delete malformedTurn.spec_execution;
  delete malformedTurn.post_update_review;
  delete malformedTurn.closure_decision;
  delete malformedTurn.next_interaction;
  delete malformedTurn.decision_trace;
  return {
    session: {
      ...envelope.session,
      turns: [malformedTurn as BrainstormTurnEnvelope["turn"]],
    },
    turn: malformedTurn as BrainstormTurnEnvelope["turn"],
  };
}

function buildSpecTree() {
  return [
    {
      node_id: "SPEC-1",
      title: "1. 系统概述",
      target_section: "1. 系统概述",
      status: "partial",
      answer_summary: "",
      completion_reason: "",
      children: [
        {
          node_id: "SPEC-1.1",
          title: "系统要做什么？",
          target_section: "1.1 系统目标",
          status: "open",
          answer_summary: "",
          completion_reason: "",
          children: [],
        },
        {
          node_id: "SPEC-1.2",
          title: "系统边界是什么？",
          target_section: "1.2 系统边界",
          status: "open",
          answer_summary: "",
          completion_reason: "",
          children: [],
        },
      ],
    },
    {
      node_id: "SPEC-3",
      title: "3. 功能需求",
      target_section: "3. 功能需求",
      status: "open",
      answer_summary: "",
      completion_reason: "",
      children: [],
    },
  ];
}

function buildSpecTreeAfterFirstTurn() {
  const tree = buildSpecTree();
  tree[0].children[0] = {
    ...tree[0].children[0],
    status: "closed",
    answer_summary: "系统初步定位为空域计算分析工具",
    completion_reason: "turn-0001 用户已确认",
  };
  return tree;
}
