import { useState } from "react";
import { Alert, Card, Space, Typography } from "antd";

import { P3BlueForceGenerator } from "../components/p3/P3BlueForceGenerator";
import type { ToolDemandSheet } from "../lib/api";
import { createMockBlueForceDemandSheet } from "../lib/toolHub";

export function XXP3SimPage() {
  const [sheet, setSheet] = useState<ToolDemandSheet | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    try {
      setGenerating(true);
      setError(null);
      const response = await createMockBlueForceDemandSheet();
      setSheet(response.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "生成模拟蓝军需求总单失败");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div id="xx-p3-page" style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div id="xx-p3-shell" style={{ maxWidth: 1200, margin: "0 auto" }}>
        <Card
          id="xx-p3-hero"
          style={{
            borderRadius: 24,
            border: "1px solid #d0d7de",
            background: "linear-gradient(180deg, #ffffff 0%, #f6f8fa 100%)",
            boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
            marginBottom: 20,
          }}
        >
          <Space direction="vertical" size={8} style={{ display: "flex" }}>
            <Typography.Title level={2} style={{ margin: 0 }}>
              P3 模拟发生器
            </Typography.Title>
            <Typography.Paragraph style={{ margin: 0, color: "#57606a", maxWidth: 760 }}>
              独立模拟 P3 阶段生成 `工具需求单` 的入口页。它不展示 P4 内部处理细节，只负责把标准输入对象发出去。
            </Typography.Paragraph>
          </Space>
        </Card>

        {error ? (
          <Alert id="xx-p3-page-error" type="error" showIcon message={error} style={{ marginBottom: 16 }} />
        ) : null}

        <P3BlueForceGenerator generating={generating} sheet={sheet} error={error} onGenerate={handleGenerate} />
      </div>
    </div>
  );
}
