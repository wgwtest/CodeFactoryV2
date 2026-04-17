import { Alert, Button, Card, Descriptions, Empty, List, Radio, Space, Spin, Tag, Typography } from "antd";

import type { MockDemandScenarioId, ToolDemandSheet } from "../../lib/api";

const SCENARIO_OPTIONS: Array<{ id: MockDemandScenarioId; label: string; description: string }> = [
  { id: "simulated_blue_force", label: "模拟蓝军", description: "围绕蓝军建模、编组、推演与复盘的典型工单。" },
  { id: "navigation_planning", label: "导航规划", description: "围绕航路规划、冲突校核与导航方案编译的典型工单。" },
  { id: "data_governance", label: "数据治理", description: "围绕对象归并、血缘核验和标准化治理的典型工单。" },
];

type P3BlueForceGeneratorProps = {
  sheets: ToolDemandSheet[];
  activeSheet: ToolDemandSheet | null;
  selectedScenarioId: MockDemandScenarioId;
  loadingSheets: boolean;
  generating: boolean;
  withdrawing: boolean;
  error: string | null;
  onGenerate: (scenarioId: MockDemandScenarioId) => Promise<void>;
  onScenarioChange: (scenarioId: MockDemandScenarioId) => void;
  onSelectSheet: (sheetId: string) => Promise<void>;
  onWithdraw: () => Promise<void>;
};

