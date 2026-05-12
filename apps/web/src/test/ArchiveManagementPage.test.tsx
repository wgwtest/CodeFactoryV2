import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";

import { ArchiveManagementPage } from "../pages/ArchiveManagementPage";
import type {
  ArchivePolicyConfig,
  ArchiveDocumentRuntimeContract,
  ArchiveDocumentRuntimeObserverPayload,
  ArchiveDocumentRuntimeStageSnapshot,
  ArchiveDocumentRuntimeStatus,
  KnowledgeArchive,
} from "../lib/api";
import type { DocumentRuntimeSnapshot, P1ResponseEnvelope } from "../features/p1/contracts";

const refreshArchivesMock = vi.fn();
const setActiveArchiveIdMock = vi.fn();
const createKnowledgeArchiveMock = vi.fn();
const extractKnowledgeArchiveMock = vi.fn();
const getArchivePolicyConfigMock = vi.fn();
const updateArchivePolicyConfigMock = vi.fn();
const getArchiveDocumentRuntimeMock = vi.fn();
const subscribeArchiveDocumentRuntimeMock = vi.fn();
const getP1DocumentRuntimeSnapshotMock = vi.fn();
const subscribeP1DocumentRuntimeSnapshotMock = vi.fn();

function renderPage(initialEntries = ["/archives"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ArchiveManagementPage />
    </MemoryRouter>,
  );
}

function buildArchive(overrides: Partial<KnowledgeArchive> = {}): KnowledgeArchive {
  return {
    archive_id: "kb-1",
    name: "知识库一",
    source_dir: "/tmp/kb-1",
    extract_root: "/tmp/extract/kb-1",
    is_active: true,
    status: "ready",
    last_built_at: "2026-04-21T03:43:00.000Z",
    last_error: null,
    summary: { archive_id: "kb-1", document_count: 3, entity_count: 12, event_count: 0, process_count: 2 },
    artifacts: { base_exists: true, curated_exists: false, publication_exists: false },
    build_state: {
      archive_id: "kb-1",
      archive_name: "知识库一",
      mode: "formal",
      status: "running",
      started_at: "2026-04-21T03:00:00.000Z",
      updated_at: "2026-04-21T03:43:00.000Z",
      expected_document_count: 3,
      completed_document_ids: ["doc-1"],
      pending_document_ids: ["doc-3"],
      failed_document_id: null,
      failed_message: null,
      current_document_id: "doc-2",
      current_document_title: "SV-2 翻译",
      current_document_path: "sv-2.docx",
      current_chunk: null,
      policy_snapshot: {
        snapshot_id: "policy-kb-1",
        captured_at: "2026-04-21T03:00:00.000Z",
        archive_id: "kb-1",
        version_label: "13 阶段抽取蓝图 v3",
        scope_label: "单文档抽取过程",
        ai_autoadapt_enabled: true,
        config_updated_at: "2026-04-21T02:58:00.000Z",
        stage_order: ["asset_intake", "parser_router"],
        stages: [
          {
            stage_id: "asset_intake",
            label: "素材接入",
            enabled: true,
            ai_mode: "轻量识别 + 规则兜底",
            default_action: "block_return",
            rule_count: 3,
          },
        ],
      },
      warning_count: 1,
      warnings: [
        {
          code: "warning",
          severity: "warning",
          file_path: "sample.docx",
          file_type: "docx",
          message: "存在 1 条待治理告警",
        },
      ],
      documents: [
        { document_id: "doc-1", path: "a.pdf", title: "概览", file_type: "pdf", source_archive: "kb-1", state: "completed" },
        { document_id: "doc-2", path: "sv-2.docx", title: "SV-2 翻译", file_type: "docx", source_archive: "kb-1", state: "running" },
        { document_id: "doc-3", path: "b.pdf", title: "FAR", file_type: "pdf", source_archive: "kb-1", state: "pending" },
      ],
    },
    ...overrides,
  };
}

function buildObserver(
  title: string,
  mode: "stage" | "node" | "edge",
  status: ArchiveDocumentRuntimeStatus,
): ArchiveDocumentRuntimeObserverPayload {
  return {
    mode,
    title,
    subtitle: "对象观察窗测试数据",
    status,
    stream: [{ event_id: `${mode}-evt-1`, kind: "progress", level: "info", message: "运行中" }],
    sections: [
      {
        section_id: "summary",
        title: "结构化摘要",
        fields: [
          { key: "object", label: "当前对象", value: "门禁决策 GD-3", tone: "info" },
          { key: "risk", label: "风险", value: "阻断 1", tone: "warning" },
        ],
      },
    ],
    actions: [{ action_id: "view", label: "查看图谱", target_kind: "graph" }],
  };
}

