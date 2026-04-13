import { useState } from "react";
import { Alert, Button, Card, Form, Input, Space, Table, Tag, Typography } from "antd";

import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { useArchiveContext } from "../context/ArchiveContext";
import { createKnowledgeArchive, extractKnowledgeArchive } from "../lib/archives";
import type { CreateKnowledgeArchiveInput, KnowledgeArchive } from "../lib/api";

const statusMeta: Record<KnowledgeArchive["status"], { color: string; label: string }> = {
  empty: { color: "default", label: "未抽取" },
  extracting: { color: "processing", label: "抽取中" },
  ready: { color: "success", label: "可用" },
  error: { color: "error", label: "异常" },
};

export function ArchiveManagementPage() {
  const { activeArchiveId, activeArchive, archives, error, loading, refreshArchives, setActiveArchiveId } = useArchiveContext();
  const [createForm, setCreateForm] = useState<CreateKnowledgeArchiveInput>({
    archive_id: "",
    name: "",
    source_dir: "",
    extract_root: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyArchiveId, setBusyArchiveId] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"create" | "extract" | "activate" | null>(null);

  async function handleCreateArchive() {
    if (!createForm.archive_id.trim() || !createForm.name.trim() || !createForm.source_dir.trim()) {
      setActionError("请完整填写知识库名称、标识和源目录");
      return;
    }

    try {
      setBusyAction("create");
      setSubmitting(true);
      await createKnowledgeArchive({
        archive_id: createForm.archive_id.trim(),
        name: createForm.name.trim(),
        source_dir: createForm.source_dir.trim(),
        extract_root: createForm.extract_root?.trim() || undefined,
      });
      setCreateForm({ archive_id: "", name: "", source_dir: "", extract_root: "" });
      await refreshArchives();
      setActionError(null);
    } catch (createError) {
      setActionError(createError instanceof Error ? createError.message : "创建知识库失败");
    } finally {
      setSubmitting(false);
      setBusyAction(null);
    }
  }

  async function handleExtractArchive(archiveId: string) {
    try {
      setBusyAction("extract");
      setBusyArchiveId(archiveId);
      await extractKnowledgeArchive(archiveId);
      await refreshArchives(archiveId === activeArchiveId ? archiveId : undefined);
      setActionError(null);
    } catch (extractError) {
      setActionError(extractError instanceof Error ? extractError.message : "执行抽取失败");
    } finally {
      setBusyArchiveId(null);
      setBusyAction(null);
    }
  }

  async function handleActivateArchive(archiveId: string) {
    try {
      setBusyAction("activate");
      setBusyArchiveId(archiveId);
      await setActiveArchiveId(archiveId);
      setActionError(null);
    } catch (activateError) {
      setActionError(activateError instanceof Error ? activateError.message : "切换知识库失败");
    } finally {
      setBusyArchiveId(null);
      setBusyAction(null);
    }
  }

  const readyCount = archives.filter((item) => item.status === "ready").length;
  const errorCount = archives.filter((item) => item.status === "error").length;
  const isExtracting = busyAction === "extract" && busyArchiveId !== null;
  const activeBusyArchive = archives.find((item) => item.archive_id === busyArchiveId) ?? null;

  return (
    <ValidationWorkspace
      title="知识库管理"
      description="为每个知识库绑定独立的本地资料目录，分别抽取、分别存储，再按需切换到文档、治理、图谱和建模页面继续工作。"
      stats={[
        { title: "知识库数量", value: archives.length },
        { title: "可用知识库", value: readyCount },
        { title: "异常知识库", value: errorCount },
        { title: "当前知识库", value: activeArchive?.name ?? "未选择" },
      ]}
    >
      {error ? <Alert showIcon type="error" message="知识库列表暂不可用" description={error} /> : null}
      {actionError ? <Alert showIcon type="error" message="知识库操作失败" description={actionError} /> : null}
      {isExtracting ? (
        <Alert
          showIcon
          type="info"
          message={`正在抽取“${activeBusyArchive?.name ?? busyArchiveId}”，期间已禁止重复提交和并发抽取。`}
        />
      ) : null}

      <Space direction="vertical" size={24} style={{ display: "flex" }}>
        <Card title="新增知识库">
          <Form layout="vertical">
            <Form.Item label="知识库名称">
              <Input
                aria-label="知识库名称"
                placeholder="例如：领域 B 知识库"
                value={createForm.name}
                disabled={busyAction !== null}
                onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="知识库标识">
              <Input
                aria-label="知识库标识"
                placeholder="例如：domain-b"
                value={createForm.archive_id}
                disabled={busyAction !== null}
                onChange={(event) => setCreateForm((current) => ({ ...current, archive_id: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="源目录">
              <Input
                aria-label="源目录"
                placeholder="/path/to/source"
                value={createForm.source_dir}
                disabled={busyAction !== null}
                onChange={(event) => setCreateForm((current) => ({ ...current, source_dir: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="解压缓存目录（可选）">
              <Input
                aria-label="解压缓存目录"
                placeholder="留空则自动生成"
                value={createForm.extract_root}
                disabled={busyAction !== null}
                onChange={(event) => setCreateForm((current) => ({ ...current, extract_root: event.target.value }))}
              />
            </Form.Item>
            <Button type="primary" onClick={handleCreateArchive} loading={submitting} disabled={busyAction !== null && busyAction !== "create"}>
              创建知识库
            </Button>
          </Form>
        </Card>

        <Card title="知识库列表">
          <Table
            rowKey="archive_id"
            loading={loading}
            pagination={false}
            dataSource={archives}
            locale={{ emptyText: "暂无知识库" }}
            columns={[
              {
                title: "知识库",
                render: (_value: unknown, record: KnowledgeArchive) => (
                  <Space direction="vertical" size={4} style={{ display: "flex" }}>
                    <Space size={8} wrap>
                      <Typography.Text strong>{record.name}</Typography.Text>
                      {record.is_active ? <Tag color="blue">当前使用中</Tag> : null}
                    </Space>
                    <Typography.Text type="secondary">{record.archive_id}</Typography.Text>
                  </Space>
                ),
              },
              {
                title: "源目录",
                dataIndex: "source_dir",
                render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
              },
              {
                title: "状态",
                render: (_value: unknown, record: KnowledgeArchive) => (
                  <Space direction="vertical" size={4} style={{ display: "flex" }}>
                    <Tag color={statusMeta[record.status].color}>{statusMeta[record.status].label}</Tag>
                    {record.last_error ? <Typography.Text type="danger">{record.last_error}</Typography.Text> : null}
                  </Space>
                ),
              },
              {
                title: "内容摘要",
                render: (_value: unknown, record: KnowledgeArchive) =>
                  record.summary ? (
                    <Space size={12} wrap>
                      <Typography.Text>{record.summary.document_count} 文档</Typography.Text>
                      <Typography.Text>{record.summary.entity_count} 实体</Typography.Text>
                      <Typography.Text>{record.summary.process_count} 流程</Typography.Text>
                    </Space>
                  ) : (
                    <Typography.Text type="secondary">尚未生成知识内容</Typography.Text>
                  ),
              },
              {
                title: "操作",
                render: (_value: unknown, record: KnowledgeArchive) => (
                  <Space wrap>
                    <Button
                      onClick={() => void handleActivateArchive(record.archive_id)}
                      disabled={record.is_active || busyAction !== null}
                      loading={busyAction === "activate" && busyArchiveId === record.archive_id}
                    >
                      {record.is_active ? "当前知识库" : "设为当前"}
                    </Button>
                    <Button
                      type="primary"
                      ghost
                      onClick={() => void handleExtractArchive(record.archive_id)}
                      disabled={busyAction !== null && !(busyAction === "extract" && busyArchiveId === record.archive_id)}
                      loading={busyAction === "extract" && busyArchiveId === record.archive_id}
                    >
                      立即抽取
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>
    </ValidationWorkspace>
  );
}
