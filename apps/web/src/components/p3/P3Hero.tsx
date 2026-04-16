import { Col, Row, Statistic, Typography } from "antd";

import type { SoftwareDesignOverview } from "../../lib/api";

export function P3Hero({ overview }: { overview: SoftwareDesignOverview }) {
  return (
    <div>
      <Typography.Title level={1} style={{ margin: 0, color: "#ffffff" }}>
        XX-P3
      </Typography.Title>
      <Typography.Paragraph style={{ margin: "8px 0 0", color: "rgba(255,255,255,0.82)", fontSize: 16 }}>
        软件设计编制与模块工单下发系统
      </Typography.Paragraph>
      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={12} md={6}>
          <Statistic title="订单数" value={overview.metrics.order_count} valueStyle={{ color: "#ffffff" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="待审批" value={overview.metrics.pending_approval_count} valueStyle={{ color: "#ffffff" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="已冻结" value={overview.metrics.frozen_count} valueStyle={{ color: "#ffffff" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="待推送" value={overview.metrics.package_ready_count} valueStyle={{ color: "#ffffff" }} />
        </Col>
      </Row>
    </div>
  );
}
