import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Descriptions, Empty, List, Space, Table, Tag, Typography } from "antd";
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

  return (
    <ValidationWorkspace
      title="接入解析验证"
      description="这个页面承接 legacy intake 上传与解析验证链，用来查看原始上传、解析状态和片段预览，不直接代表当前知识库已正式入库。"
      actions={
        <Link to="/documents">
          <Button>返回知识库文档</Button>
        </Link>
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
          type="info"
          showIcon
          message="这是独立的接入验证链"
          description="这里的上传和解析结果不会自动进入当前知识库；如果要让文档参与知识库构建，请回到“知识库文档”页走 archive 主链。"
        />

        <div>
          <DocumentUploadForm onUploaded={() => loadIntakeDocuments()} />
        </div>

        <div>
          <Typography.Title level={4}>接入解析验证</Typography.Title>
          <Typography.Paragraph type="secondary">
            展示当前已接入文档的版本状态、最新解析批次和片段预览，用于验证 legacy intake 解析链的结构化结果。
          </Typography.Paragraph>
        </div>

        {intakeError ? <Alert type="error" message="接入文档暂不可用" description={intakeError} showIcon /> : null}

        <Table
          rowKey="id"
          loading={intakeLoading}
          dataSource={intakeDocuments}
          locale={{ emptyText: "暂无接入文档" }}
          pagination={{ pageSize: 5 }}
          columns={[
            { title: "标题", dataIndex: "title" },
            { title: "来源", dataIndex: "source_name" },
            {
              title: "最新版本",
              render: (_: unknown, record: IntakeDocumentSummary) =>
                record.latest_version ? `V${record.latest_version.version_number}` : "无版本",
            },
            {
              title: "解析状态",
              render: (_: unknown, record: IntakeDocumentSummary) => mapVersionStatus(record.latest_version?.status),
            },
            {
              title: "解析器",
              render: (_: unknown, record: IntakeDocumentSummary) => record.latest_version?.latest_parse_run?.parser_name ?? "未解析",
            },
            {
              title: "片段数",
              render: (_: unknown, record: IntakeDocumentSummary) => record.latest_version?.latest_parse_run?.segment_count ?? 0,
            },
            {
              title: "操作",
              render: (_: unknown, record: IntakeDocumentSummary) => (
                <Button type="link" onClick={() => setSelectedIntakeDocumentId(record.id)}>
                  查看解析
                </Button>
              ),
            },
          ]}
        />

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
