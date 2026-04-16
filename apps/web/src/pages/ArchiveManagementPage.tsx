import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Form, Input, Progress, Row, Space, Table, Tag, Typography } from "antd";

import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { WorkspaceOverviewStrip } from "../components/WorkspaceOverviewStrip";
import { useArchiveContext } from "../context/ArchiveContext";
import { createKnowledgeArchive, extractKnowledgeArchive } from "../lib/archives";
import type { CreateKnowledgeArchiveInput, KnowledgeArchive } from "../lib/api";

const statusMeta: Record<KnowledgeArchive["status"], { color: string; label: string }> = {
  empty: { color: "default", label: "未抽取" },
  extracting: { color: "processing", label: "抽取中" },
  ready: { color: "success", label: "可用" },
  error: { color: "error", label: "异常" },
};

const actionButtonStyle = {
  minWidth: 96,
  justifyContent: "center" as const,
};

const buildDocumentStateMeta = {
  pending: { color: "default", label: "待处理" },
  running: { color: "processing", label: "进行中" },
  completed: { color: "success", label: "已完成" },
  failed: { color: "error", label: "失败" },
} as const;

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
  const activeArchiveRecord = archives.find((item) => item.archive_id === activeArchiveId) ?? null;
  const activeBuildState = activeArchiveRecord?.build_state ?? null;
  const activeArchiveStatusLabel = activeArchiveRecord ? statusMeta[activeArchiveRecord.status].label : "未选择";
  const extractingArchive =
    activeBusyArchive ?? archives.find((item) => item.status === "extracting") ?? null;
  const archiveRunStatus = extractingArchive
    ? `抽取中：${extractingArchive.name}${extractingArchive.build_state?.current_document_title ? ` · ${extractingArchive.build_state.current_document_title}` : ""}`
    : "空闲";
  const runningDocument =
    activeBuildState?.documents.find((item) => item.state === "running") ??
    (activeBuildState?.current_document_id
      ? activeBuildState.documents.find((item) => item.document_id === activeBuildState.current_document_id)
      : null) ??
    null;
  const currentChunk = activeBuildState?.current_chunk ?? null;
  const completedCount = activeBuildState?.completed_document_ids.length ?? 0;
  const pendingCount = activeBuildState?.pending_document_ids.length ?? 0;
  const failedCount = activeBuildState?.failed_document_id ? 1 : 0;
  const runningCount = activeBuildState?.documents.filter((item) => item.state === "running").length ?? 0;
  const progressPercent =
    activeBuildState && activeBuildState.expected_document_count > 0
      ? Math.round((completedCount / activeBuildState.expected_document_count) * 100)
      : 0;
  const shouldShowBuildProgress =
    activeBuildState !== null &&
    (activeArchiveRecord?.status === "extracting" ||
      activeBuildState.status === "failed" ||
      activeBuildState.status === "completed");

  useEffect(() => {
    if (activeArchiveRecord?.status !== "extracting") {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshArchives(activeArchiveId);
    }, 5000);

    return () => {
      window.clearInterval(timer);
    };
  }, [activeArchiveId, activeArchiveRecord?.status, refreshArchives]);

  return (
    <ValidationWorkspace
      title="知识库管理"
      description="为每个知识库绑定独立的本地资料目录，分别抽取、分别存储，再按需切换到文档、治理、图谱和建模页面继续工作。"
    >
      <WorkspaceOverviewStrip
        badgeLabel="知识库管理"
        badgeColor="cyan"
        title="知识库运行总览"
        tags={[
          { label: `当前知识库：${activeArchive?.name ?? "未选择"}` },
          { label: `当前状态：${activeArchiveStatusLabel}` },
          { label: `抽取任务：${archiveRunStatus}`, color: isExtracting ? "processing" : "default" },
        ]}
        metrics={[
          { title: "知识库数量", value: archives.length },
          { title: "可用知识库", value: readyCount },
          { title: "异常知识库", value: errorCount },
          { title: "当前知识库", value: activeArchive?.name ?? "未选择" },
        ]}
      />
      {error ? <Alert showIcon type="error" message="知识库列表暂不可用" description={error} /> : null}
      {actionError ? <Alert showIcon type="error" message="知识库操作失败" description={actionError} /> : null}
      {isExtracting ? (
        <Alert
          showIcon
          type="info"
          message={`正在抽取“${activeBusyArchive?.name ?? busyArchiveId}”，期间已禁止重复提交和并发抽取。`}
        />
      ) : null}
      {!isExtracting && activeArchiveRecord?.status === "extracting" ? (
        <Alert
          showIcon
          type="info"
          message={`“${activeArchiveRecord.name}”正在后台抽取，页面会自动刷新进度。`}
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

        {shouldShowBuildProgress ? (
          <Card title="抽取进度">
            <Space direction="vertical" size={18} style={{ display: "flex" }}>
              <Space wrap size={[12, 12]}>
                <Tag color={activeBuildState.status === "failed" ? "error" : activeBuildState.status === "completed" ? "success" : "processing"}>
                  {activeBuildState.status === "failed" ? "已失败" : activeBuildState.status === "completed" ? "已完成" : "运行中"}
                </Tag>
                <Typography.Text strong>{`已完成 ${completedCount} / ${activeBuildState.expected_document_count}`}</Typography.Text>
                {activeBuildState.started_at ? (
                  <Typography.Text type="secondary">{`开始时间：${new Date(activeBuildState.started_at).toLocaleString("zh-CN")}`}</Typography.Text>
                ) : null}
              </Space>

              <Progress
                percent={progressPercent}
                status={activeBuildState.status === "failed" ? "exception" : activeBuildState.status === "completed" ? "success" : "active"}
              />

              <Row gutter={[12, 12]}>
                <Col xs={12} md={6}>
                  <div style={{ borderRadius: 14, background: "rgba(16, 185, 129, 0.10)", padding: "12px 14px" }}>
                    <Typography.Text type="secondary">已完成</Typography.Text>
                    <div>
                      <Typography.Text strong style={{ fontSize: 20 }}>
                        {completedCount}
                      </Typography.Text>
                    </div>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div style={{ borderRadius: 14, background: "rgba(59, 130, 246, 0.10)", padding: "12px 14px" }}>
                    <Typography.Text type="secondary">进行中</Typography.Text>
                    <div>
                      <Typography.Text strong style={{ fontSize: 20 }}>
                        {runningCount}
                      </Typography.Text>
                    </div>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div style={{ borderRadius: 14, background: "rgba(148, 163, 184, 0.10)", padding: "12px 14px" }}>
                    <Typography.Text type="secondary">待处理</Typography.Text>
                    <div>
                      <Typography.Text strong style={{ fontSize: 20 }}>
                        {pendingCount}
                      </Typography.Text>
                    </div>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div style={{ borderRadius: 14, background: "rgba(239, 68, 68, 0.10)", padding: "12px 14px" }}>
                    <Typography.Text type="secondary">失败</Typography.Text>
                    <div>
                      <Typography.Text strong style={{ fontSize: 20 }}>
                        {failedCount}
                      </Typography.Text>
                    </div>
                  </div>
                </Col>
              </Row>

              <div
                style={{
                  borderRadius: 16,
                  border: "1px solid rgba(148, 163, 184, 0.16)",
                  background: "linear-gradient(135deg, rgba(239,246,255,0.82) 0%, rgba(248,250,252,0.96) 100%)",
                  padding: 16,
                }}
              >
                <Typography.Text type="secondary">当前处理文档</Typography.Text>
                <div style={{ marginTop: 6 }}>
                  <Typography.Text strong>{runningDocument?.title ?? activeBuildState.current_document_title ?? "当前暂无进行中的文档"}</Typography.Text>
                </div>
                {runningDocument?.path ?? activeBuildState.current_document_path ? (
                  <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                    {runningDocument?.path ?? activeBuildState.current_document_path}
                  </Typography.Paragraph>
                ) : null}
                {currentChunk ? (
                  <div
                    style={{
                      marginTop: 12,
                      borderRadius: 12,
                      background: "rgba(255, 255, 255, 0.72)",
                      border: "1px solid rgba(148, 163, 184, 0.16)",
                      padding: 12,
                    }}
                  >
                    <Space wrap size={[12, 8]}>
                      <Typography.Text type="secondary">当前块</Typography.Text>
                      <Typography.Text strong>{`${currentChunk.position ?? "-"} / ${currentChunk.total ?? "-"}`}</Typography.Text>
                      {typeof currentChunk.retry_depth === "number" && currentChunk.retry_depth > 0 ? (
                        <Tag color="gold">{`重试深度 ${currentChunk.retry_depth}`}</Tag>
                      ) : null}
                    </Space>
                    {currentChunk.heading ? (
                      <div style={{ marginTop: 8 }}>
                        <Typography.Text strong>{currentChunk.heading}</Typography.Text>
                      </div>
                    ) : null}
                    <Space wrap size={[12, 8]} style={{ marginTop: 8 }}>
                      {typeof currentChunk.char_count === "number" ? (
                        <Typography.Text type="secondary">{`块大小 ${currentChunk.char_count} 字符`}</Typography.Text>
                      ) : null}
                      {typeof currentChunk.segment_count === "number" ? (
                        <Typography.Text type="secondary">{`分段数 ${currentChunk.segment_count}`}</Typography.Text>
                      ) : null}
                    </Space>
                  </div>
                ) : null}
              </div>

              {activeBuildState.failed_message ? (
                <Alert showIcon type="error" message="抽取失败" description={activeBuildState.failed_message} />
              ) : null}

              <div>
                <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>
                  文档执行状态
                </Typography.Title>
                <Space direction="vertical" size={10} style={{ display: "flex" }}>
                  {activeBuildState.documents.slice(0, 10).map((document) => (
                    <div
                      key={document.document_id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        borderRadius: 14,
                        border: document.state === "running" ? "1px solid rgba(59, 130, 246, 0.28)" : "1px solid rgba(148, 163, 184, 0.16)",
                        background: document.state === "running" ? "rgba(239, 246, 255, 0.92)" : "#fff",
                        padding: "10px 12px",
                      }}
                    >
                      <Space direction="vertical" size={2} style={{ display: "flex", minWidth: 0 }}>
                        <Typography.Text strong ellipsis style={{ maxWidth: 680 }}>
                          {document.title}
                        </Typography.Text>
                        <Typography.Text type="secondary" ellipsis style={{ maxWidth: 680 }}>
                          {document.path}
                        </Typography.Text>
                      </Space>
                      <Tag color={buildDocumentStateMeta[document.state].color}>{buildDocumentStateMeta[document.state].label}</Tag>
                    </div>
                  ))}
                  {activeBuildState.documents.length > 10 ? (
                    <Typography.Text type="secondary">{`其余 ${activeBuildState.documents.length - 10} 篇文档仍可按相同状态继续查看。`}</Typography.Text>
                  ) : null}
                </Space>
              </div>
            </Space>
          </Card>
        ) : null}

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
                      style={actionButtonStyle}
                      onClick={() => void handleActivateArchive(record.archive_id)}
                      disabled={record.is_active || busyAction !== null}
                      loading={busyAction === "activate" && busyArchiveId === record.archive_id}
                    >
                      {record.is_active ? "当前在用" : "设为当前"}
                    </Button>
                    <Button
                      style={actionButtonStyle}
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
