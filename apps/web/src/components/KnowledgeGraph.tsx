import { useDeferredValue, useEffect, useState } from "react";
import { Alert, Button, Descriptions, Empty, Input, List, Row, Space, Spin, Statistic, Table, Tag, Typography } from "antd";

import { api } from "../lib/api";
import { EvidenceList } from "./EvidenceList";
import { ValidationDrawer } from "./ValidationDrawer";
import type {
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeSummary,
} from "../lib/api";

const typeLabels: Record<string, string> = {
  architecture_artifact: "架构产物",
  architecture_concept: "架构概念",
  domain_concept: "领域概念",
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

type KnowledgeGraphProps = {
  archiveId: string;
  entities: ArchiveKnowledgeEntity[];
  error: string | null;
  graph: ArchiveKnowledgeGraph | null;
  loading: boolean;
  summary: ArchiveKnowledgeSummary | null;
};

export function KnowledgeGraph({ archiveId, entities, error, graph, loading, summary }: KnowledgeGraphProps) {
  const [searchValue, setSearchValue] = useState("");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ArchiveKnowledgeItemDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const deferredSearchValue = useDeferredValue(searchValue);

  useEffect(() => {
    if (!selectedEntityId) {
      setDetail(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      try {
        setDetailLoading(true);
        const response = await api.get<ArchiveKnowledgeItemDetail>(
          `/knowledge/archive/${archiveId}/items/${selectedEntityId}`,
        );
        if (cancelled) {
          return;
        }
        setDetail(response.data);
        setDetailError(null);
      } catch (loadError) {
        if (!cancelled) {
          setDetailError(loadError instanceof Error ? loadError.message : "加载实体详情失败");
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
  }, [archiveId, selectedEntityId]);

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

  const normalizedQuery = deferredSearchValue.trim().toLowerCase();
  const filteredEntities = entities.filter((item) => {
    if (!normalizedQuery) {
      return true;
    }
    const haystack = [item.name, ...item.aliases].join(" ").toLowerCase();
    return haystack.includes(normalizedQuery);
  });

  return (
    <Space direction="vertical" size={24} style={{ display: "flex" }}>
      <Row gutter={16}>
        <Statistic title="文档" value={summary.document_count} />
        <Statistic title="实体" value={summary.entity_count} />
        <Statistic title="事件" value={summary.event_count} />
        <Statistic title="流程" value={summary.process_count} />
      </Row>
      <Typography.Paragraph type="secondary">关系数：{graph.edges.length}</Typography.Paragraph>

      <Space direction="vertical" size={12} style={{ display: "flex" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          实体列表
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
          当前共收录 {entities.length} 个实体，可按实体名称或别名过滤，并查看实体证据与关联关系。
        </Typography.Paragraph>
        <Input.Search
          allowClear
          placeholder="搜索实体名称或别名"
          value={searchValue}
          onChange={(event) => setSearchValue(event.target.value)}
        />
        <Table
          rowKey="id"
          dataSource={filteredEntities}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: "暂无匹配实体" }}
          columns={[
            { title: "名称", dataIndex: "name" },
            {
              title: "类别",
              dataIndex: "category",
              render: (value: string) => <Tag>{typeLabels[value] ?? value}</Tag>,
            },
            {
              title: "释义",
              render: (_: unknown, record: ArchiveKnowledgeEntity) => (
                <Space direction="vertical" size={2} style={{ display: "flex" }}>
                  <Typography.Text>{record.interpretation.display_name ?? record.interpretation.standard_name ?? "待补充"}</Typography.Text>
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
              render: (value: number) => `${value} 份文档`,
            },
            {
              title: "操作",
              render: (_: unknown, record: ArchiveKnowledgeEntity) => (
                <Button type="link" onClick={() => setSelectedEntityId(record.id)}>
                  查看详情
                </Button>
              ),
            },
          ]}
        />
      </Space>

      <ValidationDrawer
        title="实体详情"
        open={selectedEntityId !== null}
        onClose={() => setSelectedEntityId(null)}
        width={640}
        loading={detailLoading}
        loadingText="正在加载实体详情..."
        error={detailError}
        errorMessage="实体详情暂不可用"
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
                  {detail.interpretation.family_label ? `${detail.interpretation.family_label} (${detail.interpretation.family_code})` : "无"}
                </Descriptions.Item>
                <Descriptions.Item label="中文释义">{detail.interpretation.display_name ?? "无"}</Descriptions.Item>
                <Descriptions.Item label="标准名称">{detail.interpretation.standard_name ?? "无"}</Descriptions.Item>
                <Descriptions.Item label="解释">{detail.interpretation.summary}</Descriptions.Item>
                <Descriptions.Item label="通常产出方式">{detail.interpretation.producer_hint ?? "当前未识别"}</Descriptions.Item>
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
                      <Typography.Text type="secondary">{item.relation_type}</Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          </Space>
        ) : null}
      </ValidationDrawer>
    </Space>
  );
}
