import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Empty, Input, List, Modal, Space, Tabs, Tag, Typography } from "antd";

import type { RequirementAuthoringTemplate } from "../lib/api";
import {
  activateRequirementAuthoringTemplate,
  createRequirementAuthoringTemplate,
  getRequirementAuthoringTemplates,
} from "../lib/requirementAuthoring";
import "./RequirementAuthoringPage.css";

const { Text, Title } = Typography;

export function RequirementAuthoringAdminPage() {
  const [templates, setTemplates] = useState<RequirementAuthoringTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [templateCode, setTemplateCode] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const response = await getRequirementAuthoringTemplates();
        if (cancelled) {
          return;
        }
        setTemplates(response.data);
        setSelectedTemplateId(response.data[0]?.template_id ?? null);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 P2 配置失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.template_id === selectedTemplateId) ?? templates[0] ?? null,
    [selectedTemplateId, templates],
  );

  async function handleCreateTemplate() {
    const normalizedCode = templateCode.trim();
    const normalizedName = templateName.trim();
    if (!normalizedCode || !normalizedName) {
      return;
    }

    try {
      setSaving(true);
      const response = await createRequirementAuthoringTemplate({
        template_code: normalizedCode,
        name: normalizedName,
        status: "draft",
        description: "配置台新增的可替换需求规格模板。",
      });
      setTemplates((current) => [
        ...current.filter((item) => item.template_id !== response.data.template_id),
        response.data,
      ]);
      setSelectedTemplateId(response.data.template_id);
      setTemplateCode("");
      setTemplateName("");
      setModalOpen(false);
      setError(null);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "新增模板失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleActivate(template: RequirementAuthoringTemplate) {
    try {
      setSaving(true);
      const response = await activateRequirementAuthoringTemplate(template.template_id);
      setTemplates((current) =>
        current.map((item) => (item.template_id === response.data.template_id ? response.data : item)),
      );
      setSelectedTemplateId(response.data.template_id);
      setError(null);
    } catch (activateError) {
      setError(activateError instanceof Error ? activateError.message : "启用模板失败");
    } finally {
      setSaving(false);
    }
  }

  const tabItems = [
    {
      key: "templates",
      label: "规格模板",
      children: (
        <TemplatePanel
          templates={templates}
          selectedTemplateId={selectedTemplate?.template_id ?? null}
          saving={saving}
          onSelect={setSelectedTemplateId}
          onActivate={(template) => void handleActivate(template)}
          onCreate={() => setModalOpen(true)}
        />
      ),
    },
    {
      key: "fields",
      label: "表单字段",
      children: <ConfigPreview title="表单字段" items={selectedTemplate?.form_groups.flatMap((group) => group.fields.map((field) => `${group.title} / ${field.label}`)) ?? []} />,
    },
    {
      key: "mappings",
      label: "字段映射",
      children: <ConfigPreview title="字段映射" items={selectedTemplate?.field_mappings.map((item) => `${item.field_key ?? ""} -> ${item.structured_path ?? ""}`) ?? []} />,
    },
    {
      key: "questions",
      label: "问答策略",
      children: <ConfigPreview title="问答策略" items={(selectedTemplate?.questionnaire_policy.quick_inputs ?? []).map((item) => `短指令：${item}`)} />,
    },
    {
      key: "gaps",
      label: "缺口检查",
      children: <ConfigPreview title="缺口检查" items={((selectedTemplate?.gap_rules.required_fields as string[] | undefined) ?? []).map((item) => `必填字段：${item}`)} />,
    },
    {
      key: "knowledge",
      label: "知识库绑定",
      children: <ConfigPreview title="知识库绑定" items={selectedTemplate?.knowledge_bindings.map((item) => `${item.archive_id} / ${item.label}`) ?? []} />,
    },
    {
      key: "preview",
      label: "测试预览",
      children: <ConfigPreview title="测试预览" items={selectedTemplate ? [`使用 ${selectedTemplate.name} 生成专家工作台预览`, "问答和表单共用同一份标准正文状态"] : []} />,
    },
  ];

  return (
    <div className="requirement-authoring-page">
      <div className="requirement-authoring-header">
        <div>
          <Title level={2} className="requirement-authoring-title">
            P2 配置与模板管理台
          </Title>
          <Text type="secondary">管理规格模板、表单字段、映射、问答策略、缺口检查和知识库绑定。</Text>
        </div>
        <Button aria-label="新增模板" type="primary" onClick={() => setModalOpen(true)}>
          新增模板
        </Button>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} /> : null}

      <div className="requirement-authoring-panel requirement-authoring-input-panel">
        <Tabs items={tabItems} />
        {loading ? <Text type="secondary">正在加载配置...</Text> : null}
      </div>

      <Modal
        title="新增规格模板"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalOpen(false)}>
            取消
          </Button>,
          <Button key="save" aria-label="保存模板" type="primary" loading={saving} onClick={() => void handleCreateTemplate()}>
            保存模板
          </Button>,
        ]}
      >
        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <label>
            <Text>模板编码</Text>
            <Input aria-label="模板编码" value={templateCode} onChange={(event) => setTemplateCode(event.target.value)} />
          </label>
          <label>
            <Text>模板名称</Text>
            <Input aria-label="模板名称" value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
          </label>
        </Space>
      </Modal>
    </div>
  );
}

function TemplatePanel({
  templates,
  selectedTemplateId,
  saving,
  onSelect,
  onActivate,
  onCreate,
}: {
  templates: RequirementAuthoringTemplate[];
  selectedTemplateId: string | null;
  saving: boolean;
  onSelect: (templateId: string) => void;
  onActivate: (template: RequirementAuthoringTemplate) => void;
  onCreate: () => void;
}) {
  if (templates.length === 0) {
    return <Empty description="还没有可用模板" />;
  }

  return (
    <List
      dataSource={templates}
      renderItem={(template) => (
        <List.Item
          key={template.template_id}
          actions={[
            <Button key="select" size="small" onClick={() => onSelect(template.template_id)}>
              查看
            </Button>,
            <Button
              key="activate"
              aria-label={`启用${template.name}`}
              size="small"
              disabled={template.status === "active"}
              loading={saving && selectedTemplateId === template.template_id}
              onClick={() => onActivate(template)}
            >
              启用
            </Button>,
          ]}
        >
          <List.Item.Meta title={template.name} description={`${template.template_code} / ${template.description}`} />
          <Space>
            <Tag color={template.status === "active" ? "green" : "default"}>{template.status}</Tag>
            {selectedTemplateId === template.template_id ? <Tag color="blue">当前查看</Tag> : null}
          </Space>
        </List.Item>
      )}
    />
  );
}

function ConfigPreview({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="requirement-authoring-form-group">
      <Text strong>{title}</Text>
      <div style={{ marginTop: 12 }}>
        {items.length > 0 ? (
          <Space wrap>
            {items.map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </Space>
        ) : (
          <Text type="secondary">当前模板暂无配置项。</Text>
        )}
      </div>
    </div>
  );
}
