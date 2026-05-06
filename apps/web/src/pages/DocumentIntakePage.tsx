import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Col, Descriptions, Empty, List, Progress, Row, Space, Table, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import { DocumentUploadForm } from "../components/DocumentUploadForm";
import { ValidationDrawer } from "../components/ValidationDrawer";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { api } from "../lib/api";
import type { IntakeDocumentDetail, IntakeDocumentSummary } from "../lib/api";

export function DocumentIntakePage() {
  const [intakeDocuments, setIntakeDocuments] = useState<IntakeDocumentSummary[]>([]);
  const [intakeLoading, setIntakeLoading] = useState(true);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [selectedIntakeDocumentId, setSelectedIntakeDocumentId] = useState<string | null>(null);
  const [intakeDocumentDetail, setIntakeDocumentDetail] = useState<IntakeDocumentDetail | null>(null);
  const [intakeDetailLoading, setIntakeDetailLoading] = useState(false);
  const [intakeDetailError, setIntakeDetailError] = useState<string | null>(null);

  async function loadIntakeDocuments(cancelled?: { current: boolean }) {
    try {
      const response = await api.get<IntakeDocumentSummary[]>("/documents");
      if (cancelled?.current) {
        return;
      }
      setIntakeDocuments(response.data);
      setIntakeError(null);
    } catch (loadError) {
      if (!cancelled?.current) {
        setIntakeError(loadError instanceof Error ? loadError.message : "加载接入文档失败");
      }
    } finally {
      if (!cancelled?.current) {
        setIntakeLoading(false);
      }
    }
  }

  useEffect(() => {
    const cancelled = { current: false };
    void loadIntakeDocuments(cancelled);
    return () => {
      cancelled.current = true;
    };
  }, []);

  useEffect(() => {
    const documentId = selectedIntakeDocumentId;

    if (!documentId) {
      setIntakeDocumentDetail(null);
      setIntakeDetailError(null);
      return;
    }

    let cancelled = false;

    async function loadIntakeDocumentDetail() {
      try {
        setIntakeDetailLoading(true);
        const response = await api.get<IntakeDocumentDetail>(`/documents/${documentId}`);
        if (cancelled) {
          return;
        }
        setIntakeDocumentDetail(response.data);
        setIntakeDetailError(null);
      } catch (loadError) {
        if (!cancelled) {
          setIntakeDetailError(loadError instanceof Error ? loadError.message : "加载解析详情失败");
        }
      } finally {
        if (!cancelled) {
          setIntakeDetailLoading(false);
        }
      }
    }

    void loadIntakeDocumentDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedIntakeDocumentId]);

  const parsedCount = useMemo(
    () => intakeDocuments.filter((item) => item.latest_version?.status === "parsed").length,
    [intakeDocuments],
  );
  const parseFailedCount = useMemo(
    () => intakeDocuments.filter((item) => item.latest_version?.status === "parse_failed").length,
    [intakeDocuments],
  );
  const uploadedCount = useMemo(
    () => intakeDocuments.filter((item) => item.latest_version?.status === "uploaded").length,
    [intakeDocuments],
  );
  const activeIntakeSummary =
    intakeDocuments.find((item) => item.id === selectedIntakeDocumentId) ?? intakeDocuments[0] ?? null;
  const activeParseRun = intakeDocumentDetail?.latest_version?.latest_parse_run ?? activeIntakeSummary?.latest_version?.latest_parse_run ?? null;
  const activeSegments = intakeDocumentDetail?.latest_version?.segments_preview ?? [];
  const totalSegments = activeParseRun?.segment_count ?? activeSegments.length;

  return (
    <ValidationWorkspace
      title="文档接入与解析验证"
      description="上传、解析、结构化预检；这里只验证文档能否进入知识库抽取主链，不代表正式知识入库。"
      actions={
        <Space wrap>
          <Button type="primary">上传文档</Button>
          <Button>选择解析器</Button>
          <Button>批量解析</Button>
          <Link to="/documents">
            <Button>纳入当前知识库</Button>
          </Link>
        </Space>
      }
      stats={[
        { title: "接入文档", value: intakeDocuments.length },
        { title: "已解析", value: parsedCount },
        { title: "解析失败", value: parseFailedCount },
        { title: "待解析", value: uploadedCount },
      ]}
    >
      <Space direction="vertical" size={24} style={{ display: "flex" }}>
        <Alert
          className="p1-hero-alert"
          type="warning"
          showIcon
          message="这是独立的接入验证链"
          description="若要纳入知识库，将进入 13 阶段抽取主链；解析结果会先转成统一文档对象，再进入策略驱动抽取。"
        />

        {intakeError ? <Alert type="error" message="接入文档暂不可用" description={intakeError} showIcon /> : null}

        <Row gutter={[16, 16]} align="stretch">
          <Col xs={24} xl={5}>
            <Card className="p1-soft-card" title="文档接入队列">
              <Space direction="vertical" size={12} style={{ display: "flex" }}>
                <DocumentUploadForm onUploaded={() => loadIntakeDocuments()} />
                <div className="p1-filter-pill-row">
                  <span className="p1-filter-pill is-active">全部 {intakeDocuments.length}</span>
                  <span className="p1-filter-pill">待解析 {uploadedCount}</span>
                  <span className="p1-filter-pill">解析完成 {parsedCount}</span>
                  <span className="p1-filter-pill">失败 {parseFailedCount}</span>
                </div>
                <Table
                  rowKey="id"
                  loading={intakeLoading}
                  dataSource={intakeDocuments}
                  locale={{ emptyText: "暂无接入文档" }}
                  pagination={{ pageSize: 6, size: "small" }}
                  showHeader={false}
                  columns={[
                    {
                      title: "文档",
                      render: (_: unknown, record: IntakeDocumentSummary) => (
                        <Space direction="vertical" size={4} style={{ display: "flex" }}>
                          <Space wrap>
                            <Typography.Text strong>{record.title}</Typography.Text>
                            <Tag color={record.latest_version?.status === "parsed" ? "success" : record.latest_version?.status === "parse_failed" ? "error" : "processing"}>
                              {mapVersionStatus(record.latest_version?.status)}
                            </Tag>
                          </Space>
                          <Typography.Text type="secondary">
                            {record.source_name} · {record.latest_version?.latest_parse_run?.parser_name ?? "未解析"}
                          </Typography.Text>
                          <Button type="link" style={{ padding: 0 }} onClick={() => setSelectedIntakeDocumentId(record.id)}>
                            查看解析
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Space>
            </Card>
          </Col>

          <Col xs={24} xl={11}>
            <Card className="p1-soft-card" title="解析结果预览">
              <Space direction="vertical" size={14} style={{ display: "flex" }}>
                <div className="p1-card-heading">
                  <div>
                    <Typography.Title level={4}>
                      {activeIntakeSummary ? `解析预览：${activeIntakeSummary.title}` : "请选择文档"}
                    </Typography.Title>
                    <Typography.Text type="secondary">结构化解析结果 / 统一文档前预检</Typography.Text>
                  </div>
                  <Tag color="blue">{activeParseRun?.parser_name ?? "未选择解析器"}</Tag>
                </div>
                <Space wrap>
                  <Button>展开全部</Button>
                  <Button>折叠全部</Button>
                  <Button>仅看表格</Button>
                  <Button>仅看异常节点</Button>
                </Space>
                <div className="p1-parse-tree">
                  {(activeSegments.length ? activeSegments : buildFallbackParseRows(activeIntakeSummary)).map((segment, index) => (
                    <div key={segment.id} className={`p1-tree-row ${index === 0 ? "is-selected" : ""}`}>
                      <span>{`节点：${segment.heading || `段落 ${index + 1}`}`}</span>
                      <Tag>{segment.block_type}</Tag>
                      <Typography.Text type="secondary">{segment.content.length} 字</Typography.Text>
                    </div>
                  ))}
                  {!activeIntakeSummary && <Empty description="暂无解析结果" />}
                </div>
              </Space>
            </Card>
          </Col>

          <Col xs={24} xl={8}>
            <Card className="p1-soft-card p1-detail-panel" title="解析质量与入库准备">
              <Space direction="vertical" size={14} style={{ display: "flex" }}>
                <div className="p1-quality-grid">
                  <div className="p1-quality-tile">
                    <span>覆盖率</span>
                    <strong>{activeParseRun ? "96%" : "--"}</strong>
                  </div>
                  <div className="p1-quality-tile">
                    <span>未识别段落</span>
                    <strong style={{ color: totalSegments > 0 ? "#f97316" : "#94a3b8" }}>{activeParseRun ? Math.max(0, 3 - activeSegments.length) : "--"}</strong>
                  </div>
                  <div className="p1-quality-tile">
                    <span>表格解析质量</span>
                    <strong>{activeParseRun ? "92%" : "--"}</strong>
                  </div>
                  <div className="p1-quality-tile">
                    <span>文档语言</span>
                    <strong>中文</strong>
                  </div>
                </div>
                <Alert
                  type="warning"
                  showIcon
                  message="建议动作"
                  description={activeParseRun ? "可生成统一文档预览，建议补全少量元数据后送入抽取。" : "请先上传并解析文档。"}
                />
                <div>
                  <Typography.Title level={5}>知识内容类型</Typography.Title>
                  <div className="p1-filter-pill-row">
                    <span className="p1-filter-pill">行业规范</span>
                    <span className="p1-filter-pill">需求文档</span>
                    <span className="p1-filter-pill is-active">合同条款</span>
                    <span className="p1-filter-pill">业务流程说明</span>
                  </div>
                </div>
                <div>
                  <Typography.Title level={5}>策略推荐</Typography.Title>
                  <Descriptions size="small" column={1}>
                    <Descriptions.Item label="推荐策略包">合同通用抽取</Descriptions.Item>
                    <Descriptions.Item label="推荐原因">PDF / DOCX 结构稳定，适合结构化抽取</Descriptions.Item>
                    <Descriptions.Item label="可用版本">v3.12</Descriptions.Item>
                  </Descriptions>
                </div>
                <Space wrap>
                  <Button type="primary">接受推荐策略</Button>
                  <Button>手动选择策略包</Button>
                </Space>
              </Space>
            </Card>
          </Col>
        </Row>

        <Card className="p1-soft-card" title="解析结果 -> 统一文档对象">
          <div className="p1-flow-preview">
            <div className="p1-flow-box">
              <Typography.Text strong>解析结果</Typography.Text>
              <Typography.Title level={3}>{totalSegments}</Typography.Title>
              <Typography.Text type="secondary">结构化片段</Typography.Text>
            </div>
            <div className="p1-flow-arrow">→</div>
            <div className="p1-flow-box">
              <Typography.Text strong>统一文档对象</Typography.Text>
              <Typography.Title level={3}>{activeSegments.length || totalSegments}</Typography.Title>
              <Typography.Text type="secondary">block / section / anchor</Typography.Text>
            </div>
            <div className="p1-flow-arrow">→</div>
            <div className="p1-flow-box">
              <Typography.Text strong>可送入知识库抽取</Typography.Text>
              <Typography.Title level={3}>13</Typography.Title>
              <Typography.Text type="secondary">阶段主链</Typography.Text>
            </div>
          </div>
        </Card>

        <ValidationDrawer
          title="解析详情"
          open={selectedIntakeDocumentId !== null}
          onClose={() => setSelectedIntakeDocumentId(null)}
          width={760}
          loading={intakeDetailLoading}
          loadingText="正在加载解析详情..."
          error={intakeDetailError}
          errorMessage="解析详情暂不可用"
        >
          {intakeDocumentDetail ? (
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <div>
                <Typography.Title level={4} style={{ marginTop: 0 }}>
                  {intakeDocumentDetail.title}
                </Typography.Title>
                <Typography.Text type="secondary">{intakeDocumentDetail.source_name}</Typography.Text>
              </div>

              {intakeDocumentDetail.latest_version ? (
                <Descriptions bordered size="small" column={2}>
                  <Descriptions.Item label="最新版本">
                    V{intakeDocumentDetail.latest_version.version_number}
                  </Descriptions.Item>
                  <Descriptions.Item label="文件名">
                    {intakeDocumentDetail.latest_version.file_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="解析状态">
                    {mapVersionStatus(intakeDocumentDetail.latest_version.status)}
                  </Descriptions.Item>
                  <Descriptions.Item label="解析器">
                    {intakeDocumentDetail.latest_version.latest_parse_run?.parser_name ?? "未解析"}
                  </Descriptions.Item>
                  <Descriptions.Item label="解析批次">
                    {intakeDocumentDetail.latest_version.parse_runs.length}
                  </Descriptions.Item>
                  <Descriptions.Item label="片段数">
                    {intakeDocumentDetail.latest_version.latest_parse_run?.segment_count ?? 0}
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                <Empty description="暂无版本详情" />
              )}

              {intakeDocumentDetail.latest_version?.latest_parse_run?.failure_reason ? (
                <Alert
                  type="error"
                  showIcon
                  message="解析失败原因"
                  description={intakeDocumentDetail.latest_version.latest_parse_run.failure_reason}
                />
              ) : null}

              <div>
                <Typography.Title level={5}>解析片段预览</Typography.Title>
                {intakeDocumentDetail.latest_version?.segments_preview.length ? (
                  <List
                    bordered
                    dataSource={intakeDocumentDetail.latest_version.segments_preview}
                    renderItem={(segment) => (
                      <List.Item>
                        <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                          <Space wrap>
                            <Typography.Text strong>{segment.heading}</Typography.Text>
                            <Tag>{segment.block_type}</Tag>
                          </Space>
                          <Typography.Text>{segment.content}</Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无解析片段" />
                )}
              </div>
            </Space>
          ) : null}
        </ValidationDrawer>
      </Space>
    </ValidationWorkspace>
  );
}

function mapVersionStatus(status?: string) {
  if (status === "parsed") {
    return "已解析";
  }
  if (status === "parse_failed") {
    return "解析失败";
  }
  if (status === "uploaded") {
    return "待解析";
  }
  return status ?? "未知";
}

function buildFallbackParseRows(document: IntakeDocumentSummary | null) {
  if (!document) {
    return [];
  }

  const segmentCount = document.latest_version?.latest_parse_run?.segment_count ?? 0;
  return [
    {
      id: `${document.id}-title`,
      heading: `文档标题：${document.title}`,
      block_type: "title",
      content: document.title,
    },
    {
      id: `${document.id}-section`,
      heading: "章节结构",
      block_type: "section",
      content: `${document.source_name} / ${segmentCount || "待解析"} 个结构片段`,
    },
    {
      id: `${document.id}-anchor`,
      heading: "锚点映射",
      block_type: "anchor",
      content: document.latest_version?.latest_parse_run?.parser_name ?? "等待解析器输出锚点",
    },
  ];
}
