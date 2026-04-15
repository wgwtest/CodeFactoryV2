import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { ArchiveManagementPage } from "../pages/ArchiveManagementPage";

const refreshArchivesMock = vi.fn();
const setActiveArchiveIdMock = vi.fn();
const createKnowledgeArchiveMock = vi.fn();
const extractKnowledgeArchiveMock = vi.fn();

vi.mock("../context/ArchiveContext", () => ({
  useArchiveContext: () => ({
    activeArchiveId: "kb-1",
    activeArchive: { archive_id: "kb-1", name: "知识库一" },
    archives: [
      {
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
      },
      {
        archive_id: "kb-2",
        name: "知识库二",
        source_dir: "/tmp/kb-2",
        extract_root: "/tmp/extract/kb-2",
        is_active: false,
        status: "empty",
        last_built_at: null,
        last_error: null,
        summary: null,
        artifacts: { base_exists: false, curated_exists: false, publication_exists: false },
      },
    ],
    error: null,
    loading: false,
    refreshArchives: refreshArchivesMock,
    setActiveArchiveId: setActiveArchiveIdMock,
  }),
}));

vi.mock("../lib/archives", () => ({
  createKnowledgeArchive: (...args: unknown[]) => createKnowledgeArchiveMock(...args),
  extractKnowledgeArchive: (...args: unknown[]) => extractKnowledgeArchiveMock(...args),
}));

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
