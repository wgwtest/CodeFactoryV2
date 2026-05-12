import { describe, expect, it } from "vitest";

import { buildWorkspaceContext } from "../features/p1Clean/P1CleanApp";
import { p1ModuleTestEntries } from "../features/p1Clean/modules/testEntries";
import { p1WorkspaceModules } from "../features/p1Clean/registry";
import type { KnowledgeArchive } from "../lib/api";

function buildArchive(overrides: Partial<KnowledgeArchive> = {}): KnowledgeArchive {
  return {
    archive_id: "midterm-kb",
    name: "Mid Term 知识库",
    source_dir: "E:/sample/Mid Term",
    extract_root: "E:/sample/.extract/midterm-kb",
    is_active: true,
    status: "empty",
    last_built_at: null,
    last_error: null,
    summary: null,
    build_state: null,
    artifacts: {
      base_exists: false,
      curated_exists: false,
      publication_exists: false,
    },
    ...overrides,
  };
}

describe("p1 clean module registry", () => {
  it("keeps workspace modules route-driven and uniquely registered", () => {
    const routes = p1WorkspaceModules.map((module) => module.route);
    const ids = p1WorkspaceModules.map((module) => module.id);

    expect(new Set(routes).size).toBe(routes.length);
    expect(new Set(ids).size).toBe(ids.length);
    expect(routes).toEqual(["intake", "policy", "runtime", "quality", "results", "publication", "system-output"]);
  });

  it("keeps every module paired with a test entry", () => {
    const workspaceModuleIds = p1WorkspaceModules.map((module) => module.id);
    const testEntryIds = p1ModuleTestEntries.map((entry) => entry.moduleId);

    expect(testEntryIds).toEqual([
      "knowledgeBaseManagement",
      "intake",
      "policyRules",
      "runtime",
      "qualityGraph",
      "knowledgeResults",
      "publication",
      "systemOutput",
    ]);
    expect(testEntryIds).toEqual(expect.arrayContaining(workspaceModuleIds));
  });

  it("declares context contracts instead of implicit cross-module reads", () => {
    for (const module of p1WorkspaceModules) {
      expect(module.contract.inputs).toContain("archiveId");
      expect(module.contract.owns.length).toBeGreaterThan(0);
      expect(module.contract.consumes.length).toBeGreaterThan(0);
    }
  });

  it("derives workspace context from the policy config before runtime build state exists", () => {
    const context = buildWorkspaceContext(
      "midterm-kb",
      buildArchive(),
      "midterm-kb:architecture_midterm_default:policy:v1",
    );

    expect(context.documentSetId).toBe("midterm-kb:document-set");
    expect(context.policyPackageVersionId).toBe("midterm-kb:architecture_midterm_default:policy:v1");
    expect(context.runtimeSnapshotId).toBeNull();
  });

  it("keeps runtime policy snapshots authoritative after extraction starts", () => {
    const context = buildWorkspaceContext(
      "midterm-kb",
      buildArchive({
        build_state: {
          archive_id: "midterm-kb",
          archive_name: "Mid Term 知识库",
          mode: "formal",
          status: "running",
          started_at: null,
          updated_at: null,
          expected_document_count: 8,
          completed_document_ids: [],
          pending_document_ids: [],
          failed_document_id: null,
          failed_message: null,
          current_document_id: null,
          current_document_title: null,
          current_document_path: null,
          current_chunk: null,
          policy_snapshot: {
            snapshot_id: "policy-snapshot-1",
            run_id: "RUN-policy-snapshot-1",
            archive_id: "midterm-kb",
            policy_package_version_id: "midterm-kb:policy:v2",
            version_label: "Mid Term v2",
            scope_label: "Mid Term",
            captured_at: "2026-05-11T00:00:00+00:00",
            ai_autoadapt_enabled: true,
            config_updated_at: null,
            stage_order: [],
            stages: [],
          },
          documents: [],
        },
      }),
      "midterm-kb:policy:v1",
    );

    expect(context.policyPackageVersionId).toBe("midterm-kb:policy:v2");
    expect(context.runtimeSnapshotId).toBe("RUN-policy-snapshot-1");
  });
});
