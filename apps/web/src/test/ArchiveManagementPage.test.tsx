import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { ArchiveManagementPage } from "../pages/ArchiveManagementPage";
import type { KnowledgeArchive } from "../lib/api";

const refreshArchivesMock = vi.fn();
const setActiveArchiveIdMock = vi.fn();
const createKnowledgeArchiveMock = vi.fn();
const extractKnowledgeArchiveMock = vi.fn();

function buildArchive(overrides: Partial<KnowledgeArchive> = {}): KnowledgeArchive {
  return {
    archive_id: "kb-1",
    name: "知识库一",
    source_dir: "/tmp/kb-1",
    extract_root: "/tmp/extract/kb-1",
    is_active: true,
    status: "ready",
    last_built_at: null,
    last_error: null,
    summary: { archive_id: "kb-1", document_count: 1, entity_count: 2, event_count: 0, process_count: 0 },
    artifacts: { base_exists: true, curated_exists: false, publication_exists: false },
    build_state: null,
    ...overrides,
  };
}

const archiveContextValue: {
  activeArchiveId: string | null;
  activeArchive: KnowledgeArchive | null;
  archives: KnowledgeArchive[];
  error: string | null;
  loading: boolean;
  refreshArchives: typeof refreshArchivesMock;
  setActiveArchiveId: typeof setActiveArchiveIdMock;
} = {
  activeArchiveId: "kb-1",
  activeArchive: buildArchive(),
  archives: [
    buildArchive(),
    buildArchive({
      archive_id: "kb-2",
      name: "知识库二",
      source_dir: "/tmp/kb-2",
      extract_root: "/tmp/extract/kb-2",
      is_active: false,
      status: "empty",
      summary: null,
      artifacts: { base_exists: false, curated_exists: false, publication_exists: false },
    }),
  ],
  error: null,
  loading: false,
  refreshArchives: refreshArchivesMock,
  setActiveArchiveId: setActiveArchiveIdMock,
};

vi.mock("../context/ArchiveContext", () => ({
  useArchiveContext: () => archiveContextValue,
}));

vi.mock("../lib/archives", () => ({
  createKnowledgeArchive: (...args: unknown[]) => createKnowledgeArchiveMock(...args),
  extractKnowledgeArchive: (...args: unknown[]) => extractKnowledgeArchiveMock(...args),
}));

beforeEach(() => {
  archiveContextValue.activeArchiveId = "kb-1";
  archiveContextValue.activeArchive = buildArchive();
  archiveContextValue.archives = [
    buildArchive(),
    buildArchive({
      archive_id: "kb-2",
      name: "知识库二",
      source_dir: "/tmp/kb-2",
      extract_root: "/tmp/extract/kb-2",
      is_active: false,
      status: "empty",
      summary: null,
      artifacts: { base_exists: false, curated_exists: false, publication_exists: false },
    }),
  ];
  archiveContextValue.error = null;
  archiveContextValue.loading = false;
  refreshArchivesMock.mockReset();
  setActiveArchiveIdMock.mockReset();
  createKnowledgeArchiveMock.mockReset();
  extractKnowledgeArchiveMock.mockReset();
});

test("disables other archive actions while one extraction is running", async () => {
  const extractionController: { release: null | (() => void) } = { release: null };
  extractKnowledgeArchiveMock.mockImplementation(
    () =>
      new Promise<void>((resolve) => {
        extractionController.release = resolve;
      }),
  );

  render(<ArchiveManagementPage />);

  const extractButtons = await screen.findAllByRole("button", { name: "立即抽取" });
  const switchButton = screen.getByRole("button", { name: "设为当前" });

  fireEvent.click(extractButtons[0]);

  await waitFor(() => {
    expect(screen.getByText("正在抽取“知识库一”，期间已禁止重复提交和并发抽取。")).toBeInTheDocument();
    expect(extractButtons[1]).toBeDisabled();
    expect(switchButton).toBeDisabled();
  });

  if (typeof extractionController.release === "function") {
    extractionController.release();
  }

  await waitFor(() => {
    expect(refreshArchivesMock).toHaveBeenCalled();
  });
});