function buildStage(
  stageId: string,
  label: string,
  order: number,
  status: ArchiveDocumentRuntimeStatus,
  isCurrent = false,
): ArchiveDocumentRuntimeStageSnapshot {
  const graph = isCurrent
    ? {
        nodes: [
          {
            node_id: "rule-hit",
            label: "规则命中",
            node_type: "rule_hit",
            stage_id: stageId,
            status: "completed" as const,
            origin: "derived" as const,
            is_primary: true,
            is_focus: false,
            metrics: {},
            attributes: {},
          },
          {
            node_id: "gate",
            label: "门禁决策",
            node_type: "gate_decision",
            stage_id: stageId,
            status: "running" as const,
            origin: "derived" as const,
            is_primary: true,
            is_focus: true,
            metrics: {},
            attributes: {},
          },
          {
            node_id: "blocked",
            label: "阻断结果",
            node_type: "blocked_result",
            stage_id: stageId,
            status: "blocked" as const,
            origin: "derived" as const,
            is_primary: false,
            is_focus: false,
            metrics: {},
            attributes: {},
          },
        ],
        edges: [
          {
            edge_id: "rule-hit:gate",
            source: "rule-hit",
            target: "gate",
            relation: "results_in",
            stage_id: stageId,
            status: "running" as const,
            origin: "derived" as const,
            is_primary: true,
            attributes: {},
          },
          {
            edge_id: "gate:blocked",
            source: "gate",
            target: "blocked",
            relation: "blocked_by",
            stage_id: stageId,
            status: "blocked" as const,
            origin: "derived" as const,
            is_primary: true,
            attributes: {},
          },
        ],
        primary_node_ids: ["rule-hit", "gate"],
        primary_edge_ids: ["rule-hit:gate", "gate:blocked"],
      }
    : {
        nodes: [
          {
            node_id: `${stageId}-node`,
            label,
            node_type: "stage_node",
            stage_id: stageId,
            status,
            origin: "derived" as const,
            is_primary: true,
            is_focus: false,
            metrics: {},
            attributes: {},
          },
        ],
        edges: [],
        primary_node_ids: [`${stageId}-node`],
        primary_edge_ids: [],
      };

  return {
    stage_id: stageId,
    label,
    group: order <= 4 ? "摄取与统一" : order <= 10 ? "证据与知识生成" : "规范化与发布",
    order,
    status,
    is_current: isCurrent,
    graph,
    stage_observer: buildObserver(`阶段视角 · ${label}`, "stage", status),
    node_observers: isCurrent
      ? {
          "rule-hit": buildObserver("节点视角 · 规则命中", "node", "completed"),
          gate: buildObserver("节点视角 · 门禁决策", "node", "running"),
          blocked: buildObserver("节点视角 · 阻断结果", "node", "blocked"),
        }
      : {},
    edge_observers: isCurrent
      ? {
          "rule-hit:gate": buildObserver("边视角 · 规则命中 -> 门禁决策", "edge", "running"),
          "gate:blocked": buildObserver("边视角 · 门禁决策 -> 阻断结果", "edge", "blocked"),
        }
      : {},
  };
}

