import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Empty, Input, List, Space, Spin, Table, Tag, Typography } from "antd";

import { getArchiveItemDetail, getArchiveItemGraph } from "../lib/archiveKnowledge";
import { EvidenceList } from "./EvidenceList";
import { KnowledgeNeighborhoodGraph } from "./KnowledgeNeighborhoodGraph";
import { KnowledgeTopologyGraph } from "./KnowledgeTopologyGraph";
import { ValidationDrawer } from "./ValidationDrawer";
import type {
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeEvent,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeInterpretation,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeItemGraph,
  ArchiveKnowledgeProcess,
  ArchiveKnowledgeSummary,
} from "../lib/api";

const typeLabels: Record<string, string> = {
  architecture_artifact: "架构产物",
  architecture_concept: "架构概念",
  domain_concept: "领域概念",
  domain_process: "领域流程",
  organization: "组织",
  service_category: "服务分类",
  service_taxonomy: "服务分类",
  system_or_service: "系统/服务",
  operational_node: "运行节点",
  information_exchange: "信息交换",
  timeline_event: "时间事件",
};

const itemTypeLabels: Record<string, string> = {
  entity: "实体",
  event: "事件",
  process: "流程",
};

const relationTypeLabels: Record<string, string> = {
  part_of: "组成/隶属",
  describes: "描述",
  owned_by: "责任归属",
  operational_exchange: "运行交换",
  participates_in_exchange: "参与交换",
  supports: "支撑",
  scoped_by: "阶段约束",
  process_scoped_by: "阶段约束",
};

type KnowledgeBrowserItem = {
  id: string;
  item_type: "entity" | "event" | "process";
  name: string;
  category: string;
  aliases: string[];
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
};

type KnowledgeGraphProps = {
  archiveId: string | null;
  entities: ArchiveKnowledgeEntity[];
  events: ArchiveKnowledgeEvent[];
  processes: ArchiveKnowledgeProcess[];
  error: string | null;
  graph: ArchiveKnowledgeGraph | null;
  loading: boolean;
  selectedItemTypes: Array<"entity" | "event" | "process">;
  summary: ArchiveKnowledgeSummary | null;
  viewMode: "list" | "graph";
};

