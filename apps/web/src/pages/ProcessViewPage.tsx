import { Card, Typography } from "antd";

import { ProcessFlow } from "../components/ProcessFlow";

export function ProcessViewPage() {
  return (
    <Card>
      <Typography.Title level={3}>Process View</Typography.Title>
      <Typography.Paragraph>
        Inspect process-oriented knowledge as ordered steps that can later feed construct mapping and generated applications.
      </Typography.Paragraph>
      <ProcessFlow />
    </Card>
  );
}
