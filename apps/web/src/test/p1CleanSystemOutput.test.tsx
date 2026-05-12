import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SystemOutputPage } from "../features/p1Clean/modules/systemOutput/page";
import type { P1WorkspaceContext } from "../features/p1Clean/types";

const apiMocks = vi.hoisted(() => ({
  getArchiveSummary: vi.fn(),
  getArchiveGraph: vi.fn(),
  getArchivePublication: vi.fn(),
  getPublicationCandidateSnapshot: vi.fn(),
  getSystemOutputContract: vi.fn(),
}));

vi.mock("../features/p1Clean/modules/systemOutput/api", () => ({
  systemOutputApi: apiMocks,
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
  policyPackageVersionId: null,
  runtimeSnapshotId: null,
  documentSetId: null,
  publicationSnapshotId: "kb:latest-publication",
};

describe("P1 clean system output page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the formal output contract through the module adapter", async () => {
    apiMocks.getArchivePublication.mockResolvedValue({
      data: {
        archive_id: "kb",
        current_version: {
          version_label: "v1",
          publisher: "governance-confirmation",
          published_at: "2026-05-10T00:00:00+00:00",
          summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
        },
        versions: [],
        working_summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
      },
    });
    apiMocks.getSystemOutputContract.mockResolvedValue({
      data: {
        contract_version: "p1.system_output.preview.r1",
        source_kind: "live",
        generated_at: "2026-05-10T00:00:01+00:00",
        data: {
          contract_version: "P1CleanSystemOutputContract.v1",
          archive_id: "kb",
          publication_snapshot_id: "kb:latest-publication",
          canonical_publication_snapshot_id: "kb:v1",
          formal_version: "v1",
          formal_version_id: "kb:v1",
          governed_by: "governance-confirmation",
          published_at: "2026-05-10T00:00:00+00:00",
          generated_at: "2026-05-10T00:00:01+00:00",
          source_kind: "governed_publication_snapshot",
          is_formalized: true,
          supply_available: true,
          unavailable_reason: null,
          boundary: "formal output only",
          source_summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
          formal_interfaces: [
            {
              method: "GET",
              path: "/api/knowledge/archive/kb/summary",
              purpose: "Read formal summary",
              source: "formal_publication_snapshot",
              requires_publication_snapshot_id: true,
            },
          ],
          version_selection_rules: [
            {
              rule_id: "current-governed-publication",
              description: "Use current governed publication.",
              selected_publication_snapshot_id: "kb:v1",
              selected_version_label: "v1",
              governance_boundary: "post_publication_confirmation",
            },
          ],
          api_exposure_scope: {
            exposure_mode: "formal_only",
            formal_api_paths: ["/api/knowledge/archive/kb/summary"],
            candidate_api_paths: [],
            blocked_candidate_sources: ["publication_candidate_snapshot"],
          },
          readable_objects: [
            {
              object_id: "entity-approved",
              name: "Approved formal entity",
              item_type: "entity",
              category: "system_or_service",
              document_count: 1,
              evidence_count: 1,
              version_id: "kb:v1",
            },
          ],
          readable_relations: [],
          readable_evidence: [
            {
              evidence_id: "entity-approved::evidence::1",
              object_id: "entity-approved",
              document_id: "doc-1",
              excerpt: "Approved evidence",
              version_id: "kb:v1",
            },
          ],
          adapter_contract: {
            adapter_name: "P1CleanSystemOutputAdapter",
            contract_version: "P1CleanSystemOutputContract.v1",
            input_keys: ["archiveId", "publicationSnapshotId"],
            output_keys: ["formalInterfaces"],
            allowed_backend_calls: ["getArchiveSummary", "getArchiveGraph", "getArchivePublication"],
            forbidden_sources: ["runtime_temporary_nodes", "publication_candidate_snapshot"],
          },
          downstream_consumers: [
            { consumer: "P2", read_pattern: "Bind formal ids.", notes: ["No candidate API."] },
            { consumer: "P3", read_pattern: "Read formal graph.", notes: ["Read only."] },
          ],
        },
        warnings: [],
      },
    });

    render(<SystemOutputPage context={context} />);

    expect(await screen.findByText("正式知识输出合同已就绪")).toBeInTheDocument();
    expect(screen.getByText("P1CleanSystemOutputAdapter")).toBeInTheDocument();
    expect(screen.getByText("runtime_temporary_nodes")).toBeInTheDocument();
    expect(screen.getByText("Approved formal entity")).toBeInTheDocument();
    expect(screen.getByText("Approved evidence")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
    expect(screen.getByText("P3")).toBeInTheDocument();
    await waitFor(() => {
      expect(apiMocks.getSystemOutputContract).toHaveBeenCalledWith("kb", "kb:latest-publication");
    });
  });

  it("shows an unavailable reason when only a publication candidate exists", async () => {
    const candidateOnlyContext: P1WorkspaceContext = {
      ...context,
      publicationSnapshotId: null,
      runtimeSnapshotId: "RS-P1-R0-001",
      policyPackageVersionId: "PKGV-1",
      archive: {
        ...context.archive,
        artifacts: { base_exists: true, curated_exists: true, publication_exists: false },
      },
    };

    apiMocks.getArchivePublication.mockResolvedValue({
      data: {
        archive_id: "kb",
        current_version: null,
        versions: [],
        working_summary: { document_count: 1, entity_count: 1, event_count: 0, process_count: 0 },
      },
    });
    apiMocks.getPublicationCandidateSnapshot.mockResolvedValue({
      data: {
        contract_version: "p1.publication_candidate.r1",
        source_kind: "live",
        generated_at: "2026-05-10T00:00:00+00:00",
        data: {
          publication_candidate_snapshot_id: "PCS-kb-RS-P1-R0-001",
          publication_snapshot_id: "PCS-kb-RS-P1-R0-001",
          archive_id: "kb",
          run_id: "RUN-P1-R0-001",
          generated_at: "2026-05-10T00:00:00+00:00",
          status: "governance_pending",
          governance_status: "pending",
          candidate_knowledge_refs: [],
          api_exposure_scope: {
            readonly_candidate_api_paths: ["/api/p1/candidates/knowledge/read"],
            readonly_formal_api_paths: [],
            index_names: [],
            exposure_mode: "candidate_preview_only",
            not_supply_reason: "候选快照尚未经过治理确认，禁止作为正式知识供应。",
          },
        },
        warnings: [],
      },
    });
    apiMocks.getSystemOutputContract.mockResolvedValue({
      data: {
        contract_version: "p1.system_output.preview.r1",
        source_kind: "live",
        generated_at: "2026-05-10T00:00:01+00:00",
        data: {
          contract_version: "P1CleanSystemOutputContract.v1",
          archive_id: "kb",
          publication_snapshot_id: "PCS-kb-RS-P1-R0-001",
          canonical_publication_snapshot_id: null,
          formal_version: null,
          formal_version_id: null,
          governed_by: null,
          published_at: null,
          generated_at: "2026-05-10T00:00:01+00:00",
          source_kind: "governed_publication_snapshot",
          is_formalized: false,
          supply_available: false,
          unavailable_reason: "No governed publication snapshot is available for formal system output",
          boundary: "formal only",
          source_summary: { document_count: 0, entity_count: 0, event_count: 0, process_count: 0 },
          formal_interfaces: [],
          version_selection_rules: [
            {
              rule_id: "reject-unconfirmed-publication-candidate",
              description: "候选发布快照必须经过治理确认并生成正式版本后，才能进入系统间输出。",
              selected_publication_snapshot_id: "PCS-kb-RS-P1-R0-001",
              selected_version_label: "not-formalized",
              governance_boundary: "post_publication_confirmation",
            },
          ],
          api_exposure_scope: {
            exposure_mode: "not_available",
            formal_api_paths: [],
            candidate_api_paths: ["/api/p1/candidates/knowledge/read"],
            blocked_candidate_sources: ["publication_candidate_snapshot", "unconfirmed_candidate_knowledge"],
            not_supply_reason: "No governed publication snapshot is available for formal system output",
          },
          readable_objects: [],
          readable_relations: [],
          readable_evidence: [],
          adapter_contract: {
            adapter_name: "P1CleanSystemOutputAdapter",
            contract_version: "P1CleanSystemOutputContract.v1",
            input_keys: ["archiveId", "publicationSnapshotId"],
            output_keys: ["supplyAvailable"],
            allowed_backend_calls: ["getP1CleanSystemOutputContract"],
            forbidden_sources: ["runtime_temporary_nodes", "publication_candidate_snapshot"],
          },
          downstream_consumers: [
            { consumer: "P2", read_pattern: "Do not hydrate requirements.", notes: ["Wait for formal."] },
            { consumer: "P3", read_pattern: "Do not consume graph data.", notes: ["Wait for formal."] },
          ],
        },
        warnings: ["系统间输出未开放：当前快照仍处于候选或未正式入库状态。"],
      },
    });

    render(<SystemOutputPage context={candidateOnlyContext} />);

    expect(await screen.findByText("正式知识不可供应")).toBeInTheDocument();
    expect(screen.getAllByText("PCS-kb-RS-P1-R0-001")).not.toHaveLength(0);
    expect(screen.getAllByText("No governed publication snapshot is available for formal system output")).not.toHaveLength(0);
    expect(screen.getByText("not_available")).toBeInTheDocument();
    await waitFor(() => {
      expect(apiMocks.getPublicationCandidateSnapshot).toHaveBeenCalledWith("kb", "RS-P1-R0-001", "PKGV-1");
      expect(apiMocks.getSystemOutputContract).toHaveBeenCalledWith("kb", "PCS-kb-RS-P1-R0-001");
    });
  });
});
