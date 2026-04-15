import type { Key } from "react";
import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Descriptions,
  Divider,
  Empty,
  Input,
  List,
  Radio,
  Space,
  Tag,
  Typography,
} from "antd";

import { CandidateReviewTable } from "../components/CandidateReviewTable";
import { EvidenceList } from "../components/EvidenceList";
import { ValidationDrawer } from "../components/ValidationDrawer";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { WorkspaceOverviewStrip } from "../components/WorkspaceOverviewStrip";
import { useArchiveContext } from "../context/ArchiveContext";
import { api } from "../lib/api";
import { getArchivePublication } from "../lib/archiveKnowledge";
import type {
  ArchiveKnowledgeBatchApproveInput,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeItemReviewInput,
  ArchiveKnowledgeItemUpdateInput,
  ArchiveKnowledgeMergeInput,
  ArchivePublicationOverview,
  ArchiveReviewCandidate,
  ArchiveReviewStatus,
} from "../lib/api";

const itemTypeLabels: Record<string, string> = {
  entity: "实体",
  event: "事件",
  process: "流程",
};

const categoryLabels: Record<string, string> = {
  architecture_artifact: "架构产物",
  architecture_concept: "架构概念",
  domain_concept: "领域概念",
  domain_process: "领域流程",
  information_exchange: "信息交换",
  operational_node: "运行节点",
  organization: "组织",
  service_category: "服务分类",
  service_taxonomy: "服务分类",
  system_or_service: "系统/服务",
  timeline_event: "时间事件",
};

const reviewStatusLabels: Record<ArchiveReviewStatus, string> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已驳回",
};

type ItemTypeFilter = "all" | "entity" | "event" | "process";
type ReviewStatusFilter = "all" | ArchiveReviewStatus;

