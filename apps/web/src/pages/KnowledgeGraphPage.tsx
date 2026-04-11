import { Card, Typography } from "antd";

import { KnowledgeGraph } from "../components/KnowledgeGraph";

export function KnowledgeGraphPage() {
  return (
    <Card>
      <Typography.Title level={3}>Knowledge Graph</Typography.Title>
      <KnowledgeGraph />
    </Card>
  );
}
