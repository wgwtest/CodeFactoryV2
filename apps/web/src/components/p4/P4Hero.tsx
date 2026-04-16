import { Space, Tag, Typography } from "antd";

import type { ToolHubOverview } from "../../lib/api";

type P4HeroProps = {
  overview: ToolHubOverview;
  archiveName?: string | null;
};

export function P4Hero({ overview, archiveName }: P4HeroProps) {
  return (
    <div
      id="xx-p4-hero"
      style={{
        padding: "24px 28px 22px",
        color: "#0f172a",
        display: "flex",
        justifyContent: "space-between",
        gap: 24,
        flexWrap: "wrap",
      }}
    >
      <div style={{ maxWidth: 760 }}>
        <Typography.Title
          id="xx-p4-hero-title"
          level={1}
          style={{
            color: "#0f172a",
            marginBottom: 6,
            fontSize: 32,
            letterSpacing: "-0.03em",
          }}
        >
          XX-P4
        </Typography.Title>
        <Typography.Text style={{ color: "#57606a", fontSize: 15 }}>
          工具中台 / Tool Hub
        </Typography.Text>
        <Typography.Paragraph
          style={{
            color: "#57606a",
            maxWidth: 720,
            marginTop: 14,
            marginBottom: 0,
            fontSize: 15,
          }}
        >
          面向工具资产、输入工具链和自演进巡检的独立驾驶舱。当前版本聚焦 P4 第一批最小闭环，强调覆盖、
          健康度、命中解释和待演进建议。
        </Typography.Paragraph>
      </div>

      <Space id="xx-p4-hero-context" direction="vertical" size={10} style={{ minWidth: 260 }}>
        <Tag color="blue" style={{ padding: "6px 10px", borderRadius: 999, marginInlineEnd: 0 }}>
          当前知识库：{archiveName ?? "未选择"}
        </Tag>
        <Tag color="gold" style={{ padding: "6px 10px", borderRadius: 999, marginInlineEnd: 0 }}>
          待演进建议：{overview.metrics.pending_suggestion_count}
        </Tag>
        <Tag color="geekblue" style={{ padding: "6px 10px", borderRadius: 999, marginInlineEnd: 0 }}>
          最近成功率：{overview.metrics.recent_success_rate}%
        </Tag>
      </Space>
    </div>
  );
}
