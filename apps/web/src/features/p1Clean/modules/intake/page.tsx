import { useCallback, useEffect, useMemo, useState } from "react";

import { Alert, Button, Card, Col, Empty, Row, Space, Spin, Statistic, Steps, Table, Tag, Typography, Upload } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { UploadProps } from "antd";

import { useArchiveContext } from "../../../../context/ArchiveContext";
import type { KnowledgeArchiveBuildWarning } from "../../../../lib/api";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { extractKnowledgeArchive, getIntakeSnapshot, importArchiveDocument } from "./api";
import type { IntakeAvailability, IntakeContractSnapshot, IntakeDocumentRow } from "./types";
import { buildDocumentSetId, buildDocumentSetSummary, buildIntakeRows, buildPreflightSummary } from "./viewModel";

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
}

function getAvailabilityMeta(value: IntakeAvailability) {
  if (value === "available") return { label: "可用", color: "green" };
  if (value === "warning") return { label: "有警告", color: "orange" };
  return { label: "不可用", color: "red" };
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function normalizePath(value: string | null | undefined) {
  return (value ?? "").replace(/\\/g, "/").trim().toLowerCase();
}

function resolveDocumentWarning(row: IntakeDocumentRow, warnings: KnowledgeArchiveBuildWarning[] = []) {
  const sourcePath = normalizePath(row.sourcePath);
  const fileName = normalizePath(row.fileName);
  return warnings.find((warning) => {
    const warningPath = normalizePath(warning.file_path);
    return warningPath === sourcePath || warningPath.endsWith(`/${fileName}`) || sourcePath.endsWith(`/${fileName}`);
  });
}

function getDocumentIssue(row: IntakeDocumentRow, warnings: KnowledgeArchiveBuildWarning[] = []) {
  const warning = resolveDocumentWarning(row, warnings);
  return warning?.reason ?? row.parseError ?? warning?.message ?? null;
}

export function IntakePage({ context }: P1ModulePageProps) {
  const { refreshArchives } = useArchiveContext();
  const [snapshot, setSnapshot] = useState<IntakeContractSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"upload" | "extract" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fallbackSnapshot = useMemo<IntakeContractSnapshot>(
    () => ({
      archive_id: context.archiveId,
      document_set_id: context.documentSetId ?? buildDocumentSetId(context.archiveId),
      source_dir: context.archive.source_dir,
      policy_package_version_id: context.policyPackageVersionId,
      documents: [],
      summary: {
        document_count: 0,
        parsed_completed_count: 0,
        parsed_failed_count: 0,
        pending_count: 0,
        can_enter_runtime_count: 0,
        blocked_count: 0,
      },
      preflight_issues: [],
    }),
    [context.archive.source_dir, context.archiveId, context.documentSetId, context.policyPackageVersionId],
  );

  const loadIntake = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getIntakeSnapshot(context.archiveId);
      setSnapshot(response.data.data);
    } catch (loadError) {
      setError(getErrorMessage(loadError, "资料接入数据加载失败"));
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, [context.archiveId]);

  useEffect(() => {
    void loadIntake();
  }, [loadIntake]);

  const effectiveSnapshot = snapshot ?? fallbackSnapshot;
  const documents = useMemo(() => buildIntakeRows(effectiveSnapshot), [effectiveSnapshot]);
  const documentSetSummary = useMemo(() => buildDocumentSetSummary(effectiveSnapshot), [effectiveSnapshot]);
  const preflight = useMemo(() => buildPreflightSummary(effectiveSnapshot), [effectiveSnapshot]);
  const formatAvailability = getAvailabilityMeta(preflight.formatAvailability);
  const structureAvailability = getAvailabilityMeta(preflight.structureAvailability);
  const hasRunningDocuments = documents.some((document) => document.parseStatus === "running");
  const buildWarnings = context.archive.build_state?.warnings ?? [];
  const skippedDocuments = documents.filter((document) => document.parseStatus === "skipped");
  const blockedDocuments = documents.filter((document) => !document.canEnterRuntime);
  const hasPreflightBlock = documents.length > 0 && !preflight.canEnterExtraction;
  const canStartExtraction =
    preflight.canEnterExtraction && !hasRunningDocuments && actionLoading !== "upload" && documents.length > 0;
  const primaryActionLabel =
    documents.length === 0
      ? "等待资料接入"
      : hasRunningDocuments
        ? "解析预检中"
        : preflight.canEnterExtraction
          ? "启动正式抽取"
          : "预检未通过";

  async function handleUpload(file: File) {
    setActionLoading("upload");
    setError(null);
    setNotice(null);
    try {
      const response = await importArchiveDocument(context.archiveId, file);
      setNotice(`已接入 ${response.data.document?.title ?? response.data.stored_path}`);
      await refreshArchives(context.archiveId);
      await loadIntake();
    } catch (uploadError) {
      setError(getErrorMessage(uploadError, "资料上传失败"));
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExtract() {
    setActionLoading("extract");
    setError(null);
    setNotice(null);
    try {
      await extractKnowledgeArchive(context.archiveId);
      setNotice("已提交资料解析任务");
      await refreshArchives(context.archiveId);
      await loadIntake();
    } catch (extractError) {
      setError(getErrorMessage(extractError, "抽取入队失败"));
    } finally {
      setActionLoading(null);
    }
  }

  const uploadProps: UploadProps = {
    accept: ".pdf,.doc,.docx,.xlsx,.xls",
    maxCount: 1,
    showUploadList: false,
    beforeUpload: (file) => {
      void handleUpload(file);
      return false;
    },
  };

  const columns: ColumnsType<IntakeDocumentRow> = [
    {
      title: "文件",
      dataIndex: "title",
      render: (_value, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.title}</Typography.Text>
          <Typography.Text type="secondary">{row.fileName}</Typography.Text>
          <Typography.Text type="secondary" ellipsis style={{ maxWidth: 420 }}>
            {row.sourcePath}
          </Typography.Text>
        </Space>
      ),
    },
    { title: "类型", dataIndex: "fileType", width: 90, render: (value) => <Tag>{value}</Tag> },
    {
      title: "段落块",
      dataIndex: "segmentCount",
      width: 110,
      align: "right",
      render: (value: number) => formatNumber(value),
    },
    {
      title: "锚点",
      dataIndex: "anchorCount",
      width: 90,
      align: "right",
      render: (value: number) => formatNumber(value),
    },
    {
      title: "解析状态",
      dataIndex: "parseStatusLabel",
      width: 120,
      render: (_value, row) => <Tag color={row.parseStatusColor}>{row.parseStatusLabel}</Tag>,
    },
    {
      title: "解析预检",
      dataIndex: "runtimeStatus",
      width: 220,
      render: (_value, row) => (
        <Space direction="vertical" size={0}>
          <Tag color={row.runtimeStatusColor}>{row.runtimeStatus}</Tag>
          {getDocumentIssue(row, buildWarnings) ? (
            <Typography.Text type="secondary">{getDocumentIssue(row, buildWarnings)}</Typography.Text>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageFrame
      eyebrow="资料接入模块"
      title="资料接入"
      description="只负责当前知识库的文件夹选择、文件扫描、解析预检和抽取任务入队，不编辑策略、不解释质量。"
    >
      {error ? <Alert className="p1-clean-alert" type="error" showIcon message="资料接入失败" description={error} /> : null}
      {notice ? <Alert className="p1-clean-alert" type="success" showIcon message={notice} /> : null}
      {hasPreflightBlock ? (
        <Alert
          className="p1-clean-alert"
          type="warning"
          showIcon
          message={`预检未通过：${documentSetSummary.documentCount} 份资料中 ${documentSetSummary.canEnterRuntimeCount} 份可进入运行，${documentSetSummary.skippedCount} 份已跳过，${documentSetSummary.blockedCount} 份阻断`}
          description={
            <Space direction="vertical" size={2}>
              {blockedDocuments.slice(0, 4).map((document) => (
                <Typography.Text key={document.documentId}>
                  {document.fileName}：{getDocumentIssue(document, buildWarnings) ?? document.runtimeStatus}
                </Typography.Text>
              ))}
              {blockedDocuments.length > 4 ? (
                <Typography.Text type="secondary">还有 {blockedDocuments.length - 4} 份阻断资料未展开。</Typography.Text>
              ) : null}
            </Space>
          }
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card className="p1-clean-card" title="资料源">
            <Space direction="vertical" size={10}>
              <Typography.Text>知识库：{context.archive.name}</Typography.Text>
              <Typography.Text>来源：{effectiveSnapshot.source_dir}</Typography.Text>
              <Typography.Text>documentSetId：{documentSetSummary.documentSetId}</Typography.Text>
              <Typography.Text>策略版本：{effectiveSnapshot.policy_package_version_id ?? "待冻结"}</Typography.Text>
              <Space wrap>
                <Upload {...uploadProps}>
                  <Button loading={actionLoading === "upload"}>上传资料</Button>
                </Upload>
                <Button onClick={() => void loadIntake()} loading={loading}>
                  刷新集合
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card className="p1-clean-card" title="接入过程">
            <Steps
              current={2}
              items={[
                { title: "选择文件夹", description: "绑定资料来源" },
                { title: "扫描文件", description: "生成文档集合" },
                { title: "解析预检", description: "结构与格式可用性检查" },
                { title: "入队抽取", description: "输出 documentSetId" },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="p1-clean-card">
            <Statistic title="识别文档" value={documentSetSummary.documentCount} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="p1-clean-card">
            <Statistic title="可进入运行" value={documentSetSummary.canEnterRuntimeCount} valueStyle={{ color: "#237804" }} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="p1-clean-card">
            <Statistic title="已跳过" value={documentSetSummary.skippedCount} valueStyle={{ color: "#ad6800" }} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="p1-clean-card">
            <Statistic title="阻断资料" value={documentSetSummary.blockedCount} valueStyle={{ color: "#cf1322" }} />
          </Card>
        </Col>
      </Row>

      <Card
        className="p1-clean-card"
        title="解析预检"
        extra={
          <Button
            type="primary"
            loading={actionLoading === "extract"}
            disabled={!canStartExtraction}
            onClick={() => void handleExtract()}
          >
            {primaryActionLabel}
          </Button>
        }
      >
        <Space direction="vertical" size={12}>
          <Space wrap>
            <Tag color={formatAvailability.color}>格式可用性：{formatAvailability.label}</Tag>
            <Tag color={structureAvailability.color}>结构可用性：{structureAvailability.label}</Tag>
            <Tag color={preflight.canEnterExtraction ? "green" : "red"}>
              抽取运行：{preflight.canEnterExtraction ? "可进入" : "暂不可进入"}
            </Tag>
          </Space>
          {preflight.issues.length > 0 ? (
            <Space direction="vertical" size={4}>
              {preflight.issues.map((issue) => (
                <Typography.Text type="secondary" key={issue}>
                  {issue}
                </Typography.Text>
              ))}
            </Space>
          ) : (
            <Typography.Text type="secondary">预检未发现阻断项</Typography.Text>
          )}
          {skippedDocuments.length > 0 ? (
            <Space direction="vertical" size={4}>
              {skippedDocuments.map((document) => (
                <Typography.Text type="secondary" key={document.documentId}>
                  {document.fileName} 已跳过：{getDocumentIssue(document, buildWarnings) ?? "未提供跳过原因"}
                </Typography.Text>
              ))}
            </Space>
          ) : null}
        </Space>
      </Card>

      <Card className="p1-clean-card" title="文档集合预览">
        <Spin spinning={loading}>
          {documents.length > 0 ? (
            <Table rowKey="id" columns={columns} dataSource={documents} pagination={false} />
          ) : (
            <Empty description="当前文档集合为空" />
          )}
        </Spin>
      </Card>
    </PageFrame>
  );
}
