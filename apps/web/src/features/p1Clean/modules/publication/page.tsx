import { useEffect, useMemo, useState } from "react";

import { Alert, Card, Col, Descriptions, List, Row, Space, Spin, Statistic, Steps, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { ArchivePublicationOverview } from "../../../../lib/api";
import type { PublicationCandidateObject, PublicationCandidateRelation, PublicationCandidateSnapshot, QualityFinding } from "../../../p1/contracts";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { publicationApi } from "./api";
import type { PublicationStateLabel } from "./types";

type PublicationViewState = {
  overview: ArchivePublicationOverview | null;
  candidate: PublicationCandidateSnapshot | null;
  warnings: string[];
};

type ApiScopeRow = {
  key: string;
  type: "候选 API" | "候选索引";
  value: string;
};

const stateLabels: Record<string, PublicationStateLabel> = {
  machine_candidate_created: { label: "机器已生成候选", color: "blue" },
  candidate: { label: "候选态", color: "blue" },
  governance_pending: { label: "等待治理确认", color: "gold" },
  formalized: { label: "正式入库", color: "green" },
  blocked_by_quality: { label: "质量阻断", color: "red" },
  stale_after_policy_change: { label: "策略变更后过期", color: "red" },
  pending: { label: "等待治理确认", color: "gold" },
  approved: { label: "治理已确认", color: "green" },
  rejected: { label: "治理驳回", color: "red" },
  superseded: { label: "已被替代", color: "default" },
};

const qualityFindingSeverityMeta: Record<QualityFinding["severity"], { color: string; label: string }> = {
  blocked: { color: "red", label: "阻断" },
  warning: { color: "gold", label: "警告" },
  info: { color: "blue", label: "提示" },
};

function getStateLabel(value?: string | null): PublicationStateLabel {
  return value ? stateLabels[value] ?? { label: value, color: "default" } : { label: "待生成", color: "default" };
}

function formatScore(value?: number | null) {
  if (typeof value !== "number") return "待评估";
  return value <= 1 ? `${Math.round(value * 100)}分` : `${Math.round(value)}分`;
}

function formatConfidence(value?: number | null) {
  if (typeof value !== "number") return "未给出";
  return `${Math.round(value * 100)}%`;
}

function buildApiRows(candidate: PublicationCandidateSnapshot | null): ApiScopeRow[] {
  if (!candidate) return [];

  const apiRows = candidate.api_exposure_scope.readonly_candidate_api_paths.map((path) => ({
    key: `api:${path}`,
    type: "候选 API" as const,
    value: path,
  }));
  const indexRows = candidate.api_exposure_scope.index_names.map((name) => ({
    key: `index:${name}`,
    type: "候选索引" as const,
    value: name,
  }));

  return [...apiRows, ...indexRows];
}

export function PublicationPage({ context }: P1ModulePageProps) {
  const [viewState, setViewState] = useState<PublicationViewState>({
    overview: null,
    candidate: null,
    warnings: [],
  });
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setErrorMessage(null);

    Promise.all([
      publicationApi.getArchivePublication(context.archiveId).then((response) => response.data),
      publicationApi.getPublicationCandidateSnapshot(
        context.archiveId,
        context.runtimeSnapshotId,
        context.policyPackageVersionId,
      ),
    ])
      .then(([overview, candidateEnvelope]) => {
        if (disposed) return;
        setViewState({
          overview,
          candidate: candidateEnvelope.data,
          warnings: candidateEnvelope.warnings ?? [],
        });
      })
      .catch((error: unknown) => {
        if (disposed) return;
        setErrorMessage(error instanceof Error ? error.message : "发布候选快照加载失败");
      })
      .finally(() => {
        if (!disposed) {
          setLoading(false);
        }
      });

    return () => {
      disposed = true;
    };
  }, [context.archiveId, context.policyPackageVersionId, context.runtimeSnapshotId]);

  const { overview, candidate, warnings } = viewState;
  const candidateSnapshotId = candidate?.publication_candidate_snapshot_id ?? null;
  const formalPublicationSnapshotId = candidate?.publication_snapshot_id ?? context.publicationSnapshotId;
  const candidateSummary = candidate?.candidate_summary;
  const qualityDecision = candidate?.quality_decision ?? candidate?.quality_decision_summary;
  const qualityFindingReport = candidate?.quality_finding_report ?? null;
  const qualityFindings = qualityFindingReport?.findings ?? [];
  const governanceProjection = candidate?.governance_projection;
  const apiRows = useMemo(() => buildApiRows(candidate), [candidate]);
  const candidateObjects = candidate?.candidate_objects ?? [];
  const candidateRelations = candidate?.candidate_relations ?? [];
  const candidateState = getStateLabel(candidate?.status);
  const governanceState = getStateLabel(candidate?.governance_status);

  const apiColumns: ColumnsType<ApiScopeRow> = [
    {
      title: "范围",
      dataIndex: "type",
      width: 110,
      render: (value: ApiScopeRow["type"]) => <Tag color={value === "候选 API" ? "blue" : "purple"}>{value}</Tag>,
    },
    {
      title: "只读暴露对象",
      dataIndex: "value",
      render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
    },
  ];

  const objectColumns: ColumnsType<PublicationCandidateObject> = [
    {
      title: "对象",
      dataIndex: "canonical_name",
      render: (value: string, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{value}</Typography.Text>
          <Typography.Text type="secondary">{row.object_id}</Typography.Text>
        </Space>
      ),
    },
    { title: "类型", dataIndex: "object_type", width: 140 },
    {
      title: "质量",
      dataIndex: "quality_status",
      width: 110,
      render: (value: PublicationCandidateObject["quality_status"]) => (
        <Tag color={value === "passed" ? "green" : value === "blocked" ? "red" : "gold"}>{value}</Tag>
      ),
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      width: 100,
      render: (value: number | null | undefined) => formatConfidence(value),
    },
    {
      title: "证据",
      dataIndex: "evidence_refs",
      width: 90,
      render: (refs: PublicationCandidateObject["evidence_refs"]) => refs.length,
    },
  ];

  const relationColumns: ColumnsType<PublicationCandidateRelation> = [
    { title: "关系 ID", dataIndex: "relation_id" },
    { title: "类型", dataIndex: "relation_type", width: 150 },
    { title: "起点", dataIndex: "source_object_id" },
    { title: "终点", dataIndex: "target_object_id" },
    {
      title: "质量",
      dataIndex: "quality_status",
      width: 110,
      render: (value: PublicationCandidateRelation["quality_status"]) => (
        <Tag color={value === "passed" ? "green" : value === "blocked" ? "red" : "gold"}>{value}</Tag>
      ),
    },
  ];

  return (
    <PageFrame
      eyebrow="发布输出模块"
      title="发布输出"
      description="消费质量决策和运行快照，生成机器发布候选快照；候选态只读可见，治理确认后才进入正式入库。"
    >
      {errorMessage ? (
        <Alert className="p1-clean-alert" type="error" showIcon message="发布候选加载失败" description={errorMessage} />
      ) : null}
      {warnings.length ? (
        <Alert className="p1-clean-alert" type="warning" showIcon message="发布候选响应包含告警" description={warnings.join("；")} />
      ) : null}
      <Spin spinning={loading}>
        <Card className="p1-clean-card" title="发布链路">
          <Steps
            current={3}
            status={governanceProjection?.formal_entry_status === "admitted" ? "finish" : "process"}
            items={[
              {
                title: "质量决策",
                description: qualityDecision
                  ? `${qualityDecision.decision} / ${qualityDecision.output_action}`
                  : context.runtimeSnapshotId ?? "等待质量输入",
              },
              {
                title: "发布候选",
                description: candidateSnapshotId ?? "待生成候选快照",
              },
              {
                title: "候选 API",
                description: apiRows.length ? `${apiRows.length} 个候选暴露对象` : "只读候选暴露",
              },
              {
                title: "治理确认",
                description: governanceProjection?.governance_confirmation_label ?? overview?.governance_confirmation_label ?? "等待正式确认",
              },
            ]}
          />
        </Card>
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={9}>
            <Card className="p1-clean-card" title="候选快照输出">
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                <Space wrap>
                  <Tag color={candidateState.color}>{candidateState.label}</Tag>
                  <Tag color={governanceState.color}>{governanceState.label}</Tag>
                  <Tag color={governanceProjection?.formal_entry_status === "admitted" ? "green" : "gold"}>
                    {governanceProjection?.formal_entry_label ?? overview?.formal_entry_label ?? "尚未正式入库"}
                  </Tag>
                </Space>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="archiveId">
                    <Typography.Text code>{context.archiveId}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="runtimeSnapshotId">
                    <Typography.Text code>{candidate?.runtime_snapshot_id ?? candidateSummary?.generated_from_runtime_snapshot_id ?? context.runtimeSnapshotId ?? "未生成"}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="policyPackageVersionId">
                    <Typography.Text code>{candidate?.policy_package_version_id ?? context.policyPackageVersionId ?? "未冻结"}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="resolutionSnapshotId">
                    <Typography.Text code>{candidate?.resolution_snapshot_id ?? "等待知识解析快照"}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="publicationCandidateSnapshotId">
                    <Typography.Text code copyable={Boolean(candidateSnapshotId)}>
                      {candidateSnapshotId ?? "待生成"}
                    </Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="publicationSnapshotId">
                    <Typography.Text code copyable={Boolean(formalPublicationSnapshotId)}>
                      {formalPublicationSnapshotId ?? "未生成正式发布快照"}
                    </Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="候选来源">
                    {candidateSummary?.source_scope ?? overview?.candidate_scope ?? "post_quality_gate_publication_candidate"}
                  </Descriptions.Item>
                  <Descriptions.Item label="生成时间">{candidate?.generated_at ?? "等待生成"}</Descriptions.Item>
                </Descriptions>
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={15}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card className="p1-clean-card">
                  <Statistic title="质量门禁评分" value={formatScore(qualityDecision?.score)} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card className="p1-clean-card">
                  <Statistic title="候选对象" value={candidateSummary?.candidate_count ?? 0} suffix="项" />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card className="p1-clean-card">
                  <Statistic title="待治理确认" value={overview?.review_summary?.pending_count ?? candidateSummary?.candidate_knowledge_count ?? 0} suffix="项" />
                </Card>
              </Col>
            </Row>
            <Card className="p1-clean-card" title="质量决策摘要">
              <Alert
                type={
                  qualityDecision?.output_action === "return_for_rebuild"
                    ? "error"
                    : qualityDecision?.output_action === "publish_candidate_with_warning"
                      ? "warning"
                      : "info"
                }
                showIcon
                message={overview?.machine_publication_label ?? candidateSummary?.status_label ?? "机器发布候选状态待生成"}
                description={qualityDecision?.explanation ?? "等待质量门禁输出候选发布决策。"}
              />
              <Descriptions column={{ xs: 1, md: 2 }} size="small" style={{ marginTop: 16 }}>
                <Descriptions.Item label="受影响对象">
                  {(qualityDecision?.affected_object_ids ?? []).join(" / ") || "无"}
                </Descriptions.Item>
                <Descriptions.Item label="受影响关系">
                  {(qualityDecision?.affected_relation_ids ?? []).join(" / ") || "无"}
                </Descriptions.Item>
              </Descriptions>
            </Card>
            {qualityFindingReport ? (
              <Card className="p1-clean-card" title="质量发现">
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Space wrap>
                    <Tag color={qualityFindingReport.summary.publish_blocked ? "red" : "green"}>
                      {qualityFindingReport.summary.publish_blocked ? "阻断发布" : "允许发布"}
                    </Tag>
                    <Tag color="red">阻断 {qualityFindingReport.summary.blocked_count}</Tag>
                    <Tag color="gold">警告 {qualityFindingReport.summary.warning_count}</Tag>
                    {qualityFindingReport.resolution_snapshot_id ? (
                      <Tag>resolution {qualityFindingReport.resolution_snapshot_id}</Tag>
                    ) : null}
                  </Space>
                  <List
                    size="small"
                    dataSource={qualityFindings.slice(0, 6)}
                    renderItem={(finding) => {
                      const severity = qualityFindingSeverityMeta[finding.severity];
                      return (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <Space wrap>
                                <Tag color={severity.color}>{severity.label}</Tag>
                                <Typography.Text code>{finding.code}</Typography.Text>
                                {finding.target_id ? <Typography.Text type="secondary">{finding.target_id}</Typography.Text> : null}
                              </Space>
                            }
                            description={finding.message}
                          />
                        </List.Item>
                      );
                    }}
                  />
                </Space>
              </Card>
            ) : null}
          </Col>
        </Row>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card className="p1-clean-card" title="候选 API 暴露范围">
              <Table rowKey="key" columns={apiColumns} dataSource={apiRows} pagination={false} />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card className="p1-clean-card" title="治理确认状态投影">
              <Alert
                type={governanceProjection?.formal_entry_status === "admitted" ? "success" : "warning"}
                showIcon
                message={governanceProjection?.governance_confirmation_label ?? overview?.governance_confirmation_label ?? "等待治理确认"}
                description={`正式入库状态：${governanceProjection?.formal_entry_label ?? overview?.formal_entry_label ?? "尚未正式入库"}`}
              />
              <Typography.Paragraph style={{ marginTop: 16 }}>
                候选发布只表示机器已生成可审阅快照，不覆盖正式知识，也不替代治理确认页面。
              </Typography.Paragraph>
              <Alert
                type="info"
                showIcon
                message="系统间供应边界"
                description={candidate?.api_exposure_scope.not_supply_reason ?? "候选态只能预览，不作为正式 API 供应。"}
              />
            </Card>
          </Col>
        </Row>
        <Card className="p1-clean-card" title="发布候选对象与关系预览">
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <Table
              rowKey="object_id"
              columns={objectColumns}
              dataSource={candidateObjects}
              pagination={false}
              locale={{ emptyText: "暂无候选对象" }}
            />
            <Table
              rowKey="relation_id"
              columns={relationColumns}
              dataSource={candidateRelations}
              pagination={false}
              locale={{ emptyText: "暂无候选关系" }}
            />
          </Space>
        </Card>
      </Spin>
    </PageFrame>
  );
}
