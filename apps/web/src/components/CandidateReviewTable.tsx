import type { Key } from "react";
import { Button, Space, Table, Tag } from "antd";

import type { ArchiveReviewCandidate, ArchiveReviewStatus } from "../lib/api";

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

const reviewStatusColors: Record<ArchiveReviewStatus, string> = {
  pending: "gold",
  approved: "green",
  rejected: "red",
};

type CandidateReviewTableProps = {
  items: ArchiveReviewCandidate[];
  loading: boolean;
  selectedRowKeys: Key[];
  onSelectionChange: (keys: Key[]) => void;
  onOpenItem: (itemId: string) => void;
  onReview: (itemId: string, reviewStatus: ArchiveReviewStatus) => void;
};

export function CandidateReviewTable({
  items,
  loading,
  selectedRowKeys,
  onSelectionChange,
  onOpenItem,
  onReview,
}: CandidateReviewTableProps) {
  return (
    <Table
      rowKey="id"
      dataSource={items}
      loading={loading}
      pagination={{ pageSize: 8 }}
      locale={{ emptyText: "暂无候选数据" }}
      rowSelection={{
        selectedRowKeys,
        onChange: (keys) => onSelectionChange(keys),
      }}
      columns={[
        {
          title: "类型",
          dataIndex: "item_type",
          render: (value: string) => itemTypeLabels[value] ?? value,
        },
        {
          title: "名称",
          dataIndex: "canonical_name",
        },
        {
          title: "类别",
          dataIndex: "category",
          render: (value: string) => <Tag>{categoryLabels[value] ?? value}</Tag>,
        },
        {
          title: "覆盖文档",
          dataIndex: "document_count",
          render: (value: number) => `${value} 份文档`,
        },
        {
          title: "置信度",
          dataIndex: "confidence",
          render: (value: number) => value.toFixed(2),
        },
        {
          title: "审核状态",
          dataIndex: "review_status",
          render: (value: ArchiveReviewStatus) => (
            <Tag color={reviewStatusColors[value]}>{reviewStatusLabels[value]}</Tag>
          ),
        },
        {
          title: "证据",
          render: (_: unknown, record: ArchiveReviewCandidate) => {
            if (record.evidence_excerpt && record.evidence_document_title) {
              if (record.evidence_excerpt === record.evidence_document_title) {
                return record.evidence_excerpt;
              }
              return `${record.evidence_excerpt} · ${record.evidence_document_title}`;
            }
            return record.evidence_excerpt || record.evidence_document_title || "暂无证据摘录";
          },
        },
        {
          title: "操作",
          render: (_: unknown, record: ArchiveReviewCandidate) => (
            <Space size={8} wrap>
              <Button type="link" onClick={() => onOpenItem(record.id)}>
                查看 / 编辑
              </Button>
              <Button type="link" onClick={() => onReview(record.id, "approved")}>
                直接通过
              </Button>
              <Button danger type="link" onClick={() => onReview(record.id, "rejected")}>
                直接驳回
              </Button>
            </Space>
          ),
        },
      ]}
    />
  );
}
