import { useEffect, useState } from "react";
import { Button, Checkbox, Segmented, Select, Space, Tag, Typography } from "antd";

import { KnowledgeGraph } from "../components/KnowledgeGraph";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { WorkspaceOverviewStrip } from "../components/WorkspaceOverviewStrip";
import { useArchiveContext } from "../context/ArchiveContext";
import {
  getArchiveDocuments,
  getArchiveEntities,
  getArchiveEvents,
  getArchiveGraph,
  getArchiveProcesses,
  getArchivePublication,
  getArchiveSummary,
} from "../lib/archiveKnowledge";
import type {
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeEvent,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeProcess,
  ArchiveKnowledgeSummary,
  ArchivePublicationOverview,
} from "../lib/api";

const itemTypeOptions = [
  { label: "实体", value: "entity" },
  { label: "事件", value: "event" },
  { label: "流程", value: "process" },
] as const;

const SOURCE_DOCUMENT_TITLE_PREVIEW_LENGTH = 24;

function shortenDocumentTitle(title: string) {
  if (title.length <= SOURCE_DOCUMENT_TITLE_PREVIEW_LENGTH) {
    return title;
  }

  return `${title.slice(0, SOURCE_DOCUMENT_TITLE_PREVIEW_LENGTH - 3)}...`;
}

function formatSelectedDocumentSummary(documents: ArchiveKnowledgeDocument[], selectedDocumentIds: string[]) {
  if (selectedDocumentIds.length === 0) {
    return "全部素材文档";
  }

  if (selectedDocumentIds.length === 1) {
    const selectedDocument = documents.find((document) => document.id === selectedDocumentIds[0]);
    const title = selectedDocument ? selectedDocument.title : selectedDocumentIds[0];
    return `已选 1 份：${shortenDocumentTitle(title)}`;
  }

  return `已选 ${selectedDocumentIds.length} / ${documents.length} 份`;
}

