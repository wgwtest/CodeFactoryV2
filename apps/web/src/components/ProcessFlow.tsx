import { Alert, Empty, List, Space, Spin, Tag, Typography } from "antd";

import type { ArchiveKnowledgeProcess } from "../lib/api";

const categoryLabels: Record<string, string> = {
  domain_process: "领域流程"
};

type ProcessFlowProps = {
  error: string | null;
  loading: boolean;
  processes: ArchiveKnowledgeProcess[];
};

export function ProcessFlow({ error, loading, processes }: ProcessFlowProps) {
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

  return (
    <List
      bordered
      dataSource={processes}
      renderItem={(item) => (
        <List.Item>
          <Space direction="vertical" size={4} style={{ width: "100%" }}>
            <Space>
              <Typography.Text strong>{item.name}</Typography.Text>
              <Tag>{categoryLabels[item.category] ?? item.category}</Tag>
              <Typography.Text type="secondary">{item.document_ids.length} 份文档</Typography.Text>
            </Space>
            {item.evidence[0] ? <Typography.Text type="secondary">{item.evidence[0].excerpt}</Typography.Text> : null}
          </Space>
        </List.Item>
      )}
    />
  );
}
