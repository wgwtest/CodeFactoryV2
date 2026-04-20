import "./BuildWorkspacePage.css";
import { startTransition, useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Empty, Progress, Select, Space, Spin, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import type {
  P5AssemblyAttempt,
  P5BuildOverview,
  P5DeliveryOrderDetail,
  P5DeliveryOrderSummary,
  P5DesignInputSource,
  P5SupplyInputSource,
} from "../lib/api";
import {
  bootstrapSoftwareBuildWorkspace,
  clearSoftwareBuildDeliveriesForTesting,
  confirmSoftwareBuildBinding,
  createSoftwareBuildAttempt,
  getSoftwareBuildDesignInputs,
  getSoftwareBuildOrderDetail,
  getSoftwareBuildOrders,
  getSoftwareBuildOverview,
  getSoftwareBuildSupplyInputs,
  reviewSoftwareBuildFeedbackTask,
  updateSoftwareBuildModuleBinding,
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
    confirmed: "green",
    dismissed: "default",
    passed: "green",
    warning: "orange",
    skipped: "default",
    idle: "default",
    running: "processing",
    blocked: "red",
    heuristic: "blue",
    manual: "cyan",
    empty: "default",
  };
  return <Tag color={colorByStatus[status] ?? "blue"}>{status}</Tag>;
}

function buildStats(overview: P5BuildOverview | null) {
  if (!overview) {
    return [];
  }
  return [
    { title: "交付主单", value: overview.metrics.order_count },
    { title: "带缺口导出", value: overview.metrics.exported_with_gaps_count },
    { title: "正式完成", value: overview.metrics.completed_count },
    { title: "失败", value: overview.metrics.failed_count },
  ];
}

function getBindingDefaults(
  order: P5DeliveryOrderDetail | null,
  designInputs: P5DesignInputSource[],
  supplyInputs: P5SupplyInputSource[],
) {
  const designInputId = order?.active_input_binding.design_input_id ?? designInputs[0]?.design_input_id ?? null;
  const supplyInputId = order?.active_input_binding.supply_input_id ?? supplyInputs[0]?.supply_input_id ?? null;
  const supplyMode =
    order?.active_input_binding.supply_mode ?? (supplyInputId ? ("snapshot" as const) : ("empty" as const));
  return {
    designInputId,
    supplyInputId,
    supplyMode,
  };
}

