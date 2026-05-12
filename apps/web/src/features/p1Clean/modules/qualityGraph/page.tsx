import { useEffect, useMemo, useState } from "react";

import { Alert, Card, Col, Descriptions, Empty, List, Progress, Row, Skeleton, Space, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { ArchiveKnowledgeGraph, ArchiveKnowledgeSummary } from "../../../../lib/api";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { qualityGraphApi } from "./api";
import type {
  QualityEvaluationReport,
  QualityFinding,
  QualityGraphReportEnvelope,
  QualityMetric,
  QualityMetricSummary,
  QualityRuleHitExplanation,
} from "./types";
import "./page.css";

const headlineMetricIds = [
  "knowledge.concept_precision",
  "graph.relation_confidence_avg",
  "knowledge.evidence_coverage",
  "graph.explainability_coverage",
];

const metricStatusMeta: Record<QualityMetric["status"], { color: string; label: string }> = {
  pass: { color: "green", label: "通过" },
  warning: { color: "gold", label: "警告" },
  fail: { color: "red", label: "失败" },
};

const decisionMeta: Record<QualityEvaluationReport["gate_decision"]["decision"], { alertType: "success" | "warning" | "error" | "info"; color: string; label: string }> = {
  auto_pass: { alertType: "success", color: "green", label: "自动通过" },
  warn_continue: { alertType: "warning", color: "gold", label: "带警告放行" },
  block: { alertType: "error", color: "red", label: "阻断回退" },
  defer: { alertType: "info", color: "blue", label: "延迟发布" },
};

const findingSeverityMeta: Record<QualityFinding["severity"], { color: string; label: string }> = {
  blocked: { color: "red", label: "阻断" },
  warning: { color: "gold", label: "警告" },
  info: { color: "blue", label: "提示" },
};

const outputActionLabel: Record<QualityEvaluationReport["gate_decision"]["output_action"], string> = {
  publish_candidate: "允许下游生成发布候选",
  publish_candidate_with_warning: "允许下游带警告生成发布候选",
  return_for_rebuild: "返回候选态重算",
  delay_publication: "等待治理确认后再继续",
};

function formatMetricValue(metric: Pick<QualityMetric, "metric_id" | "actual">) {
  if (metric.metric_id.includes("count")) {
    return String(metric.actual);
  }
  if (Math.abs(metric.actual) <= 1) {
    return `${Math.round(metric.actual * 100)}%`;
  }
  return String(metric.actual);
}

function formatThreshold(metric: Pick<QualityMetric, "metric_id" | "threshold" | "threshold_direction">) {
  const operator = metric.threshold_direction === "gte" ? ">=" : "<=";
  const displayValue = formatMetricValue({ metric_id: metric.metric_id, actual: metric.threshold });
  return `${operator} ${displayValue}`;
}

function compactIds(ids: string[]) {
  if (!ids.length) {
    return "无";
  }
  if (ids.length <= 3) {
    return ids.join(" / ");
  }
  return `${ids.slice(0, 3).join(" / ")} 等 ${ids.length} 项`;
}

function uniqueIds(ids: string[]) {
  return Array.from(new Set(ids.filter(Boolean)));
}

function getAllMetrics(report: QualityEvaluationReport | null) {
  if (!report) {
    return [];
  }
  return [...report.knowledge_quality.metrics, ...report.graph_quality.metrics];
}

function findMetric(metrics: QualityMetric[], metricId: string) {
  return metrics.find((metric) => metric.metric_id === metricId) ?? null;
}

function buildQualityMetricSummary(report: QualityEvaluationReport, metrics: QualityMetric[]): QualityMetricSummary {
  const evidenceMetric = findMetric(metrics, "knowledge.evidence_coverage");
  const relationMetric = findMetric(metrics, "graph.relation_confidence_avg");
  const orphanMetric = findMetric(metrics, "graph.orphan_node_rate");
  const duplicateRelationMetric = findMetric(metrics, "graph.duplicate_relation_rate");
  const duplicateKnowledgeMetric = findMetric(metrics, "knowledge.duplicate_rate");
  const conflictMetric = findMetric(metrics, "knowledge.conflict_rate");
  const warningOrFailedObjectIds = uniqueIds(
    metrics.flatMap((metric) => (metric.status === "pass" ? [] : metric.affected_object_ids)),
  );
  const evidenceAnchorIds = uniqueIds([
    ...metrics.flatMap((metric) => metric.evidence_anchor_ids),
    ...report.rule_hits.flatMap((hit) => hit.evidence_anchor_ids),
  ]);
  const hasResolutionLineage = report.data_lineage.some(
    (item) => item.artifact_type === "ArchiveKnowledgeResolutionSnapshot",
  );

  return {
    evidenceCoverage: evidenceMetric?.actual ?? report.knowledge_quality.evidence_coverage,
    relationCompleteness: Math.max(
      0,
      Math.min(relationMetric?.actual ?? report.graph_quality.relation_confidence_avg, 1 - (duplicateRelationMetric?.actual ?? 0)),
    ),
    orphanNodeRate: orphanMetric?.actual ?? report.graph_quality.orphan_node_rate,
    crossDocumentVerificationCount: evidenceAnchorIds.length,
    mergedObjectCount: Math.max(hasResolutionLineage ? 1 : 0, duplicateKnowledgeMetric?.affected_object_ids.length ?? 0),
    conflictObjectCount: (conflictMetric?.actual ?? report.knowledge_quality.conflict_rate) > 0
      ? conflictMetric?.affected_object_ids.length ?? report.gate_decision.affected_object_ids.length
      : 0,
    lowConfidenceObjectCount: warningOrFailedObjectIds.length,
    ruleHitCount: report.rule_hits.length,
  };
}

function getHeadlineMetrics(metrics: QualityMetric[]) {
  const byId = new Map(metrics.map((metric) => [metric.metric_id, metric]));
  return headlineMetricIds.map((metricId) => byId.get(metricId)).filter((metric): metric is QualityMetric => Boolean(metric));
}

function getDecisionQuestions(report: QualityEvaluationReport) {
  const warningMetrics = report.gate_decision.metric_results.filter((metric) => metric.status === "warning");
  const failedMetrics = report.gate_decision.metric_results.filter((metric) => metric.status === "fail");
  const evidenceMetric = report.gate_decision.metric_results.find((metric) => metric.metric_id === "knowledge.evidence_coverage");
  const explainMetric = report.gate_decision.metric_results.find((metric) => metric.metric_id === "graph.explainability_coverage");

  return [
    {
      key: "trust",
      title: "为什么可信",
      text:
        evidenceMetric && explainMetric
          ? `证据覆盖达到 ${formatMetricValue(evidenceMetric)}，图谱解释覆盖达到 ${formatMetricValue(explainMetric)}，指标可追溯到规则执行记录。`
          : "知识质量和图谱质量均来自运行快照中的规则执行记录，不读取其它模块页面状态。",
    },
    {
      key: "warning",
      title: "为什么警告",
      text: warningMetrics.length
        ? `警告指标为 ${warningMetrics.map((metric) => metric.metric_name).join("、")}，需要携带门禁解释继续。`
        : "当前没有警告指标。",
    },
    {
      key: "gate",
      title: "为什么阻断或放行",
      text: failedMetrics.length
        ? `失败指标为 ${failedMetrics.map((metric) => metric.metric_name).join("、")}，门禁要求候选态重算。`
        : report.gate_decision.explanation,
    },
  ];
}

function QualityDecisionSummary({ report, envelope }: { report: QualityEvaluationReport; envelope: QualityGraphReportEnvelope }) {
  const decision = decisionMeta[report.gate_decision.decision];

  return (
    <Card className="p1-clean-card quality-decision-card" title="质量决策摘要">
      <Alert
        type={decision.alertType}
        showIcon
        message={`${decision.label}，评分 ${report.gate_decision.score}`}
        description={report.gate_decision.explanation}
      />
      <Descriptions className="quality-descriptions" column={{ xs: 1, md: 2, xl: 4 }} size="small">
        <Descriptions.Item label="评估合同">{envelope.contract_version}</Descriptions.Item>
        <Descriptions.Item label="数据来源">{envelope.source_kind}</Descriptions.Item>
        <Descriptions.Item label="运行快照">{report.run_id}</Descriptions.Item>
        <Descriptions.Item label="下游动作解释">{outputActionLabel[report.gate_decision.output_action]}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function QualityFindingPanel({ report }: { report: QualityEvaluationReport }) {
  const findingReport = report.quality_finding_report;
  if (!findingReport) {
    return null;
  }

  return (
    <Card className="p1-clean-card" title="对象级质量发现">
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Space wrap>
          <Tag color={findingReport.summary.publish_blocked ? "red" : "green"}>
            {findingReport.summary.publish_blocked ? "阻断发布" : "允许发布"}
          </Tag>
          <Tag color="red">阻断 {findingReport.summary.blocked_count}</Tag>
          <Tag color="gold">警告 {findingReport.summary.warning_count}</Tag>
          <Tag color="blue">提示 {findingReport.summary.info_count}</Tag>
          {findingReport.resolution_snapshot_id ? <Tag>resolution {findingReport.resolution_snapshot_id}</Tag> : null}
        </Space>
        <List
          size="small"
          dataSource={findingReport.findings.slice(0, 8)}
          renderItem={(finding) => {
            const severity = findingSeverityMeta[finding.severity];
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
  );
}

function HeadlineMetrics({ metrics }: { metrics: QualityMetric[] }) {
  if (!metrics.length) {
    return null;
  }

  return (
    <Row gutter={[16, 16]}>
      {metrics.map((metric) => {
        const status = metricStatusMeta[metric.status];
        return (
          <Col xs={24} md={12} xl={6} key={metric.metric_id}>
            <Card className="p1-clean-card quality-metric-card">
              <Space direction="vertical" size={8} className="quality-card-stack">
                <Space className="quality-card-heading">
                  <Typography.Text type="secondary">{metric.metric_name}</Typography.Text>
                  <Tag color={status.color}>{status.label}</Tag>
                </Space>
                <Statistic value={formatMetricValue(metric)} />
                <Progress
                  percent={Math.min(Math.round(metric.actual * 100), 100)}
                  status={metric.status === "fail" ? "exception" : metric.status === "warning" ? "active" : "success"}
                  showInfo={false}
                />
                <Typography.Paragraph type="secondary">{metric.explanation}</Typography.Paragraph>
              </Space>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}

function QualityMetricSummaryPanel({ summary }: { summary: QualityMetricSummary }) {
  const items = [
    { key: "evidence", title: "证据覆盖率", value: `${Math.round(summary.evidenceCoverage * 100)}%`, hint: "对象可追溯到原文证据锚点的比例" },
    { key: "relation", title: "关系完整性", value: `${Math.round(summary.relationCompleteness * 100)}%`, hint: "关系可信度与重复关系率综合后的可用度" },
    { key: "orphan", title: "孤立节点比例", value: `${Math.round(summary.orphanNodeRate * 100)}%`, hint: "没有入边或出边的节点比例" },
    { key: "cross-doc", title: "跨文档验证", value: summary.crossDocumentVerificationCount, hint: "可用于解释的证据锚点数量" },
    { key: "merged", title: "合并对象数量", value: summary.mergedObjectCount, hint: "归并快照或重复候选触达的对象数" },
    { key: "conflict", title: "冲突对象数量", value: summary.conflictObjectCount, hint: "冲突率指标影响的对象数" },
    { key: "low-confidence", title: "低置信对象数量", value: summary.lowConfidenceObjectCount, hint: "警告或失败指标影响的对象数" },
    { key: "rules", title: "规则命中摘要", value: summary.ruleHitCount, hint: "参与质量门禁解释的规则命中数" },
  ];

  return (
    <Card className="p1-clean-card" title="质量关键摘要">
      <Row gutter={[12, 12]}>
        {items.map((item) => (
          <Col xs={12} md={6} xl={3} key={item.key}>
            <div className="quality-summary-cell">
              <Typography.Text type="secondary">{item.title}</Typography.Text>
              <strong>{item.value}</strong>
              <span>{item.hint}</span>
            </div>
          </Col>
        ))}
      </Row>
    </Card>
  );
}

function QualityIssueBuckets({ report, metrics }: { report: QualityEvaluationReport; metrics: QualityMetric[] }) {
  const orphanMetric = findMetric(metrics, "graph.orphan_node_rate");
  const conflictMetric = findMetric(metrics, "knowledge.conflict_rate");
  const lowConfidenceObjectIds = uniqueIds(
    metrics.flatMap((metric) => (metric.status === "pass" ? [] : metric.affected_object_ids)),
  );
  const lowConfidenceRelationIds = uniqueIds(
    metrics.flatMap((metric) => (metric.status === "pass" ? [] : metric.affected_relation_ids)),
  );
  const buckets: Array<{
    key: string;
    title: string;
    status: QualityMetric["status"];
    ids: string[];
    description: string;
  }> = [
    {
      key: "orphan",
      title: "孤立节点",
      status: orphanMetric?.status ?? "pass",
      ids: orphanMetric?.affected_object_ids ?? [],
      description: orphanMetric?.explanation ?? "当前图谱没有发现孤立节点。",
    },
    {
      key: "conflict",
      title: "冲突对象",
      status: conflictMetric?.status ?? "pass",
      ids: (conflictMetric?.actual ?? report.knowledge_quality.conflict_rate) > 0 ? conflictMetric?.affected_object_ids ?? [] : [],
      description: conflictMetric?.explanation ?? "当前未发现冲突对象。",
    },
    {
      key: "low-confidence",
      title: "低置信对象",
      status: lowConfidenceObjectIds.length ? "warning" : "pass",
      ids: lowConfidenceObjectIds,
      description: "来自警告或失败指标的受影响对象，需要优先补证据、复核关系方向或重算候选。",
    },
    {
      key: "low-confidence-relations",
      title: "低置信关系",
      status: lowConfidenceRelationIds.length ? "warning" : "pass",
      ids: lowConfidenceRelationIds,
      description: "来自警告或失败指标的受影响关系，决定发布候选是否需要携带质量警告。",
    },
  ];

  return (
    <Card className="p1-clean-card" title="质量问题对象">
      <Row gutter={[12, 12]}>
        {buckets.map((bucket) => {
          const status = metricStatusMeta[bucket.status];
          return (
            <Col xs={24} md={12} xl={6} key={bucket.key}>
              <div className="quality-issue-cell">
                <Space className="quality-card-heading">
                  <Typography.Text strong>{bucket.title}</Typography.Text>
                  <Tag color={status.color}>{status.label}</Tag>
                </Space>
                <Typography.Paragraph type="secondary">{bucket.description}</Typography.Paragraph>
                <div className="quality-tag-list">
                  {bucket.ids.length ? (
                    bucket.ids.slice(0, 8).map((id) => <Tag key={id}>{id}</Tag>)
                  ) : (
                    <Tag color="green">无</Tag>
                  )}
                </div>
              </div>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}

function MetricTable({ metrics }: { metrics: QualityMetric[] }) {
  const columns: ColumnsType<QualityMetric> = [
    { title: "指标", dataIndex: "metric_name", width: 170 },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (status: QualityMetric["status"]) => <Tag color={metricStatusMeta[status].color}>{metricStatusMeta[status].label}</Tag>,
    },
    {
      title: "实际值",
      width: 90,
      render: (_, record) => formatMetricValue(record),
    },
    {
      title: "阈值",
      width: 110,
      render: (_, record) => formatThreshold(record),
    },
    { title: "解释", dataIndex: "explanation" },
    {
      title: "影响对象",
      width: 190,
      render: (_, record) => compactIds([...record.affected_object_ids, ...record.affected_relation_ids]),
    },
  ];

  return (
    <Card className="p1-clean-card" title="质量指标集合">
      <Table rowKey="metric_id" columns={columns} dataSource={metrics} pagination={false} scroll={{ x: 980 }} />
    </Card>
  );
}

function RuleHitTable({ ruleHits }: { ruleHits: QualityRuleHitExplanation[] }) {
  const columns: ColumnsType<QualityRuleHitExplanation> = [
    { title: "规则", dataIndex: "rule_id", width: 180 },
    { title: "版本", dataIndex: "rule_version", width: 80 },
    { title: "决策", dataIndex: "decision", width: 130 },
    {
      title: "命中指标",
      width: 220,
      render: (_, record) => compactIds(record.metric_ids),
    },
    {
      title: "证据锚点",
      width: 180,
      render: (_, record) => compactIds(record.evidence_anchor_ids),
    },
    { title: "解释链", dataIndex: "explanation" },
  ];

  return (
    <Card className="p1-clean-card" title="规则命中解释">
      <Table rowKey="hit_id" columns={columns} dataSource={ruleHits} pagination={false} scroll={{ x: 980 }} />
    </Card>
  );
}

function GraphExplainability({
  report,
  graph,
  summary,
}: {
  report: QualityEvaluationReport;
  graph: ArchiveKnowledgeGraph | null;
  summary: ArchiveKnowledgeSummary | null;
}) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={14}>
        <Card className="p1-clean-card" title="图谱可解释性报告">
          <div className="p1-clean-graph quality-explainability-graph">
            <div className="p1-clean-node input">概念质量<br />{formatMetricValue({ metric_id: "knowledge.concept_precision", actual: report.knowledge_quality.concept_precision })}</div>
            <div className="p1-clean-edge">证据</div>
            <div className="p1-clean-node rule">规则命中<br />{report.rule_hits.length} 条</div>
            <div className="p1-clean-edge">解释</div>
            <div className="p1-clean-node output">关系质量<br />{formatMetricValue({ metric_id: "graph.relation_confidence_avg", actual: report.graph_quality.relation_confidence_avg })}</div>
          </div>
          <Descriptions className="quality-descriptions" column={{ xs: 1, md: 2 }} size="small">
            <Descriptions.Item label="运行图谱投影">{report.graph_quality.graph_projection_id}</Descriptions.Item>
            <Descriptions.Item label="解释覆盖率">{formatMetricValue({ metric_id: "graph.explainability_coverage", actual: report.graph_quality.explainability_coverage })}</Descriptions.Item>
            <Descriptions.Item label="孤立节点率">{formatMetricValue({ metric_id: "graph.orphan_node_rate", actual: report.graph_quality.orphan_node_rate })}</Descriptions.Item>
            <Descriptions.Item label="重复关系率">{formatMetricValue({ metric_id: "graph.duplicate_relation_rate", actual: report.graph_quality.duplicate_relation_rate })}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card className="p1-clean-card" title="知识库图谱背景">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="文档数">{summary?.document_count ?? 0}</Descriptions.Item>
            <Descriptions.Item label="实体 / 事件 / 流程">
              {(summary?.entity_count ?? 0)} / {(summary?.event_count ?? 0)} / {(summary?.process_count ?? 0)}
            </Descriptions.Item>
            <Descriptions.Item label="图谱节点 / 边">
              {(graph?.nodes.length ?? 0)} / {(graph?.edges.length ?? 0)}
            </Descriptions.Item>
            <Descriptions.Item label="数据血缘">{compactIds(report.data_lineage.map((item) => item.artifact_id))}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );
}

function RecommendedActions({ report }: { report: QualityEvaluationReport }) {
  const questions = getDecisionQuestions(report);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={14}>
        <Card className="p1-clean-card" title="门禁解释问答">
          <List
            dataSource={questions}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta title={item.title} description={item.text} />
              </List.Item>
            )}
          />
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card className="p1-clean-card" title="建议动作">
          {report.knowledge_quality.recommended_actions.length ? (
            <List
              size="small"
              dataSource={report.knowledge_quality.recommended_actions}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前无需额外修复动作" />
          )}
        </Card>
      </Col>
    </Row>
  );
}

export function QualityGraphPage({ context }: P1ModulePageProps) {
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [graph, setGraph] = useState<ArchiveKnowledgeGraph | null>(null);
  const [reportEnvelope, setReportEnvelope] = useState<QualityGraphReportEnvelope | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadQualityGraph() {
      try {
        setLoading(true);
        const [summaryResponse, graphResponse] = await Promise.all([
          qualityGraphApi.getArchiveSummary(context.archiveId),
          qualityGraphApi.getArchiveGraph(context.archiveId),
        ]);

        let reportResponse: { data: QualityGraphReportEnvelope } | null = null;
        if (context.runtimeSnapshotId && context.policyPackageVersionId) {
          reportResponse = await qualityGraphApi.getQualityGraphReport({
            archiveId: context.archiveId,
            runtimeSnapshotId: context.runtimeSnapshotId,
            policyPackageVersionId: context.policyPackageVersionId,
          });
        }

        if (cancelled) {
          return;
        }
        setSummary(summaryResponse.data);
        setGraph(graphResponse.data);
        setReportEnvelope(reportResponse?.data ?? null);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "质量图谱加载失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadQualityGraph();
    return () => {
      cancelled = true;
    };
  }, [context.archiveId, context.policyPackageVersionId, context.runtimeSnapshotId]);

  const report = reportEnvelope?.data ?? null;
  const allMetrics = useMemo(() => getAllMetrics(report), [report]);
  const headlineMetrics = useMemo(() => getHeadlineMetrics(allMetrics), [allMetrics]);
  const qualityMetricSummary = useMemo(
    () => (report ? buildQualityMetricSummary(report, allMetrics) : null),
    [allMetrics, report],
  );
  const missingInput = !context.runtimeSnapshotId || !context.policyPackageVersionId;

  return (
    <PageFrame
      eyebrow="质量图谱模块"
      title="质量图谱"
      description="消费运行快照和策略版本，解释概念质量、关系质量、证据覆盖、图谱可解释性，以及门禁为什么通过、警告或阻断。"
    >
      <Alert
        className="p1-clean-alert"
        type={missingInput ? "warning" : "info"}
        showIcon
        message={`当前运行快照：${context.runtimeSnapshotId ?? "等待抽取运行输出"}`}
        description={`策略版本：${context.policyPackageVersionId ?? "等待策略冻结"}。质量模块只消费 archiveId、runtimeSnapshotId、policyPackageVersionId，不直接生成发布候选。`}
      />

      {error ? <Alert className="p1-clean-alert" type="error" showIcon message="质量图谱加载失败" description={error} /> : null}
      {loading ? <Skeleton active paragraph={{ rows: 8 }} /> : null}

      {!loading && !report && !missingInput ? (
        <Empty className="quality-empty" description="暂无质量评估报告" />
      ) : null}

      {!loading && missingInput ? (
        <Card className="p1-clean-card">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="需要运行快照和策略版本后才能生成质量解释" />
        </Card>
      ) : null}

      {!loading && report && reportEnvelope ? (
        <Space direction="vertical" size={16} className="quality-page-stack">
          <QualityDecisionSummary report={report} envelope={reportEnvelope} />
          <QualityFindingPanel report={report} />
          <HeadlineMetrics metrics={headlineMetrics} />
          {qualityMetricSummary ? <QualityMetricSummaryPanel summary={qualityMetricSummary} /> : null}
          <QualityIssueBuckets report={report} metrics={allMetrics} />
          <MetricTable metrics={allMetrics} />
          <RuleHitTable ruleHits={report.rule_hits} />
          <GraphExplainability report={report} graph={graph} summary={summary} />
          <RecommendedActions report={report} />
        </Space>
      ) : null}
    </PageFrame>
  );
}
