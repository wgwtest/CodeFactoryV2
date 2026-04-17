import { Card, Descriptions, Empty } from "antd";

import type { P3OrderDetail } from "../../lib/api";

export function P3OrderContextPanel({ order }: { order: P3OrderDetail | null }) {
  if (!order) {
    return (
      <Card title="当前订单上下文" style={{ borderRadius: 18 }}>
        <Empty description="请选择订单" />
      </Card>
    );
  }

  return (
    <Card title="当前订单上下文" style={{ borderRadius: 18 }}>
      <Descriptions column={1} size="small">
        <Descriptions.Item label="应用名称">{order.requirement_spec_summary.application_name}</Descriptions.Item>
        <Descriptions.Item label="领域">{order.requirement_spec_summary.domain_name}</Descriptions.Item>
        <Descriptions.Item label="虚规状态">{order.requirement_spec_summary.status}</Descriptions.Item>
        <Descriptions.Item label="P3 状态">{order.status}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
