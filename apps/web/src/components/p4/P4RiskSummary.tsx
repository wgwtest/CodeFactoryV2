import { Card, Empty, List, Tag, Typography } from "antd";

import type { ToolHubRiskSummaryItem } from "../../lib/api";

type P4RiskSummaryProps = {
  items: ToolHubRiskSummaryItem[];
};

function colorForSeverity(severity: ToolHubRiskSummaryItem["severity"]) {
  if (severity === "critical") {
    return "red";
  }
  if (severity === "warning") {
    return "gold";
  }
  return "blue";
}

export function P4RiskSummary({ items }: P4RiskSummaryProps) {
  return (
    <Card title="风险摘要" style={{ borderRadius: 18 }}>
      {items.length === 0 ? (
        <Empty description="暂无风险摘要" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          dataSource={items}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <span>
                    {item.title} <Tag color={colorForSeverity(item.severity)}>{item.severity}</Tag>
                  </span>
                }
                description={item.description}
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
