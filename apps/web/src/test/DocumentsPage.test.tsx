import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import { DocumentsPage } from "../pages/DocumentsPage";

const getMock = vi.fn();
const formalizeArchiveDocumentMock = vi.fn();
const importArchiveDocumentMock = vi.fn();
const removeArchiveDocumentMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

vi.mock("../lib/archives", () => ({
  formalizeArchiveDocument: (...args: unknown[]) => formalizeArchiveDocumentMock(...args),
  importArchiveDocument: (...args: unknown[]) => importArchiveDocumentMock(...args),
  removeArchiveDocument: (...args: unknown[]) => removeArchiveDocumentMock(...args),
}));

beforeEach(() => {
  getMock.mockReset();
  formalizeArchiveDocumentMock.mockReset();
  importArchiveDocumentMock.mockReset();
  removeArchiveDocumentMock.mockReset();
});

test("renders archive-only document workspace and opens archive knowledge drawer", async () => {
  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 65,
          entity_count: 586,
          event_count: 4,
          process_count: 6,
        },
      });
    }

    if (url.endsWith("/documents/doc-1")) {
      return Promise.resolve({
        data: {
          document: {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
          },
          knowledge_items: [
            {
              id: "entity-ov1",
              name: "OV-1",
              item_type: "entity",
              category: "architecture_artifact",
              aliases: ["远期顶层运行概念图"],
              interpretation: {
                kind_label: "架构工件",
                family_code: "OV",
                family_label: "运行视图",
                display_name: "高层运行概念图",
                standard_name: "High-Level Operational Concept Graphic",
                summary: "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
                producer_hint: "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
              },
              evidence: [
                {
                  document_id: "doc-1",
                  document_title: "NAS AV-1",
                  excerpt: "OV-1 excerpt",
                },
              ],
            },
            {
              id: "event-far-term",
              name: "远期目标（Far Term）",
              item_type: "event",
              category: "timeline_event",
              aliases: [],
              interpretation: {
                kind_label: "时间事件",
                family_code: null,
                family_label: null,
                display_name: null,
                standard_name: null,
                summary: "远期目标（Far Term）是时间事件类实体。",
                producer_hint: null,
              },
              evidence: [
                {
                  document_id: "doc-1",
                  document_title: "NAS AV-1",
                  excerpt: "Far Term excerpt",
                },
              ],
            },
          ],
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
            included_in_archive: true,
          },
          {
            id: "doc-2",
            title: "NAS Roadmap",
            file_type: "docx",
            source_archive: "20161116 路线图",
            character_count: 800,
            entity_count: 1,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 1,
            included_in_archive: false,
          },
        ],
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter>
      <DocumentsPage />
    </MemoryRouter>,
  );

  expect(await screen.findByTestId("workspace-overview-strip")).toBeInTheDocument();
  expect(screen.getByText("知识库文档总览")).toBeInTheDocument();
  expect(await screen.findByText("知识库文档页只保留 archive 主链")).toBeInTheDocument();
  expect(await screen.findByText("当前知识库文档")).toBeInTheDocument();
  expect(await screen.findByText("NAS AV-1")).toBeInTheDocument();
  expect(await screen.findByText("NAS Roadmap")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "从当前知识库移出" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "纳入当前知识库" })).toBeInTheDocument();
  expect(getMock).not.toHaveBeenCalledWith("/documents");

  fireEvent.change(screen.getByPlaceholderText("搜索文档标题、来源或类型"), { target: { value: "NAS AV-1" } });

  expect(await screen.findByDisplayValue("NAS AV-1")).toBeInTheDocument();
  expect(screen.queryByText("NAS Roadmap")).not.toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "查看" }));

  expect(await screen.findByText("文档详情")).toBeInTheDocument();
  expect(await screen.findByText("文档概览")).toBeInTheDocument();
  expect((await screen.findAllByText("实体")).length).toBeGreaterThan(0);
  expect((await screen.findAllByText("事件")).length).toBeGreaterThan(0);
  expect(await screen.findByText("高层运行概念图")).toBeInTheDocument();
  expect(await screen.findByText("OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。")).toBeInTheDocument();
  expect(await screen.findByText("OV-1 excerpt")).toBeInTheDocument();
});