export function GovernancePage() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ArchiveReviewCandidate[]>([]);
  const [query, setQuery] = useState("");
  const [itemTypeFilter, setItemTypeFilter] = useState<ItemTypeFilter>("all");
  const [reviewStatusFilter, setReviewStatusFilter] = useState<ReviewStatusFilter>("pending");
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const [activeDetail, setActiveDetail] = useState<ArchiveKnowledgeItemDetail | null>(null);
  const [publicationOverview, setPublicationOverview] = useState<ArchivePublicationOverview | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [drawerSaving, setDrawerSaving] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftCategory, setDraftCategory] = useState("");
  const [draftAliases, setDraftAliases] = useState("");
  const [versionLabel, setVersionLabel] = useState("v1");
  const [publisher, setPublisher] = useState("architect");

  async function loadCandidates() {
    if (!activeArchiveId) {
      setCandidates([]);
      return;
    }
    const response = await api.get<ArchiveReviewCandidate[]>(`/knowledge/archive/${activeArchiveId}/review-candidates`);
    setCandidates(response.data);
  }

  async function loadPublication() {
    if (!activeArchiveId) {
      setPublicationOverview(null);
      return;
    }
    const response = await getArchivePublication(activeArchiveId);
    setPublicationOverview(response.data);
  }

  useEffect(() => {
    let cancelled = false;

    async function loadInitialCandidates() {
      if (!activeArchiveId) {
        setCandidates([]);
        setPublicationOverview(null);
        setLoading(false);
        return;
      }
      try {
        const [candidateResponse, publicationResponse] = await Promise.all([
          api.get<ArchiveReviewCandidate[]>(`/knowledge/archive/${activeArchiveId}/review-candidates`),
          getArchivePublication(activeArchiveId),
        ]);
        if (cancelled) {
          return;
        }
        setCandidates(candidateResponse.data);
        setPublicationOverview(publicationResponse.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载候选知识失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadInitialCandidates();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  useEffect(() => {
    if (!activeItemId || !activeArchiveId) {
      setActiveDetail(null);
      return;
    }

    let cancelled = false;

    async function loadItemDetail() {
      try {
        setDetailLoading(true);
        const response = await api.get<ArchiveKnowledgeItemDetail>(
          `/knowledge/archive/${activeArchiveId}/items/${activeItemId}`,
        );
        if (cancelled) {
          return;
        }
        setActiveDetail(response.data);
        setDraftName(response.data.name);
        setDraftCategory(response.data.category);
        setDraftAliases(response.data.aliases.join(","));
        setActionError(null);
      } catch (loadError) {
        if (!cancelled) {
          setActionError(loadError instanceof Error ? loadError.message : "加载知识详情失败");
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }

    void loadItemDetail();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId, activeItemId]);

  const normalizedQuery = query.trim().toLowerCase();
  const filteredCandidates = candidates.filter((item) => {
    if (itemTypeFilter !== "all" && item.item_type !== itemTypeFilter) {
      return false;
    }
    if (reviewStatusFilter !== "all" && item.review_status !== reviewStatusFilter) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }
    const haystack = [item.canonical_name, item.evidence_excerpt].join(" ").toLowerCase();
    return haystack.includes(normalizedQuery);
  });

  const mergeCandidates = candidates.filter((item) => {
    if (!activeDetail) {
      return false;
    }
    return item.id !== activeDetail.id && item.item_type === activeDetail.item_type;
  });
  const reviewStatusSummaryLabel =
    reviewStatusFilter === "pending"
      ? "只看待审核"
      : reviewStatusFilter === "all"
        ? "全部"
        : reviewStatusLabels[reviewStatusFilter];

  async function handleApplyChanges() {
    if (!activeDetail || !activeArchiveId) {
      return;
    }

    try {
      setDrawerSaving(true);
      const payload: ArchiveKnowledgeItemUpdateInput = {
        name: draftName.trim(),
        category: draftCategory.trim(),
        aliases: parseAliasInput(draftAliases),
      };
      const response = await api.patch<ArchiveKnowledgeItemDetail>(
        `/knowledge/archive/${activeArchiveId}/items/${activeDetail.id}`,
        payload,
      );
      setActiveDetail(response.data);
      setDraftAliases(response.data.aliases.join(","));
      await loadCandidates();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "应用修改失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  async function handleReview(itemId: string, reviewStatus: ArchiveReviewStatus) {
    if (!activeArchiveId) {
      return;
    }
    try {
      setDrawerSaving(true);
      const payload: ArchiveKnowledgeItemReviewInput = { review_status: reviewStatus };
      const response = await api.post<ArchiveKnowledgeItemDetail>(
        `/knowledge/archive/${activeArchiveId}/items/${itemId}/review`,
        payload,
      );
      if (activeDetail && activeDetail.id === itemId) {
        setActiveDetail({ ...activeDetail, ...response.data });
      }
      await loadCandidates();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "更新审核状态失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  async function handleBatchApprove() {
    if (!activeArchiveId) {
      return;
    }
    try {
      setDrawerSaving(true);
      const payload: ArchiveKnowledgeBatchApproveInput = {
        item_ids: selectedRowKeys.map((item) => String(item)),
      };
      await api.post(`/knowledge/archive/${activeArchiveId}/reviews/batch-approve`, payload);
      setSelectedRowKeys([]);
      await loadCandidates();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "批量通过失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  async function handleApproveAllPending() {
    if (!activeArchiveId) {
      return;
    }
    try {
      setDrawerSaving(true);
      const payload: ArchiveKnowledgeBatchApproveInput = {
        item_ids: candidates
          .filter((item) => item.review_status === "pending")
          .map((item) => item.id),
      };
      await api.post(`/knowledge/archive/${activeArchiveId}/reviews/batch-approve`, payload);
      setSelectedRowKeys([]);
      await loadCandidates();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "批量通过全部待审核失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  async function handleMerge(secondaryItemId: string) {
    if (!activeDetail || !activeArchiveId) {
      return;
    }

    try {
      setDrawerSaving(true);
      const payload: ArchiveKnowledgeMergeInput = {
        primary_item_id: activeDetail.id,
        secondary_item_id: secondaryItemId,
      };
      const response = await api.post<ArchiveKnowledgeItemDetail>(
        `/knowledge/archive/${activeArchiveId}/items/merge`,
        payload,
      );
      setActiveDetail(response.data);
      setDraftName(response.data.name);
      setDraftCategory(response.data.category);
      setDraftAliases(response.data.aliases.join(","));
      await loadCandidates();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "合并知识失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  async function handlePublish() {
    if (!activeArchiveId) {
      return;
    }
    try {
      setDrawerSaving(true);
      await api.post(`/knowledge/archive/${activeArchiveId}/publish`, {
        version_label: versionLabel.trim(),
        publisher: publisher.trim(),
      });
      await loadPublication();
      setActionError(null);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : "发布知识版本失败");
    } finally {
      setDrawerSaving(false);
    }
  }

  return (
    <ValidationWorkspace
      title="知识审核发布"
      description={`审核机器抽取出的候选知识，并将修正直接应用到当前知识库。${activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}`}
    >
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <WorkspaceOverviewStrip
          badgeLabel="审核发布"
          badgeColor="gold"
          title="审核发布总览"
          tags={[
            { label: `当前知识库：${activeArchive?.name ?? "未选择"}` },
            {
              label: `发布状态：${publicationOverview?.current_version ? "已发布" : "未发布"}`,
              color: publicationOverview?.current_version ? "success" : "default",
            },
            { label: `当前筛选：${reviewStatusSummaryLabel}` },
          ]}
          metrics={[
            { title: "候选总数", value: candidates.length },
            { title: "当前筛出", value: filteredCandidates.length },
            { title: "已选中", value: selectedRowKeys.length },
            { title: "当前版本", value: publicationOverview?.current_version?.version_label ?? "未发布" },
          ]}
        />
        <div>
          <Typography.Paragraph type="secondary">
            支持改名、改类、别名编辑、单项通过、驳回、批量通过和同类知识合并。
          </Typography.Paragraph>
        </div>

        <div>
          <Typography.Title level={5}>发布当前已通过知识</Typography.Title>
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="当前发布版本">
                {publicationOverview?.current_version?.version_label ?? "尚未发布"}
              </Descriptions.Item>
              <Descriptions.Item label="发布人">
                {publicationOverview?.current_version?.publisher ?? "无"}
              </Descriptions.Item>
              <Descriptions.Item label="工作集实体数">
                {publicationOverview?.working_summary.entity_count ?? 0}
              </Descriptions.Item>
              <Descriptions.Item label="工作集流程数">
                {publicationOverview?.working_summary.process_count ?? 0}
              </Descriptions.Item>
            </Descriptions>
            <Space wrap>
              <Input
                placeholder="版本标签，例如 v1"
                value={versionLabel}
                onChange={(event) => setVersionLabel(event.target.value)}
                style={{ width: 220 }}
              />
              <Input
                placeholder="发布人"
                value={publisher}
                onChange={(event) => setPublisher(event.target.value)}
                style={{ width: 180 }}
              />
              <Button type="primary" loading={drawerSaving} onClick={handlePublish}>
                发布当前已通过知识
              </Button>
            </Space>
          </Space>
        </div>

        {error ? <Alert type="error" message="候选知识暂不可用" description={error} showIcon /> : null}
        {actionError ? <Alert type="error" message="操作未完成" description={actionError} showIcon /> : null}

        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <Input.Search
            allowClear
            placeholder="搜索名称或别名"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          <Space direction="vertical" size={8} style={{ display: "flex" }}>
            <div>
              <Typography.Text strong>类型筛选</Typography.Text>
            </div>
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              value={itemTypeFilter}
              onChange={(event) => setItemTypeFilter(event.target.value)}
              options={[
                { label: "全部类型", value: "all" },
                { label: "实体", value: "entity" },
                { label: "事件", value: "event" },
                { label: "流程", value: "process" },
              ]}
            />
          </Space>

          <Space direction="vertical" size={8} style={{ display: "flex" }}>
            <div>
              <Typography.Text strong>审核状态</Typography.Text>
            </div>
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              value={reviewStatusFilter}
              onChange={(event) => setReviewStatusFilter(event.target.value)}
              options={[
                { label: "只看待审核", value: "pending" },
                { label: "全部", value: "all" },
                { label: "已通过", value: "approved" },
                { label: "已驳回", value: "rejected" },
              ]}
            />
          </Space>

          <Space align="center" wrap>
            <Typography.Text type="secondary">当前筛出 {filteredCandidates.length} 项</Typography.Text>
            <Button type="primary" disabled={selectedRowKeys.length === 0} loading={drawerSaving} onClick={handleBatchApprove}>
              批量通过
            </Button>
            <Button loading={drawerSaving} onClick={handleApproveAllPending}>
              全部通过待审核
            </Button>
          </Space>
        </Space>

        <CandidateReviewTable
          items={filteredCandidates}
          loading={loading}
          selectedRowKeys={selectedRowKeys}
          onSelectionChange={setSelectedRowKeys}
          onOpenItem={setActiveItemId}
          onReview={handleReview}
        />

        <ValidationDrawer
          title="知识详情与编辑"
          open={activeItemId !== null}
          onClose={() => setActiveItemId(null)}
          width={760}
          loading={detailLoading}
          loadingText="正在加载知识详情..."
          error={null}
          errorMessage="知识详情暂不可用"
        >
          {activeDetail ? (
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <div>
                <Space align="center" wrap>
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    {activeDetail.name}
                  </Typography.Title>
                  <Tag>{itemTypeLabels[activeDetail.item_type] ?? activeDetail.item_type}</Tag>
                  <Tag>{categoryLabels[activeDetail.category] ?? activeDetail.category}</Tag>
                  <Tag color={activeDetail.review_status === "approved" ? "green" : activeDetail.review_status === "rejected" ? "red" : "gold"}>
                    {reviewStatusLabels[activeDetail.review_status]}
                  </Tag>
                </Space>
                <Typography.Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
                  {activeDetail.interpretation.summary}
                </Typography.Paragraph>
              </div>

              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="类型">{itemTypeLabels[activeDetail.item_type] ?? activeDetail.item_type}</Descriptions.Item>
                <Descriptions.Item label="覆盖文档">{activeDetail.document_count} 份</Descriptions.Item>
                <Descriptions.Item label="显示名称">{activeDetail.interpretation.display_name || "无"}</Descriptions.Item>
                <Descriptions.Item label="标准名">{activeDetail.interpretation.standard_name || "无"}</Descriptions.Item>
              </Descriptions>

              <Divider style={{ margin: 0 }} />

              <div>
                <Typography.Title level={5}>编辑信息</Typography.Title>
                <Space direction="vertical" size={12} style={{ display: "flex" }}>
                  <Input placeholder="知识名称" value={draftName} onChange={(event) => setDraftName(event.target.value)} />
                  <Input placeholder="知识类别" value={draftCategory} onChange={(event) => setDraftCategory(event.target.value)} />
                  <Input
                    placeholder="别名，按回车确认"
                    value={draftAliases}
                    onChange={(event) => setDraftAliases(event.target.value)}
                  />
                  <Space wrap>
                    <Button type="primary" loading={drawerSaving} onClick={handleApplyChanges}>
                      应用修改
                    </Button>
                    <Button loading={drawerSaving} onClick={() => handleReview(activeDetail.id, "approved")}>
                      通过
                    </Button>
                    <Button danger loading={drawerSaving} onClick={() => handleReview(activeDetail.id, "rejected")}>
                      驳回
                    </Button>
                  </Space>
                </Space>
              </div>

              <Divider style={{ margin: 0 }} />

              <div>
                <Typography.Title level={5}>关联文档</Typography.Title>
                {activeDetail.documents.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关联文档" />
                ) : (
                  <List
                    bordered
                    size="small"
                    dataSource={activeDetail.documents}
                    renderItem={(document) => (
                      <List.Item>
                        <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                          <Typography.Text strong>{document.title}</Typography.Text>
                          <Typography.Text type="secondary">
                            {document.file_type} · {document.source_archive}
                          </Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </div>

              <EvidenceList title="证据摘录" items={activeDetail.evidence} size="small" />

              <div>
                <Typography.Title level={5}>关系项</Typography.Title>
                {activeDetail.related_items.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关系项" />
                ) : (
                  <List
                    bordered
                    size="small"
                    dataSource={activeDetail.related_items}
                    renderItem={(relatedItem) => (
                      <List.Item>
                        <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                          <Typography.Text strong>{relatedItem.name}</Typography.Text>
                          <Typography.Text type="secondary">
                            {itemTypeLabels[relatedItem.item_type] ?? relatedItem.item_type} · {relatedItem.relation_type}
                          </Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </div>

              <div>
                <Typography.Title level={5}>可合并项</Typography.Title>
                {mergeCandidates.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有可合并的同类知识项" />
                ) : (
                  <List
                    bordered
                    size="small"
                    dataSource={mergeCandidates}
                    renderItem={(item) => (
                      <List.Item
                        actions={[
                          <Button key="merge" type="link" loading={drawerSaving} onClick={() => handleMerge(item.id)}>
                            合并到当前项
                          </Button>,
                        ]}
                      >
                        <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                          <Typography.Text strong>{item.canonical_name}</Typography.Text>
                          <Typography.Text type="secondary">
                            {categoryLabels[item.category] ?? item.category} · {item.document_count} 份文档
                          </Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </div>
            </Space>
          ) : null}
        </ValidationDrawer>
      </Space>
    </ValidationWorkspace>
  );
}

function parseAliasInput(value: string): string[] {
  return value
    .split(/[,\n，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
