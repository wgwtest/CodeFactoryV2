import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { KnowledgeResultsPage } from "../features/p1Clean/modules/knowledgeResults/page";
import type { P1WorkspaceContext } from "../features/p1Clean/types";

const apiMocks = vi.hoisted(() => ({
  getArchiveSummary: vi.fn(),
  getArchiveGraph: vi.fn(),
  getArchiveEntities: vi.fn(),
  getArchiveEvents: vi.fn(),
  getArchiveProcesses: vi.fn(),
  getArchivePublication: vi.fn(),
  getArchiveItemDetail: vi.fn(),
}));

vi.mock("../features/p1Clean/modules/knowledgeResults/api", () => ({
  knowledgeResultsApi: apiMocks,
}));

const context: P1WorkspaceContext = {
  archiveId: "kb",
  archive: {
    archive_id: "kb",
    name: "Knowledge Base",
    source_dir: "archive",
    extract_root: "extract",
    is_active: true,
    status: "ready",
    last_built_at: null,
    last_error: null,
    summary: null,
    build_state: null,
    artifacts: { base_exists: true, curated_exists: true, publication_exists: true },
  },
  policyPackageVersionId: "PKGV-1",
  runtimeSnapshotId: "RS-1",
  documentSetId: "kb:document-set",
  publicationSnapshotId: "kb:latest-publication",
};

describe("P1 clean knowledge results module", () => {
  it("loads final knowledge objects, relations, and evidence through its own adapter", async () => {
    apiMocks.getArchiveSummary.mockResolvedValue({
      data: { archive_id: "kb", document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
    });
    apiMocks.getArchiveGraph.mockResolvedValue({
      data: {
        archive_id: "kb",
        nodes: [{ id: "entity-1", label: "合同总金额", type: "amount", item_type: "entity", document_count: 1 }],
        edges: [{ source: "entity-1", label: "约束", target: "entity-2" }],
        summary: { archive_id: "kb", document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
      },
    });
    apiMocks.getArchiveEntities.mockResolvedValue({
      data: [
        {
          id: "entity-1",
          name: "合同总金额",
          category: "amount",
          aliases: ["总金额"],
          document_count: 1,
          interpretation: {
            kind_label: "实体",
            family_code: null,
            family_label: null,
            display_name: "合同总金额",
            standard_name: "合同总金额",
            summary: "合同中的总金额概念",
            producer_hint: null,
          },
        },
      ],
    });
    apiMocks.getArchiveEvents.mockResolvedValue({ data: [] });
    apiMocks.getArchiveProcesses.mockResolvedValue({ data: [] });
    apiMocks.getArchivePublication.mockResolvedValue({
      data: {
        archive_id: "kb",
        current_version: {
          version_label: "v1",
          publisher: "governance-confirmation",
          published_at: "2026-05-10T00:00:00+08:00",
          summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
        },
        versions: [],
        working_summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
      },
    });
    apiMocks.getArchiveItemDetail.mockResolvedValue({
      data: {
        id: "entity-1",
        name: "合同总金额",
        item_type: "entity",
        category: "amount",
        aliases: ["总金额"],
        review_status: "approved",
        document_count: 1,
        interpretation: {
          kind_label: "实体",
          family_code: null,
          family_label: null,
          display_name: "合同总金额",
          standard_name: "合同总金额",
          summary: "合同中的总金额概念",
          producer_hint: null,
        },
        language_projection: {
          display_name_zh: "合同总金额",
          display_name_en: null,
          acronym: null,
          aliases_zh: ["总金额"],
          aliases_en: [],
          description_zh: "合同中的总金额概念",
          evidence_summary_zh: "来源于合同正文",
          translation_status: "derived",
          translation_confidence: 0.92,
        },
        documents: [{ id: "doc-1", title: "合同.pdf", file_type: "pdf", source_archive: "archive" }],
        evidence: [{ document_id: "doc-1", document_title: "合同.pdf", excerpt: "合同总金额为一百万元。" }],
        related_items: [{ id: "entity-2", name: "付款条件", item_type: "entity", relation_type: "约束" }],
        relationship_sections: [],
      },
    });

    render(
      <MemoryRouter>
        <KnowledgeResultsPage context={context} />
      </MemoryRouter>,
    );

    expect(await screen.findByText("正式入库知识")).toBeInTheDocument();
    expect(screen.getByText("知识图谱")).toBeInTheDocument();
    expect(screen.getByText("默认语义聚合视图")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "看抽取过程" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "看质量图谱" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "看发布状态" })).not.toBeInTheDocument();
    expect(screen.getAllByText("合同总金额").length).toBeGreaterThan(0);
    expect(screen.getAllByText("合同中的总金额概念").length).toBeGreaterThan(0);
    expect(await screen.findByText("来源文档")).toBeInTheDocument();
    expect((await screen.findAllByText("合同.pdf")).length).toBeGreaterThan(0);
    expect(await screen.findByText("1 条摘录 / 1 个来源")).toBeInTheDocument();
    expect(await screen.findByText("合同总金额为一百万元。")).toBeInTheDocument();

    await waitFor(() => {
      expect(apiMocks.getArchiveItemDetail).toHaveBeenCalledWith("entity-1", "kb");
    });
  });
});
