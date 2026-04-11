import { Card, Table, Typography } from "antd";

import { DocumentUploadForm } from "../components/DocumentUploadForm";

export function DocumentsPage() {
  return (
    <Card>
      <Typography.Title level={3}>Upload Source Document</Typography.Title>
      <DocumentUploadForm />
      <Typography.Title level={4}>Document Versions</Typography.Title>
      <Table dataSource={[]} columns={[{ title: "Version", dataIndex: "version_number" }]} rowKey="version_number" />
    </Card>
  );
}
