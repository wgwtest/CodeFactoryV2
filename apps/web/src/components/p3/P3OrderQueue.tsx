import { Button, Card, Empty, List, Space, Tag, Typography } from "antd";

import type { P3OrderSummary } from "../../lib/api";

type P3OrderQueueProps = {
  orders: P3OrderSummary[];
  selectedOrderId: string | null;
  onSelectOrder: (orderId: string) => void | Promise<void>;
  onApprove: (orderId: string) => void | Promise<void>;
  onGenerateDraft: (orderId: string) => void | Promise<void>;
};

export function P3OrderQueue({ orders, selectedOrderId, onSelectOrder, onApprove, onGenerateDraft }: P3OrderQueueProps) {
  return (
    <Card title="虚规订单列表" style={{ borderRadius: 18 }}>
      {orders.length === 0 ? (
        <Empty description="当前没有订单" />
      ) : (
        <List
          dataSource={orders}
          renderItem={(order) => (
            <List.Item
              key={order.order_id}
              onClick={() => void onSelectOrder(order.order_id)}
              style={{
                cursor: "pointer",
                paddingInline: 12,
                borderRadius: 12,
                background: order.order_id === selectedOrderId ? "#eff6ff" : "transparent",
              }}
              actions={[
                <Button
                  key="approve"
                  type="primary"
                  size="small"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onApprove(order.order_id);
                  }}
                >
                  审批通过
                </Button>,
                <Button
                  key="generate"
                  size="small"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onGenerateDraft(order.order_id);
                  }}
                >
                  生成软设草案
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Typography.Text strong>{order.application_name}</Typography.Text>
                    <Tag color="blue">{order.status}</Tag>
                  </Space>
                }
                description={`需求规格: ${order.requirement_spec_id}`}
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
