import "../components/p4/p4-page.css";
import { startTransition, useEffect, useState } from "react";
import { Alert, Card, Col, Empty, Row, Space, Spin, Typography } from "antd";

import { P4CoverageMatrix } from "../components/p4/P4CoverageMatrix";
import { P4EvolutionWorkspace } from "../components/p4/P4EvolutionWorkspace";
import { P4Hero } from "../components/p4/P4Hero";
import { P4InputChainWorkspace } from "../components/p4/P4InputChainWorkspace";
import { P4MetricsPanel } from "../components/p4/P4MetricsPanel";
import { P4RiskSummary } from "../components/p4/P4RiskSummary";
import { P4RegistryWorkspace } from "../components/p4/P4RegistryWorkspace";
import { P4RunList } from "../components/p4/P4RunList";
import { P4WorkspaceTabs } from "../components/p4/P4WorkspaceTabs";
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
  rollbackEvolutionTask,
  clearDemandSheetsForTesting,
  rejectDemandSheet,
  reviewDemandItem,
  updateEvolutionConfig,
  updateToolDefinition,
} from "../lib/toolHub";

const SNAPSHOT_WARNING_MESSAGE = "P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。";

export function XXP4Page() {
  const [overview, setOverview] = useState<ToolHubOverview | null>(null);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [manufacturePlans, setManufacturePlans] = useState<ToolManufacturePlanView[]>([]);
  const [demandSheets, setDemandSheets] = useState<ToolDemandSheet[]>([]);
  const [activeSheet, setActiveSheet] = useState<ToolDemandSheet | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [evolutionConfig, setEvolutionConfig] = useState<EvolutionInspectionConfig | null>(null);
  const [evolutionRuns, setEvolutionRuns] = useState<EvolutionRun[]>([]);
  const [evolutionTasks, setEvolutionTasks] = useState<EvolutionTask[]>([]);
  const [latestEvolutionRun, setLatestEvolutionRun] = useState<EvolutionRun | null>(null);
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

  const latestMatchRun = overview.recent_match_runs[0];
  const latestEvolutionSummary = overview.recent_evolution_runs[0];
  const renderWorkspaceTabLabel = (
    id: string,
    tone: "overview" | "input" | "evolution" | "registry",
    index: string,
    title: string,
    caption: string,
  ) => (
    <div id={id} className="xx-p4-workspace-tab-card" data-workspace-tone={tone} data-nav-variant="segmented">
      <span aria-hidden="true" className="xx-p4-workspace-tab-index">
        {index}
      </span>
      <span className="xx-p4-workspace-tab-body">
        <span className="xx-p4-workspace-tab-title">{title}</span>
        <span aria-hidden="true" className="xx-p4-workspace-tab-caption">
          {caption}
        </span>
      </span>
    </div>
  );

  return (
    <div id="xx-p4-page" className="xx-p4-page">
      <div id="xx-p4-hero-shell" className="xx-p4-page-shell">
        <P4Hero />
      </div>

      <div id="xx-p4-content-shell" className="xx-p4-page-shell">
        {error ? (
          <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
        ) : null}
        {snapshotWarning ? (
          <Alert id="xx-p4-snapshot-warning" type="warning" showIcon message={snapshotWarning} style={{ marginBottom: 16 }} />
        ) : null}

        <div id="xx-p4-workspaces">
          <div className="xx-p4-workspace-frame">
            <P4WorkspaceTabs
              items={[
                {
                  key: "overview",
                  label: renderWorkspaceTabLabel("xx-p4-workspace-tab-overview", "overview", "01", "总览", "全局状态"),
                  children: (
                    <div id="xx-p4-overview-pane" className="xx-p4-pane-stack">
                      <div id="xx-p4-overview-metrics">
                        <P4MetricsPanel metrics={overview.metrics} />
                      </div>

                      <div id="xx-p4-overview-run-monitor">
                        <Card
                          className="xx-p4-panel-card xx-p4-panel-card--muted"
                          variant="borderless"
                        >
                          <div className="xx-p4-pane-stack">
                            <div>
                              <Typography.Title level={4} style={{ margin: 0 }}>
                                运行监视
                              </Typography.Title>
                              <Typography.Paragraph style={{ margin: "8px 0 0", color: "#475569" }}>
                                跟踪输入工序链、自演进巡检与风险摘要，快速判断当前 P4 工作状态是否需要下钻处理。
                              </Typography.Paragraph>
                            </div>

                            {overview.recent_match_runs.length === 0 &&
                            overview.recent_evolution_runs.length === 0 &&
                            overview.risk_summary.length === 0 ? (
                              <Empty description="最近没有运行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            ) : (
                              <div className="xx-p4-overview-monitor-grid">
                                <div>
                                  <Card
                                    id="xx-p4-run-monitor-match"
                                    className="xx-p4-overview-monitor-card"
                                    variant="borderless"
                                  >
                                    <Typography.Text type="secondary">输入工序链</Typography.Text>
                                    <Typography.Title level={2} style={{ margin: "8px 0 10px" }}>
                                      {overview.recent_match_runs.length}
                                    </Typography.Title>
                                    <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
                                      {latestMatchRun
                                        ? `${latestMatchRun.title} · ${latestMatchRun.status}`
                                        : "当前没有最近输入链任务"}
                                    </Typography.Paragraph>
                                  </Card>
                                </div>
                                <div>
                                  <Card
                                    id="xx-p4-run-monitor-evolution"
                                    className="xx-p4-overview-monitor-card"
                                    variant="borderless"
                                  >
                                    <Typography.Text type="secondary">自演进巡检</Typography.Text>
                                    <Typography.Title level={2} style={{ margin: "8px 0 10px" }}>
                                      {overview.recent_evolution_runs.length}
                                    </Typography.Title>
                                    <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
                                      {latestEvolutionSummary
                                        ? `${latestEvolutionSummary.title} · ${latestEvolutionSummary.status}`
                                        : "当前没有最近巡检任务"}
                                    </Typography.Paragraph>
                                  </Card>
                                </div>
                                <div>
                                  <Card
                                    id="xx-p4-run-monitor-risk"
                                    className="xx-p4-overview-monitor-card"
                                    variant="borderless"
                                  >
                                    <Typography.Text type="secondary">风险摘要</Typography.Text>
                                    <Typography.Title level={2} style={{ margin: "8px 0 10px" }}>
                                      {overview.risk_summary.length}
                                    </Typography.Title>
                                    <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
                                        {overview.risk_summary[0]?.title ?? "当前没有新增风险提示"}
                                    </Typography.Paragraph>
                                  </Card>
                                </div>
                              </div>
                            )}
                          </div>
                        </Card>
                      </div>

                      <Row gutter={[16, 16]}>
                        <Col xs={24} xl={12}>
                          <P4RunList
                            title="最近输入链任务"
                            items={overview.recent_match_runs}
                            emptyText="暂无输入链任务"
                          />
                        </Col>
                        <Col xs={24} xl={12}>
                          <P4RunList
                            title="最近自演进巡检"
                            items={overview.recent_evolution_runs}
                            emptyText="暂无巡检任务"
                          />
                        </Col>
                        <Col xs={24}>
                          <P4RiskSummary items={overview.risk_summary} />
                        </Col>
                      </Row>
                    </div>
                  ),
                },
                {
                  key: "input-chain",
                  label: renderWorkspaceTabLabel(
                    "xx-p4-workspace-tab-input-chain",
                    "input",
                    "02",
                    "输入工序链",
                    "总单到供给",
                  ),
                  children: (
                    <P4InputChainWorkspace
              sheets={demandSheets}
              activeSheet={activeSheet}
              selectedItemId={selectedItemId}
              refreshingItemId={refreshingItemId}
              reviewingItemId={reviewingItemId}
              rejectingCurrentSheet={rejectingCurrentSheet}
              clearingDemandSheets={clearingDemandSheets}
              error={error}
              onSelectSheet={handleSelectSheet}
              onSelectItem={setSelectedItemId}
              onRefreshProgress={handleRefreshItemProgress}
              onReviewItem={handleReviewItem}
              onRejectCurrentSheet={handleRejectCurrentSheet}
              onClearDemandSheets={handleClearDemandSheets}
            />
          ),
        },
                {
                  key: "evolution",
                  label: renderWorkspaceTabLabel(
                    "xx-p4-workspace-tab-evolution",
                    "evolution",
                    "03",
                    "自演进巡检",
                    "工具池体检",
                  ),
                  children: (
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
                  ),
                },
                {
                  key: "registry",
                  label: renderWorkspaceTabLabel("xx-p4-workspace-tab-registry", "registry", "04", "工具仓库", "资产与覆盖"),
                  children: (
                    <div id="xx-p4-registry-pane" className="xx-p4-pane-stack">
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
                      <div id="xx-p4-registry-coverage-matrix">
                        <P4CoverageMatrix id="xx-p4-coverage-matrix" matrix={overview.coverage_matrix} />
                      </div>
                    </div>
                  ),
                },
              ]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
