import { useState, type KeyboardEvent } from "react";
import { Alert, Button, Card, Col, List, Row, Space, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import { useArchiveContext } from "../context/ArchiveContext";
import type { RequirementSpecDetail } from "../lib/api";
import { buildP2SimWriteInput, p2SimTemplates, type P2SimTemplate } from "../lib/p2SimTemplates";
import { createRequirementSpec } from "../lib/requirements";

export function XXP2SimPage() {
  const { activeArchiveId } = useArchiveContext();
  const [selectedTemplateId, setSelectedTemplateId] = useState(p2SimTemplates[0]?.template_id ?? null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdSpec, setCreatedSpec] = useState<RequirementSpecDetail | null>(null);

  const selectedTemplate = p2SimTemplates.find((item) => item.template_id === selectedTemplateId) ?? p2SimTemplates[0];

  async function handleSubmit() {
    if (!selectedTemplate) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await createRequirementSpec(buildP2SimWriteInput(selectedTemplate, activeArchiveId));
      setCreatedSpec(response.data);
      setError(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "提交需求规格说明失败");
    } finally {
      setSubmitting(false);
    }
  }

  function selectTemplate(templateId: P2SimTemplate["template_id"]) {
    setSelectedTemplateId(templateId);
  }

  function handleTemplateKeyDown(event: KeyboardEvent<HTMLDivElement>, templateId: P2SimTemplate["template_id"]) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectTemplate(templateId);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div style={{ maxWidth: 1440, margin: "0 auto 20px" }}>
        <Card
          style={{
            borderRadius: 20,
            border: "1px solid #d0d7de",
            background: "linear-gradient(135deg, #0f172a 0%, #0f766e 48%, #1d4ed8 100%)",
            boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
          }}
        >
          <Space direction="vertical" size={14} style={{ display: "flex" }}>
            <Tag color="processing" style={{ width: "fit-content" }}>
              XX-P2-Sim
            </Tag>
            <div>
              <Typography.Title level={2} style={{ color: "#ffffff", margin: 0 }}>
                P3 上游模拟输入台
              </Typography.Title>
              <Typography.Paragraph style={{ color: "rgba(255,255,255,0.82)", margin: "8px 0 0" }}>
                选择一个轻量需求规格说明样板，直接提交到现有需求规格池，让 XX-P3 按真实上游接单方式继续处理。
              </Typography.Paragraph>
            </div>
            <Space wrap>
              <Tag color="cyan">无需额外推送到 P3</Tag>
              <Tag color="blue">提交状态：ready</Tag>
              <Tag color="geekblue">当前知识库：{activeArchiveId ?? "默认"}</Tag>
            </Space>
          </Space>
        </Card>
      </div>

      <div style={{ maxWidth: 1440, margin: "0 auto" }}>
        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
        {createdSpec ? (
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
            message="已提交需求规格说明"
            description={
              <Space wrap>
                <Typography.Text>规格标识：{createdSpec.id}</Typography.Text>
                <Link to="/xx-p3">前往 XX-P3</Link>
              </Space>
            }
          />
        ) : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={10}>
            <Card title="轻量样板库" style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}>
              <Space direction="vertical" size={14} style={{ display: "flex" }}>
                <Typography.Text type="secondary">点击卡片即可切换样板，右侧预览会实时更新。</Typography.Text>
                {p2SimTemplates.map((template) => {
                  const isSelected = template.template_id === selectedTemplate?.template_id;

                  return (
                    <Card
                      key={template.template_id}
                      size="small"
                      hoverable
                      role="button"
                      tabIndex={0}
                      aria-pressed={isSelected}
                      onClick={() => selectTemplate(template.template_id)}
                      onKeyDown={(event) => handleTemplateKeyDown(event, template.template_id)}
                      style={{
                        borderRadius: 16,
                        borderColor: isSelected ? "#2563eb" : "#d0d7de",
                        background: isSelected ? "linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%)" : "#ffffff",
                        cursor: "pointer",
                        boxShadow: isSelected ? "0 12px 28px rgba(37, 99, 235, 0.14)" : "0 6px 20px rgba(15, 23, 42, 0.05)",
                      }}
                    >
                      <Space direction="vertical" size={10} style={{ display: "flex" }}>
                        <Space wrap size={[8, 8]} style={{ justifyContent: "space-between" }}>
                          <Tag color={isSelected ? "blue" : "default"}>{template.badge}</Tag>
                          <Typography.Text strong>{template.title}</Typography.Text>
                          {isSelected ? <Tag color="processing">当前样板</Tag> : null}
                        </Space>
                        <Typography.Text type="secondary">{template.use_case}</Typography.Text>
                        <Typography.Text>{template.fit_for}</Typography.Text>
                        <Space wrap>
                          <Tag color="purple">对象 {template.payload.objects.length}</Tag>
                          <Tag color="cyan">流程 {template.payload.processes.length}</Tag>
                          <Tag color="gold">约束 {template.payload.non_functional_constraints.length}</Tag>
                        </Space>
                        <Typography.Text style={{ color: isSelected ? "#2563eb" : "#64748b" }}>
                          {isSelected ? `已选中，提交将使用 ${template.title}` : "点击切换为当前样板"}
                        </Typography.Text>
                      </Space>
                    </Card>
                  );
                })}
              </Space>
            </Card>
          </Col>

          <Col xs={24} xl={14}>
            <Card title="提交预览" style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}>
              {selectedTemplate ? (
                <Space direction="vertical" size={18} style={{ display: "flex" }}>
                  <div>
                    <Typography.Title level={4} style={{ margin: 0 }}>
                      {selectedTemplate.payload.application.name}
                    </Typography.Title>
                    <Typography.Paragraph style={{ margin: "8px 0 0", color: "#475569" }}>
                      {selectedTemplate.preview_summary}
                    </Typography.Paragraph>
                  </div>

                  <Space wrap>
                    <Tag color="blue">{selectedTemplate.payload.application.domain}</Tag>
                    {selectedTemplate.payload.application.target_users.map((user) => (
                      <Tag key={user}>{user}</Tag>
                    ))}
                  </Space>

                  <Card size="small" title="业务对象" style={{ borderRadius: 16 }}>
                    <List
                      size="small"
                      dataSource={selectedTemplate.payload.objects}
                      renderItem={(item) => (
                        <List.Item key={item.id}>
                          <List.Item.Meta title={item.name} description={item.summary ?? item.description} />
                        </List.Item>
                      )}
                    />
                  </Card>

                  <Card size="small" title="流程与约束" style={{ borderRadius: 16 }}>
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <List
                        size="small"
                        dataSource={selectedTemplate.payload.processes}
                        renderItem={(item) => (
                          <List.Item key={item.id}>
                            <List.Item.Meta title={item.name} description={item.description} />
                          </List.Item>
                        )}
                      />
                      <Space wrap>
                        {selectedTemplate.payload.non_functional_constraints.map((item) => (
                          <Tag key={item.id} color="gold">
                            {item.name}
                          </Tag>
                        ))}
                      </Space>
                    </Space>
                  </Card>

                  <Space wrap>
                    <Button type="primary" size="large" loading={submitting} onClick={() => void handleSubmit()}>
                      提交需求规格说明
                    </Button>
                    <Link to="/xx-p3">
                      <Button size="large">查看 XX-P3</Button>
                    </Link>
                  </Space>
                </Space>
              ) : null}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
}
