import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  getP6PortalDataView,
  type P6PortalDataFlowSeries,
  type P6PortalDataStageRow,
  type P6PortalDataViewReadEnvelope,
} from "../lib/p6";

import "./P6PortalDataPage.css";

const toneLabel: Record<string, string> = {
  knowledge: "知识",
  analysis: "规格",
  design: "设计",
  tooling: "工具",
  delivery: "交付",
};

function formatMetricValue(value: number | string, unit: string) {
  return `${value}${unit}`;
}

function formatCapturedAt(value: string) {
  if (!value) {
    return "未记录";
  }
  return value.replace("T", " ").replace("+08:00", "");
}

function FlowSeriesStrip({ series }: { series: P6PortalDataFlowSeries }) {
  const latestPoint = series.points.at(-1);
  const maxValue = Math.max(1, ...series.points.map((point) => point.value));

  return (
    <article className={`p6-data-flow p6-data-flow--${series.render_tone}`}>
      <div className="p6-data-flow__head">
        <span>{series.label}</span>
        <strong>{series.payload_label}</strong>
      </div>
      <div className="p6-data-flow__rail" aria-label={`${series.label} ${series.payload_label} 历史点`}>
        {series.points.map((point, index) => (
          <span
            key={`${point.flow_id}-${point.captured_at}-${index}`}
            className="p6-data-flow__point"
            style={{ height: `${Math.max(14, Math.round((point.value / maxValue) * 36))}px` }}
            title={`${point.payload_label} ${point.rate_label}`}
          />
        ))}
      </div>
      <div className="p6-data-flow__foot">
        <span>{toneLabel[series.render_tone] ?? series.render_tone}</span>
        <b>{latestPoint ? latestPoint.rate_label : "无历史点"}</b>
      </div>
    </article>
  );
}

function StageRow({ row, active, onSelect }: { row: P6PortalDataStageRow; active: boolean; onSelect: () => void }) {
  return (
    <tr
      aria-label={`${row.stage_id} ${row.stage_name} 阶段行`}
      className={active ? "is-active" : ""}
      onClick={onSelect}
      tabIndex={0}
    >
      <td>
        <span className={`p6-data-stage-dot p6-data-stage-dot--${row.health_level}`} />
        <strong>{row.stage_id}</strong>
        <small>{row.stage_name}</small>
      </td>
      <td>{row.overall_status}</td>
      <td>{row.realtime_input || "无实时输入"}</td>
      <td>{row.output_flow || "无输出流"}</td>
      <td>{row.connected_user_count}</td>
      <td>{row.queue_item_count}</td>
    </tr>
  );
}

