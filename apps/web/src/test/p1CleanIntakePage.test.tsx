import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { IntakePage } from "../features/p1Clean/modules/intake/page";
import type { P1WorkspaceContext } from "../features/p1Clean/types";

const getArchiveDocumentsMock = vi.fn();
const getIntakeSnapshotMock = vi.fn();
const importArchiveDocumentMock = vi.fn();
const extractKnowledgeArchiveMock = vi.fn();
const refreshArchivesMock = vi.fn();

vi.mock("../features/p1Clean/modules/intake/api", () => ({
  getArchiveDocuments: (...args: unknown[]) => getArchiveDocumentsMock(...args),
  getIntakeSnapshot: (...args: unknown[]) => getIntakeSnapshotMock(...args),
  importArchiveDocument: (...args: unknown[]) => importArchiveDocumentMock(...args),
  extractKnowledgeArchive: (...args: unknown[]) => extractKnowledgeArchiveMock(...args),
}));

vi.mock("../context/ArchiveContext", () => ({
  useArchiveContext: () => ({
    refreshArchives: refreshArchivesMock,
  }),
}));

beforeEach(() => {
  getArchiveDocumentsMock.mockReset();
  getIntakeSnapshotMock.mockReset();
  importArchiveDocumentMock.mockReset();
  extractKnowledgeArchiveMock.mockReset();
  refreshArchivesMock.mockReset();
});

function buildContext(): P1WorkspaceContext {
  return {
    archiveId: "archive-a",
    archive: {
      archive_id: "archive-a",
      name: "领域 A 知识库",
      source_dir: "E:/data/archive-a",
      extract_root: "E:/data/archive-a-extract",
      is_active: true,
      status: "ready",
      last_built_at: null,
      last_error: null,
      summary: {
        archive_id: "archive-a",
        document_count: 2,
        entity_count: 3,
        event_count: 1,
        process_count: 0,
      },
      build_state: {
        archive_id: "archive-a",
        archive_name: "领域 A 知识库",
        mode: "formal",
        status: "completed",
        started_at: null,
        updated_at: "2026-05-10T00:00:00Z",
        expected_document_count: 2,
        completed_document_ids: ["doc-1"],
        pending_document_ids: [],
        failed_document_id: null,
        failed_message: null,
        current_document_id: null,
        current_document_title: null,
        current_document_path: null,
        current_chunk: null,
        warning_count: 0,
        warnings: [],
        documents: [
          {
            document_id: "doc-1",
            path: "NAS AV-1.pdf",
            title: "NAS AV-1",
            file_type: "pdf",
            source_archive: "领域 A 原始资料",
            state: "completed",
          },
        ],
      },
      artifacts: {
        base_exists: true,
        curated_exists: true,
        publication_exists: false,
      },
    },
    policyPackageVersionId: "policy-v1",
    runtimeSnapshotId: null,
    documentSetId: null,
    publicationSnapshotId: null,
  };
}

