import { useState } from "react";
import { Alert, Button, Card, Col, Form, Input, Row, Space, Table, Tag, Typography } from "antd";

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

const extractionLogicLayers = [
  {
    title: "原始候选",
    tone: "rgba(59, 130, 246, 0.08)",
    border: "rgba(59, 130, 246, 0.18)",
    description: "结构化分块后的块级候选结果，保留更多术语、实体、流程与证据，不直接面向最终使用。",
  },
  {
    title: "治理工作态",
    tone: "rgba(245, 158, 11, 0.10)",
    border: "rgba(245, 158, 11, 0.20)",
    description: "经过审核、驳回、归并和修订后的工作结果，页面中常见的数量可能已经排除了被驳回项。",
  },
  {
    title: "发布态",
    tone: "rgba(16, 185, 129, 0.10)",
    border: "rgba(16, 185, 129, 0.20)",
    description: "对外可查询、可图谱展示、可被建模消费的权威版本，是后续需求与设计阶段的正式输入。",
  },
] as const;

const extractionLogicSteps = [
  "Docling 结构化解析",
  "结构化分块",
  "分块抽取",
  "全局归并",
  "治理/发布",
] as const;

const extractionRules = [
  "正式知识库抽取必须走 Docling + 结构化大模型，不允许静默降级。",
  "长文档正式抽取不能只看少量采样片段，必须按结构分块后覆盖多块抽取。",
  "候选知识必须保留块级或章节级证据来源，避免只有名称、没有出处。",
  "当前界面若显示的是治理/发布结果，其数量不等于原始候选总量。",
] as const;

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
        <Row gutter={[24, 24]} align="stretch">
          <Col xs={24} lg={10}>
            <Card
              title="新增知识库"
              style={{ height: "100%" }}
              styles={{ body: { paddingBottom: 20 } }}
            >
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
                <Button
                  type="primary"
                  onClick={handleCreateArchive}
                  loading={submitting}
                  disabled={busyAction !== null && busyAction !== "create"}
                >
                  创建知识库
                </Button>
              </Form>
            </Card>
          </Col>

          <Col xs={24} lg={14}>
            <Card
              title="正式抽取逻辑"
              style={{
                height: "100%",
                borderRadius: 20,
                background:
                  "linear-gradient(140deg, rgba(248,250,252,0.98) 0%, rgba(240,249,255,0.96) 45%, rgba(248,250,252,0.98) 100%)",
                boxShadow: "0 10px 26px rgba(15, 23, 42, 0.06)",
              }}
            >
              <Space direction="vertical" size={18} style={{ display: "flex" }}>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    padding: 12,
                    borderRadius: 16,
                    background: "rgba(15, 23, 42, 0.04)",
                  }}
                >
                  {extractionLogicSteps.map((step, index) => (
                    <Tag
                      key={step}
                      style={{
                        marginInlineEnd: 0,
                        borderRadius: 999,
                        paddingInline: 10,
                        lineHeight: "24px",
                        background: index === extractionLogicSteps.length - 1 ? "rgba(16, 185, 129, 0.14)" : "#fff",
                      }}
                    >
                      {step}
                    </Tag>
                  ))}
                  <Typography.Text strong style={{ width: "100%", fontSize: 13, color: "#0f172a" }}>
                    结构化分块 -&gt; 分块抽取 -&gt; 全局归并 -&gt; 治理/发布
                  </Typography.Text>
                </div>

                <div>
                  <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>
                    三层数据语义
                  </Typography.Title>
                  <Row gutter={[12, 12]}>
                    {extractionLogicLayers.map((layer) => (
                      <Col xs={24} md={8} key={layer.title}>
                        <div
                          style={{
                            height: "100%",
                            borderRadius: 16,
                            padding: 14,
                            background: layer.tone,
                            border: `1px solid ${layer.border}`,
                          }}
                        >
                          <Typography.Text strong>{layer.title}</Typography.Text>
                          <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                            {layer.description}
                          </Typography.Paragraph>
                        </div>
                      </Col>
                    ))}
                  </Row>
                </div>

                <div>
                  <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>
                    当前正式规则
                  </Typography.Title>
                  <Space direction="vertical" size={10} style={{ display: "flex" }}>
                    {extractionRules.map((rule) => (
                      <div
                        key={rule}
                        style={{
                          borderRadius: 14,
                          border: "1px solid rgba(148, 163, 184, 0.16)",
                          background: "#fff",
                          padding: "10px 12px",
                        }}
                      >
                        <Typography.Text>{rule}</Typography.Text>
                      </div>
                    ))}
                  </Space>
                </div>

                <Alert
                  showIcon
                  type="warning"
                  message="当前仍属于受限模式"
                  description="当前工程已强制使用 Docling 和结构化大模型，但长文档抽取策略仍未升级为完整的多块全覆盖抽取。对特别长、结构复杂的手册型资料，当前结果可用于治理起点，但不应被误解为最终完整知识结果。"
                />
              </Space>
            </Card>
          </Col>
        </Row>

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
