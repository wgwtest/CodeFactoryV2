import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  List,
  Modal,
  Progress,
  Radio,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { Link } from "react-router-dom";

import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { useArchiveContext } from "../context/ArchiveContext";
import { getArchiveDocuments, getArchiveDocumentRuntime, getArchivePublication } from "../lib/archiveKnowledge";
import { getArchivePolicyConfig, listArchiveIncrementalRebuildTasks, updateArchivePolicyConfig } from "../lib/archives";
import type {
  ArchiveDocumentRuntimeContract,
  ArchiveDocumentRuntimeGraphNode,
  ArchiveDocumentRuntimeStageSnapshot,
  ArchiveKnowledgeDocument,
  ArchivePolicyAction,
  ArchivePolicyConfig,
  ArchiveIncrementalRebuildTask,
  ArchivePublicationOverview,
  ArchiveRuleInputFieldContract,
  ArchiveRuleOutputFieldContract,
  ArchiveStagePolicyConfig,
  ArchiveStagePolicyRule,
  UpdateArchivePolicyConfigInput,
} from "../lib/api";

const stageFallback: ArchiveStagePolicyConfig[] = [
  buildFallbackStage("intake_validation", "接入校验", "摄取与统一", 8),
  buildFallbackStage("document_segmentation", "文档分片", "摄取与统一", 14),
  buildFallbackStage("ocr_recognition", "OCR识别", "摄取与统一", 21),
  buildFallbackStage("layout_parsing", "版面解析", "摄取与统一", 18),
  buildFallbackStage("field_normalization", "字段标准化", "证据与知识生成", 22),
  buildFallbackStage("rule_cleaning", "规则清洗", "证据与知识生成", 26),
  buildFallbackStage("entity_extraction", "实体抽取", "证据与知识生成", 34),
  buildFallbackStage("relation_extraction", "关系抽取", "证据与知识生成", 28),
  buildFallbackStage("candidate_merge", "候选合并", "证据与知识生成", 21),
  buildFallbackStage("quality_gate", "质量校验", "规范化与发布", 24),
  buildFallbackStage("publication_candidate", "发布候选", "规范化与发布", 12),
  buildFallbackStage("governance_confirmation", "治理确认", "规范化与发布", 9),
  buildFallbackStage("archive_mapping", "入仓映射", "规范化与发布", 5),
];

const actionMeta: Record<ArchivePolicyAction, { label: string; color: string }> = {
  auto_pass: { label: "自动放行", color: "success" },
  warn_continue: { label: "警告继续", color: "warning" },
  manual_review: { label: "治理确认", color: "purple" },
  block_return: { label: "阻断返回", color: "error" },
  defer_publish: { label: "延迟发布", color: "processing" },
};

const prototypeStageLabels = [
  "接入校验",
  "文档分片",
  "OCR识别",
  "版面解析",
  "字段标准化",
  "规则清洗",
  "实体抽取",
  "关系抽取",
  "候选合并",
  "质量校验",
  "发布候选",
  "治理确认",
  "入仓映射",
];

const requiredRuleTraceFields = [
  "rule_id",
  "rule_version",
  "stage_id",
  "snapshot_id",
  "input_hash",
  "output_hash",
  "affected_object_ids",
];

function getPrototypeStageLabel(stage: ArchiveStagePolicyConfig, index: number) {
  return prototypeStageLabels[index] ?? stage.label;
}

function buildFallbackStage(stageId: string, label: string, group: string, ruleCount: number): ArchiveStagePolicyConfig {
  return {
    stage_id: stageId,
    label,
    group,
    enabled: true,
    ai_mode: "按文件类型与知识类型自动适配",
    default_action: stageId === "quality_gate" ? "warn_continue" : "auto_pass",
    objective: `完成“${label}”阶段的输入校验、规则筛选、输出落点和可追踪记录。`,
    inputs: ["统一文档对象", "阶段上游输出", "策略快照"],
    ai_adaptation: "AI 只负责推荐策略组合与阈值建议，最终执行以冻结规则合同为准。",
    rules: Array.from({ length: Math.min(6, Math.max(2, Math.ceil(ruleCount / 8))) }, (_, index) => ({
      key: `RL-${stageId.toUpperCase().slice(0, 4)}-${String(index + 1).padStart(3, "0")}`,
      name: `${label}规则 ${index + 1}`,
      meaning: index % 2 === 0 ? "校验输入完整性并保留可追溯锚点" : "根据策略阈值分流低置信候选",
      threshold: index % 2 === 0 ? "coverage >= 0.85" : "confidence >= 0.80",
      action: index === 1 ? "warn_continue" : "auto_pass",
    })),
    branches: ["通过", "警告继续", "阻断返回"],
    outputs: ["阶段候选对象", "规则执行记录", "影响对象索引"],
    observability: ["input_hash", "output_hash", "affected_object_ids", "trace_fields"],
  };
}

