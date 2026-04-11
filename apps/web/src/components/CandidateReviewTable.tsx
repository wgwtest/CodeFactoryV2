import { Table } from "antd";

export function CandidateReviewTable() {
  return (
    <Table
      rowKey="id"
      dataSource={[]}
      columns={[
        { title: "Type", dataIndex: "item_type" },
        { title: "Name", dataIndex: "canonical_name" },
        { title: "Confidence", dataIndex: "confidence" }
      ]}
    />
  );
}
