import { Alert, Button, Card, Col, Form, Input, Row, Select, Space, Tag, Typography } from "antd";
import { useState } from "react";

import type { ToolHubCatalogs, ToolMatchRequestInput, ToolMatchRun } from "../../lib/api";

type P4InputChainWorkspaceProps = {
  catalogs: ToolHubCatalogs;
  activeArchiveId?: string | null;
  running: boolean;
  run: ToolMatchRun | null;
  onRun: (request: ToolMatchRequestInput) => Promise<void>;
};

type MatchFormValues = {
  scenario_text: string;
  target_stage: string;
  required_input_types: string[];
  expected_output_types: string[];
  preferred_tags: string[];
};

export function P4InputChainWorkspace({
  catalogs,
  activeArchiveId,
  running,
  run,
  onRun,
}: P4InputChainWorkspaceProps) {
  const [form] = Form.useForm<MatchFormValues>();
  const [error, setError] = useState<string | null>(null);

  async function handleFinish(values: MatchFormValues) {
    try {
      setError(null);
      await onRun({
        scenario_text: values.scenario_text,
        target_stage: values.target_stage,
        required_input_types: values.required_input_types ?? [],
        expected_output_types: values.expected_output_types ?? [],
        preferred_tags: values.preferred_tags ?? [],
        knowledge_context: {
          archive_id: activeArchiveId ?? null,
          entity_ids: [],
          process_ids: [],
          snapshot_version: "v1",
        },
      });
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "运行匹配失败");
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Card title="输入工具链" style={{ borderRadius: 18 }}>
          {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} /> : null}
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              target_stage: "modeling",
              required_input_types: ["process_list"],
              expected_output_types: ["validation_report"],
              preferred_tags: ["capability:process-analysis"],
            }}
            onFinish={(values) => void handleFinish(values)}
          >
            <Form.Item label="输入场景" name="scenario_text" rules={[{ required: true, message: "请输入场景描述" }]}>
              <Input.TextArea aria-label="输入场景" rows={5} placeholder="描述当前任务场景、希望得到的工具能力和验证目标" />
            </Form.Item>
            <Form.Item label="目标阶段" name="target_stage">
              <Select
                aria-label="目标阶段"
                options={catalogs.stages.map((item) => ({ label: item.label, value: item.id }))}
              />
            </Form.Item>
            <Form.Item label="需要的输入类型" name="required_input_types">
              <Select
                aria-label="需要的输入类型"
                mode="multiple"
                options={catalogs.input_types.map((item) => ({ label: item.label, value: item.id }))}
              />
            </Form.Item>
            <Form.Item label="期望的输出类型" name="expected_output_types">
              <Select
                aria-label="期望的输出类型"
                mode="multiple"
                options={catalogs.output_types.map((item) => ({ label: item.label, value: item.id }))}
              />
            </Form.Item>
            <Form.Item label="偏好标签" name="preferred_tags">
              <Select
                aria-label="偏好标签"
                mode="tags"
                tokenSeparators={[","]}
                options={[
                  { label: "process-analysis", value: "capability:process-analysis" },
                  { label: "coverage-analysis", value: "capability:coverage-analysis" },
                  { label: "entity-normalization", value: "capability:entity-normalization" },
                ]}
              />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={running}>
              运行匹配
            </Button>
          </Form>
        </Card>
      </Col>

      <Col xs={24} xl={14}>
        <Card title="匹配结果" style={{ borderRadius: 18 }}>
          {run ? (
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <Alert type="info" showIcon message={run.context_summary} />
              {run.candidates.map((candidate) => (
                <Card key={candidate.tool_id} size="small" style={{ borderRadius: 14, background: "#f8fafc" }}>
                  <Space direction="vertical" size={10} style={{ display: "flex" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                      <Typography.Title level={5} style={{ margin: 0 }}>
                        {candidate.name}
                      </Typography.Title>
                      <Tag color="blue">得分 {candidate.match_score}</Tag>
                    </div>
                    <div>
                      {candidate.matched_dimensions.map((item) => (
                        <Tag key={item} color="cyan">
                          {item}
                        </Tag>
                      ))}
                      <Tag color={candidate.verification_status === "verified" ? "green" : "gold"}>
                        {candidate.verification_status}
                      </Tag>
                    </div>
                    <Typography.Text strong>命中原因</Typography.Text>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {candidate.reasons.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                    {candidate.gaps.length > 0 ? (
                      <>
                        <Typography.Text strong>缺口</Typography.Text>
                        <ul style={{ margin: 0, paddingLeft: 18 }}>
                          {candidate.gaps.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                  </Space>
                </Card>
              ))}
            </Space>
          ) : (
            <Typography.Text type="secondary">运行一次匹配后，这里会展示候选工具、命中解释和缺口。</Typography.Text>
          )}
        </Card>
      </Col>
    </Row>
  );
}