function renderLifecycleTag(status: string) {
  if (status === "accepted" || status === "submitted") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "withdrawn") {
    return <Tag color="orange">{status}</Tag>;
  }
  if (status === "rejected") {
    return <Tag color="red">{status}</Tag>;
  }
  if (status === "closed") {
    return <Tag>{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderProcessingTag(status: string) {
  if (status === "matched_existing" || status === "ready_for_fetch" || status === "ready") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "manufacturing_in_progress" || status === "processing" || status === "partially_ready") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderReviewTag(status: string) {
  if (status === "reviewed") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "reviewing") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderDeliveryTag(status: string) {
  if (status === "delivered") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "delivering") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P3BlueForceGenerator({
  sheets,
  activeSheet,
  selectedScenarioId,
  loadingSheets,
  generating,
  withdrawing,
  error,
  onGenerate,
  onScenarioChange,
  onSelectSheet,
  onWithdraw,
}: P3BlueForceGeneratorProps) {
  const selectedScenario = SCENARIO_OPTIONS.find((item) => item.id === selectedScenarioId) ?? SCENARIO_OPTIONS[0];

  return (
    <Space id="xx-p3-generator" direction="vertical" size={16} style={{ display: "flex" }}>
      <Card
        id="xx-p3-generator-card"
        style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.08)" }}
      >
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <div id="xx-p3-generator-header">
            <Typography.Title level={3} style={{ margin: 0 }}>
              典型工单发生器
            </Typography.Title>
            <Typography.Paragraph style={{ margin: "8px 0 0", color: "#475569" }}>
              这里模拟 P3 把 `工具需求单` 交给 P4。当前可从多个典型业务方向选择一种场景发起工单。
            </Typography.Paragraph>
          </div>

          {error ? <Alert id="xx-p3-generator-error" type="error" showIcon message={error} /> : null}

          <div id="xx-p3-scenario-selector-shell">
            <Typography.Text strong>选择典型场景</Typography.Text>
            <Radio.Group
              id="xx-p3-scenario-selector"
              aria-label="典型工单场景"
              value={selectedScenarioId}
              onChange={(event) => onScenarioChange(event.target.value as MockDemandScenarioId)}
              style={{ display: "block", marginTop: 10 }}
            >
              <Space wrap size={12}>
                {SCENARIO_OPTIONS.map((option) => (
                  <Radio id={`xx-p3-scenario-${option.id}`} key={option.id} value={option.id}>
                    {option.label}
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
            <Typography.Paragraph id="xx-p3-scenario-description" style={{ margin: "10px 0 0", color: "#475569" }}>
              {selectedScenario.description}
            </Typography.Paragraph>
          </div>

          <Button
            id="xx-p3-generate-button"
            type="primary"
            size="large"
            loading={generating}
            onClick={() => void onGenerate(selectedScenarioId)}
          >
            生成模拟工单
          </Button>

          {activeSheet &&
          activeSheet.lifecycle_status !== "withdrawn" &&
          activeSheet.lifecycle_status !== "rejected" ? (
            <Button
              id="xx-p3-withdraw-button"
              size="large"
              loading={withdrawing}
              onClick={() => void onWithdraw()}
            >
              撤销当前工单
            </Button>
          ) : null}
        </Space>
      </Card>

      <Card
        id="xx-p3-sheet-list-card"
        title="已生成工单"
        style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.08)" }}
      >
        <div id="xx-p3-sheet-list">
          {loadingSheets ? (
            <div id="xx-p3-sheet-list-loading" style={{ padding: "12px 0", textAlign: "center" }}>
              <Spin />
            </div>
          ) : sheets.length === 0 ? (
            <Empty description="当前没有已生成工单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              size="small"
              dataSource={sheets}
              renderItem={(sheet) => {
                const selected = sheet.sheet_id === activeSheet?.sheet_id;
                return (
                  <List.Item key={sheet.sheet_id}>
                    <Space
                      align="center"
                      style={{ display: "flex", justifyContent: "space-between", width: "100%" }}
                      wrap
                    >
                      <Space direction="vertical" size={2} style={{ display: "flex" }}>
                        <Typography.Text strong>{`工单：${sheet.sheet_name}`}</Typography.Text>
                        <Typography.Text type="secondary">{`工单 ID：${sheet.sheet_id}`}</Typography.Text>
                      </Space>
                      <Space align="center" wrap>
                        {renderLifecycleTag(sheet.lifecycle_status)}
                        {renderReviewTag(sheet.review_status)}
                        {renderDeliveryTag(sheet.delivery_status)}
                        {renderProcessingTag(sheet.processing_status)}
                        <Button
                          id={`xx-p3-view-sheet-${sheet.sheet_id}`}
                          type={selected ? "primary" : "default"}
                          onClick={() => void onSelectSheet(sheet.sheet_id)}
                        >
                          查看工单 {sheet.sheet_id}
                        </Button>
                      </Space>
                    </Space>
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      </Card>

      {activeSheet ? (
        <Card
          id="xx-p3-selected-sheet-card"
          title="当前选中工单"
          style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.08)" }}
        >
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Space align="center" wrap>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {activeSheet.sheet_name}
              </Typography.Title>
              {renderLifecycleTag(activeSheet.lifecycle_status)}
              {renderReviewTag(activeSheet.review_status)}
              {renderDeliveryTag(activeSheet.delivery_status)}
              {renderProcessingTag(activeSheet.processing_status)}
            </Space>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="sheet_id">{activeSheet.sheet_id}</Descriptions.Item>
              <Descriptions.Item label="业务案例">{activeSheet.business_case}</Descriptions.Item>
              <Descriptions.Item label="生命周期状态">{`状态码 ${activeSheet.lifecycle_status}`}</Descriptions.Item>
              <Descriptions.Item label="审定状态">{activeSheet.review_status}</Descriptions.Item>
              <Descriptions.Item label="交付状态">{activeSheet.delivery_status}</Descriptions.Item>
              <Descriptions.Item label="处理进度状态">{`状态码 ${activeSheet.processing_status}`}</Descriptions.Item>
              <Descriptions.Item label="叶子项数量">{activeSheet.item_count}</Descriptions.Item>
              <Descriptions.Item label="请求方">{activeSheet.requested_by}</Descriptions.Item>
              <Descriptions.Item label="终态原因码">{activeSheet.terminal_reason_code ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="终态原因说明">{activeSheet.terminal_reason_message ?? "-"}</Descriptions.Item>
            </Descriptions>

            <List
              id="xx-p3-generated-items"
              bordered
              size="small"
              dataSource={activeSheet.items ?? []}
              locale={{ emptyText: "当前总单暂无叶子项" }}
              renderItem={(item) => (
                <List.Item key={item.item_id}>
                  <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                    <Space align="center" wrap>
                      <Typography.Text strong>{item.component_name}</Typography.Text>
                      <Tag color="gold">{item.review_status}</Tag>
                      {renderProcessingTag(item.processing_status)}
                    </Space>
                    <Typography.Text type="secondary">{item.item_id}</Typography.Text>
                    <Typography.Text style={{ color: "#475569" }}>{item.recommendation_summary}</Typography.Text>
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
