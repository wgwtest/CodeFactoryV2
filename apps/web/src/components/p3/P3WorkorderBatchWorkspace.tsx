import { Button, Card, Empty, List, Space, Typography } from "antd";

import type { P3OrderDetail, P3WorkorderBatch } from "../../lib/api";

type P3WorkorderBatchWorkspaceProps = {
  order: P3OrderDetail | null;
  onGenerateBatch: () => Promise<P3WorkorderBatch | void>;
  onPushToP4: () => Promise<void>;
};

export function P3WorkorderBatchWorkspace({ order, onGenerateBatch, onPushToP4 }: P3WorkorderBatchWorkspaceProps) {
  if (!order) {
    return (
      <Card title="批次模块工单包" style={{ borderRadius: 18 }}>
        <Empty description="请选择订单" />
      </Card>
    );
  }

  return (
    <Card title="批次模块工单包" style={{ borderRadius: 18 }}>
      {!order.workorder_batch ? (
        <Button type="primary" onClick={() => void onGenerateBatch()}>
          生成批次工单包
        </Button>
      ) : (
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Space direction="vertical" size={4}>
            <Typography.Text strong>架构建议</Typography.Text>
            <Typography.Text>{order.workorder_batch.package_overview.architecture_recommendation}</Typography.Text>
          </Space>
          <Space direction="vertical" size={4}>
            <Typography.Text strong>交互模式</Typography.Text>
            <Typography.Text>{order.workorder_batch.package_overview.interaction_mode}</Typography.Text>
          </Space>
          <List
            dataSource={order.workorder_batch.items}
            renderItem={(item) => (
              <List.Item key={item.item_id}>
                <Typography.Text>{item.title}</Typography.Text>
              </List.Item>
            )}
          />
          <Button type="primary" onClick={() => void onPushToP4()}>
            推送到 P4
          </Button>
        </Space>
      )}
    </Card>
  );
}
