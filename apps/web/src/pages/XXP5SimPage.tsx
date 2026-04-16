import { Card, Space, Typography } from "antd";

import { P5DemandQueryPanel } from "../components/p5/P5DemandQueryPanel";

export function XXP5SimPage() {
  return (
    <div id="xx-p5-page" style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div id="xx-p5-shell" style={{ maxWidth: 1200, margin: "0 auto" }}>
        <Card
          id="xx-p5-hero"
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
              P5 模拟消费器
            </Typography.Title>
            <Typography.Paragraph style={{ margin: 0, color: "#57606a", maxWidth: 760 }}>
              独立模拟 P5 消费 P4 输出的入口页。这里不修改 P4 内部状态，只做整单查询、叶子项查询和进度决策验证。
            </Typography.Paragraph>
          </Space>
        </Card>

        <P5DemandQueryPanel />
      </div>
    </div>
  );
}
