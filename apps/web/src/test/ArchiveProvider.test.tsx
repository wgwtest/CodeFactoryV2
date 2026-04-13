import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import { ArchiveProvider } from "../context/ArchiveContext";
import { DocumentsPage } from "../pages/DocumentsPage";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  localStorage.clear();
  getMock.mockReset();
  postMock.mockReset();
});

test("documents page uses the selected archive instead of the hard-coded default", async () => {
  localStorage.setItem("code-factory.activeArchiveId", "domain-b");

  getMock.mockImplementation((url: string) => {
    if (url === "/archives") {
      return Promise.resolve({
        data: [
          {
            archive_id: "20161116-nas",
            name: "默认 NAS 知识库",
            source_dir: "/tmp/legacy",
            extract_root: "/tmp/legacy-extract",
            is_active: false,
            status: "ready",
            last_built_at: null,
            last_error: null,
            summary: {
              document_count: 1,
              entity_count: 1,
              event_count: 0,
              process_count: 0,
            },
            artifacts: {
              base_exists: true,
              curated_exists: false,
              publication_exists: false,
            },
          },
          {
            archive_id: "domain-b",
            name: "领域 B 知识库",
            source_dir: "/tmp/domain-b",
            extract_root: "/tmp/domain-b-extract",
            is_active: true,
            status: "ready",
            last_built_at: "2026-04-14T10:00:00Z",
            last_error: null,
            summary: {
              document_count: 1,
              entity_count: 2,
              event_count: 0,
              process_count: 0,
            },
            artifacts: {
              base_exists: true,
              curated_exists: false,
              publication_exists: false,
            },
          },
        ],
      });
    }

    if (url === "/documents") {
      return Promise.resolve({ data: [] });
    }

    if (url === "/knowledge/archive/domain-b/summary") {
      return Promise.resolve({
        data: {
          archive_id: "domain-b",
          document_count: 1,
          entity_count: 2,
          event_count: 0,
          process_count: 0,
        },
      });
    }

    if (url === "/knowledge/archive/domain-b/documents") {
      return Promise.resolve({
        data: [
          {
            id: "doc-1",
            title: "领域 B 指南",
            file_type: "docx",
            source_archive: "领域 B 原始资料",
            character_count: 2048,
            entity_count: 2,
            event_count: 0,
            process_count: 0,
            knowledge_item_count: 2,
          },
        ],
      });
    }

    throw new Error(`unexpected url: ${url}`);
  });

  render(
    <MemoryRouter>
      <ArchiveProvider>
        <DocumentsPage />
      </ArchiveProvider>
    </MemoryRouter>,
  );

  expect(await screen.findByText("领域 B 指南")).toBeInTheDocument();
  expect(getMock).toHaveBeenCalledWith("/archives");
  expect(getMock).toHaveBeenCalledWith("/knowledge/archive/domain-b/summary");
  expect(getMock).toHaveBeenCalledWith("/knowledge/archive/domain-b/documents");
  expect(getMock).not.toHaveBeenCalledWith("/knowledge/archive/20161116-nas/summary");
});
