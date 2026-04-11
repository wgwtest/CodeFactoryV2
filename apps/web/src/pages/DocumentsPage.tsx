import { Card, Table, Typography } from "antd";

import { DocumentUploadForm } from "../components/DocumentUploadForm";

export function DocumentsPage() {
  return (
    <Card>
      <Typography.Title level={3}>Upload Source Document</Typography.Title>
      <Typography.Paragraph>
        Ingest source policies, manuals, or procedure files to create traceable document versions for parsing and extraction.
      </Typography.Paragraph>
      <DocumentUploadForm />
      <Typography.Title level={4}>Document Versions</Typography.Title>
      <Typography.Paragraph type="secondary">
        Uploaded versions become the source of evidence segments, candidate knowledge, and later publishable graph/process views.
      </Typography.Paragraph>
      <Table dataSource={[]} columns={[{ title: "Version", dataIndex: "version_number" }]} rowKey="version_number" />
    </Card>
  );
}
