import { useState } from "react";
import { Button, Space, Typography, Upload, message } from "antd";
import type { UploadFile } from "antd";

import type { ArchiveDocumentImportResult } from "../lib/api";
import { importArchiveDocument } from "../lib/archives";

type ArchiveDocumentImportFormProps = {
  archiveId: string | null;
  disabled?: boolean;
  onImported?: (result: ArchiveDocumentImportResult) => void | Promise<void>;
  onImportFailed?: (message: string) => void;
};

export function ArchiveDocumentImportForm({
  archiveId,
  disabled = false,
  onImported,
  onImportFailed,
}: ArchiveDocumentImportFormProps) {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);

  async function handleImport() {
    const activeFile = fileList[0]?.originFileObj;
    if (!archiveId) {
      const errorMessage = "请先选择当前知识库";
      message.error(errorMessage);
      onImportFailed?.(errorMessage);
      return;
    }
    if (!activeFile) {
      message.error("请先选择文件");
      return;
    }

    try {
      setUploading(true);
      const response = await importArchiveDocument(archiveId, activeFile);
      setFileList([]);
      await onImported?.(response.data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "上传并纳入当前知识库失败";
      message.error(errorMessage);
      onImportFailed?.(errorMessage);
    } finally {
      setUploading(false);
    }
  }

  return (
    <Space direction="vertical" size={12} style={{ display: "flex" }}>
      <div>
        <Typography.Title level={5} style={{ marginBottom: 4 }}>
          上传并纳入当前知识库
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          新上传的文件会写入当前知识库的素材目录，并立即按正式链路执行单文档纳入。
        </Typography.Paragraph>
      </div>

      <Space wrap>
        <Upload
          beforeUpload={() => false}
          fileList={fileList}
          maxCount={1}
          onChange={({ fileList: nextFileList }) => setFileList(nextFileList)}
          disabled={disabled || uploading}
        >
          <Button disabled={disabled || uploading}>选择文件</Button>
        </Upload>
        <Button type="primary" onClick={() => void handleImport()} loading={uploading} disabled={disabled}>
          上传并纳入当前知识库
        </Button>
      </Space>
    </Space>
  );
}
