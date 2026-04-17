import { useEffect, useState } from "react";
import { Alert, Button, Card, Space, Spin, Tag, Typography } from "antd";
import { Link, useParams } from "react-router-dom";

import { P3TemplateDetailWorkspace } from "../components/p3/P3TemplateDetailWorkspace";
import type { P3ReferenceCenter } from "../lib/api";
import { getSoftwareDesignReferenceCenter } from "../lib/softwareDesign";

export function P3TemplateDetailPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const [referenceCenter, setReferenceCenter] = useState<P3ReferenceCenter | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadReferenceCenter() {
      try {
        setLoading(true);
        const response = await getSoftwareDesignReferenceCenter();
        if (!active) {
          return;
        }
        setReferenceCenter(response.data);
        setError(null);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载模板细节失败");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadReferenceCenter();

    return () => {
      active = false;
    };
  }, []);

  if (loading && !referenceCenter) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 40px" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto" }}>
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Card
            style={{
              borderRadius: 20,
              border: "1px solid #d0d7de",
              background: "linear-gradient(135deg, #0f172a 0%, #1d4ed8 52%, #155e75 100%)",
              boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
            }}
            styles={{ body: { padding: 24 } }}
          >
            <Space direction="vertical" size={14} style={{ display: "flex" }}>
              <Space wrap>
                <Link to="/xx-p3">
                  <Button>返回 P3 总台</Button>
                </Link>
                <Tag color="processing">模板细节</Tag>
              </Space>
              <div>
                <Typography.Title level={3} style={{ color: "#ffffff", margin: 0 }}>
                  软件设计说明模板细节
                </Typography.Title>
                <Typography.Paragraph style={{ color: "rgba(255,255,255,0.82)", margin: "8px 0 0" }}>
                  独立页面承载模板骨架解析、编制输出预期和模板-规范映射，避免挤压 `/xx-p3` 主页面布局。
                </Typography.Paragraph>
                {templateId ? (
                  <Typography.Text style={{ color: "rgba(255,255,255,0.74)" }}>模板标识：{templateId}</Typography.Text>
                ) : null}
              </div>
            </Space>
          </Card>

          {error ? <Alert type="error" showIcon message={error} /> : null}
          <P3TemplateDetailWorkspace referenceCenter={referenceCenter} templateId={templateId ?? null} />
        </Space>
      </div>
    </div>
  );
}
