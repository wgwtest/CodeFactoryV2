import { useDeferredValue, useEffect, useState } from "react";
import { Alert, Button, Descriptions, Empty, Input, List, Space, Table, Tag, Typography } from "antd";

import { DocumentUploadForm } from "../components/DocumentUploadForm";
import { EvidenceList } from "../components/EvidenceList";
import { ValidationDrawer } from "../components/ValidationDrawer";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { api } from "../lib/api";
import { getArchiveDocumentDetail, getArchiveDocuments, getArchiveSummary } from "../lib/archiveKnowledge";
import type {
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeDocumentDetail,
  ArchiveKnowledgeDocumentKnowledgeItem,
  ArchiveKnowledgeSummary,
  IntakeDocumentDetail,
  IntakeDocumentSummary,
} from "../lib/api";

const categoryLabels: Record<string, string> = {
  architecture_artifact: "架构工件",
  architecture_concept: "架构概念",
  domain_concept: "领域概念",
  domain_process: "领域流程",
  organization: "组织",
  service_category: "服务分类",
  service_taxonomy: "服务分类",
  system_or_service: "系统/服务",
  timeline_event: "时间事件",
};

const knowledgeSections: Array<{ key: "entity" | "event" | "process"; title: string }> = [
  { key: "entity", title: "实体" },
  { key: "event", title: "事件" },
  { key: "process", title: "流程" },
];

