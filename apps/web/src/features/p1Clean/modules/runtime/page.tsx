import { useEffect, useMemo, useState } from "react";

import { Alert, Badge, Button, Card, Col, Empty, List, Row, Select, Space, Spin, Statistic, Steps, Tag, Timeline, Typography } from "antd";

import { useArchiveContext } from "../../../../context/ArchiveContext";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { runtimeApi } from "./api";
import type {
  RuntimeContract,
  RuntimeDocument,
  RuntimeStageSnapshot,
  RuntimeTransportStatus,
} from "./types";
import "./runtime.css";

const RUNTIME_STREAM_INTERVAL_MS = 2000;
const RUNTIME_POLLING_INTERVAL_MS = 5000;
const RUNTIME_HEARTBEAT_MS = 10000;

const statusColor: Record<string, string> = {
  pending: "default",
  running: "processing",
  completed: "success",
  blocked: "error",
  warning: "warning",
  unavailable: "default",
};

const levelColor: Record<string, string> = {
  neutral: "gray",
  info: "blue",
  success: "green",
  warning: "orange",
  danger: "red",
};

const runtimeEventLabels: Record<string, string> = {
  run_started: "运行启动",
  document_started: "文档开始",
  parse_snapshot_ready: "解析就绪",
  rule_started: "规则执行",
  rule_hit: "规则命中",
  object_candidate_created: "对象生成",
  relation_candidate_created: "关系生成",
  merge_candidate_created: "合并候选",
  quality_metric_updated: "质量更新",
  run_completed: "运行完成",
  run_failed: "运行失败",
};

const transportMeta: Record<RuntimeTransportStatus, { label: string; color: string; text: string }> = {
  idle: { label: "未连接", color: "default", text: "等待文档集合和策略版本" },
  connecting: { label: "连接中", color: "processing", text: "正在连接运行流" },
  streaming: { label: "stream", color: "success", text: "SSE 实时流已连接" },
  polling: { label: "polling", color: "warning", text: "SSE 不可用，已切换轮询" },
  unavailable: { label: "不可用", color: "default", text: "缺少运行输入合同" },
  error: { label: "异常", color: "error", text: "运行状态读取失败" },
};

function formatUnknown(value: unknown, fallback = "未提供") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function toErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "运行态接口暂不可用";
}

function getRuntimeSnapshotId(runtime: RuntimeContract | null, fallback: string | null) {
  const policySnapshot = runtime?.policy_snapshot as
    | {
        run_id?: string | null;
        snapshot_id?: string | null;
        policy_snapshot_id?: string | null;
      }
    | null
    | undefined;

  return (
    runtime?.runtime_snapshot_id ??
    policySnapshot?.run_id ??
    runtime?.policy_snapshot_id ??
    policySnapshot?.policy_snapshot_id ??
    policySnapshot?.snapshot_id ??
    fallback ??
    null
  );
}

type RuntimeDisplayEvent = {
  event_id: string;
  event_type: string;
  level: string;
  message: string;
  stage_id?: string | null;
  stage_label?: string | null;
  timestamp?: string | null;
};

function collectRuntimeEvents(runtime: RuntimeContract | null): RuntimeDisplayEvent[] {
  if (!runtime) {
    return [];
  }

  if (runtime.runtime_events?.length) {
    return runtime.runtime_events
      .map((event) => {
        const stage = runtime.stages.find((item) => item.stage_id === event.stage_id);
        return {
          event_id: event.event_id,
          event_type: event.event_type,
          level: event.level,
          message: event.message,
          stage_id: event.stage_id,
          stage_label: stage?.label ?? event.stage_id ?? runtime.current_stage_label,
          timestamp: event.timestamp,
        };
      })
      .slice(-18)
      .reverse();
  }

  return runtime.stages
    .flatMap((stage) =>
      stage.stage_observer.stream.map((event) => ({
        ...event,
        event_type: event.kind,
        stage_id: stage.stage_id,
        stage_label: stage.label,
      })),
    )
    .slice(-12)
    .reverse();
}

