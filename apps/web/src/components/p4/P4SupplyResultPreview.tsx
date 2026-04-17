import { Descriptions, Empty, Space, Tag, Typography } from "antd";

import type { ToolDemandItem } from "../../lib/api";

type P4SupplyResultPreviewProps = {
  item: ToolDemandItem | null;
};

function renderResultTag(resultType: string | undefined) {
  if (resultType === "existing_tool" || resultType === "manufactured_tool") {
    return <Tag color="green">{resultType}</Tag>;
  }
  if (resultType === "pending_manufacture") {
    return <Tag color="blue">{resultType}</Tag>;
  }
  return <Tag color="gold">pending_decision</Tag>;
}

export function P4SupplyResultPreview({ item }: P4SupplyResultPreviewProps) {
  if (!item) {
    return (
      <div id="xx-p4-supply-preview-empty">
        <Empty description="请选择一个需求项查看供给与交付结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  const supplyResult = item.supply_result ?? null;

  return (
    <Space id="xx-p4-supply-preview" direction="vertical" size={16} style={{ display: "flex" }}>
      <Space align="center" wrap>
        <Typography.Title level={5} style={{ margin: 0 }}>
          {item.component_name}
        </Typography.Title>
        {renderResultTag(supplyResult?.result_type)}
      </Space>

      <Descriptions id="xx-p4-review-supply-result" bordered size="small" column={2}>
        <Descriptions.Item label="审定状态">{item.review_status}</Descriptions.Item>
        <Descriptions.Item label="供给结果">{supplyResult?.result_type ?? "待审定后生成正式供给结果"}</Descriptions.Item>
        <Descriptions.Item label="结论说明" span={2}>
          {supplyResult?.last_message ?? item.recommendation_summary}
        </Descriptions.Item>
        <Descriptions.Item label="获取接口">
          {supplyResult?.fetch_interface?.entrypoint_locator ?? "当前暂无正式获取接口"}
        </Descriptions.Item>
        <Descriptions.Item label="进度查询接口">
          {supplyResult?.progress_query_interface ?? "当前无需查询"}
        </Descriptions.Item>
        <Descriptions.Item label="预计完成时间">
          {supplyResult?.estimated_ready_at ?? "当前未给出"}
        </Descriptions.Item>
        <Descriptions.Item label="建议轮询秒数">
          {supplyResult?.suggested_poll_after_seconds ?? "-"}
        </Descriptions.Item>
      </Descriptions>

      <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>{item.analysis_result}</Typography.Paragraph>
      <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>{item.check_result}</Typography.Paragraph>
    </Space>
  );
}
