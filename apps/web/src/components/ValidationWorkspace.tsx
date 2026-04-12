import type { ReactNode } from "react";
import { Card, Col, Row, Space, Statistic, Typography } from "antd";

export type ValidationWorkspaceStat = {
  title: string;
  value: number | string;
};

type ValidationWorkspaceProps = {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  stats?: ValidationWorkspaceStat[];
  children: ReactNode;
};

export function ValidationWorkspace({
  title,
  description,
  actions,
  stats = [],
  children,
}: ValidationWorkspaceProps) {
  return (
    <Card>
      <Space direction="vertical" size={24} style={{ display: "flex" }}>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 280 }}>
            <Typography.Title level={3}>{title}</Typography.Title>
            {description ? <Typography.Paragraph>{description}</Typography.Paragraph> : null}
          </div>
          {actions ? <div>{actions}</div> : null}
        </div>

        {stats.length > 0 ? (
          <Row gutter={16}>
            {stats.map((stat) => (
              <Col key={stat.title}>
                <Statistic title={stat.title} value={stat.value} />
              </Col>
            ))}
          </Row>
        ) : null}

        {children}
      </Space>
    </Card>
  );
}
