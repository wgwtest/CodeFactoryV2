import { Typography } from "antd";

import type { ToolHubOverviewMetrics } from "../../lib/api";

type P4MetricsPanelProps = {
  metrics: ToolHubOverviewMetrics;
};

const metricItems: Array<{
  key: keyof ToolHubOverviewMetrics;
  title: string;
  suffix?: string;
}> = [
  { key: "tool_count", title: "工具总数" },
  { key: "verified_tool_count", title: "已验证工具" },
  { key: "active_chain_count", title: "活跃工具链" },
  { key: "overlap_candidate_count", title: "重叠候选" },
  { key: "pending_suggestion_count", title: "待演进建议" },
  { key: "recent_success_rate", title: "最近 24h 成功率", suffix: "%" },
];

export function P4MetricsPanel({ metrics }: P4MetricsPanelProps) {
  return (
    <div id="xx-p4-metrics-strip" className="xx-p4-metrics-strip">
      {metricItems.map((item) => (
        <div key={item.key} id={`xx-p4-metric-${item.key}`} className="xx-p4-metric-card">
          <Typography.Text className="xx-p4-metric-title">
            {item.title}
          </Typography.Text>
          <Typography.Text strong className="xx-p4-metric-value">
            {metrics[item.key]}
            {item.suffix ?? ""}
          </Typography.Text>
        </div>
      ))}
    </div>
  );
}
