import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Input, List, Space, Switch, Tag, Typography } from "antd";

import type { ItemProgressView, ToolDemandItem, ToolDemandSheet } from "../../lib/api";
import { getDemandItem, getDemandItemProgress, getDemandSheet } from "../../lib/toolHub";

function renderLifecycleTag(status: string) {
  if (status === "accepted" || status === "submitted") {
    return <Tag color="blue">{`状态码 ${status}`}</Tag>;
  }
  if (status === "withdrawn") {
    return <Tag color="orange">{`状态码 ${status}`}</Tag>;
  }
  if (status === "rejected") {
    return <Tag color="red">{`状态码 ${status}`}</Tag>;
  }
  if (status === "closed") {
    return <Tag>{`状态码 ${status}`}</Tag>;
  }
  return <Tag color="gold">{`状态码 ${status}`}</Tag>;
}

function renderProcessingTag(status: string) {
  if (status === "matched_existing" || status === "ready_for_fetch" || status === "ready") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "manufacturing_in_progress" || status === "processing" || status === "partially_ready") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderReviewTag(status: string) {
  if (status === "reviewed") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "reviewing") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderDeliveryTag(status: string) {
  if (status === "delivered") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "delivering") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P5DemandQueryPanel() {
  const [sheetId, setSheetId] = useState("");
  const [itemId, setItemId] = useState("");
  const [sheet, setSheet] = useState<ToolDemandSheet | null>(null);
  const [item, setItem] = useState<ToolDemandItem | null>(null);
  const [progress, setProgress] = useState<ItemProgressView | null>(null);
  const [autoPoll, setAutoPoll] = useState(false);
  const [loadingSheet, setLoadingSheet] = useState(false);
  const [loadingItem, setLoadingItem] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleQuerySheet(targetSheetId = sheetId) {
    if (!targetSheetId.trim()) {
      return;
    }

    try {
      setLoadingSheet(true);
      setError(null);
      const response = await getDemandSheet(targetSheetId.trim());
      setSheet(response.data);
      const firstItemId = response.data.items?.[0]?.item_id ?? "";
      setItemId(firstItemId);
      if (!firstItemId) {
        setItem(null);
        setProgress(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "查询工具需求单失败");
    } finally {
      setLoadingSheet(false);
    }
  }

  async function handleQueryItem(targetItemId = itemId) {
    if (!targetItemId.trim()) {
      return;
    }

    try {
      setLoadingItem(true);
      setError(null);
      const response = await getDemandItem(targetItemId.trim());
      setItem(response.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "查询叶子项失败");
    } finally {
      setLoadingItem(false);
    }
  }

  async function handleRefreshProgress(targetItemId = itemId) {
    if (!targetItemId.trim()) {
      return;
    }

    try {
      setLoadingItem(true);
      setError(null);
      const [progressResponse, itemResponse] = await Promise.all([
        getDemandItemProgress(targetItemId.trim()),
        getDemandItem(targetItemId.trim()),
      ]);
      setProgress(progressResponse.data);
      setItem(itemResponse.data);
      if (sheet?.sheet_id) {
        const sheetResponse = await getDemandSheet(sheet.sheet_id);
        setSheet(sheetResponse.data);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "刷新叶子项进度失败");
    } finally {
      setLoadingItem(false);
    }
  }

  useEffect(() => {
    if (!autoPoll || !itemId.trim()) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      void handleRefreshProgress(itemId);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [autoPoll, itemId, sheet?.sheet_id]);

  return (
    <Space id="xx-p5-query-panel" direction="vertical" size={16} style={{ display: "flex" }}>
      {error ? <Alert id="xx-p5-query-error" type="error" showIcon message={error} /> : null}

      <Card id="xx-p5-sheet-query-card" title="整单查询" style={{ borderRadius: 20 }}>
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              id="xx-p5-sheet-id-input"
              aria-label="工具需求单 ID"
              placeholder="输入 sheet_id，例如 tds-001"
              value={sheetId}
              onChange={(event) => setSheetId(event.target.value)}
            />
            <Button type="primary" loading={loadingSheet} onClick={() => void handleQuerySheet()}>
              查询整单
            </Button>
          </Space.Compact>

          {sheet ? (
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="需求单">{sheet.sheet_name}</Descriptions.Item>
                <Descriptions.Item label="生命周期状态">{renderLifecycleTag(sheet.lifecycle_status)}</Descriptions.Item>
                <Descriptions.Item label="sheet_id">{sheet.sheet_id}</Descriptions.Item>
                <Descriptions.Item label="业务案例">{sheet.business_case}</Descriptions.Item>
                <Descriptions.Item label="审定状态">{renderReviewTag(sheet.review_status)}</Descriptions.Item>
                <Descriptions.Item label="交付状态">{renderDeliveryTag(sheet.delivery_status)}</Descriptions.Item>
                <Descriptions.Item label="处理进度状态">{renderProcessingTag(sheet.processing_status)}</Descriptions.Item>
                <Descriptions.Item label="终态原因码">{sheet.terminal_reason_code ?? "-"}</Descriptions.Item>
              </Descriptions>

              <List
                id="xx-p5-sheet-items"
                bordered
                size="small"
                dataSource={sheet.items ?? []}
                locale={{ emptyText: "当前总单暂无叶子项" }}
                renderItem={(demandItem) => (
                  <List.Item key={demandItem.item_id}>
                    <Space direction="vertical" size={4} style={{ display: "flex", width: "100%" }}>
                      <Space align="center" wrap>
                        <Typography.Text strong>{demandItem.component_name}</Typography.Text>
                        <Tag color="gold">{demandItem.review_status}</Tag>
                        {renderProcessingTag(demandItem.processing_status)}
                      </Space>
                      <Typography.Text type="secondary">{demandItem.item_id}</Typography.Text>
                      <Button
                        type="link"
                        style={{ paddingInline: 0 }}
                        onClick={() => {
                          setItemId(demandItem.item_id);
                          void handleQueryItem(demandItem.item_id);
                        }}
                      >
                        查看叶子项
                      </Button>
                    </Space>
                  </List.Item>
                )}
              />
            </Space>
          ) : null}
        </Space>
      </Card>

      <Card id="xx-p5-item-query-card" title="叶子项进度" style={{ borderRadius: 20 }}>
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              id="xx-p5-item-id-input"
              aria-label="叶子项 ID"
              placeholder="输入 item_id，例如 tdi-001"
              value={itemId}
              onChange={(event) => setItemId(event.target.value)}
            />
            <Button loading={loadingItem} onClick={() => void handleQueryItem()}>
              查询叶子项
            </Button>
            <Button type="primary" loading={loadingItem} onClick={() => void handleRefreshProgress()}>
              刷新进度
            </Button>
          </Space.Compact>

          <Space align="center">
            <Typography.Text>自动轮询</Typography.Text>
            <Switch id="xx-p5-auto-poll" checked={autoPoll} onChange={setAutoPoll} />
          </Space>

          {item ? (
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="组件">{item.component_name}</Descriptions.Item>
              <Descriptions.Item label="状态">{renderProcessingTag(item.processing_status)}</Descriptions.Item>
              <Descriptions.Item label="审定状态">{item.review_status}</Descriptions.Item>
              <Descriptions.Item label="推荐结论">{item.recommendation_type}</Descriptions.Item>
              <Descriptions.Item label="item_id">{item.item_id}</Descriptions.Item>
              <Descriptions.Item label="路径">{item.ancestry.join(" / ")}</Descriptions.Item>
            </Descriptions>
          ) : null}

          {progress ? (
            <Card id="xx-p5-progress-card" size="small" style={{ borderRadius: 16, background: "#f8fafc" }}>
              <Space direction="vertical" size={8} style={{ display: "flex" }}>
                <Typography.Text strong>{progress.last_message}</Typography.Text>
                <Typography.Text type="secondary">
                  生命周期状态：{progress.sheet_lifecycle_status}
                </Typography.Text>
                <Typography.Text type="secondary">
                  审定状态：{progress.sheet_review_status}；交付状态：{progress.sheet_delivery_status}
                </Typography.Text>
                <Typography.Text type="secondary">
                  叶子项处理状态：{progress.status}
                </Typography.Text>
                <Typography.Text type="secondary">当前进度：{progress.progress_percent}%</Typography.Text>
                {progress.result_type === "pending_manufacture" || progress.result_type === "manufactured_tool" ? (
                  <Typography.Text type="secondary">
                    当前进度由 P4 模拟执行器后台推进，P5 仅执行查询与取用决策。
                  </Typography.Text>
                ) : null}
                {progress.suggested_poll_after_seconds != null ? (
                  <Typography.Text type="secondary">
                    建议轮询：{progress.suggested_poll_after_seconds} 秒
                  </Typography.Text>
                ) : null}
                {progress.fetch_interface ? (
                  <Typography.Text type="secondary">
                    获取接口：{progress.fetch_interface.entrypoint_locator}
                  </Typography.Text>
                ) : null}
              </Space>
            </Card>
          ) : null}
        </Space>
      </Card>
    </Space>
  );
}
