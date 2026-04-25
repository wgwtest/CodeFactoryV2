import { Card, Empty, List, Typography } from "antd";

import type { P3OrderDetail } from "../../lib/api";

export function P3DesignWorkspace({ order }: { order: P3OrderDetail | null }) {
  if (!order?.design_description) {
    return (
      <Card title="软件设计说明草案" style={{ borderRadius: 18 }}>
        <Empty description="当前没有软设草案" />
      </Card>
    );
  }

  return (
    <Card title="软件设计说明草案" style={{ borderRadius: 18 }}>
      <List
        dataSource={order.design_description.sections}
        renderItem={(section) => (
          <List.Item key={section.id}>
            <List.Item.Meta
              title={<Typography.Text strong>{section.title}</Typography.Text>}
              description={section.summary}
            />
          </List.Item>
        )}
      />
    </Card>
  );
}
