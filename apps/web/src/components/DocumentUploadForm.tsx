import { Button, Form, Input, Upload } from "antd";

export function DocumentUploadForm() {
  return (
    <Form layout="vertical">
      <Form.Item label="标题" name="title">
        <Input />
      </Form.Item>
      <Form.Item label="来源名称" name="source_name">
        <Input />
      </Form.Item>
      <Upload beforeUpload={() => false}>
        <Button>选择文件</Button>
      </Upload>
      <Button type="primary" htmlType="submit">
        上传
      </Button>
    </Form>
  );
}