export function DocumentsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [documents, setDocuments] = useState<ArchiveKnowledgeDocument[]>([]);
  const [intakeDocuments, setIntakeDocuments] = useState<IntakeDocumentSummary[]>([]);
  const [intakeLoading, setIntakeLoading] = useState(true);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [selectedIntakeDocumentId, setSelectedIntakeDocumentId] = useState<string | null>(null);
  const [intakeDocumentDetail, setIntakeDocumentDetail] = useState<IntakeDocumentDetail | null>(null);
  const [intakeDetailLoading, setIntakeDetailLoading] = useState(false);
  const [intakeDetailError, setIntakeDetailError] = useState<string | null>(null);
  const [searchValue, setSearchValue] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [documentDetail, setDocumentDetail] = useState<ArchiveKnowledgeDocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const deferredSearchValue = useDeferredValue(searchValue);

  async function loadArchiveDocuments(cancelled?: { current: boolean }) {
    try {
      const [summaryResponse, documentsResponse] = await Promise.all([
        getArchiveSummary(),
        getArchiveDocuments(),
      ]);
      if (cancelled?.current) {
        return;
      }
      setSummary(summaryResponse.data);
      setDocuments(documentsResponse.data);
      setError(null);
    } catch (loadError) {
      if (!cancelled?.current) {
        setError(loadError instanceof Error ? loadError.message : "加载档案文档失败");
      }
    } finally {
      if (!cancelled?.current) {
        setLoading(false);
      }
    }
  }

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

    void Promise.all([
      loadArchiveDocuments(cancelled),
      loadIntakeDocuments(cancelled),
    ]);
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

  useEffect(() => {
    const documentId = selectedDocumentId;

    if (!documentId) {
      setDocumentDetail(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;

    async function loadDocumentDetail() {
      const activeDocumentId = documentId;
      try {
        setDetailLoading(true);
        setDocumentDetail(null);
        if (activeDocumentId === null) {
          return;
        }
        const response = await getArchiveDocumentDetail(activeDocumentId);
        if (cancelled) {
          return;
        }
        setDocumentDetail(response.data);
        setDetailError(null);
      } catch (loadError) {
        if (!cancelled) {
          setDetailError(loadError instanceof Error ? loadError.message : "加载文档详情失败");
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }

    void loadDocumentDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedDocumentId]);

  const normalizedQuery = deferredSearchValue.trim().toLowerCase();
  const filteredDocuments = documents.filter((item) => {
    if (!normalizedQuery) {
      return true;
    }
    const haystack = [item.title, item.source_archive, item.file_type].join(" ").toLowerCase();
    return haystack.includes(normalizedQuery);
  });

  const groupedKnowledge = {
    entity: documentDetail?.knowledge_items.filter((item) => item.item_type === "entity") ?? [],
    event: documentDetail?.knowledge_items.filter((item) => item.item_type === "event") ?? [],
    process: documentDetail?.knowledge_items.filter((item) => item.item_type === "process") ?? [],
  };

  return (
    <ValidationWorkspace
      title="上传源文档"
      description="导入政策、手册或规程类资料，形成可追溯的文档版本，作为后续解析、抽取和治理的基础。"
      stats={
        summary
          ? [
              { title: "文档总数", value: summary.document_count },
              { title: "实体", value: summary.entity_count },
              { title: "事件", value: summary.event_count },
              { title: "流程", value: summary.process_count },
            ]
          : []
      }
    >
      <Space direction="vertical" size={24} style={{ display: "flex" }}>
        <div>
          <DocumentUploadForm onUploaded={() => loadIntakeDocuments()} />
        </div>

        <div>
          <Typography.Title level={4}>接入解析验证</Typography.Title>
          <Typography.Paragraph type="secondary">
            展示当前已接入文档的版本状态、最新解析批次和片段预览，用于验证 `P1.2` 的结构化解析产物。
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

        <div>
          <Typography.Title level={4}>已建库档案文档</Typography.Title>
          <Typography.Paragraph type="secondary">
            当前演示清单来自 20161116 NAS 架构资料集，展示已解压并完成知识构建的真实文档。
          </Typography.Paragraph>
        </div>

        {error ? <Alert type="error" message="档案文档暂不可用" description={error} showIcon /> : null}

        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <Input.Search
            allowClear
            placeholder="搜索文档标题、来源或类型"
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
          />

          <Table
            rowKey="id"
            loading={loading}
            dataSource={filteredDocuments}
            locale={{ emptyText: "暂无档案文档" }}
            pagination={{ pageSize: 10 }}
            columns={[
              {
                title: "文档标题",
                dataIndex: "title",
                render: (value: string, record: ArchiveKnowledgeDocument) => (
                  <Button type="link" style={{ padding: 0 }} onClick={() => setSelectedDocumentId(record.id)}>
                    {value}
                  </Button>
                ),
              },
              { title: "文件类型", dataIndex: "file_type" },
              { title: "来源档案", dataIndex: "source_archive" },
              {
                title: "字符数",
                dataIndex: "character_count",
                render: (value: number) => value.toLocaleString("zh-CN"),
              },
              {
                title: "关联知识",
                dataIndex: "knowledge_item_count",
                render: (value: number) => `${value} 项知识`,
              },
              {
                title: "操作",
                render: (_: unknown, record: ArchiveKnowledgeDocument) => (
                  <Button type="link" onClick={() => setSelectedDocumentId(record.id)}>
                    查看
                  </Button>
                ),
              },
            ]}
          />
        </Space>

        <ValidationDrawer
          title="文档详情"
          open={selectedDocumentId !== null}
          onClose={() => setSelectedDocumentId(null)}
          width={720}
          loading={detailLoading}
          loadingText="正在加载文档详情..."
          error={detailError}
          errorMessage="文档详情暂不可用"
        >
          {documentDetail ? (
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <div>
                <Typography.Title level={4} style={{ marginTop: 0 }}>
                  {documentDetail.document.title}
                </Typography.Title>
                <Space wrap>
                  <Tag>{documentDetail.document.file_type}</Tag>
                  <Typography.Text type="secondary">{documentDetail.document.source_archive}</Typography.Text>
                </Space>
              </div>

              <div>
                <Typography.Title level={5}>文档概览</Typography.Title>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="字符数">{documentDetail.document.character_count.toLocaleString("zh-CN")}</Descriptions.Item>
                  <Descriptions.Item label="知识总数">{documentDetail.document.knowledge_item_count}</Descriptions.Item>
                  <Descriptions.Item label="实体数">{documentDetail.document.entity_count}</Descriptions.Item>
                  <Descriptions.Item label="事件数">{documentDetail.document.event_count}</Descriptions.Item>
                  <Descriptions.Item label="流程数">{documentDetail.document.process_count}</Descriptions.Item>
                  <Descriptions.Item label="文件类型">{documentDetail.document.file_type}</Descriptions.Item>
                </Descriptions>
              </div>

              {knowledgeSections.map((section) => (
                <DocumentKnowledgeSection
                  key={section.key}
                  title={section.title}
                  items={groupedKnowledge[section.key]}
                />
              ))}
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

type DocumentKnowledgeSectionProps = {
  title: string;
  items: ArchiveKnowledgeDocumentKnowledgeItem[];
};

function DocumentKnowledgeSection({ title, items }: DocumentKnowledgeSectionProps) {
  return (
    <div>
      <Space align="center" size={8} style={{ marginBottom: 12 }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        <Typography.Text type="secondary">{items.length} 项</Typography.Text>
      </Space>

      {items.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`该文档未关联此类知识`} />
      ) : (
        <List
          bordered
          dataSource={items}
          renderItem={(item) => (
            <List.Item>
              <Space direction="vertical" size={8} style={{ display: "flex", width: "100%" }}>
                <Space wrap>
                  <Typography.Text strong>{item.name}</Typography.Text>
                  <Tag>{categoryLabels[item.category] ?? item.category}</Tag>
                  {item.interpretation.display_name ? (
                    <Typography.Text type="secondary">{item.interpretation.display_name}</Typography.Text>
                  ) : null}
                  {item.interpretation.standard_name ? (
                    <Typography.Text type="secondary">{item.interpretation.standard_name}</Typography.Text>
                  ) : null}
                </Space>

                <Typography.Text>{item.interpretation.summary}</Typography.Text>

                {item.aliases.length > 0 ? (
                  <Typography.Text type="secondary">别名：{item.aliases.join(" / ")}</Typography.Text>
                ) : null}

                <EvidenceList items={item.evidence} size="small" bordered={false} />
              </Space>
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
