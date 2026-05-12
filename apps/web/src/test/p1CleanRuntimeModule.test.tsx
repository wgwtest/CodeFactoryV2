import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { P1WorkspaceContext } from "../features/p1Clean/types";
import { runtimeApi } from "../features/p1Clean/modules/runtime/api";
import { RuntimePage } from "../features/p1Clean/modules/runtime/page";
import type { RuntimeContract } from "../features/p1Clean/modules/runtime/types";

vi.mock("../features/p1Clean/modules/runtime/api", () => ({
  runtimeApi: {
    canUseRuntimeStream: vi.fn(),
    getRuntimeContract: vi.fn(),
    getRuntimeDocuments: vi.fn(),
    startRuntimeExtraction: vi.fn(),
    subscribeRuntimeContract: vi.fn(),
  },
}));

const getRuntimeDocumentsMock = vi.mocked(runtimeApi.getRuntimeDocuments);
const getRuntimeContractMock = vi.mocked(runtimeApi.getRuntimeContract);
const canUseRuntimeStreamMock = vi.mocked(runtimeApi.canUseRuntimeStream);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function buildContext(): P1WorkspaceContext {
  return {
    archiveId: "nas-a",
    archive: {
      archive_id: "nas-a",
      name: "NAS Archive",
      source_dir: "E:/sample",
      extract_root: "E:/sample/.extract",
      is_active: true,
      status: "ready",
      last_built_at: null,
      last_error: null,
      summary: null,
      artifacts: {
        base_exists: true,
        curated_exists: true,
        publication_exists: false,
      },
      build_state: {
        archive_id: "nas-a",
        archive_name: "NAS Archive",
        mode: "runtime",
        status: "running",
        started_at: null,
        updated_at: null,
        expected_document_count: 8,
        completed_document_ids: ["doc-1", "doc-3", "doc-4", "doc-5", "doc-6", "doc-7", "doc-8"],
        skipped_document_ids: ["doc-2"],
        pending_document_ids: [],
        failed_document_id: null,
        failed_message: null,
        current_document_id: "doc-1",
        current_document_title: "SV-2 Translation",
        current_document_path: "runtime/SV-2.docx",
        current_chunk: null,
        current_stage_id: "quality_policy_evaluation_governance_gate",
        current_stage_label: "质量门禁",
        current_stage_status: "running",
        current_stage_message: "后端正在执行质量门禁",
        warning_count: 1,
        warnings: [
          {
            code: "docling_docx_skipped",
            severity: "warning",
            file_path: "E:/sample/SV-2翻译.docx",
            file_type: "docx",
            message: "Docling failed",
            reason: "SV-2翻译.docx 未能通过 Docling 解析。",
          },
        ],
        documents: [
          {
            document_id: "doc-1",
            path: "runtime/SV-1.docx",
            title: "SV-1 Translation",
            file_type: "docx",
            source_archive: "test",
            state: "completed",
          },
          {
            document_id: "doc-2",
            path: "runtime/SV-2.docx",
            title: "SV-2 Translation",
            file_type: "docx",
            source_archive: "test",
            state: "skipped",
          },
        ],
      },
    },
    documentSetId: "nas-a:document-set",
    policyPackageVersionId: "policy-v1",
    runtimeSnapshotId: null,
    publicationSnapshotId: null,
  };
}

