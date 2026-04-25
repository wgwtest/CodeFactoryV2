import { Button, Card, Empty, Input, List, Space, Typography } from "antd";
import { useState } from "react";

import type { P3OrderDetail } from "../../lib/api";

type P3ReviewWorkspaceProps = {
  order: P3OrderDetail | null;
  onCreateThread: (payload: { topic: string; anchor: string; message: string }) => Promise<void>;
  onFreeze: () => Promise<void>;
};

export function P3ReviewWorkspace({ order, onCreateThread, onFreeze }: P3ReviewWorkspaceProps) {
  const [message, setMessage] = useState("补充后续微服务拆分条件。");

  if (!order) {
    return (
      <Card title="评审协作" style={{ borderRadius: 18 }}>
        <Empty description="请选择订单" />
      </Card>
    );
  }

  return (
    <Card title="评审协作" style={{ borderRadius: 18 }}>
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="输入评审意见"
        />
        <Space>
          <Button
            onClick={() =>
              void onCreateThread({
                topic: "统一服务补充说明",
                anchor: "section:architecture",
                message,
              })
            }
          >
            新增评论线程
          </Button>
          <Button type="primary" onClick={() => void onFreeze()}>
            冻结软件设计说明
          </Button>
        </Space>
        <List
          locale={{ emptyText: "当前没有评论线程" }}
          dataSource={order.review_threads}
          renderItem={(thread) => (
            <List.Item key={thread.thread_id}>
              <List.Item.Meta
                title={<Typography.Text strong>{thread.topic}</Typography.Text>}
                description={thread.messages.join(" / ")}
              />
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}
