import { Alert, Button, Card, Col, Divider, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { ReactElement } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getP1EvaluationReport } from "../api/p1RefactorApi";
import type { EvaluationRunReport, P1ResponseEnvelope, QualityMetric, RuleHitExplanation } from "../contracts";
import { p1R0EvaluationReport } from "../fixtures/p1R0Fixtures";
import "./QualityDashboardPage.css";

const defaultArchiveId = "archive-contract-demo";
const defaultRunId = "RUN-P1-R0-001";

type GateDecision = NonNullable<EvaluationRunReport["gate_decision"]>;

const decisionColor: Record<GateDecision["decision"], string> = {
  auto_pass: "green",
  warn_continue: "gold",
  block: "red",
  defer: "purple",
};

const decisionText: Record<GateDecision["decision"], string> = {
  auto_pass: "自动通过",
  warn_continue: "带警告继续",
  block: "阻断返回",
  defer: "延迟发布",
};

const actionText: Record<GateDecision["output_action"], string> = {
  publish_candidate: "生成发布候选",
  publish_candidate_with_warning: "生成带警告发布候选",
  return_for_rebuild: "返回重算",
  delay_publication: "延迟发布",
};

const statusColor: Record<QualityMetric["status"], string> = {
  pass: "green",
  warning: "gold",
  fail: "red",
};

const statusText: Record<QualityMetric["status"], string> = {
  pass: "通过",
  warning: "警告",
  fail: "失败",
};

function formatRatio(value: number): string {
  if (value <= 1) {
    return `${Math.round(value * 100)}%`;
  }
  return `${value}`;
}

function compactTags(values: readonly string[] | null | undefined): ReactElement {
  const tagValues = values ?? [];
  if (!tagValues.length) {
    return <Typography.Text type="secondary">-</Typography.Text>;
  }
  return (
    <Space size={[4, 4]} wrap>
      {tagValues.slice(0, 3).map((value) => (
        <Tag key={value}>{value}</Tag>
      ))}
      {tagValues.length > 3 ? <Tag>+{tagValues.length - 3}</Tag> : null}
    </Space>
  );
}

const fallbackGateDecision: GateDecision = {
  decision: "defer",
  score: 0,
  metric_results: [],
  rule_hits: [],
  metric_hits: [],
  affected_object_ids: [],
  affected_relation_ids: [],
  output_action: "delay_publication",
  explanation: "质量门禁结论暂不可用。",
  generated_at: defaultRunId,
};

