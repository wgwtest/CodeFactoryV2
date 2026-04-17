import { Button, Card, Empty, Segmented, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import type { ToolDemandItem } from "../../lib/api";

type P4DemandItemBoardProps = {
  items: ToolDemandItem[];
  selectedItemId: string | null;
  refreshingItemId: string | null;
  onSelectItem: (itemId: string) => void;
  onRefreshProgress: (itemId: string) => Promise<void>;
};

type ItemFilter = "all" | "pending_review" | "approved_delivery" | "approved_manufacture" | "rejected";

function renderReviewTag(status: string) {
  if (status === "approved_delivery") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "approved_manufacture") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "rejected") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderRecommendationTag(type: string) {
  if (type === "existing_tool") {
    return <Tag color="cyan">{type}</Tag>;
  }
  if (type === "manufacture_candidate") {
    return <Tag color="orange">{type}</Tag>;
  }
  return <Tag>{type}</Tag>;
}

export function P4DemandItemBoard({
  items,
  selectedItemId,
  refreshingItemId,
  onSelectItem,
  onRefreshProgress,
}: P4DemandItemBoardProps) {
  const [filter, setFilter] = useState<ItemFilter>("all");

  const filteredItems = useMemo(() => {
    const sorted = [...items].sort((left, right) => {
      if (left.review_status === "pending_review" && right.review_status !== "pending_review") {
        return -1;
      }
      if (left.review_status !== "pending_review" && right.review_status === "pending_review") {
        return 1;
      }
      return right.updated_at.localeCompare(left.updated_at);
    });
    if (filter === "all") {
      return sorted;
    }
    return sorted.filter((item) => item.review_status === filter);
  }, [filter, items]);

  if (items.length === 0) {
    return (
      <div id="xx-p4-demand-item-empty">
        <Empty description="当前总单暂无工具需求项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <Space id="xx-p4-demand-item-board" direction="vertical" size={12} style={{ display: "flex" }}>
      <Segmented
        id="xx-p4-demand-item-filter"
        value={filter}
        onChange={(value) => setFilter(value as ItemFilter)}
        options={[
          { label: "全部", value: "all" },
          { label: "待审定", value: "pending_review" },
          { label: "直接交付", value: "approved_delivery" },
          { label: "进入研制", value: "approved_manufacture" },
          { label: "已驳回", value: "rejected" },
        ]}
      />

      {filteredItems.length === 0 ? (
        <Empty description="当前筛选条件下没有工具需求项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        filteredItems.map((item) => {
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
                  {renderReviewTag(item.review_status)}
                  {renderRecommendationTag(item.recommendation_type)}
                </Space>

                <Typography.Text type="secondary">{item.ancestry.join(" / ")}</Typography.Text>
                <Typography.Text>{item.recommendation_summary}</Typography.Text>

                <Space wrap>
                  <Button size="small" onClick={() => onSelectItem(item.item_id)}>
                    审定与处置
                  </Button>
                  {item.supply_result?.progress_query_interface ? (
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
        })
      )}
    </Space>
  );
}
