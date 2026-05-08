import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";
import type { RequirementAuthoringDocumentDetail, RequirementAuthoringTemplate } from "../lib/api";

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
});

test("renders P2 expert workbench with CLI question mode, form mode, live document, annotation, check and freeze", async () => {
  const template: RequirementAuthoringTemplate = buildTemplate();
  let document: RequirementAuthoringDocumentDetail = buildDocument();

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-authoring/workbench-config") {
      return Promise.resolve({ data: buildWorkbenchConfig() });
    }
    if (url === "/requirement-authoring/templates") {
      return Promise.resolve({ data: [template] });
    }
    if (url === "/requirement-authoring/documents") {
      return Promise.resolve({
        data: [
          {
            document_id: "doc-1",
            title: "空域协同规划软件需求规格说明",
            template_id: "tpl-81433-default",
            status: "draft",
            layout_ratio: "2:3",
            archive_ids: ["20161116-nas"],
            updated_at: "2026-04-30T00:00:00Z",
          },
        ],
      });
    }
    if (url === "/requirement-authoring/documents/doc-1") {
      return Promise.resolve({ data: document });
    }
    if (url === "/requirement-authoring/knowledge-providers") {
      return Promise.resolve({ data: buildKnowledgeProviders() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-authoring/knowledge-bindings") {
      return Promise.resolve({ data: buildKnowledgeBinding() });
    }
    if (url === "/requirement-authoring/documents") {
      return Promise.resolve({ data: document });
    }
    if (url === "/requirement-authoring/documents/doc-1/save") {
      const title = (body as { title?: string }).title ?? document.title;
      const saveBody = body as {
        template_id?: string;
        archive_ids?: string[];
        knowledge_binding?: RequirementAuthoringDocumentDetail["semantic_state"]["knowledge_binding"];
      };
      document = {
        ...document,
        title,
        template_id: saveBody.template_id ?? document.template_id,
        archive_ids: saveBody.archive_ids ?? document.archive_ids,
        semantic_state: {
          ...document.semantic_state,
          knowledge_binding: saveBody.knowledge_binding ?? document.semantic_state.knowledge_binding ?? null,
        },
        status: "draft",
        updated_at: "2026-04-30T00:10:00Z",
      };
      return Promise.resolve({ data: document });
    }
    if (url === "/requirement-authoring/documents/doc-1/messages") {
      document = {
        ...document,
        conversation: [
          ...document.conversation,
          { id: "msg-user", role: "user", content: (body as { content: string }).content },
          { id: "msg-ai", role: "assistant", content: "已补入超时提醒。你可以直接回：可以 / 更正式 / 重拟。" },
        ],
        document: {
          ...document.document,
          sections: document.document.sections.map((section) =>
            section.section_id === "3"
              ? {
                  ...section,
                  clauses: section.clauses.map((clause) =>
                    clause.clause_id === "REQ-3.3"
                      ? { ...clause, content: "异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。" }
                      : clause,
                  ),
                }
              : section,
          ),
        },
      };
      return Promise.resolve({ data: document });
    }
    if (url === "/requirement-authoring/documents/doc-1/check") {
      document = { ...document, check_result: { blocking_count: 1, warning_count: 0, passed_count: 3, items: [] } };
      return Promise.resolve({ data: document });
    }
    if (url === "/requirement-authoring/documents/doc-1/freeze") {
      document = { ...document, status: "frozen", frozen_package: { p3_consumable: true } };
      return Promise.resolve({ data: document });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  patchMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-authoring/documents/doc-1/form-fields") {
      const fields = (body as { fields: Record<string, string> }).fields;
      document = {
        ...document,
        semantic_state: { ...document.semantic_state, fields: { ...document.semantic_state.fields, ...fields } },
        document: {
          ...document.document,
          sections: document.document.sections.map((section) =>
            section.section_id === "5"
              ? {
                  ...section,
                  clauses: [
                    {
                      clause_id: "REQ-5.1",
                      title: "验收准则",
                      content: fields.acceptance_criteria,
                      status: "synced",
                    },
                  ],
                }
              : section,
          ),
        },
      };
      return Promise.resolve({ data: document });
    }
    throw new Error(`unexpected patch url: ${url}`);
  });
  deleteMock.mockImplementation((url: string) => {
    if (url === "/requirement-authoring/documents/doc-1") {
      return Promise.resolve({ data: { deleted: true, document_id: "doc-1" } });
    }
    throw new Error(`unexpected delete url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/requirement-authoring"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 专家需求规格编写工作台" })).toBeInTheDocument();
  expect(screen.getByText("配置接口下发的专家工作台副标题。")).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("P1 知识绑定")).not.toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "文档模板：81433号" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "领域知识：未选择" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建文档" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "打开文档" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "保存草稿" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "删除文档" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "打开文档" }));
  expect(await screen.findByText("打开文档 / 草稿")).toBeInTheDocument();
  expect(screen.getByText("打开后会恢复右侧标准正文、左侧问答记录、表单字段、批注和检查状态。")).toBeInTheDocument();
  expect(screen.getByText("空域协同规划软件需求规格说明")).toBeInTheDocument();
  expect(screen.getByText("81433号")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "打开" }));
  await waitFor(() => expect(getMock).toHaveBeenCalledWith("/requirement-authoring/documents/doc-1"));
  expect(await screen.findByText("我会按标准规格骨架持续起草和修补。你可以直接回：可以 / 更正式 / 加超时 / 重拟 / 继续。")).toBeInTheDocument();
  expect(screen.getByLabelText("文档名称")).toHaveValue("空域协同规划软件需求规格说明");
  fireEvent.click(screen.getByRole("button", { name: "删除文档" }));
  fireEvent.click(screen.getByRole("button", { name: "取消" }));

  fireEvent.click(screen.getByRole("button", { name: "领域知识：未选择" }));
  expect(await screen.findByText("选择领域知识")).toBeInTheDocument();
  expect(screen.getByText("空域规划领域知识")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "应用领域知识" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-authoring/knowledge-bindings", {
      provider_id: "xx-p1-sim",
      domain_id: "airspace-planning",
    }),
  );
  expect((await screen.findAllByText("领域知识已绑定")).length).toBeGreaterThan(0);
  expect(await screen.findByRole("button", { name: "领域知识：空域规划" })).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "新建文档" }));

  expect(await screen.findByText("问答模式")).toBeInTheDocument();
  expect(screen.getByText("表单模式")).toBeInTheDocument();
  expect(screen.getAllByText("标准需求规格说明").length).toBeGreaterThan(0);
  expect(screen.getByText("2:3")).toBeInTheDocument();
  expect(screen.queryByText("写入正文")).not.toBeInTheDocument();
  expect(screen.queryByText("XX-P1-Sim")).not.toBeInTheDocument();
  expect(screen.queryByText("mock")).not.toBeInTheDocument();
  expect(screen.queryByText("模拟")).not.toBeInTheDocument();
  expect(screen.queryByText("发生器")).not.toBeInTheDocument();
  expect(screen.getByTestId("requirement-authoring-document-canvas")).toBeInTheDocument();
  expect(screen.getByTestId("requirement-authoring-document-paper")).toBeInTheDocument();
  expect(screen.getByText("配置可导出稿")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "保存草稿" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "删除文档" })).toBeEnabled();

  fireEvent.change(screen.getByLabelText("文档名称"), { target: { value: "专家评审草稿 A" } });
  fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-authoring/documents/doc-1/save", expect.objectContaining({
      title: "专家评审草稿 A",
      template_id: "tpl-81433-default",
      archive_ids: ["airspace-planning"],
      knowledge_binding: expect.objectContaining({ editor_badge: "领域知识已绑定" }),
    })),
  );
  expect(await screen.findByText("草稿已保存")).toBeInTheDocument();
  expect(screen.getByLabelText("文档名称")).toHaveValue("专家评审草稿 A");

  fireEvent.change(screen.getByLabelText("文档名称"), { target: { value: "问答前临时改名" } });
  const input = screen.getByPlaceholderText("输入 A、可以、更正式、加超时、重拟，或直接补充一句业务事实");
  fireEvent.change(input, { target: { value: "加超时，别写太复杂" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith("/requirement-authoring/documents/doc-1/save", expect.objectContaining({
      title: "问答前临时改名",
      template_id: "tpl-81433-default",
      archive_ids: ["airspace-planning"],
      knowledge_binding: expect.objectContaining({ editor_badge: "领域知识已绑定" }),
    })),
  );
  expect(await screen.findByText("异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。")).toBeInTheDocument();
  expect(await screen.findByText(/你可以直接回/)).toBeInTheDocument();
  expect(screen.getByLabelText("文档名称")).toHaveValue("问答前临时改名");

  fireEvent.click(screen.getByText("表单模式"));
  fireEvent.change(screen.getByLabelText("验收准则"), { target: { value: "关键流程可追溯，超时提醒可验证。" } });
  await waitFor(() => expect(screen.getByText("关键流程可追溯，超时提醒可验证。")).toBeInTheDocument());

  fireEvent.click(screen.getByText("REQ-3.3"));
  expect(await screen.findByText("条款批注")).toBeInTheDocument();
  expect(await screen.findByText("P3 输入映射")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "缺口检查" }));
  expect(await screen.findByText("阻断项 1")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "冻结版本" }));
  expect(await screen.findByText("P3 可消费")).toBeInTheDocument();
  expect(screen.getByLabelText("验收准则")).toBeDisabled();
  fireEvent.click(screen.getByText("问答模式"));
  expect(screen.getByPlaceholderText("输入 A、可以、更正式、加超时、重拟，或直接补充一句业务事实")).toBeDisabled();
  expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();

  const shell = screen.getByTestId("requirement-authoring-workbench");
  expect(within(shell).getByText("1:1")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "删除文档" }));
  expect(await screen.findByText("删除当前规格文档？")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "确认删除" }));
  await waitFor(() => expect(deleteMock).toHaveBeenCalledWith("/requirement-authoring/documents/doc-1"));
  expect(await screen.findByText("文档已删除")).toBeInTheDocument();
  expect(screen.getByText("配置下发：创建文档后展示标准正文。")).toBeInTheDocument();
});

function buildWorkbenchConfig() {
  return {
    page: {
      title: "P2 专家需求规格编写工作台",
      subtitle: "配置接口下发的专家工作台副标题。",
    },
    defaults: {
      document_title: "配置下发的默认需求规格说明",
      layout_ratio: "2:3",
      allow_empty_knowledge_binding: true,
    },
    layout_options: [
      { ratio: "2:3", label: "2:3" },
      { ratio: "1:1", label: "1:1" },
    ],
    document_statuses: [
      { status: "draft", label: "配置草稿", editable: true },
      { status: "checking", label: "配置检查中", editable: false },
      { status: "ready_to_freeze", label: "配置待冻结", editable: true },
      { status: "frozen", label: "配置已冻结", editable: false },
      { status: "submitted_to_p3", label: "配置已提交 P3", editable: false },
      { status: "archived", label: "配置已归档", editable: false },
    ],
    actions: [
      { action_id: "create_document", label: "新建文档", style: "primary" },
      { action_id: "open_document", label: "打开文档" },
      { action_id: "save_draft", label: "保存草稿", requires_document: true, disabled_when_frozen: true },
      { action_id: "delete_document", label: "删除文档", requires_document: true, danger: true },
      { action_id: "run_check", label: "缺口检查", requires_document: true },
      { action_id: "freeze", label: "冻结版本", requires_document: true },
    ],
    document_surface: {
      title: "标准需求规格说明",
      badges: ["配置可导出稿"],
      ribbon: ["配置页面 A4", "配置样式 标准正文", "配置段落 1.5 倍行距", "配置导出 DOCX / PDF"],
    },
    empty_states: {
      question_mode: "配置下发：创建规格文档后开始问答协作",
      form_mode: "配置下发：创建规格文档后开始表单校对",
      document: "配置下发：创建文档后展示标准正文。",
    },
  };
}

function buildTemplate(): RequirementAuthoringTemplate {
  return {
    template_id: "tpl-81433-default",
    template_code: "81433",
    name: "软件级需求规格说明模板",
    status: "active",
    description: "默认模板",
    sections: [],
    form_groups: [
      {
        group_id: "function",
        title: "功能需求",
        fields: [
          { field_key: "acceptance_criteria", label: "验收准则", required: true, clause_id: "REQ-5.1" },
        ],
      },
    ],
    field_mappings: [],
    questionnaire_policy: { quick_inputs: ["可以", "更正式", "加超时", "重拟"] },
    gap_rules: { required_fields: ["acceptance_criteria"] },
    knowledge_bindings: [{ archive_id: "20161116-nas", label: "NAS 体系结构知识库", enabled: true }],
    created_at: "2026-04-30T00:00:00Z",
    updated_at: "2026-04-30T00:00:00Z",
  };
}

function buildDocument(): RequirementAuthoringDocumentDetail {
  return {
    document_id: "doc-1",
    title: "空域协同规划软件需求规格说明",
    template_id: "tpl-81433-default",
    status: "draft",
    layout_ratio: "2:3",
    archive_ids: ["20161116-nas"],
    created_at: "2026-04-30T00:00:00Z",
    updated_at: "2026-04-30T00:00:00Z",
    semantic_state: { fields: { acceptance_criteria: "" }, knowledge_binding: null },
    conversation: [
      {
        id: "msg-1",
        role: "assistant",
        content: "我会按标准规格骨架持续起草和修补。你可以直接回：可以 / 更正式 / 加超时 / 重拟 / 继续。",
      },
    ],
    document: {
      title: "标准需求规格说明",
      sections: [
        {
          section_id: "1",
          title: "1 总则",
          clauses: [{ clause_id: "REQ-1.1", title: "编写目的", content: "待补齐：软件名称和领域范围。", status: "missing" }],
        },
        {
          section_id: "3",
          title: "3 功能需求",
          clauses: [
            { clause_id: "REQ-3.1", title: "用户与角色", content: "待补齐：目标用户、角色和职责。", status: "missing" },
            { clause_id: "REQ-3.2", title: "核心业务流程", content: "待补齐：核心业务流程和正常流程。", status: "missing" },
            { clause_id: "REQ-3.3", title: "异常与补偿", content: "待补齐：异常流程、超时和补偿策略。", status: "missing" },
          ],
        },
        {
          section_id: "5",
          title: "5 验收准则",
          clauses: [{ clause_id: "REQ-5.1", title: "验收准则", content: "待补齐：验收准则。", status: "missing" }],
        },
      ],
    },
    annotations: [
      {
        clause_id: "REQ-3.3",
        title: "异常与补偿",
        interpretation: "说明异常路径和补偿策略。",
        source_refs: ["NAS 体系结构知识库"],
        semantic_mapping: [{ field_key: "exception_flow", structured_path: "rules.exception_flow" }],
        p3_mapping: ["rules.exception_flow"],
        gaps: [],
        pending_confirmations: ["该条款仍需专家确认。"],
      },
    ],
    check_result: { blocking_count: 0, warning_count: 0, passed_count: 0, items: [] },
    frozen_package: null,
  };
}

function buildKnowledgeProviders() {
  return {
    items: [
      {
        provider_id: "xx-p1-sim",
        provider_name: "XX-P1-Sim",
        provider_kind: "p1_knowledge_provider",
        status: "online",
        capabilities: ["domain_catalog", "knowledge_archive"],
        version: "v1.0",
        seed: "xx-p1-sim-fixed-v1",
        domains: [
          {
            domain_id: "airspace-planning",
            domain_name: "空域规划领域知识",
            domain_summary: "包含空域对象、冲突窗口、协同规划流程、会签约束和证据片段。",
            archive_version: "v1.0",
            concept_count: 12,
            rule_count: 8,
            process_count: 3,
            evidence_count: 18,
          },
        ],
      },
    ],
  };
}

function buildKnowledgeBinding() {
  return {
    binding_id: "binding-xx-p1-sim-airspace-planning",
    provider: buildKnowledgeProviders().items[0],
    domain: buildKnowledgeProviders().items[0].domains[0],
    knowledge_archive: {
      archive_version: "v1.0",
      concepts: [{ concept_id: "concept-airspace-cell", name: "空域单元", definition: "用于表达可规划的空域范围。" }],
      rules: [{ rule_id: "rule-confirm-conflict-window", name: "冲突窗口确认规则", description: "冲突窗口未确认时，不得直接发布规划结果。" }],
      processes: [{ process_id: "process-airspace-coordination", name: "空域规划协同流程", steps: ["任务创建", "冲突识别"] }],
      constraints: [{ constraint_id: "constraint-audit-trace", category: "traceability", description: "关键状态变化需要保留责任人、时间和依据。" }],
      evidence_refs: [{ evidence_id: "evidence-airspace-term", source: "P1 发布态领域知识", excerpt: "空域规划过程应形成可追溯记录。" }],
    },
    editor_badge: "领域知识已绑定",
    created_document: null,
    frozen_package: null,
  };
}
