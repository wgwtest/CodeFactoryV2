import { Alert, Button, Card, Empty, List, Space, Statistic, Tag } from "antd";

import type { EvolutionRun } from "../../lib/api";

type P4EvolutionWorkspaceProps = {
  runs: EvolutionRun[];
  latestRun: EvolutionRun | null;
  running: boolean;
  onRun: () => Promise<void>;
};

export function P4EvolutionWorkspace({ runs, latestRun, running, onRun }: P4EvolutionWorkspaceProps) {
  const activeRun = latestRun ?? runs[0] ?? null;

  return (
    <Space direction="vertical" size={16} style={{ display: "flex" }}>
      <Card
        title="自演进巡检"
        extra={
          <Button type="primary" onClick={() => void onRun()} loading={running}>
            触发巡检
          </Button>
        }
        style={{ borderRadius: 18 }}
      >
        {activeRun ? (
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Space wrap size={16}>
              <Statistic title="工具数" value={activeRun.summary.tool_count} />
              <Statistic title="发现项" value={activeRun.summary.finding_count} />
              <Statistic title="重叠风险" value={activeRun.summary.overlap_risk_count} />
              <Statistic title="覆盖空白" value={activeRun.summary.coverage_gap_count} />
            </Space>
            <Alert
              type="info"
              showIcon
              message={`最近巡检：${activeRun.created_at}`}
              description="巡检关注描述缺失、域模型完整性、工具重叠与业务域覆盖空白。"
            />
            <List
              dataSource={activeRun.findings}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta title={item.title} description={item.description} />
                  <Tag color={item.severity === "critical" ? "red" : item.severity === "warning" ? "gold" : "blue"}>
                    {item.kind}
                  </Tag>
                </List.Item>
              )}
            />
          </Space>
        ) : (
          <Empty description="暂无巡检记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </Space>
  );
}