test("renders intake contract from archive documents", async () => {
  getIntakeSnapshotMock.mockResolvedValue({
    data: {
      contract_version: "p1.intake.r1",
      source_kind: "live",
      generated_at: "2026-05-10T00:00:00Z",
      warnings: [],
      data: {
        archive_id: "archive-a",
        document_set_id: "archive-a:document-set",
        source_dir: "E:/data/archive-a",
        policy_package_version_id: "policy-v1",
        documents: [
          {
            document_id: "doc-1",
            title: "NAS AV-1",
            file_name: "NAS AV-1.pdf",
            file_type: "pdf",
            source_path: "E:/data/archive-a/NAS AV-1.pdf",
            parse_status: "completed",
            parse_error: null,
            segment_count: 12,
            anchor_count: 3,
            can_enter_runtime: true,
          },
          {
            document_id: "doc-2",
            title: "NAS Roadmap",
            file_name: "NAS Roadmap.docx",
            file_type: "docx",
            source_path: "E:/data/archive-a/NAS Roadmap.docx",
            parse_status: "completed",
            parse_error: null,
            segment_count: 9,
            anchor_count: 1,
            can_enter_runtime: true,
          },
        ],
        summary: {
          document_count: 2,
          parsed_completed_count: 2,
          parsed_failed_count: 0,
          pending_count: 0,
          can_enter_runtime_count: 2,
          blocked_count: 0,
        },
        preflight_issues: [],
      },
    },
  });

  render(<IntakePage context={buildContext()} />);

  expect(await screen.findByText("NAS AV-1")).toBeInTheDocument();
  expect(screen.getByText("NAS Roadmap")).toBeInTheDocument();
  expect(screen.getByText("documentSetId：archive-a:document-set")).toBeInTheDocument();
  expect(screen.getByText("格式可用性：可用")).toBeInTheDocument();
  expect(screen.getByText("结构可用性：可用")).toBeInTheDocument();
  expect(screen.getByText("抽取运行：可进入")).toBeInTheDocument();
  expect(getIntakeSnapshotMock).toHaveBeenCalledWith("archive-a");
});

test("surfaces skipped document reason and blocks misleading extraction action", async () => {
  const context = buildContext();
  context.archive.build_state!.warning_count = 1;
  context.archive.build_state!.warnings = [
    {
      code: "docling_docx_skipped",
      severity: "warning",
      file_path: "E:/data/archive-a/SV-2翻译.docx",
      file_type: "docx",
      message: "Docling failed",
      reason: "正式知识库抽取要求 DOC/DOCX 使用 Docling 解析，但当前文件未能通过 Docling 成功解析。",
    },
  ];

  getIntakeSnapshotMock.mockResolvedValue({
    data: {
      contract_version: "p1.intake.r1",
      source_kind: "live",
      generated_at: "2026-05-10T00:00:00Z",
      warnings: [],
      data: {
        archive_id: "archive-a",
        document_set_id: "archive-a:document-set",
        source_dir: "E:/data/archive-a",
        policy_package_version_id: "policy-v1",
        documents: [
          {
            document_id: "doc-1",
            title: "NAS AV-1",
            file_name: "NAS AV-1.pdf",
            file_type: "pdf",
            source_path: "E:/data/archive-a/NAS AV-1.pdf",
            parse_status: "completed",
            parse_error: null,
            segment_count: 12,
            anchor_count: 3,
            can_enter_runtime: true,
          },
          {
            document_id: "doc-2",
            title: "NAS Roadmap",
            file_name: "NAS Roadmap.docx",
            file_type: "docx",
            source_path: "E:/data/archive-a/NAS Roadmap.docx",
            parse_status: "completed",
            parse_error: null,
            segment_count: 9,
            anchor_count: 1,
            can_enter_runtime: true,
          },
          {
            document_id: "doc-3",
            title: "SV-2翻译",
            file_name: "SV-2翻译.docx",
            file_type: "docx",
            source_path: "E:/data/archive-a/SV-2翻译.docx",
            parse_status: "skipped",
            parse_error: "该文档未纳入当前知识库集合。",
            segment_count: 0,
            anchor_count: 0,
            can_enter_runtime: false,
          },
        ],
        summary: {
          document_count: 3,
          parsed_completed_count: 2,
          parsed_failed_count: 0,
          pending_count: 0,
          can_enter_runtime_count: 2,
          blocked_count: 1,
        },
        preflight_issues: [],
      },
    },
  });

  render(<IntakePage context={context} />);

  expect(await screen.findByText(/预检未通过：3 份资料中 2 份可进入运行，1 份已跳过，1 份阻断/)).toBeInTheDocument();
  expect(screen.getAllByText("已跳过").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/正式知识库抽取要求 DOC\/DOCX 使用 Docling 解析/).length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "预检未通过" })).toBeDisabled();
  expect(extractKnowledgeArchiveMock).not.toHaveBeenCalled();
});
