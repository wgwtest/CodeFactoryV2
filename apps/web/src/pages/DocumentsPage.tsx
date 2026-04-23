import { useDeferredValue, useEffect, useState } from "react";
import { Alert, Button, Descriptions, Empty, Input, List, Space, Table, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import { ArchiveDocumentImportForm } from "../components/ArchiveDocumentImportForm";
import { EvidenceList } from "../components/EvidenceList";
import { ValidationDrawer } from "../components/ValidationDrawer";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { WorkspaceOverviewStrip } from "../components/WorkspaceOverviewStrip";
import { useArchiveContext } from "../context/ArchiveContext";
import { getArchiveDocumentDetail, getArchiveDocuments, getArchiveSummary } from "../lib/archiveKnowledge";
import { formalizeArchiveDocument, removeArchiveDocument } from "../lib/archives";
import type {
  ArchiveDocumentImportResult,
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeDocumentDetail,
  ArchiveKnowledgeDocumentKnowledgeItem,
  ArchiveKnowledgeSummary,
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
  const { activeArchive, activeArchiveId, refreshArchives } = useArchiveContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [documents, setDocuments] = useState<ArchiveKnowledgeDocument[]>([]);
  const [searchValue, setSearchValue] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [documentDetail, setDocumentDetail] = useState<ArchiveKnowledgeDocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [documentMutation, setDocumentMutation] = useState<{ documentId: string; action: "include" | "remove" } | null>(null);
  const [documentFeedback, setDocumentFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const deferredSearchValue = useDeferredValue(searchValue);

  async function loadArchiveDocuments(cancelled?: { current: boolean }) {
    if (!activeArchiveId) {
      if (!cancelled?.current) {
        setSummary(null);
        setDocuments([]);
        setLoading(false);
      }
      return;
    }

    try {
      const [summaryResponse, documentsResponse] = await Promise.all([
        getArchiveSummary(activeArchiveId),
        getArchiveDocuments(activeArchiveId),
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

  useEffect(() => {
    const cancelled = { current: false };
    void loadArchiveDocuments(cancelled);
    return () => {
      cancelled.current = true;
    };
  }, [activeArchiveId]);

  useEffect(() => {
    const documentId = selectedDocumentId;

    if (!documentId || !activeArchiveId) {
      setDocumentDetail(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;

    async function loadDocumentDetail() {
      const activeDocumentId = documentId;
      const currentArchiveId = activeArchiveId;
      try {
        setDetailLoading(true);
        setDocumentDetail(null);
        if (activeDocumentId === null || currentArchiveId === null) {
          return;
        }
        const response = await getArchiveDocumentDetail(activeDocumentId, currentArchiveId);
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
  }, [activeArchiveId, selectedDocumentId]);

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
  const currentMutationDocument = documentMutation
    ? documents.find((item) => item.id === documentMutation.documentId) ?? null
    : null;
  const documentMutationStatus = documentMutation
    ? documentMutation.action === "include"
      ? "正在并入"
      : "正在移出"
    : "空闲";

  async function runArchiveDocumentMutation(record: ArchiveKnowledgeDocument, action: "include" | "remove") {
    if (!activeArchiveId || documentMutation !== null) {
      return;
    }

    try {
      setDocumentFeedback(null);
      setDocumentMutation({ documentId: record.id, action });
      const response =
        action === "include"
          ? await formalizeArchiveDocument(activeArchiveId, record.id)
          : await removeArchiveDocument(activeArchiveId, record.id);
      await Promise.all([loadArchiveDocuments(), refreshArchives(activeArchiveId)]);

      if (selectedDocumentId === record.id) {
        const detailResponse = await getArchiveDocumentDetail(record.id, activeArchiveId);
        setDocumentDetail(detailResponse.data);
        setDetailError(null);
      }

      setDocumentFeedback({
        type: "success",
        message: formatDocumentMutationSuccessMessage(record.title, response.data.action, response.data.mode),
      });
    } catch (mutationError) {
      setDocumentFeedback({
        type: "error",
        message:
          mutationError instanceof Error
            ? mutationError.message
            : action === "include"
              ? "文档正式并入失败"
              : "文档正式移出失败",
      });
    } finally {
      setDocumentMutation(null);
    }
  }

  async function handleImportedArchiveDocument(result: ArchiveDocumentImportResult) {
    if (!activeArchiveId) {
      return;
    }

    await Promise.all([loadArchiveDocuments(), refreshArchives(activeArchiveId)]);
    setSelectedDocumentId(result.document?.id ?? result.document_id);
    setDocumentFeedback({
      type: "success",
      message: formatDocumentImportSuccessMessage(result.document?.title ?? result.document_id, result.mode),
    });
  }

  return (
    <ValidationWorkspace
      title="知识库文档"
      description={
        <>
          当前页面只聚焦知识库主链文档，用于查看当前 archive 的正式文档清单，并执行单文档正式并入或移出。
          {activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}
        </>
      }
      actions={
        <Link to="/documents/intake">
          <Button>前往接入解析验证</Button>
        </Link>
      }
    >
      <Space direction="vertical" size={24} style={{ display: "flex" }}>
        <WorkspaceOverviewStrip
          badgeLabel="知识库文档"
          badgeColor="blue"
          title="知识库文档总览"
          tags={[
            { label: `当前知识库：${activeArchive?.name ?? "未选择"}` },
            {
              label: currentMutationDocument
                ? `正式任务：${documentMutationStatus} · ${currentMutationDocument.title}`
                : `正式任务：${documentMutationStatus}`,
              color: documentMutation ? "processing" : "default",
            },
          ]}
          metrics={[
            { title: "知识库文档", value: summary?.document_count ?? 0 },
            { title: "实体", value: summary?.entity_count ?? 0 },
            { title: "事件", value: summary?.event_count ?? 0 },
            { title: "流程", value: summary?.process_count ?? 0 },
          ]}
        />

        <Alert
          type="info"
          showIcon
          message="知识库文档页只保留 archive 主链"
          description="上传、解析验证和旧的 DB intake 逻辑已迁移到“接入解析验证”页面；这里仅处理当前知识库的正式文档查看、并入和移出。"
        />

        <ArchiveDocumentImportForm
          archiveId={activeArchiveId}
          disabled={!activeArchiveId || activeArchive?.status === "extracting" || documentMutation !== null}
          onImported={(result) => void handleImportedArchiveDocument(result)}
          onImportFailed={(message) => setDocumentFeedback({ type: "error", message })}
        />

        <div>
          <Typography.Title level={4}>当前知识库文档</Typography.Title>
          <Typography.Paragraph type="secondary">
            这里只展示当前 archive 已经建立正式产物仓的文档视图，并支持按文档执行正式并入或正式移出。
          </Typography.Paragraph>
        </div>

        {error ? <Alert type="error" message="档案文档暂不可用" description={error} showIcon /> : null}
        {documentFeedback ? (
          <Alert
            type={documentFeedback.type}
            message={documentFeedback.type === "success" ? "正式操作已完成" : "正式操作失败"}
            description={documentFeedback.message}
            showIcon
          />
        ) : null}

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
                render: (_: unknown, record: ArchiveKnowledgeDocument) => {
                  const isIncluded = record.included_in_archive !== false;
                  const isMutating = documentMutation?.documentId === record.id;
                  const mutationLabel =
                    isMutating && documentMutation
                      ? documentMutation.action === "include"
                        ? "正在并入"
                        : "正在移出"
                      : isIncluded
                        ? "已并入"
                        : "未并入";
                  const mutationColor = isMutating ? "processing" : isIncluded ? "green" : "default";

                  return (
                    <Space size={4} wrap>
                      <Tag color={mutationColor}>{mutationLabel}</Tag>
                      <Button type="link" onClick={() => setSelectedDocumentId(record.id)}>
                        查看
                      </Button>
                      <Button
                        type="link"
                        onClick={() => void runArchiveDocumentMutation(record, isIncluded ? "remove" : "include")}
                        loading={isMutating}
                        disabled={documentMutation !== null}
                      >
                        {isIncluded ? "从当前知识库移出" : "纳入当前知识库"}
                      </Button>
                    </Space>
                  );
                },
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
                  <Descriptions.Item label="纳入当前知识库状态">
                    <Tag color={documentDetail.document.included_in_archive !== false ? "green" : "default"}>
                      {documentDetail.document.included_in_archive !== false ? "已并入" : "未并入"}
                    </Tag>
                  </Descriptions.Item>
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

function formatDocumentMutationSuccessMessage(
  title: string,
  action: "include" | "remove",
  mode: "incremental_merge" | "full_rebuild_bootstrap" | "incremental_remove" | "full_rebuild_bootstrap_remove",
) {
  if (action === "include") {
    return mode === "full_rebuild_bootstrap"
      ? `已完成“${title}”的正式产物仓初始化重建，当前知识库已完成全库重建。`
      : `已完成“${title}”的单文档正式并入，当前知识库已重算。`;
  }

  return mode === "full_rebuild_bootstrap_remove"
    ? `已完成“${title}”的正式产物仓初始化，并已将该文档正式移出当前知识库。`
    : `已完成“${title}”的正式移出，当前知识库已重算。`;
}

function formatDocumentImportSuccessMessage(
  title: string,
  mode: "single_document_import" | "full_rebuild_bootstrap_import",
) {
  return mode === "full_rebuild_bootstrap_import"
    ? `已完成“${title}”的上传并纳入当前知识库，当前知识库已完成全库重建。`
    : `已完成“${title}”的上传并纳入当前知识库，当前知识库已完成增量重算。`;
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
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该文档未关联此类知识" />
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