function buildRuntime(): RuntimeContract {
  return {
    archive_id: "nas-a",
    document_id: "doc-1",
    document_title: "SV-2 Translation",
    document_set_id: "nas-a:document-set",
    runtime_snapshot_id: "RUN-policy-1",
    stream_status: "polling",
    current_document_id: "doc-1",
    current_stage_or_rule_id: "quality.min_supporting_documents",
    current_stage_id: "quality_policy_evaluation_governance_gate",
    current_stage_label: "质量门禁",
    current_stage_status: "running",
    current_stage_message: "后端正在执行质量门禁",
    status: "running",
    runtime_status: "running",
    runtime_mode: "persisted",
    persisted_stage_ids: ["asset_intake", "quality_policy_evaluation_governance_gate"],
    source_document: {
      title: "SV-2 Translation",
      path: "runtime/SV-2.docx",
    },
    policy_snapshot: {
      snapshot_id: "policy-1",
      run_id: "RUN-policy-1",
      archive_id: "nas-a",
      policy_package_version_id: "policy-v1",
      version_label: "Policy v1",
      scope_label: "test",
      captured_at: "2026-05-10T00:00:00+00:00",
      ai_autoadapt_enabled: true,
      config_updated_at: null,
      stage_order: [],
      stages: [],
    },
    policy_package_id: "package-1",
    policy_package_version_id: "policy-v1",
    policy_version: "policy-v1",
    policy_snapshot_id: "policy-1",
    rule_execution_records: [],
    runtime_events: [
      {
        event_id: "doc-1:1:run_started",
        event_type: "run_started",
        level: "success",
        message: "运行已启动",
        document_id: "doc-1",
        stage_id: "asset_intake",
        payload: {},
      },
      {
        event_id: "doc-1:2:object_candidate_created",
        event_type: "object_candidate_created",
        level: "success",
        message: "对象候选生成：National Airspace System",
        document_id: "doc-1",
        stage_id: "concept_candidate_review",
        object_id: "entity-1",
        candidate_id: "entity-1",
        payload: {},
      },
      {
        event_id: "doc-1:3:relation_candidate_created",
        event_type: "relation_candidate_created",
        level: "success",
        message: "关系候选生成：part_of",
        document_id: "doc-1",
        stage_id: "relation_review_family_normalization",
        relation_id: "doc-1:relation:1",
        candidate_id: "doc-1:relation:1",
        payload: {},
      },
    ],
    generated_candidates: [
      {
        candidate_id: "entity-1",
        candidate_type: "entity",
        label: "National Airspace System",
        source_document_id: "doc-1",
        stage_id: "concept_candidate_review",
        status: "running",
        evidence_count: 1,
        relation_count: 0,
        attributes: {},
      },
      {
        candidate_id: "doc-1:relation:1",
        candidate_type: "relation",
        label: "part_of",
        source_document_id: "doc-1",
        stage_id: "relation_review_family_normalization",
        status: "running",
        evidence_count: 1,
        relation_count: 1,
        attributes: {
          source_name: "National Airspace System",
          target_name: "Mission Orchestration",
        },
      },
    ],
    stages: [
      {
        stage_id: "asset_intake",
        label: "Asset Intake",
        group: "Input",
        order: 1,
        status: "completed",
        is_current: false,
        graph: {
          nodes: [],
          edges: [],
          primary_node_ids: [],
          primary_edge_ids: [],
        },
        stage_observer: {
          mode: "stage",
          title: "Asset Intake",
          status: "completed",
          stream: [
            {
              event_id: "e-1",
              kind: "progress",
              level: "success",
              message: "文档集合已进入运行",
            },
          ],
          sections: [],
          actions: [],
        },
        node_observers: {},
        edge_observers: {},
      },
      {
        stage_id: "quality_policy_evaluation_governance_gate",
        label: "Quality Gate",
        group: "Policy",
        order: 2,
        status: "running",
        is_current: true,
        graph: {
          nodes: [
            {
              node_id: "doc-1:rule",
              label: "规则命中",
              node_type: "rule_hit",
              stage_id: "quality_policy_evaluation_governance_gate",
              status: "completed",
              origin: "derived",
              is_primary: true,
              is_focus: false,
              metrics: {},
              attributes: {},
            },
            {
              node_id: "doc-1:output",
              label: "运行快照",
              node_type: "runtime_snapshot",
              stage_id: "quality_policy_evaluation_governance_gate",
              status: "running",
              origin: "derived",
              is_primary: true,
              is_focus: true,
              metrics: {},
              attributes: {},
            },
          ],
          edges: [
            {
              edge_id: "doc-1:rule:output",
              source: "doc-1:rule",
              target: "doc-1:output",
              relation: "results_in",
              stage_id: "quality_policy_evaluation_governance_gate",
              status: "running",
              origin: "derived",
              is_primary: true,
              attributes: {},
            },
          ],
          primary_node_ids: ["doc-1:rule", "doc-1:output"],
          primary_edge_ids: ["doc-1:rule:output"],
        },
        stage_observer: {
          mode: "stage",
          title: "阶段视角 · 质量门禁",
          subtitle: "SV-2 Translation",
          status: "running",
          stream: [
            {
              event_id: "e-2",
              kind: "rule",
              level: "warning",
              message: "命中规则：min_supporting_documents",
            },
          ],
          sections: [
            {
              section_id: "gate",
              title: "门禁摘要",
              fields: [
                {
                  key: "evidence_count",
                  label: "evidence_count",
                  value: "2",
                  tone: "success",
                },
              ],
            },
          ],
          actions: [],
        },
        node_observers: {},
        edge_observers: {},
      },
    ],
    graph_projection: {
      nodes: [
        {
          node_id: "doc-1:rule",
          label: "规则命中",
          node_type: "rule_hit",
          stage_id: "quality_policy_evaluation_governance_gate",
          status: "completed",
          origin: "derived",
          is_primary: true,
          is_focus: false,
          metrics: {},
          attributes: {},
        },
        {
          node_id: "doc-1:output",
          label: "运行快照",
          node_type: "runtime_snapshot",
          stage_id: "quality_policy_evaluation_governance_gate",
          status: "running",
          origin: "derived",
          is_primary: true,
          is_focus: true,
          metrics: {},
          attributes: {},
        },
      ],
      edges: [
        {
          edge_id: "doc-1:rule:output",
          source: "doc-1:rule",
          target: "doc-1:output",
          relation: "results_in",
          stage_id: "quality_policy_evaluation_governance_gate",
          status: "running",
          origin: "derived",
          is_primary: true,
          attributes: {},
        },
      ],
      node_count: 2,
      edge_count: 1,
      current_stage_id: "quality_policy_evaluation_governance_gate",
      current_node_ids: ["doc-1:rule", "doc-1:output"],
      current_edge_ids: ["doc-1:rule:output"],
      changed_node_ids: ["doc-1:rule", "doc-1:output"],
      changed_edge_ids: ["doc-1:rule:output"],
      summary: {},
    },
  } as RuntimeContract;
}