function getCurrentObject(runtime: RuntimeContract | null) {
  return (
    runtime?.generated_candidates?.find((candidate) => candidate.candidate_type !== "relation") ??
    runtime?.graph_projection?.nodes.find((node) => node.is_focus || node.is_primary) ??
    null
  );
}

function getCurrentRelation(runtime: RuntimeContract | null) {
  return (
    runtime?.generated_candidates?.find((candidate) => candidate.candidate_type === "relation") ??
    runtime?.graph_projection?.edges.find((edge) => edge.is_primary) ??
    null
  );
}

function getCurrentStage(runtime: RuntimeContract | null): RuntimeStageSnapshot | null {
  if (!runtime) {
    return null;
  }
  return runtime.stages.find((stage) => stage.stage_id === runtime.current_stage_id) ?? runtime.stages.find((stage) => stage.is_current) ?? null;
}

function getStageStepStatus(stage: RuntimeStageSnapshot) {
  if (stage.status === "blocked") return "error" as const;
  if (stage.status === "warning") return "process" as const;
  if (stage.status === "completed") return "finish" as const;
  if (stage.status === "running") return "process" as const;
  return "wait" as const;
}

function mergeRuntimeDocuments(context: P1ModulePageProps["context"], documents: RuntimeDocument[]) {
  const byId = new Map(documents.map((document) => [document.id, document]));
  for (const document of context.archive.build_state?.documents ?? []) {
    if (!document.document_id || byId.has(document.document_id)) {
      continue;
    }
    byId.set(document.document_id, {
      id: document.document_id,
      title: document.title,
      file_type: document.file_type,
      source_archive: document.source_archive,
      character_count: 0,
      included_in_archive: document.state === "completed",
      entity_count: 0,
      event_count: 0,
      process_count: 0,
      knowledge_item_count: 0,
    });
  }
  return Array.from(byId.values());
}

function countItems(value: unknown[] | undefined | null) {
  return value?.length ?? 0;
}

function getArchiveRuntimeSummary(context: P1ModulePageProps["context"], documents: RuntimeDocument[]) {
  const buildState = context.archive.build_state;
  const expectedCount = buildState?.expected_document_count ?? documents.length ?? context.archive.summary?.document_count ?? 0;
  const completedCount = countItems(buildState?.completed_document_ids) || context.archive.summary?.document_count || 0;
  const skippedCount = countItems(buildState?.skipped_document_ids);
  const pendingCount = countItems(buildState?.pending_document_ids);
  const failedCount = buildState?.failed_document_id ? 1 : 0;

  return {
    status: buildState?.status ?? context.archive.status,
    expectedCount,
    completedCount,
    skippedCount,
    pendingCount,
    failedCount,
    warningCount: buildState?.warning_count ?? countItems(buildState?.warnings),
    currentDocumentTitle: buildState?.current_document_title ?? null,
    currentStageLabel: buildState?.current_stage_label ?? null,
    currentStageMessage: buildState?.current_stage_message ?? null,
  };
}

function getArchiveDocumentStateMap(context: P1ModulePageProps["context"]) {
  return new Map((context.archive.build_state?.documents ?? []).map((document) => [document.document_id, document.state]));
}

function RuntimeGraphProjection({
  contextDocumentSetId,
  policyPackageVersionId,
  runtime,
  runtimeSnapshotId,
}: {
  contextDocumentSetId: string | null;
  policyPackageVersionId: string | null;
  runtime: RuntimeContract | null;
  runtimeSnapshotId: string | null;
}) {
  const currentStage = getCurrentStage(runtime);
  const inputLabel = runtime?.document_title ?? "等待选择运行文档";
  const policyLabel =
    runtime?.policy_version ??
    runtime?.policy_package_version_id ??
    policyPackageVersionId ??
    runtime?.policy_snapshot_id ??
    "等待策略版本";

  return (
    <div className="p1-runtime-graph" aria-label="运行态语义图谱">
      <div className="p1-runtime-graph-node is-input">
        <span>输入对象</span>
        <strong>{inputLabel}</strong>
        <small>{contextDocumentSetId ?? "documentSetId 待生成"}</small>
      </div>
      <div className="p1-runtime-graph-edge">依据</div>
      <div className="p1-runtime-graph-node is-policy">
        <span>策略/动作依据</span>
        <strong>{policyLabel}</strong>
        <small>{currentStage?.label ?? "当前阶段来自后端"}</small>
      </div>
      <div className="p1-runtime-graph-edge">输出</div>
      <div className="p1-runtime-graph-node is-output">
        <span>输出对象</span>
        <strong>{runtimeSnapshotId ?? "runtimeSnapshotId 待生成"}</strong>
        <small>{runtime?.publication_candidate_status?.candidate_snapshot_id ? "候选快照已投影" : "运行快照供下游消费"}</small>
      </div>
    </div>
  );
}

