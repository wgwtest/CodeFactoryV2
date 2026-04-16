import { Alert, Button, Card, Descriptions, List, Space, Tag, Typography } from "antd";

import type { ToolDemandSheet } from "../../lib/api";

type P3BlueForceGeneratorProps = {
  generating: boolean;
  sheet: ToolDemandSheet | null;
  error: string | null;
  onGenerate: () => Promise<void>;
};

function renderStatusTag(status: string) {
  if (status === "ready") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "processing" || status === "partially_ready") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P3BlueForceGenerator({ generating, sheet, error, onGenerate }: P3BlueForceGeneratorProps) {
  return (
    <Space id="xx-p3-generator" direction="vertical" size={16} style={{ display: "flex" }}>
      <Card
        id="xx-p3-generator-card"
        style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.08)" }}
      >
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <div id="xx-p3-generator-header">
            <Typography.Title level={3} style={{ margin: 0 }}>
              模拟蓝军需求发生器
            </Typography.Title>
            <Typography.Paragraph style={{ margin: "8px 0 0", color: "#475569" }}>
              这里模拟 P3 把 `工具需求单` 交给 P4。当前只生成固定的“模拟蓝军一期工具需求单”，用于闭环验证。
            </Typography.Paragraph>
          </div>

          {error ? <Alert id="xx-p3-generator-error" type="error" showIcon message={error} /> : null}

          <Button
            id="xx-p3-generate-button"
            type="primary"
            size="large"
            loading={generating}
            onClick={() => void onGenerate()}
          >
            生成模拟蓝军需求总单
          </Button>
        </Space>
      </Card>

      {sheet ? (
        <Card
          id="xx-p3-generated-sheet"
          title="最近生成结果"
          style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.08)" }}
        >
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Space align="center" wrap>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {sheet.sheet_name}
              </Typography.Title>
              {renderStatusTag(sheet.status)}
            </Space>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="sheet_id">{sheet.sheet_id}</Descriptions.Item>
              <Descriptions.Item label="业务案例">{sheet.business_case}</Descriptions.Item>
              <Descriptions.Item label="叶子项数量">{sheet.item_count}</Descriptions.Item>
              <Descriptions.Item label="请求方">{sheet.requested_by}</Descriptions.Item>
            </Descriptions>

            <List
              id="xx-p3-generated-items"
              bordered
              size="small"
              dataSource={sheet.items ?? []}
              locale={{ emptyText: "当前总单暂无叶子项" }}
              renderItem={(item) => (
                <List.Item key={item.item_id}>
                  <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                    <Space align="center" wrap>
                      <Typography.Text strong>{item.component_name}</Typography.Text>
                      {renderStatusTag(item.status)}
                    </Space>
                    <Typography.Text type="secondary">{item.item_id}</Typography.Text>
                    <Typography.Text style={{ color: "#475569" }}>{item.match_result}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Space>
        </Card>
      ) : null}
    </Space>
  );
}
