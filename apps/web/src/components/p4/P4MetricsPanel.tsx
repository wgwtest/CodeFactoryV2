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
    <div
      id="xx-p4-metrics-strip"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(132px, 1fr))",
        gap: 12,
        padding: 12,
        borderRadius: 20,
        background: "rgba(255, 255, 255, 0.12)",
        border: "1px solid rgba(255, 255, 255, 0.14)",
        backdropFilter: "blur(14px)",
        boxShadow: "0 18px 36px rgba(8, 15, 34, 0.14)",
      }}
    >
      {metricItems.map((item) => (
        <div
          key={item.key}
          id={`xx-p4-metric-${item.key}`}
          style={{
            minHeight: 72,
            padding: "10px 12px",
            borderRadius: 14,
            background: "rgba(247, 250, 252, 0.92)",
            boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.7)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <Typography.Text
            style={{
              fontSize: 11,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#64748b",
            }}
          >
            {item.title}
          </Typography.Text>
          <Typography.Text
            strong
            style={{
              fontSize: 26,
              lineHeight: 1.1,
              color: "#0f172a",
              marginTop: 6,
            }}
          >
            {metrics[item.key]}
            {item.suffix ?? ""}
          </Typography.Text>
        </div>
      ))}
    </div>
  );
}
