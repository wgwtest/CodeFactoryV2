import { Card, Empty, List, Tag, Typography } from "antd";

import type { ToolHubRecentRunSummary } from "../../lib/api";

type P4RunListProps = {
  title: string;
  items: ToolHubRecentRunSummary[];
  emptyText: string;
};

export function P4RunList({ title, items, emptyText }: P4RunListProps) {
  return (
    <Card title={title} className="xx-p4-panel-card">
      {items.length === 0 ? (
        <Empty description={emptyText} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          dataSource={items}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <span>
                    {item.title} <Tag>{item.run_type === "match" ? "输入链" : "巡检"}</Tag>
                  </span>
                }
                description={`${item.summary} · ${item.created_at}`}
              />
              <Typography.Text strong>{item.status}</Typography.Text>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
