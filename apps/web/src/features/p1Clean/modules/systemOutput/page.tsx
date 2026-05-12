import { useEffect, useMemo, useState } from "react";

import { Alert, Card, Col, Descriptions, Empty, Row, Space, Spin, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { ArchivePublicationOverview } from "../../../../lib/api";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { systemOutputApi } from "./api";
import type {
  DownstreamConsumptionGuide,
  SystemOutputContract,
  SystemOutputEndpoint,
  SystemReadableEvidence,
  SystemReadableKnowledgeObject,
  SystemReadableKnowledgeRelation,
} from "./types";

type SystemOutputState = {
  contract: SystemOutputContract | null;
  publication: ArchivePublicationOverview | null;
  selectedPublicationSnapshotId: string | null;
  warnings: string[];
  loading: boolean;
  error: string | null;
};

const emptySummary = {
  document_count: 0,
  entity_count: 0,
  event_count: 0,
  process_count: 0,
};

const emptyState: SystemOutputState = {
  contract: null,
  publication: null,
  selectedPublicationSnapshotId: null,
  warnings: [],
  loading: false,
  error: null,
};

function readErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "正式输出合同读取失败";
}

export function SystemOutputPage({ context }: P1ModulePageProps) {
  const [state, setState] = useState<SystemOutputState>(emptyState);
  const publicationSnapshotId = context.publicationSnapshotId;

  useEffect(() => {
    let alive = true;
    setState((previous) => ({ ...previous, loading: true, error: null, warnings: [] }));

    async function loadSystemOutput() {
      const warnings: string[] = [];
      let selectedPublicationSnapshotId = publicationSnapshotId ?? null;

      if (!selectedPublicationSnapshotId) {
        try {
          const candidateResponse = await systemOutputApi.getPublicationCandidateSnapshot(
            context.archiveId,
            context.runtimeSnapshotId,
            context.policyPackageVersionId,
          );
          selectedPublicationSnapshotId =
            candidateResponse.data.data.publication_snapshot_id ??
            candidateResponse.data.data.publication_candidate_snapshot_id;
          warnings.push(...(candidateResponse.data.warnings ?? []));
        } catch {
          warnings.push("未能读取发布候选 publicationSnapshotId，系统间输出保持不可供应。");
        }
      }

      const [publicationResponse, contractResponse] = await Promise.all([
        systemOutputApi.getArchivePublication(context.archiveId),
        systemOutputApi.getSystemOutputContract(context.archiveId, selectedPublicationSnapshotId),
      ]);

      if (!alive) return;
      setState({
        publication: publicationResponse.data,
        contract: contractResponse.data.data,
        selectedPublicationSnapshotId,
        warnings: [...warnings, ...(contractResponse.data.warnings ?? [])],
        loading: false,
        error: null,
      });
    }

    loadSystemOutput().catch((error: unknown) => {
      if (!alive) return;
      setState((previous) => ({
        ...previous,
        loading: false,
        error: readErrorMessage(error),
      }));
    });

    return () => {
      alive = false;
    };
  }, [context.archiveId, context.policyPackageVersionId, context.runtimeSnapshotId, publicationSnapshotId]);

  const endpointColumns: ColumnsType<SystemOutputEndpoint> = useMemo(
    () => [
      {
        title: "方法",
        dataIndex: "method",
        width: 90,
        render: (value: SystemOutputEndpoint["method"]) => (
          <Tag color={value === "GET" ? "blue" : "green"}>{value}</Tag>
        ),
      },
      { title: "接口", dataIndex: "path" },
      { title: "用途", dataIndex: "purpose" },
      {
        title: "来源边界",
        dataIndex: "source",
        width: 120,
        render: () => <Tag color="success">正式快照</Tag>,
      },
    ],
    [],
  );

  const objectColumns: ColumnsType<SystemReadableKnowledgeObject> = useMemo(
    () => [
      {
        title: "对象",
        dataIndex: "name",
        render: (value: string, row) => (
          <Space direction="vertical" size={0}>
            <Typography.Text strong>{value}</Typography.Text>
            <Typography.Text type="secondary">{row.object_id}</Typography.Text>
          </Space>
        ),
      },
      { title: "类型", dataIndex: "item_type", width: 120 },
      { title: "证据", dataIndex: "evidence_count", width: 90 },
      { title: "版本", dataIndex: "version_id", width: 160 },
    ],
    [],
  );

  const relationColumns: ColumnsType<SystemReadableKnowledgeRelation> = useMemo(
    () => [
      { title: "关系", dataIndex: "relation_type", width: 150 },
      { title: "起点", dataIndex: "source_object_id" },
      { title: "终点", dataIndex: "target_object_id" },
      { title: "版本", dataIndex: "version_id", width: 160 },
    ],
    [],
  );

  const evidenceColumns: ColumnsType<SystemReadableEvidence> = useMemo(
    () => [
      { title: "对象", dataIndex: "object_id", width: 180 },
      { title: "文档", dataIndex: "document_id", width: 160 },
      {
        title: "证据摘录",
        dataIndex: "excerpt",
        render: (value: string | null | undefined) => value || "无摘录",
      },
    ],
    [],
  );

  const consumerColumns: ColumnsType<DownstreamConsumptionGuide> = useMemo(
    () => [
      { title: "系统", dataIndex: "consumer", width: 80, render: (value: string) => <Tag>{value}</Tag> },
      { title: "消费方式", dataIndex: "read_pattern" },
      { title: "说明", dataIndex: "notes", render: (notes: string[]) => notes.join(" / ") },
    ],
    [],
  );

  const contract = state.contract;
  const sourceSummary = contract?.source_summary ?? emptySummary;
  const currentVersion = state.publication?.current_version;
  const supplyAvailable = Boolean(contract?.supply_available);
  const selectedPublicationSnapshotId =
    contract?.publication_snapshot_id ?? state.selectedPublicationSnapshotId ?? publicationSnapshotId;

  return (
    <PageFrame
      eyebrow="系统间输出接口模块"
      title="系统间输出接口"
      description="面向 P2/P3/P6 等后续系统供应正式知识合同；候选态只显示不可供应原因和预览边界。"
    >
      <Spin spinning={state.loading}>
        {state.error ? (
          <Alert className="p1-clean-alert" type="error" showIcon message="正式输出合同读取失败" description={state.error} />
        ) : null}
        {state.warnings.length ? (
          <Alert className="p1-clean-alert" type="warning" showIcon message="系统间输出告警" description={state.warnings.join("；")} />
        ) : null}
        <Alert
          className="p1-clean-alert"
          type={supplyAvailable ? "success" : "warning"}
          showIcon
          message={supplyAvailable ? "正式知识输出合同已就绪" : "正式知识不可供应"}
          description={
            supplyAvailable
              ? "当前输出只暴露治理确认后的正式对象、关系、证据和版本号。"
              : contract?.unavailable_reason ?? "尚未取得可供后续系统消费的正式版本。"
          }
        />

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={10}>
            <Card className="p1-clean-card" title="输出合同">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="合同版本">{contract?.contract_version ?? "P1CleanSystemOutputContract.v1"}</Descriptions.Item>
                <Descriptions.Item label="archiveId">{context.archiveId}</Descriptions.Item>
                <Descriptions.Item label="publicationSnapshotId">
                  <Typography.Text code>{selectedPublicationSnapshotId ?? "等待发布模块输出"}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="是否正式入库">{supplyAvailable ? "是" : "否"}</Descriptions.Item>
                <Descriptions.Item label="正式版本">
                  {contract?.formal_version ?? currentVersion?.version_label ?? "尚未正式入库"}
                </Descriptions.Item>
                <Descriptions.Item label="formalVersionId">
                  {contract?.formal_version_id ?? contract?.canonical_publication_snapshot_id ?? "无"}
                </Descriptions.Item>
                <Descriptions.Item label="治理确认人">
                  {contract?.governed_by ?? currentVersion?.publisher ?? "无"}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col xs={24} xl={14}>
            <Row gutter={[16, 16]}>
              <Col xs={12} md={6}>
                <Card className="p1-clean-card">
                  <Statistic title="文档" value={sourceSummary.document_count} />
                </Card>
              </Col>
              <Col xs={12} md={6}>
                <Card className="p1-clean-card">
                  <Statistic title="可读对象" value={contract?.readable_objects.length ?? 0} />
                </Card>
              </Col>
              <Col xs={12} md={6}>
                <Card className="p1-clean-card">
                  <Statistic title="可读关系" value={contract?.readable_relations.length ?? 0} />
                </Card>
              </Col>
              <Col xs={12} md={6}>
                <Card className="p1-clean-card">
                  <Statistic title="证据" value={contract?.readable_evidence.length ?? 0} />
                </Card>
              </Col>
            </Row>
          </Col>
        </Row>

        <Card className="p1-clean-card" title="API 暴露范围">
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Space wrap>
              <Tag color={supplyAvailable ? "green" : "red"}>
                {contract?.api_exposure_scope.exposure_mode ?? "not_available"}
              </Tag>
              {(contract?.api_exposure_scope.blocked_candidate_sources ?? []).map((item) => (
                <Tag color="red" key={item}>{item}</Tag>
              ))}
            </Space>
            <Table
              rowKey="path"
              columns={endpointColumns}
              dataSource={contract?.formal_interfaces ?? []}
              pagination={false}
              locale={{ emptyText: "未正式入库时不暴露正式供应 API" }}
            />
          </Space>
        </Card>

        <Card className="p1-clean-card" title="下游可读取对象、关系和证据">
          {supplyAvailable ? (
            <Space direction="vertical" size="large" style={{ width: "100%" }}>
              <Table rowKey="object_id" columns={objectColumns} dataSource={contract?.readable_objects ?? []} pagination={false} />
              <Table rowKey="relation_id" columns={relationColumns} dataSource={contract?.readable_relations ?? []} pagination={false} />
              <Table rowKey="evidence_id" columns={evidenceColumns} dataSource={contract?.readable_evidence ?? []} pagination={false} />
            </Space>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={contract?.api_exposure_scope.not_supply_reason ?? "等待正式知识供应合同"} />
          )}
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card className="p1-clean-card" title="版本选择规则">
              {contract ? (
                <Space direction="vertical" size="middle">
                  {contract.version_selection_rules.map((rule) => (
                    <div key={rule.rule_id}>
                      <Typography.Text strong>{rule.selected_version_label}</Typography.Text>
                      <Typography.Paragraph>{rule.description}</Typography.Paragraph>
                      <Tag color="purple">{rule.governance_boundary}</Tag>
                    </div>
                  ))}
                </Space>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待合同" />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card className="p1-clean-card" title="adapter 合同">
              {contract ? (
                <Space direction="vertical" size="middle">
                  <Typography.Text strong>{contract.adapter_contract.adapter_name}</Typography.Text>
                  <Typography.Paragraph>{contract.boundary}</Typography.Paragraph>
                  <Space wrap>
                    {contract.adapter_contract.allowed_backend_calls.map((item) => (
                      <Tag color="blue" key={item}>{item}</Tag>
                    ))}
                  </Space>
                  <Space wrap>
                    {contract.adapter_contract.forbidden_sources.map((item) => (
                      <Tag color="red" key={item}>{item}</Tag>
                    ))}
                  </Space>
                </Space>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="adapter 合同未就绪" />
              )}
            </Card>
          </Col>
        </Row>

        <Card className="p1-clean-card" title="P2/P3 消费说明">
          {contract ? (
            <Table
              rowKey="consumer"
              columns={consumerColumns}
              dataSource={contract.downstream_consumers}
              pagination={false}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待正式知识供应合同" />
          )}
        </Card>
      </Spin>
    </PageFrame>
  );
}
