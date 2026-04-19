import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Empty, Input, Space, Tag, Typography } from "antd";

import type { ToolDeliveryManifest } from "../../lib/api";
import { getToolDeliveryManifest } from "../../lib/toolHub";

type P5DeliveryManifestPanelProps = {
  initialToolId?: string;
};

export function P5DeliveryManifestPanel({ initialToolId = "" }: P5DeliveryManifestPanelProps) {
  const [toolId, setToolId] = useState(initialToolId);
  const [manifest, setManifest] = useState<ToolDeliveryManifest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleQuery(targetToolId = toolId) {
    if (!targetToolId.trim()) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await getToolDeliveryManifest(targetToolId.trim());
      setManifest(response.data);
      setToolId(response.data.tool_id);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "查询交付清单失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialToolId) {
      void handleQuery(initialToolId);
    }
  }, [initialToolId]);

  return (
    <Card id="xx-p5-delivery-manifest" title="交付清单" style={{ borderRadius: 20 }}>
      <Space direction="vertical" size={16} style={{ display: "flex" }}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            id="xx-p5-delivery-manifest-tool-id"
            placeholder="输入 tool_id"
            value={toolId}
            onChange={(event) => setToolId(event.target.value)}
          />
          <Button id="xx-p5-delivery-manifest-query" type="primary" loading={loading} onClick={() => void handleQuery()}>
            查询交付清单
          </Button>
        </Space.Compact>

        {error ? <Alert id="xx-p5-delivery-manifest-error" type="error" showIcon message={error} /> : null}

        {manifest ? (
          <>
            <Descriptions id="xx-p5-delivery-manifest-meta" bordered size="small" column={2}>
              <Descriptions.Item label="工具">{manifest.tool_name}</Descriptions.Item>
              <Descriptions.Item label="接入方式">{manifest.integration_mode}</Descriptions.Item>
              <Descriptions.Item label="依赖策略">{manifest.dependency_policy}</Descriptions.Item>
              <Descriptions.Item label="导入路径">{manifest.import_specifier}</Descriptions.Item>
              <Descriptions.Item label="样例宿主">{manifest.example_host_path}</Descriptions.Item>
              <Descriptions.Item label="manifest">{manifest.manifest_path}</Descriptions.Item>
            </Descriptions>

            <Typography.Paragraph id="xx-p5-delivery-manifest-import" code style={{ margin: 0 }}>
              import {'{ QueryTableWidget }'} from "{manifest.import_specifier}";
            </Typography.Paragraph>

            <div id="xx-p5-delivery-manifest-deps" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {manifest.runtime_dependencies.map((item) => (
                <Tag key={item} color="blue">
                  {item}
                </Tag>
              ))}
            </div>
          </>
        ) : (
          <Empty description="当前没有交付清单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Space>
    </Card>
  );
}
