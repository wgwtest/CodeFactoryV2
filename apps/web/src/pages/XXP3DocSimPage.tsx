import { useEffect, useState } from "react";
import { Alert, Button, Card, Empty, Space, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import type { P5DesignInputSource } from "../lib/api";
import { createSoftwareBuildDesignInputSim, getSoftwareBuildDesignInputs } from "../lib/softwareBuild";

const presetPayload = {
  application_name: "基于地理信息系统的通视分析软件",
  requirement_spec_id: "spec-gis-los-analysis-001",
  baseline_id: "baseline-gis-los-analysis-001",
  notes: "基于地理信息系统的通视分析软件冻结设计样例",
  module_specs: [
    {
      module_id: "module-workspace",
      name: "构建工作台",
      objective: "渲染通视分析软件的 P5 工作台壳层与核心区块。",
      inputs: ["delivery_order"],
      outputs: ["workspace_ui"],
      constraints: ["禁止复用门户式顶部导航"],
      recommended_tools: ["ui_shell"],
    },
    {
      module_id: "module-runtime",
      name: "构建运行监控",
      objective: "输出通视分析软件构建运行阶段、日志和状态标签。",
      inputs: ["attempt_manifest"],
      outputs: ["runtime_snapshot"],
      constraints: ["日志区必须可回看"],
      recommended_tools: ["runtime_board"],
    },
    {
      module_id: "module-feedback",
      name: "缺口回流",
      objective: "沉淀通视分析软件装配缺口、批阅意见和回流任务。",
      inputs: ["gap_list"],
      outputs: ["feedback_task"],
      constraints: ["缺口回流结论必须保留可审阅记录"],
      recommended_tools: ["feedback_console"],
    },
  ],
} as const;

const shellStyle = {
  minHeight: "100vh",
  background: "#eef1f4",
  padding: "24px 24px 32px",
};

const cardStyle = {
  borderRadius: 24,
  border: "1px solid rgba(116, 126, 138, 0.18)",
  background: "rgba(255, 255, 255, 0.92)",
  boxShadow: "0 18px 40px rgba(36, 45, 56, 0.08)",
};

export function XXP3DocSimPage() {
  const [items, setItems] = useState<P5DesignInputSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadItems() {
    try {
      setLoading(true);
      setError(null);
      const response = await getSoftwareBuildDesignInputs();
      setItems(response.data.data.items.filter((item) => item.source_kind === "xx_p3_doc_sim"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载设计模拟输出失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadItems();
  }, []);

  async function handleCreate() {
    try {
      setCreating(true);
      setError(null);
      const response = await createSoftwareBuildDesignInputSim({ ...presetPayload });
      setNotice(`已生成设计模拟输出 ${response.data.design_input_id}`);
      await loadItems();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "生成设计模拟输出失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={shellStyle}>
      <div style={{ maxWidth: 1260, margin: "0 auto" }}>
        <Card style={{ ...cardStyle, marginBottom: 18 }}>
          <Space direction="vertical" size={10} style={{ display: "flex" }}>
            <Space align="center" wrap>
              <Tag color="cyan">XX / P3 / DOC / SIM</Tag>
              <Link to="/build">返回 P5 工作台</Link>
            </Space>
            <Typography.Title level={2} style={{ margin: 0 }}>
              P3 文档模拟输出台
            </Typography.Title>
            <Typography.Paragraph style={{ margin: 0, color: "#5a6472", maxWidth: 840 }}>
              这里不做 P3 全流程，只负责生成“基于地理信息系统的通视分析软件”的冻结设计样例。生成完成后停留在当前页面，供你检查输出结果，再决定是否切换到 P5 继续后续操作。
            </Typography.Paragraph>
            <Space wrap>
              <Button type="primary" onClick={() => void handleCreate()} loading={creating}>
                生成设计模拟输出
              </Button>
              <Button onClick={() => void loadItems()} loading={loading}>
                刷新列表
              </Button>
            </Space>
          </Space>
        </Card>

        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
        {notice ? <Alert type="success" showIcon message={notice} style={{ marginBottom: 16 }} /> : null}

        <Card title="已生成的设计模拟输出" style={cardStyle} loading={loading}>
          {items.length === 0 ? (
            <Empty description="当前还没有 P3 文档模拟输出。" />
          ) : (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              {items.map((item) => (
                <div
                  key={item.design_input_id}
                  style={{
                    borderRadius: 18,
                    padding: 16,
                    border: "1px solid rgba(116, 126, 138, 0.18)",
                    background: "rgba(246, 248, 250, 0.9)",
                  }}
                >
                  <Space direction="vertical" size={6} style={{ display: "flex" }}>
                    <Space wrap>
                      <Typography.Text strong>{item.application_name}</Typography.Text>
                      <Tag>{item.design_input_id}</Tag>
                    </Space>
                    <Typography.Text type="secondary">
                      requirement: {item.requirement_spec_id} / baseline: {item.baseline_id}
                    </Typography.Text>
                    <Typography.Text type="secondary">模块: {item.module_names.join(" / ")}</Typography.Text>
                  </Space>
                </div>
              ))}
            </Space>
          )}
        </Card>
      </div>
    </div>
  );
}
