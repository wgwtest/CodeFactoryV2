import "../components/p4/p4-page.css";
import { startTransition, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Alert, Button, Card, Col, Descriptions, Empty, Modal, Row, Space, Spin, Tag, Typography } from "antd";

import { P4CoverageMatrix } from "../components/p4/P4CoverageMatrix";
import { P4EvolutionWorkspace } from "../components/p4/P4EvolutionWorkspace";
import { P4Hero } from "../components/p4/P4Hero";
import { P4RealToolDeliveryWorkspace } from "../components/p4/P4RealToolDeliveryWorkspace";
import { P4RiskSummary } from "../components/p4/P4RiskSummary";
import { P4RegistryWorkspace } from "../components/p4/P4RegistryWorkspace";
import { P4RunList } from "../components/p4/P4RunList";
import type {
  EvolutionFindingDecisionInput,
  EvolutionInspectionConfig,
  EvolutionRun,
  EvolutionTask,
  ToolDefinition,
  ToolDemandSheet,
  ToolDemandReviewDecisionInput,
  ToolDefinitionWriteInput,
  ToolHubOverview,
  ToolManufacturePlanView,
} from "../lib/api";
import {
  clearToolsForTesting,
  createEvolutionRunV2,
  createToolDefinition,
  decideEvolutionFinding,
  deleteToolDefinition,
  getEvolutionConfig,
  getManufacturePlans,
  getDemandItemProgress,
  getDemandSheet,
  getDemandSheets,
  getEvolutionRunsV2,
  getEvolutionTasks,
  getToolDefinitions,
  getToolHubOverview,
  buildP4ObjectViewsProjection,
  rollbackEvolutionTask,
  clearDemandSheetsForTesting,
  rejectDemandSheet,
  reviewDemandItem,
  updateEvolutionConfig,
  updateToolDefinition,
} from "../lib/toolHub";
import type { P4ObjectViewsProjection } from "../lib/toolHub";

const SNAPSHOT_WARNING_MESSAGE = "P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。";

function formatLifecycleStatus(status?: string | null) {
  switch (status) {
    case "accepted":
      return "已受理";
    case "reviewed":
      return "已审定";
    case "processing":
      return "处理中";
    case "ready":
      return "可关闭";
    default:
      return status ?? "-";
  }
}

function formatReviewStatus(status?: string | null) {
  switch (status) {
    case "pending_review":
      return "待审定";
    case "approved_delivery":
      return "已批准交付";
    case "approved_manufacture":
      return "已批准生产";
    case "rejected":
      return "已驳回";
    default:
      return status ?? "-";
  }
}

function formatProcessingStatus(status?: string | null) {
  switch (status) {
    case "matched_existing":
      return "已命中现有工具";
    case "ready_for_fetch":
      return "可取用";
    case "manufacturing":
    case "manufacturing_in_progress":
      return "生产中";
    default:
      return status ?? "-";
  }
}

function formatRecommendationType(type?: string | null) {
  switch (type) {
    case "existing_tool":
      return "现有工具";
    case "manufactured_tool":
      return "研制工具";
    default:
      return type ?? "-";
  }
}

function formatBusinessCase(businessCase?: string | null) {
  switch (businessCase) {
    case "navigation_planning":
      return "航路规划";
    case "simulated_blue_force":
      return "模拟蓝军";
    default:
      return businessCase ?? "-";
  }
}

function formatPercent(numerator: number, denominator: number) {
  if (!denominator) {
    return "0%";
  }
  return `${Math.round((numerator / denominator) * 100)}%`;
}

