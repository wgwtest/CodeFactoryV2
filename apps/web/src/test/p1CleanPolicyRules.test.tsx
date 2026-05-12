import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { P1_POLICY_CONFIG_UPDATED_EVENT } from "../features/p1Clean/events";
import { PolicyRulesPage } from "../features/p1Clean/modules/policyRules/page";
import type { PolicyRulesConfig } from "../features/p1Clean/modules/policyRules/types";
import type { ArchiveIncrementalRebuildTask, KnowledgeArchive } from "../lib/api";

const getArchivePolicyConfigMock = vi.fn();
const updateArchivePolicyConfigMock = vi.fn();
const listArchiveIncrementalRebuildTasksMock = vi.fn();
const refreshArchivesMock = vi.fn();

vi.mock("../features/p1Clean/modules/policyRules/api", () => ({
  policyRulesApi: {
    getArchivePolicyConfig: (...args: unknown[]) => getArchivePolicyConfigMock(...args),
    updateArchivePolicyConfig: (...args: unknown[]) => updateArchivePolicyConfigMock(...args),
    listArchiveIncrementalRebuildTasks: (...args: unknown[]) => listArchiveIncrementalRebuildTasksMock(...args),
  },
}));

vi.mock("../context/ArchiveContext", () => ({
  useArchiveContext: () => ({
    refreshArchives: refreshArchivesMock,
  }),
}));

function buildArchive(): KnowledgeArchive {
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
    build_state: null,
    artifacts: { base_exists: true, curated_exists: false, publication_exists: false },
  };
}

function buildPolicyConfig(overrides: Partial<PolicyRulesConfig> = {}): PolicyRulesConfig {
  return {
    archive_id: "kb-1",
    policy_contract_version: "p1.policy_contract.v1",
    policy_package_id: "architecture_midterm_default",
    policy_package_name: "Mid Term 体系结构默认策略包",
    policy_package_version_id: "kb-1:architecture_midterm_default:policy:v1",
    policy_package_version_status: "published",
    policy_package_version_hash: "sha256:policyhash0001",
    policy_package_version_created_at: "2026-05-10T10:00:00.000Z",
    previous_policy_package_version_id: null,
    policy_package_versions: [
      {
        version_id: "kb-1:architecture_midterm_default:policy:v1",
        version_label: "architecture_midterm_default v1",
        version_hash: "sha256:policyhash0001",
        status: "published",
        created_at: "2026-05-10T10:00:00.000Z",
      },
    ],
    policy_contract_status: "valid",
    policy_contract_errors: [],
    impact_set: null,
    incremental_rebuild_task: null,
    version_label: "architecture_midterm_default v1",
    scope_label: "Mid Term 体系结构文档：AV-1、OV-1、OV-2、OV-5、OV-7、SV-1、SV-2、SV-4",
    ai_autoadapt_enabled: true,
    updated_at: "2026-05-10T10:00:00.000Z",
    stage_order: ["asset_intake"],
    stages: {
      asset_intake: {
        stage_id: "asset_intake",
        label: "素材接入",
        group: "摄取与统一",
        enabled: true,
        ai_mode: "轻量识别 + 规则兜底",
        default_action: "block_return",
        objective: "判断当前文档能否进入正式抽取链路。",
        inputs: ["原始文件流"],
        ai_adaptation: "AI 自动识别语种和版式。",
        rules: [
          {
            key: "asset-1",
            rule_id: "asset-1",
            name: "接入格式完整性",
            meaning: "文件必须可读取并命中允许类型。",
            threshold: "mime_type in allowlist && size > 0",
            action: "block_return",
            rule_version: "r1.0",
            effect_kind: "block",
            scope_selector: { source_stage_id: "asset_intake" },
            input_schema: [
              {
                field_name: "input_hash",
                source_artifact: "runtime_snapshot",
                field_type: "string",
                required: true,
              },
            ],
            output_schema: [
              {
                field_name: "affected_object_ids",
                target_artifact: "impact_set",
                field_type: "string[]",
                used_for_impact: true,
              },
              {
                field_name: "output_hash",
                target_artifact: "runtime_snapshot",
                field_type: "string",
              },
            ],
            parameters: { conditions: [{ condition_id: "asset-1:threshold", operator: "matches" }] },
            trace_fields: [
              "rule_id",
              "rule_version",
              "rule_hash",
              "stage_id",
              "snapshot_id",
              "input_hash",
              "output_hash",
              "affected_object_ids",
            ],
            action_mapping: {
              effect_kind: "block",
              on_match: "block_return",
              runtime_decision: "block_return",
              impact_strategy: "track blocked objects",
            },
            rule_hash: "sha256:rulehash0001",
            contract_status: "valid",
            contract_errors: [],
          },
        ],
        branches: ["格式损坏 -> 阻断并退回素材池"],
        outputs: ["接入质量标签"],
        observability: ["mime_type", "input_hash"],
      },
    },
    ...overrides,
  };
}