describe("p1 clean runtime module", () => {
  it("loads runtime through the module adapter and falls back to polling when stream is unavailable", async () => {
    getRuntimeDocumentsMock.mockResolvedValue({
      data: [
        {
          id: "doc-1",
          title: "SV-2 Translation",
          file_type: "docx",
          source_archive: "test",
          character_count: 1200,
          included_in_archive: true,
          entity_count: 1,
          event_count: 0,
          process_count: 1,
          knowledge_item_count: 2,
        },
      ],
    } as Awaited<ReturnType<typeof runtimeApi.getRuntimeDocuments>>);
    getRuntimeContractMock.mockResolvedValue({ data: buildRuntime() } as Awaited<
      ReturnType<typeof runtimeApi.getRuntimeContract>
    >);
    canUseRuntimeStreamMock.mockReturnValue(false);

    render(<RuntimePage context={buildContext()} />);

    await waitFor(() =>
      expect(getRuntimeContractMock).toHaveBeenCalledWith(
        expect.objectContaining({
          archiveId: "nas-a",
          documentId: "doc-1",
          documentSetId: "nas-a:document-set",
          policyPackageVersionId: "policy-v1",
        }),
      ),
    );

    expect((await screen.findAllByText("RUN-policy-1")).length).toBeGreaterThan(0);
    expect(screen.getByText("知识库抽取总控")).toBeInTheDocument();
    expect(screen.getByText("单文档观察")).toBeInTheDocument();
    expect(screen.getByText("本次抽取产生 1 条告警")).toBeInTheDocument();
    expect(screen.getByText(/SV-2翻译.docx 未能通过 Docling 解析/)).toBeInTheDocument();
    expect(screen.getAllByText("质量门禁").length).toBeGreaterThan(0);
    expect(screen.getByText("SSE 不可用，已切换轮询")).toBeTruthy();
    expect(screen.getByText("输入对象")).toBeTruthy();
    expect(screen.getByText("策略/动作依据")).toBeTruthy();
    expect(screen.getByText("输出对象")).toBeTruthy();
    expect(screen.getByText("对象生成")).toBeTruthy();
    expect(screen.getAllByText(/National Airspace System/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/part_of/).length).toBeGreaterThan(0);
  });
});