export function KnowledgeGraphPage() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [graph, setGraph] = useState<ArchiveKnowledgeGraph | null>(null);
  const [documents, setDocuments] = useState<ArchiveKnowledgeDocument[]>([]);
  const [entities, setEntities] = useState<ArchiveKnowledgeEntity[]>([]);
  const [events, setEvents] = useState<ArchiveKnowledgeEvent[]>([]);
  const [processes, setProcesses] = useState<ArchiveKnowledgeProcess[]>([]);
  const [publicationOverview, setPublicationOverview] = useState<ArchivePublicationOverview | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "graph">("list");
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [selectedItemTypes, setSelectedItemTypes] = useState<Array<"entity" | "event" | "process">>([
    "entity",
    "event",
    "process",
  ]);

  useEffect(() => {
    setSelectedDocumentIds([]);
  }, [activeArchiveId]);

  useEffect(() => {
    let cancelled = false;

    async function loadArchiveDocuments() {
      if (!activeArchiveId) {
        setDocuments([]);
        setDocumentsLoading(false);
        return;
      }

      try {
        setDocumentsLoading(true);
        const response = await getArchiveDocuments(activeArchiveId);
        if (cancelled) {
          return;
        }
        setDocuments(response.data);
      } catch {
        if (!cancelled) {
          setDocuments([]);
        }
      } finally {
        if (!cancelled) {
          setDocumentsLoading(false);
        }
      }
    }

    void loadArchiveDocuments();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  useEffect(() => {
    let cancelled = false;

    async function loadArchiveKnowledge() {
      if (!activeArchiveId) {
        setSummary(null);
        setGraph(null);
        setDocuments([]);
        setEntities([]);
        setEvents([]);
        setProcesses([]);
        setPublicationOverview(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const sourceFilter = selectedDocumentIds.length > 0 ? { documentIds: selectedDocumentIds } : undefined;
        const [summaryResponse, graphResponse, entitiesResponse, eventsResponse, processesResponse, publicationResponse] =
          await Promise.all([
            getArchiveSummary(activeArchiveId, sourceFilter),
            getArchiveGraph(activeArchiveId, sourceFilter),
            getArchiveEntities(activeArchiveId, sourceFilter),
            getArchiveEvents(activeArchiveId, sourceFilter),
            getArchiveProcesses(activeArchiveId, sourceFilter),
            getArchivePublication(activeArchiveId),
          ]);
        if (cancelled) {
          return;
        }
        setSummary(summaryResponse.data);
        setGraph(graphResponse.data);
        setEntities(entitiesResponse.data);
        setEvents(eventsResponse.data);
        setProcesses(processesResponse.data);
        setPublicationOverview(publicationResponse.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载档案知识失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadArchiveKnowledge();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId, selectedDocumentIds]);

  const allDocumentIds = documents.map((document) => document.id);
  const selectedDocumentSummary = formatSelectedDocumentSummary(documents, selectedDocumentIds);
  const allDocumentsSelected = documents.length > 0 && selectedDocumentIds.length === documents.length;

  function handleSelectAllDocuments() {
    setSelectedDocumentIds(allDocumentIds);
  }

  function handleClearSelectedDocuments() {
    setSelectedDocumentIds([]);
  }

  return (
    <ValidationWorkspace
      title="知识图谱"
      description={`浏览已发布知识中的实体、事件、流程及其关联关系。${activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}`}
    >
      {summary ? (
        <WorkspaceOverviewStrip
          badgeLabel="已发布知识仓"
          title="档案知识总览"
          tags={[
            { label: `版本：${publicationOverview?.current_version?.version_label ?? "未发布"}` },
            { label: `节点：${graph?.nodes.length ?? 0}` },
            { label: `关系：${graph?.edges.length ?? 0}` },
          ]}
          metrics={[
            { title: "文档", value: summary.document_count, accent: "#0f766e", tone: "rgba(20, 184, 166, 0.08)" },
            { title: "实体", value: summary.entity_count, accent: "#1d4ed8", tone: "rgba(59, 130, 246, 0.10)" },
            { title: "事件", value: summary.event_count, accent: "#b45309", tone: "rgba(245, 158, 11, 0.12)" },
            { title: "流程", value: summary.process_count, accent: "#7c3aed", tone: "rgba(139, 92, 246, 0.10)" },
          ]}
        >
          <Space direction="vertical" size={10} style={{ display: "flex" }}>
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <Space wrap size={[12, 8]}>
                <Typography.Text type="secondary">类型筛选</Typography.Text>
                <Checkbox.Group
                  options={itemTypeOptions.map((item) => ({ label: item.label, value: item.value }))}
                  value={selectedItemTypes}
                  onChange={(values) => setSelectedItemTypes(values as Array<"entity" | "event" | "process">)}
                />
              </Space>

              <Space wrap size={[12, 8]}>
                <Typography.Text type="secondary">视图选择</Typography.Text>
                <Segmented
                  options={[
                    { label: "列表视图", value: "list" },
                    { label: "图谱视图", value: "graph" },
                  ]}
                  value={viewMode}
                  onChange={(value) => setViewMode(value as "list" | "graph")}
                />
              </Space>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <Space wrap size={[12, 8]} style={{ flex: 1, minWidth: 280 }}>
                <Typography.Text type="secondary">来源文档</Typography.Text>
                <Select
                  data-testid="knowledge-source-documents-select"
                  mode="multiple"
                  showSearch
                  value={selectedDocumentIds}
                  loading={documentsLoading}
                  placeholder="全部素材文档"
                  style={{ minWidth: 320, flex: 1 }}
                  maxTagCount={0}
                  maxTagPlaceholder={() => selectedDocumentSummary}
                  optionFilterProp="label"
                  onChange={(values) => setSelectedDocumentIds(values)}
                  popupRender={(menu) => (
                    <div>
                      <div
                        onMouseDown={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 12,
                          padding: "8px 12px 6px",
                          borderBottom: "1px solid rgba(15, 23, 42, 0.08)",
                        }}
                      >
                        <Space size={12}>
                          <Button
                            type="link"
                            size="small"
                            style={{ padding: 0, height: "auto" }}
                            disabled={documents.length === 0 || allDocumentsSelected}
                            onClick={handleSelectAllDocuments}
                          >
                            全选
                          </Button>
                          <Button
                            type="link"
                            size="small"
                            style={{ padding: 0, height: "auto" }}
                            disabled={selectedDocumentIds.length === 0}
                            onClick={handleClearSelectedDocuments}
                          >
                            清空
                          </Button>
                        </Space>

                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {selectedDocumentIds.length === 0
                            ? `全部 ${documents.length} 份`
                            : `已选 ${selectedDocumentIds.length} / ${documents.length} 份`}
                        </Typography.Text>
                      </div>
                      {menu}
                    </div>
                  )}
                  options={documents.map((document) => ({
                    label: document.title,
                    value: document.id,
                  }))}
                />
              </Space>

              <Tag style={{ borderRadius: 9999, paddingInline: 10, lineHeight: "22px", marginInlineEnd: 0 }}>
                {selectedDocumentIds.length === 0
                  ? `当前来源：全部 ${documents.length} 份`
                  : `当前来源：已选 ${selectedDocumentIds.length} / ${documents.length} 份`}
              </Tag>
            </div>
          </Space>
        </WorkspaceOverviewStrip>
      ) : null}

      <KnowledgeGraph
        archiveId={activeArchiveId}
        entities={entities}
        events={events}
        processes={processes}
        error={error}
        graph={graph}
        loading={loading}
        selectedDocumentIds={selectedDocumentIds}
        selectedItemTypes={selectedItemTypes}
        summary={summary}
        viewMode={viewMode}
      />
    </ValidationWorkspace>
  );
}
