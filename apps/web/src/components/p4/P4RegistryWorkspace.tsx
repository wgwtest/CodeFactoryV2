import { Button, Card, Form, Input, Modal, Select, Space, Table, Tag } from "antd";
import { useEffect, useState } from "react";

import type { ToolDefinition, ToolDefinitionWriteInput, ToolHubCatalogs } from "../../lib/api";

type P4RegistryWorkspaceProps = {
  tools: ToolDefinition[];
  catalogs: ToolHubCatalogs;
  saving: boolean;
  onCreate: (payload: ToolDefinitionWriteInput) => Promise<void>;
  onUpdate: (toolId: string, payload: ToolDefinitionWriteInput) => Promise<void>;
};

type RegistryFormValues = {
  name: string;
  slug: string;
  status: ToolDefinition["status"];
  summary: string;
  problem_statement: string;
  primary_domain_id: string;
  tool_form_id: string;
  runtime_platform_ids: string[];
  lifecycle_stage_ids: string[];
  input_types: string[];
  output_types: string[];
  supported_sources: string[];
};

function buildFormValues(tool?: ToolDefinition | null): RegistryFormValues {
  if (!tool) {
    return {
      name: "",
      slug: "",
      status: "draft",
      summary: "",
      problem_statement: "",
      primary_domain_id: "",
      tool_form_id: "",
      runtime_platform_ids: [],
      lifecycle_stage_ids: [],
      input_types: [],
      output_types: [],
      supported_sources: ["manual_input"],
    };
  }
  return {
    name: tool.name,
    slug: tool.slug,
    status: tool.status,
    summary: tool.summary,
    problem_statement: tool.problem_statement,
    primary_domain_id: tool.primary_domain_id,
    tool_form_id: tool.tool_form_id,
    runtime_platform_ids: tool.runtime_platform_ids,
    lifecycle_stage_ids: tool.lifecycle_stage_ids,
    input_types: tool.input_types,
    output_types: tool.output_types,
    supported_sources: tool.supported_sources,
  };
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-\u4e00-\u9fa5]/g, "")
    .replace(/-+/g, "-");
}

function retainCustomTags(tags: string[]) {
  const managedPrefixes = ["domain:", "form:", "runtime:", "lifecycle:", "input:", "output:", "stage:", "capability:"];
  return tags.filter((tag) => tag.startsWith("risk:") || managedPrefixes.every((prefix) => !tag.startsWith(prefix)));
}

