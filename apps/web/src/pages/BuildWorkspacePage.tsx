import "./BuildWorkspacePage.css";
import { startTransition, useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Empty, Progress, Space, Spin, Tag, Typography } from "antd";

import type { P5AssemblyAttempt, P5BuildOverview, P5DeliveryOrderDetail, P5DeliveryOrderSummary } from "../lib/api";
import {
  bootstrapSoftwareBuildWorkspace,
  createSoftwareBuildAttempt,
  getSoftwareBuildOrderDetail,
  getSoftwareBuildOrders,
  getSoftwareBuildOverview,
} from "../lib/softwareBuild";

const DEFAULT_EXPORT_ROOT = ".data/software_build_exports";

function formatAttemptLabel(sequence: number) {
  return `attempt-${String(sequence).padStart(3, "0")}`;
}

function renderStatusTag(status: string) {
  const colorByStatus: Record<string, string> = {
    draft: "default",
    assembling: "processing",
    exported_with_gaps: "orange",
    completed_with_gaps: "gold",
    completed: "green",
    failed: "red",
    bound: "green",
    placeholder: "orange",
    pending_confirmation: "gold",
    passed: "green",
    warning: "orange",
    skipped: "default",
    idle: "default",
    running: "processing",
    blocked: "red",
  };
  return <Tag color={colorByStatus[status] ?? "blue"}>{status}</Tag>;
}

function buildStats(overview: P5BuildOverview | null) {
  if (!overview) {
    return [];
  }
  return [
    { title: "P5 交付主单", value: overview.metrics.order_count },
    { title: "带缺口交付", value: overview.metrics.exported_with_gaps_count },
    { title: "正式完成", value: overview.metrics.completed_count },
    { title: "失败", value: overview.metrics.failed_count },
  ];
}

