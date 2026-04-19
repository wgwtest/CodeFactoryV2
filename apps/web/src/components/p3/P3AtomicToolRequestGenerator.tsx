import { useState } from "react";
import { Alert, Button, Card, Descriptions, Space, Tag, Typography } from "antd";

import type { ToolBuildRun } from "../../lib/api";
import { createFrontendComponentBuildRequest, getBuildRun } from "../../lib/toolHub";

const QUERY_TABLE_WIDGET_REQUEST = {
  requested_by: "p3-sim",
  component_name: "QueryTableWidget",
  scenario_id: "frontend-query-table-widget",
  tool_definition: {
    name: "查询表格元组件",
    slug: "query-table-widget",
    status: "draft" as const,
    summary: "可嵌入宿主项目的查询表格元组件",
    problem_statement: "复用列表筛选、表格渲染和行级操作骨架",
    primary_domain_id: "cross_domain_shared",
    tool_form_id: "frontend_component",
    tool_granularity: "atomic" as const,
    packaging_type: "source_package" as const,
    integration_mode: "import_component" as const,
    dependency_policy: "peer" as const,
    runtime_dependencies: ["react@18", "antd@5"],
    host_constraints: {
      frontend_framework: "react",
      ui_library: "antd",
    },
    runtime_platform_ids: ["web_frontend"],
    lifecycle_stage_ids: ["solution_design"],
    input_types: ["query_params", "column_schema"],
    output_types: ["tsx_component", "delivery_manifest"],
    supported_sources: ["manual_input"],
    tags: [],
    usage_notes: "",
    keywords: ["查询", "表格"],
    verification: {
      status: "unverified" as const,
      last_verified_result: "",
      sample_case_ids: [],
    },
  },
};

export function P3AtomicToolRequestGenerator() {
  const [latestBuildRun, setLatestBuildRun] = useState<ToolBuildRun | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    try {
      setSubmitting(true);
      setError(null);
      const response = await createFrontendComponentBuildRequest(QUERY_TABLE_WIDGET_REQUEST);
      setLatestBuildRun(response.data);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "提交元组件需求失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRefreshBuildRun() {
    if (!latestBuildRun) {
      return;
    }

    try {
      setRefreshing(true);
      setError(null);
      const response = await getBuildRun(latestBuildRun.build_run_id);
      setLatestBuildRun(response.data);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "刷新 build run 失败");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Card id="xx-p3-atomic-tool-request" title="前端元组件需求" style={{ borderRadius: 20 }}>
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
          固定样例：`QueryTableWidget`。这里模拟 P3 把真实前端元组件需求提交给 P4，后续由 P4 生成可交付产物。
        </Typography.Paragraph>

        {error ? <Alert id="xx-p3-atomic-tool-request-error" type="error" showIcon message={error} /> : null}

        <Button id="xx-p3-atomic-tool-request-submit" type="primary" loading={submitting} onClick={() => void handleSubmit()}>
          提交到 P4
        </Button>

        {latestBuildRun ? (
          <>
            <Descriptions id="xx-p3-atomic-tool-request-result" bordered size="small" column={2}>
              <Descriptions.Item label="build_run_id">{latestBuildRun.build_run_id}</Descriptions.Item>
              <Descriptions.Item label="tool_id">{latestBuildRun.tool_id}</Descriptions.Item>
              <Descriptions.Item label="队列">{latestBuildRun.queue_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={latestBuildRun.status === "completed" ? "green" : "blue"}>{latestBuildRun.status}</Tag>
              </Descriptions.Item>
            </Descriptions>

            <Button id="xx-p3-atomic-tool-request-refresh" loading={refreshing} onClick={() => void handleRefreshBuildRun()}>
              刷新 Build Run
            </Button>
          </>
        ) : null}
      </Space>
    </Card>
  );
}