export function QualityDashboardPage() {
  const [report, setReport] = useState<P1ResponseEnvelope<EvaluationRunReport>>(p1R0EvaluationReport);
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    void getP1EvaluationReport(defaultArchiveId, defaultRunId)
      .then((response) => {
        if (!cancelled) {
          setReport(response);
          setApiWarning(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "未知错误";
          setReport({
            ...p1R0EvaluationReport,
            source_kind: "mock_fallback",
            warnings: [`后端 evaluation-report adapter 暂不可用：${message}`],
          });
          setApiWarning(`后端 evaluation-report adapter 暂不可用，当前显示前端 fallback：${message}`);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const data = report.data;
  const gateDecision = data.gate_decision ?? data.knowledge_quality.gate_decision ?? fallbackGateDecision;
  const metricRows = useMemo(
    () => [
      ...data.knowledge_quality.metrics.map((metric) => ({ ...metric, group: "知识质量" })),
      ...data.graph_quality.metrics.map((metric) => ({ ...metric, group: "图谱质量" })),
    ],
    [data.graph_quality.metrics, data.knowledge_quality.metrics],
  );

  const metricColumns: ColumnsType<(typeof metricRows)[number]> = [
    {
      title: "指标",
      dataIndex: "metric_name",
      key: "metric_name",
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.metric_name}</Typography.Text>
          <Typography.Text type="secondary">{row.metric_id}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "分组",
      dataIndex: "group",
      key: "group",
      width: 96,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: "实际 / 阈值",
      key: "actual",
      width: 132,
      render: (_, row) => (
        <Typography.Text>
          {formatRatio(row.actual)} {row.threshold_direction === "gte" ? ">=" : "<="} {formatRatio(row.threshold)}
        </Typography.Text>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 92,
      render: (value: QualityMetric["status"]) => <Tag color={statusColor[value]}>{statusText[value]}</Tag>,
    },
    {
      title: "追踪对象",
      key: "trace",
      render: (_, row) => (
        <Space direction="vertical" size={4}>
          {compactTags(row.affected_object_ids)}
          {(row.affected_relation_ids ?? []).length ? compactTags(row.affected_relation_ids) : null}
        </Space>
      ),
    },
    {
      title: "解释",
      dataIndex: "explanation",
      key: "explanation",
    },
  ];

  const ruleColumns: ColumnsType<RuleHitExplanation> = [
    {
      title: "规则",
      dataIndex: "rule_id",
      key: "rule_id",
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.rule_id}</Typography.Text>
          <Typography.Text type="secondary">
            {row.rule_version} · {row.rule_hash}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "决策",
      dataIndex: "decision",
      key: "decision",
      width: 130,
      render: (value: string) => <Tag color={value === "warn_continue" ? "gold" : "blue"}>{value}</Tag>,
    },
    {
      title: "输入 / 输出",
      key: "artifacts",
      render: (_, row) => (
        <Space direction="vertical" size={4}>
          <Typography.Text>输入：{row.input_artifact_refs.map((item) => item.artifact_id).join(", ")}</Typography.Text>
          <Typography.Text>输出：{row.output_artifact_refs.map((item) => item.artifact_id).join(", ")}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "影响对象",
      key: "affected",
      render: (_, row) => compactTags([...(row.affected_object_ids ?? []), ...(row.affected_relation_ids ?? [])]),
    },
    {
      title: "证据锚点",
      key: "anchors",
      render: (_, row) => compactTags(row.evidence_anchor_ids),
    },
  ];

  return (
    <main className="p1-quality-page">
      <section className="p1-quality-hero">
        <div>
          <Tag color="geekblue">W4 质量评估</Tag>
          <Typography.Title className="p1-quality-title">知识质量与图谱质量评测</Typography.Title>
          <Typography.Text type="secondary">
            {data.archive_id} · {data.run_id}
          </Typography.Text>
        </div>
        <Space wrap>
          <Tag color={report.source_kind === "live" ? "green" : report.source_kind === "fixture" ? "blue" : "orange"}>
            {report.source_kind}
          </Tag>
          <Button>
            <Link to="/p1">返回 P1 入口</Link>
          </Button>
        </Space>
      </section>

      {apiWarning ? <Alert type="warning" showIcon message={apiWarning} style={{ marginBottom: 16 }} /> : null}
      {report.warnings?.map((warning) => (
        <Alert key={warning} type="warning" showIcon message={warning} style={{ marginBottom: 16 }} />
      ))}

      <Row gutter={[16, 16]} className="p1-quality-summary">
        <Col xs={24} lg={8}>
          <Card>
            <Statistic
              title="质量门禁"
              value={decisionText[gateDecision.decision]}
              valueStyle={{ color: decisionColor[gateDecision.decision] }}
            />
            <Typography.Paragraph className="p1-quality-card-note">{gateDecision.explanation}</Typography.Paragraph>
            <Tag color={decisionColor[gateDecision.decision]}>{actionText[gateDecision.output_action]}</Tag>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic title="概念精度" value={formatRatio(data.knowledge_quality.concept_precision)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic title="证据覆盖率" value={formatRatio(data.knowledge_quality.evidence_coverage)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic title="关系可信度" value={formatRatio(data.graph_quality.relation_confidence_avg)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic title="可解释覆盖率" value={formatRatio(data.graph_quality.explainability_coverage)} />
          </Card>
        </Col>
      </Row>

      <Card className="p1-quality-panel" title="质量指标解释">
        <Table rowKey="metric_id" columns={metricColumns} dataSource={metricRows} pagination={false} />
      </Card>

      <Card className="p1-quality-panel" title="规则命中追踪">
        <Table rowKey="hit_id" columns={ruleColumns} dataSource={data.rule_hits} pagination={false} />
        <Divider />
        <Typography.Text strong>数据血缘</Typography.Text>
        <div className="p1-quality-lineage">
          {data.data_lineage.map((item) => (
            <Tag key={item.artifact_id} color="cyan">
              {item.artifact_type}: {item.artifact_id}
            </Tag>
          ))}
        </div>
      </Card>
    </main>
  );
}
