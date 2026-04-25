import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Empty,
  InputNumber,
  List,
  Space,
  Statistic,
  Switch,
  Tag,
  Typography,
} from "antd";

import type {
  EvolutionFinding,
  EvolutionFindingDecisionInput,
  EvolutionInspectionConfig,
  EvolutionRun,
  EvolutionTask,
} from "../../lib/api";

type P4EvolutionWorkspaceProps = {
  config: EvolutionInspectionConfig | null;
  runs: EvolutionRun[];
  tasks: EvolutionTask[];
  latestRun: EvolutionRun | null;
  running: boolean;
  savingConfig: boolean;
  decidingFindingId: string | null;
  rollingBackTaskId: string | null;
  onRun: () => Promise<void>;
  onSaveConfig: (payload: Partial<EvolutionInspectionConfig>) => Promise<void>;
  onDecisionFinding: (findingId: string, payload: EvolutionFindingDecisionInput) => Promise<void>;
  onRollbackTask: (taskId: string) => Promise<void>;
};

const RULE_OPTIONS: Array<{ label: string; value: EvolutionFinding["kind"] }> = [
  { label: "描述缺失", value: "missing_description" },
  { label: "域模型/标签不规范", value: "taxonomy_issue" },
  { label: "能力重叠风险", value: "overlap_risk" },
  { label: "业务域覆盖空白", value: "coverage_gap" },
];

const AUTO_APPLY_OPTIONS: Array<{ label: string; value: EvolutionFinding["kind"] }> = [
  { label: "描述缺失", value: "missing_description" },
  { label: "域模型/标签不规范", value: "taxonomy_issue" },
];

