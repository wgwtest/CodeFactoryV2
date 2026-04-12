import { List, Space, Typography } from "antd";

import type { ArchiveKnowledgeEvidence } from "../lib/api";

type EvidenceListProps = {
  title?: string;
  items: ArchiveKnowledgeEvidence[];
  emptyText?: string;
  bordered?: boolean;
  size?: "small" | "default" | "large";
};

export function EvidenceList({
  title,
  items,
  emptyText = "暂无证据摘录",
  bordered = true,
  size = "default",
}: EvidenceListProps) {
  return (
    <div>
      {title ? <Typography.Title level={5}>{title}</Typography.Title> : null}
      <List
        bordered={bordered}
        size={size}
        dataSource={items}
        locale={{ emptyText }}
        renderItem={(item) => (
          <List.Item>
            <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
              <Typography.Text>{item.excerpt || "无摘录"}</Typography.Text>
              {item.document_title ? <Typography.Text type="secondary">{item.document_title}</Typography.Text> : null}
            </Space>
          </List.Item>
        )}
      />
    </div>
  );
}
