import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";
import type { RequirementAnalysisSession, RequirementAnalysisTurnEnvelope } from "../lib/api";

const getMock = vi.fn();
const postMock = vi.fn();
const putMock = vi.fn();
const deleteMock = vi.fn();
const scrollIntoViewMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    put: (...args: unknown[]) => putMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  putMock.mockReset();
  deleteMock.mockReset();
  scrollIntoViewMock.mockReset();
  HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;
});

test("keeps XG requirement analysis lab view tabs explicit while business state changes", async () => {
  let session = buildSession("created");
  const deferredTurn = createDeferred<{ data: RequirementAnalysisTurnEnvelope }>();

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/lab-config") {
      return Promise.resolve({ data: buildLabConfig() });
    }
    if (url === "/requirement-analysis/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/requirement-analysis/providers") {
      return Promise.resolve({
        data: {
          items: [
            { provider_id: "mock", name: "Mock Provider", status: "active" },
            { provider_id: "deepseek", name: "DeepSeek", status: "active" },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "xg-template-81433-default",
              template_code: "81433",
              base_template_id: "81433号",
              base_template_name: "软件级需求规格说明模板",
              name: "软件级需求规格说明模板",
              description: "基于 81433 的默认实例模板。",
              status: "active",
            },
            {
              template_id: "xg-template-82259-default",
              template_code: "82259",
              base_template_id: "82259号",
              base_template_name: "平台级需求规格说明模板",
              name: "平台级需求规格说明模板",
              description: "基于 82259 的默认实例模板。",
              status: "available",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/template-bases") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "81433号",
              template_code: "81433",
              name: "软件级需求规格说明模板",
              description: "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
              status: "active",
            },
            {
              template_id: "82259号",
              template_code: "82259",
              name: "平台级需求规格说明模板",
              description: "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
              status: "available",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-81433-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-default",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: "软件级需求规格说明模板",
          description: "基于 81433 的默认实例模板。",
          status: "active",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n\n## 1. 文档定位\n",
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-82259-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-82259-default",
          template_code: "82259",
          base_template_id: "82259号",
          base_template_name: "平台级需求规格说明模板",
          name: "平台级需求规格说明模板",
          description: "基于 82259 的默认实例模板。",
          status: "available",
          format: "markdown",
          content: "# 82259 平台级规格模板\n\n## 1. 文档定位\n",
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-81433-attitude-analysis") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-attitude-analysis",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: "态势分析系统需求规格模板",
          description: "基于 81433 扩充的 Lab 模板实例。",
          status: "available",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n\n## 1. 文档定位\n",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-analysis/sessions") {
      expect(body).toMatchObject({
        topic: "配置下发的需求规格探索课题",
        orchestrator_id: "xg-heuristic-orchestrator",
        provider_id: "deepseek",
        model: "deepseek-config-model",
        template_id: "xg-template-82259-default",
        knowledge_package_id: "configured-knowledge-package",
        write_policy: "configured_patch_only",
      });
      return Promise.resolve({ data: session });
    }
    if (url === "/requirement-analysis/templates") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-attitude-analysis",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: (body as { name: string }).name,
          description: "基于 81433 扩充的 Lab 模板实例。",
          status: "available",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n\n## 1. 文档定位\n",
        },
      });
    }
    if (url === "/requirement-analysis/sessions/ra-airspace-001/turns") {
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

  putMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-analysis/templates/xg-template-82259-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-82259-default",
          template_code: "82259",
          base_template_id: "82259号",
          base_template_name: "平台级需求规格说明模板",
          name: "平台级需求规格说明模板",
          description: "基于 82259 的默认实例模板。",
          status: "available",
          format: "markdown",
          content: (body as { content: string }).content,
        },
      });
    }
    throw new Error(`unexpected put url: ${url}`);
  });

  deleteMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/templates/xg-template-81433-attitude-analysis") {
      return Promise.resolve({ data: { deleted: true, template_id: "xg-template-81433-attitude-analysis" } });
    }
    throw new Error(`unexpected delete url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-requirement-analysis-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 XG 需求分析组织器 Lab" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();

  expect(screen.getByRole("tab", { name: /组织器配置/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.getByRole("tab", { name: /当前 Turn/ })).toHaveAttribute("aria-selected", "false");
  expect(screen.getByRole("tab", { name: /调用日志/ })).toHaveAttribute("aria-selected", "false");

  expect(screen.getByText("RequirementAnalysisOrchestrator 插槽")).toBeInTheDocument();
  expect(screen.getByText("可替换组织器")).toBeInTheDocument();
  expect(screen.getByText("启动参数")).toBeInTheDocument();
  expect(screen.getByText("需求规格说明模板")).toBeInTheDocument();
  expect(screen.queryByText("模板实例")).not.toBeInTheDocument();
  expect(screen.queryByText("实例是会话实际使用和编辑的对象。")).not.toBeInTheDocument();
  const startupTemplateSelect = screen.getByRole("combobox", { name: "启动模板实例" });
  expect(startupTemplateSelect).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /选择基础模板/ })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建实例" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "删除实例" })).toBeInTheDocument();
  expect(screen.getByText("XG Heuristic Orchestrator")).toBeInTheDocument();
  expect(screen.getByText("XG Strong Rule Orchestrator")).toBeInTheDocument();
  expect(screen.getByText("DeepSeek")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /选择模板实例 软件级需求规格说明模板/ })).toBeInTheDocument();
  await waitFor(() =>
    expect((screen.getByLabelText("需求规格说明模板正文") as HTMLTextAreaElement).value).toContain("# 81433 软件级需求规格模板"),
  );
  expect(screen.getByText(/当前 Provider：/)).toBeInTheDocument();
  expect(screen.queryByText("CLI 式问答区")).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByDisplayValue("配置下发的需求规格探索课题")).toBeInTheDocument());

  fireEvent.click(screen.getByRole("button", { name: /选择模板实例 平台级需求规格说明模板/ }));
  await waitFor(() =>
    expect((screen.getByLabelText("需求规格说明模板正文") as HTMLTextAreaElement).value).toContain("# 82259 平台级规格模板"),
  );
  fireEvent.mouseDown(startupTemplateSelect);
  fireEvent.click(await screen.findByTitle("平台级需求规格说明模板 (xg-template-82259-default)"));
  fireEvent.change(screen.getByLabelText("需求规格说明模板正文"), {
    target: { value: "# 82259 平台级规格模板\n\n## 1. 范围与边界\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存模板" }));
  await waitFor(() =>
    expect(putMock).toHaveBeenCalledWith("/requirement-analysis/templates/xg-template-82259-default", {
      content: "# 82259 平台级规格模板\n\n## 1. 范围与边界\n",
      name: "平台级需求规格说明模板",
      description: "基于 82259 的默认实例模板。",
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "新建实例" }));
  expect(screen.getByText("新建需求规格说明模板实例")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /选择基础模板 软件级需求规格说明模板/ })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("新建模板实例名称"), {
    target: { value: "态势分析系统需求规格模板" },
  });
  fireEvent.change(screen.getByLabelText("新建模板实例说明"), {
    target: { value: "基于 81433 扩充的 Lab 模板实例。" },
  });
  fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));
  fireEvent.click(screen.getByRole("button", { name: "新建实例" }));
  expect(screen.getByLabelText("新建模板实例名称")).toHaveValue("配置下发的需求规格探索课题模板实例");
  expect(screen.getByLabelText("新建模板实例说明")).toHaveValue("基于 82259 扩充的 Lab 模板实例。");
  fireEvent.change(screen.getByLabelText("新建模板实例名称"), {
    target: { value: "态势分析系统需求规格模板" },
  });
  fireEvent.change(screen.getByLabelText("新建模板实例说明"), {
    target: { value: "基于 81433 扩充的 Lab 模板实例。" },
  });
  fireEvent.click(screen.getByRole("button", { name: /选择基础模板 软件级需求规格说明模板/ }));
  fireEvent.click(screen.getByRole("button", { name: "创建实例" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-analysis/templates", {
      base_template_id: "81433号",
      name: "态势分析系统需求规格模板",
      description: "基于 81433 扩充的 Lab 模板实例。",
    }),
  );
  expect(await screen.findByText("xg-template-81433-attitude-analysis")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "删除实例" }));
  await waitFor(() =>
    expect(deleteMock).toHaveBeenCalledWith("/requirement-analysis/templates/xg-template-81433-attitude-analysis"),
  );

  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions", expect.any(Object)));

  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByRole("heading", { name: "会话管理" })).not.toBeInTheDocument();
  expect(await screen.findByText("会话 ra-airspace-001")).toBeInTheDocument();
  expect(screen.getByText("CLI 式问答区")).toBeInTheDocument();
  expect(screen.getAllByText("Provider deepseek").length).toBeGreaterThan(0);
  expect(screen.getAllByText("空域运算软件需求规格探索").length).toBeGreaterThan(0);
  expect(screen.getByText("只生成 document_patch 建议")).toBeInTheDocument();
  const assistantIntroMessage = screen.getByText("我会先验证这个课题的需求边界。当前知识包只作为背景，不会自动写入正式规格。");
  const assistantIntroBubble = assistantIntroMessage.closest(".requirement-analysis-lab-message") as HTMLElement;
  expect(assistantIntroBubble).toHaveClass("is-assistant");
  expect(within(assistantIntroBubble).getByText("助手")).toBeInTheDocument();

  const input = screen.getByPlaceholderText("输入 A / 继续 / 更正式 / 或直接描述需求...");
  expect(input.tagName).toBe("TEXTAREA");
  fireEvent.change(input, { target: { value: "第一行需求\n第二行补充" } });
  fireEvent.keyDown(input, { key: "Enter", code: "Enter", shiftKey: true });
  expect(input).toHaveValue("第一行需求\n第二行补充");

  fireEvent.change(input, { target: { value: "A，先按计算分析工具理解" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions/ra-airspace-001/turns", {
      user_input: "A，先按计算分析工具理解",
    }),
  );

  expect(screen.getByText("A，先按计算分析工具理解")).toBeInTheDocument();
  const pendingUserBubble = screen.getByText("A，先按计算分析工具理解").closest(".requirement-analysis-lab-message") as HTMLElement;
  expect(pendingUserBubble).toHaveClass("is-user");
  expect(within(pendingUserBubble).getByText("用户")).toBeInTheDocument();
  const pendingAssistantBubble = screen.getByText("正在生成回应...").closest(".requirement-analysis-lab-message") as HTMLElement;
  expect(pendingAssistantBubble).toHaveClass("is-assistant");
  expect(within(pendingAssistantBubble).getByText("助手")).toBeInTheDocument();
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
  expect(screen.getByText("结构化状态")).toBeInTheDocument();
  expect(screen.getByText("需求分析结构化状态")).toBeInTheDocument();
  const decisionStatePage = screen.getByTestId("requirement-analysis-decision-state-page");
  expect(decisionStatePage).toHaveTextContent("系统初步定位为空域计算分析工具");
  expect(screen.getByText("探索与收束阶段")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "临时正文" }));
  expect(screen.getByText("临时正文")).toBeInTheDocument();
  expect(screen.getByText("81433号需求规格说明（Lab 临时正文）")).toBeInTheDocument();
  const workingDocumentPage = screen.getByTestId("requirement-analysis-working-document-page");
  expect(workingDocumentPage).toBeInTheDocument();
  expect(workingDocumentPage).toHaveTextContent("本系统面向空域领域专家，支持围绕空域运算任务进行输入组织、计算分析与结果确认。");
  expect(within(workingDocumentPage).queryByText("turn-0001")).not.toBeInTheDocument();
  expect(within(workingDocumentPage).queryByText("frag-0001")).not.toBeInTheDocument();
  expect(screen.getByText("用户选择先按计算分析工具理解")).toBeInTheDocument();
  const revisionMarker = screen.getByTestId("requirement-analysis-marker-frag-0001");
  const revisionHighlight = screen.getByTestId("requirement-analysis-highlight-frag-0001");
  expect(revisionMarker).toHaveTextContent("第1轮修订");
  expect(revisionMarker).not.toHaveTextContent("turn-0001");
  expect(revisionMarker).not.toHaveTextContent("frag-0001");
  expect(revisionMarker).not.toHaveClass("is-active");
  expect(revisionHighlight).not.toHaveClass("is-active");
  fireEvent.click(revisionMarker);
  expect(revisionMarker).toHaveClass("is-active");
  expect(revisionHighlight).toHaveClass("is-active");
  expect(document.querySelectorAll('[data-marker-group="requirement-analysis-revision-marker"]')).toHaveLength(1);
  expect(screen.queryByText("系统要做什么？")).not.toBeInTheDocument();
  expect(screen.queryByText("问题工作项")).not.toBeInTheDocument();
  expect(screen.queryByText("已确认事实")).not.toBeInTheDocument();
  expect(screen.queryByText("文档修补建议")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "需求规格完成度树" }));
  expect(screen.getAllByText("focus: SPEC-1.2").length).toBeGreaterThan(0);
  expect(screen.getAllByText("1. 系统概述").length).toBeGreaterThan(0);
  expect(screen.getByText("系统要做什么？")).toBeInTheDocument();
  expect(screen.getByText("系统边界是什么？")).toBeInTheDocument();
  expect(screen.queryByText("回答摘要：系统初步定位为空域计算分析工具")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "沟通路径" }));
  expect(screen.getAllByText("turn-0001").length).toBeGreaterThan(0);
  expect(screen.getAllByText("SPEC-1.1").length).toBeGreaterThan(0);
  expect(screen.getByText("推荐")).toBeInTheDocument();
  expect(screen.getByText("先确认输入")).toBeInTheDocument();
  expect(screen.getByText("先确认输出")).toBeInTheDocument();
  const quickOptions = screen.getByLabelText("快捷回复选项");
  const optionRows = within(quickOptions).getAllByTestId("requirement-analysis-quick-option");
  expect(optionRows).toHaveLength(3);
  fireEvent.click(optionRows[1]);
  expect(postMock).not.toHaveBeenCalledWith("/requirement-analysis/sessions/ra-airspace-001/turns", {
    user_input: "B，先确认输出",
  });

  fireEvent.click(within(optionRows[1]).getByRole("button", { name: "选择 B" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions/ra-airspace-001/turns", {
      user_input: "B，先确认输出",
    }),
  );

  fireEvent.click(screen.getByRole("tab", { name: /当前 Turn/ }));

  expect(screen.getByTestId("requirement-analysis-turn-grid")).toHaveClass("is-turn-single");
  expect(screen.getByText("当前 Turn 决策审计")).toBeInTheDocument();
  expect(screen.getByText("上轮系统留题")).toBeInTheDocument();
  expect(screen.getByText("本轮用户输入")).toBeInTheDocument();
  expect(screen.getByText("输入承接判断")).toBeInTheDocument();
  expect(screen.getByText("规格补充执行")).toBeInTheDocument();
  expect(screen.getByText("临时正文应用结果")).toBeInTheDocument();
  expect(screen.getByText("目标范围回看")).toBeInTheDocument();
  expect(screen.getByText("全局回看")).toBeInTheDocument();
  expect(screen.getByText("本轮处理闭环")).toBeInTheDocument();
  expect(screen.getByText("下一轮交互设计")).toBeInTheDocument();
  expect(screen.getByText("决策依据")).toBeInTheDocument();
  expect(screen.getByText("阶段执行审计")).toBeInTheDocument();
  expect(screen.getByText("阶段 decision_state_delta 已生成结构化状态增量与正文投影候选。")).toBeInTheDocument();
  expect(screen.getByText("阶段 next_interaction_planning 已基于结构化状态生成下一步交互规划。")).toBeInTheDocument();
  expect(screen.queryByText("上一轮用户关注点（审计上下文）")).not.toBeInTheDocument();
  expect(screen.queryByText("系统理解与回应")).not.toBeInTheDocument();
  expect(screen.queryByText("影响的规格节点")).not.toBeInTheDocument();
  expect(screen.queryByText("本轮状态变化")).not.toBeInTheDocument();
  expect(screen.queryByText("下一轮建议话题")).not.toBeInTheDocument();
  expect(screen.getAllByText("SPEC-1.1").length).toBeGreaterThan(0);
  expect(screen.getAllByText("quick_option_answer").length).toBeGreaterThan(0);
  expect(screen.getByText("系统初步定位为空域计算分析工具")).toBeInTheDocument();
  expect(screen.getAllByText("1.1 系统目标").length).toBeGreaterThan(0);
  expect(screen.getByText("应用正文块：blk-0001")).toBeInTheDocument();
  expect(screen.getByText("当前章节已具备可接受表达。")).toBeInTheDocument();
  expect(screen.getByText("下一处缺口位于 2.1 输入数据。")).toBeInTheDocument();
  expect(screen.getByText("本轮输入已被吸收，并形成系统目标章节的正文建议；无需继续追问同一题。")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /调用日志/ }));

  expect(screen.getByRole("tab", { name: /调用日志.*3 条/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("模型 / Runner 调用日志")).toBeInTheDocument();
  expect(screen.getAllByText("call-0001").length).toBeGreaterThan(0);
  expect(screen.getAllByText("call-0002").length).toBeGreaterThan(0);
  expect(screen.getAllByText("call-0003").length).toBeGreaterThan(0);
  expect(screen.getByText(/turn-0001 · decision_state_delta \/ decision_state_delta \/ policy_interpreted/)).toBeInTheDocument();
  expect(screen.getByText(/deepseek-chat/)).toBeInTheDocument();
  expect(screen.getAllByText("turn-0001").length).toBeGreaterThan(0);
  expect(screen.getByRole("tab", { name: "概览" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("user_input")).toBeInTheDocument();
  expect(screen.getByText("（配置接口下发：用户输入字段说明。）")).toBeInTheDocument();
  expect(screen.getByText("normalized_input")).toBeInTheDocument();
  expect(screen.getByText("（组织器对用户输入的归一化理解，用于判断输入类型、选项匹配和语义摘要。）")).toBeInTheDocument();
  expect(screen.getByText("A，先按计算分析工具理解")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "当前 turn 上下文" }));
  expect(screen.getByRole("tab", { name: "当前 turn 上下文" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("provider_request.prompt_bundle.context_json")).toBeInTheDocument();
  expect(screen.getByText("（写入提示词的结构化上下文快照，用于确认本轮带入了哪些会话状态。）")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "输出格式要求" }));
  expect(screen.getByRole("tab", { name: "输出格式要求" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("provider_request.prompt_bundle.schema_json")).toBeInTheDocument();
  expect(screen.getByText("（要求模型返回的 JSON 输出格式约束，用于校验输出字段是否齐全。）")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "请求" }));
  expect(screen.getByRole("tab", { name: "请求" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("provider_request.messages")).toBeInTheDocument();
  expect(screen.getByText("（配置接口下发：模型 messages 字段说明。）")).toBeInTheDocument();
  expect(screen.getByText("provider_request.prompt_bundle.assembled_prompt")).toBeInTheDocument();
  expect(screen.getByText("（组织器拼装后的完整提示词，用于检查模型实际收到的任务说明。）")).toBeInTheDocument();
  expect(screen.getAllByText("provider_request.prompt_bundle.stage_id").length).toBeGreaterThan(0);
  expect(screen.getAllByText("provider_request.prompt_bundle.prompt_id").length).toBeGreaterThan(0);
  expect(screen.getAllByText("（Mock Provider 的调试上下文，仅在本地模拟调用时使用。）").length).toBeGreaterThan(0);
  expect(screen.getAllByText("（运行器传入 Provider 的会话与组织器上下文，用于复盘调用边界。）").length).toBeGreaterThan(0);
  expect(screen.getByText("intent prompt")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /call-0002/ }));
  expect(screen.getByText(/Stage: decision_state_delta \/ decision_state_delta \/ policy_interpreted/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "请求" }));
  expect(screen.getAllByText("provider_request.prompt_bundle.decision_state_json").length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("tab", { name: "原始输出" }));
  expect(screen.getByText("provider_response.raw_content")).toBeInTheDocument();
  expect(screen.getByText("（Provider 返回的原始文本，解析失败时优先看这一块。）")).toBeInTheDocument();
  expect(screen.getByText("provider_response.parsed_json")).toBeInTheDocument();
  expect(screen.getByText("（从原始文本解析出的 JSON 对象，用于判断模型是否按输出格式要求返回。）")).toBeInTheDocument();
  expect(screen.getAllByText(/"decision_state_delta"/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/系统初步定位为空域计算分析工具/).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("tab", { name: "输出后处理" }));
  expect(screen.getByText("provider_normalized_output")).toBeInTheDocument();
  expect(screen.getByText("（Provider 输出经过规范化后的中间结果，用于屏蔽不同模型返回格式差异。）")).toBeInTheDocument();
  expect(screen.getByText("service_output")).toBeInTheDocument();
  expect(screen.getByText("（Turn 服务最终采纳的输出，用于生成聊天回应、规格补丁和状态更新。）")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /组织器配置/ }));
  expect(screen.getByText("需求规格说明模板")).toBeInTheDocument();
});

test("switches to session tab immediately while startup request is still pending", async () => {
  const deferredSession = createDeferred<{ data: RequirementAnalysisSession }>();
  mockRequirementAnalysisBootstrap();

  postMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/sessions") {
      return deferredSession.promise;
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-requirement-analysis-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 XG 需求分析组织器 Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions", expect.any(Object)));

  expect(screen.getByRole("tab", { name: /会话管理/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("尚未创建 Requirement Analysis 会话。请先回到“组织器配置”点击“启动验证”。")).toBeInTheDocument();

  deferredSession.resolve({ data: buildSession("created") });
  expect(await screen.findByText("会话 ra-airspace-001")).toBeInTheDocument();
});

test("shows a protocol error instead of blanking when Current Turn misses required audit fields", async () => {
  const session = buildSession("created");
  const malformedEnvelope = buildMalformedTurnEnvelope();

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/lab-config") {
      return Promise.resolve({ data: buildLabConfig() });
    }
    if (url === "/requirement-analysis/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/requirement-analysis/providers") {
      return Promise.resolve({
        data: {
          items: [{ provider_id: "mock", name: "Mock Provider", status: "active" }],
        },
      });
    }
    if (url === "/requirement-analysis/templates") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "xg-template-81433-default",
              template_code: "81433",
              base_template_id: "81433号",
              base_template_name: "软件级需求规格说明模板",
              name: "软件级需求规格说明模板",
              description: "基于 81433 的默认实例模板。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/template-bases") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "81433号",
              template_code: "81433",
              name: "软件级需求规格说明模板",
              description: "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-81433-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-default",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: "软件级需求规格说明模板",
          description: "基于 81433 的默认实例模板。",
          status: "active",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/sessions") {
      return Promise.resolve({ data: session });
    }
    if (url === "/requirement-analysis/sessions/ra-airspace-001/turns") {
      return Promise.resolve({ data: malformedEnvelope });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-requirement-analysis-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 XG 需求分析组织器 Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions", expect.any(Object)));

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

test("renders Current Turn without blanking when review arrays are omitted", async () => {
  const session = buildSession("created");
  const envelope = buildTurnEnvelopeWithSparseReviewArrays();

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/lab-config") {
      return Promise.resolve({ data: buildLabConfig() });
    }
    if (url === "/requirement-analysis/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/requirement-analysis/providers") {
      return Promise.resolve({
        data: {
          items: [{ provider_id: "mock", name: "Mock Provider", status: "active" }],
        },
      });
    }
    if (url === "/requirement-analysis/templates") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "xg-template-81433-default",
              template_code: "81433",
              base_template_id: "81433号",
              base_template_name: "软件级需求规格说明模板",
              name: "软件级需求规格说明模板",
              description: "基于 81433 的默认实例模板。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/template-bases") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "81433号",
              template_code: "81433",
              name: "软件级需求规格说明模板",
              description: "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-81433-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-default",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: "软件级需求规格说明模板",
          description: "基于 81433 的默认实例模板。",
          status: "active",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/sessions") {
      return Promise.resolve({ data: session });
    }
    if (url === "/requirement-analysis/sessions/ra-airspace-001/turns") {
      return Promise.resolve({ data: envelope });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-requirement-analysis-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 XG 需求分析组织器 Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/requirement-analysis/sessions", expect.any(Object)));

  fireEvent.click(screen.getByRole("tab", { name: /会话管理/ }));
  fireEvent.change(screen.getByPlaceholderText("输入 A / 继续 / 更正式 / 或直接描述需求..."), {
    target: { value: "A，先按计算分析工具理解" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));
  await screen.findByText("基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。");

  fireEvent.click(screen.getByRole("tab", { name: /当前 Turn/ }));

  expect(screen.getByText("目标范围回看")).toBeInTheDocument();
  expect(screen.getByText("模型确认目标范围已覆盖。")).toBeInTheDocument();
  expect(screen.queryByText("当前 Turn 协议错误")).not.toBeInTheDocument();
});

test("lets provider log audit outputs expand until near one screen before internal scrolling", () => {
  const css = readFileSync(resolve(process.cwd(), "src/pages/RequirementAnalysisLabPage.css"), "utf8");

  expect(css).toContain("max-height: min(72vh, 920px);");
  expect(css).not.toContain("max-height: 320px;");
});

test("uses a 4:6 session workspace ratio so the working document is wider than the CLI column", () => {
  const css = readFileSync(resolve(process.cwd(), "src/pages/RequirementAnalysisLabPage.css"), "utf8");

  expect(css).toContain(".requirement-analysis-lab-tab-grid.is-session");
  expect(css).toContain("grid-template-columns: minmax(360px, 0.8fr) minmax(560px, 1.2fr);");
  expect(css).not.toContain("grid-template-columns: minmax(420px, 0.95fr) minmax(460px, 1.05fr);");
});

test("styles user chat messages as a clearer pale-green bubble distinct from assistant messages", () => {
  const css = readFileSync(resolve(process.cwd(), "src/pages/RequirementAnalysisLabPage.css"), "utf8");

  expect(css).toMatch(/\.requirement-analysis-lab-message-meta\s*\{[^}]*grid-column: 1;[^}]*grid-row: 1;/s);
  expect(css).toMatch(/\.requirement-analysis-lab-message-meta\s*\{[^}]*width: 44px;[^}]*justify-items: center;[^}]*text-align: center;/s);
  expect(css).toMatch(/\.requirement-analysis-lab-message-meta\s*\{[^}]*justify-self: start;/s);
  expect(css).toMatch(/\.requirement-analysis-lab-message p\s*\{[^}]*grid-column: 2;[^}]*grid-row: 1;/s);
  expect(css).toContain(".requirement-analysis-lab-message-avatar");
  expect(css).toContain("width: 44px;");
  expect(css).toMatch(/\.requirement-analysis-lab-message span\s*\{[^}]*line-height: 1;/s);
  expect(css).toContain(".requirement-analysis-lab-message.is-user");
  expect(css).toContain("align-self: flex-end;");
  expect(css).toContain("grid-template-columns: minmax(0, 1fr) 72px;");
  expect(css).toContain(".requirement-analysis-lab-message.is-user .requirement-analysis-lab-message-meta");
  expect(css).toMatch(/\.requirement-analysis-lab-message\.is-user \.requirement-analysis-lab-message-meta\s*\{[^}]*grid-column: 2;[^}]*grid-row: 1;[^}]*justify-self: end;/s);
  expect(css).toMatch(/\.requirement-analysis-lab-message.is-user p\s*\{[^}]*grid-column: 1;[^}]*grid-row: 1;/s);
  expect(css).toContain("background: #dff3d8;");
  expect(css).toContain("border-color: #b3d7ad;");
  expect(css).toContain(".requirement-analysis-lab-message.is-assistant");
  expect(css).toContain("align-items: start;");
  expect(css).toContain("background: #f4f8f7;");
});

test("places revision markers in a right-side rail outside the paper instead of reserving an in-page left column", () => {
  const css = readFileSync(resolve(process.cwd(), "src/pages/RequirementAnalysisLabPage.css"), "utf8");

  expect(css).toContain(".requirement-analysis-lab-working-document-sheet");
  expect(css).toContain("grid-template-columns: minmax(0, 920px) 220px;");
  expect(css).toContain(".requirement-analysis-lab-working-document-revision-rail");
  expect(css).not.toContain("grid-template-columns: 184px minmax(0, 1fr);");
});

test("renders one right-side revision marker per turn even when the turn edits multiple document positions", async () => {
  mockRequirementAnalysisBootstrap();
  const session = buildSessionWithCrossPositionRevision();

  postMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/sessions") {
      return Promise.resolve({ data: session });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/p2-requirement-analysis-lab"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 XG 需求分析组织器 Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启动验证" }));
  await screen.findByText("会话 ra-airspace-001");
  fireEvent.click(screen.getByRole("tab", { name: "临时正文" }));

  await screen.findByTestId("requirement-analysis-marker-frag-0001");
  const markers = Array.from(document.querySelectorAll('[data-marker-group="requirement-analysis-revision-marker"]'));
  expect(markers).toHaveLength(1);
  expect(markers[0]).toHaveTextContent("第1轮修订");
  expect(markers[0]).toHaveTextContent("影响 2 处");

  const firstHighlight = screen.getByTestId("requirement-analysis-highlight-frag-0001");
  const secondHighlight = screen.getByTestId("requirement-analysis-highlight-frag-0002");
  expect(firstHighlight).not.toHaveClass("is-active");
  expect(secondHighlight).not.toHaveClass("is-active");

  fireEvent.click(markers[0]);

  expect(firstHighlight).toHaveClass("is-active");
  expect(secondHighlight).toHaveClass("is-active");
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
        orchestrator_id: "xg-heuristic-orchestrator",
        name: "XG Heuristic Orchestrator",
        version: "0.1.0",
        stage: "P2",
        document_type: "xg",
        contract: "xg-orchestrator-contract@1",
        mode: "policy_interpreted",
        status: "active",
        description: "面向需求规格说明的开放式 Requirement Analysis 组织器。",
        entry: null,
        capabilities: ["free_text_input", "guided_question", "quick_options", "spec_tree_update", "document_patch", "turn_audit"],
        requires: { template: true, knowledge_binding: true, model_provider: "optional" },
        package_path: "orchestrators/xg/xg-heuristic-orchestrator",
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

function buildLabConfig() {
  return {
    page: {
      title: "P2 XG 需求分析组织器 Lab",
      subtitle: "配置接口下发的 Lab 副标题。",
    },
    defaults: {
      topic: "配置下发的需求规格探索课题",
      orchestrator_id: "xg-heuristic-orchestrator",
      provider_id: "deepseek",
      model: "deepseek-config-model",
      template_id: "xg-template-81433-default",
      knowledge_package_id: "configured-knowledge-package",
      write_policy: "configured_patch_only",
    },
    startup_fields: [
      {
        field: "topic",
        label: "课题输入",
        control: "textarea",
        required: true,
        placeholder: "输入本次需求规格探索课题",
      },
    ],
    write_policies: [
      {
        policy_id: "configured_patch_only",
        label: "配置下发写入策略",
        description: "由配置接口下发的写入策略说明。",
      },
    ],
    provider_log_schema: {
      fields: [
        {
          path: "user_input",
          label: "User Input",
          description: "配置接口下发：用户输入字段说明。",
          used_when: "每轮用户输入后使用。",
        },
        {
          path: "normalized_input",
          label: "Normalized Input",
          description: "组织器对用户输入的归一化理解，用于判断输入类型、选项匹配和语义摘要。",
          used_when: "每轮输入归一化后使用。",
        },
        {
          path: "provider_request.messages",
          label: "Provider Request Messages",
          description: "配置接口下发：模型 messages 字段说明。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.assembled_prompt",
          label: "Assembled Prompt",
          description: "组织器拼装后的完整提示词，用于检查模型实际收到的任务说明。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.stage_id",
          label: "Stage ID",
          description: "当前模型调用所属的轮次阶段标识，用于区分意图理解、结构化状态增量和下一步交互规划。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.prompt_id",
          label: "Prompt ID",
          description: "当前阶段使用的 Prompt 资产标识，用于核对是否命中了正确的阶段提示词。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.context_json",
          label: "Context JSON",
          description: "写入提示词的结构化上下文快照，用于确认本轮带入了哪些会话状态。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.working_document_json",
          label: "Working Document JSON",
          description: "本轮调用前带入模型的临时正文快照，用于判断模型是否看到了既有正文。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.decision_state_json",
          label: "Decision State JSON",
          description: "当前会话的需求分析结构化状态快照，用于确认规划阶段读取的是已应用后的决策状态。",
          used_when: "结构化状态增量和下一步交互规划阶段调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.decision_state_document_json",
          label: "Decision State Document JSON",
          description: "结构化状态的 A4 承载页投影，用于检查用户可见状态页与模型上下文是否一致。",
          used_when: "结构化状态展示和下一步交互规划阶段使用。",
        },
        {
          path: "provider_request.prompt_bundle.working_document_excerpt",
          label: "Working Document Excerpt",
          description: "与本轮目标最相关的正文摘录，用于检查模型面对的是哪一段正文。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.review_target_paths",
          label: "Review Target Paths",
          description: "本轮重点审查的规格锚点路径，用于解释当前回看到底在看哪里。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.recent_revision_fragments",
          label: "Recent Revision Fragments",
          description: "最近几轮命中的修订片段摘要，用于判断模型是否看到了最近修改痕迹。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.review_goal",
          label: "Review Goal",
          description: "本轮回看目标，说明当前章节还要确认什么。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.prompt_bundle.schema_json",
          label: "输出格式要求 JSON",
          description: "要求模型返回的 JSON 输出格式约束，用于校验输出字段是否齐全。",
          used_when: "每次调用模型前使用。",
        },
        {
          path: "provider_request.mock_context",
          label: "Mock Context",
          description: "Mock Provider 的调试上下文，仅在本地模拟调用时使用。",
          used_when: "Mock Provider 调用时使用。",
        },
        {
          path: "provider_request.runner_context",
          label: "Runner Context",
          description: "运行器传入 Provider 的会话与组织器上下文，用于复盘调用边界。",
          used_when: "组织器 Runner 调用时使用。",
        },
        {
          path: "provider_response.raw_content",
          label: "Raw Content",
          description: "Provider 返回的原始文本，解析失败时优先看这一块。",
          used_when: "模型返回后使用。",
        },
        {
          path: "provider_response.parsed_json",
          label: "Parsed JSON",
          description: "从原始文本解析出的 JSON 对象，用于判断模型是否按输出格式要求返回。",
          used_when: "模型返回后使用。",
        },
        {
          path: "provider_response.target_review_json",
          label: "Target Review JSON",
          description: "服务端或模型给出的目标范围回看结果，用于判断本轮命中范围是否已足够。",
          used_when: "临时正文回看后使用。",
        },
        {
          path: "provider_response.global_review_json",
          label: "Global Review JSON",
          description: "服务端或模型给出的全局回看结果，用于判断为何继续追问或进入下一节点。",
          used_when: "临时正文回看后使用。",
        },
        {
          path: "provider_normalized_output",
          label: "Provider Normalized Output",
          description: "Provider 输出经过规范化后的中间结果，用于屏蔽不同模型返回格式差异。",
          used_when: "Provider 适配后使用。",
        },
        {
          path: "service_output",
          label: "Service Output",
          description: "Turn 服务最终采纳的输出，用于生成聊天回应、规格补丁和状态更新。",
          used_when: "Turn 后处理后使用。",
        },
      ],
    },
    turn_audit_schema: {
      protocol_version: "xg-turn-audit-v1",
      required_fields: [
        "previous_interaction",
        "input_relation",
        "spec_execution",
        "post_update_review",
        "closure_decision",
        "next_interaction",
        "decision_trace",
      ],
    },
  };
}

function mockRequirementAnalysisBootstrap() {
  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-analysis/lab-config") {
      return Promise.resolve({ data: buildLabConfig() });
    }
    if (url === "/requirement-analysis/orchestrators") {
      return Promise.resolve({ data: buildOrchestrators() });
    }
    if (url === "/requirement-analysis/providers") {
      return Promise.resolve({
        data: {
          items: [
            { provider_id: "mock", name: "Mock Provider", status: "active" },
            { provider_id: "deepseek", name: "DeepSeek", status: "active" },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "xg-template-81433-default",
              template_code: "81433",
              base_template_id: "81433号",
              base_template_name: "软件级需求规格说明模板",
              name: "软件级需求规格说明模板",
              description: "基于 81433 的默认实例模板。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/template-bases") {
      return Promise.resolve({
        data: {
          items: [
            {
              template_id: "81433号",
              template_code: "81433",
              name: "软件级需求规格说明模板",
              description: "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
              status: "active",
            },
          ],
        },
      });
    }
    if (url === "/requirement-analysis/templates/xg-template-81433-default") {
      return Promise.resolve({
        data: {
          template_id: "xg-template-81433-default",
          template_code: "81433",
          base_template_id: "81433号",
          base_template_name: "软件级需求规格说明模板",
          name: "软件级需求规格说明模板",
          description: "基于 81433 的默认实例模板。",
          status: "active",
          format: "markdown",
          content: "# 81433 软件级需求规格模板\n",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });
}

function buildSession(status: RequirementAnalysisSession["status"]): RequirementAnalysisSession {
  return {
    session_id: "ra-airspace-001",
    topic: "空域运算软件需求规格探索",
    status,
    orchestrator: buildOrchestrators().items[0],
    provider_id: "deepseek",
    model: "deepseek-chat",
    template_id: "xg-template-81433-default",
    knowledge_package_id: "airspace-domain-demo",
    write_policy: "patch_suggestion_only",
    session_phase: "exploration_convergence",
    decision_state: {
      topic: "空域运算软件需求规格探索",
      confirmed_facts: [],
      confirmed_decisions: [],
      tentative_assumptions: [],
      open_questions: [
        {
          item_id: "DS-Q-001",
          content: "需要确认系统更偏向计算分析工具、协同规划平台，还是二者都有。",
          source_turn_id: null,
          target_section: "1.1 系统目标",
          status: "open",
        },
      ],
      rejected_directions: [],
      next_focus: "需要确认系统更偏向计算分析工具、协同规划平台，还是二者都有。",
      chapter_projections: [],
    },
    decision_state_document: {
      document_id: "decision-state-document",
      title: "需求分析结构化状态",
      phase: "exploration_convergence",
      sections: [
        { section_id: "confirmed_facts", heading: "一、已确认事实", items: [] },
        { section_id: "confirmed_decisions", heading: "二、已确认决策", items: [] },
        { section_id: "tentative_assumptions", heading: "三、暂定假设", items: [] },
        {
          section_id: "open_questions",
          heading: "四、未闭合问题",
          items: [
            {
              item_id: "DS-Q-001",
              content: "需要确认系统更偏向计算分析工具、协同规划平台，还是二者都有。",
              source_turn_id: null,
              target_section: "1.1 系统目标",
              status: "open",
            },
          ],
        },
        { section_id: "rejected_directions", heading: "五、被否定方向", items: [] },
        {
          section_id: "next_focus",
          heading: "六、下一步交互焦点",
          items: [
            {
              item_id: "DS-FOCUS",
              content: "需要确认系统更偏向计算分析工具、协同规划平台，还是二者都有。",
              source_turn_id: null,
              target_section: "",
              status: "active",
            },
          ],
        },
        { section_id: "chapter_projections", heading: "七、章节投影", items: [] },
      ],
    },
    draft_snapshot: null,
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
    working_document: {
      document_id: "lab-working-document",
      title: "81433号需求规格说明（Lab 临时正文）",
      topic: "空域运算软件需求规格探索",
      blocks: [],
      revision_fragments: [],
    },
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
  } as unknown as RequirementAnalysisSession;
}

function buildSessionWithCrossPositionRevision(): RequirementAnalysisSession {
  return {
    ...buildSession("waiting_user"),
    working_document: {
      document_id: "lab-working-document",
      title: "81433号需求规格说明（Lab 临时正文）",
      topic: "空域运算软件需求规格探索",
      blocks: [
        {
          block_id: "blk-0001",
          anchor_path: "1 总则 / 编写目的",
          block_type: "paragraph",
          order_index: 10,
          text: "本规格说明用于定义态势分析系统的需求规格。",
          last_turn_id: "turn-0001",
          source_fragment_ids: ["frag-0001"],
        },
        {
          block_id: "blk-0002",
          anchor_path: "2 项目概述 / 软件定位",
          block_type: "paragraph",
          order_index: 20,
          text: "本软件是一款态势分析系统，提供展示、分析与部门协同能力。",
          last_turn_id: "turn-0001",
          source_fragment_ids: ["frag-0002"],
        },
      ],
      revision_fragments: [
        {
          fragment_id: "frag-0001",
          turn_id: "turn-0001",
          color_token: "turn-color-01",
          target_block_id: "blk-0001",
          apply_mode: "append_to_block",
          start_offset: 0,
          end_offset: 24,
          user_input_summary: "用户描述态势分析系统",
          supplement_reason: "补入编写目的",
          hit_spec_nodes: ["SPEC-REQ-1.1"],
        },
        {
          fragment_id: "frag-0002",
          turn_id: "turn-0001",
          color_token: "turn-color-01",
          target_block_id: "blk-0002",
          apply_mode: "append_to_block",
          start_offset: 0,
          end_offset: 29,
          user_input_summary: "用户描述态势分析系统",
          supplement_reason: "补入软件定位",
          hit_spec_nodes: ["SPEC-REQ-2.1"],
        },
      ],
    },
  };
}

function buildTurnEnvelope(): RequirementAnalysisTurnEnvelope {
  const turn = {
    turn_id: "turn-0001",
    session_id: "ra-airspace-001",
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
    decision_state_delta: {
      confirmed_facts: [
        {
          content: "系统初步定位为空域计算分析工具",
          target_section: "1.1 系统目标",
          status: "active",
        },
      ],
      confirmed_decisions: [],
      tentative_assumptions: [],
      open_questions: [
        {
          content: "输入数据来源、计算结果形式、专家校核职责尚未确认。",
          target_section: "2.1 输入数据",
          status: "open",
        },
      ],
      rejected_directions: [],
      next_focus: "建议下一步确认输入数据来源和输出结果形式。",
      chapter_projections: [
        {
          content: "1.1 系统目标",
          target_section: "1.1 系统目标",
          status: "projected",
        },
      ],
    },
    decision_state_change_summary: {
      turn_id: "turn-0001",
      added_counts: { confirmed_facts: 1, open_questions: 1, chapter_projections: 1 },
      next_focus: "建议下一步确认输入数据来源和输出结果形式。",
    },
    decision_trace: ["用户输入是本轮 Turn 起点。", "本轮影响 1.1 系统目标。"],
    normalized_input: {
      input_type: "quick_option_answer",
      matched_option: "A",
      matched_option_label: "先按计算分析工具理解",
      semantic: "先按计算分析工具理解",
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
      working_document_update: {
        applied_block_ids: ["blk-0001"],
        applied_fragment_ids: ["frag-0001"],
        before_excerpt: "",
        after_excerpt: "本系统面向空域领域专家，支持围绕空域运算任务进行输入组织、计算分析与结果确认。",
      },
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
      summary: "当前章节已具备可接受表达。 下一处缺口位于 2.1 输入数据。",
      target_review: {
        status: "acceptable",
        review_target: ["1.1 系统目标"],
        reason: "当前章节已具备可接受表达。",
        missing_aspects: [],
      },
      global_review: {
        status: "move_next_node",
        summary: "下一处缺口位于 2.1 输入数据。",
        remaining_gaps: ["输入数据来源、计算结果形式、专家校核职责尚未确认。"],
      },
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
    stage_audits: [
      {
        stage_id: "intent_understanding",
        stage_kind: "intent",
        stage_type: "policy_interpreted",
        execution_mode: "model",
        provider_call_log_id: "call-0001",
        validation_status: "accepted",
        blocking_used: false,
        adopted_fields: ["intent_understanding_result", "stage_task_definition"],
        summary: "阶段 intent_understanding 已生成意图理解、目标文档结构和阶段任务定义。",
      },
      {
        stage_id: "decision_state_delta",
        stage_kind: "decision_state_delta",
        stage_type: "policy_interpreted",
        execution_mode: "model",
        provider_call_log_id: "call-0002",
        validation_status: "accepted",
        blocking_used: false,
        adopted_fields: ["decision_state_delta", "document_patch"],
        summary: "阶段 decision_state_delta 已生成结构化状态增量与正文投影候选。",
      },
      {
        stage_id: "next_interaction_planning",
        stage_kind: "next_interaction",
        stage_type: "policy_interpreted",
        execution_mode: "model",
        provider_call_log_id: "call-0003",
        validation_status: "accepted",
        blocking_used: false,
        adopted_fields: ["next_interaction_plan"],
        summary: "阶段 next_interaction_planning 已基于结构化状态生成下一步交互规划。",
      },
    ],
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
      decision_state: {
        topic: "空域运算软件需求规格探索",
        confirmed_facts: [
          {
            item_id: "DS-F-001",
            content: "系统初步定位为空域计算分析工具",
            source_turn_id: "turn-0001",
            target_section: "1.1 系统目标",
            status: "active",
          },
        ],
        confirmed_decisions: [],
        tentative_assumptions: [],
        open_questions: [
          {
            item_id: "DS-Q-002",
            content: "输入数据来源、计算结果形式、专家校核职责尚未确认。",
            source_turn_id: "turn-0001",
            target_section: "2.1 输入数据",
            status: "open",
          },
        ],
        rejected_directions: [],
        next_focus: "建议下一步确认输入数据来源和输出结果形式。",
        chapter_projections: [
          {
            item_id: "DS-P-001",
            content: "1.1 系统目标",
            source_turn_id: "turn-0001",
            target_section: "1.1 系统目标",
            status: "projected",
          },
        ],
      },
      decision_state_document: {
        document_id: "decision-state-document",
        title: "需求分析结构化状态",
        phase: "exploration_convergence",
        sections: [
          {
            section_id: "confirmed_facts",
            heading: "一、已确认事实",
            items: [
              {
                item_id: "DS-F-001",
                content: "系统初步定位为空域计算分析工具",
                source_turn_id: "turn-0001",
                target_section: "1.1 系统目标",
                status: "active",
              },
            ],
          },
          { section_id: "confirmed_decisions", heading: "二、已确认决策", items: [] },
          { section_id: "tentative_assumptions", heading: "三、暂定假设", items: [] },
          {
            section_id: "open_questions",
            heading: "四、未闭合问题",
            items: [
              {
                item_id: "DS-Q-002",
                content: "输入数据来源、计算结果形式、专家校核职责尚未确认。",
                source_turn_id: "turn-0001",
                target_section: "2.1 输入数据",
                status: "open",
              },
            ],
          },
          { section_id: "rejected_directions", heading: "五、被否定方向", items: [] },
          {
            section_id: "next_focus",
            heading: "六、下一步交互焦点",
            items: [
              {
                item_id: "DS-FOCUS",
                content: "建议下一步确认输入数据来源和输出结果形式。",
                source_turn_id: null,
                target_section: "",
                status: "active",
              },
            ],
          },
          {
            section_id: "chapter_projections",
            heading: "七、章节投影",
            items: [
              {
                item_id: "DS-P-001",
                content: "1.1 系统目标",
                source_turn_id: "turn-0001",
                target_section: "1.1 系统目标",
                status: "projected",
              },
            ],
          },
        ],
      },
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
      working_document: {
        document_id: "lab-working-document",
        title: "81433号需求规格说明（Lab 临时正文）",
        topic: "空域运算软件需求规格探索",
        blocks: [
          {
            block_id: "blk-0001",
            anchor_path: "1.1 系统目标",
            block_type: "paragraph",
            order_index: 10,
            text: "本系统面向空域领域专家，支持围绕空域运算任务进行输入组织、计算分析与结果确认。",
            last_turn_id: "turn-0001",
            source_fragment_ids: ["frag-0001"],
          },
        ],
        revision_fragments: [
          {
            fragment_id: "frag-0001",
            turn_id: "turn-0001",
            color_token: "turn-color-01",
            target_block_id: "blk-0001",
            apply_mode: "append_to_block",
            start_offset: 0,
            end_offset: 30,
            user_input_summary: "用户选择先按计算分析工具理解",
            supplement_reason: "补入系统目标正文",
            hit_spec_nodes: ["SPEC-1.1"],
          },
        ],
      },
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
          stage_id: "intent_understanding",
          stage_type: "policy_interpreted",
          provider_id: "deepseek",
          model: "deepseek-chat",
          status: "completed",
          created_at: "2026-05-01T00:00:00Z",
          turn_id: "turn-0001",
          orchestrator_id: "xg-heuristic-orchestrator",
          orchestrator_mode: "policy_interpreted",
          audit: {
            user_input: "A，先按计算分析工具理解",
            normalized_input: {
              input_type: "quick_option_answer",
              matched_option: "A",
              matched_option_label: "先按计算分析工具理解",
              semantic: "先按计算分析工具理解",
            },
            provider_request: {
              messages: [
                { role: "system", content: "system prompt" },
                { role: "user", content: "assembled prompt" },
              ],
              prompt_bundle: {
                stage_id: "intent_understanding",
                prompt_id: "intent_understanding",
                assembled_prompt: "intent prompt",
                context_json: '{"topic":"空域运算软件需求规格探索"}',
                schema_json: '{"intent_understanding_result":"object"}',
              },
            },
            provider_response: {
              raw_content: '{"intent_understanding_result":{"input_type":"quick_option_answer"}}',
              parsed_json: {
                intent_understanding_result: {
                  input_type: "quick_option_answer",
                },
              },
            },
            provider_normalized_output: {
              intent_understanding_result: {
                input_type: "quick_option_answer",
              },
            },
            service_output: {
              intent_understanding_result: {
                input_type: "quick_option_answer",
              },
            },
          },
        },
        {
          call_id: "call-0002",
          stage_id: "decision_state_delta",
          stage_type: "policy_interpreted",
          provider_id: "deepseek",
          model: "deepseek-chat",
          status: "completed",
          created_at: "2026-05-01T00:00:01Z",
          turn_id: "turn-0001",
          orchestrator_id: "xg-heuristic-orchestrator",
          orchestrator_mode: "policy_interpreted",
          audit: {
            user_input: "A，先按计算分析工具理解",
            normalized_input: {
              input_type: "quick_option_answer",
              matched_option: "A",
              matched_option_label: "先按计算分析工具理解",
              semantic: "先按计算分析工具理解",
            },
            provider_request: {
              messages: [
                { role: "system", content: "system prompt" },
                { role: "user", content: "decision state prompt" },
              ],
              prompt_bundle: {
                stage_id: "decision_state_delta",
                prompt_id: "decision_state_delta",
                assembled_prompt: "decision state prompt",
                context_json: '{"topic":"空域运算软件需求规格探索"}',
                decision_state_json: '{"confirmed_facts":[]}',
                working_document_json: '{"document_id":"lab-working-document"}',
                working_document_excerpt: "",
                review_target_paths: ["1.1 系统目标"],
                recent_revision_fragments: ["frag-0001"],
                review_goal: "系统要做什么？",
                schema_json: '{"decision_state_delta":{}}',
              },
            },
            provider_response: {
              raw_content: '{"decision_state_delta":{"confirmed_facts":[{"content":"系统初步定位为空域计算分析工具"}]}}',
              parsed_json: {
                decision_state_delta: {
                  confirmed_facts: [{ content: "系统初步定位为空域计算分析工具" }],
                },
              },
            },
            provider_normalized_output: {
              decision_state_delta: {
                confirmed_facts: [{ content: "系统初步定位为空域计算分析工具" }],
              },
            },
            service_output: {
              assistant_message: "基于你的输入，本轮更新了：1.1 系统目标。建议下一步确认输入数据来源和输出结果形式。",
              working_document_update: {
                applied_block_ids: ["blk-0001"],
                applied_fragment_ids: ["frag-0001"],
              },
            },
          },
        },
        {
          call_id: "call-0003",
          stage_id: "next_interaction_planning",
          stage_type: "policy_interpreted",
          provider_id: "deepseek",
          model: "deepseek-chat",
          status: "completed",
          created_at: "2026-05-01T00:00:02Z",
          turn_id: "turn-0001",
          orchestrator_id: "xg-heuristic-orchestrator",
          orchestrator_mode: "policy_interpreted",
          audit: {
            user_input: "A，先按计算分析工具理解",
            normalized_input: {
              input_type: "quick_option_answer",
              matched_option: "A",
              matched_option_label: "先按计算分析工具理解",
              semantic: "先按计算分析工具理解",
            },
            provider_request: {
              messages: [
                { role: "system", content: "system prompt" },
                { role: "user", content: "planning prompt" },
              ],
              prompt_bundle: {
                stage_id: "next_interaction_planning",
                prompt_id: "next_interaction_planning",
                assembled_prompt: "planning prompt",
                context_json: '{"topic":"空域运算软件需求规格探索"}',
                decision_state_json: '{"confirmed_facts":[{"content":"系统初步定位为空域计算分析工具"}]}',
                schema_json: '{"next_interaction_plan":{}}',
              },
            },
            provider_response: {
              raw_content: '{"next_interaction_plan":{"next_question":"建议下一步确认输入数据来源和输出结果形式。"}}',
              parsed_json: {
                next_interaction_plan: {
                  next_question: "建议下一步确认输入数据来源和输出结果形式。",
                },
              },
            },
            provider_normalized_output: {
              next_interaction_plan: {
                next_question: "建议下一步确认输入数据来源和输出结果形式。",
              },
            },
            service_output: {
              next_interaction_plan: {
                next_question: "建议下一步确认输入数据来源和输出结果形式。",
              },
            },
          },
        },
      ],
    },
    turn,
  } as unknown as RequirementAnalysisTurnEnvelope;
}

function buildMalformedTurnEnvelope(): RequirementAnalysisTurnEnvelope {
  const envelope = buildTurnEnvelope();
  const malformedTurn = { ...envelope.turn } as Partial<RequirementAnalysisTurnEnvelope["turn"]>;
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
      turns: [malformedTurn as RequirementAnalysisTurnEnvelope["turn"]],
    },
    turn: malformedTurn as RequirementAnalysisTurnEnvelope["turn"],
  };
}

function buildTurnEnvelopeWithSparseReviewArrays(): RequirementAnalysisTurnEnvelope {
  const envelope = buildTurnEnvelope();
  const sparseTurn = {
    ...envelope.turn,
    post_update_review: {
      summary: "模型确认目标范围已覆盖。 可以推进下一节点。",
      target_review: {
        status: "acceptable",
        reason: "模型确认目标范围已覆盖。",
      },
      global_review: {
        status: "move_next_node",
        summary: "可以推进下一节点。",
      },
    },
  } as unknown as RequirementAnalysisTurnEnvelope["turn"];
  return {
    session: {
      ...envelope.session,
      turns: [sparseTurn],
    },
    turn: sparseTurn,
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
