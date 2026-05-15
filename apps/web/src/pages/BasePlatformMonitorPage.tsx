import { useCallback, useState } from "react";

import {
  getPlatformExchangeMonitor,
  type PlatformExchangeArtifact,
  type PlatformExchangeConsumption,
  type PlatformExchangeMonitorSnapshot,
  type PlatformExchangeMonitorStage,
  type PlatformExchangeStageKey,
} from "../lib/platformExchange";
import { usePollingResource } from "../lib/usePollingResource";
import "./BasePlatformMonitorPage.css";

const STAGE_TITLES: Record<PlatformExchangeStageKey, string> = {
  P1: "业务知识库",
  P2: "需求分析系统",
  P3: "软件设计系统",
  P4: "工具仓库",
  P5: "软件构建系统",
};

const MONITOR_REFRESH_INTERVAL_MS = 1000;

export function BasePlatformMonitorPage() {
  const [snapshot, setSnapshot] = useState<PlatformExchangeMonitorSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadMonitorSnapshot = useCallback(async () => {
    const response = await getPlatformExchangeMonitor();
    return response.data;
  }, []);

  const { loading } = usePollingResource({
    intervalMs: MONITOR_REFRESH_INTERVAL_MS,
    load: loadMonitorSnapshot,
    onData: useCallback((nextSnapshot: PlatformExchangeMonitorSnapshot) => {
      setSnapshot(nextSnapshot);
      setError(null);
    }, []),
    onError: useCallback((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : "加载基础平台监控快照失败");
    }, []),
  });

  if (loading && snapshot === null) {
    return (
      <main className="base-platform-monitor base-platform-monitor-loading">
        <p>连接 Base Platform Monitor...</p>
      </main>
    );
  }

  if (error !== null && snapshot === null) {
    return (
      <main className="base-platform-monitor">
        <h1>Base Platform Monitor</h1>
        <p className="base-platform-monitor-subtitle">基础平台全阶段监控日志台</p>
        <section className="base-platform-monitor-error" role="alert">
          {error}
        </section>
      </main>
    );
  }

  if (snapshot === null) {
    return null;
  }

  return (
    <main className="base-platform-monitor">
      <header className="base-platform-monitor-header">
        <p className="base-platform-monitor-eyebrow">Base Platform</p>
        <h1>Base Platform Monitor</h1>
        <p className="base-platform-monitor-subtitle">基础平台全阶段监控日志台</p>
      </header>

      <div className="base-platform-monitor-grid" aria-live="polite">
        {snapshot.stages.map((stage) => (
          <StageLogPanel key={stage.stage} stage={stage} />
        ))}
        <BasePlatformLedger snapshot={snapshot} />
      </div>
    </main>
  );
}

function StageLogPanel({ stage }: { stage: PlatformExchangeMonitorStage }) {
  const title = STAGE_TITLES[stage.stage] ?? "未命名分系统";
  const hasLogs = stage.published.length > 0 || stage.consumed.length > 0;

  return (
    <section className="base-platform-log-panel" data-testid={`base-platform-stage-${stage.stage}`}>
      <header className="base-platform-panel-header">
        <div>
          <p>{stage.stage}</p>
          <h2>{title}</h2>
        </div>
        <span>{stage.published.length + stage.consumed.length} logs</span>
      </header>

      <div className="base-platform-log-stream">
        {hasLogs ? (
          <>
            {stage.published.map((artifact) => (
              <code className="base-platform-log-line" key={`artifact-${artifact.artifact_id}`}>
                {formatArtifactLog(stage.stage, artifact)}
              </code>
            ))}
            {stage.consumed.map((consumption) => (
              <code className="base-platform-log-line" key={`consumption-${consumption.consumption_id}`}>
                {formatConsumptionLog(stage.stage, consumption)}
              </code>
            ))}
          </>
        ) : (
          <code className="base-platform-log-line base-platform-log-empty">
            {stage.empty_state ?? "暂无平台资源 / 暂无消费记录 / 未接入首版链路"}
          </code>
        )}
      </div>
    </section>
  );
}

