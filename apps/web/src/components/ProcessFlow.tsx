import { useDeferredValue, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Empty, Input, List, Space, Spin, Table, Tag, Typography } from "antd";

import { getArchiveItemDetail, getArchiveItemGraph } from "../lib/archiveKnowledge";
import type {
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeItemGraph,
  ArchiveKnowledgeProcess,
} from "../lib/api";
import { EvidenceList } from "./EvidenceList";
import { KnowledgeNeighborhoodGraph } from "./KnowledgeNeighborhoodGraph";
import { ValidationDrawer } from "./ValidationDrawer";

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

const itemTypeLabels: Record<string, string> = {
  entity: "实体",
  event: "事件",
  process: "流程",
};

const relationTypeLabels: Record<string, string> = {
  describes: "描述",
  operational_exchange: "运行交换",
  owned_by: "责任归属",
  participates_in_exchange: "参与交换",
  part_of: "组成/隶属",
  supports: "支撑",
  process_scoped_by: "阶段约束",
  scoped_by: "阶段约束",
};

type ProcessFlowProps = {
  archiveId: string | null;
  error: string | null;
  loading: boolean;
  processes: ArchiveKnowledgeProcess[];
};

export function ProcessFlow({ archiveId, error, loading, processes }: ProcessFlowProps) {
  const [searchValue, setSearchValue] = useState("");
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ArchiveKnowledgeItemDetail | null>(null);
  const [itemGraph, setItemGraph] = useState<ArchiveKnowledgeItemGraph | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const deferredSearchValue = useDeferredValue(searchValue);

  useEffect(() => {
    const processId = selectedProcessId;

    if (!processId || !archiveId) {
      setDetail(null);
      setItemGraph(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      const activeProcessId = processId;
      const currentArchiveId = archiveId;
      try {
        setDetailLoading(true);
        if (activeProcessId === null || currentArchiveId === null) {
          return;
        }
        const [detailResponse, graphResponse] = await Promise.all([
          getArchiveItemDetail(activeProcessId, currentArchiveId),
          getArchiveItemGraph(activeProcessId, currentArchiveId),
        ]);
        if (cancelled) {
          return;
        }
        setDetail(detailResponse.data);
        setItemGraph(graphResponse.data);
        setDetailError(null);
      } catch (loadError) {
        if (!cancelled) {
          setDetailError(loadError instanceof Error ? loadError.message : "加载流程详情失败");
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
  }, [archiveId, selectedProcessId]);

  if (loading) {
    return (
      <Space direction="vertical" size={8} style={{ display: "flex", padding: "24px 0" }}>
        <Spin />
        <Typography.Text type="secondary">正在加载档案流程...</Typography.Text>
      </Space>
    );
  }

  if (error) {
    return <Alert type="error" message="档案流程暂不可用" description={error} showIcon />;
  }

  if (processes.length === 0) {
    return <Empty description="暂无流程数据" />;
  }

  const normalizedQuery = deferredSearchValue.trim().toLowerCase();
  const filteredProcesses = processes.filter((item) => {
    if (!normalizedQuery) {
      return true;
    }

    const haystack = [item.name, ...item.evidence.map((entry) => entry.excerpt)].join(" ").toLowerCase();
    return haystack.includes(normalizedQuery);
  });

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
                流程清单
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                先从已发布流程中检索目标流程，再下钻查看证据、关联对象、业务关系结构与关系邻域。
              </Typography.Paragraph>
            </Space>
            <Space wrap size={[8, 8]}>
              <Tag
                color="blue"
                style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}
              >
                当前显示：{filteredProcesses.length}
              </Tag>
            </Space>
          </div>

          <Input.Search
            allowClear
            placeholder="搜索流程名称或证据摘录"
            size="large"
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            style={{ maxWidth: 420 }}
          />

          <Table
            rowKey="id"
            dataSource={filteredProcesses}
            size="middle"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: "暂无匹配流程" }}
            columns={[
              { title: "名称", dataIndex: "name" },
              {
                title: "类别",
                dataIndex: "category",
                width: 120,
                render: (value: string) => <Tag>{categoryLabels[value] ?? value}</Tag>,
              },
              {
                title: "证据摘要",
                render: (_: unknown, record: ArchiveKnowledgeProcess) => (
                  <Typography.Text type="secondary">
                    {record.evidence[0]?.excerpt ?? "暂无证据摘录"}
                  </Typography.Text>
                ),
              },
              {
                title: "覆盖文档",
                dataIndex: "document_ids",
                width: 120,
                render: (value: string[]) => `${value.length} 份文档`,
              },
              {
                title: "操作",
                width: 120,
                render: (_: unknown, record: ArchiveKnowledgeProcess) => (
                  <Button type="link" onClick={() => setSelectedProcessId(record.id)}>
                    查看链路
                  </Button>
                ),
              },
            ]}
          />
        </Space>
      </Card>

      <ValidationDrawer
        title="流程详情"
        open={selectedProcessId !== null}
        onClose={() => setSelectedProcessId(null)}
        width={640}
        loading={detailLoading}
        loadingText="正在加载流程详情..."
        error={detailError}
        errorMessage="流程详情暂不可用"
      >
        {detail ? (
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <div>
              <Typography.Title level={4} style={{ marginTop: 0 }}>
                {detail.name}
              </Typography.Title>
              <Space wrap>
                <Tag>{itemTypeLabels[detail.item_type] ?? detail.item_type}</Tag>
                <Tag>{categoryLabels[detail.category] ?? detail.category}</Tag>
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
                <Descriptions.Item label="中文释义">
                  {detail.interpretation.display_name ?? "无"}
                </Descriptions.Item>
                <Descriptions.Item label="标准名称">
                  {detail.interpretation.standard_name ?? "无"}
                </Descriptions.Item>
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
