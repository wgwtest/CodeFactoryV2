import { Card, Empty, List, Space, Tag, Typography } from "antd";

import type { P3ReferenceCenter } from "../../lib/api";
import { buildSectionBridges, buildTemplateOutputs, getTemplateDetailModel } from "./p3TemplateDetail";

type P3TemplateDetailWorkspaceProps = {
  referenceCenter: P3ReferenceCenter | null;
  templateId: string | null;
};

export function P3TemplateDetailWorkspace({ referenceCenter, templateId }: P3TemplateDetailWorkspaceProps) {
  if (!referenceCenter) {
    return (
      <Card style={{ borderRadius: 20 }}>
        <Empty description="当前没有可用模板或规范资产" />
      </Card>
    );
  }

  const { template, mappings } = getTemplateDetailModel(referenceCenter, templateId);

  if (!template) {
    return (
      <Card style={{ borderRadius: 20 }}>
        <Empty description="未找到对应模板" />
      </Card>
    );
  }

  const sectionTitles = template.sections.map((section) => section.title);
  const parsedOutputs = buildTemplateOutputs(sectionTitles);

  return (
    <Space direction="vertical" size={16} style={{ display: "flex" }}>
      <Card
        size="small"
        title="模板定位"
        extra={
          <Space wrap>
            <a href={template.official_detail_url} target="_blank" rel="noreferrer">
              官方详情
            </a>
            {template.pdf_url ? (
              <a href={template.pdf_url} target="_blank" rel="noreferrer">
                打开源 PDF
              </a>
            ) : null}
          </Space>
        }
        style={{ borderRadius: 16 }}
      >
        <Space direction="vertical" size={10} style={{ display: "flex" }}>
          <Typography.Text strong>{template.title}</Typography.Text>
          <Space wrap>
            <Tag color="blue">{template.source_doc_id}</Tag>
            <Tag color="geekblue">v{template.version}</Tag>
            <Tag color="cyan">{template.document_type}</Tag>
          </Space>
          <Typography.Text>{template.summary}</Typography.Text>
          <Typography.Text>{template.recommendation}</Typography.Text>
        </Space>
      </Card>

      <Card size="small" title="模板骨架解析" style={{ borderRadius: 16 }}>
        <List
          size="small"
          dataSource={template.sections}
          renderItem={(section, index) => {
            const bridges = buildSectionBridges(referenceCenter, mappings, section.title);
            return (
              <List.Item key={section.section_id}>
                <Space align="start" size={12} style={{ width: "100%" }}>
                  <Tag color="processing" style={{ minWidth: 34, textAlign: "center", marginTop: 2 }}>
                    {index + 1}
                  </Tag>
                  <Space direction="vertical" size={6} style={{ display: "flex", flex: 1 }}>
                    <Typography.Text strong>{section.title}</Typography.Text>
                    <Typography.Text type="secondary">{section.summary}</Typography.Text>
                    {bridges.length > 0 ? (
                      <Space wrap>
                        {bridges.map((bridge) => (
                          <Tag key={`${section.section_id}-${bridge.label}-${bridge.pairText}`}>
                            {bridge.label} · {bridge.pairText}
                          </Tag>
                        ))}
                      </Space>
                    ) : null}
                  </Space>
                </Space>
              </List.Item>
            );
          }}
        />
      </Card>

      <Card size="small" title="编制输出预期" style={{ borderRadius: 16 }}>
        <List
          size="small"
          dataSource={parsedOutputs}
          renderItem={(item) => (
            <List.Item>
              <Typography.Text>{item}</Typography.Text>
            </List.Item>
          )}
        />
      </Card>

      <Card size="small" title="模板-规范映射" style={{ borderRadius: 16 }}>
        {mappings.length === 0 ? (
          <Empty description="当前模板没有映射记录" />
        ) : (
          <List
            dataSource={mappings}
            renderItem={(mapping) => (
              <List.Item key={`${mapping.template_id}-${mapping.doc_id}`}>
                <List.Item.Meta
                  title={
                    <Space wrap>
                      <Tag color="blue">{mapping.doc_id}</Tag>
                      <Typography.Text strong>
                        {referenceCenter.standards.find((standard) => standard.doc_id === mapping.doc_id)?.title ??
                          mapping.doc_id}
                      </Typography.Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4} style={{ display: "flex" }}>
                      <Typography.Text>{mapping.rationale}</Typography.Text>
                      {mapping.section_pairs.map((pair) => (
                        <Typography.Text
                          key={`${mapping.doc_id}-${pair.template_section}-${pair.standard_section}`}
                          type="secondary"
                        >
                          {pair.template_section}
                          {" -> "}
                          {pair.standard_section}
                        </Typography.Text>
                      ))}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </Space>
  );
}
