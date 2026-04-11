import { Card, Typography } from "antd";

import { KnowledgeGraph } from "../components/KnowledgeGraph";

export function KnowledgeGraphPage() {
  return (
    <Card>
      <Typography.Title level={3}>Knowledge Graph</Typography.Title>
      <Typography.Paragraph>
        Explore published domain entities and their relations for a selected knowledge version.
      </Typography.Paragraph>
      <KnowledgeGraph />
    </Card>
  );
}
