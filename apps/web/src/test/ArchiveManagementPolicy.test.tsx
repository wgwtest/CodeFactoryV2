import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";

import { ArchiveManagementPage } from "../pages/ArchiveManagementPage";
import { RuleContractEditorPage } from "../pages/P1PrototypeWorkflowPages";
import type { ArchivePolicyConfig, KnowledgeArchive } from "../lib/api";

const refreshArchivesMock = vi.fn();
const setActiveArchiveIdMock = vi.fn();
const createKnowledgeArchiveMock = vi.fn();
const extractKnowledgeArchiveMock = vi.fn();
const getArchivePolicyConfigMock = vi.fn();
const updateArchivePolicyConfigMock = vi.fn();
const getArchiveDocumentRuntimeMock = vi.fn();
const subscribeArchiveDocumentRuntimeMock = vi.fn();

function buildArchive(overrides: Partial<KnowledgeArchive> = {}): KnowledgeArchive {
  return {
    archive_id: "kb-1",
    name: "知识库一",
    source_dir: "/tmp/kb-1",
    extract_root: "/tmp/extract/kb-1",
    is_active: true,
    status: "ready",
    last_built_at: "2026-04-22T09:00:00.000Z",
    last_error: null,
    summary: { archive_id: "kb-1", document_count: 3, entity_count: 12, event_count: 0, process_count: 2 },
    artifacts: { base_exists: true, curated_exists: false, publication_exists: false },
    build_state: null,
    ...overrides,
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
        inputs: ["原始文件流", "来源标记"],
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

const archiveContextValue = {
  activeArchiveId: "kb-1",
  activeArchive: buildArchive(),
  archives: [buildArchive()],
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

beforeEach(() => {
  archiveContextValue.activeArchiveId = "kb-1";
  archiveContextValue.activeArchive = buildArchive();
  archiveContextValue.archives = [buildArchive()];
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

  getArchivePolicyConfigMock.mockResolvedValue({ data: buildPolicyConfig() });
  updateArchivePolicyConfigMock.mockResolvedValue({ data: buildPolicyConfig() });
});

test("loads policy config from backend and shows editable stage form", async () => {
  render(<ArchiveManagementPage />);

  fireEvent.click(await screen.findByRole("button", { name: "策略与配置" }));

  expect(await screen.findByRole("heading", { name: "策略与配置工作台" })).toBeInTheDocument();
  expect(getArchivePolicyConfigMock).toHaveBeenCalledWith("kb-1");
  expect(screen.getByText("13 阶段策略导航")).toBeInTheDocument();
  expect(screen.getByText("蓝图元信息")).toBeInTheDocument();
  expect(screen.getByDisplayValue("13 阶段抽取蓝图 v1")).toBeInTheDocument();
  expect(screen.getByText("当前阶段配置 · 素材接入")).toBeInTheDocument();
});

test("saves edited policy config back to backend contract", async () => {
  render(<ArchiveManagementPage />);

  fireEvent.click(await screen.findByRole("button", { name: "策略与配置" }));
  expect(await screen.findByRole("heading", { name: "策略与配置工作台" })).toBeInTheDocument();

  fireEvent.change(screen.getByDisplayValue("13 阶段抽取蓝图 v1"), {
    target: { value: "13 阶段抽取蓝图 v2" },
  });
  fireEvent.change(screen.getByDisplayValue("判断文档是否可以进入正式抽取链路。"), {
    target: { value: "先完成接入质量判断，再决定是否进入正式抽取链路。" },
  });

  fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));

  await waitFor(() => {
    expect(updateArchivePolicyConfigMock).toHaveBeenCalledWith(
      "kb-1",
      expect.objectContaining({
        version_label: "13 阶段抽取蓝图 v2",
        scope_label: "单文档抽取过程",
        ai_autoadapt_enabled: true,
        stage_order: expect.arrayContaining(["asset_intake", "indexes_snapshots_apis"]),
        stages: expect.objectContaining({
          asset_intake: expect.objectContaining({
            objective: "先完成接入质量判断，再决定是否进入正式抽取链路。",
          }),
        }),
      }),
    );
  });
});

test("saves rule field contract as a new policy package version", async () => {
  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <RuleContractEditorPage />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "规则字段配置与合同编辑" })).toBeInTheDocument();
  expect(screen.getByText("input_schema JSON 草稿")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "保存为新版本" }));

  await waitFor(() => {
    expect(updateArchivePolicyConfigMock).toHaveBeenCalledWith(
      "kb-1",
      expect.objectContaining({
        policy_package_version_status: "draft",
        stages: expect.objectContaining({
          asset_intake: expect.objectContaining({
            rules: expect.arrayContaining([
              expect.objectContaining({
                key: "asset-1",
                rule_version: "r1.1",
                input_schema: expect.arrayContaining([expect.objectContaining({ field_name: "input_hash" })]),
                output_schema: expect.arrayContaining([expect.objectContaining({ field_name: "affected_object_ids" })]),
                trace_fields: expect.arrayContaining(["rule_id", "rule_version", "input_hash", "output_hash"]),
              }),
            ]),
          }),
        }),
      }),
    );
  });
});
