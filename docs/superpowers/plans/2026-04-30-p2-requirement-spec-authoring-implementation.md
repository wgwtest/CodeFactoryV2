# P2 Requirement Spec Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable P2 configurable standard requirements specification authoring system, including the expert workbench, configuration console, and backend APIs needed by both screens.

**Architecture:** Add a new `requirement_authoring` backend module with persisted templates and authoring documents while keeping the existing `/requirements` pool intact. Add React pages for `/requirement-authoring` and `/requirement-authoring/admin` that share one authoring document state: question mode, form mode, standard document rendering, annotations, gap check, and freeze.

**Tech Stack:** FastAPI, SQLAlchemy JSON columns, Pydantic, pytest, React 18, Ant Design 5, Vitest, Testing Library.

---

## File Structure

- Create `apps/api/app/requirement_authoring/models.py`: Pydantic contracts and default template builders.
- Create `apps/api/app/requirement_authoring/service.py`: template seeding, document lifecycle, deterministic question/form sync, gap check, freeze package.
- Create `apps/api/app/api/routes/requirement_authoring.py`: HTTP endpoints under `/requirement-authoring`.
- Modify `apps/api/app/db/models/requirements.py`: add `RequirementAuthoringTemplate` and `RequirementAuthoringDocument` tables.
- Modify `apps/api/app/main.py`: include the new router.
- Create `apps/api/tests/test_requirement_authoring_api.py`: backend TDD coverage.
- Create `apps/web/src/lib/requirementAuthoring.ts`: frontend API client.
- Modify `apps/web/src/lib/api.ts`: authoring types.
- Create `apps/web/src/pages/RequirementAuthoringPage.tsx`: expert workbench.
- Create `apps/web/src/pages/RequirementAuthoringAdminPage.tsx`: configuration console.
- Create `apps/web/src/pages/RequirementAuthoringPage.css`: dense professional split-screen styling.
- Modify `apps/web/src/App.tsx`: routes and menu entries.
- Create `apps/web/src/test/RequirementAuthoringPage.test.tsx`: workbench tests.
- Create `apps/web/src/test/RequirementAuthoringAdminPage.test.tsx`: config console tests.

## Task 1: Backend Authoring API

**Files:**
- Create: `apps/api/tests/test_requirement_authoring_api.py`
- Create: `apps/api/app/requirement_authoring/models.py`
- Create: `apps/api/app/requirement_authoring/service.py`
- Create: `apps/api/app/api/routes/requirement_authoring.py`
- Modify: `apps/api/app/db/models/requirements.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_requirement_authoring_document_lifecycle() -> None:
    client = TestClient(create_app())

    templates = client.get("/api/requirement-authoring/templates")
    assert templates.status_code == 200
    assert templates.json()[0]["template_code"] == "81433"
    assert templates.json()[0]["status"] == "active"

    created = client.post(
        "/api/requirement-authoring/documents",
        json={
            "title": "空域协同规划软件需求规格说明",
            "template_id": templates.json()[0]["template_id"],
            "archive_ids": ["20161116-nas"],
        },
    )
    assert created.status_code == 200
    document = created.json()
    assert document["layout_ratio"] == "2:3"
    assert document["status"] == "draft"
    assert document["document"]["sections"][2]["clauses"][0]["clause_id"] == "REQ-3.1"
    assert "待补齐" in document["document"]["sections"][2]["clauses"][1]["content"]

    replied = client.post(
        f"/api/requirement-authoring/documents/{document['document_id']}/messages",
        json={"content": "加超时，别写太复杂"},
    )
    assert replied.status_code == 200
    updated = replied.json()
    assert updated["semantic_state"]["fields"]["exception_flow"] == "包含超时提醒和人工确认，不扩展复杂补偿链路。"
    assert "超时提醒" in updated["document"]["sections"][2]["clauses"][2]["content"]
    assert updated["conversation"][-1]["role"] == "assistant"
    assert "可以直接回" in updated["conversation"][-1]["content"]

    form_updated = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
        json={"fields": {"acceptance_criteria": "关键流程可追溯，超时提醒可验证。"}},
    )
    assert form_updated.status_code == 200
    assert "关键流程可追溯" in form_updated.json()["document"]["sections"][4]["clauses"][0]["content"]

    checked = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/check")
    assert checked.status_code == 200
    assert checked.json()["check_result"]["blocking_count"] > 0

    freeze_blocked = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/freeze")
    assert freeze_blocked.status_code == 409

    completed = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
        json={
            "fields": {
                "application_name": "空域协同规划软件",
                "domain_scope": "国家空域管理",
                "target_users": "运行协调员、体系架构师",
                "main_process": "协同规划与冲突处置",
                "normal_flow": "创建规划、识别冲突、协同确认、形成处置记录。",
                "non_functional": "关键告警 2 分钟内反馈。",
            }
        },
    )
    assert completed.status_code == 200

    checked_ready = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/check")
    assert checked_ready.json()["status"] == "ready_to_freeze"

    frozen = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"
    assert frozen.json()["frozen_package"]["p3_consumable"] is True
    assert frozen.json()["frozen_package"]["structured_spec"]["application"]["name"] == "空域协同规划软件"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run pytest apps/api/tests/test_requirement_authoring_api.py -q`

