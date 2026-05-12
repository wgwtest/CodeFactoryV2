import { useCallback, useEffect, useMemo, useState } from "react";

import { Alert, Button, Card, Col, Descriptions, Empty, Input, Row, Select, Space, Spin, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type {
  ArchiveIncrementalRebuildTask,
  ArchivePolicyImpactSet,
  ArchivePolicyPackageVersion,
  ArchiveRuleInputFieldContract,
  ArchiveRuleOutputFieldContract,
  UpdateArchivePolicyConfigInput,
} from "../../../../lib/api";
import { useArchiveContext } from "../../../../context/ArchiveContext";
import { P1_POLICY_CONFIG_UPDATED_EVENT } from "../../events";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { policyRulesApi } from "./api";
import type {
  PolicyRuleContractRow,
  PolicyRuleWithContract,
  PolicyRulesConfig,
  PolicyStageWithRuleContracts,
  RuleDraftValidation,
} from "./types";

const { TextArea } = Input;

const REQUIRED_INPUT_FIELDS = ["input_hash"];
const REQUIRED_OUTPUT_FIELDS = ["output_hash", "affected_object_ids"];
const REQUIRED_TRACE_FIELDS = [
  "rule_id",
  "rule_version",
  "rule_hash",
  "stage_id",
  "snapshot_id",
  "input_hash",
  "output_hash",
  "affected_object_ids",
];

const RULE_EXECUTION_RECORD_FIELDS = [
  "execution_id",
  "archive_id",
  "document_id",
  "stage_id",
  "rule_id",
  "rule_version",
  "rule_hash",
  "policy_snapshot_id",
  "policy_package_id",
  "policy_package_version_id",
  "policy_version",
  "input_artifact_refs",
  "input_hash",
  "output_artifact_refs",
  "output_hash",
  "affected_object_ids",
  "affected_relation_ids",
  "decision",
  "metrics",
  "executed_at",
  "source",
];

function statusColor(status?: string | null) {
  if (status === "valid" || status === "published") return "green";
  if (status === "draft" || status === "candidate") return "blue";
  if (status === "warning" || status === "governance_pending") return "gold";
  if (status === "invalid" || status === "deprecated") return "red";
  if (status === "archived") return "default";
  return "default";
}

function ruleIdentity(rule: Pick<PolicyRuleWithContract, "key" | "rule_id">) {
  return String(rule.rule_id || rule.key).trim();
}

function getOrderedStages(config: PolicyRulesConfig): PolicyStageWithRuleContracts[] {
  const orderedStages = config.stage_order
    .map((stageId) => config.stages[stageId])
    .filter((stage): stage is PolicyStageWithRuleContracts => Boolean(stage));
  const orderedIds = new Set(orderedStages.map((stage) => stage.stage_id));
  const extraStages = Object.values(config.stages).filter((stage) => !orderedIds.has(stage.stage_id));
  return [...orderedStages, ...extraStages];
}

function buildRuleRows(config: PolicyRulesConfig): PolicyRuleContractRow[] {
  return getOrderedStages(config).flatMap((stage) =>
    stage.rules.map((rule) => {
      const identity = ruleIdentity(rule);
      return {
        rowId: `${stage.stage_id}:${identity}`,
        stageId: stage.stage_id,
        stageLabel: stage.label,
        ruleId: identity,
        ruleName: rule.name,
        action: rule.action,
        effectKind: String(rule.effect_kind ?? ""),
        inputFieldCount: rule.input_schema?.length ?? 0,
        outputFieldCount: rule.output_schema?.length ?? 0,
        traceFieldCount: rule.trace_fields?.length ?? 0,
        contractStatus: String(rule.contract_status ?? "unknown"),
        contractErrors: rule.contract_errors ?? [],
      };
    }),
  );
}

function buildVersionEntries(config: PolicyRulesConfig): ArchivePolicyPackageVersion[] {
  const entries = [...(config.policy_package_versions ?? [])];
  const currentVersionId = config.policy_package_version_id ?? null;
  if (currentVersionId && !entries.some((entry) => entry.version_id === currentVersionId)) {
    entries.unshift({
      version_id: currentVersionId,
      version_label: config.version_label,
      version_hash: config.policy_package_version_hash,
      status: config.policy_package_version_status,
      created_at: config.policy_package_version_created_at,
      previous_version_id: config.previous_policy_package_version_id,
    });
  }
  return entries;
}

function buildPolicyUpdatePayload(config: PolicyRulesConfig): UpdateArchivePolicyConfigInput {
  return {
    policy_package_id: config.policy_package_id,
    policy_package_name: config.policy_package_name,
    policy_package_version_id: config.policy_package_version_id,
    policy_package_version_status: config.policy_package_version_status,
    policy_package_version_hash: config.policy_package_version_hash,
    policy_package_version_created_at: config.policy_package_version_created_at,
    previous_policy_package_version_id: config.previous_policy_package_version_id,
    policy_package_versions: config.policy_package_versions,
    version_label: config.version_label,
    scope_label: config.scope_label,
    ai_autoadapt_enabled: config.ai_autoadapt_enabled,
    stage_order: config.stage_order,
    stages: config.stages,
  };
}

function clonePolicyConfig(config: PolicyRulesConfig): PolicyRulesConfig {
  return JSON.parse(JSON.stringify(config)) as PolicyRulesConfig;
}

function formatDate(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function shortenHash(value?: string | null) {
  if (!value) return "未生成";
  return value.length > 22 ? `${value.slice(0, 19)}...` : value;
}

function stringifySchema(value: unknown) {
  return JSON.stringify(value ?? [], null, 2);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseSchemaArray<T>(raw: string, label: string): { data: T[]; errors: string[] } {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return { data: [], errors: [`${label} 必须是 JSON 数组`] };
    }
    return { data: parsed as T[], errors: [] };
  } catch (error) {
    return {
      data: [],
      errors: [`${label} 不是合法 JSON：${error instanceof Error ? error.message : "解析失败"}`],
    };
  }
}

function fieldNames(fields: Array<{ field_name?: string }>) {
  return new Set(fields.map((field) => String(field.field_name ?? "").trim()).filter(Boolean));
}

function validateFieldObjects(
  fields: unknown[],
  label: "input_schema" | "output_schema",
  refKey: "source_artifact" | "target_artifact",
) {
  const errors: string[] = [];
  fields.forEach((field, index) => {
    if (!isRecord(field)) {
      errors.push(`${label}[${index}] 必须是对象`);
      return;
    }
    if (!String(field.field_name ?? "").trim()) {
      errors.push(`missing ${label}[${index}].field_name`);
    }
    if (!String(field[refKey] ?? "").trim()) {
      errors.push(`missing ${label}[${index}].${refKey}`);
    }
    if (!String(field.field_type ?? "").trim()) {
      errors.push(`missing ${label}[${index}].field_type`);
    }
  });
  return errors;
}

function validateDraft(inputSchemaText: string, outputSchemaText: string, rawTraceFields: string[]): RuleDraftValidation {
  const input = parseSchemaArray<ArchiveRuleInputFieldContract>(inputSchemaText, "规则输入 Schema");
  const output = parseSchemaArray<ArchiveRuleOutputFieldContract>(outputSchemaText, "规则输出 Schema");
  const traceFields = Array.from(new Set(rawTraceFields.map((field) => field.trim()).filter(Boolean)));
  const errors = [...input.errors, ...output.errors];

  errors.push(...validateFieldObjects(input.data, "input_schema", "source_artifact"));
  errors.push(...validateFieldObjects(output.data, "output_schema", "target_artifact"));

  const inputFieldNames = fieldNames(input.data);
  const outputFieldNames = fieldNames(output.data);
  const traceFieldNames = new Set(traceFields);

  for (const fieldName of REQUIRED_INPUT_FIELDS) {
    if (!inputFieldNames.has(fieldName)) errors.push(`missing input_schema.${fieldName}`);
  }
  for (const fieldName of REQUIRED_OUTPUT_FIELDS) {
    if (!outputFieldNames.has(fieldName)) errors.push(`missing output_schema.${fieldName}`);
  }
  for (const fieldName of REQUIRED_TRACE_FIELDS) {
    if (!traceFieldNames.has(fieldName)) errors.push(`missing trace_fields.${fieldName}`);
  }

  return {
    status: errors.length ? "invalid" : "valid",
    errors,
    inputSchema: input.data,
    outputSchema: output.data,
    traceFields,
  };
}

function impactSummary(impactSet?: ArchivePolicyImpactSet | null) {
  if (!impactSet) return null;
  return [
    `${impactSet.changed_rule_ids.length} 条规则`,
    `${impactSet.affected_document_ids.length} 个文档`,
    `${impactSet.affected_stage_ids.length} 个阶段`,
    `${impactSet.affected_candidate_ids.length} 个候选`,
    `${impactSet.affected_relation_ids.length} 条关系`,
  ].join(" / ");
}

export function PolicyRulesPage({ context }: P1ModulePageProps) {
  const { refreshArchives } = useArchiveContext();
  const [policyConfig, setPolicyConfig] = useState<PolicyRulesConfig | null>(null);
  const [rebuildTasks, setRebuildTasks] = useState<ArchiveIncrementalRebuildTask[]>([]);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [inputSchemaText, setInputSchemaText] = useState("[]");
  const [outputSchemaText, setOutputSchemaText] = useState("[]");
  const [traceFields, setTraceFields] = useState<string[]>([]);
  const [draftValidation, setDraftValidation] = useState<RuleDraftValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const refreshPolicyRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [configResponse, tasksResponse] = await Promise.all([
        policyRulesApi.getArchivePolicyConfig(context.archiveId),
        policyRulesApi.listArchiveIncrementalRebuildTasks(context.archiveId),
      ]);
      const config = configResponse.data as PolicyRulesConfig;
      const stages = getOrderedStages(config);
      const firstStage = stages[0] ?? null;
      const firstRule = firstStage?.rules[0] ?? null;

      setPolicyConfig(config);
      setRebuildTasks(tasksResponse.data);
      setSelectedVersionId(config.policy_package_version_id ?? null);
      setSelectedStageId((current) => (current && config.stages[current] ? current : firstStage?.stage_id ?? null));
      setSelectedRuleId((current) => {
        if (current && stages.some((stage) => stage.rules.some((rule) => ruleIdentity(rule) === current))) {
          return current;
        }
        return firstRule ? ruleIdentity(firstRule) : null;
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "策略配置加载失败");
    } finally {
      setLoading(false);
    }
  }, [context.archiveId]);

  useEffect(() => {
    void refreshPolicyRules();
  }, [refreshPolicyRules]);

  const stages = useMemo(() => (policyConfig ? getOrderedStages(policyConfig) : []), [policyConfig]);
  const versionEntries = useMemo(() => (policyConfig ? buildVersionEntries(policyConfig) : []), [policyConfig]);
  const ruleRows = useMemo(() => (policyConfig ? buildRuleRows(policyConfig) : []), [policyConfig]);
  const selectedStage = useMemo(
    () => stages.find((stage) => stage.stage_id === selectedStageId) ?? stages[0] ?? null,
    [selectedStageId, stages],
  );
  const selectedRule = useMemo(() => {
    if (!selectedStage) return null;
    return selectedStage.rules.find((rule) => ruleIdentity(rule) === selectedRuleId) ?? selectedStage.rules[0] ?? null;
  }, [selectedRuleId, selectedStage]);
  const latestImpactSet = policyConfig?.impact_set ?? rebuildTasks[0]?.impact_set ?? null;
  const latestTask = policyConfig?.incremental_rebuild_task ?? rebuildTasks[0] ?? null;
  const selectedVersion = versionEntries.find((entry) => entry.version_id === selectedVersionId) ?? versionEntries[0] ?? null;
  const currentVersionId = policyConfig?.policy_package_version_id ?? context.policyPackageVersionId ?? null;

  useEffect(() => {
    if (!selectedRule) return;
    setInputSchemaText(stringifySchema(selectedRule.input_schema));
    setOutputSchemaText(stringifySchema(selectedRule.output_schema));
    setTraceFields(selectedRule.trace_fields ?? []);
    setDraftValidation(null);
    setFeedback(null);
  }, [selectedRule]);

  function selectStage(stageId: string) {
    const stage = stages.find((item) => item.stage_id === stageId) ?? null;
    setSelectedStageId(stageId);
    setSelectedRuleId(stage?.rules[0] ? ruleIdentity(stage.rules[0]) : null);
  }

  function selectRule(row: PolicyRuleContractRow) {
    setSelectedStageId(row.stageId);
    setSelectedRuleId(row.ruleId);
  }

  async function reloadTasks() {
    const tasksResponse = await policyRulesApi.listArchiveIncrementalRebuildTasks(context.archiveId);
    setRebuildTasks(tasksResponse.data);
  }

  async function saveConfig(nextConfig: PolicyRulesConfig, successMessage: string) {
    setSaving(true);
    setError(null);
    try {
      const response = await policyRulesApi.updateArchivePolicyConfig(
        context.archiveId,
        buildPolicyUpdatePayload(nextConfig),
      );
      const updated = response.data as PolicyRulesConfig;
      setPolicyConfig(updated);
      setSelectedVersionId(updated.policy_package_version_id ?? null);
      setFeedback(successMessage);
      await reloadTasks();
      await refreshArchives(context.archiveId);
      window.dispatchEvent(new CustomEvent(P1_POLICY_CONFIG_UPDATED_EVENT, { detail: { archiveId: context.archiveId } }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "策略配置保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveRuleContract() {
    if (!policyConfig || !selectedStage || !selectedRule) return;
    const validation = validateDraft(inputSchemaText, outputSchemaText, traceFields);
    setDraftValidation(validation);
    if (validation.status === "invalid") return;

    const nextConfig = clonePolicyConfig(policyConfig);
    const stage = nextConfig.stages[selectedStage.stage_id];
    const targetRuleId = ruleIdentity(selectedRule);
    stage.rules = stage.rules.map((rule) =>
      ruleIdentity(rule) === targetRuleId
        ? {
            ...rule,
            input_schema: validation.inputSchema,
            output_schema: validation.outputSchema,
            trace_fields: validation.traceFields,
          }
        : rule,
    );
    nextConfig.policy_package_version_status = "draft";
    await saveConfig(nextConfig, "规则字段合同已保存为策略草稿，后端已重新校验合同并计算影响面。");
  }

  async function handleFreezeCurrentVersion() {
    if (!policyConfig) return;
    const nextConfig = clonePolicyConfig(policyConfig);
    nextConfig.policy_package_version_status = "published";
    await saveConfig(nextConfig, "当前策略包版本已标记为可冻结使用版本。");
  }

  const versionColumns: ColumnsType<ArchivePolicyPackageVersion> = [
    {
      title: "版本",
      dataIndex: "version_id",
      render: (value) => <Typography.Text code>{value || "未命名版本"}</Typography.Text>,
    },
    { title: "标签", dataIndex: "version_label", width: 180 },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (value) => <Tag color={statusColor(String(value ?? ""))}>{String(value ?? "unknown")}</Tag>,
    },
    {
      title: "哈希",
      dataIndex: "version_hash",
      width: 170,
      render: (value) => <Typography.Text code>{shortenHash(String(value ?? ""))}</Typography.Text>,
    },
    { title: "创建时间", dataIndex: "created_at", width: 180, render: (value) => formatDate(String(value ?? "")) },
  ];

  const ruleColumns: ColumnsType<PolicyRuleContractRow> = [
    {
      title: "规则",
      dataIndex: "ruleId",
      width: 170,
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text code>{value}</Typography.Text>
          <Typography.Text type="secondary">{record.ruleName}</Typography.Text>
        </Space>
      ),
    },
    { title: "阶段", dataIndex: "stageLabel", width: 120 },
    { title: "效果", dataIndex: "effectKind", width: 120, render: (value) => <Tag>{value}</Tag> },
    { title: "动作", dataIndex: "action", width: 130 },
    { title: "输入字段", dataIndex: "inputFieldCount", width: 100 },
    { title: "输出字段", dataIndex: "outputFieldCount", width: 100 },
    { title: "Trace", dataIndex: "traceFieldCount", width: 90 },
    {
      title: "状态",
      dataIndex: "contractStatus",
      width: 110,
      render: (value) => <Tag color={statusColor(value)}>{value}</Tag>,
    },
    {
      title: "操作",
      width: 90,
      render: (_, record) => (
        <Button type="link" onClick={() => selectRule(record)}>
          编辑
        </Button>
      ),
    },
  ];

  const taskColumns: ColumnsType<ArchiveIncrementalRebuildTask> = [
    { title: "任务", dataIndex: "task_id", render: (value) => <Typography.Text code>{value}</Typography.Text> },
    { title: "起点阶段", dataIndex: "start_stage_id", width: 180 },
    { title: "状态", dataIndex: "status", width: 100, render: (value) => <Tag>{String(value)}</Tag> },
    {
      title: "正式知识写入",
      dataIndex: "writes_official_knowledge",
      width: 130,
      render: (value) => <Tag color={value ? "red" : "green"}>{value ? "会写入" : "不会写入"}</Tag>,
    },
    {
      title: "输出策略",
      dataIndex: "output_policy",
      width: 250,
      render: (value) => <Typography.Text>{value}</Typography.Text>,
    },
  ];

  return (
    <PageFrame
      eyebrow="策略规则模块"
      title="策略规则"
      description="独立管理策略包版本、规则输入输出合同、动作映射、RuleExecutionRecord 字段和规则变更影响面。"
    >
      {loading ? (
        <Card className="p1-clean-card">
          <Space>
            <Spin />
            <Typography.Text>正在加载策略合同...</Typography.Text>
          </Space>
        </Card>
      ) : null}
      {error ? (
        <Alert
          className="p1-clean-alert"
          type="error"
          showIcon
          message="策略规则模块暂时不可用"
          description={error}
          action={<Button onClick={() => void refreshPolicyRules()}>重试</Button>}
        />
      ) : null}
      {!loading && !error && !policyConfig ? (
        <Card className="p1-clean-card">
          <Empty description="没有可用策略配置" />
        </Card>
      ) : null}
      {policyConfig ? (
        <>
          <Alert
            className="p1-clean-alert"
            type="info"
            showIcon
            message="规则变更只生成影响面与候选重算任务"
            description="本模块保存的是策略合同草稿或冻结版本；后端会生成 ImpactSet 与 candidate_or_pending_confirmation_only 任务，不直接覆盖正式知识。"
          />
          {feedback ? <Alert className="p1-clean-alert" type="success" showIcon message={feedback} /> : null}
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={8}>
              <Card className="p1-clean-card is-active" title="当前策略包">
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Typography.Title level={3} style={{ margin: 0 }}>
                    {currentVersionId ?? "待冻结策略版本"}
                  </Typography.Title>
                  <Descriptions size="small" column={1}>
                    <Descriptions.Item label="知识库">{context.archive.name}</Descriptions.Item>
                    <Descriptions.Item label="策略包">{policyConfig.policy_package_name}</Descriptions.Item>
                    <Descriptions.Item label="策略包 ID">{policyConfig.policy_package_id}</Descriptions.Item>
                    <Descriptions.Item label="覆盖范围">{policyConfig.scope_label}</Descriptions.Item>
                    <Descriptions.Item label="合同版本">{policyConfig.policy_contract_version ?? "未声明"}</Descriptions.Item>
                    <Descriptions.Item label="合同校验">
                      <Tag color={statusColor(policyConfig.policy_contract_status)}>
                        {policyConfig.policy_contract_status ?? "unknown"}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="版本状态">
                      <Tag color={statusColor(policyConfig.policy_package_version_status)}>
                        {policyConfig.policy_package_version_status ?? "unknown"}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                  <Button type="primary" loading={saving} onClick={() => void handleFreezeCurrentVersion()}>
                    冻结当前策略版本
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col xs={24} xl={8}>
              <Card className="p1-clean-card" title="可用策略版本">
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Select
                    value={selectedVersionId ?? undefined}
                    onChange={setSelectedVersionId}
                    options={versionEntries.map((entry) => ({
                      label: `${entry.version_id ?? "unknown"} · ${entry.status ?? "unknown"}`,
                      value: String(entry.version_id ?? entry.version_hash),
                    }))}
                    placeholder="选择策略版本"
                  />
                  {selectedVersion ? (
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="标签">{selectedVersion.version_label ?? "未标注"}</Descriptions.Item>
                      <Descriptions.Item label="状态">
                        <Tag color={statusColor(selectedVersion.status)}>{selectedVersion.status ?? "unknown"}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="哈希">{shortenHash(selectedVersion.version_hash)}</Descriptions.Item>
                      <Descriptions.Item label="前序版本">
                        {selectedVersion.previous_version_id ?? "无"}
                      </Descriptions.Item>
                    </Descriptions>
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无版本记录" />
                  )}
                </Space>
              </Card>
            </Col>
            <Col xs={24} xl={8}>
              <Card className="p1-clean-card" title="ImpactSet 摘要">
                {latestImpactSet ? (
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <Typography.Text strong>{impactSummary(latestImpactSet)}</Typography.Text>
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="影响面">{latestImpactSet.impact_id}</Descriptions.Item>
                      <Descriptions.Item label="最小重算阶段">
                        {latestImpactSet.minimum_rebuild_stage_id ?? "未指定"}
                      </Descriptions.Item>
                      <Descriptions.Item label="生成时间">{formatDate(latestImpactSet.generated_at)}</Descriptions.Item>
                    </Descriptions>
                    {latestTask ? (
                      <Tag color={latestTask.writes_official_knowledge ? "red" : "green"}>
                        {latestTask.writes_official_knowledge ? "会写正式知识" : "仅候选任务"}
                      </Tag>
                    ) : null}
                  </Space>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无规则变更影响面" />
                )}
              </Card>
            </Col>
          </Row>

          <Card className="p1-clean-card" title="策略包版本清单">
            <Table
              rowKey={(record) => String(record.version_id ?? record.version_hash ?? "version")}
              columns={versionColumns}
              dataSource={versionEntries}
              pagination={false}
              scroll={{ x: 840 }}
              onRow={(record) => ({
                onClick: () => setSelectedVersionId(String(record.version_id ?? record.version_hash)),
              })}
            />
          </Card>

          <Card className="p1-clean-card" title="规则合同清单">
            <Table
              rowKey="rowId"
              columns={ruleColumns}
              dataSource={ruleRows}
              pagination={{ pageSize: 6 }}
              scroll={{ x: 980 }}
            />
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={10}>
              <Card className="p1-clean-card" title="规则合同上下文">
                {selectedRule && selectedStage ? (
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <Select
                      value={selectedStage.stage_id}
                      onChange={selectStage}
                      options={stages.map((stage) => ({ label: `${stage.label} · ${stage.stage_id}`, value: stage.stage_id }))}
                    />
                    <Select
                      value={ruleIdentity(selectedRule)}
                      onChange={setSelectedRuleId}
                      options={selectedStage.rules.map((rule) => ({
                        label: `${ruleIdentity(rule)} · ${rule.name}`,
                        value: ruleIdentity(rule),
                      }))}
                    />
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="阶段">{selectedStage.label}</Descriptions.Item>
                      <Descriptions.Item label="规则版本">{selectedRule.rule_version ?? "未声明"}</Descriptions.Item>
                      <Descriptions.Item label="规则哈希">{shortenHash(selectedRule.rule_hash)}</Descriptions.Item>
                      <Descriptions.Item label="效果类型">{selectedRule.effect_kind ?? "未声明"}</Descriptions.Item>
                      <Descriptions.Item label="命中动作">{selectedRule.action}</Descriptions.Item>
                      <Descriptions.Item label="校验状态">
                        <Tag color={statusColor(selectedRule.contract_status)}>{selectedRule.contract_status ?? "unknown"}</Tag>
                      </Descriptions.Item>
                    </Descriptions>
                    {selectedRule.contract_errors?.length ? (
                      <Alert
                        type="warning"
                        showIcon
                        message="服务端合同校验问题"
                        description={selectedRule.contract_errors.join("；")}
                      />
                    ) : null}
                    <Typography.Text strong>动作映射</Typography.Text>
                    <pre style={{ margin: 0, maxHeight: 260, overflow: "auto", background: "#f8fafc", padding: 12 }}>
                      {JSON.stringify(selectedRule.action_mapping ?? {}, null, 2)}
                    </pre>
                    <Typography.Text strong>RuleExecutionRecord 字段</Typography.Text>
                    <Space size={[6, 6]} wrap>
                      {RULE_EXECUTION_RECORD_FIELDS.map((field) => (
                        <Tag key={field}>{field}</Tag>
                      ))}
                    </Space>
                  </Space>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择规则" />
                )}
              </Card>
            </Col>
            <Col xs={24} xl={14}>
              <Card
                className="p1-clean-card"
                title="规则字段合同编辑"
                extra={
                  <Space>
                    <Button onClick={() => setDraftValidation(validateDraft(inputSchemaText, outputSchemaText, traceFields))}>
                      校验草稿
                    </Button>
                    <Button type="primary" loading={saving} onClick={() => void handleSaveRuleContract()}>
                      保存为策略草稿
                    </Button>
                  </Space>
                }
              >
                <Space direction="vertical" size={14} style={{ width: "100%" }}>
                  {draftValidation ? (
                    <Alert
                      type={draftValidation.status === "valid" ? "success" : "error"}
                      showIcon
                      message={draftValidation.status === "valid" ? "草稿合同可保存" : "草稿合同仍有缺口"}
                      description={draftValidation.errors.join("；") || "input_schema、output_schema 与 trace_fields 已满足基础合同。"}
                    />
                  ) : null}
                  <Row gutter={[12, 12]}>
                    <Col xs={24} lg={12}>
                      <Typography.Text strong>规则输入 Schema</Typography.Text>
                      <TextArea
                        aria-label="规则输入 Schema"
                        value={inputSchemaText}
                        onChange={(event) => setInputSchemaText(event.target.value)}
                        autoSize={{ minRows: 12, maxRows: 18 }}
                      />
                    </Col>
                    <Col xs={24} lg={12}>
                      <Typography.Text strong>规则输出 Schema</Typography.Text>
                      <TextArea
                        aria-label="规则输出 Schema"
                        value={outputSchemaText}
                        onChange={(event) => setOutputSchemaText(event.target.value)}
                        autoSize={{ minRows: 12, maxRows: 18 }}
                      />
                    </Col>
                  </Row>
                  <Typography.Text strong>Trace fields</Typography.Text>
                  <Select
                    mode="tags"
                    value={traceFields}
                    onChange={setTraceFields}
                    options={REQUIRED_TRACE_FIELDS.map((field) => ({ label: field, value: field }))}
                    tokenSeparators={[",", "\n"]}
                    style={{ width: "100%" }}
                  />
                </Space>
              </Card>
            </Col>
          </Row>

          <Card className="p1-clean-card" title="候选重算任务">
            <Table
              rowKey="task_id"
              columns={taskColumns}
              dataSource={rebuildTasks}
              pagination={false}
              locale={{ emptyText: "暂无候选重算任务" }}
              scroll={{ x: 960 }}
            />
          </Card>
        </>
      ) : null}
    </PageFrame>
  );
}