export function P4EvolutionWorkspace({
  config,
  runs,
  tasks,
  latestRun,
  running,
  savingConfig,
  decidingFindingId,
  rollingBackTaskId,
  onRun,
  onSaveConfig,
  onDecisionFinding,
  onRollbackTask,
}: P4EvolutionWorkspaceProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [includeDraftTools, setIncludeDraftTools] = useState(true);
  const [intervalMinutes, setIntervalMinutes] = useState<number>(60);
  const [overlapThreshold, setOverlapThreshold] = useState<number>(3);
  const [focusRuleIds, setFocusRuleIds] = useState<EvolutionFinding["kind"][]>(RULE_OPTIONS.map((item) => item.value));
  const [autoApplyRuleIds, setAutoApplyRuleIds] = useState<EvolutionFinding["kind"][]>(AUTO_APPLY_OPTIONS.map((item) => item.value));

  useEffect(() => {
    if (!config) {
      return;
    }
    setEnabled(config.enabled);
    setIncludeDraftTools(config.include_draft_tools);
    setIntervalMinutes(config.interval_minutes);
    setOverlapThreshold(config.overlap_threshold);
    setFocusRuleIds(config.focus_rule_ids);
    setAutoApplyRuleIds(config.auto_apply_rule_ids);
  }, [config]);

  useEffect(() => {
    const preferredRunId = latestRun?.run_id ?? runs[0]?.run_id ?? null;
    if (!preferredRunId) {
      setSelectedRunId(null);
      return;
    }
    setSelectedRunId((current) => (current && runs.some((run) => run.run_id === current) ? current : preferredRunId));
  }, [latestRun, runs]);

  const activeRun = runs.find((run) => run.run_id === selectedRunId) ?? latestRun ?? runs[0] ?? null;
  const activeRunQueueTasks = tasks.filter(
    (task) => task.source_run_id === activeRun?.run_id && (task.task_status === "queued" || task.task_status === "running"),
  );
  const globalQueueTasks = tasks.filter((task) => task.task_status === "queued" || task.task_status === "running");
  const queueTasks = activeRun ? activeRunQueueTasks : globalQueueTasks;
  const completedTasks = tasks.filter((task) => task.task_status === "completed" || task.task_status === "rolled_back");

  async function handleSaveConfig() {
    await onSaveConfig({
      enabled,
      include_draft_tools: includeDraftTools,
      interval_minutes: intervalMinutes,
      overlap_threshold: overlapThreshold,
      focus_rule_ids: focusRuleIds,
      auto_apply_rule_ids: autoApplyRuleIds,
    });
  }

  function renderFindingStatusTag(finding: EvolutionFinding) {
    if (finding.decision_status === "accepted_to_task") {
      return <Tag color="green">已采纳</Tag>;
    }
    if (finding.decision_status === "ignored") {
      return <Tag color="default">已忽略</Tag>;
    }
    return <Tag color="gold">待处置</Tag>;
  }

  function renderTaskStatusTag(task: EvolutionTask) {
    if (task.task_status === "completed") {
      return <Tag color="green">completed</Tag>;
    }
    if (task.task_status === "running") {
      return <Tag color="blue">running</Tag>;
    }
    if (task.task_status === "rolled_back") {
      return <Tag color="purple">rolled_back</Tag>;
    }
    if (task.task_status === "failed") {
      return <Tag color="red">failed</Tag>;
    }
    return <Tag color="gold">queued</Tag>;
  }

  return (
    <div id="xx-p4-evolution-workspace" className="xx-p4-pane-stack">
      <div className="xx-p4-evolution-grid">
        <Card
          id="xx-p4-evolution-config-card"
          title="巡检配置"
          className="xx-p4-panel-card"
          extra={
            <Space>
              <Button id="xx-p4-evolution-save-config-button" onClick={() => void handleSaveConfig()} loading={savingConfig}>
                保存配置
              </Button>
              <Button id="xx-p4-evolution-trigger-button" type="primary" onClick={() => void onRun()} loading={running}>
                触发巡检
              </Button>
            </Space>
          }
        >
          {config ? (
            <div className="xx-p4-evolution-config-form">
              <div className="xx-p4-evolution-config-row">
                <span>启用定时巡检</span>
                <Switch checked={enabled} onChange={setEnabled} />
              </div>
              <div className="xx-p4-evolution-config-row">
                <span>纳入草稿工具</span>
                <Switch checked={includeDraftTools} onChange={setIncludeDraftTools} />
              </div>
              <div className="xx-p4-evolution-config-row">
                <span>巡检间隔（分钟）</span>
                <InputNumber min={1} value={intervalMinutes} onChange={(value) => setIntervalMinutes(value ?? 60)} />
              </div>
              <div className="xx-p4-evolution-config-row">
                <span>重叠阈值</span>
                <InputNumber min={2} max={5} value={overlapThreshold} onChange={(value) => setOverlapThreshold(value ?? 3)} />
              </div>
              <div className="xx-p4-evolution-config-block">
                <Typography.Text strong>重点巡检规则</Typography.Text>
                <Checkbox.Group
                  value={focusRuleIds}
                  options={RULE_OPTIONS}
                  onChange={(values) => setFocusRuleIds(values as EvolutionFinding["kind"][])}
                />
              </div>
              <div className="xx-p4-evolution-config-block">
                <Typography.Text strong>自动执行规则</Typography.Text>
                <Checkbox.Group
                  value={autoApplyRuleIds}
                  options={AUTO_APPLY_OPTIONS}
                  onChange={(values) => setAutoApplyRuleIds(values as EvolutionFinding["kind"][])}
                />
              </div>
              <Typography.Text type="secondary">
                最近更新：{config.updated_at} · 操作者：{config.updated_by}
              </Typography.Text>
            </div>
          ) : (
            <Empty description="当前没有可用巡检配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card id="xx-p4-evolution-run-list-card" title="已巡检轮次" className="xx-p4-panel-card">
          {runs.length === 0 ? (
            <Empty description="暂无巡检记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={runs}
              renderItem={(run) => (
                <List.Item
                  className={run.run_id === activeRun?.run_id ? "xx-p4-evolution-run-item is-active" : "xx-p4-evolution-run-item"}
                  onClick={() => setSelectedRunId(run.run_id)}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>{run.trigger_type === "scheduled" ? "定时巡检" : "手动巡检"}</Typography.Text>
                        <Tag color={run.status === "completed" ? "green" : run.status === "failed" ? "red" : "blue"}>
                          {run.status}
                        </Tag>
                      </Space>
                    }
                    description={`${run.created_at} · ${run.summary.finding_count} 项发现`}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        <Card id="xx-p4-evolution-summary-card" title="当前轮次摘要" className="xx-p4-panel-card">
          {activeRun ? (
            <div className="xx-p4-pane-stack">
              <div className="xx-p4-evolution-summary-stats">
                <Statistic title="发现项" value={activeRun.summary.finding_count} />
                <Statistic title="已采纳" value={activeRun.summary.accepted_count} />
                <Statistic title="已忽略" value={activeRun.summary.ignored_count} />
                <Statistic title="生成任务" value={activeRun.summary.generated_task_count} />
              </div>
              <Alert
                type="info"
                showIcon
                message={`触发方式：${activeRun.trigger_type === "scheduled" ? "定时" : "手动"} · 状态：${activeRun.status}`}
                description={`时间：${activeRun.created_at} · 操作者：${activeRun.triggered_by}`}
              />
              <div className="xx-p4-evolution-summary-breakdown">
                <Tag color="gold">描述缺失 {activeRun.summary.missing_description_count}</Tag>
                <Tag color="blue">标签异常 {activeRun.summary.taxonomy_issue_count}</Tag>
                <Tag color="red">重叠风险 {activeRun.summary.overlap_risk_count}</Tag>
                <Tag color="default">覆盖空白 {activeRun.summary.coverage_gap_count}</Tag>
              </div>
            </div>
          ) : (
            <Empty description="请先触发一次巡检" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card id="xx-p4-evolution-findings-card" title="发现项处置" className="xx-p4-panel-card">
          {activeRun ? (
            <List
              dataSource={activeRun.findings}
              renderItem={(finding) => (
                <List.Item
                  actions={[
                    finding.decision_status === "pending" ? (
                      <Button
                        key="accept"
                        id={`xx-p4-evolution-accept-finding-${finding.finding_id}`}
                        type="link"
                        loading={decidingFindingId === finding.finding_id}
                        onClick={() =>
                          void onDecisionFinding(finding.finding_id, {
                            actor_id: "p4-workspace",
                            decision: "accept",
                            note: "转入 P4 内部优化任务",
                          })
                        }
                      >
                        采纳
                      </Button>
                    ) : null,
                    finding.decision_status === "pending" ? (
                      <Button
                        key="ignore"
                        id={`xx-p4-evolution-ignore-finding-${finding.finding_id}`}
                        type="link"
                        loading={decidingFindingId === finding.finding_id}
                        onClick={() =>
                          void onDecisionFinding(finding.finding_id, {
                            actor_id: "p4-workspace",
                            decision: "ignore",
                            note: "当前轮次暂不采纳",
                          })
                        }
                      >
                        忽略
                      </Button>
                    ) : null,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>{finding.title}</Typography.Text>
                        {renderFindingStatusTag(finding)}
                        <Tag color={finding.severity === "critical" ? "red" : finding.severity === "warning" ? "gold" : "blue"}>
                          {finding.kind}
                        </Tag>
                      </Space>
                    }
                    description={
                      <div className="xx-p4-pane-stack">
                        <Typography.Text>{finding.description}</Typography.Text>
                        {finding.linked_task_id ? (
                          <Typography.Text type="secondary">关联任务：{finding.linked_task_id}</Typography.Text>
                        ) : null}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="当前没有可处置的发现项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        <Card id="xx-p4-evolution-task-queue-card" title="自演进任务队列" className="xx-p4-panel-card">
          {queueTasks.length === 0 ? (
            <Empty description="当前没有待执行的自演进任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={queueTasks}
              renderItem={(task) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>{task.planned_action}</Typography.Text>
                        {renderTaskStatusTag(task)}
                        <Tag color={task.task_type === "auto_apply" ? "green" : "default"}>{task.task_type}</Tag>
                      </Space>
                    }
                    description={`${task.task_id} · ${task.target_tool_ids.join(", ") || "无目标工具"} · ${task.result_summary}`}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        <Card id="xx-p4-evolution-completed-card" title="已完成优化项" className="xx-p4-panel-card">
          {completedTasks.length === 0 ? (
            <Empty description="当前没有已完成优化项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={completedTasks}
              renderItem={(task) => (
                <List.Item
                  actions={[
                    task.rollback_available ? (
                      <Button
                        key="rollback"
                        id={`xx-p4-evolution-rollback-task-${task.task_id}`}
                        type="link"
                        loading={rollingBackTaskId === task.task_id}
                        onClick={() => void onRollbackTask(task.task_id)}
                      >
                        回退本次改写
                      </Button>
                    ) : null,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>{task.planned_action}</Typography.Text>
                        {renderTaskStatusTag(task)}
                      </Space>
                    }
                    description={`${task.result_summary} · 变更数 ${task.change_count} · 更新时间 ${task.updated_at}`}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </div>
    </div>
  );
}
