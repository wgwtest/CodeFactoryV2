import { Card, Typography } from "antd";

import { ProcessFlow } from "../components/ProcessFlow";

export function ProcessViewPage() {
  return (
    <Card>
      <Typography.Title level={3}>Process View</Typography.Title>
      <ProcessFlow />
    </Card>
  );
}