function buildRuntimeContract(overrides: Partial<ArchiveDocumentRuntimeContract> = {}): ArchiveDocumentRuntimeContract {
  return {
    archive_id: "kb-1",
    document_id: "doc-1",
    document_title: "概览",
    current_stage_id: "quality_policy_evaluation_governance_gate",
    current_stage_label: "质量门禁",
    status: "running",
    runtime_mode: "persisted",
    persisted_stage_ids: [
      "asset_intake",
      "parser_router",
      "parser_execution",
      "unified_document_object",
      "evidence_constructor",
      "evidence_graph_chunk_layer",
      "evidence_pack",
      "concept_candidate_review",
      "relation_review_family_normalization",
      "definition_summary_conflict_consolidation",
      "canonical_knowledge",
      "quality_policy_evaluation_governance_gate",
      "indexes_snapshots_apis",
    ],
    source_document: {
      title: "概览",
      file_type: "pdf",
      source_archive: "kb-1",
      source_file_path: "/tmp/kb-1/a.pdf",
    },
    policy_snapshot: {
      snapshot_id: "policy-doc-1",
      captured_at: "2026-04-21T03:01:00.000Z",
      archive_id: "kb-1",
      version_label: "13 阶段抽取蓝图 v3",
      scope_label: "单文档抽取过程",
      ai_autoadapt_enabled: true,
      config_updated_at: "2026-04-21T02:58:00.000Z",
      stage_order: [
        "asset_intake",
        "parser_router",
        "parser_execution",
        "unified_document_object",
        "evidence_constructor",
      ],
      stages: [
        {
          stage_id: "asset_intake",
          label: "素材接入",
          enabled: true,
          ai_mode: "轻量识别 + 规则兜底",
          default_action: "block_return",
          rule_count: 3,
        },
      ],
    },
    stages: [
      buildStage("asset_intake", "素材接入", 1, "completed"),
      buildStage("parser_router", "解析路由", 2, "completed"),
      buildStage("parser_execution", "解析执行", 3, "completed"),
      buildStage("unified_document_object", "统一文档", 4, "completed"),
      buildStage("evidence_constructor", "证据构造", 5, "completed"),
      buildStage("evidence_graph_chunk_layer", "证据图谱/切块", 6, "completed"),
      buildStage("evidence_pack", "证据包", 7, "completed"),
      buildStage("concept_candidate_review", "概念审查", 8, "completed"),
      buildStage("relation_review_family_normalization", "关系/家族", 9, "completed"),
      buildStage("definition_summary_conflict_consolidation", "定义/冲突", 10, "completed"),
      buildStage("canonical_knowledge", "规范知识", 11, "completed"),
      buildStage("quality_policy_evaluation_governance_gate", "质量门禁", 12, "running", true),
      buildStage("indexes_snapshots_apis", "发布/API", 13, "pending"),
    ],
    ...overrides,
  };
}

function buildP1RuntimeSnapshot(overrides: Partial<DocumentRuntimeSnapshot> = {}): DocumentRuntimeSnapshot {
  return {
    archive_id: "kb-1",
    document_id: "doc-1",
    run_id: "RUN-P1-R0-001",
    status: "running",
    current_stage_id: "quality_gate",
    current_stage_message: "质量门禁正在执行证据覆盖率规则",
    stream_status: "connected",
    policy_snapshot: {
      snapshot_id: "RS-P1-R0-001",
      archive_id: "kb-1",
      run_id: "RUN-P1-R0-001",
      policy_package_id: "PKG-CONTRACT-GENERAL",
      policy_package_version_id: "PKGV-20260508-R0",
      policy_package_version_hash: "sha256:p1r0policy0001",
      frozen_at: "2026-05-08T10:00:00+08:00",
      stage_contract_refs: ["unified_document", "quality_gate"],
      rule_contract_refs: ["RL-QG-COVERAGE-001@r1.0"],
    },
    stage_snapshots: [
      {
        stage_id: "unified_document",
        stage_name: "统一文档对象",
        status: "completed",
        input_object_count: 1,
        output_object_count: 128,
        rule_execution_record_ids: ["RECORD-DOC-STRUCT-001"],
        graph_projection_id: "GRAPH-P1-R0-001",
      },
      {
        stage_id: "quality_gate",
        stage_name: "质量门禁",
        status: "running",
        input_object_count: 24,
        output_object_count: 6,
        rule_execution_record_ids: ["RECORD-QG-001"],
        graph_projection_id: "GRAPH-P1-R0-001",
      },
      {
        stage_id: "publication_candidate",
        stage_name: "发布候选",
        status: "pending",
        input_object_count: 6,
        output_object_count: 0,
        rule_execution_record_ids: [],
        graph_projection_id: "GRAPH-P1-R0-001",
      },
    ],
    graph_projection: {
      graph_projection_id: "GRAPH-P1-R0-001",
      archive_id: "kb-1",
      document_id: "doc-1",
      view_mode: "semantic_aggregate",
      layout_strategy: "layered_dag",
      highlighted_node_ids: ["node-rule-coverage"],
      highlighted_edge_ids: ["edge-rule-to-output"],
      nodes: [
        {
          node_id: "node-input-candidates",
          label: "候选知识集合 24",
          node_type: "input_object",
          stage_id: "quality_gate",
          status: "running",
          semantic_role: "input",
          object_count: 24,
        },
        {
          node_id: "node-rule-coverage",
          label: "证据覆盖率门禁",
          node_type: "rule",
          stage_id: "quality_gate",
          status: "running",
          semantic_role: "basis",
          payload_ref: "RL-QG-COVERAGE-001@r1.0",
        },
        {
          node_id: "node-output-publication",
          label: "发布候选输入包 6",
          node_type: "output_object",
          stage_id: "quality_gate",
          status: "pending",
          semantic_role: "output",
          object_count: 6,
        },
      ],
      edges: [
        {
          edge_id: "edge-input-to-rule",
          source: "node-input-candidates",
          target: "node-rule-coverage",
          relation: "evaluated_by",
          stage_id: "quality_gate",
          evidence: "evidence_coverage actual=0.91",
        },
        {
          edge_id: "edge-rule-to-output",
          source: "node-rule-coverage",
          target: "node-output-publication",
          relation: "warn_continue",
          stage_id: "quality_gate",
          evidence: "threshold >= 0.90",
        },
      ],
    },
    rule_execution_records: [
      {
        execution_id: "RECORD-QG-001",
        run_id: "RUN-P1-R0-001",
        archive_id: "kb-1",
        document_id: "doc-1",
        stage_id: "quality_gate",
        rule_id: "RL-QG-COVERAGE-001",
        rule_version: "r1.0",
        rule_hash: "sha256:rulecoverage001",
        input_artifact_refs: [{ artifact_id: "candidate-knowledge", artifact_type: "knowledge_candidate" }],
        output_artifact_refs: [{ artifact_id: "publication-candidate", artifact_type: "publication_candidate" }],
        input_hash: "sha256:input001",
        output_hash: "sha256:output001",
        affected_object_ids: ["K-24", "K-31", "P-24"],
        affected_relation_ids: ["R-11"],
        metrics: { evidence_coverage: 0.91 },
        decision: "warn_continue",
        executed_at: "2026-05-08T10:00:00+08:00",
      },
    ],
    event_trace: [
      {
        trace_id: "TRACE-QG-001",
        source_kind: "runtime",
        object_ids: ["RL-QG-COVERAGE-001", "K-24"],
        summary: "质量门禁命中证据覆盖率规则，输出带警告发布候选。",
      },
    ],
    ...overrides,
  };
}