test("imports a new document into the active archive and shows import feedback", async () => {
  importArchiveDocumentMock.mockResolvedValue({
    data: {
      archive_id: "20161116-nas",
      document_id: "doc-imported",
      action: "include",
      mode: "single_document_import",
      document_included: true,
      stored_path: "manual_uploads/2026-04-18/new-guide.docx",
      summary: {
        archive_id: "20161116-nas",
        document_count: 2,
        entity_count: 11,
        event_count: 1,
        process_count: 1,
      },
      document: {
        id: "doc-imported",
        title: "new-guide",
        file_type: "docx",
        source_archive: "manual_uploads",
        character_count: 900,
        entity_count: 1,
        event_count: 0,
        process_count: 0,
        knowledge_item_count: 1,
        included_in_archive: true,
      },
    },
  });

  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 2,
          entity_count: 11,
          event_count: 1,
          process_count: 1,
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
            included_in_archive: true,
          },
          {
            id: "doc-imported",
            title: "new-guide",
            file_type: "docx",
            source_archive: "manual_uploads",
            character_count: 900,
            entity_count: 1,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 1,
            included_in_archive: true,
          },
        ],
      });
    }

    if (url.endsWith("/documents/doc-imported")) {
      return Promise.resolve({
        data: {
          document: {
            id: "doc-imported",
            title: "new-guide",
            file_type: "docx",
            source_archive: "manual_uploads",
            character_count: 900,
            entity_count: 1,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 1,
            included_in_archive: true,
          },
          knowledge_items: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  const { container } = render(
    <MemoryRouter>
      <DocumentsPage />
    </MemoryRouter>,
  );

  const fileInput = container.querySelector('input[type="file"]');
  if (!(fileInput instanceof HTMLInputElement)) {
    throw new Error("file input not found");
  }

  const uploadFile = new File(["new guide"], "new-guide.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });

  fireEvent.change(fileInput, { target: { files: [uploadFile] } });
  fireEvent.click(await screen.findByRole("button", { name: "上传并纳入当前知识库" }));

  await waitFor(() => {
    expect(importArchiveDocumentMock).toHaveBeenCalledWith("20161116-nas", expect.any(File));
  });

  await waitFor(() => {
    expect(screen.getByText("已完成“new-guide”的上传并纳入当前知识库，当前知识库已完成增量重算。")).toBeInTheDocument();
  });
});

test("formalizes an archive document and shows incremental rebuild feedback", async () => {
  const formalizeController: { finish?: (value: unknown) => void } = {};
  formalizeArchiveDocumentMock.mockImplementation(
    () =>
      new Promise((resolve) => {
        formalizeController.finish = resolve as (value: unknown) => void;
      }),
  );

  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 2,
          entity_count: 10,
          event_count: 1,
          process_count: 1,
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
            included_in_archive: false,
          },
        ],
      });
    }

    if (url.endsWith("/documents/doc-1")) {
      return Promise.resolve({
        data: {
          document: {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 3,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 5,
          },
          knowledge_items: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter>
      <DocumentsPage />
    </MemoryRouter>,
  );

  const formalizeButton = await screen.findByRole("button", { name: "纳入当前知识库" });
  fireEvent.click(formalizeButton);

  await waitFor(() => {
    expect(formalizeArchiveDocumentMock).toHaveBeenCalledWith("20161116-nas", "doc-1");
    expect(formalizeButton).toBeDisabled();
  });

  const finishFormalize = formalizeController.finish;
  if (!finishFormalize) {
    throw new Error("formalize resolver missing");
  }
  finishFormalize({
    data: {
      archive_id: "20161116-nas",
      document_id: "doc-1",
      action: "include",
      mode: "incremental_merge",
      document_included: true,
      summary: {
        archive_id: "20161116-nas",
        document_count: 2,
        entity_count: 10,
        event_count: 1,
        process_count: 1,
      },
      document: {
        id: "doc-1",
        title: "NAS AV-1",
        file_type: "pdf",
        source_archive: "20161116 档案",
        character_count: 1200,
        entity_count: 3,
        event_count: 1,
        process_count: 1,
        knowledge_item_count: 5,
        included_in_archive: true,
      },
    },
  });

  await waitFor(() => {
    expect(screen.getByText("已完成“NAS AV-1”的单文档正式并入，当前知识库已重算。")).toBeInTheDocument();
  });
});

test("removes an included archive document and disables all archive toggle actions while pending", async () => {
  const removeController: { finish?: (value: unknown) => void } = {};
  removeArchiveDocumentMock.mockImplementation(
    () =>
      new Promise((resolve) => {
        removeController.finish = resolve as (value: unknown) => void;
      }),
  );

  getMock.mockImplementation((url: string) => {
    if (url.endsWith("/summary")) {
      return Promise.resolve({
        data: {
          archive_id: "20161116-nas",
          document_count: 2,
          entity_count: 10,
          event_count: 1,
          process_count: 1,
        },
      });
    }

    if (url.includes("/knowledge/archive/") && url.endsWith("/documents")) {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
            included_in_archive: true,
          },
          {
            id: "doc-2",
            title: "NAS Roadmap",
            file_type: "docx",
            source_archive: "20161116 路线图",
            character_count: 800,
            entity_count: 1,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 1,
            included_in_archive: false,
          },
        ],
      });
    }

    if (url.endsWith("/documents/doc-1")) {
      return Promise.resolve({
        data: {
          document: {
            id: "doc-1",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "20161116 档案",
            character_count: 1200,
            entity_count: 2,
            event_count: 1,
            process_count: 1,
            knowledge_item_count: 4,
            included_in_archive: false,
          },
          knowledge_items: [],
        },
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter>
      <DocumentsPage />
    </MemoryRouter>,
  );

  const removeButton = await screen.findByRole("button", { name: "从当前知识库移出" });
  const includeButton = await screen.findByRole("button", { name: "纳入当前知识库" });

  fireEvent.click(removeButton);

  await waitFor(() => {
    expect(removeArchiveDocumentMock).toHaveBeenCalledWith("20161116-nas", "doc-1");
    expect(includeButton).toBeDisabled();
    expect(screen.getByText("正在移出")).toBeInTheDocument();
  });

  const finishRemove = removeController.finish;
  if (!finishRemove) {
    throw new Error("remove resolver missing");
  }
  finishRemove({
    data: {
      archive_id: "20161116-nas",
      document_id: "doc-1",
      action: "remove",
      mode: "incremental_remove",
      document_included: false,
      summary: {
        archive_id: "20161116-nas",
        document_count: 1,
        entity_count: 8,
        event_count: 1,
        process_count: 1,
      },
      document: {
        id: "doc-1",
        title: "NAS AV-1",
        file_type: "pdf",
        source_archive: "20161116 档案",
        character_count: 1200,
        entity_count: 2,
        event_count: 1,
        process_count: 1,
        knowledge_item_count: 4,
        included_in_archive: false,
      },
    },
  });

  await waitFor(() => {
    expect(screen.getByText("已完成“NAS AV-1”的正式移出，当前知识库已重算。")).toBeInTheDocument();
  });
});
