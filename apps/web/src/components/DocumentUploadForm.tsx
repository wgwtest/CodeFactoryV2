import { useState } from "react";
import { Button, Form, Input, Upload, message } from "antd";
import type { UploadFile } from "antd";

import { api } from "../lib/api";

type DocumentUploadFormProps = {
  onUploaded?: () => void | Promise<void>;
};

export function DocumentUploadForm({ onUploaded }: DocumentUploadFormProps) {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);

  async function handleSubmit(values: { title: string; source_name: string }) {
    const activeFile = fileList[0]?.originFileObj;
    if (!activeFile) {
      message.error("请先选择文件");
      return;
    }

    const payload = new FormData();
    payload.append("title", values.title);
    payload.append("source_name", values.source_name);
    payload.append("file", activeFile);

    try {
      setUploading(true);
      await api.post("/documents", payload, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      message.success("文档上传并解析完成");
      form.resetFields();
      setFileList([]);
      await onUploaded?.();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "文档上传失败");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Form layout="vertical" form={form} onFinish={(values) => void handleSubmit(values)}>
      <Form.Item label="标题" name="title">
        <Input />
      </Form.Item>
      <Form.Item label="来源名称" name="source_name">
        <Input />
      </Form.Item>
      <Upload
        beforeUpload={() => false}
        fileList={fileList}
        maxCount={1}
        onChange={({ fileList: nextFileList }) => setFileList(nextFileList)}
      >
        <Button>选择文件</Button>
      </Upload>
      <Button type="primary" htmlType="submit" loading={uploading}>
        上传
      </Button>
    </Form>
  );
}