export function P4RegistryWorkspace({
  tools,
  catalogs,
  saving,
  onCreate,
  onUpdate,
}: P4RegistryWorkspaceProps) {
  const [form] = Form.useForm<RegistryFormValues>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTool, setEditingTool] = useState<ToolDefinition | null>(null);

  useEffect(() => {
    form.setFieldsValue(buildFormValues(editingTool));
  }, [editingTool, form]);

  async function handleFinish(values: RegistryFormValues) {
    const derivedTags = [
      `domain:${values.primary_domain_id}`,
      `form:${values.tool_form_id}`,
      ...values.runtime_platform_ids.map((item) => `runtime:${item}`),
      ...values.lifecycle_stage_ids.map((item) => `lifecycle:${item}`),
      ...values.input_types.map((item) => `input:${item}`),
      ...values.output_types.map((item) => `output:${item}`),
    ];
    const payload: ToolDefinitionWriteInput = {
      ...values,
      slug: values.slug || slugify(values.name),
      tags: derivedTags,
      usage_notes: "",
      keywords: values.name ? [values.name.slice(0, 2)] : [],
      verification: {
        status: "unverified",
        last_verified_result: "",
        sample_case_ids: [],
      },
    };

    if (editingTool) {
      await onUpdate(editingTool.tool_id, {
        ...payload,
        tags: [...payload.tags, ...retainCustomTags(editingTool.tags)],
        usage_notes: editingTool.usage_notes,
        keywords: editingTool.keywords,
        verification: editingTool.verification,
      });
    } else {
      await onCreate(payload);
    }

    setModalOpen(false);
    setEditingTool(null);
    form.resetFields();
  }

  return (
    <>
      <Card
        title="工具仓库"
        extra={
          <Button
            type="primary"
            onClick={() => {
              setEditingTool(null);
              form.setFieldsValue(buildFormValues(null));
              setModalOpen(true);
            }}
          >
            新建工具
          </Button>
        }
        style={{ borderRadius: 18 }}
      >
        <Table
          rowKey="tool_id"
          dataSource={tools}
          pagination={false}
          columns={[
            {
              title: "工具",
              dataIndex: "name",
              render: (_, record) => (
                <Space direction="vertical" size={4}>
                  <strong>{record.name}</strong>
                  <span style={{ color: "#64748b" }}>{record.summary}</span>
                </Space>
              ),
            },
            {
              title: "状态",
              dataIndex: "status",
              render: (value) => (
                <Tag color={value === "active" ? "green" : value === "archived" ? "default" : "gold"}>{value}</Tag>
              ),
            },
            {
              title: "业务域",
              dataIndex: "primary_domain_id",
              render: (value) => catalogs.domains.find((item) => item.id === value)?.label ?? value,
            },
            {
              title: "形态",
              dataIndex: "tool_form_id",
              render: (value) => catalogs.tool_forms.find((item) => item.id === value)?.label ?? value,
            },
            {
              title: "运行平台",
              dataIndex: "runtime_platform_ids",
              render: (value: string[]) =>
                value
                  .map((item) => catalogs.runtime_platforms.find((platform) => platform.id === item)?.label ?? item)
                  .join(" / "),
            },
            {
              title: "验证",
              dataIndex: ["verification", "status"],
              render: (value) => <Tag color={value === "verified" ? "green" : "blue"}>{value}</Tag>,
            },
            {
              title: "操作",
              key: "actions",
              render: (_, record) => (
                <Space>
                  <Button
                    type="link"
                    onClick={() => {
                      setEditingTool(record);
                      form.setFieldsValue(buildFormValues(record));
                      setModalOpen(true);
                    }}
                  >
                    编辑
                  </Button>
                  {record.status !== "archived" ? (
                    <Button
                      type="link"
                      danger
                      onClick={() =>
                        void onUpdate(record.tool_id, {
                          ...record,
                          status: "archived",
                        })
                      }
                    >
                      归档
                    </Button>
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editingTool ? "编辑工具" : "新建工具"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        destroyOnHidden
        forceRender
      >
        <Form form={form} layout="vertical" onFinish={(values) => void handleFinish(values)} initialValues={buildFormValues(null)}>
          <Form.Item label="工具名称" name="name" rules={[{ required: true, message: "请输入工具名称" }]}>
            <Input aria-label="工具名称" />
          </Form.Item>
          <Form.Item label="Slug" name="slug">
            <Input aria-label="Slug" />
          </Form.Item>
          <Form.Item label="摘要" name="summary" rules={[{ required: true, message: "请输入摘要" }]}>
            <Input.TextArea aria-label="摘要" rows={3} />
          </Form.Item>
          <Form.Item label="问题定义" name="problem_statement">
            <Input.TextArea aria-label="问题定义" rows={2} />
          </Form.Item>
          <Form.Item label="主业务域" name="primary_domain_id" rules={[{ required: true, message: "请选择主业务域" }]}>
            <Select aria-label="主业务域" options={catalogs.domains.map((item) => ({ label: item.label, value: item.id }))} />
          </Form.Item>
          <Form.Item label="工具形态" name="tool_form_id" rules={[{ required: true, message: "请选择工具形态" }]}>
            <Select aria-label="工具形态" options={catalogs.tool_forms.map((item) => ({ label: item.label, value: item.id }))} />
          </Form.Item>
          <Form.Item label="运行平台" name="runtime_platform_ids">
            <Select
              aria-label="运行平台"
              mode="multiple"
              options={catalogs.runtime_platforms.map((item) => ({ label: item.label, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="适用生命周期环节" name="lifecycle_stage_ids">
            <Select
              aria-label="适用生命周期环节"
              mode="multiple"
              options={catalogs.lifecycle_stages.map((item) => ({ label: item.label, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="输入类型" name="input_types">
            <Select
              aria-label="输入类型"
              mode="multiple"
              options={catalogs.input_types.map((item) => ({ label: item.label, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="输出类型" name="output_types">
            <Select
              aria-label="输出类型"
              mode="multiple"
              options={catalogs.output_types.map((item) => ({ label: item.label, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="支持来源" name="supported_sources">
            <Select
              aria-label="支持来源"
              mode="multiple"
              options={catalogs.supported_sources.map((item) => ({ label: item.label, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              aria-label="状态"
              options={[
                { label: "草稿", value: "draft" },
                { label: "激活", value: "active" },
                { label: "归档", value: "archived" },
              ]}
            />
          </Form.Item>
          <Space>
            <Button onClick={() => setModalOpen(false)}>取消</Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存工具
            </Button>
          </Space>
        </Form>
      </Modal>
    </>
  );
}