Expected: FAIL because `/api/requirement-authoring/templates` is not registered.

- [ ] **Step 3: Implement the backend module**

Implement the new SQLAlchemy models, service, and router exactly around the tested endpoints:

- `GET /api/requirement-authoring/templates`
- `POST /api/requirement-authoring/templates`
- `PUT /api/requirement-authoring/templates/{template_id}`
- `POST /api/requirement-authoring/templates/{template_id}/activate`
- `GET /api/requirement-authoring/documents`
- `POST /api/requirement-authoring/documents`
- `GET /api/requirement-authoring/documents/{document_id}`
- `POST /api/requirement-authoring/documents/{document_id}/messages`
- `PATCH /api/requirement-authoring/documents/{document_id}/form-fields`
- `PATCH /api/requirement-authoring/documents/{document_id}/clauses/{clause_id}`
- `POST /api/requirement-authoring/documents/{document_id}/check`
- `POST /api/requirement-authoring/documents/{document_id}/freeze`

- [ ] **Step 4: Run the backend test and verify it passes**

Run: `uv run pytest apps/api/tests/test_requirement_authoring_api.py -q`

Expected: PASS.

## Task 2: Frontend Expert Workbench

**Files:**
- Create: `apps/web/src/test/RequirementAuthoringPage.test.tsx`
- Create: `apps/web/src/lib/requirementAuthoring.ts`
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/pages/RequirementAuthoringPage.tsx`
- Create: `apps/web/src/pages/RequirementAuthoringPage.css`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Write the failing workbench test**

```tsx
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";

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
  const template = buildTemplate();
  let document = buildDocument();

  getMock.mockImplementation((url: string) => {
    if (url === "/archives") {
      return Promise.resolve({ data: [] });
    }
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
```

- [ ] **Step 2: Run the workbench test and verify it fails**

Run: `pnpm --dir apps/web test -- RequirementAuthoringPage.test.tsx`

Expected: FAIL because `/requirement-authoring` is not routed.

- [ ] **Step 3: Implement the workbench page**

Build the route with a professional split-screen operations layout:

- left panel has only `问答模式` and `表单模式`;
- default split uses CSS grid columns `minmax(380px, 2fr) minmax(520px, 3fr)`;
- `1:1` toggle uses `minmax(420px, 1fr) minmax(520px, 1fr)`;
- no button or text labeled `写入正文`;
- messages and form edits update the same document response;
- clause click opens a floating annotation drawer/popover;
- check and freeze buttons call backend actions.

- [ ] **Step 4: Run the workbench test and verify it passes**

Run: `pnpm --dir apps/web test -- RequirementAuthoringPage.test.tsx`

Expected: PASS.

## Task 3: Frontend Configuration Console

**Files:**
- Create: `apps/web/src/test/RequirementAuthoringAdminPage.test.tsx`
- Create: `apps/web/src/pages/RequirementAuthoringAdminPage.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Write the failing admin test**

```tsx
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
    if (url === "/archives") {
      return Promise.resolve({ data: [] });
    }
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
```

- [ ] **Step 2: Run the admin test and verify it fails**

Run: `pnpm --dir apps/web test -- RequirementAuthoringAdminPage.test.tsx`

Expected: FAIL because the admin route/page does not exist.

- [ ] **Step 3: Implement the admin page**

Use the same API client. The page must expose first-version usable controls for:

- specification templates;
- form fields;
- field mappings;
- questionnaire strategy;
- gap checks;
- knowledge binding;
- test preview.

- [ ] **Step 4: Run the admin test and verify it passes**

Run: `pnpm --dir apps/web test -- RequirementAuthoringAdminPage.test.tsx`

Expected: PASS.

## Task 4: Integrated Verification

- [ ] **Step 1: Run targeted backend tests**

Run: `uv run pytest apps/api/tests/test_requirement_authoring_api.py apps/api/tests/test_requirement_specs_api.py -q`

Expected: PASS.

- [ ] **Step 2: Run targeted frontend tests**

Run: `pnpm --dir apps/web test -- RequirementAuthoringPage.test.tsx RequirementAuthoringAdminPage.test.tsx AppRoutes.test.tsx`

Expected: PASS.

- [ ] **Step 3: Run full frontend build**

Run: `pnpm --dir apps/web build`

Expected: PASS.

- [ ] **Step 4: Commit the implementation**

Run:

```bash
git add apps/api apps/web docs/superpowers/plans/2026-04-30-p2-requirement-spec-authoring-implementation.md
git commit -m "实现P2需求规格编写首版"
```

Expected: commit succeeds with the new P2 authoring implementation.

## Self-Review

- Spec coverage: expert workbench, two input tabs, 2:3 and 1:1 split, continuous right-side standard document, floating clause annotations, configurable templates, form fields, mappings, question policy, gap checks, knowledge binding, check, and freeze are covered.
- Scope: first-version usable implementation, not full platform governance.
- Placeholder scan: no deferred task or undefined route remains in this plan.
