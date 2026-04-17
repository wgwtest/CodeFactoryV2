import { Button, Card, Empty, Input, List, Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";

import type { P3ReferenceCenter, P3StandardSearchResult } from "../../lib/api";
import { getTemplateDetailModel } from "./p3TemplateDetail";

type P3TemplateCenterWorkspaceProps = {
  referenceCenter: P3ReferenceCenter | null;
  searchQuery: string;
  searchResults: P3StandardSearchResult[];
  onSearchQueryChange: (query: string) => void;
  onSearch: () => void | Promise<void>;
};

export function P3TemplateCenterWorkspace({
  referenceCenter,
  searchQuery,
  searchResults,
  onSearchQueryChange,
  onSearch,
}: P3TemplateCenterWorkspaceProps) {
  const navigate = useNavigate();

  if (!referenceCenter) {
    return (
      <Card title="模板与规范中心" style={{ borderRadius: 18 }}>
        <Empty description="当前没有可用模板或规范资产" />
      </Card>
    );
  }

  const visibleResults = searchResults.length > 0 ? searchResults : [];

  return (
    <Card
      title="模板与规范中心"
      extra={<Tag color="blue">P3.1 基础能力</Tag>}
      style={{ borderRadius: 18 }}
      styles={{ body: { padding: 20 } }}
    >
      <Space direction="vertical" size={20} style={{ display: "flex" }}>
        <Card
          size="small"
          title="模板清单"
          extra={<Tag color="processing">主页面仅保留摘要入口</Tag>}
          style={{
            borderRadius: 16,
            background: "linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%)",
          }}
        >
          <List
            locale={{ emptyText: "当前没有可用模板" }}
            dataSource={referenceCenter.templates}
            renderItem={(template) => {
              const { mappings } = getTemplateDetailModel(referenceCenter, template.template_id);
              return (
                <List.Item key={template.template_id} style={{ paddingInline: 0 }}>
                  <Card size="small" style={{ width: "100%", borderRadius: 14 }}>
                    <Space direction="vertical" size={10} style={{ display: "flex" }}>
                      <Space direction="vertical" size={2}>
                        <Typography.Text strong>{template.title}</Typography.Text>
                        <Space wrap>
                          <Tag>{template.source_doc_id}</Tag>
                          <Tag color="geekblue">v{template.version}</Tag>
                          <Tag color="cyan">{template.document_type}</Tag>
                          <Tag color="purple">章节 {template.sections.length}</Tag>
                          <Tag color="gold">映射 {mappings.length}</Tag>
                        </Space>
                      </Space>

                      <Typography.Text type="secondary">{template.summary}</Typography.Text>
                      <Typography.Text>{template.recommendation}</Typography.Text>

                      {template.sections.length > 0 ? (
                        <Space wrap>
                          {template.sections.slice(0, 3).map((section) => (
                            <Tag key={section.section_id}>{section.title}</Tag>
                          ))}
                          {template.sections.length > 3 ? <Tag>还有 {template.sections.length - 3} 节</Tag> : null}
                        </Space>
                      ) : null}

                      <Space wrap>
                        <Button type="primary" size="small" onClick={() => navigate(`/xx-p3/templates/${template.template_id}`)}>
                          细节
                        </Button>
                        <a href={template.official_detail_url} target="_blank" rel="noreferrer">
                          官方详情
                        </a>
                        {template.pdf_url ? (
                          <a href={template.pdf_url} target="_blank" rel="noreferrer">
                            打开源 PDF
                          </a>
                        ) : null}
                      </Space>
                    </Space>
                  </Card>
                </List.Item>
              );
            }}
          />
        </Card>

        <Card size="small" title="规范检索" style={{ borderRadius: 16 }}>
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Space.Compact style={{ width: "100%" }}>
              <Input
                value={searchQuery}
                onChange={(event) => onSearchQueryChange(event.target.value)}
                placeholder="输入 design description、traceability、platform 等关键词"
              />
              <Button type="primary" onClick={() => void onSearch()}>
                检索规范
              </Button>
            </Space.Compact>

            <List
              locale={{ emptyText: "当前没有检索结果" }}
              dataSource={visibleResults}
              renderItem={(item) => (
                <List.Item key={`${item.doc_id}-${item.matched_section}`}>
                  <List.Item.Meta
                    title={
                      <Space wrap>
                        <Tag color="processing">{item.doc_id}</Tag>
                        <Typography.Text strong>{item.title}</Typography.Text>
                        <Tag>{item.matched_section}</Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={2} style={{ display: "flex" }}>
                        <Typography.Text>{item.excerpt}</Typography.Text>
                        <a href={item.official_detail_url} target="_blank" rel="noreferrer">
                          打开官方详情
                        </a>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Space>
        </Card>
      </Space>
    </Card>
  );
}
