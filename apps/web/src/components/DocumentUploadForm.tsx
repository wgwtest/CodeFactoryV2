import { Button, Form, Input, Upload } from "antd";

export function DocumentUploadForm() {
  return (
    <Form layout="vertical">
      <Form.Item label="Title" name="title">
        <Input />
      </Form.Item>
      <Form.Item label="Source Name" name="source_name">
        <Input />
      </Form.Item>
      <Upload beforeUpload={() => false}>
        <Button>Select File</Button>
      </Upload>
      <Button type="primary" htmlType="submit">
        Upload
      </Button>
    </Form>
  );
}
