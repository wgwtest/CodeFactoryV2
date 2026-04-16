import { Descriptions, Empty, Space, Tag, Typography } from "antd";

import type { ToolDemandItem } from "../../lib/api";

type P4SupplyResultPreviewProps = {
  item: ToolDemandItem | null;
};

function renderResultTag(resultType: string) {
  if (resultType === "existing_tool" || resultType === "manufactured_tool") {
    return <Tag color="green">{resultType}</Tag>;
  }
  return <Tag color="gold">{resultType}</Tag>;
}

export function P4SupplyResultPreview({ item }: P4SupplyResultPreviewProps) {
  if (!item) {
    return (
      <div id="xx-p4-supply-preview-empty">
        <Empty description="请选择一个叶子项查看供给结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <Space id="xx-p4-supply-preview" direction="vertical" size={16} style={{ display: "flex" }}>
      <Space align="center" wrap>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {item.component_name}
        </Typography.Title>
        {renderResultTag(item.supply_result.result_type)}
      </Space>

      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="叶子项">{item.item_id}</Descriptions.Item>
        <Descriptions.Item label="状态">{item.status}</Descriptions.Item>
        <Descriptions.Item label="供给结论" span={2}>
          {item.supply_result.summary}
        </Descriptions.Item>
        <Descriptions.Item label="获取接口">
          {item.supply_result.fetch_manifest?.fetch_path ?? "当前暂无可获取工具"}
        </Descriptions.Item>
        <Descriptions.Item label="进度查询接口">
          {item.supply_result.progress_query_path ?? "当前无需查询"}
        </Descriptions.Item>
        <Descriptions.Item label="预计完成时间">
          {item.supply_result.estimated_ready_at ?? "当前未给出"}
        </Descriptions.Item>
        <Descriptions.Item label="预计剩余小时">
          {item.supply_result.estimated_ready_in_hours ?? "-"}
        </Descriptions.Item>
      </Descriptions>

      <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>{item.analysis_result}</Typography.Paragraph>
      <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>{item.check_result}</Typography.Paragraph>
    </Space>
  );
}
