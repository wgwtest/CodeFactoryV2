import { Button, Card, Typography } from "antd";

import { CandidateReviewTable } from "../components/CandidateReviewTable";

export function GovernancePage() {
  return (
    <Card>
      <Typography.Title level={3}>Candidate Review Queue</Typography.Title>
      <Typography.Paragraph>
        Review extracted entities, events, and processes before they are promoted into a published knowledge version.
      </Typography.Paragraph>
      <CandidateReviewTable />
      <Button type="primary">Publish Version</Button>
    </Card>
  );
}
