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
import { useArchiveContext } from "../context/ArchiveContext";
import type {
  EvolutionRun,
  ToolDefinition,
  ToolDemandSheet,
  ToolDefinitionWriteInput,
  ToolHubOverview,
} from "../lib/api";
import {
  createMockBlueForceDemandSheet,
  createEvolutionRun,
  createToolDefinition,
  getDemandItemProgress,
  getDemandSheet,
  getDemandSheets,
  getEvolutionRuns,
  getToolDefinitions,
  getToolHubOverview,
  updateToolDefinition,
} from "../lib/toolHub";

const SNAPSHOT_WARNING_MESSAGE = "P4 数据快照不一致，当前视图可能不是同一份统一数据层结果。";

export function XXP4Page() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [overview, setOverview] = useState<ToolHubOverview | null>(null);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [demandSheets, setDemandSheets] = useState<ToolDemandSheet[]>([]);
  const [activeSheet, setActiveSheet] = useState<ToolDemandSheet | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [evolutionRuns, setEvolutionRuns] = useState<EvolutionRun[]>([]);
  const [latestEvolutionRun, setLatestEvolutionRun] = useState<EvolutionRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingTool, setSavingTool] = useState(false);
  const [creatingMockSheet, setCreatingMockSheet] = useState(false);
  const [refreshingItemId, setRefreshingItemId] = useState<string | null>(null);
  const [runningEvolution, setRunningEvolution] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snapshotWarning, setSnapshotWarning] = useState<string | null>(null);

  async function loadPage(showLoading = false, preferredSheetId?: string | null, preferredItemId?: string | null) {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const [overviewResponse, toolsResponse, evolutionResponse, demandSheetsResponse] = await Promise.all([
        getToolHubOverview(),
        getToolDefinitions(),
        getEvolutionRuns(),
        getDemandSheets(),
      ]);
      const overviewEnvelope = overviewResponse.data;
      const toolsEnvelope = toolsResponse.data;
      const evolutionEnvelope = evolutionResponse.data;
      const demandSheetEnvelope = demandSheetsResponse.data;
      const snapshotIds = [
        overviewEnvelope.meta.snapshot_id,
        toolsEnvelope.meta.snapshot_id,
        evolutionEnvelope.meta.snapshot_id,
      ];
      const hasSnapshotMismatch = new Set(snapshotIds).size > 1;
      const currentActiveSheetId = preferredSheetId ?? activeSheet?.sheet_id ?? demandSheetEnvelope.items[0]?.sheet_id ?? null;
      const activeSheetResponse = currentActiveSheetId ? await getDemandSheet(currentActiveSheetId) : null;
      const activeSheetDetail = activeSheetResponse?.data ?? null;
      const nextSelectedItemId =
        preferredItemId && activeSheetDetail?.items?.some((item) => item.item_id === preferredItemId)
          ? preferredItemId
          : activeSheetDetail?.items?.[0]?.item_id ?? null;
      startTransition(() => {
        setOverview(overviewEnvelope.data);
        setTools(toolsEnvelope.data.items);
        setDemandSheets(demandSheetEnvelope.items);
        setActiveSheet(activeSheetDetail);
        setSelectedItemId(nextSelectedItemId);
        setEvolutionRuns(evolutionEnvelope.data.items);
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

  async function handleGenerateMockSheet() {
    try {
      setCreatingMockSheet(true);
      const response = await createMockBlueForceDemandSheet();
      await loadPage(false, response.data.sheet_id, response.data.items?.[0]?.item_id ?? null);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "生成模拟蓝军需求总单失败");
    } finally {
      setCreatingMockSheet(false);
    }
  }

  async function handleSelectSheet(sheetId: string) {
    try {
      const response = await getDemandSheet(sheetId);
      setActiveSheet(response.data);
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

  async function handleRunEvolution() {
    try {
      setRunningEvolution(true);
      const response = await createEvolutionRun();
      setLatestEvolutionRun(response.data);
      await loadPage();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "触发自演进巡检失败");
    } finally {
      setRunningEvolution(false);
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
    <div id={id} className="xx-p4-workspace-tab-card" data-workspace-tone={tone}>
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
    <div id="xx-p4-page" style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div id="xx-p4-hero-shell" style={{ maxWidth: 1440, margin: "0 auto 20px" }}>
        <Card
          style={{
            borderRadius: 20,
            border: "1px solid #d0d7de",
            background: "linear-gradient(180deg, #ffffff 0%, #f6f8fa 100%)",
            boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
          }}
        >
          <P4Hero overview={overview} archiveName={activeArchive?.name ?? activeArchiveId} />
        </Card>
      </div>

      <div id="xx-p4-content-shell" style={{ maxWidth: 1440, margin: "0 auto 0" }}>
        {error ? (
          <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
        ) : null}
        {snapshotWarning ? (
          <Alert id="xx-p4-snapshot-warning" type="warning" showIcon message={snapshotWarning} style={{ marginBottom: 16 }} />
        ) : null}

        <div id="xx-p4-workspaces">
          <Card style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}>
            <P4WorkspaceTabs
              items={[
                {
                  key: "overview",
                  label: renderWorkspaceTabLabel("xx-p4-workspace-tab-overview", "overview", "01", "总览", "全局状态"),
                  children: (
                    <Space direction="vertical" size={18} style={{ display: "flex" }}>
                      <div id="xx-p4-overview-metrics">
                        <P4MetricsPanel metrics={overview.metrics} />
                      </div>

                      <div id="xx-p4-overview-run-monitor">
                        <Card
                          variant="borderless"
                          style={{ borderRadius: 18, background: "#f8fafc", boxShadow: "inset 0 0 0 1px #e2e8f0" }}
                        >
                          <Space direction="vertical" size={18} style={{ display: "flex" }}>
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
                              <Row gutter={[16, 16]}>
                                <Col xs={24} lg={8}>
                                  <Card
                                    id="xx-p4-run-monitor-match"
                                    variant="borderless"
                                    style={{ background: "#ffffff", boxShadow: "inset 0 0 0 1px #e2e8f0" }}
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
                                </Col>
                                <Col xs={24} lg={8}>
                                  <Card
                                    id="xx-p4-run-monitor-evolution"
                                    variant="borderless"
                                    style={{ background: "#ffffff", boxShadow: "inset 0 0 0 1px #e2e8f0" }}
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
                                </Col>
                                <Col xs={24} lg={8}>
                                  <Card
                                    id="xx-p4-run-monitor-risk"
                                    variant="borderless"
                                    style={{ background: "#ffffff", boxShadow: "inset 0 0 0 1px #e2e8f0" }}
                                  >
                                    <Typography.Text type="secondary">风险摘要</Typography.Text>
                                    <Typography.Title level={2} style={{ margin: "8px 0 10px" }}>
                                      {overview.risk_summary.length}
                                    </Typography.Title>
                                    <Typography.Paragraph style={{ marginBottom: 0, color: "#475569" }}>
                                      {overview.risk_summary[0]?.title ?? "当前没有新增风险提示"}
                                    </Typography.Paragraph>
                                  </Card>
                                </Col>
                              </Row>
                            )}
                          </Space>
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
                    </Space>
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
                      creatingMockSheet={creatingMockSheet}
                      refreshingItemId={refreshingItemId}
                      error={error}
                      onGenerateMockSheet={handleGenerateMockSheet}
                      onSelectSheet={handleSelectSheet}
                      onSelectItem={setSelectedItemId}
                      onRefreshProgress={handleRefreshItemProgress}
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
                      runs={evolutionRuns}
                      latestRun={latestEvolutionRun}
                      running={runningEvolution}
                      onRun={handleRunEvolution}
                    />
                  ),
                },
                {
                  key: "registry",
                  label: renderWorkspaceTabLabel("xx-p4-workspace-tab-registry", "registry", "04", "工具仓库", "资产与覆盖"),
                  children: (
                    <Space direction="vertical" size={18} style={{ display: "flex" }}>
                      <P4RegistryWorkspace
                        tools={tools}
                        catalogs={overview.catalogs}
                        saving={savingTool}
                        onCreate={handleCreateTool}
                        onUpdate={handleUpdateTool}
                      />
                      <div id="xx-p4-registry-coverage-matrix">
                        <P4CoverageMatrix id="xx-p4-coverage-matrix" matrix={overview.coverage_matrix} />
                      </div>
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      </div>
    </div>
  );
}