function usePolicyWorkbench() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [config, setConfig] = useState<ArchivePolicyConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPolicy() {
      if (!activeArchiveId) {
        setConfig(null);
        return;
      }

      try {
        setLoading(true);
        const response = await getArchivePolicyConfig(activeArchiveId);
        if (cancelled) return;
        setConfig(response.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setConfig(null);
          setError(loadError instanceof Error ? loadError.message : "策略配置加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadPolicy();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  const stages = useMemo(() => normalizePolicyStages(config), [config]);

  return { activeArchive, activeArchiveId, config, setConfig, stages, loading, error };
}

function normalizePolicyStages(config: ArchivePolicyConfig | null) {
  if (!config) {
    return stageFallback;
  }

  const ordered = config.stage_order.map((stageId) => config.stages[stageId]).filter(Boolean);
  return ordered.length ? ordered : Object.values(config.stages);
}

function getStageByIndex(stages: ArchiveStagePolicyConfig[], index: number) {
  return stages[Math.min(index, Math.max(0, stages.length - 1))] ?? stageFallback[index] ?? stageFallback[0];
}

function getRuleContractDefaultStage(stages: ArchiveStagePolicyConfig[]) {
  const preferred = getStageByIndex(stages, 5);
  return preferred.rules.length ? preferred : stages.find((stage) => stage.rules.length > 0) ?? preferred;
}

function getStagePolicyDefaultStage(stages: ArchiveStagePolicyConfig[]) {
  return stages.find((stage) => stage.rules.length > 0) ?? getStageByIndex(stages, 5);
}

function formatAction(action: ArchivePolicyAction) {
  return actionMeta[action]?.label ?? action;
}

function actionColor(action: ArchivePolicyAction) {
  return actionMeta[action]?.color ?? "default";
}

function countRules(stages: ArchiveStagePolicyConfig[]) {
  return stages.reduce((total, stage) => total + stage.rules.length, 0);
}

function getRuleId(rule: ArchiveStagePolicyRule) {
  return rule.rule_id ?? rule.key;
}

function getRuleVersion(rule: ArchiveStagePolicyRule) {
  return rule.rule_version ?? "r1.0";
}

function getRuleEffectKind(rule: ArchiveStagePolicyRule) {
  return rule.effect_kind ?? "filter";
}

function isStructuralEffectKind(effectKind: string | null | undefined) {
  return ["merge", "split", "block", "publish_candidate"].includes(effectKind ?? "");
}

function getRuleTraceFields(rule: ArchiveStagePolicyRule) {
  return rule.trace_fields?.length ? rule.trace_fields : requiredRuleTraceFields;
}

function getRuleInputSchema(rule: ArchiveStagePolicyRule) {
  return rule.input_schema?.length
    ? rule.input_schema
    : [
        {
          field_name: "candidate_id",
          source_artifact: "candidate_knowledge",
          field_type: "string",
          required: true,
          include_in_input_hash: true,
          validation: "non_empty",
          example: "CND-001",
          business_meaning: "候选对象标识",
        },
        {
          field_name: "input_hash",
          source_artifact: "runtime_snapshot",
          field_type: "string",
          required: true,
          include_in_input_hash: true,
          validation: "sha256",
          example: "inp_b34e7d...",
          business_meaning: "影响面重算定位",
        },
      ];
}

function getRuleOutputSchema(rule: ArchiveStagePolicyRule) {
  return rule.output_schema?.length
    ? rule.output_schema
    : [
        {
          field_name: "affected_object_ids",
          target_artifact: "impact_set",
          field_type: "string[]",
          producer: "rule_engine",
          include_in_output_hash: true,
          write_to_runtime: true,
          write_to_audit: true,
          used_for_impact: true,
          example: "[OBJ-M-204]",
          business_meaning: "受影响对象",
        },
        {
          field_name: "output_hash",
          target_artifact: "runtime_snapshot",
          field_type: "string",
          producer: "rule_engine",
          include_in_output_hash: true,
          write_to_runtime: true,
          write_to_audit: true,
          used_for_impact: false,
          example: "out_a91e...",
          business_meaning: "输出摘要",
        },
      ];
}

function toJsonDraft(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function parseJsonDraft<T>(draft: string, label: string) {
  try {
    return { value: JSON.parse(draft) as T, error: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : "无法解析 JSON";
    return { value: null, error: `${label} JSON 格式错误：${message}` };
  }
}

function validateRuleContractDraft(
  inputSchema: ArchiveRuleInputFieldContract[],
  outputSchema: ArchiveRuleOutputFieldContract[],
  traceFields: string[],
) {
  const inputFields = new Set(inputSchema.map((field) => field.field_name));
  const outputFields = new Set(outputSchema.map((field) => field.field_name));
  const traceFieldSet = new Set(traceFields);
  const errors: string[] = [];

  if (!inputFields.has("input_hash")) errors.push("input_schema 缺少 input_hash");
  if (!outputFields.has("output_hash")) errors.push("output_schema 缺少 output_hash");
  if (!outputFields.has("affected_object_ids")) errors.push("output_schema 缺少 affected_object_ids");
  requiredRuleTraceFields.forEach((field) => {
    if (!traceFieldSet.has(field)) errors.push(`trace_fields 缺少 ${field}`);
  });

  return errors;
}

function bumpRuleVersion(version: string | null | undefined) {
  const source = version || "r1.0";
  const match = source.match(/^r(\d+)(?:\.(\d+))?$/);
  if (!match) return `${source}.1`;
  const major = Number(match[1]);
  const minor = Number(match[2] ?? "0") + 1;
  return `r${major}.${minor}`;
}

function bumpTrailingPolicyVersion(value: string | null | undefined, fallback: string) {
  const source = value || fallback;
  const match = source.match(/v(\d+)(?!.*v\d+)/);
  if (!match || match.index === undefined) return `${source}-next`;
  const next = `v${Number(match[1]) + 1}`;
  return `${source.slice(0, match.index)}${next}${source.slice(match.index + match[0].length)}`;
}

function buildPolicyConfigPayload(config: ArchivePolicyConfig): UpdateArchivePolicyConfigInput {
  return {
    policy_package_id: config.policy_package_id,
    policy_package_name: config.policy_package_name,
    policy_package_version_id: config.policy_package_version_id,
    policy_package_version_status: config.policy_package_version_status,
    policy_package_version_hash: config.policy_package_version_hash,
    version_label: config.version_label,
    scope_label: config.scope_label,
    ai_autoadapt_enabled: config.ai_autoadapt_enabled,
    stage_order: config.stage_order,
    stages: config.stages,
  };
}

function PageLinkButton({ to, children }: { to: string; children: string }) {
  return (
    <Link to={to}>
      <Button>{children}</Button>
    </Link>
  );
}

function StageRail({
  stages,
  selectedStageId,
  onSelect,
}: {
  stages: ArchiveStagePolicyConfig[];
  selectedStageId: string;
  onSelect: (stageId: string) => void;
}) {
  return (
    <div className="p1-policy-stage-list">
      {stages.map((stage, index) => (
        <button
          key={stage.stage_id}
          className={`p1-policy-stage-card${stage.stage_id === selectedStageId ? " is-active" : ""}`}
          type="button"
          onClick={() => onSelect(stage.stage_id)}
        >
          <span className="p1-stage-index">{index + 1}</span>
          <span>
            <strong>{getPrototypeStageLabel(stage, index)}</strong>
            <small>{stage.enabled ? "已启用" : "未启用"} · 规则 {stage.rules.length}</small>
          </span>
          <Tag color={stage.enabled ? "success" : "default"}>{stage.enabled ? "启用" : "关闭"}</Tag>
        </button>
      ))}
    </div>
  );
}

function RuleTable({ rules }: { rules: ArchiveStagePolicyRule[] }) {
  return (
    <Table
      rowKey="key"
      size="small"
      pagination={false}
      dataSource={rules}
      columns={[
        { title: "规则名称", dataIndex: "name" },
        { title: "适用条件 / 阈值", dataIndex: "threshold" },
        { title: "动作", render: (_, record: ArchiveStagePolicyRule) => <Tag color={actionColor(record.action)}>{formatAction(record.action)}</Tag> },
        { title: "含义", dataIndex: "meaning" },
        {
          title: "操作",
          render: (_, record: ArchiveStagePolicyRule) => (
            <Space size={4} wrap>
              <Button type="link" size="small" href="/policies/rule-contract">编辑 I/O 合同</Button>
              <Button type="link" size="small" href="/policies/diff">比较版本</Button>
              <Button type="link" size="small" title={`查看${record.name}命中历史`}>查看命中历史</Button>
            </Space>
          ),
        },
      ]}
    />
  );
}

export function StrategyLibraryPage() {
  const { activeArchive, config, stages, loading, error } = usePolicyWorkbench();
  const [usePolicyOpen, setUsePolicyOpen] = useState(false);
  const totalRules = countRules(stages);
  const currentPackage = config?.scope_label ?? "合同通用抽取";
  const templates = [
    { name: currentPackage, version: config?.version_label ?? "v3.12", coverage: `${stages.length}/13`, rules: totalRules, status: "已发布" },
    { name: "合同增强抽取", version: "v3.15", coverage: "13/13", rules: totalRules + 38, status: "推荐模板" },
    { name: "需求文档结构抽取", version: "v2.08", coverage: "11/13", rules: Math.max(80, totalRules - 70), status: "草稿" },
    { name: "FAQ 轻量抽取", version: "v1.05", coverage: "8/13", rules: 86, status: "模板" },
  ];

  return (
    <ValidationWorkspace
      title="策略库与策略模板管理"
      description="复用、复制、版本化管理 13 阶段知识抽取策略；采集新文件时可以选择既有规则包，也可以派生新策略包。"
      actions={
        <Space wrap>
          <Button type="primary">新建策略包</Button>
          <Button>从现有策略复制</Button>
          <Button>导入策略模板</Button>
          <PageLinkButton to="/policies/diff">查看策略差异</PageLinkButton>
          <PageLinkButton to="/policies/stages">进入阶段配置</PageLinkButton>
        </Space>
      }
      stats={[
        { title: "策略包总数", value: 128 },
        { title: "推荐模板", value: 26 },
        { title: "已发布策略", value: 78 },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="后端策略合同暂不可用，当前展示原型级默认策略" description={error} /> : null}
        <div className="p1-prototype-grid">
          <Card className="p1-soft-card" title="策略包分类">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <div className="p1-filter-group">
                <Typography.Text strong>业务域 / 知识内容类型</Typography.Text>
                <div className="p1-filter-pill-row">
                  <span className="p1-filter-pill">行业规范 18</span>
                  <span className="p1-filter-pill">需求文档 22</span>
                  <span className="p1-filter-pill is-active">合同条款 28</span>
                  <span className="p1-filter-pill">业务流程 14</span>
                  <span className="p1-filter-pill">制度文件 16</span>
                </div>
              </div>
              <div className="p1-filter-group">
                <Typography.Text strong>文件类型</Typography.Text>
                <div className="p1-filter-pill-row">
                  <span className="p1-filter-pill is-active">PDF 56</span>
                  <span className="p1-filter-pill">DOCX 48</span>
                  <span className="p1-filter-pill">XLSX 21</span>
                  <span className="p1-filter-pill">PPTX 9</span>
                </div>
              </div>
              <Alert type="info" showIcon message="资产说明" description="策略包包含阶段配置、规则、阈值、输入输出合同和历史运行快照。" />
            </Space>
          </Card>

          <Card className="p1-soft-card" title="策略包资产库" loading={loading}>
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Input.Search placeholder="搜索策略包名称 / 维护人 / 适用范围" />
              <div className="p1-strategy-card-list">
                {templates.map((item, index) => (
                  <div key={item.name} className={`p1-strategy-asset-card${index === 0 ? " is-active" : ""}`}>
                    <div>
                      <Typography.Text strong>{item.name}</Typography.Text>
                      <div>
                        <Tag color="blue">合同条款</Tag>
                        <Tag>{item.version}</Tag>
                        <Tag color={item.status === "已发布" ? "success" : item.status === "推荐模板" ? "orange" : "default"}>{item.status}</Tag>
                      </div>
                    </div>
                    <div className="p1-strategy-metrics">
                      <span>阶段覆盖 <strong>{item.coverage}</strong></span>
                      <span>规则数 <strong>{item.rules}</strong></span>
                      <span>最近使用 <strong>{126 - index * 18} 次</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </Space>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="策略包详情">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <Typography.Title level={3}>{currentPackage}</Typography.Title>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="当前知识库">{activeArchive?.name ?? "未选择"}</Descriptions.Item>
                <Descriptions.Item label="策略版本">{config?.version_label ?? "v3.12"}</Descriptions.Item>
                <Descriptions.Item label="阶段覆盖">{stages.length}/13</Descriptions.Item>
                <Descriptions.Item label="规则总数">{totalRules}</Descriptions.Item>
                <Descriptions.Item label="AI 自动适配">{config?.ai_autoadapt_enabled ? "已启用" : "未启用"}</Descriptions.Item>
                <Descriptions.Item label="维护组">策略组-A</Descriptions.Item>
              </Descriptions>
              <Alert type="warning" showIcon message="新版规则可能触发增量重算" description="规则包变更不会自动改写已正式入库知识，需要先生成影响面并执行增量重算。" />
              <div className="p1-stage-track">
                {stages.slice(0, 13).map((stage, index) => (
                  <div key={stage.stage_id} className={`p1-stage-step${stage.enabled ? " is-done" : " is-pending"}`}>
                    <span className="p1-stage-index">{index + 1}</span>
                    <span className="p1-stage-label">{getPrototypeStageLabel(stage, index)}</span>
                  </div>
                ))}
              </div>
              <Space wrap>
                <Button type="primary" onClick={() => setUsePolicyOpen(true)}>使用此策略</Button>
                <Button>复制改造</Button>
                <Button>设为知识库默认策略</Button>
                <Link to="/policies/diff"><Button>查看版本差异</Button></Link>
                <Link to="/policies/impact"><Button>生成影响面</Button></Link>
              </Space>
            </Space>
          </Card>
        </div>
        <Modal
          open={usePolicyOpen}
          title="使用策略包并准备冻结运行快照"
          okText="确认选择"
          cancelText="取消"
          onCancel={() => setUsePolicyOpen(false)}
          onOk={() => setUsePolicyOpen(false)}
          destroyOnHidden
        >
          <Space direction="vertical" size={14} style={{ display: "flex" }}>
            <Alert
              type="info"
              showIcon
              message="策略选择只影响后续抽取任务"
              description="历史运行仍绑定旧快照；真正启动抽取时会再次确认策略包版本并冻结 snapshot_id。"
            />
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="目标知识库">{activeArchive?.name ?? "未选择"}</Descriptions.Item>
              <Descriptions.Item label="策略包">{currentPackage}</Descriptions.Item>
              <Descriptions.Item label="策略包版本">{config?.version_label ?? "v3.12"}</Descriptions.Item>
              <Descriptions.Item label="文档范围">当前知识库全部待抽取文档 / 可在启动前调整</Descriptions.Item>
              <Descriptions.Item label="API 状态">策略库枚举接口暂缺，当前使用 policy-config 真实配置 + 模板 mock fallback</Descriptions.Item>
            </Descriptions>
          </Space>
        </Modal>
      </Space>
    </ValidationWorkspace>
  );
}

export function StagePolicyConfigPage() {
  const { config, stages, loading, error } = usePolicyWorkbench();
  const initialStage = getStagePolicyDefaultStage(stages).stage_id;
  const [selectedStageId, setSelectedStageId] = useState(initialStage);
  const selectedStage = stages.find((stage) => stage.stage_id === selectedStageId) ?? getStagePolicyDefaultStage(stages);
  const selectedStageIndex = Math.max(0, stages.findIndex((stage) => stage.stage_id === selectedStage.stage_id));
  const selectedStageLabel = getPrototypeStageLabel(selectedStage, selectedStageIndex);
  const selectedStageRules = selectedStage.rules.length
    ? selectedStage.rules
    : buildFallbackStage(selectedStage.stage_id, selectedStage.label, selectedStage.group, selectedStageIndex + 1).rules;

  useEffect(() => {
    if (!stages.some((stage) => stage.stage_id === selectedStageId)) {
      setSelectedStageId(getStagePolicyDefaultStage(stages).stage_id);
    }
  }, [selectedStageId, stages]);

  return (
    <ValidationWorkspace
      title="阶段策略配置"
      description="按 13 阶段配置知识抽取策略；抽取启动时会冻结该策略包版本作为运行快照，后续规则调整需生成影响面再增量重算。"
      actions={
        <Space wrap>
          <PageLinkButton to="/policies">返回策略库</PageLinkButton>
          <Button>另存为新策略包</Button>
          <Button type="primary">保存为新版本</Button>
          <Button>发布模板</Button>
        </Space>
      }
      stats={[
        { title: "当前策略包", value: config?.scope_label ?? "合同通用抽取" },
        { title: "策略版本", value: config?.version_label ?? "v3.12" },
        { title: "规则总数", value: countRules(stages) },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="策略合同加载失败，当前展示默认合同原型" description={error} /> : null}
        <div className="p1-prototype-grid">
          <Card className="p1-soft-card" title="13 阶段导航" loading={loading}>
            <StageRail stages={stages} selectedStageId={selectedStage.stage_id} onSelect={setSelectedStageId} />
          </Card>

          <Card className="p1-soft-card" title={`当前阶段配置：${selectedStageLabel}`}>
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <div className="p1-config-two-column">
                <label>
                  <span>阶段目标</span>
                  <Input.TextArea rows={4} defaultValue={selectedStage.objective} />
                </label>
                <label>
                  <span>AI 自动适配策略</span>
                  <Radio.Group defaultValue="auto">
                    <Space direction="vertical">
                      <Radio value="auto">依据文件类型 + 知识类型自动选择规则模板</Radio>
                      <Radio value="fixed">仅使用固定规则集</Radio>
                      <Radio value="threshold">允许 AI 推荐阈值，保存前人工确认</Radio>
                    </Space>
                  </Radio.Group>
                </label>
              </div>
              <div className="p1-config-two-column">
                <label>
                  <span>允许输入产物</span>
                  <Select mode="tags" style={{ width: "100%" }} defaultValue={selectedStage.inputs} />
                </label>
                <label>
                  <span>期望输出产物</span>
                  <Select mode="tags" style={{ width: "100%" }} defaultValue={selectedStage.outputs} />
                </label>
              </div>
              <div className="p1-config-two-column">
                <label>
                  <span>默认动作</span>
                  <Select
                    style={{ width: "100%" }}
                    defaultValue={selectedStage.default_action}
                    options={Object.entries(actionMeta).map(([value, meta]) => ({ value, label: meta.label }))}
                  />
                </label>
                <label>
                  <span>观测字段</span>
                  <Select mode="tags" style={{ width: "100%" }} defaultValue={selectedStage.observability} />
                </label>
              </div>
              <RuleTable rules={selectedStageRules} />
            </Space>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="策略预览与影响提示">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
                  <Alert
                type="info"
                showIcon
                message={`当前策略包版本：${config?.scope_label ?? "合同通用抽取"} / ${config?.version_label ?? "v3.12"}`}
                description={`当前编辑阶段：${selectedStageLabel}，保存后不会覆盖正在运行的抽取快照。`}
              />
              <div className="p1-mini-flow">
                <div>{selectedStage.inputs.slice(0, 3).map((item) => <Tag key={item} color="green">{item}</Tag>)}</div>
                <strong>{selectedStageLabel}</strong>
                <div>{selectedStage.outputs.slice(0, 3).map((item) => <Tag key={item} color="blue">{item}</Tag>)}</div>
              </div>
              <Typography.Title level={5}>最可能影响的阶段</Typography.Title>
              <Space wrap>
                <Tag color="blue">实体抽取</Tag>
                <Tag color="blue">关系抽取</Tag>
                <Tag color="orange">候选合并</Tag>
                <Tag color="orange">质量校验</Tag>
              </Space>
              <Alert type="warning" showIcon message="保存后需要计算影响面" description="结构性规则、输入输出合同或阈值变更，会进入规则差异与增量重算流程。" />
            </Space>
          </Card>
        </div>
      </Space>
    </ValidationWorkspace>
  );
}

export function RuleContractEditorPage() {
  const { stages, config, setConfig, error } = usePolicyWorkbench();
  const defaultStage = getRuleContractDefaultStage(stages);
  const [selectedStageId, setSelectedStageId] = useState(defaultStage.stage_id);
  const [selectedRuleKey, setSelectedRuleKey] = useState("");
  const selectedStage = stages.find((stage) => stage.stage_id === selectedStageId) ?? defaultStage;
  const selectedRule =
    selectedStage.rules.find((rule) => rule.key === selectedRuleKey || getRuleId(rule) === selectedRuleKey) ??
    selectedStage.rules[0] ??
    buildFallbackStage("rule", "规则", "规则", 8).rules[0];
  const selectedStageIndex = Math.max(0, stages.findIndex((stage) => stage.stage_id === selectedStage.stage_id));
  const selectedStageLabel = getPrototypeStageLabel(selectedStage, selectedStageIndex);
  const inputSchema = getRuleInputSchema(selectedRule);
  const outputSchema = getRuleOutputSchema(selectedRule);
  const traceFields = getRuleTraceFields(selectedRule);
  const [inputSchemaDraft, setInputSchemaDraft] = useState(() => toJsonDraft(inputSchema));
  const [outputSchemaDraft, setOutputSchemaDraft] = useState(() => toJsonDraft(outputSchema));
  const [parametersDraft, setParametersDraft] = useState(() => toJsonDraft(selectedRule.parameters ?? {}));
  const [traceFieldsDraft, setTraceFieldsDraft] = useState<string[]>(traceFields);
  const [saving, setSaving] = useState(false);
  const [saveFeedback, setSaveFeedback] = useState<{
    type: "success" | "info" | "warning" | "error";
    message: string;
    description?: string;
  } | null>(null);
  const contractErrors = selectedRule.contract_errors ?? [];
  const inputDraftResult = parseJsonDraft<ArchiveRuleInputFieldContract[]>(inputSchemaDraft, "input_schema");
  const outputDraftResult = parseJsonDraft<ArchiveRuleOutputFieldContract[]>(outputSchemaDraft, "output_schema");
  const parameterDraftResult = parseJsonDraft<Record<string, unknown>>(parametersDraft, "parameters");
  const draftInputSchema = Array.isArray(inputDraftResult.value) ? inputDraftResult.value : inputSchema;
  const draftOutputSchema = Array.isArray(outputDraftResult.value) ? outputDraftResult.value : outputSchema;
  const draftContractErrors = [
    inputDraftResult.error,
    outputDraftResult.error,
    parameterDraftResult.error,
    inputDraftResult.value !== null && !Array.isArray(inputDraftResult.value) ? "input_schema 必须是字段数组" : null,
    outputDraftResult.value !== null && !Array.isArray(outputDraftResult.value) ? "output_schema 必须是字段数组" : null,
    parameterDraftResult.value !== null && (Array.isArray(parameterDraftResult.value) || typeof parameterDraftResult.value !== "object")
      ? "parameters 必须是对象"
      : null,
    ...validateRuleContractDraft(draftInputSchema, draftOutputSchema, traceFieldsDraft),
  ].filter(Boolean) as string[];
  const contractOk = draftContractErrors.length === 0;
  const recordPreview = {
    execution_id: `rex-${selectedStage.stage_id}-${getRuleId(selectedRule)}`,
    archive_id: config?.archive_id ?? "--",
    document_id: "DOC-20260506-0172",
    stage_id: selectedStage.stage_id,
    rule_id: getRuleId(selectedRule),
    rule_version: getRuleVersion(selectedRule),
    rule_hash: selectedRule.rule_hash ?? "--",
    input_hash: "inp_runtime",
    output_hash: "out_runtime",
    affected_object_ids: "[OBJ-M-204, CND-1008]",
    decision: getRuleEffectKind(selectedRule),
  };
  const structuralEffect = isStructuralEffectKind(getRuleEffectKind(selectedRule));
  const conditionBlocks = [
    { key: "semantic_similarity", label: "相似度阈值", expression: "semantic_similarity >= 0.92", output: "merged_object_id" },
    { key: "confidence_score", label: "置信度阈值", expression: "confidence_score >= 0.75", output: "decision_reason" },
    { key: "anchor_overlap_count", label: "锚点重叠", expression: "anchor_overlap_count >= 1", output: "affected_object_ids" },
    { key: "object_type", label: "对象类型约束", expression: "object_type in 合同主体、金额条款、义务条款", output: "stale_mark" },
  ];
  const executionRows = Array.from({ length: 5 }, (_, index) => ({
    key: `exec-${index + 1}`,
    input: 18 - index * 2,
    hit: 9 - index,
    output: 7 - Math.floor(index / 2),
    failed: index === 4 ? 1 : 0,
    time: `2026-05-06 10:${26 + index}:1${index}`,
    snapshot: `SNAP-20260506-${172 + index}`,
  }));
  const versionRows = [
    { key: "r6.2", version: "r6.2", change: "新增 anchor_ids 输入字段", action: "归并", impact: "候选对象定位更精确" },
    { key: "r6.3", version: "r6.3", change: "semantic_similarity 从 0.90 调整到 0.92", action: "过滤", impact: "减少误归并" },
    { key: "r6.4", version: getRuleVersion(selectedRule), change: "输出 affected_object_ids 与 output_hash", action: getRuleEffectKind(selectedRule), impact: "可进入影响面重算" },
  ];

  async function saveRuleContract(mode: "draft" | "version") {
    if (!config) {
      setSaveFeedback({ type: "warning", message: "当前没有可保存的策略包配置", description: "请先选择知识库并等待策略配置加载完成。" });
      return;
    }
    if (draftContractErrors.length > 0 || !Array.isArray(inputDraftResult.value) || !Array.isArray(outputDraftResult.value) || !parameterDraftResult.value) {
      setSaveFeedback({ type: "error", message: "合同校验未通过，暂不保存", description: draftContractErrors.join("；") });
      return;
    }

    const currentStageConfig = config.stages[selectedStage.stage_id];
    if (!currentStageConfig) {
      setSaveFeedback({ type: "error", message: "未找到当前阶段配置", description: selectedStage.stage_id });
      return;
    }
    if (!currentStageConfig.rules.some((rule) => rule.key === selectedRule.key || getRuleId(rule) === getRuleId(selectedRule))) {
      setSaveFeedback({ type: "warning", message: "当前阶段还没有可保存的真实规则", description: "请先在阶段策略配置中新增规则，再编辑字段合同。" });
      return;
    }

    const nextRuleVersion = mode === "version" ? bumpRuleVersion(getRuleVersion(selectedRule)) : getRuleVersion(selectedRule);
    const nextRule: ArchiveStagePolicyRule = {
      ...selectedRule,
      rule_version: nextRuleVersion,
      input_schema: inputDraftResult.value,
      output_schema: outputDraftResult.value,
      parameters: parameterDraftResult.value,
      trace_fields: traceFieldsDraft,
      contract_status: "valid",
      contract_errors: [],
      rule_hash: undefined,
    };
    const nextStage: ArchiveStagePolicyConfig = {
      ...currentStageConfig,
      rules: currentStageConfig.rules.map((rule) => (rule.key === selectedRule.key || getRuleId(rule) === getRuleId(selectedRule) ? nextRule : rule)),
    };
    const nextConfig: ArchivePolicyConfig = {
      ...config,
      version_label: mode === "version" ? bumpTrailingPolicyVersion(config.version_label, "13 阶段抽取蓝图 v1") : config.version_label,
      policy_package_version_id:
        mode === "version"
          ? bumpTrailingPolicyVersion(config.policy_package_version_id, `${config.archive_id}:policy:v1`)
          : config.policy_package_version_id,
      policy_package_version_status: "draft",
      policy_package_version_hash: undefined,
      stages: {
        ...config.stages,
        [selectedStage.stage_id]: nextStage,
      },
    };

    try {
      setSaving(true);
      const response = await updateArchivePolicyConfig(config.archive_id, buildPolicyConfigPayload(nextConfig));
      setConfig(response.data);
      setSaveFeedback({
        type: "success",
        message: mode === "version" ? "已保存为新策略包版本" : "已保存合同草稿",
        description: `后端已重新计算策略包 hash：${response.data.policy_package_version_hash ?? "--"}`,
      });
    } catch (saveError) {
      setSaveFeedback({
        type: "error",
        message: "保存规则字段合同失败",
        description: saveError instanceof Error ? saveError.message : "未知错误",
      });
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (!stages.some((stage) => stage.stage_id === selectedStageId)) {
      setSelectedStageId(getRuleContractDefaultStage(stages).stage_id);
    }
  }, [selectedStageId, stages]);

  useEffect(() => {
    if (!selectedStage.rules.some((rule) => rule.key === selectedRuleKey || getRuleId(rule) === selectedRuleKey)) {
      const firstRule = selectedStage.rules[0];
      setSelectedRuleKey(firstRule ? getRuleId(firstRule) : "");
    }
  }, [selectedRuleKey, selectedStage.rules]);

  useEffect(() => {
    setInputSchemaDraft(toJsonDraft(inputSchema));
    setOutputSchemaDraft(toJsonDraft(outputSchema));
    setParametersDraft(toJsonDraft(selectedRule.parameters ?? {}));
    setTraceFieldsDraft(traceFields);
    setSaveFeedback(null);
  }, [selectedStage.stage_id, selectedRule.key, selectedRule.rule_id, selectedRule.rule_version]);

  return (
    <ValidationWorkspace
      title="规则字段配置与合同编辑"
      description="阶段策略配置会冻结到运行快照，本页负责单条规则的字段级输入/输出合同、判断条件、trace fields 与 RuleExecutionRecord 预览。"
      actions={
        <Space wrap>
          <Button
            onClick={() =>
              setSaveFeedback({
                type: draftContractErrors.length ? "error" : "success",
                message: draftContractErrors.length ? "合同校验未通过" : "合同校验通过",
                description: draftContractErrors.length ? draftContractErrors.join("；") : "当前字段合同满足 RuleExecutionRecord 最小闭环。",
              })
            }
          >
            校验合同
          </Button>
          <Button loading={saving} onClick={() => void saveRuleContract("draft")}>保存草稿</Button>
          <Button type="primary" loading={saving} onClick={() => void saveRuleContract("version")}>保存为新版本</Button>
          <Button
            onClick={() =>
              setSaveFeedback({
                type: "info",
                message: "RuleExecutionRecord 已进入运行合同",
                description: "质量门禁阶段会输出真实执行记录；其它阶段当前展示的是按字段合同生成的预览结构。",
              })
            }
          >
            查看执行记录
          </Button>
          <PageLinkButton to="/policies/stages">返回阶段配置</PageLinkButton>
        </Space>
      }
      stats={[
        { title: "rule_id", value: getRuleId(selectedRule) },
        { title: "rule_version", value: getRuleVersion(selectedRule) },
        { title: "effect_kind", value: getRuleEffectKind(selectedRule) },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="当前使用默认合同原型" description={error} /> : null}
        {saveFeedback ? <Alert type={saveFeedback.type} showIcon closable message={saveFeedback.message} description={saveFeedback.description} onClose={() => setSaveFeedback(null)} /> : null}
        <Alert
          type="info"
          showIcon
          message="阶段策略配置负责编排规则，本页负责单条规则的字段级可运行合同。"
          description="已有抽取运行继续使用历史规则快照，新版本只影响后续选择该版本的抽取或增量重算。"
        />
        {structuralEffect ? (
          <Alert
            type="warning"
            showIcon
            message="结构性规则变更会触发影响面计算，保存新版本后不会直接覆盖已有知识。"
            description="正式入库知识不会被规则变更静默覆盖；结构性变更只生成修订候选并等待治理确认。"
          />
        ) : null}
        <Alert
          type={contractOk ? "success" : "error"}
          showIcon
          message={contractOk ? "合同完整性检查通过" : "合同校验未通过"}
          description={
            contractOk
              ? "input_schema、output_schema、input_hash、output_hash、affected_object_ids 与 trace_fields 已具备最小闭环。"
              : (draftContractErrors.length ? draftContractErrors : contractErrors).join("；")
          }
        />
        <div className="p1-prototype-grid is-wide-right">
          <Card className="p1-soft-card" title="规则身份与适用范围">
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Select
                style={{ width: "100%" }}
                value={selectedStage.stage_id}
                onChange={setSelectedStageId}
                options={stages.map((stage, index) => ({ value: stage.stage_id, label: getPrototypeStageLabel(stage, index) }))}
              />
              <Select
                style={{ width: "100%" }}
                value={getRuleId(selectedRule)}
                onChange={setSelectedRuleKey}
                options={selectedStage.rules.map((rule) => ({
                  value: getRuleId(rule),
                  label: `${rule.name} / ${getRuleId(rule)}`,
                }))}
              />
              <Descriptions column={1} size="small">
                <Descriptions.Item label="规则名称">{selectedRule.name}</Descriptions.Item>
                <Descriptions.Item label="规则说明">{selectedRule.meaning || "--"}</Descriptions.Item>
                <Descriptions.Item label="所属策略包">{config?.policy_package_name ?? config?.scope_label ?? "合同通用抽取"}</Descriptions.Item>
                <Descriptions.Item label="策略包版本">{config?.policy_package_version_id ?? config?.version_label ?? "--"}</Descriptions.Item>
                <Descriptions.Item label="适用阶段">{selectedStageLabel}</Descriptions.Item>
                <Descriptions.Item label="阈值 / 条件">{selectedRule.threshold || "--"}</Descriptions.Item>
                <Descriptions.Item label="默认动作">
                  <Tag color={actionColor(selectedRule.action)}>{formatAction(selectedRule.action)}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="规则哈希">{selectedRule.rule_hash ?? "--"}</Descriptions.Item>
              </Descriptions>
              <Card size="small" title="scope_selector">
                <pre className="p1-json-preview">{JSON.stringify(selectedRule.scope_selector ?? {}, null, 2)}</pre>
              </Card>
            </Space>
          </Card>

          <Card className="p1-soft-card" title="字段级合同工程台">
            <Space direction="vertical" size={18} style={{ display: "flex" }}>
              <div className="p1-card-heading">
                <div>
                  <Typography.Title level={5}>输入字段合同 input_schema</Typography.Title>
                  <Typography.Text type="secondary">字段名、来源产物、必填、hash、校验和缺失动作同步进入运行合同。</Typography.Text>
                </div>
                <Space wrap>
                  <Button size="small">新增字段</Button>
                  <Button size="small">导入字段模板</Button>
                  <Button size="small">从上游产物选择字段</Button>
                  <Button size="small">批量设置 hash 字段</Button>
                </Space>
              </div>
              <Table
                size="small"
                pagination={false}
                rowKey="field_name"
                dataSource={draftInputSchema}
                columns={[
                  { title: "字段名", dataIndex: "field_name" },
                  { title: "来源产物", dataIndex: "source_artifact" },
                  { title: "类型", dataIndex: "field_type" },
                  { title: "必填", render: (_value: unknown, record: ArchiveRuleInputFieldContract) => (record.required ? <Tag color="blue">是</Tag> : <Tag>否</Tag>) },
                  { title: "参与 input_hash", render: (_value: unknown, record: ArchiveRuleInputFieldContract) => (record.include_in_input_hash ? "是" : "否") },
                  { title: "校验规则", dataIndex: "validation" },
                  { title: "示例值", dataIndex: "example" },
                  { title: "业务含义", dataIndex: "business_meaning" },
                  { title: "缺失动作", dataIndex: "missing_action" },
                ]}
              />
              <label className="p1-contract-editor-field">
                <span>input_schema JSON 草稿</span>
                <Input.TextArea
                  rows={8}
                  value={inputSchemaDraft}
                  onChange={(event) => setInputSchemaDraft(event.target.value)}
                />
              </label>
              <div className="p1-contract-condition-grid">
                <Card size="small" title="规则参数与判断条件">
                  <Space direction="vertical" size={10} style={{ display: "flex" }}>
                    <Segmented options={["全部满足", "任一满足", "自定义表达式"]} defaultValue="全部满足" />
                    {conditionBlocks.map((condition) => (
                      <button key={condition.key} type="button" className="p1-condition-block">
                        <span>{condition.label}</span>
                        <strong>{condition.expression}</strong>
                        <small>读取 {condition.key} → 影响 {condition.output}</small>
                      </button>
                    ))}
                    <Alert type="info" showIcon message="AI 自动适配：允许 AI 推荐阈值，保存前仍以固定合同为准。" />
                    <label className="p1-contract-editor-field">
                      <span>parameters JSON 草稿</span>
                      <Input.TextArea
                        rows={5}
                        value={parametersDraft}
                        onChange={(event) => setParametersDraft(event.target.value)}
                      />
                    </label>
                  </Space>
                </Card>
                <Card size="small" title="动作映射">
                  <div className="p1-contract-action-map">
                    <span>输入候选集合</span>
                    <strong>{getRuleEffectKind(selectedRule)}</strong>
                    <span>规则条件命中</span>
                    <strong>归并 / 过滤 / 拆分 / 阻断 / 发布候选</strong>
                    <span>输出对象集合</span>
                  </div>
                </Card>
              </div>
              <Typography.Title level={5}>输出字段合同 output_schema</Typography.Title>
              <Table
                size="small"
                pagination={false}
                rowKey="field_name"
                dataSource={draftOutputSchema}
                columns={[
                  { title: "输出字段", dataIndex: "field_name" },
                  { title: "目标产物", dataIndex: "target_artifact" },
                  { title: "类型", dataIndex: "field_type" },
                  { title: "生成方", dataIndex: "producer" },
                  { title: "写入运行态", render: (_value: unknown, record: ArchiveRuleOutputFieldContract) => (record.write_to_runtime ? "是" : "否") },
                  { title: "写入审计", render: (_value: unknown, record: ArchiveRuleOutputFieldContract) => (record.write_to_audit ? "是" : "否") },
                  { title: "用于影响面", render: (_value: unknown, record: ArchiveRuleOutputFieldContract) => (record.used_for_impact ? <Tag color="orange">是</Tag> : "否") },
                  { title: "示例输出", dataIndex: "example" },
                  { title: "业务含义", dataIndex: "business_meaning" },
                ]}
              />
              <label className="p1-contract-editor-field">
                <span>output_schema JSON 草稿</span>
                <Input.TextArea
                  rows={8}
                  value={outputSchemaDraft}
                  onChange={(event) => setOutputSchemaDraft(event.target.value)}
                />
              </label>
            </Space>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="执行记录与影响说明">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <Typography.Title level={5}>Trace Fields</Typography.Title>
              <Select
                mode="tags"
                style={{ width: "100%" }}
                value={traceFieldsDraft}
                onChange={setTraceFieldsDraft}
                options={requiredRuleTraceFields.map((field) => ({ label: field, value: field }))}
              />
              <div className="p1-filter-pill-row">
                {traceFieldsDraft.map((item) => (
                  <span key={item} className="p1-filter-pill is-active">{item}</span>
                ))}
              </div>
              <Card size="small" title="合同完整性检查">
                <div className="p1-contract-check-list">
                  {[
                    ["input_schema 完整", draftInputSchema.length > 0],
                    ["output_schema 完整", draftOutputSchema.length > 0],
                    ["input_hash 已配置", draftInputSchema.some((field) => field.field_name === "input_hash")],
                    ["output_hash 已配置", draftOutputSchema.some((field) => field.field_name === "output_hash")],
                    ["affected_object_ids 已配置", draftOutputSchema.some((field) => field.field_name === "affected_object_ids")],
                    ["trace_fields 已配置", requiredRuleTraceFields.every((field) => traceFieldsDraft.includes(field))],
                  ].map(([label, passed]) => (
                    <span key={String(label)} className={passed ? "is-pass" : "is-fail"}>
                      {String(label)}
                    </span>
                  ))}
                </div>
              </Card>
              <Card size="small" title="RuleExecutionRecord 预览">
                <Descriptions column={1} size="small">
                  {Object.entries(recordPreview).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>{String(value)}</Descriptions.Item>
                  ))}
                </Descriptions>
                <Alert
                  type="warning"
                  showIcon
                  message="没有 RuleExecutionRecord 的规则输出不得进入发布候选。"
                  style={{ marginTop: 12 }}
                />
              </Card>
              <Card size="small" title="影响面预估">
                <Space direction="vertical" size={8}>
                  <Tag color="purple">minimum_rebuild_stage_id = {selectedStageIndex + 1}</Tag>
                  {["候选知识", "关系", "质量门禁", "发布候选快照"].map((item) => <Tag key={item} color="orange">{item}</Tag>)}
                  <span>保存为新版本后会生成 ImpactSet，只标记受影响候选与发布候选，不直接覆盖正式入库知识。</span>
                  <span>运行时会用 input_hash / output_hash / affected_object_ids 定位需要增量重算的对象。</span>
                </Space>
              </Card>
              <Card size="small" title="示例输入 -> 示例输出">
                <div className="p1-sample-io">
                  <pre>{JSON.stringify({ candidate_id: "CND-1008", semantic_similarity: 0.94, confidence_score: 0.81 }, null, 2)}</pre>
                  <span>→</span>
                  <pre>{JSON.stringify({ decision: "命中", affected_object_ids: ["OBJ-M-204"], output_hash: "out_a91e" }, null, 2)}</pre>
                </div>
              </Card>
              <Alert
                type="info"
                showIcon
                message="这条主干已经接入策略快照与 runtime 合同"
                description="抽取启动会冻结策略包版本；质量门禁等阶段会输出 RuleExecutionRecord；后续规则变更影响面可以沿这些字段追踪。"
              />
            </Space>
          </Card>
        </div>
        <div className="p1-config-two-column">
          <Card className="p1-soft-card" title="最近执行样本">
            <Table
              rowKey="key"
              size="small"
              pagination={false}
              dataSource={executionRows}
              columns={[
                { title: "输入对象数", dataIndex: "input" },
                { title: "命中数", dataIndex: "hit" },
                { title: "输出对象数", dataIndex: "output" },
                { title: "失败数", dataIndex: "failed" },
                { title: "执行时间", dataIndex: "time" },
                { title: "运行快照 ID", dataIndex: "snapshot" },
              ]}
            />
          </Card>
          <Card className="p1-soft-card" title="版本变更记录">
            <Table
              rowKey="key"
              size="small"
              pagination={false}
              dataSource={versionRows}
              columns={[
                { title: "版本", dataIndex: "version" },
                { title: "阈值 / 字段变化", dataIndex: "change" },
                { title: "动作", dataIndex: "action" },
                { title: "影响", dataIndex: "impact" },
              ]}
            />
          </Card>
        </div>
      </Space>
    </ValidationWorkspace>
  );
}

export function LegacyRuleContractEditorPage() {
  const { stages, config, error } = usePolicyWorkbench();
  const defaultStage = getStageByIndex(stages, 5);
  const [selectedStageId, setSelectedStageId] = useState(defaultStage.stage_id);
  const selectedStage = stages.find((stage) => stage.stage_id === selectedStageId) ?? defaultStage;
  const selectedRule = selectedStage.rules[0] ?? buildFallbackStage("rule", "规则", "规则", 8).rules[0];
  const selectedStageIndex = Math.max(0, stages.findIndex((stage) => stage.stage_id === selectedStage.stage_id));
  const selectedStageLabel = getPrototypeStageLabel(selectedStage, selectedStageIndex);

  return (
    <ValidationWorkspace
      title="规则输入输出合同编辑"
      description="为每条规则明确输入 Schema、输出 Schema、trace fields 和影响对象字段，保证规则变更后能够按合同定位并增量重算。"
      actions={
        <Space wrap>
          <Button type="primary">保存为新版本</Button>
          <Button>校验合同</Button>
          <Button>查看执行记录</Button>
          <PageLinkButton to="/policies/stages">返回阶段配置</PageLinkButton>
        </Space>
      }
      stats={[
        { title: "规则名称", value: selectedRule.name },
        { title: "rule_id", value: selectedRule.key },
        { title: "策略包", value: config?.scope_label ?? "合同通用抽取" },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="当前使用默认合同原型" description={error} /> : null}
        <Alert type="warning" showIcon message="结构性规则，变更后必须计算影响面并刷新相关阶段图谱" />
        <div className="p1-prototype-grid is-wide-right">
          <Card className="p1-soft-card" title="规则身份与适用范围">
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Select
                style={{ width: "100%" }}
                value={selectedStage.stage_id}
                onChange={setSelectedStageId}
                options={stages.map((stage, index) => ({ value: stage.stage_id, label: getPrototypeStageLabel(stage, index) }))}
              />
              <Descriptions column={1} size="small">
                <Descriptions.Item label="规则说明">{selectedRule.meaning}</Descriptions.Item>
                <Descriptions.Item label="适用阶段">{selectedStageLabel}</Descriptions.Item>
                <Descriptions.Item label="依赖上游产物">{selectedStage.inputs.join("、")}</Descriptions.Item>
                <Descriptions.Item label="默认动作">
                  <Tag color={actionColor(selectedRule.action)}>{formatAction(selectedRule.action)}</Tag>
                </Descriptions.Item>
              </Descriptions>
              <Alert type="error" showIcon message="合同完整性检查" description="示例：input_hash、affected_object_ids 必须存在，用于后续影响面追踪。" />
            </Space>
          </Card>

          <Card className="p1-soft-card" title="输入 / 输出 Schema 编辑">
            <Space direction="vertical" size={18} style={{ display: "flex" }}>
              <Typography.Title level={5}>输入合同</Typography.Title>
              <Table
                size="small"
                pagination={false}
                dataSource={[
                  { key: "candidate_id", source: "候选知识", type: "string", required: "必填", use: "标识被比较的候选对象" },
                  { key: "semantic_similarity", source: "相似度评估", type: "float", required: "必填", use: "判断是否满足归并阈值" },
                  { key: "anchor_ids", source: "锚点证据", type: "string[]", required: "必填", use: "追踪证据来源并支持审计" },
                  { key: "input_hash", source: "运行快照", type: "string", required: "必填", use: "影响面重算定位" },
                ]}
                columns={[
                  { title: "字段名", dataIndex: "key" },
                  { title: "来源产物", dataIndex: "source" },
                  { title: "类型", dataIndex: "type" },
                  { title: "是否必填", dataIndex: "required" },
                  { title: "用于判断的原因", dataIndex: "use" },
                ]}
              />
              <Typography.Title level={5}>输出合同</Typography.Title>
              <Table
                size="small"
                pagination={false}
                dataSource={[
                  { key: "merged_object_id", meaning: "归并后对象 ID", action: "归并", trace: "是" },
                  { key: "discarded_candidate_ids", meaning: "被折叠的旧候选", action: "标记归档", trace: "是" },
                  { key: "decision_reason", meaning: "规则决策说明", action: "写入审计", trace: "是" },
                  { key: "output_hash", meaning: "输出合同摘要", action: "写入快照", trace: "是" },
                ]}
                columns={[
                  { title: "输出字段", dataIndex: "key" },
                  { title: "含义", dataIndex: "meaning" },
                  { title: "可能动作", dataIndex: "action" },
                  { title: "是否写入运行记录", dataIndex: "trace" },
                ]}
              />
            </Space>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="执行记录与影响说明">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <Typography.Title level={5}>Trace Fields</Typography.Title>
              <div className="p1-filter-pill-row">
                {["rule_id", "rule_version", "stage_id", "snapshot_id", "input_hash", "output_hash", "affected_object_ids"].map((item) => (
                  <span key={item} className="p1-filter-pill is-active">{item}</span>
                ))}
              </div>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="最近执行">ex-20260506-000812</Descriptions.Item>
                <Descriptions.Item label="命中次数">12,842</Descriptions.Item>
                <Descriptions.Item label="影响阶段">规则清洗、实体抽取、候选合并、质量校验</Descriptions.Item>
              </Descriptions>
              <Alert type="warning" showIcon message="保存后需设计影响面" description="不会直接覆盖正式入库知识，只会生成待重算任务和修订候选。" />
            </Space>
          </Card>
        </div>
      </Space>
    </ValidationWorkspace>
  );
}

export function StrategyDiffPage() {
  const { stages, config } = usePolicyWorkbench();
  const changedStages = stages.filter((stage, index) => index === 5 || index === 6 || index === 8 || index === 9);
  const diffRows = changedStages.flatMap((stage) =>
    (stage.rules.length ? stage.rules.slice(0, 2) : buildFallbackStage(stage.stage_id, stage.label, stage.group, 8).rules.slice(0, 1)).map((rule, index) => ({
      key: `${stage.stage_id}-${rule.key}`,
      stage: getPrototypeStageLabel(stage, Math.max(0, stages.findIndex((item) => item.stage_id === stage.stage_id))),
      rule: rule.name,
      oldVersion: `r${index + 1}.3`,
      newVersion: `r${index + 1}.4`,
      type: index === 0 ? "结构性变化" : "阈值调整",
      input: index === 0 ? "输入新增 source_anchor_ids" : "输入无变化",
      output: index === 0 ? "输出新增 affected_object_ids" : "输出无变化",
      impact: index === 0 ? "中高" : "中",
    })),
  );

  return (
    <ValidationWorkspace
      title="策略版本与规则差异"
      description="比较策略包版本之间的规则语义差异，评估对阶段、规则与知识生成动作的影响。"
      actions={
        <Space wrap>
          <Link to="/policies/impact"><Button type="primary">生成影响面</Button></Link>
          <Button>复制为新策略包</Button>
          <Button>设为知识库默认策略</Button>
          <PageLinkButton to="/policies/stages">返回策略配置</PageLinkButton>
        </Space>
      }
      stats={[
        { title: "基准策略版本", value: "v3.11" },
        { title: "目标策略版本", value: config?.version_label ?? "v3.12" },
        { title: "影响阶段", value: `${changedStages.length} / 13` },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Alert
          type="warning"
          showIcon
          message="版本比较不会自动重算已有知识"
          description="当前使用 policy-config 真实策略数据生成语义差异；专用策略 diff API 暂缺，因此差异计数为 mock fallback。生成 ImpactSet 后才进入增量重算。"
        />
        <div className="p1-prototype-grid is-wide-right">
          <Card className="p1-soft-card" title="版本 A / 版本 B">
            <div className="p1-version-timeline">
              {[
                ["基准版本", "v3.11", "历史运行快照"],
                ["目标版本", config?.version_label ?? "v3.12", "当前策略配置"],
                ["比较时间", "2026-05-06 10:42", "前端生成"],
                ["适用知识类型", config?.scope_label ?? "合同条款", "策略包范围"],
              ].map(([title, value, desc]) => (
                <div key={title} className="p1-version-card">
                  <span>{title}</span>
                  <strong>{value}</strong>
                  <small>{desc}</small>
                </div>
              ))}
            </div>
            <StageRail stages={stages} selectedStageId={changedStages[0]?.stage_id ?? stages[0]?.stage_id} onSelect={() => undefined} />
          </Card>
          <Card className="p1-soft-card" title="差异摘要">
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <div className="p1-stat-strip">
                <div className="p1-stat-card"><span>新增规则数</span><strong>12</strong></div>
                <div className="p1-stat-card"><span>修改规则数</span><strong>18</strong></div>
                <div className="p1-stat-card"><span>停用规则数</span><strong>5</strong></div>
                <div className="p1-stat-card"><span>动作变化数</span><strong>7</strong></div>
                <div className="p1-stat-card"><span>阈值变化数</span><strong>11</strong></div>
                <div className="p1-stat-card"><span>结构性变化</span><strong>2</strong></div>
              </div>
              <Alert type="info" showIcon message="影响等级：中高" description="主要集中在规则清洗、实体抽取、候选合并与质量校验。" />
              <div className="p1-stage-track">
                {stages.slice(0, 13).map((stage, index) => (
                  <div key={stage.stage_id} className={`p1-stage-step${changedStages.some((item) => item.stage_id === stage.stage_id) ? " is-current" : " is-done"}`}>
                    <span className="p1-stage-index">{index + 1}</span>
                    <span className="p1-stage-label">{getPrototypeStageLabel(stage, index)}</span>
                  </div>
                ))}
              </div>
              <Table
                rowKey="key"
                size="small"
                pagination={{ pageSize: 8 }}
                dataSource={diffRows}
                columns={[
                  { title: "阶段", dataIndex: "stage" },
                  { title: "规则名称", dataIndex: "rule" },
                  { title: "旧版本", dataIndex: "oldVersion" },
                  { title: "新版本", dataIndex: "newVersion" },
                  { title: "变更类型", dataIndex: "type" },
                  { title: "输入合同变化", dataIndex: "input" },
                  { title: "输出合同变化", dataIndex: "output" },
                  { title: "动作变化", render: () => <Tag color="orange">可能变化</Tag> },
                  { title: "预计影响", dataIndex: "impact" },
                ]}
              />
            </Space>
          </Card>
          <Card className="p1-soft-card p1-detail-panel" title="差异解释窗">
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <Alert type="warning" showIcon message="当前命中规则：重复候选归并规则" description="结构性变化会影响候选知识、发布候选与质量门禁判断。" />
              <Descriptions column={1} size="small">
                <Descriptions.Item label="读取输入">candidate_id、semantic_similarity、anchor_ids、input_hash</Descriptions.Item>
                <Descriptions.Item label="产生输出">merged_object_id、affected_object_ids、decision_reason、output_hash</Descriptions.Item>
                <Descriptions.Item label="知识影响">候选可能被保留 / 替换 / 拆分 / 阻断</Descriptions.Item>
                <Descriptions.Item label="是否需要影响面重算">是</Descriptions.Item>
              </Descriptions>
              <Alert type="info" showIcon message="进入影响面与增量重算确认后，才会计算并刷新受影响知识。" />
            </Space>
          </Card>
        </div>
      </Space>
    </ValidationWorkspace>
  );
}

export function RuleImpactRecomputePage() {
  const { activeArchiveId, config, stages } = usePolicyWorkbench();
  const [tasks, setTasks] = useState<ArchiveIncrementalRebuildTask[]>([]);
  const [tasksError, setTasksError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!activeArchiveId) {
      setTasks([]);
      return () => {
        cancelled = true;
      };
    }

    listArchiveIncrementalRebuildTasks(activeArchiveId)
      .then((response) => {
        if (cancelled) return;
        const ordered = [...response.data].sort((left, right) => {
          const leftTime = new Date(left.created_at).getTime() || 0;
          const rightTime = new Date(right.created_at).getTime() || 0;
          return rightTime - leftTime;
        });
        setTasks(ordered);
        setTasksError(null);
      })
      .catch((error) => {
        if (cancelled) return;
        setTasks([]);
        setTasksError(error instanceof Error ? error.message : "增量重算任务读取失败");
      });

    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  const latestTask = config?.incremental_rebuild_task ?? tasks[0] ?? null;
  const activeImpact = config?.impact_set ?? latestTask?.impact_set ?? null;
  const isBackendImpact = Boolean(activeImpact);
  const stageLabelById = new Map(stages.map((stage, index) => [stage.stage_id, getPrototypeStageLabel(stage, index)]));
  const minimumStageIndex = activeImpact?.minimum_rebuild_stage_id
    ? Math.max(0, stages.findIndex((stage) => stage.stage_id === activeImpact.minimum_rebuild_stage_id))
    : 5;
  const affectedStageIds = activeImpact?.affected_stage_ids?.length
    ? activeImpact.affected_stage_ids
    : ["rule_cleaning", "entity_extraction", "concept_candidate_review", "quality_gate"];
  const impactRows = activeImpact
    ? [
        ["changed_rule_ids", String(activeImpact.changed_rule_ids.length), activeImpact.changed_rule_ids.slice(0, 3).join(", ") || "无规则变更"],
        ["affected_stage_ids", String(activeImpact.affected_stage_ids.length), activeImpact.affected_stage_ids.map((stageId) => stageLabelById.get(stageId) ?? stageId).slice(0, 4).join("、")],
        ["affected_document_ids", String(activeImpact.affected_document_ids.length), activeImpact.affected_document_ids.slice(0, 3).join(", ") || "暂无文档"],
        ["affected_chunk_ids", String(activeImpact.affected_chunk_ids.length), activeImpact.affected_chunk_ids.slice(0, 3).join(", ") || "暂无分片"],
        ["affected_candidate_ids", String(activeImpact.affected_candidate_ids.length), activeImpact.affected_candidate_ids.slice(0, 3).join(", ") || "暂无候选"],
        ["affected_relation_ids", String(activeImpact.affected_relation_ids.length), activeImpact.affected_relation_ids.slice(0, 3).join(", ") || "暂无关系"],
        ["affected_publication_snapshot_ids", String(activeImpact.affected_publication_snapshot_ids.length), activeImpact.affected_publication_snapshot_ids.slice(0, 3).join(", ") || "暂无发布快照"],
      ]
    : [
        ["changed_rule_ids", "6", "RL-CLEAN-006, RL-MERGE-021"],
        ["affected_stage_ids", "4", "规则清洗、实体抽取、候选合并、质量校验"],
        ["affected_document_ids", "128", "DOC-2026-0182, DOC-2026-0244"],
        ["affected_chunk_ids", "2,431", "CK-44102, CK-44198"],
        ["affected_candidate_ids", "684", "stale 候选"],
        ["affected_relation_ids", "219", "待重新推断关系"],
        ["affected_publication_snapshot_ids", "32", "待重新确认"],
      ];
  const recomputeRows = affectedStageIds.map((stageId, index) => {
    const pendingBase =
      activeImpact?.affected_candidate_ids.length ||
      activeImpact?.affected_document_ids.length ||
      [684, 503, 228, 156][index] ||
      0;
    return {
      stage: stageLabelById.get(stageId) ?? stageId,
      pending: Math.max(0, Math.ceil(pendingBase / Math.max(1, index + 1))),
      running: latestTask?.status === "running" && index === 0 ? 1 : 0,
      done: latestTask?.status === "completed" ? Math.max(0, Math.ceil(pendingBase / Math.max(1, index + 2))) : 0,
      failed: latestTask?.status === "failed" && index === 0 ? 1 : 0,
    };
  });
  const eventItems = activeImpact
    ? [
        `影响面计算完成：${activeImpact.affected_candidate_ids.length} 个候选、${activeImpact.affected_relation_ids.length} 条关系被标记为 stale`,
        `阶段重算计划生成：minimum_rebuild_stage_id = ${activeImpact.minimum_rebuild_stage_id ?? "--"}`,
        `规则变更：${activeImpact.changed_rule_ids.join(", ") || "无"}`,
        `增量任务：${latestTask?.task_id ?? "--"} / ${latestTask?.status ?? "queued"}`,
        `正式入库写入：${latestTask?.writes_official_knowledge ? "会写入" : "不会写入，仅生成候选或待确认结果"}`,
      ]
    : [
        "影响面计算完成：684 个候选、219 条关系被标记为 stale",
        "阶段重算开始：minimum_rebuild_stage_id = 6，复用 1-5 阶段历史快照",
        "规则执行：RL-CLEAN-006 输出 affected_object_ids 与 output_hash",
        "候选替换：合同金额条款 -> 合同总金额条款，生成修订候选",
        "发布候选快照更新：32 个候选等待治理重新确认",
      ];

  return (
    <ValidationWorkspace
      title="规则变更影响面与增量重算"
      description="基于规则输入输出合同精确计算 ImpactSet，按最早受影响阶段执行增量重算，不直接覆盖正式入库知识。"
      actions={
        <Space wrap>
          <Button type="primary">开始增量重算</Button>
          <Button>暂停</Button>
          <Button>导出影响报告</Button>
        </Space>
      }
      stats={[
        { title: "变更批次 ID", value: activeImpact?.impact_id ?? "CHG-20260506-IR-018" },
        { title: "新策略包版本", value: config?.version_label ?? "v3.12" },
        { title: "最早重算阶段", value: activeImpact?.minimum_rebuild_stage_id ? stageLabelById.get(activeImpact.minimum_rebuild_stage_id) ?? activeImpact.minimum_rebuild_stage_id : "规则清洗" },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Alert
          type={isBackendImpact ? "success" : "warning"}
          showIcon
          message={isBackendImpact ? "已读取后端 ImpactSet / 增量重算任务" : "暂无后端增量重算任务，当前为明确标识的 mock fallback"}
          description={
            isBackendImpact
              ? `任务 ${latestTask?.task_id ?? "--"}，状态 ${latestTask?.status ?? "queued"}；writes_official_knowledge=${latestTask?.writes_official_knowledge ? "true" : "false"}。`
              : `页面仍使用真实 policy-config 展示新策略版本；影响对象数量、重算进度和事件流为前端占位。${tasksError ? `任务接口状态：${tasksError}` : ""}`
          }
        />
        <Alert type="info" showIcon message="比较缓存和规则变更不会直接改写已有知识，只有在影响面计算与增量重算后，才会生成新的修订候选。" />
        <div className="p1-prototype-grid">
          <Card className="p1-soft-card" title="ImpactSet 面板">
            {impactRows.map(([title, value, desc]) => (
              <div key={title} className="p1-impact-row">
                <span>{title}</span>
                <strong>{value}</strong>
                <small>{desc}</small>
              </div>
            ))}
          </Card>
          <Card className="p1-soft-card" title="重算计划图">
            <Space direction="vertical" size={18} style={{ display: "flex" }}>
              <div className="p1-recompute-plan">
                {Array.from({ length: 13 }, (_, index) => (
                  <span key={index + 1} className={index >= minimumStageIndex && index < 12 ? "is-active" : undefined}>{index + 1}</span>
                ))}
              </div>
              <Alert
                type="warning"
                showIcon
                message={`minimum_rebuild_stage_id = ${activeImpact?.minimum_rebuild_stage_id ?? "rule_cleaning"}`}
                description="复用该阶段之前的历史快照，从最早受影响阶段开始对 stale 对象增量重算。"
              />
              <div className="p1-stat-strip">
                {recomputeRows.slice(0, 4).map((row) => (
                  <div className="p1-stat-card" key={row.stage}><span>{row.stage}待处理</span><strong>{row.pending}</strong></div>
                ))}
              </div>
              <Table
                rowKey="stage"
                size="small"
                pagination={false}
                dataSource={recomputeRows}
                columns={[
                  { title: "阶段", dataIndex: "stage" },
                  { title: "待处理", dataIndex: "pending" },
                  { title: "运行中", dataIndex: "running" },
                  { title: "完成", dataIndex: "done" },
                  { title: "失败", dataIndex: "failed" },
                ]}
              />
              <div className="p1-mini-flow">
                <Tag color="orange">stale 候选</Tag>
                <span>→</span>
                <Tag color="processing">重算中</Tag>
                <span>→</span>
                <Tag color="success">新候选</Tag>
                <span>→</span>
                <Tag color="purple">等待治理确认</Tag>
              </div>
            </Space>
          </Card>
          <Card className="p1-soft-card p1-detail-panel" title="新旧差异观察窗">
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Segmented options={["候选知识", "关系", "发布候选"]} defaultValue="候选知识" />
              <Alert type="warning" showIcon message="统一候选知识 K-24" description="旧规则输出已被新规则输出替代，正式入库知识尚未覆盖。" />
              <Descriptions column={1} size="small">
                <Descriptions.Item label="旧规则输出">合同金额条款 / 置信度 0.78</Descriptions.Item>
                <Descriptions.Item label="新规则输出">合同总金额条款 / 置信度 0.91</Descriptions.Item>
                <Descriptions.Item label="是否影响发布候选">是</Descriptions.Item>
                <Descriptions.Item label="是否需要治理重新确认">是</Descriptions.Item>
              </Descriptions>
            </Space>
          </Card>
        </div>
        <Card className="p1-soft-card" title="实时事件流">
          <List
            size="small"
            dataSource={eventItems}
            renderItem={(item) => <List.Item><Tag color={isBackendImpact ? "success" : "processing"}>{isBackendImpact ? "后端任务" : "mock fallback"}</Tag>{item}</List.Item>}
          />
        </Card>
      </Space>
    </ValidationWorkspace>
  );
}

function useRuntimeWorkbench() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [documents, setDocuments] = useState<ArchiveKnowledgeDocument[]>([]);
  const [runtime, setRuntime] = useState<ArchiveDocumentRuntimeContract | null>(null);
  const [publication, setPublication] = useState<ArchivePublicationOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRuntime() {
      if (!activeArchiveId) {
        setDocuments([]);
        setRuntime(null);
        setPublication(null);
        return;
      }

      try {
        setLoading(true);
        const [documentsResponse, publicationResponse] = await Promise.all([
          getArchiveDocuments(activeArchiveId),
          getArchivePublication(activeArchiveId),
        ]);
        if (cancelled) return;
        setDocuments(documentsResponse.data);
        setPublication(publicationResponse.data);
        const firstDocument = documentsResponse.data[0];
        if (firstDocument) {
          const runtimeResponse = await getArchiveDocumentRuntime(firstDocument.id, activeArchiveId);
          if (cancelled) return;
          setRuntime(runtimeResponse.data);
        } else {
          setRuntime(null);
        }
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "运行快照加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadRuntime();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  return { activeArchive, documents, runtime, publication, error, loading };
}

function findRuntimeStage(runtime: ArchiveDocumentRuntimeContract | null, stageIds: string[]) {
  return runtime?.stages.find((stage) => stageIds.includes(stage.stage_id)) ?? null;
}

function getRuntimeRuleNodes(stage: ArchiveDocumentRuntimeStageSnapshot | null) {
  return stage?.graph.nodes.filter((node) => node.node_type.includes("rule") || "rule_key" in node.attributes) ?? [];
}

function getNodeValue(node: ArchiveDocumentRuntimeGraphNode, key: string, fallback = "--") {
  const raw = node.metrics[key] ?? node.attributes[key];
  return raw === undefined || raw === null || raw === "" ? fallback : String(raw);
}

export function QualityGateExplanationPage() {
  const { activeArchive, runtime, error, loading } = useRuntimeWorkbench();
  const qualityStage = findRuntimeStage(runtime, ["quality_policy_evaluation_governance_gate", "quality_gate"]);
  const ruleNodes = getRuntimeRuleNodes(qualityStage);
  const metrics = [
    ["支持文档数", "28", ">= 20", "通过"],
    ["证据覆盖率", "91%", ">= 90%", "通过"],
    ["冲突数", "3", "<= 2", "警告"],
    ["关系完整度", "87%", ">= 85%", "通过"],
    ["定义完整度", "82%", ">= 85%", "警告"],
    ["候选可信度", "0.88", ">= 0.80", "通过"],
  ];

  return (
    <ValidationWorkspace
      title="质量门禁策略执行解释"
      description="单文档工作台 / 质量门禁阶段聚焦视图，解释机器门禁如何自动决定发布候选去向。"
      actions={
        <Space wrap>
          <Button>查看规则</Button>
          <Button>查看原文</Button>
          <Button type="primary">导出解释报告</Button>
        </Space>
      }
      stats={[
        { title: "当前文档", value: runtime?.document_title ?? "暂无运行文档" },
        { title: "当前阶段", value: qualityStage?.label ?? "质量门禁" },
        { title: "策略快照", value: runtime?.policy_snapshot?.snapshot_id ?? "未冻结" },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="运行快照暂不可用，当前展示解释页原型" description={error} /> : null}
        <Card className="p1-soft-card" loading={loading}>
          <Typography.Title level={5}>门禁决策概览</Typography.Title>
          <div className="p1-decision-options">
            <div><Tag color="success">自动执行</Tag><strong>全部规则通过</strong><span>机器自动放行生成发布候选</span></div>
            <div className="is-active"><Tag color="warning">警告继续</Tag><strong>存在非阻断问题</strong><span>带门禁警告生成发布候选</span></div>
            <div><Tag color="error">阻断返回</Tag><strong>存在阻断问题</strong><span>回退到相关阶段</span></div>
            <div><Tag color="processing">延迟发布</Tag><strong>等待条件满足</strong><span>延迟生成发布候选</span></div>
          </div>
          <Typography.Title level={4} className="p1-decision-banner">机器带警告继续生成发布候选</Typography.Title>
        </Card>

        <div className="p1-prototype-grid">
          <Card className="p1-soft-card" title="质量指标仪表盘">
            <div className="p1-quality-grid">
              {metrics.map(([label, actual, threshold, status]) => (
                <div key={label} className="p1-quality-tile">
                  <span>{label}</span>
                  <strong style={{ color: status === "警告" ? "#f97316" : "#16a34a" }}>{actual}</strong>
                  <small>Threshold {threshold}</small>
                  <Tag color={status === "警告" ? "warning" : "success"}>{status}</Tag>
                </div>
              ))}
            </div>
            <Alert className="p1-hero-alert" type="warning" showIcon message="门禁综合结果：警告继续" />
          </Card>

          <Card className="p1-soft-card" title="规则命中图谱">
            <div className="p1-quality-rule-map">
              <div className="p1-rule-input-stack">
                {["金额条款候选", "关系候选", "定义项候选", "冲突候选", "证据锚点集合", "发布候选输入包"].map((item, index) => (
                  <span key={item} className={index === 2 ? "is-active" : ""}>{item}</span>
                ))}
              </div>
              <div className="p1-rule-hit-stack">
                {(ruleNodes.length ? ruleNodes : [null, null, null, null]).slice(0, 4).map((node, index) => (
                  <div key={node?.node_id ?? index} className={`p1-rule-hit-card${index === 2 ? " is-active" : ""}`}>
                    <Tag color={index === 2 ? "warning" : "success"}>{node ? getNodeValue(node, "rule_key", node.label) : `QG-00${index + 1}`}</Tag>
                    <strong>{node?.label ?? ["证据覆盖率门禁", "冲突密度门禁", "定义完整度门禁", "候选可信度门禁"][index]}</strong>
                    <span>{node ? getNodeValue(node, "threshold") : index === 2 ? ">=85%" : ">=90%"}</span>
                  </div>
                ))}
              </div>
              <div className="p1-rule-output-stack">
                <span>自动执行</span>
                <span className="is-active">警告继续</span>
                <span>阻断返回</span>
                <span>延迟发布</span>
              </div>
            </div>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="规则解释观察窗">
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Tag color="warning">定义完整度门禁 · 警告命中</Tag>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="rule_id">{ruleNodes[0] ? getNodeValue(ruleNodes[0], "rule_key", "QG-007") : "QG-007"}</Descriptions.Item>
                <Descriptions.Item label="输入对象">定义项候选集合 / 证据锚点集合 / 发布候选输入包</Descriptions.Item>
                <Descriptions.Item label="actual">82%</Descriptions.Item>
                <Descriptions.Item label="threshold">&gt;= 85%</Descriptions.Item>
                <Descriptions.Item label="输出动作">警告继续</Descriptions.Item>
              </Descriptions>
              <Alert type="info" showIcon message="本阶段不执行人工复核动作；治理确认属于后续独立阶段。" />
            </Space>
          </Card>
        </div>

        <Card className="p1-soft-card" title="规则执行记录">
          <Table
            rowKey="rule"
            size="small"
            pagination={false}
            dataSource={metrics.map(([label, actual, threshold, status], index) => ({
              rule: `QG-${String(index + 1).padStart(3, "0")} ${label}`,
              input: index + 3,
              actual,
              threshold,
              outcome: status === "警告" ? "命中警告" : "命中通过",
              action: status === "警告" ? "警告继续" : "自动执行",
              time: `10:26:${31 + index * 3}`,
            }))}
            columns={[
              { title: "规则", dataIndex: "rule" },
              { title: "输入对象数", dataIndex: "input" },
              { title: "actual", dataIndex: "actual" },
              { title: "threshold", dataIndex: "threshold" },
              { title: "outcome", dataIndex: "outcome" },
              { title: "action", dataIndex: "action" },
              { title: "执行时间", dataIndex: "time" },
            ]}
          />
        </Card>
      </Space>
    </ValidationWorkspace>
  );
}

export function PublicationCandidatePage() {
  const { runtime, publication, error, loading } = useRuntimeWorkbench();
  const publicationStage = findRuntimeStage(runtime, ["indexes_snapshots_apis", "publication_candidate"]);
  const candidateRows = [
    ["新产生", "合同金额条款", "金额条款", "v3.12", "带警告通过", "只读候选 API", publication?.governance_confirmation_label ?? "等待治理确认"],
    ["修订候选", "交付责任", "义务条款", "v3.12", "带警告通过", "只读候选 API", "等待治理确认"],
    ["修订候选", "违约责任", "责任条款", "v3.12", "带警告通过", "只读候选 API", "等待治理确认"],
    ["stale", "付款条件（旧）", "付款条款", "v3.08", "带警告通过", "只读候选 API", "等待重新确认"],
    ["被替代", "合同总金额（旧）", "金额条款", "v3.05", "警告较多", "只读候选 API", "被替代"],
  ];

  return (
    <ValidationWorkspace
      title="发布候选快照与 API 暴露"
      description="单文档工作台 / 发布与 API 阶段聚焦视图，清楚区分机器发布候选、API 暴露范围、等待治理确认与正式入库状态。"
      actions={
        <Space wrap>
          <Button>查看快照</Button>
          <Button>查看 API</Button>
          <Button type="primary">导出候选报告</Button>
        </Space>
      }
      stats={[
        { title: "当前文档", value: runtime?.document_title ?? "暂无运行文档" },
        { title: "发布候选快照 ID", value: publication?.candidate_source ?? "PCS-20260506-1028" },
        { title: "当前治理状态", value: publication?.governance_confirmation_label ?? "等待治理确认" },
      ]}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        {error ? <Alert type="warning" showIcon message="发布快照暂不可用，当前展示发布页原型" description={error} /> : null}
        <Alert className="p1-hero-alert" type="warning" showIcon message="机器已发布候选，尚未正式入库" description="候选 API 仅暴露只读候选结果；正式入库必须等待治理确认完成。" />
        <Card className="p1-soft-card" loading={loading}>
          <div className="p1-publication-steps">
            {[
              ["1", "门禁决策", "警告继续"],
              ["2", "机器已发布候选", "候选快照已生成"],
              ["3", "API / 索引暴露范围", "只读候选 API 已暴露"],
              ["4", "等待治理确认", "等待人工治理确认"],
              ["5", "正式入库状态", publication?.formal_entry_label ?? "尚未入库"],
            ].map(([index, title, desc], itemIndex) => (
              <div key={index} className={itemIndex === 3 ? "is-active" : ""}>
                <strong>{index}</strong>
                <span>{title}</span>
                <small>{desc}</small>
              </div>
            ))}
          </div>
        </Card>

        <div className="p1-prototype-grid">
          <Card className="p1-soft-card" title="候选快照摘要">
            <div className="p1-quality-grid">
              <div className="p1-quality-tile"><span>候选知识数</span><strong>{publication?.working_summary.entity_count ?? 24}</strong></div>
              <div className="p1-quality-tile"><span>候选关系数</span><strong>{publicationStage?.graph.edges.length ?? 11}</strong></div>
              <div className="p1-quality-tile"><span>证据链覆盖</span><strong>91%</strong></div>
              <div className="p1-quality-tile"><span>可暴露 API 数</span><strong>6</strong></div>
            </div>
            <Alert className="p1-hero-alert" type="warning" showIcon message="机器已发布候选，等待治理确认" />
          </Card>

          <Card className="p1-soft-card" title="发布候选结构图">
            <div className="p1-publication-map">
              <div className="p1-flow-box"><Tag color="orange">1</Tag><strong>门禁决策</strong><span>Gate Decision</span></div>
              <div className="p1-flow-arrow">→</div>
              <div className="p1-flow-box"><Tag color="success">2</Tag><strong>发布候选快照</strong><span>Publication Candidate Snapshot</span></div>
              <div className="p1-flow-arrow">→</div>
              <div className="p1-flow-box"><Tag color="blue">3</Tag><strong>索引投影</strong><span>Index Projection</span></div>
              <div className="p1-flow-arrow">→</div>
              <div className="p1-flow-box"><Tag color="purple">4</Tag><strong>治理确认</strong><span>Governance Confirmation</span></div>
            </div>
            <div className="p1-api-scope-grid">
              <div>
                <Typography.Text strong>候选知识与关系集合（只读）</Typography.Text>
                <div className="p1-api-path">候选知识集合 K-24</div>
                <div className="p1-api-path">候选关系集合 R-11</div>
              </div>
              <div>
                <Typography.Text strong>API 暴露路径（只读候选 API）</Typography.Text>
                <div className="p1-api-path">/candidate/knowledge/read</div>
                <div className="p1-api-path">/candidate/relation/read</div>
                <div className="p1-api-path">/candidate/search</div>
              </div>
            </div>
          </Card>

          <Card className="p1-soft-card p1-detail-panel" title="候选详情观察窗">
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <Tag color="blue">统一候选知识 K-24</Tag>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="来源阶段">{publicationStage?.label ?? "候选合并 / 质量门禁 / 发布候选"}</Descriptions.Item>
                <Descriptions.Item label="规则版本">{runtime?.policy_snapshot?.version_label ?? "v3.12"}</Descriptions.Item>
                <Descriptions.Item label="证据链">A-102、A-115、A-204</Descriptions.Item>
                <Descriptions.Item label="API 暴露路径">/candidate/search?doc=2026Q1</Descriptions.Item>
                <Descriptions.Item label="正式入库版本">尚未入库</Descriptions.Item>
              </Descriptions>
              <Alert type="warning" showIcon message="旧候选已被新策略替代，等待重新确认" />
            </Space>
          </Card>
        </div>

        <Card className="p1-soft-card" title="候选知识清单">
          <Table
            rowKey={(record) => `${record[0]}-${record[1]}`}
            size="small"
            pagination={false}
            dataSource={candidateRows}
            columns={[
              { title: "状态", render: (_, record: string[]) => <Tag color={record[0] === "被替代" ? "error" : record[0] === "stale" ? "warning" : "blue"}>{record[0]}</Tag> },
              { title: "名称", render: (_, record: string[]) => record[1] },
              { title: "类型", render: (_, record: string[]) => record[2] },
              { title: "规则版本", render: (_, record: string[]) => record[3] },
              { title: "质量状态", render: (_, record: string[]) => <Tag color="warning">{record[4]}</Tag> },
              { title: "API 暴露", render: (_, record: string[]) => <Tag color="blue">{record[5]}</Tag> },
              { title: "治理状态", render: (_, record: string[]) => <Tag color="purple">{record[6]}</Tag> },
            ]}
          />
        </Card>
      </Space>
    </ValidationWorkspace>
  );
}