function BasePlatformLedger({ snapshot }: { snapshot: PlatformExchangeMonitorSnapshot }) {
  return (
    <section className="base-platform-log-panel base-platform-ledger" data-testid="base-platform-ledger">
      <header className="base-platform-panel-header">
        <div>
          <p>Base Platform</p>
          <h2>平台资源底账</h2>
        </div>
        <span>read only</span>
      </header>

      <div className="base-platform-ledger-grid">
        <LedgerBlock title="资源类型">{renderCountRows(snapshot.base_platform.artifact_totals.by_type)}</LedgerBlock>
        <LedgerBlock title="生产阶段">
          {renderCountRows(snapshot.base_platform.artifact_totals.by_producer_stage)}
        </LedgerBlock>
        <LedgerBlock title="生命周期">
          {renderCountRows(snapshot.base_platform.artifact_totals.by_lifecycle_status)}
        </LedgerBlock>
        <LedgerBlock title="消费阶段">
          {renderCountRows(snapshot.base_platform.consumption_totals.by_consumer_stage)}
        </LedgerBlock>
        <LedgerBlock title="消费结果">
          {renderCountRows(snapshot.base_platform.consumption_totals.by_result_status)}
        </LedgerBlock>
      </div>

      <div className="base-platform-ledger-stream">
        {snapshot.base_platform.latest_artifacts.map((artifact) => (
          <code className="base-platform-log-line" key={`ledger-artifact-${artifact.artifact_id}`}>
            {formatPlatformArtifactLog(artifact)}
          </code>
        ))}
        {snapshot.base_platform.latest_consumptions.map((consumption) => (
          <code className="base-platform-log-line" key={`ledger-consumption-${consumption.consumption_id}`}>
            {formatPlatformConsumptionLog(consumption)}
          </code>
        ))}
      </div>
    </section>
  );
}

function LedgerBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="base-platform-ledger-block">
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  );
}

function renderCountRows(counts: Record<string, number>) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return <p className="base-platform-ledger-empty">0</p>;
  }
  return entries.map(([key, value]) => (
    <p className="base-platform-ledger-count" key={key}>
      {key}: {value}
    </p>
  ));
}

function formatArtifactLog(stage: string, artifact: PlatformExchangeArtifact) {
  return [
    formatInstant(artifact.published_at),
    stage,
    `发布 ${artifact.artifact_type}`,
    `artifact=${artifact.artifact_id}`,
    `version=${artifact.artifact_version}`,
    `hash=${artifact.payload_hash}`,
  ].join("  ");
}

function formatConsumptionLog(stage: string, consumption: PlatformExchangeConsumption) {
  return [
    formatInstant(consumption.consumed_at),
    stage,
    `消费 artifact=${consumption.artifact_id}`,
    `session=${consumption.consumer_ref_id}`,
    `status=${consumption.result_status}`,
  ].join("  ");
}

function formatPlatformArtifactLog(artifact: PlatformExchangeArtifact) {
  return [
    formatInstant(artifact.published_at),
    "Base Platform",
    `存储 artifact=${artifact.artifact_id}`,
    `from=${artifact.producer_stage}`,
    `type=${artifact.artifact_type}`,
    `status=${artifact.lifecycle_status}`,
  ].join("  ");
}

function formatPlatformConsumptionLog(consumption: PlatformExchangeConsumption) {
  return [
    formatInstant(consumption.consumed_at),
    "Base Platform",
    `记录消费 artifact=${consumption.artifact_id}`,
    `by=${consumption.consumer_stage}`,
    `status=${consumption.result_status}`,
  ].join("  ");
}

function formatInstant(value: string | null | undefined) {
  if (!value) {
    return "time=unknown";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}