function buildP1RuntimeEnvelope(
  overrides: Partial<DocumentRuntimeSnapshot> = {},
): P1ResponseEnvelope<DocumentRuntimeSnapshot> {
  return {
    contract_version: "p1.document_runtime.r0",
    source_kind: "fixture",
    generated_at: "2026-05-08T10:00:00+08:00",
    data: buildP1RuntimeSnapshot(overrides),
  };
}

function buildPolicyConfig(overrides: Partial<ArchivePolicyConfig> = {}): ArchivePolicyConfig {
  return {
    archive_id: "kb-1",
    version_label: "13 阶段抽取蓝图 v1",
    scope_label: "单文档抽取过程",
    ai_autoadapt_enabled: true,
    updated_at: "2026-04-22T09:00:00.000Z",
    stage_order: [
      "asset_intake",
      "parser_router",
      "parser_execution",
      "unified_document_object",
      "evidence_constructor",
      "evidence_graph_chunk_layer",
      "evidence_pack",
      "concept_candidate_review",
      "relation_review_family_normalization",
      "definition_summary_conflict_consolidation",
      "canonical_knowledge",
      "quality_policy_evaluation_governance_gate",
      "indexes_snapshots_apis",
    ],
    stages: {
      asset_intake: {
        stage_id: "asset_intake",
        label: "素材接入",
        group: "摄取与统一",
        enabled: true,
        ai_mode: "轻量识别 + 规则兜底",
        default_action: "block_return",
        objective: "判断文档是否可以进入正式抽取链路。",
        inputs: ["原始文件流", "来源标记", "接入白名单"],
        ai_adaptation: "AI 自动识别语种、版式和扫描特征。",
        rules: [
          {
            key: "asset-1",
            name: "接入格式完整性",
            meaning: "文件必须可读取并命中允许类型。",
            threshold: "mime_type in allowlist && size > 0",
            action: "block_return",
          },
        ],
        branches: ["扫描件 -> OCR 预处理", "格式损坏 -> 阻断并退回素材池"],
        outputs: ["接入质量标签", "文档类型初判"],
        observability: ["mime_type", "scan_score"],
      },
      parser_router: {
        stage_id: "parser_router",
        label: "解析路由",
        group: "摄取与统一",
        enabled: true,
        ai_mode: "解析器路由建议",
        default_action: "auto_pass",
        objective: "为当前文档选择最合适的解析器组合。",
        inputs: ["接入质量标签"],
        ai_adaptation: "AI 根据版式、语言和图文比例给解析链路排序。",
        rules: [],
        branches: ["已知模板 -> 高速解析链"],
        outputs: ["解析器选择结果"],
        observability: ["parser_choice"],
      },
      parser_execution: {
        stage_id: "parser_execution",
        label: "解析执行",
        group: "摄取与统一",
        enabled: true,
        ai_mode: "结构修复辅助",
        default_action: "warn_continue",
        objective: "稳定产出结构化解析结果。",
        inputs: ["解析器选择结果"],
        ai_adaptation: "AI 对段落续接、表格裂解和标题层级混乱进行修复。",
        rules: [],
        branches: ["解析稳定 -> 统一文档对象"],
        outputs: ["结构化正文"],
        observability: ["body_coverage"],
      },
      unified_document_object: {
        stage_id: "unified_document_object",
        label: "统一文档",
        group: "摄取与统一",
        enabled: true,
        ai_mode: "对象整编与字段对齐",
        default_action: "auto_pass",
        objective: "将多来源解析结果压成统一文档对象。",
        inputs: ["结构化正文"],
        ai_adaptation: "AI 统一标题、段落、表格和附件字段。",
        rules: [],
        branches: ["对象完整 -> 证据构造"],
        outputs: ["统一文档对象"],
        observability: ["schema_score"],
      },
      evidence_constructor: {
        stage_id: "evidence_constructor",
        label: "证据构造",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "证据片段定位",
        default_action: "auto_pass",
        objective: "从统一文档对象中切出可回溯证据片段。",
        inputs: ["统一文档对象"],
        ai_adaptation: "AI 按语义边界和章节结构切出证据片段。",
        rules: [],
        branches: ["证据稳定 -> 图谱/切块层"],
        outputs: ["证据片段集"],
        observability: ["evidence_count"],
      },
      evidence_graph_chunk_layer: {
        stage_id: "evidence_graph_chunk_layer",
        label: "证据图谱/切块",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "图谱切块编排",
        default_action: "auto_pass",
        objective: "组织证据图谱节点和 chunk 分层。",
        inputs: ["证据片段集"],
        ai_adaptation: "AI 根据实体密度和章节边界生成图谱节点。",
        rules: [],
        branches: ["切块稳定 -> 证据包"],
        outputs: ["证据图谱节点"],
        observability: ["chunk_token"],
      },
      evidence_pack: {
        stage_id: "evidence_pack",
        label: "证据包",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "证据包编排与压缩",
        default_action: "auto_pass",
        objective: "将图谱节点和原文证据打包成标准证据包。",
        inputs: ["证据图谱节点"],
        ai_adaptation: "AI 自动裁剪主证据、补证据和风险摘要。",
        rules: [],
        branches: ["证据包稳定 -> 三条审查支路"],
        outputs: ["标准证据包"],
        observability: ["pack_token"],
      },
      concept_candidate_review: {
        stage_id: "concept_candidate_review",
        label: "概念审查",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "概念候选判断",
        default_action: "manual_review",
        objective: "筛出值得进入规范知识层的概念候选。",
        inputs: ["标准证据包"],
        ai_adaptation: "AI 结合证据包和术语策略生成概念候选。",
        rules: [],
        branches: ["可信度高 -> 规范知识汇流"],
        outputs: ["概念候选集"],
        observability: ["confidence"],
      },
      relation_review_family_normalization: {
        stage_id: "relation_review_family_normalization",
        label: "关系/家族",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "关系归一与家族推断",
        default_action: "warn_continue",
        objective: "识别关系、家族归属和继承路径。",
        inputs: ["标准证据包"],
        ai_adaptation: "AI 自动判断关系方向和家族归属。",
        rules: [],
        branches: ["关系稳定 -> 规范知识汇流"],
        outputs: ["归一关系候选"],
        observability: ["relation_count"],
      },
      definition_summary_conflict_consolidation: {
        stage_id: "definition_summary_conflict_consolidation",
        label: "定义/冲突",
        group: "证据与知识生成",
        enabled: true,
        ai_mode: "定义整合与冲突诊断",
        default_action: "manual_review",
        objective: "生成定义、摘要和冲突结论。",
        inputs: ["标准证据包"],
        ai_adaptation: "AI 自动汇总定义候选、摘要和冲突说明。",
        rules: [],
        branches: ["冲突可收敛 -> 规范知识汇流"],
        outputs: ["定义候选"],
        observability: ["conflict_count"],
      },
      canonical_knowledge: {
        stage_id: "canonical_knowledge",
        label: "规范知识",
        group: "规范化与发布",
        enabled: true,
        ai_mode: "规范对象整编",
        default_action: "auto_pass",
        objective: "形成可治理、可发布的规范知识对象。",
        inputs: ["概念候选集"],
        ai_adaptation: "AI 自动拼装规范知识对象。",
        rules: [],
        branches: ["对象稳定 -> 质量门禁"],
        outputs: ["规范知识对象"],
        observability: ["canonical_object_score"],
      },
      quality_policy_evaluation_governance_gate: {
        stage_id: "quality_policy_evaluation_governance_gate",
        label: "质量门禁",
        group: "规范化与发布",
        enabled: true,
        ai_mode: "质量门禁决策辅助",
        default_action: "block_return",
        objective: "集中执行质量门禁并决定是否阻断。",
        inputs: ["规范知识对象"],
        ai_adaptation: "AI 根据前序阶段风险信号给出门禁建议。",
        rules: [],
        branches: ["门禁通过 -> 发布/API"],
        outputs: ["Gate 决策"],
        observability: ["gate_decision"],
      },
      indexes_snapshots_apis: {
        stage_id: "indexes_snapshots_apis",
        label: "发布/API",
        group: "规范化与发布",
        enabled: true,
        ai_mode: "发布策略建议",
        default_action: "defer_publish",
        objective: "控制索引、快照和 API 发布的范围。",
        inputs: ["Gate 决策"],
        ai_adaptation: "AI 根据风险等级建议发布通道。",
        rules: [],
        branches: ["门禁通过 -> 正式发布"],
        outputs: ["索引发布决策"],
        observability: ["publish_scope"],
      },
    },
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
      status: "error",
      last_error: "源目录缺失",
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
  getArchivePolicyConfig: (...args: unknown[]) => getArchivePolicyConfigMock(...args),
  updateArchivePolicyConfig: (...args: unknown[]) => updateArchivePolicyConfigMock(...args),
}));

