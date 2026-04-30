import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";
import type { RequirementAuthoringDocumentDetail, RequirementAuthoringTemplate } from "../lib/api";

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
});

test("renders P2 expert workbench with CLI question mode, form mode, live document, annotation, check and freeze", async () => {
  const template: RequirementAuthoringTemplate = buildTemplate();
  let document: RequirementAuthoringDocumentDetail = buildDocument();

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-authoring/templates") {
      return Promise.resolve({ data: [template] });
    }
    if (url === "/requirement-authoring/documents") {
      return Promise.resolve({ data: [] });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-authoring/documents") {
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

  render(
    <MemoryRouter initialEntries={["/requirement-authoring"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 专家需求规格编写工作台" })).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "创建规格文档" }));

  expect(await screen.findByText("问答模式")).toBeInTheDocument();
  expect(screen.getByText("表单模式")).toBeInTheDocument();
  expect(screen.getByText("标准需求规格说明")).toBeInTheDocument();
  expect(screen.getByText("2:3")).toBeInTheDocument();
  expect(screen.queryByText("写入正文")).not.toBeInTheDocument();
  expect(screen.getByTestId("requirement-authoring-document-canvas")).toBeInTheDocument();
  expect(screen.getByTestId("requirement-authoring-document-paper")).toBeInTheDocument();
  expect(screen.getByText("可导出稿")).toBeInTheDocument();

  const input = screen.getByPlaceholderText("输入 A、可以、更正式、加超时、重拟，或直接补充一句业务事实");
  fireEvent.change(input, { target: { value: "加超时，别写太复杂" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。")).toBeInTheDocument();
  expect(await screen.findByText(/你可以直接回/)).toBeInTheDocument();

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

  const shell = screen.getByTestId("requirement-authoring-workbench");
  expect(within(shell).getByText("1:1")).toBeInTheDocument();
});

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
    semantic_state: { fields: { acceptance_criteria: "" } },
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
