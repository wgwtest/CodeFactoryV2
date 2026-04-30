import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

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

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  putMock.mockReset();
});

test("renders P2 configuration console and creates a replaceable template", async () => {
  const templates = [buildTemplate()];

  getMock.mockImplementation((url: string) => {
    if (url === "/requirement-authoring/templates") {
      return Promise.resolve({ data: templates });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string, body?: unknown) => {
    if (url === "/requirement-authoring/templates") {
      const created = {
        ...buildTemplate(),
        template_id: "tpl-custom",
        template_code: (body as { template_code: string }).template_code,
        name: (body as { name: string }).name,
        status: "draft",
      };
      templates.push(created);
      return Promise.resolve({ data: created });
    }
    if (url === "/requirement-authoring/templates/tpl-custom/activate") {
      templates[1] = { ...templates[1], status: "active" };
      return Promise.resolve({ data: templates[1] });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/requirement-authoring/admin"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "P2 配置与模板管理台" })).toBeInTheDocument();
  expect(screen.getByText("规格模板")).toBeInTheDocument();
  expect(screen.getByText("表单字段")).toBeInTheDocument();
  expect(screen.getByText("字段映射")).toBeInTheDocument();
  expect(screen.getByText("问答策略")).toBeInTheDocument();
  expect(screen.getByText("缺口检查")).toBeInTheDocument();
  expect(screen.getByText("知识库绑定")).toBeInTheDocument();
  expect(screen.getByText("测试预览")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "新增模板" }));
  fireEvent.change(await screen.findByLabelText("模板编码"), { target: { value: "CUSTOM-1" } });
  fireEvent.change(screen.getByLabelText("模板名称"), { target: { value: "自定义软件规格模板" } });
  fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

  expect(await screen.findByText("自定义软件规格模板")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "启用自定义软件规格模板" }));
  expect(await screen.findByText("active")).toBeInTheDocument();
});

function buildTemplate() {
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
        fields: [{ field_key: "normal_flow", label: "正常流程", required: true, clause_id: "REQ-3.2" }],
      },
    ],
    field_mappings: [{ field_key: "normal_flow", clause_id: "REQ-3.2", structured_path: "processes[0].description" }],
    questionnaire_policy: { quick_inputs: ["可以", "更正式", "加超时", "重拟"] },
    gap_rules: { required_fields: ["normal_flow"] },
    knowledge_bindings: [{ archive_id: "20161116-nas", label: "NAS 体系结构知识库", enabled: true }],
    created_at: "2026-04-30T00:00:00Z",
    updated_at: "2026-04-30T00:00:00Z",
  };
}