vi.mock("../lib/archiveKnowledge", () => ({
  getArchiveDocumentRuntime: (...args: unknown[]) => getArchiveDocumentRuntimeMock(...args),
  subscribeArchiveDocumentRuntime: (...args: unknown[]) => subscribeArchiveDocumentRuntimeMock(...args),
}));

vi.mock("../features/p1/api/p1RefactorApi", () => ({
  getP1DocumentRuntimeSnapshot: (...args: unknown[]) => getP1DocumentRuntimeSnapshotMock(...args),
  subscribeP1DocumentRuntimeSnapshot: (...args: unknown[]) => subscribeP1DocumentRuntimeSnapshotMock(...args),
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
      status: "error",
      last_error: "源目录缺失",
    }),
  ];
  archiveContextValue.error = null;
  archiveContextValue.loading = false;

  refreshArchivesMock.mockReset();
  setActiveArchiveIdMock.mockReset();
  createKnowledgeArchiveMock.mockReset();
  extractKnowledgeArchiveMock.mockReset();
  getArchivePolicyConfigMock.mockReset();
  updateArchivePolicyConfigMock.mockReset();
  getArchiveDocumentRuntimeMock.mockReset();
  subscribeArchiveDocumentRuntimeMock.mockReset();
  getP1DocumentRuntimeSnapshotMock.mockReset();
  subscribeP1DocumentRuntimeSnapshotMock.mockReset();

  getArchiveDocumentRuntimeMock.mockResolvedValue({ data: buildRuntimeContract() });
  getP1DocumentRuntimeSnapshotMock.mockResolvedValue(buildP1RuntimeEnvelope());
  getArchivePolicyConfigMock.mockResolvedValue({ data: buildPolicyConfig() });
  updateArchivePolicyConfigMock.mockResolvedValue({ data: buildPolicyConfig() });
  subscribeArchiveDocumentRuntimeMock.mockImplementation(
    (_documentId: string, _archiveId: string, handlers: { onRuntime: (runtime: ArchiveDocumentRuntimeContract) => void }) => {
      handlers.onRuntime(buildRuntimeContract());
      return { close: vi.fn() };
    },
  );
  subscribeP1DocumentRuntimeSnapshotMock.mockImplementation(
    (
      _archiveId: string,
      _documentId: string,
      handlers: { onRuntime: (runtime: DocumentRuntimeSnapshot, envelope: P1ResponseEnvelope<DocumentRuntimeSnapshot>) => void },
    ) => {
      const envelope = buildP1RuntimeEnvelope();
      handlers.onRuntime(envelope.data, envelope);
      return { close: vi.fn() };
    },
  );
});

