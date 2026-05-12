import { Alert, Button, Card, Col, Form, Input, Layout, Modal, Row, Space, Tag, Typography } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useArchiveContext } from "../../../../context/ArchiveContext";
import {
  getArchivePolicyLabel,
  getArchiveSnapshotLabel,
  getArchiveStatusColor,
  getArchiveStatusLabel,
  getArchiveTopic,
} from "../../archivePresentation";
import { buildP1WorkspacePath } from "../../routing";
import { knowledgeBaseManagementApi } from "./api";

type ArchiveCreateFormValues = {
  archive_id?: string;
  name: string;
  source_dir: string;
  extract_root?: string;
};

const MID_TERM_EXAMPLE_SOURCE_DIR =
  "E:/project/Web/智能软件生成/知识构建原始材料/体系结构运行测试小规模v3/Mid Term";

function buildArchiveId(value: string) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || `kb-${Date.now()}`;
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "创建知识库失败";
}

export function KnowledgeBaseManagementPage() {
  const navigate = useNavigate();
  const { archives, loading, error, refreshArchives } = useArchiveContext();
  const [form] = Form.useForm<ArchiveCreateFormValues>();
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const openCreateModal = () => {
    setSubmitError(null);
    form.resetFields();
    setModalOpen(true);
  };

  const closeCreateModal = () => {
    if (submitting) {
      return;
    }
    setModalOpen(false);
    setSubmitError(null);
  };

  const handleCreateArchive = async (values: ArchiveCreateFormValues) => {
    setSubmitting(true);
    setSubmitError(null);
    const archiveId = buildArchiveId(values.archive_id || values.name);

    try {
      const response = await knowledgeBaseManagementApi.createArchive({
        archive_id: archiveId,
        name: values.name.trim(),
        source_dir: values.source_dir.trim(),
        extract_root: values.extract_root?.trim() || undefined,
      });
      await knowledgeBaseManagementApi.activateArchive(response.data.archive_id);
      await refreshArchives(response.data.archive_id);
      setModalOpen(false);
      navigate(buildP1WorkspacePath(response.data.archive_id));
    } catch (createError) {
      setSubmitError(getErrorMessage(createError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout className="p1-clean-shell p1-kb-gateway">
      <Layout.Content className="p1-clean-content">
        <main className="p1-clean-page">
          <section className="p1-kb-hero">
            <div>
              <Tag color="blue">P1 上层入口</Tag>
              <Typography.Title level={1}>知识库管理</Typography.Title>
              <Typography.Paragraph>
                先选择或创建一个知识库，再进入该知识库的资料接入、策略规则、抽取运行、质量图谱和发布输出工作区。
                这层只负责知识库管理，不混入单个知识库内部流程导航。
              </Typography.Paragraph>
            </div>
            <Space wrap>
              <Button size="large" onClick={openCreateModal}>
                创建知识库
              </Button>
              <Button size="large" onClick={() => void refreshArchives()}>
                刷新
              </Button>
            </Space>
          </section>

          <Alert
            className="p1-clean-alert"
            type="info"
            showIcon
            message="层级关系：/p1 是知识库管理，/p1/archives/:archiveId/... 才是单知识库工作区。"
            description="后续每个工作区模块只接收统一上下文，不直接读取其它模块内部状态。"
          />

          {error ? (
            <Alert className="p1-clean-alert" type="error" showIcon message="知识库列表加载失败" description={error} />
          ) : null}

          <Row gutter={[16, 16]}>
            {archives.map((archive) => (
              <Col xs={24} lg={8} key={archive.archive_id}>
                <Card
                  loading={loading}
                  className={`p1-clean-card p1-kb-card ${archive.is_active ? "is-active" : ""}`}
                  title={
                    <Space direction="vertical" size={2}>
                      <Typography.Text strong>{archive.name}</Typography.Text>
                      <Typography.Text type="secondary">来源：{archive.source_dir}</Typography.Text>
                    </Space>
                  }
                  extra={<Tag color={getArchiveStatusColor(archive)}>{getArchiveStatusLabel(archive)}</Tag>}
                >
                  <Space direction="vertical" size={12} className="p1-kb-card-body">
                    <Typography.Paragraph>{getArchiveTopic(archive)}</Typography.Paragraph>
                    <div className="p1-kb-meta-grid">
                      <span>文档数</span>
                      <strong>{archive.summary?.document_count ?? archive.build_state?.expected_document_count ?? 0}</strong>
                      <span>默认策略</span>
                      <strong>{getArchivePolicyLabel(archive)}</strong>
                      <span>最近快照</span>
                      <strong>{getArchiveSnapshotLabel(archive)}</strong>
                      <span>最近运行</span>
                      <strong>{archive.last_built_at ?? archive.build_state?.updated_at ?? "--"}</strong>
                    </div>
                    <Space wrap>
                      <Button type="primary" onClick={() => navigate(buildP1WorkspacePath(archive.archive_id))}>
                        进入知识库工作区
                      </Button>
                      <Button onClick={() => navigate(buildP1WorkspacePath(archive.archive_id, "intake"))}>资料接入</Button>
                    </Space>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>

          {!loading && archives.length === 0 ? (
            <Card className="p1-clean-card p1-empty-card">
              <Typography.Title level={4}>还没有知识库</Typography.Title>
              <Typography.Paragraph>请先创建知识库或从资料文件夹导入，随后再进入 P1 工作区。</Typography.Paragraph>
            </Card>
          ) : null}

          <Modal
            title="创建知识库"
            open={modalOpen}
            confirmLoading={submitting}
            okText="创建并进入工作区"
            cancelText="取消"
            onCancel={closeCreateModal}
            onOk={() => void form.submit()}
            destroyOnHidden
          >
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Alert
                type="info"
                showIcon
                message="当前接入方式"
                description="后端创建知识库需要一个本机可访问的资料文件夹路径，例如 E:/project/data/contracts。浏览器无法直接读取真实文件夹路径，所以这里先按路径创建，后续再接批量上传式文件夹导入。"
              />
              {submitError ? <Alert type="error" showIcon message="创建失败" description={submitError} /> : null}
              <Form form={form} layout="vertical" onFinish={(values) => void handleCreateArchive(values)}>
                <Form.Item
                  label="知识库名称"
                  name="name"
                  rules={[{ required: true, message: "请输入知识库名称" }]}
                >
                  <Input placeholder="例如：销售合同知识库" />
                </Form.Item>
                <Form.Item label="知识库标识" name="archive_id" extra="可选。留空时会根据名称自动生成，只允许英文、数字、短横线和下划线。">
                  <Input placeholder="例如：sales-contracts" />
                </Form.Item>
                <Form.Item
                  label="资料文件夹路径"
                  name="source_dir"
                  rules={[{ required: true, message: "请输入后端可访问的资料文件夹路径" }]}
                  extra={`该路径必须存在且是目录。P1 Mid Term 黄金样例可填写：${MID_TERM_EXAMPLE_SOURCE_DIR}`}
                >
                  <Input placeholder={MID_TERM_EXAMPLE_SOURCE_DIR} />
                </Form.Item>
                <Form.Item label="抽取产物目录" name="extract_root" extra="可选。留空时系统会自动分配。">
                  <Input placeholder="例如：E:/project/data/contracts-extract" />
                </Form.Item>
              </Form>
            </Space>
          </Modal>
        </main>
      </Layout.Content>
    </Layout>
  );
}