export function KnowledgeGraph({
  archiveId,
  entities,
  events,
  processes,
  error,
  graph,
  loading,
  selectedItemTypes,
  summary,
  viewMode,
}: KnowledgeGraphProps) {
  const [searchValue, setSearchValue] = useState("");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ArchiveKnowledgeItemDetail | null>(null);
  const [itemGraph, setItemGraph] = useState<ArchiveKnowledgeItemGraph | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const deferredSearchValue = useDeferredValue(searchValue);

  const allItems = useMemo<KnowledgeBrowserItem[]>(
    () => [
      ...entities.map((item) => ({ ...item, item_type: "entity" as const })),
      ...events,
      ...processes,
    ],
    [entities, events, processes],
  );

  const aliasesById = useMemo(
    () => new Map(allItems.map((item) => [item.id, item.aliases])),
    [allItems],
  );

  const filteredItems = useMemo(() => {
    const normalizedQuery = deferredSearchValue.trim().toLowerCase();
    return allItems.filter((item) => {
      if (!selectedItemTypes.includes(item.item_type)) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [
        item.name,
        ...item.aliases,
        item.interpretation.display_name ?? "",
        item.interpretation.standard_name ?? "",
        item.interpretation.summary,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [allItems, deferredSearchValue, selectedItemTypes]);

  useEffect(() => {
    if (selectedItemId && !allItems.some((item) => item.id === selectedItemId)) {
      setSelectedItemId(null);
    }
  }, [allItems, selectedItemId]);

  useEffect(() => {
    const itemId = selectedItemId;

    if (!itemId || !archiveId) {
      setDetail(null);
      setItemGraph(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      const activeItemId = itemId;
      const currentArchiveId = archiveId;
      try {
        setDetailLoading(true);
        if (activeItemId === null || currentArchiveId === null) {
          return;
        }
        const [detailResponse, graphResponse] = await Promise.all([
          getArchiveItemDetail(activeItemId, currentArchiveId),
          getArchiveItemGraph(activeItemId, currentArchiveId),
        ]);
        if (cancelled) {
          return;
        }
        setDetail(detailResponse.data);
        setItemGraph(graphResponse.data);
        setDetailError(null);
      } catch (loadError) {
        if (!cancelled) {
          setDetailError(loadError instanceof Error ? loadError.message : "加载知识详情失败");
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [archiveId, selectedItemId]);

  if (loading) {
    return (
      <Space direction="vertical" size={8} style={{ display: "flex", padding: "24px 0" }}>
        <Spin />
        <Typography.Text type="secondary">正在加载档案知识...</Typography.Text>
      </Space>
    );
  }

  if (error) {
    return <Alert type="error" message="档案知识暂不可用" description={error} showIcon />;
  }

  if (!summary || !graph) {
    return <Empty description="暂无档案知识" />;
  }

  return (
    <Space direction="vertical" size={24} style={{ display: "flex" }}>
      <Card
        variant="borderless"
        style={{ borderRadius: 24, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.06)" }}
        styles={{ body: { padding: 24 } }}
      >
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <Space direction="vertical" size={6} style={{ display: "flex" }}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {viewMode === "list" ? "知识列表" : "知识图谱"}
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                {viewMode === "list"
                  ? "列表视图会根据上方类型筛选实时收敛范围，并继续支持查看详情、证据、关系结构和邻域。"
                  : "图谱视图会在当前类型筛选范围内绘制知识关系，并保留搜索命中节点及其一度关联。"}
              </Typography.Paragraph>
            </Space>
            <Space wrap size={[8, 8]}>
              <Tag
                color="blue"
                style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}
              >
                {viewMode === "list" ? `当前显示：${filteredItems.length}` : `当前类型：${selectedItemTypes.length}`}
              </Tag>
              <Tag style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}>
                总关系数：{graph.edges.length}
              </Tag>
            </Space>
          </div>

          <Input.Search
            allowClear
            placeholder="搜索名称、别名或释义"
            size="large"
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            style={{ maxWidth: 420 }}
          />

          {selectedItemTypes.length === 0 ? (
            <Empty description="请至少选择一种知识类型" />
          ) : viewMode === "list" ? (
            <Table
              rowKey="id"
              dataSource={filteredItems}
              size="middle"
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: "暂无匹配知识" }}
              columns={[
                { title: "名称", dataIndex: "name" },
                {
                  title: "类型",
                  dataIndex: "item_type",
                  width: 90,
                  render: (value: string) => <Tag>{itemTypeLabels[value] ?? value}</Tag>,
                },
                {
                  title: "类别",
                  dataIndex: "category",
                  width: 120,
                  render: (value: string) => <Tag>{typeLabels[value] ?? value}</Tag>,
                },
                {
                  title: "释义",
                  render: (_: unknown, record: KnowledgeBrowserItem) => (
                    <Space direction="vertical" size={2} style={{ display: "flex" }}>
                      {record.interpretation.display_name &&
                      record.interpretation.display_name !== record.name ? (
                        <Typography.Text strong>{record.interpretation.display_name}</Typography.Text>
                      ) : record.interpretation.standard_name ? (
                        <Typography.Text strong>{record.interpretation.standard_name}</Typography.Text>
                      ) : null}
                      <Typography.Text type="secondary">{record.interpretation.summary}</Typography.Text>
                    </Space>
                  ),
                },
                {
                  title: "别名",
                  dataIndex: "aliases",
                  render: (aliases: string[]) => aliases.join(" / ") || "无",
                },
                {
                  title: "覆盖文档",
                  dataIndex: "document_count",
                  width: 100,
                  render: (value: number) => `${value} 份文档`,
                },
                {
                  title: "操作",
                  width: 100,
                  render: (_: unknown, record: KnowledgeBrowserItem) => (
                    <Button type="link" onClick={() => setSelectedItemId(record.id)}>
                      查看详情
                    </Button>
                  ),
                },
              ]}
            />
          ) : (
            <KnowledgeTopologyGraph
              aliasesById={aliasesById}
              graph={graph}
              query={deferredSearchValue}
              selectedItemId={selectedItemId}
              selectedItemTypes={selectedItemTypes}
              onSelectItem={setSelectedItemId}
            />
          )}
        </Space>
      </Card>

      <ValidationDrawer
        title="知识详情"
        open={selectedItemId !== null}
        onClose={() => setSelectedItemId(null)}
        width={640}
        loading={detailLoading}
        loadingText="正在加载知识详情..."
        error={detailError}
        errorMessage="知识详情暂不可用"
      >
        {detail ? (
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <div>
              <Typography.Title level={4} style={{ marginTop: 0 }}>
                {detail.name}
              </Typography.Title>
              <Space wrap>
                <Tag>{itemTypeLabels[detail.item_type] ?? detail.item_type}</Tag>
                <Tag>{typeLabels[detail.category] ?? detail.category}</Tag>
                <Typography.Text type="secondary">{detail.document_count} 份文档</Typography.Text>
              </Space>
            </div>

            <div>
              <Typography.Title level={5}>这是什么</Typography.Title>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="知识类型">{detail.interpretation.kind_label}</Descriptions.Item>
                <Descriptions.Item label="工件族">
                  {detail.interpretation.family_label
                    ? `${detail.interpretation.family_label} (${detail.interpretation.family_code})`
                    : "无"}
                </Descriptions.Item>
                <Descriptions.Item label="中文释义">{detail.interpretation.display_name ?? "无"}</Descriptions.Item>
                <Descriptions.Item label="标准名称">{detail.interpretation.standard_name ?? "无"}</Descriptions.Item>
                <Descriptions.Item label="解释">{detail.interpretation.summary}</Descriptions.Item>
                <Descriptions.Item label="通常产出方式">
                  {detail.interpretation.producer_hint ?? "当前未识别"}
                </Descriptions.Item>
              </Descriptions>
            </div>

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="别名">{detail.aliases.join(" / ") || "无"}</Descriptions.Item>
            </Descriptions>

            <EvidenceList title="证据摘录" items={detail.evidence} />

            <div>
              <Typography.Title level={5}>关联文档</Typography.Title>
              <List
                bordered
                dataSource={detail.documents}
                locale={{ emptyText: "暂无关联文档" }}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={2}>
                      <Typography.Text>{item.title}</Typography.Text>
                      <Typography.Text type="secondary">
                        {item.file_type} · {item.source_archive}
                      </Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>

            <div>
              <Typography.Title level={5}>业务关系结构</Typography.Title>
              {detail.relationship_sections.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无业务关系结构" />
              ) : (
                <Space direction="vertical" size={12} style={{ display: "flex" }}>
                  {detail.relationship_sections.map((section) => (
                    <div key={section.key}>
                      <Typography.Text strong>{section.title}</Typography.Text>
                      <List
                        bordered
                        size="small"
                        dataSource={section.items}
                        locale={{ emptyText: "暂无关联内容" }}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={2} style={{ display: "flex" }}>
                              <Space wrap>
                                <Tag>{itemTypeLabels[item.item_type] ?? item.item_type}</Tag>
                                <Tag color="blue">{item.relation_label}</Tag>
                                <Typography.Text>{item.name}</Typography.Text>
                              </Space>
                              {item.evidence ? (
                                <Typography.Text type="secondary">{item.evidence}</Typography.Text>
                              ) : null}
                            </Space>
                          </List.Item>
                        )}
                      />
                    </div>
                  ))}
                </Space>
              )}
            </div>

            <div>
              <Typography.Title level={5}>关联关系</Typography.Title>
              <List
                bordered
                dataSource={detail.related_items}
                locale={{ emptyText: "暂无关联关系" }}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <Tag>{itemTypeLabels[item.item_type] ?? item.item_type}</Tag>
                      <Typography.Text>{item.name}</Typography.Text>
                      <Typography.Text type="secondary">
                        {relationTypeLabels[item.relation_type] ?? item.relation_type}
                      </Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>

            <KnowledgeNeighborhoodGraph graph={itemGraph} />
          </Space>
        ) : null}
      </ValidationDrawer>
    </Space>
  );
}
