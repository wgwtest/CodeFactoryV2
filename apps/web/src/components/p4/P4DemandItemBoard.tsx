import { Button, Card, Empty, Space, Tag, Typography } from "antd";

import type { ToolDemandItem } from "../../lib/api";

type P4DemandItemBoardProps = {
  items: ToolDemandItem[];
  selectedItemId: string | null;
  refreshingItemId: string | null;
  onSelectItem: (itemId: string) => void;
  onRefreshProgress: (itemId: string) => Promise<void>;
};

function renderStatusTag(status: string) {
  if (status === "matched_existing" || status === "ready_for_fetch") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "manufacturing_in_progress") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P4DemandItemBoard({
  items,
  selectedItemId,
  refreshingItemId,
  onSelectItem,
  onRefreshProgress,
}: P4DemandItemBoardProps) {
  if (items.length === 0) {
    return (
      <div id="xx-p4-demand-item-empty">
        <Empty description="当前总单暂无叶子项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <Space id="xx-p4-demand-item-board" direction="vertical" size={12} style={{ display: "flex" }}>
      {items.map((item) => {
        const selected = item.item_id === selectedItemId;
        return (
          <Card
            key={item.item_id}
            id={`xx-p4-demand-item-${item.item_id}`}
            size="small"
            hoverable
            onClick={() => onSelectItem(item.item_id)}
            style={{
              borderRadius: 16,
              background: selected ? "#eef4ff" : "#ffffff",
              borderColor: selected ? "#1f6feb" : "#d0d7de",
            }}
          >
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Space align="center" wrap>
                <Typography.Text strong>{item.component_name}</Typography.Text>
                {renderStatusTag(item.status)}
              </Space>

              <Typography.Text type="secondary">{item.ancestry.join(" / ")}</Typography.Text>
              <Typography.Text>{item.match_result}</Typography.Text>

              <Space wrap>
                <Button size="small" onClick={() => onSelectItem(item.item_id)}>
                  查看供给
                </Button>
                {item.supply_result.progress_query_path ? (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    loading={refreshingItemId === item.item_id}
                    onClick={() => void onRefreshProgress(item.item_id)}
                  >
                    刷新进度
                  </Button>
                ) : null}
              </Space>
            </Space>
          </Card>
        );
      })}
    </Space>
  );
}
