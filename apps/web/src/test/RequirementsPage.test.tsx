import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
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

test("creates requirement model, adds formal and temporary objects, then saves", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/requirements/specs") {
      return Promise.resolve({ data: [] });
    }

    if (url === "/requirements/formal-elements?item_type=entity&archive_id=20161116-nas") {
      return Promise.resolve({
        data: [
          {
            id: "entity-nas",
            name: "国家空域系统",
            item_type: "entity",
            category: "system_or_service",
            aliases: ["NAS"],
            document_count: 11,
            summary: "国家空域系统 是系统/服务类实体。",
            source_archive_id: "20161116-nas",
          },
          {
            id: "entity-controller",
            name: "运行协调员",
            item_type: "entity",
            category: "organization",
            aliases: [],
            document_count: 8,
            summary: "运行协调员 是组织类实体。",
            source_archive_id: "20161116-nas",
          },
        ],
      });
    }

    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/requirements/specs") {
      return Promise.resolve({
        data: {
          id: "spec-1",
          application_name: "未命名应用",
          domain_name: "",
          status: "draft",
          archive_id: "20161116-nas",
          object_count: 0,
          formal_object_count: 0,
          temporary_object_count: 0,
          process_count: 0,
          created_at: "2026-04-14T00:00:00Z",
          updated_at: "2026-04-14T00:00:00Z",
          payload: {
            application: {
              name: "未命名应用",
              domain: "",
              summary: "",
              target_users: [],
            },
            objects: [],
            processes: [],
            rules: [],
            metrics: [],
            non_functional_constraints: [],
          },
        },
      });
    }

    throw new Error(`unexpected post url: ${url}`);
  });

  putMock.mockImplementation((url: string, body: unknown) => {
    if (url === "/requirements/specs/spec-1") {
      const payload = body as {
        archive_id: string;
        status: string;
        payload: {
          application: { name: string; domain: string; summary: string; target_users: string[] };
          objects: Array<{ name: string; source_kind: string }>;
          processes: unknown[];
          rules: unknown[];
          metrics: unknown[];
          non_functional_constraints: unknown[];
        };
      };

      return Promise.resolve({
        data: {
          id: "spec-1",
          application_name: payload.payload.application.name,
          domain_name: payload.payload.application.domain,
          status: payload.status,
          archive_id: payload.archive_id,
          object_count: payload.payload.objects.length,
          formal_object_count: payload.payload.objects.filter((item) => item.source_kind === "formal").length,
          temporary_object_count: payload.payload.objects.filter((item) => item.source_kind === "temporary").length,
          process_count: payload.payload.processes.length,
          created_at: "2026-04-14T00:00:00Z",
          updated_at: "2026-04-14T01:00:00Z",
          payload: payload.payload,
        },
      });
    }

    throw new Error(`unexpected put url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/requirements"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "应用需求建模" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "创建需求模型" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "创建需求模型" }));

  expect(await screen.findByDisplayValue("未命名应用")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("应用名称"), { target: { value: "空域协同平台" } });
  fireEvent.change(screen.getByLabelText("领域范围"), { target: { value: "国家空域管理" } });
  fireEvent.change(screen.getByLabelText("目标用户"), { target: { value: "运行协调员,体系架构师" } });

  const formalCard = await screen.findByText("国家空域系统");
  const formalRow = formalCard.closest(".ant-list-item");
  expect(formalRow).not.toBeNull();
  fireEvent.click(within(formalRow as HTMLElement).getByRole("button", { name: "加入模型" }));

  expect(await screen.findByText("已选业务对象")).toBeInTheDocument();
  expect((await screen.findAllByText("国家空域系统")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "新增临时对象" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("对象名称"), { target: { value: "协同告警单" } });
  fireEvent.change(within(dialog).getByLabelText("对象说明"), { target: { value: "建模现场新增的支撑对象" } });
  fireEvent.click(screen.getByRole("button", { name: "确认添加" }));

  expect(await screen.findByText("协同告警单")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "保存模型" }));

  expect(await screen.findByText("最近保存时间：2026-04-14T01:00:00Z")).toBeInTheDocument();
  expect(await screen.findByText("空域协同平台")).toBeInTheDocument();
});
