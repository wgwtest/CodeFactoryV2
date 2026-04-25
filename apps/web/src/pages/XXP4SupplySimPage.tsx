import { useEffect, useState } from "react";
import { Alert, Button, Card, Empty, Space, Tag, Typography } from "antd";
import { Link, useNavigate } from "react-router-dom";

import type { P5SupplyInputSource } from "../lib/api";
import { createSoftwareBuildSupplyInputSim, getSoftwareBuildSupplyInputs } from "../lib/softwareBuild";

const presetPayload = {
  snapshot_name: "通视分析软件供给样例快照",
  notes: "供通视分析软件样例命中使用",
  tools: [
    {
      tool_id: "tool-ui-shell",
      tool_name: "UI Shell",
      tool_slug: "ui-shell",
      verification_status: "verified",
      keywords: ["ui_shell", "workspace", "frontend"],
    },
    {
      tool_id: "tool-runtime-board",
      tool_name: "Runtime Board",
      tool_slug: "runtime-board",
      verification_status: "verified",
      keywords: ["runtime_board", "monitor", "log"],
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

export function XXP4SupplySimPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<P5SupplyInputSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadItems() {
    try {
      setLoading(true);
      setError(null);
      const response = await getSoftwareBuildSupplyInputs();
      setItems(response.data.data.items.filter((item) => item.source_kind === "xx_p4_supply_sim"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载供给模拟输出失败");
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
      await createSoftwareBuildSupplyInputSim({ ...presetPayload });
      navigate("/build");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "生成供给模拟输出失败");
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
              <Tag color="geekblue">XX / P4 / SUPPLY / SIM</Tag>
              <Link to="/build">返回 P5 工作台</Link>
            </Space>
            <Typography.Title level={2} style={{ margin: 0 }}>
              P4 供给模拟输出台
            </Typography.Title>
            <Typography.Paragraph style={{ margin: 0, color: "#5a6472", maxWidth: 840 }}>
              这里生成“基于地理信息系统的通视分析软件”可消费的供给快照样例。供给对象保持已审定资产快照形态，并在生成后立即返回 P5 工作台，让当前主单直接看到新的供给候选。
            </Typography.Paragraph>
            <Space wrap>
              <Button type="primary" onClick={() => void handleCreate()} loading={creating}>
                生成供给输出并返回 P5
              </Button>
              <Button onClick={() => void loadItems()} loading={loading}>
                刷新列表
              </Button>
            </Space>
          </Space>
        </Card>

        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
        {notice ? <Alert type="success" showIcon message={notice} style={{ marginBottom: 16 }} /> : null}

        <Card title="已生成的供给模拟输出" style={cardStyle} loading={loading}>
          {items.length === 0 ? (
            <Empty description="当前还没有 P4 供给模拟输出。" />
          ) : (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              {items.map((item) => (
                <div
                  key={item.supply_input_id}
                  style={{
                    borderRadius: 18,
                    padding: 16,
                    border: "1px solid rgba(116, 126, 138, 0.18)",
                    background: "rgba(246, 248, 250, 0.9)",
                  }}
                >
                  <Space direction="vertical" size={6} style={{ display: "flex" }}>
                    <Space wrap>
                      <Typography.Text strong>{item.snapshot_name}</Typography.Text>
                      <Tag>{item.supply_input_id}</Tag>
                    </Space>
                    <Typography.Text type="secondary">工具数: {item.tool_count}</Typography.Text>
                    <Typography.Text type="secondary">工具: {item.tool_names.join(" / ")}</Typography.Text>
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
