import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Empty, Input, Space, Tag, Typography } from "antd";

import type { ToolBuildRun, ToolDeliveryManifest } from "../../lib/api";
import { getBuildRun, getToolDeliveryManifest } from "../../lib/toolHub";

type P4RealToolDeliveryWorkspaceProps = {
  initialBuildRunId?: string;
  initialToolId?: string;
};

export function P4RealToolDeliveryWorkspace({
  initialBuildRunId = "",
  initialToolId = "",
}: P4RealToolDeliveryWorkspaceProps) {
  const [buildRunId, setBuildRunId] = useState(initialBuildRunId);
  const [toolId, setToolId] = useState(initialToolId);
  const [buildRun, setBuildRun] = useState<ToolBuildRun | null>(null);
  const [manifest, setManifest] = useState<ToolDeliveryManifest | null>(null);
  const [loadingBuildRun, setLoadingBuildRun] = useState(false);
  const [loadingManifest, setLoadingManifest] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLoadBuildRun(targetBuildRunId = buildRunId) {
    if (!targetBuildRunId.trim()) {
      return;
    }

    try {
      setLoadingBuildRun(true);
      setError(null);
      const response = await getBuildRun(targetBuildRunId.trim());
      setBuildRun(response.data);
      setBuildRunId(response.data.build_run_id);
      setToolId(response.data.tool_id);
      if (response.data.tool_id) {
        await handleLoadManifest(response.data.tool_id);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "查询 build run 失败");
    } finally {
      setLoadingBuildRun(false);
    }
  }

  async function handleLoadManifest(targetToolId = toolId) {
    if (!targetToolId.trim()) {
      return;
    }

    try {
      setLoadingManifest(true);
      setError(null);
      const response = await getToolDeliveryManifest(targetToolId.trim());
      setManifest(response.data);
      setToolId(response.data.tool_id);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "查询 delivery manifest 失败");
    } finally {
      setLoadingManifest(false);
    }
  }

  useEffect(() => {
    if (initialToolId) {
      void handleLoadManifest(initialToolId);
    }
  }, [initialToolId]);

  useEffect(() => {
    if (initialBuildRunId) {
      void handleLoadBuildRun(initialBuildRunId);
    }
  }, [initialBuildRunId]);

  return (
    <Card id="xx-p4-real-tool-delivery" title="真实工具交付" className="xx-p4-panel-card">
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
          这里查看真实前端元组件的 build run、交付清单和接入说明。默认样例为 `QueryTableWidget`。
        </Typography.Paragraph>

        {error ? <Alert id="xx-p4-real-tool-delivery-error" type="error" showIcon message={error} /> : null}

        <div id="xx-p4-real-tool-delivery-build-run-query">
          <Typography.Text strong>Build Run 查询</Typography.Text>
          <Space.Compact style={{ width: "100%", marginTop: 8 }}>
            <Input
              id="xx-p4-real-tool-delivery-build-run-input"
              placeholder="输入 build_run_id"
              value={buildRunId}
              onChange={(event) => setBuildRunId(event.target.value)}
            />
            <Button loading={loadingBuildRun} onClick={() => void handleLoadBuildRun()}>
              查询 Build Run
            </Button>
          </Space.Compact>
        </div>

        <div id="xx-p4-real-tool-delivery-manifest-query">
          <Typography.Text strong>交付清单查询</Typography.Text>
          <Space.Compact style={{ width: "100%", marginTop: 8 }}>
            <Input
              id="xx-p4-real-tool-delivery-tool-input"
              placeholder="输入 tool_id"
              value={toolId}
              onChange={(event) => setToolId(event.target.value)}
            />
            <Button type="primary" loading={loadingManifest} onClick={() => void handleLoadManifest()}>
              查询交付清单
            </Button>
          </Space.Compact>
        </div>

        {buildRun ? (
          <Descriptions id="xx-p4-real-tool-delivery-build-run-meta" bordered size="small" column={2}>
            <Descriptions.Item label="build_run_id">{buildRun.build_run_id}</Descriptions.Item>
            <Descriptions.Item label="tool_id">{buildRun.tool_id}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={buildRun.status === "completed" ? "green" : buildRun.status === "failed" ? "red" : "blue"}>
                {buildRun.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="队列">{buildRun.queue_name}</Descriptions.Item>
          </Descriptions>
        ) : null}

        {manifest ? (
          <div id="xx-p4-real-tool-delivery-manifest-panel" className="xx-p4-real-delivery-result">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="工具">{manifest.tool_name}</Descriptions.Item>
              <Descriptions.Item label="形态">{manifest.tool_form_id}</Descriptions.Item>
              <Descriptions.Item label="打包">{manifest.packaging_type}</Descriptions.Item>
              <Descriptions.Item label="接入方式">{manifest.integration_mode}</Descriptions.Item>
              <Descriptions.Item label="依赖策略">{manifest.dependency_policy}</Descriptions.Item>
              <Descriptions.Item label="导入路径">{manifest.import_specifier}</Descriptions.Item>
              <Descriptions.Item label="样例宿主">{manifest.example_host_path}</Descriptions.Item>
              <Descriptions.Item label="manifest">{manifest.manifest_path}</Descriptions.Item>
            </Descriptions>

            <div id="xx-p4-real-tool-delivery-runtime-deps" style={{ marginTop: 12 }}>
              <Typography.Text strong>运行时依赖</Typography.Text>
              <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                {manifest.runtime_dependencies.map((item) => (
                  <Tag key={item} color="blue">
                    {item}
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div id="xx-p4-real-tool-delivery-empty">
            <Empty description="当前还没有查询到真实交付清单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        )}
      </Space>
    </Card>
  );
}