test("renders overview workspace with archive table", async () => {
  renderPage();

  expect((await screen.findAllByRole("heading", { name: "知识库总览与抽取启动" })).length).toBeGreaterThan(0);
  expect(screen.getByText(/P1 业务知识库控制台/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建知识库" })).toBeInTheDocument();
  expect(screen.getAllByText("知识库一").length).toBeGreaterThan(0);
  expect(screen.getAllByText("知识库二").length).toBeGreaterThan(0);
});

test("shows retry action when archive list loading fails", async () => {
  archiveContextValue.error = "Network Error";

  renderPage();

  expect(await screen.findByText("知识库列表加载失败")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "重新加载知识库列表" }));
  expect(refreshArchivesMock).toHaveBeenCalledWith("kb-1");
});

test("enters single archive and single document views with runtime stream data", async () => {
  renderPage();

  fireEvent.click((await screen.findAllByRole("button", { name: "进入单知识库" }))[0]);
  expect(await screen.findByRole("heading", { name: /单知识库运行/ })).toBeInTheDocument();
  expect(await screen.findByText("当前运行策略")).toBeInTheDocument();
  expect(screen.getAllByText(/13 阶段抽取蓝图 v3/).length).toBeGreaterThan(0);

  fireEvent.click(screen.getAllByRole("button", { name: "进入单文档" })[0]);

  expect(await screen.findByRole("heading", { name: /单文档实时工作台/ })).toBeInTheDocument();
  expect(await screen.findByText("对象观察窗")).toBeInTheDocument();
  expect(await screen.findByTestId("document-runtime-summary-strip")).toBeInTheDocument();
  expect(await screen.findByTestId("document-graph-control-panel")).toBeInTheDocument();
  expect(subscribeP1DocumentRuntimeSnapshotMock).toHaveBeenCalledWith(
    "kb-1",
    "doc-1",
    expect.objectContaining({
      onRuntime: expect.any(Function),
      onError: expect.any(Function),
    }),
    { intervalMs: 2000, heartbeatMs: 15000 },
  );
  expect((await screen.findAllByText(/已连接 Stream/)).length).toBeGreaterThan(0);
  expect(screen.getAllByText("质量门禁").length).toBeGreaterThan(0);
  expect(screen.getByText("运行模式")).toBeInTheDocument();
  expect(screen.getByText("策略版本")).toBeInTheDocument();
  expect(screen.getByText("运行策略快照")).toBeInTheDocument();
  expect(screen.getAllByText("持久化运行态").length).toBeGreaterThan(0);
  expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
});