export function P6PortalDataPage() {
  const [searchParams] = useSearchParams();
  const scenarioId = searchParams.get("scenario") ?? "baseline";
  const [selectedStageId, setSelectedStageId] = useState(searchParams.get("selected_stage_id") ?? "P3");
  const [envelope, setEnvelope] = useState<P6PortalDataViewReadEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    async function loadPortalData() {
      try {
        const response = await getP6PortalDataView({
          source: "mock",
          scenario: scenarioId,
          selected_stage_id: selectedStageId,
        });
        if (cancelled) {
          return;
        }
        setEnvelope(response.data);
        setError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载 P6 数据视图失败");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadPortalData();

    return () => {
      cancelled = true;
    };
  }, [scenarioId, selectedStageId]);

  const view = envelope?.view;
  const selectedDetail = view?.selected_stage_detail;
  const portalPath = `/portal?scenario=${scenarioId}`;
  const hasHistory = (view?.history_sample_count ?? 0) > 0;
  const totalFlowPoints = useMemo(
    () => view?.flow_series.reduce((total, series) => total + series.points.length, 0) ?? 0,
    [view],
  );

  if (!view || !selectedDetail) {
    return (
      <main className="p6-data-page p6-data-page--status">
        <section className="p6-data-status-panel">
          <h1>{error ? "数据视图加载失败" : "正在加载五阶段数据视图"}</h1>
          <p>{error ?? "正在读取同源展示合同、阶段总表和模拟历史样本。"}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="p6-data-page">
      <header className="p6-data-header">
        <div>
          <p>P6 / portal-data / {view.scenario_summary.source_label}</p>
          <h1>五阶段同源数据精确观察</h1>
          <span>
            {view.scenario_summary.label} · {loading ? "刷新中" : "已装载"} ·{" "}
            {formatCapturedAt(view.scenario_summary.captured_at)}
          </span>
        </div>
        <nav aria-label="P6 数据视图动作">
          <Link to={portalPath}>返回语义画布</Link>
          <Link to="/xx-p6-sim">模拟发生器</Link>
        </nav>
      </header>

      <section className="p6-data-summary-grid" aria-label="场景摘要">
        <article>
          <span>阶段</span>
          <strong>{view.scenario_summary.stage_count}</strong>
        </article>
        <article>
          <span>跨阶段流</span>
          <strong>{view.scenario_summary.flow_count}</strong>
        </article>
        <article>
          <span>接入用户</span>
          <strong>{view.scenario_summary.connected_user_count}</strong>
        </article>
        <article>
          <span>队列对象</span>
          <strong>{view.scenario_summary.queue_item_count}</strong>
        </article>
        <article>
          <span>历史样本</span>
          <strong>{view.scenario_summary.history_sample_count}</strong>
        </article>
      </section>

      <section className="p6-data-main-grid">
        <section className="p6-data-flow-panel" aria-label="跨阶段流量图">
          <div className="p6-data-section-title">
            <h2>跨阶段流量图</h2>
            <span>{hasHistory ? `${totalFlowPoints} 个历史点` : "0 个历史点"}</span>
          </div>
          {!hasHistory ? <div className="p6-data-empty-history">暂无历史样本</div> : null}
          <div className="p6-data-flow-grid">
            {view.flow_series.map((series) => (
              <FlowSeriesStrip key={series.flow_id} series={series} />
            ))}
          </div>
        </section>

        <aside className="p6-data-detail-panel">
          <div className="p6-data-section-title">
            <h2>{selectedDetail.stage_id} 下钻区</h2>
            <span>{selectedDetail.stage_name}</span>
          </div>
          <p className="p6-data-detail-panel__summary">{selectedDetail.summary}</p>
          <div className="p6-data-detail-metrics">
            {selectedDetail.overall_metrics.map((metric) => (
              <span key={metric.key}>
                {metric.label}
                <strong>{formatMetricValue(metric.value, metric.unit)}</strong>
              </span>
            ))}
          </div>
          <div className="p6-data-detail-list">
            <strong>展示端口</strong>
            {selectedDetail.flow_ports.map((port) => (
              <span key={port.port_id}>
                {port.direction === "input" ? "输入" : "输出"} · {port.label} · {port.connected_target} · {port.current_rate}
              </span>
            ))}
          </div>
          <div className="p6-data-detail-list">
            <strong>接入用户</strong>
            <span>{selectedDetail.connected_users.map((user) => user.role_label).join(" / ")}</span>
          </div>
          <div className="p6-data-detail-list">
            <strong>来源依据</strong>
            <span>{selectedDetail.source_trace[0]?.source_doc ?? "未提供 source_trace"}</span>
          </div>
        </aside>
      </section>

      <section className="p6-data-table-panel" aria-label="五阶段合同总表">
        <div className="p6-data-section-title">
          <h2>五阶段合同总表</h2>
          <span>点击阶段行切换下钻</span>
        </div>
        <div className="p6-data-table-scroll">
          <table>
            <thead>
              <tr>
                <th>阶段</th>
                <th>总体状态</th>
                <th>实时输入 / 处理</th>
                <th>输出流</th>
                <th>用户</th>
                <th>队列</th>
              </tr>
            </thead>
            <tbody>
              {view.stage_rows.map((row) => (
                <StageRow
                  key={row.stage_id}
                  row={row}
                  active={row.stage_id === selectedDetail.stage_id}
                  onSelect={() => setSelectedStageId(row.stage_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
