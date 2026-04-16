import { Card, Space, Typography } from "antd";

import type { ToolHubCoverageMatrix } from "../../lib/api";

type P4CoverageMatrixProps = {
  id?: string;
  matrix: ToolHubCoverageMatrix;
};

function resolveCellColor(value: number) {
  if (value <= 0) {
    return "#e2e8f0";
  }
  if (value === 1) {
    return "#bfdbfe";
  }
  if (value === 2) {
    return "#60a5fa";
  }
  return "#1d4ed8";
}

export function P4CoverageMatrix({ id, matrix }: P4CoverageMatrixProps) {
  return (
    <div id={id}>
      <Card
        title="覆盖热力矩阵"
        extra={<Typography.Text type="secondary">阶段 × 工具分类</Typography.Text>}
        style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}
      >
        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `180px repeat(${matrix.stages.length}, minmax(48px, 1fr))`,
              gap: 8,
              alignItems: "center",
            }}
          >
            <div />
            {matrix.stages.map((stage) => (
              <Typography.Text
                key={stage.id}
                style={{ fontSize: 12, textAlign: "center", color: "#475569", fontWeight: 600 }}
              >
                {stage.label}
              </Typography.Text>
            ))}

            {matrix.rows.map((row) => (
              <div
                key={row.category_id}
                style={{ display: "contents" }}
              >
                <Typography.Text key={`${row.category_id}-label`} style={{ color: "#0f172a", fontWeight: 600 }}>
                  {row.category_label}
                </Typography.Text>
                {row.cells.map((cell) => (
                  <div
                    key={`${row.category_id}-${cell.stage_id}`}
                    style={{
                      height: 40,
                      borderRadius: 12,
                      background: resolveCellColor(cell.value),
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: cell.value > 1 ? "#f8fafc" : "#0f172a",
                      fontWeight: 700,
                    }}
                    title={`${row.category_label} / ${cell.stage_id}: ${cell.value}`}
                  >
                    {cell.value}
                  </div>
                ))}
              </div>
            ))}
          </div>

          <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
            颜色越深，表示该分类在对应阶段的工具覆盖越密。空白区表示当前仍无激活工具覆盖。
          </Typography.Paragraph>
        </Space>
      </Card>
    </div>
  );
}