test("falls back to snapshot polling when runtime stream fails before first payload", async () => {
  subscribeP1DocumentRuntimeSnapshotMock.mockImplementation(
    (_archiveId: string, _documentId: string, handlers: { onError: (error: Event | Error) => void }) => {
      handlers.onError(new Event("error"));
      return { close: vi.fn() };
    },
  );
  getP1DocumentRuntimeSnapshotMock.mockResolvedValue(buildP1RuntimeEnvelope());

  renderPage();

  fireEvent.click((await screen.findAllByRole("button", { name: "进入单知识库" }))[0]);
  fireEvent.click(screen.getAllByRole("button", { name: "进入单文档" })[0]);

  await waitFor(() => {
    expect(getP1DocumentRuntimeSnapshotMock).toHaveBeenCalledWith("kb-1", "doc-1");
  });
  expect((await screen.findAllByText(/已回退轮询/)).length).toBeGreaterThan(0);
  expect(await screen.findByTestId("document-graph-control-panel")).toBeInTheDocument();
});

test("keeps live current stage pinned while allowing completed-stage snapshot review", async () => {
  const { container } = renderPage();

  fireEvent.click((await screen.findAllByRole("button", { name: "进入单知识库" }))[0]);
  fireEvent.click(screen.getAllByRole("button", { name: "进入单文档" })[0]);

  await screen.findByTestId("document-runtime-summary-strip");

  const pendingStageButton = container.querySelector<HTMLButtonElement>('[data-stage-id="publication_candidate"]');
  const currentStageButton = container.querySelector<HTMLButtonElement>('[data-stage-id="quality_gate"]');
  const completedStageButton = container.querySelector<HTMLButtonElement>('[data-stage-id="unified_document"]');

  expect(pendingStageButton).not.toBeNull();
  expect(currentStageButton).not.toBeNull();
  expect(completedStageButton).not.toBeNull();
  expect(pendingStageButton?.disabled).toBe(true);
  expect(currentStageButton?.dataset.stageView).toBe("live");

  fireEvent.click(completedStageButton!);

  expect(currentStageButton?.dataset.stageView).toBe("live");
  expect(completedStageButton?.dataset.stageView).toBe("snapshot");
  expect(screen.getByTestId("runtime-live-current-stage").textContent).toContain("quality_gate");
  expect(screen.getByTestId("runtime-inspected-stage").textContent).toContain("unified_document");
});