export function RuntimePage({ context }: P1ModulePageProps) {
  const { refreshArchives } = useArchiveContext();
  const [documents, setDocuments] = useState<RuntimeDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<RuntimeContract | null>(null);
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [transport, setTransport] = useState<RuntimeTransportStatus>("idle");
  const [lastRuntimeAt, setLastRuntimeAt] = useState<string | null>(null);
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<string | null>(null);
  const [runtimeRefreshKey, setRuntimeRefreshKey] = useState(0);
  const [runtimeStarting, setRuntimeStarting] = useState(false);

  const hasRuntimeInputs = Boolean(context.documentSetId && context.policyPackageVersionId);

  useEffect(() => {
    let cancelled = false;
    setDocumentsLoading(true);
    setDocumentsError(null);

    runtimeApi
      .getRuntimeDocuments(context.archiveId)
      .then((response) => {
        if (cancelled) return;
        const nextDocuments = mergeRuntimeDocuments(context, response.data);
        const preferredDocumentId = context.archive.build_state?.current_document_id;
        const nextSelectedDocumentId =
          (preferredDocumentId && nextDocuments.some((document) => document.id === preferredDocumentId)
            ? preferredDocumentId
            : null) ??
          nextDocuments[0]?.id ??
          null;

        setDocuments(nextDocuments);
        setSelectedDocumentId((current) =>
          current && nextDocuments.some((document) => document.id === current) ? current : nextSelectedDocumentId,
        );
      })
      .catch((error) => {
        if (cancelled) return;
        setDocuments([]);
        setSelectedDocumentId(null);
        setDocumentsError(toErrorMessage(error));
      })
      .finally(() => {
        if (!cancelled) {
          setDocumentsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [context, context.archive.build_state?.current_document_id, context.archiveId, runtimeRefreshKey]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setRuntime(null);
      setTransport("idle");
      return;
    }

    if (!hasRuntimeInputs) {
      setRuntime(null);
      setTransport("unavailable");
      return;
    }

    let cancelled = false;
    let pollingStarted = false;
    let pollingTimer: number | undefined;
    let subscription: { close: () => void } | null = null;

    const input = {
      archiveId: context.archiveId,
      documentId: selectedDocumentId,
      documentSetId: context.documentSetId ?? undefined,
      policyPackageVersionId: context.policyPackageVersionId ?? undefined,
    };

    const fetchRuntime = async () => {
      const response = await runtimeApi.getRuntimeContract(input);
      if (cancelled) return;
      setRuntime(response.data);
      setRuntimeError(null);
      setLastRuntimeAt(new Date().toISOString());
    };

    const startPolling = () => {
      if (pollingStarted || cancelled) return;
      pollingStarted = true;
      setTransport("polling");
      void fetchRuntime().catch((error) => {
        if (!cancelled) {
          setRuntimeError(toErrorMessage(error));
          setTransport("error");
        }
      });
      pollingTimer = window.setInterval(() => {
        void fetchRuntime().catch((error) => {
          if (!cancelled) {
            setRuntimeError(toErrorMessage(error));
          }
        });
      }, RUNTIME_POLLING_INTERVAL_MS);
    };

    const connect = async () => {
      setRuntimeLoading(true);
      setRuntimeError(null);
      setTransport("connecting");

      try {
        await fetchRuntime();
      } catch (error) {
        if (!cancelled) {
          setRuntimeError(toErrorMessage(error));
        }
      } finally {
        if (!cancelled) {
          setRuntimeLoading(false);
        }
      }

      if (cancelled) return;

      if (!runtimeApi.canUseRuntimeStream()) {
        startPolling();
        return;
      }

      try {
        subscription = runtimeApi.subscribeRuntimeContract(
          input,
          {
            onRuntime: (nextRuntime) => {
              if (cancelled) return;
              setRuntime(nextRuntime);
              setRuntimeError(null);
              setTransport("streaming");
              setLastRuntimeAt(new Date().toISOString());
            },
            onHeartbeat: () => {
              if (!cancelled) {
                setTransport("streaming");
                setLastHeartbeatAt(new Date().toISOString());
              }
            },
            onError: (error) => {
              if (cancelled) return;
              subscription?.close();
              setRuntimeError(`运行流断开：${toErrorMessage(error)}。已切换到轮询。`);
              startPolling();
            },
          },
          {
            intervalMs: RUNTIME_STREAM_INTERVAL_MS,
            heartbeatMs: RUNTIME_HEARTBEAT_MS,
          },
        );
      } catch (error) {
        if (!cancelled) {
          setRuntimeError(`运行流不可用：${toErrorMessage(error)}。已切换到轮询。`);
          startPolling();
        }
      }
    };

    void connect();

    return () => {
      cancelled = true;
      subscription?.close();
      if (pollingTimer !== undefined) {
        window.clearInterval(pollingTimer);
      }
    };
  }, [context.archiveId, context.documentSetId, context.policyPackageVersionId, hasRuntimeInputs, runtimeRefreshKey, selectedDocumentId]);

  const currentStage = useMemo(() => getCurrentStage(runtime), [runtime]);
  const currentStageIndex = runtime?.stages.findIndex((stage) => stage.stage_id === currentStage?.stage_id) ?? -1;
  const runtimeEvents = useMemo(() => collectRuntimeEvents(runtime), [runtime]);
  const runtimeSnapshotId = getRuntimeSnapshotId(runtime, context.runtimeSnapshotId);
  const selectedDocument = documents.find((document) => document.id === selectedDocumentId) ?? null;
  const archiveRuntimeSummary = useMemo(() => getArchiveRuntimeSummary(context, documents), [context, documents]);
  const archiveDocumentStateMap = useMemo(() => getArchiveDocumentStateMap(context), [context]);
  const archiveWarnings = context.archive.build_state?.warnings ?? [];
  const documentOptions = useMemo(
    () =>
      documents.map((document) => {
        const state = archiveDocumentStateMap.get(document.id);
        return {
          label: state ? `${document.title} · ${state}` : document.title,
          value: document.id,
          disabled: state === "skipped" || state === "failed" || document.included_in_archive === false,
        };
      }),
    [archiveDocumentStateMap, documents],
  );
  const transportInfo = transportMeta[transport];
  const primaryNodes =
    runtime?.graph_projection?.nodes.filter((node) => node.is_primary).slice(0, 6) ??
    currentStage?.graph.nodes.filter((node) => node.is_primary).slice(0, 6) ??
    [];
  const primaryEdges =
    runtime?.graph_projection?.edges.filter((edge) => edge.is_primary).slice(0, 6) ??
    currentStage?.graph.edges.filter((edge) => edge.is_primary).slice(0, 6) ??
    [];
  const currentObject = getCurrentObject(runtime);
  const currentRelation = getCurrentRelation(runtime);
  const latestEvent = runtimeEvents[0] ?? null;
  const currentObjectLabel = currentObject
    ? "candidate_type" in currentObject
      ? `${currentObject.label} / ${currentObject.candidate_type}`
      : `${currentObject.label} / ${currentObject.node_type}`
    : "等待对象候选";
  const currentRelationLabel = currentRelation
    ? "candidate_type" in currentRelation
      ? `${currentRelation.label} / ${formatUnknown(currentRelation.attributes.source_name, "源对象")} -> ${formatUnknown(
          currentRelation.attributes.target_name,
          "目标对象",
        )}`
      : `${currentRelation.relation} / ${currentRelation.source} -> ${currentRelation.target}`
    : "等待关系候选";

  const handleStartRuntime = async () => {
    setRuntimeStarting(true);
    setRuntimeError(null);
    try {
      await runtimeApi.startRuntimeExtraction(context.archiveId);
      await refreshArchives(context.archiveId);
      setRuntimeRefreshKey((value) => value + 1);
    } catch (error) {
      setRuntimeError(`启动运行失败：${toErrorMessage(error)}`);
    } finally {
      setRuntimeStarting(false);
    }
  };

  return (
    <PageFrame
      eyebrow="抽取运行模块"
      title="抽取运行"
      description="消费 archiveId、documentSetId、policyPackageVersionId，展示后端实时运行事实、运行事件流和运行态语义图谱。"
    >
      {!hasRuntimeInputs && (
        <Alert
          className="p1-clean-alert"
          type="warning"
          showIcon
          message="等待运行输入合同"
          description="运行模块只消费 documentSetId 和 policyPackageVersionId；输入未齐备时不会伪造阶段状态。"
        />
      )}
      {documentsError && <Alert className="p1-clean-alert" type="error" showIcon message="文档集合读取失败" description={documentsError} />}
      {runtimeError && <Alert className="p1-clean-alert" type="warning" showIcon message="运行连接提示" description={runtimeError} />}

      <Card
        className="p1-clean-card"
        title="知识库抽取总控"
        extra={
          <Space>
            <Button onClick={() => setRuntimeRefreshKey((value) => value + 1)}>刷新</Button>
            <Button
              type="primary"
              loading={runtimeStarting}
              onClick={handleStartRuntime}
              disabled={!context.policyPackageVersionId}
            >
              启动知识库抽取
            </Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} md={4}>
            <Statistic title="运行状态" value={archiveRuntimeSummary.status} valueStyle={{ fontSize: 20 }} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="文档总数" value={archiveRuntimeSummary.expectedCount} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="已完成" value={archiveRuntimeSummary.completedCount} valueStyle={{ color: "#237804" }} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="已跳过" value={archiveRuntimeSummary.skippedCount} valueStyle={{ color: "#ad6800" }} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="待处理" value={archiveRuntimeSummary.pendingCount} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="告警" value={archiveRuntimeSummary.warningCount} valueStyle={{ color: "#cf1322" }} />
          </Col>
        </Row>
        <Space direction="vertical" size={8} style={{ marginTop: 16, width: "100%" }}>
          <Space wrap>
            <Tag color={statusColor[archiveRuntimeSummary.status] ?? "default"}>{archiveRuntimeSummary.status}</Tag>
            <Typography.Text>
              当前文档：{archiveRuntimeSummary.currentDocumentTitle ?? "无正在运行的文档"}
            </Typography.Text>
            <Typography.Text>
              当前阶段：{archiveRuntimeSummary.currentStageLabel ?? "无正在运行的阶段"}
            </Typography.Text>
          </Space>
          {archiveRuntimeSummary.currentStageMessage ? (
            <Typography.Text type="secondary">{archiveRuntimeSummary.currentStageMessage}</Typography.Text>
          ) : null}
          {archiveWarnings.length > 0 ? (
            <Alert
              type="warning"
              showIcon
              message={`本次抽取产生 ${archiveWarnings.length} 条告警`}
              description={
                <Space direction="vertical" size={2}>
                  {archiveWarnings.slice(0, 4).map((warning) => (
                    <Typography.Text key={`${warning.code}:${warning.file_path}`}>
                      {warning.file_path}：{warning.reason ?? warning.message}
                    </Typography.Text>
                  ))}
                </Space>
              }
            />
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card
            className="p1-clean-card"
            title="单文档观察"
            extra={
              <Space>
                <Button
                  aria-label="刷新运行"
                  onClick={() => setRuntimeRefreshKey((value) => value + 1)}
                  disabled={!selectedDocumentId}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <Space direction="vertical" size={14} className="p1-runtime-stack">
              <div className="p1-runtime-field">
                <Typography.Text type="secondary">运行文档</Typography.Text>
                <Select
                  loading={documentsLoading}
                  value={selectedDocumentId ?? undefined}
                  placeholder="选择文档下钻"
                  onChange={setSelectedDocumentId}
                  options={documentOptions}
                />
              </div>
              <div className="p1-runtime-kv">
                <span>archiveId</span>
                <strong>{context.archiveId}</strong>
                <span>documentSetId</span>
                <strong>{context.documentSetId ?? "等待资料接入输出"}</strong>
                <span>policyPackageVersionId</span>
                <strong>{context.policyPackageVersionId ?? "等待策略冻结"}</strong>
                <span>runtimeSnapshotId</span>
                <strong>{runtimeSnapshotId ?? "运行后生成"}</strong>
              </div>
              <Alert
                type={transport === "streaming" ? "success" : transport === "polling" ? "warning" : "info"}
                showIcon
                message={
                  <Space>
                    <Badge status={transportInfo.color as "default" | "processing" | "success" | "warning" | "error"} />
                    <span>{transportInfo.text}</span>
                    <Tag color={transportInfo.color}>{transportInfo.label}</Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={2}>
                    <Typography.Text>最近运行刷新：{lastRuntimeAt ?? "等待首次响应"}</Typography.Text>
                    <Typography.Text>最近心跳：{lastHeartbeatAt ?? "等待 stream heartbeat"}</Typography.Text>
                  </Space>
                }
              />
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card className="p1-clean-card" title="当前阶段">
            {runtimeLoading && !runtime ? (
              <Spin />
            ) : currentStage ? (
              <Space direction="vertical" size={14} className="p1-runtime-stack">
                <Space wrap>
                  <Tag color={statusColor[currentStage.status]}>{currentStage.status}</Tag>
                  <Typography.Text strong>{runtime?.current_stage_label ?? currentStage.label}</Typography.Text>
                </Space>
                <Typography.Paragraph className="p1-runtime-message">
                  {runtime?.current_stage_message ?? currentStage.stage_observer.subtitle ?? "当前阶段来自后端运行状态。"}
                </Typography.Paragraph>
                <div className="p1-runtime-kv">
                  <span>stageId</span>
                  <strong>{currentStage.stage_id}</strong>
                  <span>runtimeMode</span>
                  <strong>{runtime?.runtime_mode ?? "derived"}</strong>
                  <span>runtimeStatus</span>
                  <strong>{runtime?.runtime_status ?? runtime?.status ?? "pending"}</strong>
                  <span>currentRule</span>
                  <strong>{runtime?.current_stage_or_rule_id ?? currentStage.stage_id}</strong>
                  <span>persistedStages</span>
                  <strong>{runtime?.persisted_stage_ids?.length ?? 0}</strong>
                  <span>ruleRecords</span>
                  <strong>{runtime?.rule_execution_records?.length ?? 0}</strong>
                </div>
              </Space>
            ) : (
              <Empty description={selectedDocument ? "等待运行态响应" : "暂无可运行文档"} />
            )}
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card className="p1-clean-card" title="运行消息">
            {currentStage?.stage_observer.sections.length ? (
              <List
                className="p1-runtime-sections"
                dataSource={currentStage.stage_observer.sections}
                renderItem={(section) => (
                  <List.Item>
                    <List.Item.Meta
                      title={section.title}
                      description={
                        <div className="p1-runtime-kv is-compact">
                          {section.fields.map((field) => (
                            <span key={field.key} className="p1-runtime-pair">
                              <Typography.Text type="secondary">{field.label}</Typography.Text>
                              <Typography.Text>{field.value}</Typography.Text>
                            </span>
                          ))}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无运行消息" />
            )}
          </Card>
        </Col>
      </Row>

      <Card className="p1-clean-card p1-runtime-row" title="实时焦点">
        <div className="p1-runtime-focus-grid">
          <div>
            <Typography.Text type="secondary">当前文档</Typography.Text>
            <strong>{runtime?.document_title ?? selectedDocument?.title ?? "等待运行文档"}</strong>
            <small>{runtime?.current_document_id ?? selectedDocumentId ?? "documentId 待选择"}</small>
          </div>
          <div>
            <Typography.Text type="secondary">当前规则</Typography.Text>
            <strong>{runtime?.current_stage_or_rule_id ?? currentStage?.stage_id ?? "等待规则执行"}</strong>
            <small>{runtime?.current_stage_label ?? currentStage?.label ?? "阶段待定位"}</small>
          </div>
          <div>
            <Typography.Text type="secondary">当前事件</Typography.Text>
            <strong>{latestEvent ? runtimeEventLabels[latestEvent.event_type] ?? latestEvent.event_type : "等待事件"}</strong>
            <small>{latestEvent?.message ?? "事件流连接后更新"}</small>
          </div>
          <div>
            <Typography.Text type="secondary">当前对象</Typography.Text>
            <strong>{currentObjectLabel}</strong>
            <small>{runtime?.generated_candidates?.length ?? 0} 个候选</small>
          </div>
          <div>
            <Typography.Text type="secondary">当前关系</Typography.Text>
            <strong>{currentRelationLabel}</strong>
            <small>{runtime?.graph_projection?.edge_count ?? primaryEdges.length} 条投影关系</small>
          </div>
        </div>
      </Card>

      <Row gutter={[16, 16]} className="p1-runtime-row">
        <Col xs={24} xl={14}>
          <Card className="p1-clean-card" title="运行态语义图谱快照">
            <RuntimeGraphProjection
              contextDocumentSetId={context.documentSetId}
              policyPackageVersionId={context.policyPackageVersionId}
              runtime={runtime}
              runtimeSnapshotId={runtimeSnapshotId}
            />
            <div className="p1-runtime-stage-graph">
              <div>
                <Typography.Text type="secondary">当前阶段主对象</Typography.Text>
                {primaryNodes.length ? (
                  <List
                    size="small"
                    dataSource={primaryNodes}
                    renderItem={(node) => (
                      <List.Item>
                        <Space wrap>
                          <Tag color={statusColor[node.status]}>{node.status}</Tag>
                          <Typography.Text>{node.label}</Typography.Text>
                          <Typography.Text type="secondary">{node.node_type}</Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无主对象" />
                )}
              </div>
              <div>
                <Typography.Text type="secondary">当前阶段主关系</Typography.Text>
                {primaryEdges.length ? (
                  <List
                    size="small"
                    dataSource={primaryEdges}
                    renderItem={(edge) => (
                      <List.Item>
                        <Space wrap>
                          <Tag color={statusColor[edge.status]}>{edge.status}</Tag>
                          <Typography.Text>{edge.relation}</Typography.Text>
                          <Typography.Text type="secondary">{`${edge.source} -> ${edge.target}`}</Typography.Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无主关系" />
                )}
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} xl={10}>
          <Card className="p1-clean-card" title="阶段状态">
            {runtime?.stages.length ? (
              <Steps
                direction="vertical"
                current={currentStageIndex}
                items={runtime.stages.map((stage) => ({
                  title: stage.label,
                  status: getStageStepStatus(stage),
                  description: (
                    <Space wrap>
                      <Tag color={statusColor[stage.status]}>{stage.status}</Tag>
                      <Typography.Text type="secondary">{stage.group}</Typography.Text>
                    </Space>
                  ),
                }))}
              />
            ) : (
              <Empty description="等待后端阶段状态" />
            )}
          </Card>
        </Col>
      </Row>

      <Card className="p1-clean-card p1-runtime-row" title="运行事件流">
        {runtimeEvents.length ? (
          <Timeline
            items={runtimeEvents.map((event: RuntimeDisplayEvent) => ({
              color: levelColor[event.level] ?? "blue",
              children: (
                <Space direction="vertical" size={2}>
                  <Space wrap>
                    <Tag color={levelColor[event.level] ?? "blue"}>
                      {runtimeEventLabels[event.event_type] ?? event.event_type}
                    </Tag>
                    <Typography.Text strong>{event.stage_label}</Typography.Text>
                    <Typography.Text type="secondary">{event.timestamp ?? "实时投影"}</Typography.Text>
                  </Space>
                  <Typography.Text>{event.message}</Typography.Text>
                </Space>
              ),
            }))}
          />
        ) : (
          <Empty description="暂无运行事件" />
        )}
      </Card>
    </PageFrame>
  );
}
