import { Button, Card, Empty, List, Space, Tag, Typography } from "antd";

import type { RequirementSpecSummary } from "../../lib/api";

type P3RequirementIntakePanelProps = {
  specs: RequirementSpecSummary[];
  acceptedRequirementSpecIds: string[];
  onCreateOrder: (specId: string) => void | Promise<void>;
};

export function P3RequirementIntakePanel({
  specs,
  acceptedRequirementSpecIds,
  onCreateOrder,
}: P3RequirementIntakePanelProps) {
  const acceptedSpecIds = new Set(acceptedRequirementSpecIds);

  return (
    <Card title="待受理需求规格" style={{ borderRadius: 18 }}>
      {specs.length === 0 ? (
        <Empty description="当前没有可受理虚规" />
      ) : (
        <List
          dataSource={specs}
          renderItem={(spec) => {
            const alreadyAccepted = acceptedSpecIds.has(spec.id);
            return (
              <List.Item
                key={spec.id}
                actions={[
                  <Button
                    key="create-order"
                    type="primary"
                    size="small"
                    disabled={spec.status !== "ready" || alreadyAccepted}
                    onClick={() => void onCreateOrder(spec.id)}
                  >
                    接收为P3订单
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space wrap>
                      <Typography.Text strong>{spec.application_name}</Typography.Text>
                      <Tag color={alreadyAccepted ? "blue" : spec.status === "ready" ? "green" : "default"}>
                        {alreadyAccepted ? "已受理" : spec.status}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Typography.Text type="secondary">
                      领域: {spec.domain_name} · 对象 {spec.object_count} · 流程 {spec.process_count}
                    </Typography.Text>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </Card>
  );
}
