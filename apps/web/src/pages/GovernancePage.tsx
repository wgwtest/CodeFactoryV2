import { Button, Card, Typography } from "antd";

import { CandidateReviewTable } from "../components/CandidateReviewTable";

export function GovernancePage() {
  return (
    <Card>
      <Typography.Title level={3}>Candidate Review Queue</Typography.Title>
      <CandidateReviewTable />
      <Button type="primary">Publish Version</Button>
    </Card>
  );
}
