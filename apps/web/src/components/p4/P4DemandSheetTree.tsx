import { Empty, Space, Tag, Tree, Typography } from "antd";
import type { DataNode } from "antd/es/tree";

import type { ToolDemandNode, ToolDemandSheet } from "../../lib/api";

type P4DemandSheetTreeProps = {
  sheet: ToolDemandSheet | null;
  selectedItemId: string | null;
  onSelectItem: (itemId: string) => void;
};

function renderStatusTag(status: string) {
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

export function P4DemandSheetTree({ sheet, selectedItemId, onSelectItem }: P4DemandSheetTreeProps) {
  if (!sheet) {
    return (
      <div id="xx-p4-demand-tree-empty">
        <Empty description="还没有工具需求单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  const itemBySourceNodeId = new Map((sheet.items ?? []).map((item) => [item.source_node_id, item]));

  function buildTreeNode(node: ToolDemandNode): DataNode {
    const relatedItem = itemBySourceNodeId.get(node.node_id);
    const key = relatedItem?.item_id ?? node.node_id;
    return {
      key,
      title: (
        <Space size={8} wrap>
          <Typography.Text>{node.node_name}</Typography.Text>
          {relatedItem ? renderStatusTag(relatedItem.review_status) : null}
        </Space>
      ),
      children: node.children.map(buildTreeNode),
    };
  }

  const treeData = [buildTreeNode(sheet.root_node)];
  const selectableKeys = new Set((sheet.items ?? []).map((item) => item.item_id));

  return (
    <Space id="xx-p4-demand-tree" direction="vertical" size={12} style={{ display: "flex" }}>
      <Typography.Text type="secondary">
        当前总单：{sheet.sheet_name} · {sheet.item_count} 个叶子项
      </Typography.Text>
      <div id="xx-p4-demand-tree-control">
        <Tree
          defaultExpandAll
          selectedKeys={selectedItemId ? [selectedItemId] : []}
          treeData={treeData}
          onSelect={(keys) => {
            const nextKey = String(keys[0] ?? "");
            if (selectableKeys.has(nextKey)) {
              onSelectItem(nextKey);
            }
          }}
        />
      </div>
    </Space>
  );
}