export function XXP4Page() {
  const [overview, setOverview] = useState<ToolHubOverview | null>(null);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [manufacturePlans, setManufacturePlans] = useState<ToolManufacturePlanView[]>([]);
  const [demandSheets, setDemandSheets] = useState<ToolDemandSheet[]>([]);
  const [activeSheet, setActiveSheet] = useState<ToolDemandSheet | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [activeObjectView, setActiveObjectView] = useState("pool");
  const [evolutionConfig, setEvolutionConfig] = useState<EvolutionInspectionConfig | null>(null);
  const [evolutionRuns, setEvolutionRuns] = useState<EvolutionRun[]>([]);
  const [evolutionTasks, setEvolutionTasks] = useState<EvolutionTask[]>([]);
  const [latestEvolutionRun, setLatestEvolutionRun] = useState<EvolutionRun | null>(null);
  const [evolutionConfigModalOpen, setEvolutionConfigModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingTool, setSavingTool] = useState(false);
  const [refreshingItemId, setRefreshingItemId] = useState<string | null>(null);
  const [reviewingItemId, setReviewingItemId] = useState<string | null>(null);
  const [rejectingCurrentSheet, setRejectingCurrentSheet] = useState(false);
  const [clearingDemandSheets, setClearingDemandSheets] = useState(false);
  const [runningEvolution, setRunningEvolution] = useState(false);
  const [savingEvolutionConfig, setSavingEvolutionConfig] = useState(false);
  const [decidingEvolutionFindingId, setDecidingEvolutionFindingId] = useState<string | null>(null);
  const [rollingBackEvolutionTaskId, setRollingBackEvolutionTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [snapshotWarning, setSnapshotWarning] = useState<string | null>(null);

  async function loadPage(showLoading = false, preferredSheetId?: string | null, preferredItemId?: string | null) {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const [
        overviewResponse,
        toolsResponse,
        evolutionConfigResponse,
        evolutionResponse,
        evolutionTasksResponse,
        demandSheetsResponse,
        manufacturePlansResponse,
      ] = await Promise.all([
        getToolHubOverview(),
        getToolDefinitions(),
        getEvolutionConfig(),
        getEvolutionRunsV2(),
        getEvolutionTasks(),
        getDemandSheets(),
        getManufacturePlans(),
      ]);
      const overviewEnvelope = overviewResponse.data;
      const toolsEnvelope = toolsResponse.data;
      const evolutionConfigEnvelope = evolutionConfigResponse.data;
      const evolutionEnvelope = evolutionResponse.data;
      const evolutionTasksEnvelope = evolutionTasksResponse.data;
      const demandSheetEnvelope = demandSheetsResponse.data;
      const manufacturePlanEnvelope = manufacturePlansResponse.data;
      const snapshotIds = [
        overviewEnvelope.meta.snapshot_id,
        toolsEnvelope.meta.snapshot_id,
        evolutionConfigEnvelope.meta.snapshot_id,
        evolutionEnvelope.meta.snapshot_id,
        evolutionTasksEnvelope.meta.snapshot_id,
      ];
      const hasSnapshotMismatch = new Set(snapshotIds).size > 1;
      const availableSheetIds = new Set(demandSheetEnvelope.items.map((sheet) => sheet.sheet_id));
      const requestedSheetId =
        preferredSheetId === null ? null : preferredSheetId ?? activeSheet?.sheet_id ?? demandSheetEnvelope.items[0]?.sheet_id ?? null;
      const currentActiveSheetId =
        preferredSheetId === null
          ? null
          : requestedSheetId && availableSheetIds.has(requestedSheetId)
            ? requestedSheetId
            : demandSheetEnvelope.items[0]?.sheet_id ?? null;
      const activeSheetResponse = currentActiveSheetId ? await getDemandSheet(currentActiveSheetId) : null;
      const activeSheetDetail = activeSheetResponse?.data ?? null;
      const nextSelectedItemId =
        preferredItemId && activeSheetDetail?.items?.some((item) => item.item_id === preferredItemId)
          ? preferredItemId
          : activeSheetDetail?.items?.[0]?.item_id ?? null;
      startTransition(() => {
        setOverview(overviewEnvelope.data);
        setTools(toolsEnvelope.data.items);
        setManufacturePlans(manufacturePlanEnvelope.items);
        setDemandSheets(demandSheetEnvelope.items);
        setActiveSheet(activeSheetDetail);
        setSelectedItemId(nextSelectedItemId);
        setSelectedToolId((currentToolId) =>
          currentToolId && toolsEnvelope.data.items.some((tool) => tool.tool_id === currentToolId)
            ? currentToolId
            : activeSheetDetail?.items?.find((item) => item.recommended_tool_id)?.recommended_tool_id ??
              toolsEnvelope.data.items[0]?.tool_id ??
              null,
        );
        setEvolutionConfig(evolutionConfigEnvelope.data);
        setEvolutionRuns(evolutionEnvelope.data.items);
        setEvolutionTasks(evolutionTasksEnvelope.data.items);
        setSnapshotWarning(hasSnapshotMismatch ? SNAPSHOT_WARNING_MESSAGE : null);
        setError(null);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载 XX-P4 数据失败");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadPage(true);
  }, []);

  useEffect(() => {
    const fallbackToolId =
      activeSheet?.items?.find((item) => item.recommended_tool_id)?.recommended_tool_id ?? tools[0]?.tool_id ?? null;
    setSelectedToolId((currentToolId) =>
      currentToolId && tools.some((tool) => tool.tool_id === currentToolId) ? currentToolId : fallbackToolId,
    );
  }, [activeSheet?.sheet_id, activeSheet?.items, tools]);

  async function handleSelectSheet(sheetId: string) {
    const summary = demandSheets.find((sheet) => sheet.sheet_id === sheetId) ?? null;
    try {
      if (summary) {
        setActiveSheet(summary);
        setSelectedItemId(summary.items?.[0]?.item_id ?? null);
      }
      const response = await getDemandSheet(sheetId);
      setActiveSheet(response.data);
      setDemandSheets((currentSheets) =>
        currentSheets.map((sheet) => (sheet.sheet_id === response.data.sheet_id ? { ...sheet, ...response.data } : sheet)),
      );
      setSelectedItemId(response.data.items?.[0]?.item_id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载工具需求单失败");
    }
  }

  async function handleRefreshItemProgress(itemId: string) {
    if (!activeSheet) {
      return;
    }

    try {
      setRefreshingItemId(itemId);
      await getDemandItemProgress(itemId);
      await loadPage(false, activeSheet.sheet_id, itemId);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "刷新叶子项进度失败");
    } finally {
      setRefreshingItemId(null);
    }
  }

  async function handleReviewItem(itemId: string, payload: ToolDemandReviewDecisionInput) {
    if (!activeSheet) {
      return;
    }

    try {
      setReviewingItemId(itemId);
      setError(null);
      await reviewDemandItem(itemId, payload);
      await loadPage(false, activeSheet.sheet_id, itemId);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "提交需求项审定失败");
    } finally {
      setReviewingItemId(null);
    }
  }

  async function handleRejectCurrentSheet() {
    if (!activeSheet) {
      return;
    }

    try {
      setRejectingCurrentSheet(true);
      const response = await rejectDemandSheet(activeSheet.sheet_id, {
        actor_id: "p4-workspace",
        actor_phase: "P4",
        reason_code: "manual_reject",
        reason_message: "P4 工作台人工驳回当前工单。",
      });
      const rejectedSheet = response.data;
      startTransition(() => {
        setActiveSheet(rejectedSheet);
        setDemandSheets((currentSheets) =>
          currentSheets.map((sheet) => (sheet.sheet_id === rejectedSheet.sheet_id ? { ...sheet, ...rejectedSheet } : sheet)),
        );
        setError(null);
      });
    } catch (rejectError) {
      setError(rejectError instanceof Error ? rejectError.message : "驳回当前工单失败");
    } finally {
      setRejectingCurrentSheet(false);
    }
  }

  async function handleClearDemandSheets() {
    try {
      setClearingDemandSheets(true);
      await clearDemandSheetsForTesting();
      await loadPage(false, null, null);
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "清理测试工单失败");
    } finally {
      setClearingDemandSheets(false);
    }
  }

  async function handleRunEvolution() {
    try {
      setRunningEvolution(true);
      const response = await createEvolutionRunV2({ actor_id: "p4-workspace" });
      setLatestEvolutionRun(response.data);
      await loadPage();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "触发自演进巡检失败");
    } finally {
      setRunningEvolution(false);
    }
  }

  async function handleSaveEvolutionConfig(payload: Partial<EvolutionInspectionConfig>) {
    try {
      setSavingEvolutionConfig(true);
      await updateEvolutionConfig(payload);
      await loadPage();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存自演进巡检配置失败");
    } finally {
      setSavingEvolutionConfig(false);
    }
  }

  async function handleDecisionEvolutionFinding(findingId: string, payload: EvolutionFindingDecisionInput) {
    try {
      setDecidingEvolutionFindingId(findingId);
      await decideEvolutionFinding(findingId, payload);
      await loadPage();
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : "提交自演进发现项决策失败");
    } finally {
      setDecidingEvolutionFindingId(null);
    }
  }

  async function handleRollbackEvolutionTask(taskId: string) {
    try {
      setRollingBackEvolutionTaskId(taskId);
      await rollbackEvolutionTask(taskId, {
        actor_id: "p4-workspace",
        note: "P4 工作台人工回退自动改写。",
      });
      await loadPage();
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : "回退自演进任务失败");
    } finally {
      setRollingBackEvolutionTaskId(null);
    }
  }

  async function handleCreateTool(payload: ToolDefinitionWriteInput) {
    try {
      setSavingTool(true);
      await createToolDefinition(payload);
      await loadPage();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "创建工具失败");
    } finally {
      setSavingTool(false);
    }
  }

  async function handleUpdateTool(toolId: string, payload: ToolDefinitionWriteInput) {
    try {
      setSavingTool(true);
      await updateToolDefinition(toolId, payload);
      await loadPage();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "更新工具失败");
    } finally {
      setSavingTool(false);
    }
  }

  async function handleDeleteTool(toolId: string) {
    try {
      setSavingTool(true);
      await deleteToolDefinition(toolId);
      await loadPage();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "移除工具失败");
    } finally {
      setSavingTool(false);
    }
  }

  async function handleClearTools() {
    try {
      setSavingTool(true);
      await clearToolsForTesting();
      await loadPage();
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "清空工具仓库失败");
    } finally {
      setSavingTool(false);
    }
  }

  if (loading && !overview) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!overview) {
    return (
      <div style={{ padding: 32 }}>
        <Alert type="error" showIcon message={error ?? "XX-P4 加载失败"} />
      </div>
    );
  }

  const latestFrontendToolId = tools.find((tool) => tool.tool_form_id === "frontend_component")?.tool_id ?? "";
  const objectProjection: P4ObjectViewsProjection = buildP4ObjectViewsProjection({
    overview,
    tools,
    demandSheets,
    activeSheet,
    selectedItemId,
    selectedToolId,
    manufacturePlans,
    evolutionConfig,
    evolutionRuns,
    evolutionTasks,
  });
  const activeDemandItem = objectProjection.workorder_processing.active_item;
  const selectedTool = objectProjection.tool_build.selected_tool;
  const selectedManufacturePlan = objectProjection.tool_build.manufacture_plan;
  const activeTab = objectProjection.object_tabs.find((tab) => tab.key === activeObjectView) ?? objectProjection.object_tabs[0];
  const activeSheetCompletionRate = activeSheet
    ? formatPercent(activeSheet.approved_delivery_count + activeSheet.approved_manufacture_count, Math.max(activeSheet.item_count, 1))
    : "0%";
  const activeToolUsageCount = selectedTool ? objectProjection.delivered_tool_attribute.used_by_items.length : 0;
  const routeByKey: Record<P4ObjectViewsProjection["object_tabs"][number]["key"], string> = {
    pool: "工单池",
    processing: "工单处理",
    build: "工具构建",
    usage: "取用驾驶舱",
    registry: "资产列表",
    graph: "覆盖图谱",
    asset: "资产属性",
    config: "演进配置",
    lineage: "演进轨迹",
  };
  const workspaceSubtitleByKey: Record<P4ObjectViewsProjection["object_tabs"][number]["key"], string> = {
    pool: "保持工单池、当前工单、工具项的递进关系，不改主体结构。",
    processing: "面向单张工单推进处理状态、卡点、完成条件和进入动作。",
    build: "围绕单工具查看匹配、生产、约束和实时过程值。",
    usage: "把取用情况放到前台，直接看热点工具、冷点工具和领域热度。",
    registry: "以工具资产为中心查看资源、版本、验证和登记状态。",
    graph: "从覆盖关系看业务变化和时序变化，不再用单纯矩阵表达。",
    asset: "强调成品工具已经落到哪些工程，以及它经历过哪些演进。",
    config: "围绕巡检范围、策略、回合数和回退边界配置运行约束。",
    lineage: "追踪主干、分支、回退点与最近几轮演进结果。",
  };
  const objectContextByKey: Record<P4ObjectViewsProjection["object_tabs"][number]["key"], { kind: string; main: string }> = {
    pool: { kind: "工单", main: "工单池 / 当前工单 / 工具项" },
    processing: { kind: "处理", main: "工单生命周期推进" },
    build: { kind: "构建", main: "单工具构建与过程值" },
    usage: { kind: "取用", main: "取用驾驶舱" },
    registry: { kind: "资产", main: "工具资源与登记" },
    graph: { kind: "图谱", main: "覆盖知识图谱" },
    asset: { kind: "属性", main: "成品工具属性" },
    config: { kind: "演进", main: "巡检配置与触发" },
    lineage: { kind: "轨迹", main: "演进主干与分支" },
  };
  const activeContext = objectContextByKey[activeTab.key];

  const renderWorkspaceAction = () => {
    if (activeTab.key === "pool") {
      return null;
    }
    if (activeTab.key === "processing") {
      return (
        <Button type="primary" onClick={() => setActiveObjectView("build")} disabled={!activeDemandItem}>
          进入工具构建
        </Button>
      );
    }
    if (activeTab.key === "build") {
      return (
        <Button type="primary" onClick={() => setActiveObjectView("registry")} disabled={!selectedTool}>
          查看生产中工具
        </Button>
      );
    }
    if (activeTab.key === "usage") {
      return <Button type="primary" onClick={() => setActiveObjectView("registry")}>查看热点工具</Button>;
    }
    if (activeTab.key === "registry") {
      return <Button type="primary" onClick={() => setActiveObjectView("asset")}>打开选中资产</Button>;
    }
    if (activeTab.key === "graph") {
      return <Button type="primary" onClick={() => setActiveObjectView("asset")}>查看资产属性</Button>;
    }
    if (activeTab.key === "asset") {
      return <Button type="primary" onClick={() => setActiveObjectView("lineage")}>查看演进轨迹</Button>;
    }
    if (activeTab.key === "config") {
      return <Button type="primary" onClick={() => setEvolutionConfigModalOpen(true)}>配置巡检</Button>;
    }
    return <Button type="primary" onClick={handleRunEvolution} loading={runningEvolution}>触发巡检</Button>;
  };

  const renderMetricCard = (label: string, value: ReactNode, tone: "navy" | "teal" | "amber" | "neutral" = "neutral") => (
    <div className={`xx-p4-metric-card xx-p4-metric-card--${tone}`}>
      <span className="xx-p4-metric-card-label">{label}</span>
      <strong className="xx-p4-metric-card-value">{value}</strong>
    </div>
  );

  const workorderPoolView = (
    <div id="xx-p4-workorder-pool-view" className="xx-p4-pane-stack">
      <div className="xx-p4-object-work-grid xx-p4-object-grid-three">
        <Card className="xx-p4-panel-card" title="P3 工单池">
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            {demandSheets.length ? (
              <>
                <div className="xx-p4-entity-list" role="list" aria-label="P3 工单池">
                  {demandSheets.map((sheet) => {
                    const selected = sheet.sheet_id === activeSheet?.sheet_id;
                    return (
                      <article
                        key={sheet.sheet_id}
                        className={`xx-p4-entity-row${selected ? " is-active" : ""}`}
                        role="listitem"
                        tabIndex={0}
                        aria-selected={selected}
                        onClick={() => void handleSelectSheet(sheet.sheet_id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            void handleSelectSheet(sheet.sheet_id);
                          }
                        }}
                      >
                        <div className="xx-p4-entity-row-main">
                          <div className="xx-p4-entity-row-head">
                            <Typography.Text strong>{sheet.sheet_name}</Typography.Text>
                            <span className="xx-p4-entity-row-count">{sheet.item_count} 项</span>
                          </div>
                          <div className="xx-p4-entity-row-meta">
                            <span className="xx-p4-status-chip xx-p4-status-chip--pending">
                              {sheet.pending_review_count} 待审
                            </span>
                            <span className="xx-p4-status-chip xx-p4-status-chip--neutral">
                              {sheet.approved_delivery_count} 已交付
                            </span>
                            <span className="xx-p4-status-chip xx-p4-status-chip--info">
                              {sheet.lifecycle_status === "accepted" ? "已受理" : sheet.lifecycle_status}
                            </span>
                          </div>
                        </div>
                        <div className="xx-p4-entity-row-state">{selected ? "当前" : null}</div>
                      </article>
                    );
                  })}
                </div>
                <div className="xx-p4-object-summary xx-p4-object-summary--neutral">
                  <div className="xx-p4-object-summary-kicker">接入概况</div>
                  <div className="xx-p4-metric-grid xx-p4-metric-grid--compact">
                    {renderMetricCard("工单数", demandSheets.length, "navy")}
                    {renderMetricCard("待审", demandSheets.reduce((sum, sheet) => sum + sheet.pending_review_count, 0), "amber")}
                    {renderMetricCard("已交付", demandSheets.reduce((sum, sheet) => sum + sheet.approved_delivery_count, 0), "teal")}
                  </div>
                </div>
              </>
            ) : (
              <Empty description="当前没有工具需求单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Space>
        </Card>

        <Card className="xx-p4-panel-card" title="当前工单">
          {activeSheet ? (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div className="xx-p4-object-summary">
                <div className="xx-p4-object-summary-kicker">当前工单</div>
                <div className="xx-p4-object-summary-title">{activeSheet.sheet_name}</div>
                <div className="xx-p4-object-summary-id">{activeSheet.sheet_id}</div>
                <div className="xx-p4-object-summary-meta">
                  <span className="xx-p4-status-chip xx-p4-status-chip--info">{activeSheet.source.scenario_name || "P3 工具需求输入"}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--neutral">{formatBusinessCase(activeSheet.business_case)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--success">{formatLifecycleStatus(activeSheet.lifecycle_status)}</span>
                </div>
                <div className="xx-p4-metric-grid">
                  {renderMetricCard("工具项", activeSheet.item_count, "navy")}
                  {renderMetricCard("待审", activeSheet.pending_review_count, "amber")}
                  {renderMetricCard("已交付", activeSheet.approved_delivery_count, "teal")}
                  {renderMetricCard("完成度", activeSheetCompletionRate, "neutral")}
                </div>
              </div>
              <div className="xx-p4-entity-list" role="list" aria-label="当前工单工具列表">
                {(activeSheet.items ?? []).map((item) => {
                  const selected = item.item_id === selectedItemId;
                  return (
                    <article
                      key={item.item_id}
                      className={`xx-p4-entity-row${selected ? " is-active" : ""}`}
                      role="listitem"
                      tabIndex={0}
                      aria-selected={selected}
                      onClick={() => setSelectedItemId(item.item_id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelectedItemId(item.item_id);
                        }
                      }}
                    >
                      <div className="xx-p4-entity-row-main">
                        <div className="xx-p4-entity-row-head">
                          <Typography.Text strong>{item.component_name}</Typography.Text>
                          <span className="xx-p4-entity-row-code">{formatRecommendationType(item.recommendation_type)}</span>
                        </div>
                        <div className="xx-p4-entity-row-meta">
                          <span className="xx-p4-status-chip xx-p4-status-chip--info">
                            {item.recommendation_type === "existing_tool" ? "匹配现有工具" : formatRecommendationType(item.recommendation_type)}
                          </span>
                          <span className="xx-p4-status-chip xx-p4-status-chip--pending">{formatReviewStatus(item.review_status)}</span>
                        </div>
                      </div>
                      <div className="xx-p4-entity-row-state">{selected ? "当前" : null}</div>
                    </article>
                  );
                })}
              </div>
              <div className="xx-p4-object-summary xx-p4-object-summary--action">
                <div className="xx-p4-object-summary-kicker">工单动作</div>
                <div className="xx-p4-object-summary-title">进入工单处理</div>
                <div className="xx-p4-object-summary-body">以工单为单位推进工具审定、生产和交付，不在这里切换到单个工具页面。</div>
                <Button type="primary" onClick={() => setActiveObjectView("processing")}>
                  进入工单
                </Button>
              </div>
            </Space>
          ) : (
            <Empty description="当前没有工具需求单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card className="xx-p4-panel-card" title={activeDemandItem?.component_name ?? "当前工具"}>
          {activeDemandItem ? (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div className="xx-p4-object-summary">
                <div className="xx-p4-object-summary-kicker">当前工具</div>
                <div className="xx-p4-object-summary-title">{activeDemandItem.component_name}</div>
                <div className="xx-p4-object-summary-id">{activeDemandItem.component_code}</div>
                <div className="xx-p4-object-summary-meta">
                  <span className="xx-p4-status-chip xx-p4-status-chip--info">{activeSheet?.sheet_name ?? "未关联工单"}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--pending">{formatReviewStatus(activeDemandItem.review_status)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--neutral">{formatRecommendationType(activeDemandItem.recommendation_type)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--success">{formatProcessingStatus(activeDemandItem.processing_status)}</span>
                </div>
                <div className="xx-p4-metric-grid xx-p4-metric-grid--compact">
                  {renderMetricCard("所属工单", activeSheet?.sheet_name ?? "-", "navy")}
                  {renderMetricCard("匹配结果", activeDemandItem.match_result.includes("命中") ? "命中" : "未命中", "teal")}
                  {renderMetricCard("推荐摘要", activeDemandItem.recommendation_summary.slice(0, 18) || "-", "amber")}
                </div>
                <div className="xx-p4-object-summary-body">{activeDemandItem.problem_statement}</div>
              </div>
              <Button type="primary" onClick={() => setActiveObjectView("build")}>
                进入工具构建
              </Button>
            </Space>
          ) : (
            <Empty description="请选择一个工具" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </div>
    </div>
  );

  const workorderProcessingView = (
    <div id="xx-p4-workorder-processing-view" className="xx-p4-pane-stack">
      <div className="xx-p4-object-work-grid xx-p4-object-grid-three">
        <Card className="xx-p4-panel-card" title="工单生命周期">
          {activeSheet ? (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div className="xx-p4-object-summary">
                <div className="xx-p4-object-summary-kicker">工单生命周期</div>
                <div className="xx-p4-object-summary-title">{activeSheet.sheet_name}</div>
                <div className="xx-p4-object-summary-id">{activeSheet.sheet_id}</div>
                <div className="xx-p4-object-summary-meta">
                  <span className="xx-p4-status-chip xx-p4-status-chip--success">{formatLifecycleStatus(activeSheet.lifecycle_status)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--info">{formatProcessingStatus(activeSheet.processing_status)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--neutral">{formatBusinessCase(activeSheet.business_case)}</span>
                </div>
                <div className="xx-p4-metric-grid">
                  {renderMetricCard("工具总数", activeSheet.item_count, "navy")}
                  {renderMetricCard("生产中", activeSheet.approved_manufacture_count, "amber")}
                  {renderMetricCard("已交付", activeSheet.approved_delivery_count, "teal")}
                  {renderMetricCard("待审", activeSheet.pending_review_count, "neutral")}
                </div>
                <div className="xx-p4-object-summary-body">
                  工单内工具全部达到可取用或明确驳回，工单才可关闭。
                </div>
              </div>
              <div className="xx-p4-entity-list" role="list" aria-label="工单生命周期节点">
                {[
                  { key: "接收", action: "接收 P3 冻结工单", result: "已完成" },
                  { key: "处理", action: "逐个推进工具构建", result: "进行中" },
                  { key: "验收", action: "检查工具交付与取用投影", result: activeSheet.delivery_status === "delivered" ? "已完成" : "待验收" },
                  { key: "关闭", action: "写入工单完成事件", result: activeSheet.processing_status === "ready" ? "可关闭" : "未满足" },
                ].map((item) => (
                  <article key={item.key} className={`xx-p4-entity-row${item.key === "处理" ? " is-active" : ""}`} role="listitem">
                    <div className="xx-p4-entity-row-main">
                      <div className="xx-p4-entity-row-head">
                        <Typography.Text strong>{item.key}</Typography.Text>
                        <span className="xx-p4-entity-row-desc">{item.action}</span>
                      </div>
                    </div>
                    <div className="xx-p4-entity-row-actions">
                      <span
                        className={`xx-p4-status-chip ${
                          item.result === "已完成"
                            ? "xx-p4-status-chip--success"
                            : item.result === "进行中"
                              ? "xx-p4-status-chip--info"
                              : item.result === "可关闭"
                                ? "xx-p4-status-chip--neutral"
                                : "xx-p4-status-chip--pending"
                        }`}
                      >
                        {item.result}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
              <Space wrap>
                <Button danger loading={rejectingCurrentSheet} onClick={() => void handleRejectCurrentSheet()} disabled={!activeSheet}>
                  驳回当前工单
                </Button>
                <Button danger ghost loading={clearingDemandSheets} onClick={() => void handleClearDemandSheets()}>
                  测试一键清理全部工单
                </Button>
              </Space>
            </Space>
          ) : (
            <Empty description="当前没有工具需求单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card className="xx-p4-panel-card" title="工单内工具进展">
          {activeSheet?.items?.length ? (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div className="xx-p4-entity-list" role="list" aria-label="工单内工具进展">
                {activeSheet.items.map((item) => {
                  const selected = item.item_id === selectedItemId;
                  const matchLabel = item.match_result.includes("命中") ? "已命中" : "未命中";
                  const progressLabel = formatProcessingStatus(item.processing_status);
                  const reviewLabel = formatReviewStatus(item.review_status);
                  return (
                    <article
                      key={item.item_id}
                      className={`xx-p4-entity-row${selected ? " is-active" : ""}`}
                      role="listitem"
                      tabIndex={0}
                      aria-selected={selected}
                      onClick={() => setSelectedItemId(item.item_id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelectedItemId(item.item_id);
                        }
                      }}
                    >
                      <div className="xx-p4-entity-row-main">
                        <div className="xx-p4-entity-row-head">
                          <Typography.Text strong>{item.component_name}</Typography.Text>
                          <span className="xx-p4-entity-row-code">工具项</span>
                        </div>
                        <div className="xx-p4-entity-row-meta">
                          <span className={`xx-p4-status-chip ${matchLabel === "已命中" ? "xx-p4-status-chip--success" : "xx-p4-status-chip--pending"}`}>
                            {matchLabel}
                          </span>
                          <span className="xx-p4-status-chip xx-p4-status-chip--info">{progressLabel}</span>
                          <span className="xx-p4-status-chip xx-p4-status-chip--neutral">{reviewLabel}</span>
                        </div>
                      </div>
                      <div className="xx-p4-entity-row-state">{selected ? "当前" : null}</div>
                    </article>
                  );
                })}
              </div>
              <Row gutter={[12, 12]}>
                <Col span={12}>
                  <Card className="xx-p4-subcard" title="工单完成度">
                    <Typography.Title level={2} style={{ margin: 0 }}>{activeSheetCompletionRate}</Typography.Title>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card className="xx-p4-subcard" title="阻塞工具">
                    <Typography.Title level={2} style={{ margin: 0 }}>{activeSheet.pending_review_count + activeSheet.rejected_item_count}</Typography.Title>
                  </Card>
                </Col>
              </Row>
            </Space>
          ) : (
            <Empty description="当前工单没有工具" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card className="xx-p4-panel-card" title="当前工具处理入口">
          {activeDemandItem ? (
            <Space direction="vertical" size={12} style={{ display: "flex" }}>
              <div className="xx-p4-object-summary xx-p4-object-summary--action">
                <div className="xx-p4-object-summary-kicker">当前工具处理入口</div>
                <div className="xx-p4-object-summary-title">{activeDemandItem.component_name}</div>
                <div className="xx-p4-object-summary-meta">
                  <span className="xx-p4-status-chip xx-p4-status-chip--success">{activeDemandItem.match_result.includes("命中") ? "已命中" : "未命中"}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--pending">{formatReviewStatus(activeDemandItem.review_status)}</span>
                  <span className="xx-p4-status-chip xx-p4-status-chip--info">{formatProcessingStatus(activeDemandItem.processing_status)}</span>
                </div>
                <div className="xx-p4-object-summary-body">{activeDemandItem.recommendation_summary}</div>
                <Button style={{ marginTop: 12 }} type="primary" onClick={() => setActiveObjectView("build")}>
                  进入工具构建
                </Button>
              </div>
              <div className="xx-p4-object-summary xx-p4-object-summary--neutral">
                <div className="xx-p4-object-summary-kicker">工单关闭条件</div>
                <div className="xx-p4-object-summary-body">
                  该工具构建完成后，工单仍需继续检查剩余工具项；全部工具处理完，工单才进入关闭。
                </div>
              </div>
            </Space>
          ) : (
            <Empty description="请选择一个工具查看推进阻塞" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </div>
    </div>
  );

  const buildStrategyText = selectedTool
    ? `${selectedTool.primary_domain_id} / ${selectedTool.tool_form_id} / ${selectedTool.verification.status}`
    : "等待选择工具";
  const buildConstraintText = activeDemandItem?.supply_result?.fetch_interface?.entrypoint_locator ?? "当前暂无交付约束";
  const buildVersionText = selectedManufacturePlan?.status ?? selectedTool?.updated_at ?? "当前暂无版本控制信息";

  const toolBuildView = (
    <div id="xx-p4-tool-build-view" className="xx-p4-pane-stack">
      <Card className="xx-p4-panel-card" title="工具构建">
        {selectedTool ? (
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            <Space wrap>
              <Typography.Text strong>{selectedTool.name}</Typography.Text>
              <Tag color={selectedTool.status === "active" ? "green" : selectedTool.status === "draft" ? "gold" : "default"}>
                {selectedTool.status}
              </Tag>
              <Tag color="cyan">{selectedTool.tool_form_id}</Tag>
            </Space>
            <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
              {selectedTool.summary}
            </Typography.Paragraph>
            <Space wrap>
              <Button onClick={() => setActiveObjectView("registry")}>进入工具资源列表</Button>
              <Button type="primary" ghost onClick={() => setActiveObjectView("asset")}>
                查看成品工具属性
              </Button>
            </Space>
          </Space>
        ) : (
          <Empty description="当前没有可构建的工具" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card className="xx-p4-panel-card" title="匹配策略">
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Typography.Text>{activeDemandItem?.recommendation_summary ?? "当前没有匹配摘要"}</Typography.Text>
              <Typography.Text type="secondary">{buildStrategyText}</Typography.Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card className="xx-p4-panel-card" title="交付约束">
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Typography.Text>{buildConstraintText}</Typography.Text>
              <Typography.Text type="secondary">
                {activeDemandItem?.supply_result?.last_message ?? "当前没有正式交付约束"}
              </Typography.Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card className="xx-p4-panel-card" title="版本控制">
            <Space direction="vertical" size={8} style={{ display: "flex" }}>
              <Typography.Text>{buildVersionText}</Typography.Text>
              <Typography.Text type="secondary">
                {selectedManufacturePlan ? `计划 ${selectedManufacturePlan.plan_id} · ${selectedManufacturePlan.progress_percent}%` : "当前没有研制队列"}
              </Typography.Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24}>
          <Card id="xx-p4-tool-build-process-values" className="xx-p4-panel-card" title="实时过程值">
            {activeDemandItem ? (
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="当前状态">{activeDemandItem.processing_status}</Descriptions.Item>
                <Descriptions.Item label="审定状态">{activeDemandItem.review_status}</Descriptions.Item>
                <Descriptions.Item label="匹配结果" span={2}>
                  {activeDemandItem.match_result}
                </Descriptions.Item>
                <Descriptions.Item label="分析结果" span={2}>
                  {activeDemandItem.analysis_result}
                </Descriptions.Item>
                <Descriptions.Item label="校验结果" span={2}>
                  {activeDemandItem.check_result}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Empty description="请选择一个工具查看实时过程值" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );

  const usageRecords = objectProjection.usage_cockpit.active_items;
  const hotTools = objectProjection.usage_cockpit.hot_tools;
  const coldTools = objectProjection.usage_cockpit.cold_tools;
  const hotDomains = objectProjection.usage_cockpit.hot_domains;
  const coldDomains = objectProjection.usage_cockpit.cold_domains;
  const usageCockpitView = (
    <div id="xx-p4-usage-cockpit-view" className="xx-p4-pane-stack">
      <Card className="xx-p4-panel-card" title="取用驾驶舱">
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-overview-monitor-card" title="正在使用工具" variant="borderless">
              {usageRecords.length ? (
                <Space direction="vertical" size={6} style={{ display: "flex" }}>
                  {usageRecords.map((item) => (
                    <Tag key={item.item_id} color="green">
                      {item.component_name}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Empty description="当前没有正在使用的工具" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-overview-monitor-card" title="热点工具" variant="borderless">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {hotTools.map((tool) => (
                  <Tag key={tool.tool_id} color="blue">
                    {tool.name}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-overview-monitor-card" title="冷门工具" variant="borderless">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {coldTools.length ? (
                  coldTools.map((tool) => (
                    <Tag key={tool.tool_id} color="default">
                      {tool.name}
                    </Tag>
                  ))
                ) : (
                  <Empty description="当前没有冷门工具" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card className="xx-p4-overview-monitor-card" title="热点领域" variant="borderless">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {hotDomains.map((domain) => (
                  <Tag key={domain.id} color="orange">
                    {domain.label}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card className="xx-p4-overview-monitor-card" title="冷门领域" variant="borderless">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {coldDomains.map((domain) => (
                  <Tag key={domain.id} color="purple">
                    {domain.label}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      </Card>
    </div>
  );

  const resourceListView = (
    <div id="xx-p4-tool-resource-list-view" className="xx-p4-pane-stack">
      <Typography.Title level={4} style={{ margin: 0 }}>
        工具资产资源列表
      </Typography.Title>
      <P4RegistryWorkspace
        tools={tools}
        manufacturePlans={manufacturePlans}
        catalogs={overview.catalogs}
        saving={savingTool}
        onCreate={handleCreateTool}
        onUpdate={handleUpdateTool}
        onDelete={handleDeleteTool}
        onClearAllTools={handleClearTools}
      />
    </div>
  );

  const coverageGraphView = (
    <div id="xx-p4-coverage-knowledge-graph-view" className="xx-p4-pane-stack">
      <Card className="xx-p4-panel-card" title="覆盖知识图谱">
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={12}>
            <Card className="xx-p4-subcard" title="业务变化">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {overview.coverage_matrix.rows.slice(0, 4).map((row) => (
                  <Tag key={row.row_id} color="blue">
                    {row.row_label}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card className="xx-p4-subcard" title="时序变化">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {tools.slice(0, 4).map((tool) => (
                  <Tag key={tool.tool_id} color="green">
                    {tool.name} · {tool.updated_at.slice(0, 10)}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24}>
            <P4CoverageMatrix id="xx-p4-coverage-matrix" matrix={overview.coverage_matrix} />
          </Col>
        </Row>
      </Card>
    </div>
  );

  const assetAttributeView = (
    <div id="xx-p4-delivered-tool-attribute-view" className="xx-p4-pane-stack">
      <Card className="xx-p4-panel-card" title="成品工具属性">
        <Space direction="vertical" size={12} style={{ display: "flex" }}>
          <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
            这里强调成品工具已经落到哪些工程里，以及它经历过哪些变化和演进。
          </Typography.Paragraph>
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="当前成品工具">{selectedTool?.name ?? "暂无成品工具"}</Descriptions.Item>
            <Descriptions.Item label="使用状态">{selectedTool?.status ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="使用工程" span={2}>
              {usageRecords.length ? usageRecords.map((item) => item.component_name).join(" / ") : "当前没有工程使用记录"}
            </Descriptions.Item>
            <Descriptions.Item label="变化演进关系" span={2}>
              {objectProjection.delivered_tool_attribute.evolution_task_count
                ? `最近 ${objectProjection.delivered_tool_attribute.evolution_task_count} 个演进任务 · ${objectProjection.delivered_tool_attribute.rollback_available_count} 个可回退任务`
                : "当前没有演进轨迹"}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>
      <P4RealToolDeliveryWorkspace initialToolId={selectedTool?.tool_id ?? latestFrontendToolId} />
    </div>
  );

  const evolutionConfigView = (
    <div id="xx-p4-evolution-config-view" className="xx-p4-pane-stack">
      <Card
        className="xx-p4-panel-card"
        title="演进配置"
        extra={<Button onClick={() => setEvolutionConfigModalOpen(true)}>Config</Button>}
      >
        {evolutionConfig ? (
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="巡检范围">匹配策略 / 交付约束 / 版本控制</Descriptions.Item>
              <Descriptions.Item label="启用状态">{evolutionConfig.enabled ? "已启用" : "已停用"}</Descriptions.Item>
              <Descriptions.Item label="巡检间隔">{evolutionConfig.interval_minutes} 分钟</Descriptions.Item>
              <Descriptions.Item label="重叠阈值">{evolutionConfig.overlap_threshold}</Descriptions.Item>
              <Descriptions.Item label="纳入草稿工具">{evolutionConfig.include_draft_tools ? "是" : "否"}</Descriptions.Item>
              <Descriptions.Item label="自动应用规则">{evolutionConfig.auto_apply_rule_ids.join(" / ")}</Descriptions.Item>
            </Descriptions>
            <Typography.Text type="secondary">
              最近更新：{evolutionConfig.updated_at} · 操作者：{evolutionConfig.updated_by}
            </Typography.Text>
          </Space>
        ) : (
          <Empty description="当前没有可用巡检配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      <P4EvolutionWorkspace
        config={evolutionConfig}
        runs={evolutionRuns}
        tasks={evolutionTasks}
        latestRun={latestEvolutionRun}
        running={runningEvolution}
        savingConfig={savingEvolutionConfig}
        decidingFindingId={decidingEvolutionFindingId}
        rollingBackTaskId={rollingBackEvolutionTaskId}
        onRun={handleRunEvolution}
        onSaveConfig={handleSaveEvolutionConfig}
        onDecisionFinding={handleDecisionEvolutionFinding}
        onRollbackTask={handleRollbackEvolutionTask}
      />

      <Modal
        title="演进配置深化"
        open={evolutionConfigModalOpen}
        onCancel={() => setEvolutionConfigModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        {evolutionConfig ? (
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
              巡检范围、匹配策略、交付约束和版本控制都在这里编辑。
            </Typography.Paragraph>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="巡检范围">匹配策略 / 交付约束 / 版本控制</Descriptions.Item>
              <Descriptions.Item label="模式">manual_and_scheduled</Descriptions.Item>
              <Descriptions.Item label="当前回合数上限">{evolutionConfig.max_run_history}</Descriptions.Item>
              <Descriptions.Item label="自动应用规则">{evolutionConfig.auto_apply_rule_ids.join(" / ")}</Descriptions.Item>
            </Descriptions>
          </Space>
        ) : (
          <Empty description="当前没有可编辑配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Modal>
    </div>
  );

  const evolutionLineageView = (
    <div id="xx-p4-evolution-lineage-view" className="xx-p4-pane-stack">
      <Card className="xx-p4-panel-card" title="被演进对象分支轨迹图">
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-subcard" title="版本主干">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {evolutionRuns.slice(0, 3).map((run) => (
                  <Tag key={run.run_id} color="blue">
                    {run.run_id}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-subcard" title="演进分支">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {evolutionTasks.filter((task) => task.task_status !== "rolled_back").slice(0, 3).map((task) => (
                  <Tag key={task.task_id} color="green">
                    {task.task_id}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card className="xx-p4-subcard" title="回退点">
              <Space direction="vertical" size={6} style={{ display: "flex" }}>
                {evolutionTasks.filter((task) => task.rollback_available).slice(0, 3).map((task) => (
                  <Tag key={task.task_id} color="orange">
                    {task.task_id}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24}>
            <P4RunList title="最近演进轮次" items={overview.recent_evolution_runs} emptyText="暂无演进轮次" />
          </Col>
          <Col xs={24}>
            <P4RiskSummary items={overview.risk_summary} />
          </Col>
        </Row>
      </Card>
    </div>
  );

  const viewByKey: Record<P4ObjectViewsProjection["object_tabs"][number]["key"], ReactNode> = {
    pool: workorderPoolView,
    processing: workorderProcessingView,
    build: toolBuildView,
    usage: usageCockpitView,
    registry: resourceListView,
    graph: coverageGraphView,
    asset: assetAttributeView,
    config: evolutionConfigView,
    lineage: evolutionLineageView,
  };

  return (
    <div id="xx-p4-page" className="xx-p4-page">
      <div id="xx-p4-hero-shell" className="xx-p4-page-shell">
        <P4Hero />
      </div>

      <div id="xx-p4-content-shell" className="xx-p4-page-shell">
        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
        {snapshotWarning ? (
          <Alert id="xx-p4-snapshot-warning" type="warning" showIcon message={snapshotWarning} style={{ marginBottom: 16 }} />
        ) : null}

        <div id="xx-p4-object-workbench" className="xx-p4-workspace-frame xx-p4-object-workbench">
          <aside id="xx-p4-object-nav" className="xx-p4-object-sidebar">
            <div className="xx-p4-object-side-head">
              <div className="xx-p4-object-side-title">对象工作台</div>
              <p className="xx-p4-object-side-note">{activeContext.main}</p>
            </div>

            <div className="xx-p4-object-context-card">
              <div className="xx-p4-object-context-title">
                <span>当前对象</span>
                <span className="xx-p4-state-pill xx-p4-state-pill--teal">{activeContext.kind}</span>
              </div>
              <div className="xx-p4-object-context-row">
                <span>工单</span>
                <strong>{activeSheet?.sheet_name ?? "未选择"}</strong>
              </div>
              <div className="xx-p4-object-context-row">
                <span>工具</span>
                <strong>{activeDemandItem?.component_name ?? selectedTool?.name ?? "未选择"}</strong>
              </div>
              <div className="xx-p4-object-context-row">
                <span>进度</span>
                <strong>{activeSheet ? `${activeSheetCompletionRate} / ${formatLifecycleStatus(activeSheet.lifecycle_status)}` : "-"}</strong>
              </div>
              <div className="xx-p4-object-context-row">
                <span>取用</span>
                <strong>{selectedTool ? `${activeToolUsageCount} 个工程` : "-"}</strong>
              </div>
            </div>

            <nav className="xx-p4-object-nav-list" aria-label="P4 对象工作台" role="tablist">
              {objectProjection.object_tabs.map((tab, index) => {
                const active = tab.key === activeTab.key;
                return (
                  <button
                    key={tab.key}
                    id={`xx-p4-object-tab-${tab.key}`}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    aria-label={tab.title}
                    className={`xx-p4-object-nav-item${active ? " is-active" : ""}`}
                    data-object-nav="p4-object-workbench"
                    data-workspace-tone={tab.key}
                    onClick={() => setActiveObjectView(tab.key)}
                  >
                    <span className="xx-p4-object-nav-title">
                      <span>{`${index + 1}. ${tab.title}`}</span>
                      <span className="xx-p4-object-nav-kind">{objectContextByKey[tab.key].kind}</span>
                    </span>
                    <span className="xx-p4-object-nav-desc">{tab.caption}</span>
                  </button>
                );
              })}
            </nav>

            <div className="xx-p4-object-side-foot">
              <span>阶段边界</span>
              <strong>P4 不生成 P3，不替代 P5</strong>
            </div>
          </aside>

          <section id="xx-p4-object-workspace" className="xx-p4-object-workspace">
            <div className="xx-p4-object-workspace-head">
              <div>
                <div className="xx-p4-object-workspace-title">
                  <span className="xx-p4-object-route">{`P4 / ${routeByKey[activeTab.key]}`}</span>
                  <h2>{activeTab.title}</h2>
                </div>
                <p className="xx-p4-object-workspace-subtitle">{workspaceSubtitleByKey[activeTab.key]}</p>
              </div>
              <div className="xx-p4-object-actions">
                {renderWorkspaceAction()}
              </div>
            </div>
            <div id="xx-p4-object-view-panel" className="xx-p4-object-view-panel">
              {viewByKey[activeTab.key]}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