test.skip("opens policy view from overview", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "策略与配置" }));
  expect(await screen.findByRole("heading", { name: "规则与质量工作台" })).toBeInTheDocument();
  expect(screen.getByText("知识抽取蓝图 v1")).toBeInTheDocument();
  expect(screen.getByText("内容质量策略 v1")).toBeInTheDocument();
});

test.skip("opens stage-based policy workbench from overview", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "策略/质量" }));
  expect(await screen.findByRole("heading", { name: "策略与配置工作台" })).toBeInTheDocument();
  expect(screen.getByText("13 阶段策略导航")).toBeInTheDocument();
  expect(screen.getByText("这是一张抽取前 / 抽取中的策略编排台")).toBeInTheDocument();
  expect(screen.getAllByText("单文档抽取过程").length).toBeGreaterThan(0);
  expect(screen.getByText("当前阶段配置 · 素材接入")).toBeInTheDocument();
});

test.skip("opens configured stage workbench from overview", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "策略与配置" }));
  expect(await screen.findByRole("heading", { name: "策略与配置工作台" })).toBeInTheDocument();
  expect(screen.getByText("13 阶段策略导航")).toBeInTheDocument();
  expect(screen.getByText("这是一张抽取前 / 抽取中的策略编排台")).toBeInTheDocument();
  expect(screen.getByText("单文档抽取过程")).toBeInTheDocument();
  expect(screen.getByText("当前阶段配置 · 素材接入")).toBeInTheDocument();
});

test.skip("opens policy configuration workspace from overview", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "策略与配置" }));
  expect(await screen.findByRole("heading", { name: "策略与配置工作台" })).toBeInTheDocument();
  expect(screen.getByText("13 阶段策略导航")).toBeInTheDocument();
  expect(screen.getByText("当前阶段配置 · 素材接入")).toBeInTheDocument();
  expect(screen.getByText("比较策略版本")).toBeInTheDocument();
});

test("creates archive through modal", async () => {
  createKnowledgeArchiveMock.mockResolvedValue({ data: buildArchive({ archive_id: "kb-3", name: "知识库三" }) });
  refreshArchivesMock.mockResolvedValue(undefined);

  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "新建知识库" }));
  const dialog = await screen.findByRole("dialog");
  const inputs = within(dialog).getAllByRole("textbox");

  fireEvent.change(inputs[0], { target: { value: "kb-3" } });
  fireEvent.change(inputs[1], { target: { value: "知识库三" } });
  fireEvent.change(inputs[2], { target: { value: "/tmp/kb-3" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "创建知识库" }));

  await waitFor(() => {
    expect(createKnowledgeArchiveMock).toHaveBeenCalledWith({
      archive_id: "kb-3",
      name: "知识库三",
      source_dir: "/tmp/kb-3",
    });
    expect(refreshArchivesMock).toHaveBeenCalledWith("kb-3");
  });
});

test("runs extract action and switches to archive view immediately", async () => {
  extractKnowledgeArchiveMock.mockResolvedValue({ data: buildArchive() });
  refreshArchivesMock.mockResolvedValue(undefined);

  renderPage();

  fireEvent.click((await screen.findAllByRole("button", { name: "立即抽取" }))[0]);
  const dialog = await screen.findByRole("dialog", { name: "启动抽取并冻结策略快照" });
  fireEvent.click(within(dialog).getByRole("button", { name: "确认并启动抽取" }));

  await waitFor(() => {
    expect(extractKnowledgeArchiveMock).toHaveBeenCalledWith("kb-1");
    expect(refreshArchivesMock).toHaveBeenCalledWith("kb-1");
  });
  expect(await screen.findByRole("heading", { name: /单知识库运行/ })).toBeInTheDocument();
  expect(await screen.findByText("当前运行策略")).toBeInTheDocument();
});