export function BuildWorkspacePage() {
  const [overview, setOverview] = useState<P5BuildOverview | null>(null);
  const [orders, setOrders] = useState<P5DeliveryOrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<P5DeliveryOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [runningAttempt, setRunningAttempt] = useState(false);
  const latestRequestRef = useRef(0);

  function beginRequest() {
    latestRequestRef.current += 1;
    return latestRequestRef.current;
  }

  async function loadOrderDetail(orderId: string, requestId = beginRequest()) {
    const detailResponse = await getSoftwareBuildOrderDetail(orderId);
    if (requestId !== latestRequestRef.current) {
      return;
    }
    setSelectedOrder(detailResponse.data);
  }

  async function loadPage(showLoading = false, preferredOrderId: string | null = null) {
    if (showLoading) {
      setLoading(true);
    }
    const requestId = beginRequest();
    try {
      const [overviewResponse, ordersResponse] = await Promise.all([getSoftwareBuildOverview(), getSoftwareBuildOrders()]);
      const orderItems = ordersResponse.data.data.items;
      const activeOrderId = preferredOrderId ?? selectedOrderId ?? orderItems[0]?.delivery_order_id ?? null;
      const detailResponse = activeOrderId ? await getSoftwareBuildOrderDetail(activeOrderId) : null;
      if (requestId !== latestRequestRef.current) {
        return;
      }
      startTransition(() => {
        setOverview(overviewResponse.data.data);
        setOrders(orderItems);
        setSelectedOrderId(activeOrderId);
        setSelectedOrder(detailResponse?.data ?? null);
        setError(null);
      });
    } catch (loadError) {
      if (requestId !== latestRequestRef.current) {
        return;
      }
      setError(loadError instanceof Error ? loadError.message : "加载 P5 工作台失败");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadPage(true);
  }, []);

  async function handleBootstrap() {
    try {
      setBootstrapping(true);
      setError(null);
      const response = await bootstrapSoftwareBuildWorkspace({
        export_root: DEFAULT_EXPORT_ROOT,
        build_profile: "demo",
        attempt_note: "bootstrap-demo",
      });
      setNotice(response.data.created_demo_inputs ? "已装载 P5.1 演示闭环输入。" : "已复用现有演示输入并追加 attempt。");
      await loadPage(false, response.data.delivery_order_id);
    } catch (bootstrapError) {
      setError(bootstrapError instanceof Error ? bootstrapError.message : "装载演示闭环失败");
    } finally {
      setBootstrapping(false);
    }
  }

  async function handleCreateAttempt() {
    if (!selectedOrderId || !selectedOrder) {
      return;
    }
    try {
      setRunningAttempt(true);
      setError(null);
      const nextSequence = selectedOrder.current_attempt_count + 1;
      await createSoftwareBuildAttempt(selectedOrderId, {
        export_root: DEFAULT_EXPORT_ROOT,
        build_profile: "baseline",
        attempt_note: `workspace-${formatAttemptLabel(nextSequence)}`,
      });
      setNotice(`已为 ${selectedOrder.application_name} 发起新的构建尝试。`);
      await loadPage(false, selectedOrderId);
    } catch (attemptError) {
      setError(attemptError instanceof Error ? attemptError.message : "发起构建尝试失败");
    } finally {
      setRunningAttempt(false);
    }
  }

  const latestAttempt: P5AssemblyAttempt | null = selectedOrder?.attempts.at(-1) ?? null;
  const stats = buildStats(overview);

  return (
    <div className="p5-build-page">
      <div className="p5-build-shell">
        <section className="p5-build-hero">
          <div className="p5-build-hero-copy">
            <Typography.Text className="p5-build-kicker">P5.1 Minimal Delivery Loop</Typography.Text>
            <div className="p5-build-title-row">
              <Typography.Title level={1} className="p5-build-title">
                软件构建系统
              </Typography.Title>
              <Tag color="blue">独立工作台</Tag>
            </div>
            <Typography.Paragraph className="p5-build-description">
              当前工作台承接冻结后的 P3 设计与 P4 供给快照，在一个页面内完成主单选择、attempt 执行、运行监控、输出预览与缺口留痕。
            </Typography.Paragraph>
          </div>
          <div className="p5-build-hero-actions">
            <Button onClick={() => void loadPage(false, selectedOrderId)} loading={loading}>
              刷新
            </Button>
            <Button onClick={() => void handleBootstrap()} loading={bootstrapping}>
              装载演示闭环
            </Button>
            <Button type="primary" onClick={() => void handleCreateAttempt()} loading={runningAttempt} disabled={!selectedOrderId}>
              发起构建尝试
            </Button>
          </div>
          <div className="p5-build-metric-strip">
            {stats.map((stat) => (
              <div key={stat.title} className="p5-build-metric-card">
                <Typography.Text className="p5-build-metric-title">{stat.title}</Typography.Text>
                <Typography.Text className="p5-build-metric-value">{stat.value}</Typography.Text>
              </div>
            ))}
          </div>
        </section>

        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
        {notice ? (
          <Alert
            type="success"
            showIcon
            closable
            message={notice}
            style={{ marginBottom: 16 }}
            onClose={() => setNotice(null)}
          />
        ) : null}

        {loading && !overview ? (
          <div className="p5-build-loading">
            <Spin size="large" />
          </div>
        ) : (
          <section className="p5-build-workspace">
            <aside className="p5-build-sidebar">
              <Card className="p5-build-panel" title="交付主单队列">
                {orders.length === 0 ? (
                  <Empty
                    description={
                      <Space direction="vertical" size={8}>
                        <Typography.Text>当前暂无 P5 交付主单。</Typography.Text>
                        <Typography.Text type="secondary">可直接装载演示闭环，先形成可测试的最小循环。</Typography.Text>
                      </Space>
                    }
                  />
                ) : (
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    {orders.map((item) => {
                      const active = item.delivery_order_id === selectedOrderId;
                      return (
                        <button
                          key={item.delivery_order_id}
                          type="button"
                          className={`p5-build-order-card${active ? " is-active" : ""}`}
                          onClick={() => {
                            setSelectedOrderId(item.delivery_order_id);
                            void loadOrderDetail(item.delivery_order_id);
                          }}
                        >
                          <div className="p5-build-order-card-row">
                            <Typography.Text strong>{item.application_name}</Typography.Text>
                            {renderStatusTag(item.status)}
                          </div>
                          <Typography.Text type="secondary">P3: {item.p3_order_id}</Typography.Text>
                          <Typography.Text type="secondary">
                            最近尝试 {item.current_attempt_count > 0 ? formatAttemptLabel(item.current_attempt_count) : "未开始"}
                          </Typography.Text>
                        </button>
                      );
                    })}
                  </Space>
                )}
              </Card>

              <Card className="p5-build-panel" title="联调输入快照">
                {!latestAttempt ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未生成 attempt 输入快照" />
                ) : (
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    <div className="p5-build-subpanel">
                      <Typography.Text strong>冻结设计输入</Typography.Text>
                      <Typography.Paragraph type="secondary">
                        {latestAttempt.input_snapshot.design_input.source_kind} / {latestAttempt.input_snapshot.design_input.order_id}
                      </Typography.Paragraph>
                      <Typography.Text>baseline: {latestAttempt.input_snapshot.design_input.baseline_id}</Typography.Text>
                      <Typography.Text>模块数: {latestAttempt.input_snapshot.design_input.module_count}</Typography.Text>
                    </div>
                    <div className="p5-build-subpanel">
                      <Typography.Text strong>供给快照输入</Typography.Text>
                      <Typography.Paragraph type="secondary">
                        {latestAttempt.input_snapshot.supply_input.source_kind}
                      </Typography.Paragraph>
                      <Typography.Text>工具数: {latestAttempt.input_snapshot.supply_input.tool_count}</Typography.Text>
                      <Typography.Text>已命中: {latestAttempt.input_snapshot.supply_input.matched_tool_count}</Typography.Text>
                    </div>
                  </Space>
                )}
              </Card>
            </aside>

            <div className="p5-build-main">
              <Card
                className="p5-build-panel p5-build-context-panel"
                title={selectedOrder?.application_name ?? "当前工作对象"}
                extra={latestAttempt ? <Typography.Text strong>{`最近尝试 ${formatAttemptLabel(latestAttempt.sequence)}`}</Typography.Text> : null}
              >
                {!selectedOrder ? (
                  <Empty description="先装载演示闭环或选择一张交付主单。" />
                ) : (
                  <div className="p5-build-context-grid">
                    <div className="p5-build-context-item">
                      <Typography.Text type="secondary">主单</Typography.Text>
                      <Typography.Text strong>{selectedOrder.delivery_order_id}</Typography.Text>
                    </div>
                    <div className="p5-build-context-item">
                      <Typography.Text type="secondary">来源 P3</Typography.Text>
                      <Typography.Text>{selectedOrder.p3_order_id}</Typography.Text>
                    </div>
                    <div className="p5-build-context-item">
                      <Typography.Text type="secondary">需求规格</Typography.Text>
                      <Typography.Text>{selectedOrder.requirement_spec_id}</Typography.Text>
                    </div>
                    <div className="p5-build-context-item">
                      <Typography.Text type="secondary">当前状态</Typography.Text>
                      <Space>{renderStatusTag(selectedOrder.status)}</Space>
                    </div>
                  </div>
                )}
              </Card>

              <div className="p5-build-two-column-grid">
                <Card className="p5-build-panel" title="装配流程主视图">
                  {!latestAttempt ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无装配投影" />
                  ) : (
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      {latestAttempt.assembly_plan.modules.map((module) => (
                        <div
                          key={module.module_id}
                          className={`p5-build-module-card${
                            module.binding_status === "bound" ? " is-bound" : " is-placeholder"
                          }`}
                        >
                          <div className="p5-build-order-card-row">
                            <Typography.Text strong>{module.name}</Typography.Text>
                            {renderStatusTag(module.binding_status)}
                          </div>
                          <Typography.Paragraph type="secondary">{module.objective}</Typography.Paragraph>
                          <Space wrap>
                            {module.target_directories.map((directory) => (
                              <Tag key={directory}>{directory}</Tag>
                            ))}
                            {module.bound_tool_name ? <Tag color="green">{module.bound_tool_name}</Tag> : null}
                          </Space>
                          {module.gap_reason ? (
                            <Typography.Paragraph className="p5-build-warning-copy">{module.gap_reason}</Typography.Paragraph>
                          ) : null}
                        </div>
                      ))}
                    </Space>
                  )}
                </Card>

                <Card className="p5-build-panel" title="构建运行与监控">
                  {!latestAttempt ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无运行监控数据" />
                  ) : (
                    <Space direction="vertical" size={14} style={{ display: "flex" }}>
                      <div className="p5-build-order-card-row">
                        <Typography.Text strong>{latestAttempt.runtime_snapshot.executor_name}</Typography.Text>
                        <Space>
                          {renderStatusTag(latestAttempt.runtime_snapshot.executor_status)}
                          {renderStatusTag(latestAttempt.runtime_snapshot.attempt_status)}
                        </Space>
                      </div>
                      <Progress percent={latestAttempt.runtime_snapshot.progress_percent} strokeColor="#1d4ed8" />
                      <Space direction="vertical" size={10} style={{ display: "flex" }}>
                        {latestAttempt.runtime_snapshot.stages.map((stage) => (
                          <div key={stage.stage_id} className="p5-build-stage-row">
                            <div>
                              <Typography.Text strong>{stage.label}</Typography.Text>
                              <Typography.Paragraph type="secondary">{stage.detail}</Typography.Paragraph>
                            </div>
                            {renderStatusTag(stage.status)}
                          </div>
                        ))}
                      </Space>
                      <div className="p5-build-log-block">
                        {latestAttempt.runtime_snapshot.recent_logs.map((log, index) => (
                          <div key={`${log.timestamp}-${index}`} className="p5-build-log-line">
                            <Tag color={log.level === "warning" ? "orange" : log.level === "error" ? "red" : "blue"}>{log.level}</Tag>
                            <Typography.Text>{log.message}</Typography.Text>
                          </div>
                        ))}
                      </div>
                    </Space>
                  )}
                </Card>

                <Card className="p5-build-panel" title="输出结果预览">
                  {!latestAttempt ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无输出结果" />
                  ) : (
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <div className="p5-build-subpanel">
                        <Typography.Text strong>导出根目录</Typography.Text>
                        <Typography.Paragraph copyable={{ text: latestAttempt.output_preview.root_directory }}>
                          {latestAttempt.output_preview.root_directory}
                        </Typography.Paragraph>
                      </div>
                      <div className="p5-build-output-dir-strip">
                        {latestAttempt.output_preview.directories.map((directory) => (
                          <Tag key={directory}>{directory}</Tag>
                        ))}
                      </div>
                      <Space direction="vertical" size={10} style={{ display: "flex" }}>
                        {latestAttempt.output_preview.key_files.map((item) => (
                          <div key={item.path} className="p5-build-output-item">
                            <div>
                              <Typography.Text strong>{item.path}</Typography.Text>
                              <Typography.Paragraph type="secondary">{item.summary}</Typography.Paragraph>
                            </div>
                            {renderStatusTag(item.status)}
                          </div>
                        ))}
                      </Space>
                    </Space>
                  )}
                </Card>

                <Card className="p5-build-panel" title="缺口与反馈">
                  {!latestAttempt ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无缺口与反馈" />
                  ) : (
                    <Space direction="vertical" size={14} style={{ display: "flex" }}>
                      <div className="p5-build-subpanel">
                        <Typography.Text strong>缺口清单</Typography.Text>
                        {latestAttempt.gaps.length === 0 ? (
                          <Typography.Paragraph type="secondary">当前 attempt 无缺口。</Typography.Paragraph>
                        ) : (
                          <Space direction="vertical" size={10} style={{ display: "flex" }}>
                            {latestAttempt.gaps.map((gap) => (
                              <div key={gap.gap_id} className="p5-build-gap-item">
                                <Space wrap>
                                  <Tag color="orange">{gap.kind}</Tag>
                                  <Typography.Text strong>{gap.summary}</Typography.Text>
                                </Space>
                                <Typography.Paragraph type="secondary">{gap.detail}</Typography.Paragraph>
                              </div>
                            ))}
                          </Space>
                        )}
                      </div>

                      <div className="p5-build-subpanel">
                        <Typography.Text strong>反馈任务</Typography.Text>
                        {latestAttempt.feedback_tasks.length === 0 ? (
                          <Typography.Paragraph type="secondary">暂无反馈任务。</Typography.Paragraph>
                        ) : (
                          <Space direction="vertical" size={10} style={{ display: "flex" }}>
                            {latestAttempt.feedback_tasks.map((task) => (
                              <div key={task.task_id} className="p5-build-gap-item">
                                <Space wrap>
                                  {renderStatusTag(task.status)}
                                  <Typography.Text strong>{task.title}</Typography.Text>
                                </Space>
                                <Typography.Paragraph type="secondary">{task.detail}</Typography.Paragraph>
                              </div>
                            ))}
                          </Space>
                        )}
                      </div>
                    </Space>
                  )}
                </Card>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