export function BuildWorkspacePage() {
  const [overview, setOverview] = useState<P5BuildOverview | null>(null);
  const [orders, setOrders] = useState<P5DeliveryOrderSummary[]>([]);
  const [designInputs, setDesignInputs] = useState<P5DesignInputSource[]>([]);
  const [supplyInputs, setSupplyInputs] = useState<P5SupplyInputSource[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<P5DeliveryOrderDetail | null>(null);
  const [bindingDesignInputId, setBindingDesignInputId] = useState<string | null>(null);
  const [bindingSupplyInputId, setBindingSupplyInputId] = useState<string | null>(null);
  const [bindingSupplyMode, setBindingSupplyMode] = useState<"snapshot" | "empty">("empty");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [clearingDeliveries, setClearingDeliveries] = useState(false);
  const [bindingSubmitting, setBindingSubmitting] = useState(false);
  const [runningAttempt, setRunningAttempt] = useState(false);
  const [taskSubmittingId, setTaskSubmittingId] = useState<string | null>(null);
  const [moduleSubmittingId, setModuleSubmittingId] = useState<string | null>(null);
  const latestRequestRef = useRef(0);

  const selectedSupplyInput = supplyInputs.find((item) => item.supply_input_id === bindingSupplyInputId) ?? null;

  function beginRequest() {
    latestRequestRef.current += 1;
    return latestRequestRef.current;
  }

  function syncBindingState(
    order: P5DeliveryOrderDetail | null,
    nextDesignInputs: P5DesignInputSource[],
    nextSupplyInputs: P5SupplyInputSource[],
  ) {
    const defaults = getBindingDefaults(order, nextDesignInputs, nextSupplyInputs);
    setBindingDesignInputId(defaults.designInputId);
    setBindingSupplyInputId(defaults.supplyInputId);
    setBindingSupplyMode(defaults.supplyMode);
  }

  async function loadOrderDetail(orderId: string, requestId = beginRequest()) {
    const detailResponse = await getSoftwareBuildOrderDetail(orderId);
    if (requestId !== latestRequestRef.current) {
      return;
    }
    startTransition(() => {
      setSelectedOrderId(orderId);
      setSelectedOrder(detailResponse.data);
      syncBindingState(detailResponse.data, designInputs, supplyInputs);
    });
  }

  async function loadPage(showLoading = false, preferredOrderId?: string | null) {
    if (showLoading) {
      setLoading(true);
    }
    const requestId = beginRequest();
    try {
      const [overviewResponse, ordersResponse, designInputsResponse, supplyInputsResponse] = await Promise.all([
        getSoftwareBuildOverview(),
        getSoftwareBuildOrders(),
        getSoftwareBuildDesignInputs(),
        getSoftwareBuildSupplyInputs(),
      ]);
      const orderItems = ordersResponse.data.data.items;
      const nextDesignInputs = designInputsResponse.data.data.items;
      const nextSupplyInputs = supplyInputsResponse.data.data.items;
      const requestedOrderId = preferredOrderId !== undefined ? preferredOrderId : selectedOrderId;
      const activeOrderId =
        requestedOrderId && orderItems.some((item) => item.delivery_order_id === requestedOrderId)
          ? requestedOrderId
          : orderItems[0]?.delivery_order_id ?? null;
      const detailResponse = activeOrderId ? await getSoftwareBuildOrderDetail(activeOrderId) : null;
      if (requestId !== latestRequestRef.current) {
        return;
      }
      startTransition(() => {
        setOverview(overviewResponse.data.data);
        setOrders(orderItems);
        setDesignInputs(nextDesignInputs);
        setSupplyInputs(nextSupplyInputs);
        setSelectedOrderId(activeOrderId);
        setSelectedOrder(detailResponse?.data ?? null);
        syncBindingState(detailResponse?.data ?? null, nextDesignInputs, nextSupplyInputs);
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

  async function handleClearDeliveries() {
    try {
      setClearingDeliveries(true);
      setError(null);
      const response = await clearSoftwareBuildDeliveriesForTesting();
      startTransition(() => {
        setSelectedOrderId(null);
        setSelectedOrder(null);
      });
      setNotice(
        `已清空 ${response.data.cleared_order_count} 张 P5 交付主单，移除 ${response.data.cleared_attempt_count} 次构建尝试。`,
      );
      await loadPage(false, null);
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "清空 P5 交付失败");
    } finally {
      setClearingDeliveries(false);
    }
  }

  async function handleConfirmBinding() {
    if (!selectedOrderId || !bindingDesignInputId) {
      return;
    }
    try {
      setBindingSubmitting(true);
      setError(null);
      await confirmSoftwareBuildBinding(selectedOrderId, {
        design_input_id: bindingDesignInputId,
        supply_mode: bindingSupplyMode,
        supply_input_id: bindingSupplyMode === "snapshot" ? bindingSupplyInputId : null,
        confirmed_by: "p5-workbench",
      });
      setNotice("已确认当前输入绑定。");
      await loadPage(false, selectedOrderId);
    } catch (bindingError) {
      setError(bindingError instanceof Error ? bindingError.message : "确认输入绑定失败");
    } finally {
      setBindingSubmitting(false);
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

  async function handleBindModule(moduleId: string, toolId: string) {
    if (!selectedOrderId) {
      return;
    }
    try {
      setModuleSubmittingId(moduleId);
      setError(null);
      await updateSoftwareBuildModuleBinding(selectedOrderId, moduleId, {
        tool_id: toolId,
        updated_by: "p5-workbench",
      });
      setNotice(`已更新模块 ${moduleId} 的手动绑定。`);
      await loadPage(false, selectedOrderId);
    } catch (moduleError) {
      setError(moduleError instanceof Error ? moduleError.message : "更新模块绑定失败");
    } finally {
      setModuleSubmittingId(null);
    }
  }

  async function handleReviewTask(taskId: string, decision: "confirmed" | "dismissed") {
    const latestAttempt = selectedOrder?.attempts.at(-1);
    if (!selectedOrderId || !latestAttempt) {
      return;
    }
    try {
      setTaskSubmittingId(taskId);
      setError(null);
      await reviewSoftwareBuildFeedbackTask(selectedOrderId, latestAttempt.attempt_id, taskId, {
        decision,
        reviewed_by: "p5-workbench",
        review_note: decision === "confirmed" ? "工作台确认进入回流队列" : "当前轮次先保留占位，不进入回流",
      });
      setNotice(decision === "confirmed" ? "已确认反馈任务。" : "已忽略反馈任务。");
      await loadPage(false, selectedOrderId);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "更新反馈任务失败");
    } finally {
      setTaskSubmittingId(null);
    }
  }

  const latestAttempt: P5AssemblyAttempt | null = selectedOrder?.attempts.at(-1) ?? null;
  const stats = buildStats(overview);
  const hasOrders = orders.length > 0;

  return (
    <div className="p5-build-page">
      <div className="p5-build-shell">
        <header className="p5-build-header">
          <div className="p5-build-header-main">
            <div className="p5-build-header-copy">
              <Typography.Text className="p5-build-kicker">P5.1 最小构建闭环</Typography.Text>
              <div className="p5-build-heading-row">
                <Typography.Title level={1} className="p5-build-title">
                  软件构建系统
                </Typography.Title>
                <Typography.Text className="p5-build-subtitle">
                  交付主单 / 输入绑定 / 构建尝试 / 人工批阅
                </Typography.Text>
              </div>
              <Typography.Paragraph className="p5-build-description">
                当前工作台只围绕单一交付上下文组织输入绑定、装配投影、运行监控、输出预览与反馈评审，不承担门户式顶部导航。
              </Typography.Paragraph>
              <div className="p5-build-stage-links">
                <Link to="/xx-p3-doc-sim">P3 文档模拟输出台</Link>
                <Link to="/xx-p4-supply-sim">P4 供给模拟输出台</Link>
              </div>
            </div>
            <div className="p5-build-header-side">
              <div className="p5-build-summary-card">
                <Typography.Text className="p5-build-summary-title">当前运行概览</Typography.Text>
                <div className="p5-build-metric-strip">
                  {stats.map((stat) => (
                    <div key={stat.title} className="p5-build-metric-card">
                      <Typography.Text className="p5-build-metric-title">{stat.title}</Typography.Text>
                      <Typography.Text className="p5-build-metric-value">{stat.value}</Typography.Text>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p5-build-toolbar">
                <Button onClick={() => void loadPage(false, selectedOrderId)} loading={loading}>
                  刷新
                </Button>
                <Button
                  danger
                  onClick={() => void handleClearDeliveries()}
                  loading={clearingDeliveries}
                  disabled={!hasOrders}
                >
                  清空当前 P5 交付
                </Button>
                <Button onClick={() => void handleBootstrap()} loading={bootstrapping}>
                  装载演示闭环
                </Button>
                <Button
                  type="primary"
                  onClick={() => void handleCreateAttempt()}
                  loading={runningAttempt}
                  disabled={!selectedOrderId}
                >
                  发起构建尝试
                </Button>
              </div>
            </div>
          </div>
        </header>

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
          <section className="p5-build-grid">
            <aside className="p5-build-column p5-build-sidebar">
              <Card className="p5-build-panel" title="交付主单队列">
                {orders.length === 0 ? (
                  <Empty
                    description={
                      <Space direction="vertical" size={8}>
                        <Typography.Text>当前暂无 P5 交付主单。</Typography.Text>
                        <Typography.Text type="secondary">先生成模拟输入，再装载演示闭环或新建主单。</Typography.Text>
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
                            void loadOrderDetail(item.delivery_order_id);
                          }}
                        >
                          <div className="p5-build-order-row">
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
            </aside>

            <main className="p5-build-column p5-build-main">
              <Card
                className="p5-build-panel"
                title={selectedOrder?.application_name ?? "当前工作对象"}
                extra={latestAttempt ? <Typography.Text strong>{formatAttemptLabel(latestAttempt.sequence)}</Typography.Text> : null}
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
                      <Typography.Text type="secondary">绑定状态</Typography.Text>
                      <Space>
                        {renderStatusTag(selectedOrder.active_input_binding.is_confirmed ? "confirmed" : "draft")}
                        {renderStatusTag(selectedOrder.status)}
                      </Space>
                    </div>
                  </div>
                )}
              </Card>

              <Card className="p5-build-panel" title="装配流程主视图">
                {!latestAttempt ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前还没有装配投影。" />
                ) : (
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    {latestAttempt.assembly_plan.modules.map((module) => (
                      <div
                        key={module.module_id}
                        className={`p5-build-module-card${
                          module.binding_status === "bound" ? " is-bound" : " is-placeholder"
                        }`}
                      >
                        <div className="p5-build-order-row">
                          <Typography.Text strong>{module.name}</Typography.Text>
                          <Space size={6} wrap>
                            {renderStatusTag(module.binding_status)}
                            {renderStatusTag(module.binding_source)}
                          </Space>
                        </div>
                        <Typography.Paragraph type="secondary">{module.objective}</Typography.Paragraph>
                        <Space wrap>
                          {module.target_directories.map((directory) => (
                            <Tag key={directory}>{directory}</Tag>
                          ))}
                          {module.bound_tool_name ? <Tag color="green">{module.bound_tool_name}</Tag> : null}
                        </Space>
                        {module.gap_reason ? <Typography.Paragraph className="p5-build-warning-copy">{module.gap_reason}</Typography.Paragraph> : null}
                        {module.binding_status === "placeholder" && selectedSupplyInput?.tools.length ? (
                          <Space wrap>
                            {selectedSupplyInput.tools.map((tool) => (
                              <Button
                                key={`${module.module_id}-${tool.tool_id}`}
                                size="small"
                                onClick={() => void handleBindModule(module.module_id, tool.tool_id)}
                                loading={moduleSubmittingId === module.module_id}
                              >
                                使用 {tool.tool_name}
                              </Button>
                            ))}
                          </Space>
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
                    <div className="p5-build-order-row">
                      <Typography.Text strong>{latestAttempt.runtime_snapshot.executor_name}</Typography.Text>
                      <Space>
                        {renderStatusTag(latestAttempt.runtime_snapshot.executor_status)}
                        {renderStatusTag(latestAttempt.runtime_snapshot.attempt_status)}
                      </Space>
                    </div>
                    <Progress percent={latestAttempt.runtime_snapshot.progress_percent} strokeColor="#48686a" />
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
            </main>

            <aside className="p5-build-column p5-build-sidepanel">
              <Card className="p5-build-panel" title="输入绑定与确认">
                <Space direction="vertical" size={12} style={{ display: "flex" }}>
                  <div className="p5-build-subpanel">
                    <Typography.Text strong>冻结设计输入</Typography.Text>
                    <Select
                      value={bindingDesignInputId ?? undefined}
                      options={designInputs.map((item) => ({
                        value: item.design_input_id,
                        label: `${item.application_name} (${item.source_kind})`,
                      }))}
                      onChange={(value) => setBindingDesignInputId(value)}
                    />
                  </div>
                  <div className="p5-build-subpanel">
                    <div className="p5-build-order-row">
                      <Typography.Text strong>供给快照输入</Typography.Text>
                      <Button size="small" type={bindingSupplyMode === "empty" ? "default" : "text"} onClick={() => setBindingSupplyMode("empty")}>
                        供给为空
                      </Button>
                    </div>
                    <Select
                      value={bindingSupplyInputId ?? undefined}
                      options={supplyInputs.map((item) => ({
                        value: item.supply_input_id,
                        label: `${item.snapshot_name} (${item.tool_count} tools)`,
                      }))}
                      onChange={(value) => {
                        setBindingSupplyMode("snapshot");
                        setBindingSupplyInputId(value);
                      }}
                      placeholder="选择供给快照"
                    />
                  </div>
                  {selectedOrder ? (
                    <Space size={8} wrap>
                      {renderStatusTag(selectedOrder.active_input_binding.is_confirmed ? "confirmed" : "draft")}
                      <Tag>{selectedOrder.active_input_binding.supply_mode}</Tag>
                    </Space>
                  ) : null}
                  <Button type="primary" onClick={() => void handleConfirmBinding()} loading={bindingSubmitting} disabled={!selectedOrderId}>
                    确认当前输入绑定
                  </Button>
                </Space>
              </Card>

              <Card className="p5-build-panel" title="输出结果预览">
                {!latestAttempt ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无输出结果" />
                ) : (
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    <div className="p5-build-subpanel p5-build-console-panel">
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
                    <div className="p5-build-subpanel p5-build-gap-surface">
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
                              <Space wrap>
                                <Button
                                  size="small"
                                  type="primary"
                                  ghost
                                  onClick={() => void handleReviewTask(task.task_id, "confirmed")}
                                  loading={taskSubmittingId === task.task_id}
                                  disabled={task.status !== "pending_confirmation"}
                                >
                                  确认反馈任务
                                </Button>
                                <Button
                                  size="small"
                                  onClick={() => void handleReviewTask(task.task_id, "dismissed")}
                                  loading={taskSubmittingId === task.task_id}
                                  disabled={task.status !== "pending_confirmation"}
                                >
                                  忽略反馈任务
                                </Button>
                              </Space>
                            </div>
                          ))}
                        </Space>
                      )}
                    </div>
                  </Space>
                )}
              </Card>
            </aside>
          </section>
        )}
      </div>
    </div>
  );
}