test("renders archive creation form and extraction logic explanation side by side", async () => {
  render(<ArchiveManagementPage />);

  expect(await screen.findByTestId("workspace-overview-strip")).toBeInTheDocument();
  expect(screen.getByText("知识库运行总览")).toBeInTheDocument();
  expect(await screen.findByText("新增知识库")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "创建知识库" })).toBeInTheDocument();
  expect(screen.getByText("正式抽取逻辑")).toBeInTheDocument();
  expect(screen.getByText("结构化分块 -> 分块抽取 -> 全局归并 -> 治理/发布")).toBeInTheDocument();
  expect(screen.getByText("原始候选")).toBeInTheDocument();
  expect(screen.getByText("治理工作态")).toBeInTheDocument();
  expect(screen.getByText("发布态")).toBeInTheDocument();
  expect(screen.getByText("当前仍属于受限模式")).toBeInTheDocument();
});

test("renders archive extraction progress for the active extracting archive", async () => {
  archiveContextValue.archives = [
    buildArchive({
      status: "extracting",
      summary: { archive_id: "kb-1", document_count: 3, entity_count: 2, event_count: 0, process_count: 1 },
      build_state: {
        archive_id: "kb-1",
        archive_name: "知识库一",
        mode: "formal",
        status: "running",
        updated_at: "2026-04-16T13:39:38.694577+00:00",
        started_at: "2026-04-16T13:34:38.694577+00:00",
        expected_document_count: 3,
        completed_document_ids: ["doc-1"],
        pending_document_ids: ["doc-3"],
        failed_document_id: null,
        failed_message: null,
        current_document_id: "doc-2",
        current_document_title: "FM 6-0",
        current_document_path: "FM_6-0.pdf",
        current_chunk: {
          chunk_id: "chunk-007",
          position: 7,
          total: 19,
          heading: "Command and staff relationships",
          char_count: 4321,
          segment_count: 8,
          retry_depth: 1,
        },
        documents: [
          { document_id: "doc-1", path: "ADRP.pdf", title: "ADRP", file_type: "pdf", source_archive: "kb", state: "completed" },
          { document_id: "doc-2", path: "FM_6-0.pdf", title: "FM 6-0", file_type: "pdf", source_archive: "kb", state: "running" },
          { document_id: "doc-3", path: "MIL-STD.pdf", title: "MIL-STD", file_type: "pdf", source_archive: "kb", state: "pending" },
        ],
      },
    }),
  ];
  archiveContextValue.activeArchive = archiveContextValue.archives[0];

  render(<ArchiveManagementPage />);

  expect(await screen.findByText("抽取进度")).toBeInTheDocument();
  expect(screen.getByText("当前处理文档")).toBeInTheDocument();
  expect(screen.getAllByText("FM 6-0").length).toBeGreaterThan(0);
  expect(screen.getByText("已完成 1 / 3")).toBeInTheDocument();
  expect(screen.getByText("当前块")).toBeInTheDocument();
  expect(screen.getByText("7 / 19")).toBeInTheDocument();
  expect(screen.getByText("Command and staff relationships")).toBeInTheDocument();
  expect(screen.getByText("重试深度 1")).toBeInTheDocument();
  expect(screen.getAllByText("进行中").length).toBeGreaterThan(0);
});

test("uses compact active action label and aligned action button widths", async () => {
  render(<ArchiveManagementPage />);

  const activeButton = await screen.findByRole("button", { name: "当前在用" });
  const switchButton = screen.getByRole("button", { name: "设为当前" });
  const extractButtons = screen.getAllByRole("button", { name: "立即抽取" });

  expect(activeButton).toHaveStyle({ minWidth: "96px" });
  expect(switchButton).toHaveStyle({ minWidth: "96px" });
  expect(extractButtons[0]).toHaveStyle({ minWidth: "96px" });
});