function buildTask(): ArchiveIncrementalRebuildTask {
  return {
    task_id: "task-policy-1",
    archive_id: "kb-1",
    status: "pending",
    mode: "policy_change",
    minimum_rebuild_stage_id: "asset_intake",
    start_stage_id: "asset_intake",
    affected_document_ids: ["doc-1"],
    affected_stage_ids: ["asset_intake"],
    impact_set: {
      impact_id: "impact-policy-1",
      archive_id: "kb-1",
      changed_rule_ids: ["asset-1"],
      changed_stage_ids: ["asset_intake"],
      affected_document_ids: ["doc-1"],
      affected_stage_ids: ["asset_intake"],
      affected_chunk_ids: [],
      affected_candidate_ids: ["entity-alpha"],
      affected_relation_ids: [],
      affected_publication_snapshot_ids: [],
      minimum_rebuild_stage_id: "asset_intake",
      source_policy_snapshot_id: "snap-old",
      target_policy_snapshot_id: "snap-new",
      rule_changes: [
        {
          stage_id: "asset_intake",
          rule_id: "asset-1",
          change_type: "updated",
          previous_rule_hash: "sha256:old",
          next_rule_hash: "sha256:new",
        },
      ],
      generated_at: "2026-05-10T10:05:00.000Z",
    },
    writes_official_knowledge: false,
    output_policy: "candidate_or_pending_confirmation_only",
    allowed_outputs: ["impact_set", "candidate_task"],
    created_at: "2026-05-10T10:05:00.000Z",
  };
}

function renderPolicyRulesPage() {
  return render(
    <PolicyRulesPage
      context={{
        archiveId: "kb-1",
        archive: buildArchive(),
        policyPackageVersionId: "kb-1:architecture_midterm_default:policy:v1",
        runtimeSnapshotId: null,
        documentSetId: null,
        publicationSnapshotId: null,
      }}
    />,
  );
}

describe("p1 clean policy rules module", () => {
  beforeEach(() => {
    getArchivePolicyConfigMock.mockReset();
    updateArchivePolicyConfigMock.mockReset();
    listArchiveIncrementalRebuildTasksMock.mockReset();
    refreshArchivesMock.mockReset();

    getArchivePolicyConfigMock.mockResolvedValue({ data: buildPolicyConfig() });
    updateArchivePolicyConfigMock.mockResolvedValue({
      data: buildPolicyConfig({
        policy_package_version_id: "kb-1:architecture_midterm_default:policy:v2",
        policy_package_version_status: "draft",
        impact_set: buildTask().impact_set,
        incremental_rebuild_task: buildTask(),
      }),
    });
    listArchiveIncrementalRebuildTasksMock.mockResolvedValue({ data: [buildTask()] });
  });

  it("loads policy package, rule contracts, action mapping, and candidate-only impact tasks", async () => {
    renderPolicyRulesPage();

    expect(await screen.findByRole("heading", { name: "策略规则" })).toBeInTheDocument();
    expect(getArchivePolicyConfigMock).toHaveBeenCalledWith("kb-1");
    expect(listArchiveIncrementalRebuildTasksMock).toHaveBeenCalledWith("kb-1");
    expect(screen.getAllByText("kb-1:architecture_midterm_default:policy:v1").length).toBeGreaterThan(0);
    expect(screen.getByText("architecture_midterm_default")).toBeInTheDocument();
    expect(screen.getAllByText("asset-1").length).toBeGreaterThan(0);
    expect(screen.getByText("规则字段合同编辑")).toBeInTheDocument();
    expect(screen.getByText("RuleExecutionRecord 字段")).toBeInTheDocument();
    expect(screen.getAllByText("policy_snapshot_id").length).toBeGreaterThan(0);
    expect(screen.getByText(/track blocked objects/)).toBeInTheDocument();
    expect(screen.getByText("candidate_or_pending_confirmation_only")).toBeInTheDocument();
    expect(screen.getByText("仅候选任务")).toBeInTheDocument();
  });

  it("saves edited rule field contracts through the policyRules API adapter", async () => {
    const eventSpy = vi.fn();
    window.addEventListener(P1_POLICY_CONFIG_UPDATED_EVENT, eventSpy);

    renderPolicyRulesPage();

    const inputSchema = await screen.findByLabelText("规则输入 Schema");
    fireEvent.change(inputSchema, {
      target: {
        value: JSON.stringify(
          [
            {
              field_name: "input_hash",
              source_artifact: "runtime_snapshot",
              field_type: "string",
              required: true,
            },
            {
              field_name: "contract_revision_reason",
              source_artifact: "policy_editor",
              field_type: "string",
              required: false,
            },
          ],
          null,
          2,
        ),
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存为策略草稿" }));

    await waitFor(() => {
      expect(updateArchivePolicyConfigMock).toHaveBeenCalledWith(
        "kb-1",
        expect.objectContaining({
          policy_package_version_status: "draft",
          stages: expect.objectContaining({
            asset_intake: expect.objectContaining({
              rules: expect.arrayContaining([
                expect.objectContaining({
                  rule_id: "asset-1",
                  input_schema: expect.arrayContaining([
                    expect.objectContaining({ field_name: "contract_revision_reason" }),
                  ]),
                  output_schema: expect.arrayContaining([
                    expect.objectContaining({ field_name: "affected_object_ids" }),
                    expect.objectContaining({ field_name: "output_hash" }),
                  ]),
                  trace_fields: expect.arrayContaining(["rule_id", "rule_version", "rule_hash", "input_hash", "output_hash"]),
                }),
              ]),
            }),
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(refreshArchivesMock).toHaveBeenCalledWith("kb-1");
      expect(eventSpy).toHaveBeenCalled();
    });
    window.removeEventListener(P1_POLICY_CONFIG_UPDATED_EVENT, eventSpy);
  });
});
