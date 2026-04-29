import { Button, Card, Empty, List, Space, Tag, Typography } from "antd";

import type { P3OrderSummary } from "../../lib/api";

type P3OrderQueueProps = {
  orders: P3OrderSummary[];
  selectedOrderId: string | null;
  onSelectOrder: (orderId: string) => void | Promise<void>;
  onApprove: (orderId: string) => void | Promise<void>;
  onReject: (orderId: string) => void | Promise<void>;
  onGenerateDraft: (orderId: string) => void | Promise<void>;
};

export function P3OrderQueue({
  orders,
  selectedOrderId,
  onSelectOrder,
  onApprove,
  onReject,
  onGenerateDraft,
}: P3OrderQueueProps) {
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
                padding: 12,
                borderRadius: 12,
                background: order.order_id === selectedOrderId ? "#eff6ff" : "transparent",
                alignItems: "stretch",
              }}
            >
              <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
                  <Space wrap size={[8, 8]} style={{ width: "100%" }}>
                    <Typography.Text
                      strong
                      style={{
                        fontSize: 15,
                        lineHeight: 1.5,
                        whiteSpace: "normal",
                        wordBreak: "break-word",
                      }}
                    >
                      {order.application_name}
                    </Typography.Text>
                    <Tag color="blue" style={{ marginInlineEnd: 0 }}>
                      {order.status}
                    </Tag>
                  </Space>
                  <Typography.Text type="secondary" style={{ whiteSpace: "normal", wordBreak: "break-all" }}>
                    需求规格: {order.requirement_spec_id}
                  </Typography.Text>
                </div>

                <div
                  data-testid={`p3-order-actions-${order.order_id}`}
                  style={{ display: "flex", flexWrap: "wrap", gap: 8 }}
                >
                  <Button
                    type="primary"
                    size="small"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onApprove(order.order_id);
                    }}
                  >
                    审批通过
                  </Button>
                  <Button
                    danger
                    size="small"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onReject(order.order_id);
                    }}
                  >
                    驳回
                  </Button>
                  <Button
                    size="small"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onGenerateDraft(order.order_id);
                    }}
                  >
                    生成软设草案
                  </Button>
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
