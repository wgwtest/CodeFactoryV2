import type { ReactNode } from "react";
import { Card, Space, Tag, Typography } from "antd";

type WorkspaceOverviewTag = {
  label: string;
  color?: string;
};

export type WorkspaceOverviewMetric = {
  title: string;
  value: number | string;
  accent?: string;
  tone?: string;
};

type WorkspaceOverviewStripProps = {
  badgeLabel: string;
  badgeColor?: string;
  title: string;
  tags?: WorkspaceOverviewTag[];
  metrics: WorkspaceOverviewMetric[];
  children?: ReactNode;
};

const metricPalette = [
  { accent: "#0f766e", tone: "rgba(20, 184, 166, 0.08)" },
  { accent: "#1d4ed8", tone: "rgba(59, 130, 246, 0.10)" },
  { accent: "#b45309", tone: "rgba(245, 158, 11, 0.12)" },
  { accent: "#7c3aed", tone: "rgba(139, 92, 246, 0.10)" },
];

function formatMetricValue(value: number | string) {
  return typeof value === "number" ? value.toLocaleString("zh-CN") : value;
}

export function WorkspaceOverviewStrip({
  badgeLabel,
  badgeColor = "processing",
  title,
  tags = [],
  metrics,
  children,
}: WorkspaceOverviewStripProps) {
  return (
    <Card
      data-testid="workspace-overview-strip"
      variant="borderless"
      style={{
        borderRadius: 16,
        overflow: "hidden",
        background:
          "linear-gradient(135deg, rgba(244,248,255,0.96) 0%, rgba(238,247,241,0.96) 52%, rgba(255,250,240,0.96) 100%)",
        boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
      }}
      styles={{ body: { padding: "10px 14px" } }}
    >
      <Space direction="vertical" size={10} style={{ display: "flex" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "nowrap",
            overflowX: "auto",
            paddingBottom: 2,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "nowrap",
              flexShrink: 0,
              minWidth: "max-content",
            }}
          >
            <Tag
              color={badgeColor}
              style={{
                borderRadius: 9999,
                paddingInline: 10,
                lineHeight: "22px",
                marginInlineEnd: 0,
              }}
            >
              {badgeLabel}
            </Tag>
            <Typography.Title level={5} style={{ margin: 0, whiteSpace: "nowrap" }}>
              {title}
            </Typography.Title>
            {tags.map((tag) => (
              <Tag
                key={tag.label}
                color={tag.color}
                style={{ borderRadius: 9999, paddingInline: 10, lineHeight: "22px", marginInlineEnd: 0 }}
              >
                {tag.label}
              </Tag>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "nowrap",
              flexShrink: 0,
              minWidth: "max-content",
            }}
          >
            {metrics.map((metric, index) => {
              const palette = metricPalette[index % metricPalette.length];
              const accent = metric.accent ?? palette.accent;
              const tone = metric.tone ?? palette.tone;

              return (
                <div
                  key={metric.title}
                  style={{
                    borderRadius: 9999,
                    padding: "5px 10px",
                    background: tone,
                    border: "1px solid rgba(148, 163, 184, 0.16)",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <Typography.Text style={{ color: accent, fontWeight: 600, fontSize: 12, whiteSpace: "nowrap" }}>
                    {metric.title}
                  </Typography.Text>
                  <Typography.Text style={{ color: "#0f172a", fontWeight: 700, fontSize: 14, whiteSpace: "nowrap" }}>
                    {formatMetricValue(metric.value)}
                  </Typography.Text>
                </div>
              );
            })}
          </div>
        </div>
        {children}
      </Space>
    </Card>
  );
}
