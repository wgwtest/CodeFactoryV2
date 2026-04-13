import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();
const putMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    put: (...args: unknown[]) => putMock(...args),
  },
}));

test("renders application modeler, switches steps, saves draft, and exports markdown", async () => {
  postMock.mockImplementation((url: string) => {
    if (url === "/modeling/requirement-drafts") {
      return Promise.resolve({
        data: {
          draft: {
            draft_id: "draft-1",
            archive_id: "20161116-nas",
            status: "draft",
            current_step: "goal",
            application_name: "",
            application_goal: {
              problem_statement: "",
              target_outcome: "",
              success_criteria: [],
            },
            audiences: [],
            roles: [],
            business_flows: [],
            business_objects: [],
            key_events: [],
            application_structure: {
              workspaces: [],
              pages: [],
              permission_intents: [],
            },
            knowledge_references: [],
            manual_additions: [],
            created_at: "2026-04-13T00:00:00Z",
            updated_at: "2026-04-13T00:00:00Z",
          },
          recommendations: {
            goal: [
              {
                id: "goal-1",
                name: "缩短办理周期",
                description: "适用于审批链路过长的场景。",
                source: "recommended_common",
                tags: ["效率提升"],
              },
            ],
            audience: [
              {
                id: "audience-1",
                name: "业务发起人员",
                description: "负责提交申请并跟踪进度。",
                source: "recommended_common",
                tags: ["办理发起"],
              },
            ],
            flow: [
              {
                id: "flow-1",
                name: "申请审批流程",
                description: "申请审批流程覆盖发起、审核、办结。",
                source: "recommended_domain",
                tags: ["领域流程"],
              },
            ],
            object_event: [],
            structure: [
              {
                id: "structure-1",
                name: "工作台 + 待办处理页",
                description: "适用于审批办理场景。",
                source: "recommended_common",
                tags: ["工作台"],
              },
            ],
          },
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  putMock.mockResolvedValue({
    data: {
      draft: {
        draft_id: "draft-1",
        archive_id: "20161116-nas",
        status: "draft",
        current_step: "audience",
        application_name: "审批协同应用",
        application_goal: {
          problem_statement: "",
          target_outcome: "",
          success_criteria: [],
        },
        audiences: [],
        roles: [],
        business_flows: [],
        business_objects: [],
        key_events: [],
        application_structure: {
          workspaces: [],
          pages: [],
          permission_intents: [],
        },
        knowledge_references: [],
        manual_additions: [],
        created_at: "2026-04-13T00:00:00Z",
        updated_at: "2026-04-13T00:05:00Z",
      },
      recommendations: {
        goal: [],
        audience: [],
        flow: [],
        object_event: [],
        structure: [],
      },
    },
  });

  getMock.mockImplementation((url: string) => {
    if (url === "/modeling/requirement-drafts/draft-1/export") {
      return Promise.resolve({
        data: {
          draft_id: "draft-1",
          model: {
            archive_id: "20161116-nas",
            application_name: "审批协同应用",
            application_goal: {
              problem_statement: "审批流转慢",
              target_outcome: "缩短办理周期",
              success_criteria: ["审批时长下降"],
            },
            audiences: [],
            roles: [],
            business_flows: [],
            business_objects: [],
            key_events: [],
            application_structure: {
              workspaces: [],
              pages: [],
              permission_intents: [],
            },
            knowledge_references: [],
            manual_additions: [],
          },
          json_text: "{\n  \"application_name\": \"审批协同应用\"\n}",
          yaml_text: "application_name: 审批协同应用",
          markdown: "# 应用需求模型\n\n## 核心流程范围\n- 申请审批流程",
        },
      });
    }

    throw new Error(`unexpected get url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/modeling"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("应用需求建模器")).toBeInTheDocument();
  expect(await screen.findByText("业务目标")).toBeInTheDocument();
  expect(await screen.findByText("使用对象")).toBeInTheDocument();
  expect(await screen.findByText("核心流程")).toBeInTheDocument();
  expect(await screen.findByText("关键信息与动作")).toBeInTheDocument();
  expect(await screen.findByText("应用承载方式")).toBeInTheDocument();
  expect(await screen.findByText("业务模型预览")).toBeInTheDocument();
  expect(await screen.findByText("应用结构建议")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "保存草稿" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "导出结果" })).toBeInTheDocument();
  expect(await screen.findByText("申请审批流程")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("先给这个应用起个名字"), {
    target: { value: "审批协同应用" },
  });

  fireEvent.click(screen.getByText("使用对象"));
  expect(await screen.findByText("谁会使用这个应用？")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
  await waitFor(() =>
    expect(putMock).toHaveBeenCalledWith("/modeling/requirement-drafts/draft-1", expect.objectContaining({
      current_step: "audience",
      application_name: "审批协同应用",
    })),
  );

  fireEvent.click(screen.getByRole("button", { name: "导出结果" }));
  await waitFor(() => expect(getMock).toHaveBeenCalledWith("/modeling/requirement-drafts/draft-1/export"));
  expect(await screen.findByText("导出结果预览")).toBeInTheDocument();
  expect(await screen.findByText("## 核心流程范围")).toBeInTheDocument();
});
