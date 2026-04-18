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
        title={matrix.title}
        className="xx-p4-panel-card"
        extra={
          <Typography.Text type="secondary">
            {matrix.y_axis_label} × {matrix.x_axis_label}
          </Typography.Text>
        }
      >
        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `180px repeat(${matrix.columns.length}, minmax(48px, 1fr))`,
              gap: 8,
              alignItems: "center",
            }}
          >
            <div />
            {matrix.columns.map((column) => (
              <Typography.Text
                key={column.id}
                style={{ fontSize: 12, textAlign: "center", color: "#475569", fontWeight: 600 }}
              >
                {column.label}
              </Typography.Text>
            ))}

            {matrix.rows.map((row) => (
              <div
                key={row.row_id}
                style={{ display: "contents" }}
              >
                <Typography.Text key={`${row.row_id}-label`} style={{ color: "#0f172a", fontWeight: 600 }}>
                  {row.row_label}
                </Typography.Text>
                {row.cells.map((cell) => (
                  <div
                    key={`${row.row_id}-${cell.column_id}`}
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
                    title={`${row.row_label} / ${cell.column_id}: ${cell.value}`}
                  >
                    {cell.value}
                  </div>
                ))}
              </div>
            ))}
          </div>

          <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
            颜色越深，表示该业务域在对应工具形态上的活跃工具越密。空白区表示当前仍无激活工具覆盖。
          </Typography.Paragraph>
        </Space>
      </Card>
    </div>
  );
}
