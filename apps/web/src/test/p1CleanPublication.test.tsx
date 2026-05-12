import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { P1WorkspaceContext } from "../features/p1Clean/types";

const publicationApiMocks = vi.hoisted(() => ({
  getArchivePublication: vi.fn(),
  getPublicationCandidateSnapshot: vi.fn(),
}));

vi.mock("../features/p1Clean/modules/publication/api", () => ({
  publicationApi: publicationApiMocks,
}));

import { PublicationPage } from "../features/p1Clean/modules/publication/page";

function buildContext(): P1WorkspaceContext {
  return {
    archiveId: "kb-demo",
    archive: {
      archive_id: "kb-demo",
      name: "Demo KB",
      source_dir: "docs",
      extract_root: "out",
      is_active: true,
      status: "ready",
      last_built_at: null,
      last_error: null,
      summary: null,
      build_state: null,
      artifacts: { base_exists: true, curated_exists: false, publication_exists: false },
    },
    policyPackageVersionId: "PKGV-1",
    runtimeSnapshotId: "RS-P1-R0-001",
    documentSetId: "kb-demo:document-set",
    publicationSnapshotId: null,
  };
}

describe("P1 clean publication module", () => {
  it("loads candidate snapshot through the module adapter and renders candidate-only status", async () => {
    publicationApiMocks.getArchivePublication.mockResolvedValue({
      data: {
        archive_id: "kb-demo",
        current_version: null,
        versions: [],
        working_summary: { document_count: 1, entity_count: 2, event_count: 0, process_count: 0 },
        candidate_source: "publication_candidate_snapshot",
        candidate_scope: "post_quality_gate_publication_candidate",
        machine_publication_status: "candidate_available",
        machine_publication_label: "机器已发布候选",
        governance_confirmation_status: "waiting_confirmation",
        governance_confirmation_label: "等待治理确认",
        formal_entry_status: "not_admitted",
        formal_entry_label: "尚未正式入库",
        review_summary: { pending_count: 1, approved_count: 0, rejected_count: 0 },
      },
    });
    publicationApiMocks.getPublicationCandidateSnapshot.mockResolvedValue({
      contract_version: "p1.publication_candidate.r1",
      source_kind: "live",
      generated_at: "2026-05-08T10:00:00+08:00",
      data: {
        publication_candidate_snapshot_id: "PCS-kb-demo-RS-P1-R0-001",
        publication_snapshot_id: "PCS-kb-demo-RS-P1-R0-001",
        archive_id: "kb-demo",
        run_id: "RUN-P1-R0-001",
        runtime_snapshot_id: "RS-P1-R0-001",
        policy_package_version_id: "PKGV-1",
        resolution_snapshot_id: "RESOLVE-P1-R0-001",
        generated_at: "2026-05-08T10:00:00+08:00",
        status: "governance_pending",
        governance_status: "pending",
        candidate_summary: {
          publication_snapshot_id: "PCS-kb-demo-RS-P1-R0-001",
          status_label: "机器已发布候选",
          source_scope: "post_quality_gate_publication_candidate",
          generated_from_runtime_snapshot_id: "RS-P1-R0-001",
          candidate_count: 6,
          candidate_knowledge_count: 1,
        },
        quality_decision_summary: {
          decision: "warn_continue",
          output_action: "publish_candidate_with_warning",
          score: 0.88,
          explanation: "质量门禁允许机器发布候选，但候选仍需治理确认后才能正式入库。",
          affected_object_ids: ["K-24"],
          affected_relation_ids: ["R-11"],
        },
        quality_decision: {
          decision: "warn_continue",
          output_action: "publish_candidate_with_warning",
          score: 0.88,
          explanation: "质量门禁允许机器发布候选，但候选仍需治理确认后才能正式入库。",
          affected_object_ids: ["K-24"],
          affected_relation_ids: ["R-11"],
        },
        governance_projection: {
          governance_confirmation_status: "waiting_confirmation",
          governance_confirmation_label: "等待治理确认",
          formal_entry_status: "not_admitted",
          formal_entry_label: "尚未正式入库",
          confirmation_required: true,
        },
        candidate_objects: [
          {
            object_id: "CK-contract-amount",
            canonical_name: "合同总金额",
            object_type: "amount_clause",
            source_document_ids: ["doc-1"],
            source_candidate_ids: ["K-24"],
            evidence_refs: [{ artifact_id: "anchor-A-102", artifact_type: "source_anchor" }],
            confidence: 0.91,
            quality_status: "warning",
            governance_status: "pending",
            version: "candidate-v1",
            source_snapshot_id: "RESOLVE-P1-R0-001",
          },
        ],
        candidate_relations: [],
        candidate_knowledge_refs: [{ artifact_id: "publication-candidate", artifact_type: "canonical_knowledge_candidate" }],
        api_exposure_scope: {
          readonly_candidate_api_paths: ["/api/p1/candidates/knowledge/read"],
          readonly_formal_api_paths: [],
          index_names: ["candidate_kb_demo_knowledge"],
          exposure_mode: "candidate_preview_only",
          not_supply_reason: "候选快照尚未经过治理确认，禁止作为正式知识供应。",
        },
      },
      warnings: [],
    });

    render(<PublicationPage context={buildContext()} />);

    expect(await screen.findAllByText("机器已发布候选")).not.toHaveLength(0);
    expect(screen.getAllByText("等待治理确认")).not.toHaveLength(0);
    expect(screen.getAllByText("尚未正式入库")).not.toHaveLength(0);
    expect(screen.getAllByText("PCS-kb-demo-RS-P1-R0-001")).not.toHaveLength(0);
    expect(screen.getByText("合同总金额")).toBeTruthy();
    expect(screen.getByText("/api/p1/candidates/knowledge/read")).toBeTruthy();
    expect(screen.getByText("candidate_kb_demo_knowledge")).toBeTruthy();
    expect(publicationApiMocks.getPublicationCandidateSnapshot).toHaveBeenCalledWith("kb-demo", "RS-P1-R0-001", "PKGV-1");
  });
});
