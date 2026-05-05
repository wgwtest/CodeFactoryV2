import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

test("renders xx-p1-sim as an upstream P1 knowledge service interface", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/xx-p1-sim/domains") {
      return Promise.resolve({ data: buildDomainCatalog() });
    }
    if (url === "/xx-p1-sim/domains/airspace-planning/knowledge") {
      return Promise.resolve({ data: buildKnowledgeArchive() });
    }
    if (url === "/xx-p1-sim/logs") {
      return Promise.resolve({ data: buildLogs() });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  postMock.mockImplementation((url: string) => {
    if (url === "/xx-p1-sim/register") {
      return Promise.resolve({ data: buildDomainCatalog().provider });
    }
    if (url === "/xx-p1-sim/reset") {
      return Promise.resolve({ data: { provider_id: "xx-p1-sim", seed: "xx-p1-sim-fixed-v1", archive_version: "v1.0", log_count: 1 } });
    }
    throw new Error(`unexpected post url: ${url}`);
  });

  render(
    <MemoryRouter initialEntries={["/xx-p1-sim"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "XX-P1-Sim" })).toBeInTheDocument();
  expect(screen.queryByText("知识仓库")).not.toBeInTheDocument();
  expect(screen.getByText("P1 服务接口")).toBeInTheDocument();
  expect(screen.getByText("最近调用日志")).toBeInTheDocument();
  expect(screen.getByText("领域知识目录")).toBeInTheDocument();
  expect(screen.getByText("空域规划知识包预览")).toBeInTheDocument();
  expect(screen.getByText("/api/xx-p1-sim/domains/{domain_id}/knowledge")).toBeInTheDocument();
  expect(screen.getByText("空域规划领域知识")).toBeInTheDocument();
  expect(screen.getByText("knowledge_archive v1.0")).toBeInTheDocument();
  expect(screen.queryByText("服务注册状态")).not.toBeInTheDocument();
  expect(screen.queryByText("P1 输出契约")).not.toBeInTheDocument();
  expect(screen.queryByText("空域协同规划软件")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "注册到 P2" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/xx-p1-sim/register"));

  fireEvent.click(screen.getByRole("button", { name: "重置种子" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/xx-p1-sim/reset"));
});

function buildDomainCatalog() {
  return {
    provider: {
      provider_id: "xx-p1-sim",
      provider_name: "XX-P1-Sim",
      provider_kind: "p1_knowledge_provider",
      status: "online",
      capabilities: ["domain_catalog", "knowledge_archive"],
      version: "v1.0",
      seed: "xx-p1-sim-fixed-v1",
    },
    items: [
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
  };
}

function buildKnowledgeArchive() {
  return {
    provider_id: "xx-p1-sim",
    domain_id: "airspace-planning",
    archive_id: "archive-airspace-planning-v1",
    archive_version: "v1.0",
    published_at: "2026-04-30T00:00:00+00:00",
    concepts: [
      { concept_id: "concept-airspace-cell", name: "空域单元", definition: "用于表达可规划的空域范围。" },
      { concept_id: "concept-conflict-window", name: "冲突窗口", definition: "存在冲突风险的窗口。" },
      { concept_id: "concept-coordination-task", name: "协同任务", definition: "协同处理事项。" },
    ],
    entities: [],
    rules: [{ rule_id: "rule-confirm-conflict-window", name: "冲突窗口确认规则", description: "冲突窗口未确认时，不得直接发布规划结果。" }],
    processes: [{ process_id: "process-airspace-coordination", name: "空域规划协同流程", steps: ["任务创建", "冲突识别", "协同会签", "结果发布"] }],
    constraints: [{ constraint_id: "constraint-audit-trace", category: "traceability", description: "关键状态变化需要保留责任人、时间和依据。" }],
    evidence_refs: [{ evidence_id: "evidence-airspace-term", source: "P1 发布态领域知识", excerpt: "空域规划过程应形成可追溯记录。" }],
  };
}

function buildLogs() {
  return {
    items: [
      {
        call_id: "p1-sim-call-0001",
        called_at: "2026-04-30T21:45:08+00:00",
        method: "GET",
        path: "/api/xx-p1-sim/domains",
        domain_id: null,
        status_code: 200,
        archive_version: "v1.0",
      },
    ],
  };
}
