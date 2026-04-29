import { startTransition, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { buildP6CssVariables, resolveP6FeedbackCopy, resolveP6StageName } from "../components/p6/p6Baseline";
import {
  getP6DisplayBaseline,
  getP6ObservationProjection,
  getP6PlatformRoutes,
  listP6MockScenarios,
  type P6MockScenarioCatalog,
  type P6ObservationProjectionReadEnvelope,
  type P6PlatformDisplayBaselinePackage,
  type P6PlatformRoutes,
  type P6SourceMode,
} from "../lib/p6";

import "./P6ObservationPage.css";

function toneClassName(tone: string) {
  return `p6-observation-chip--${tone}`;
}

export function P6ObservationPage() {
  const navigate = useNavigate();
  const [sourceMode] = useState<P6SourceMode>("mock");
  const [scenarioCatalog, setScenarioCatalog] = useState<P6MockScenarioCatalog | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState("baseline");
  const [projectionEnvelope, setProjectionEnvelope] = useState<P6ObservationProjectionReadEnvelope | null>(null);
  const [baselinePackage, setBaselinePackage] = useState<P6PlatformDisplayBaselinePackage | null>(null);
  const [platformRoutes, setPlatformRoutes] = useState<P6PlatformRoutes | null>(null);
  const [focusStageId, setFocusStageId] = useState("P2");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadSharedConfig() {
      setLoading(true);
      try {
        const [catalogResponse, baselineResponse, routesResponse] = await Promise.all([
          listP6MockScenarios(),
          getP6DisplayBaseline(),
          getP6PlatformRoutes(),
        ]);
        if (cancelled) {
          return;
        }

        const catalog = catalogResponse.data;
        startTransition(() => {
          setScenarioCatalog(catalog);
          setBaselinePackage(baselineResponse.data);
          setPlatformRoutes(routesResponse.data);
          setSelectedScenarioId((current) =>
            catalog.items.some((item) => item.scenario_id === current) ? current : catalog.default_scenario_id,
          );
        });
        setError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载串行观察配置失败");
        setLoading(false);
      }
    }

    void loadSharedConfig();

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  useEffect(() => {
    if (!scenarioCatalog || !baselinePackage || !platformRoutes) {
      return undefined;
    }

    let cancelled = false;

    async function loadProjection() {
      setLoading(true);
      try {
        const response = await getP6ObservationProjection({
          source: sourceMode,
          scenario: selectedScenarioId,
        });
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setProjectionEnvelope(response.data);
          setFocusStageId(response.data.projection.focus_stage_id);
        });
        setError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载串行观察投影失败");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [baselinePackage, platformRoutes, scenarioCatalog, selectedScenarioId, sourceMode]);

  const focusStageCard = useMemo(
    () => projectionEnvelope?.projection.stage_cards.find((item) => item.stage_id === focusStageId) ?? null,
    [focusStageId, projectionEnvelope],
  );

  if (!projectionEnvelope || !baselinePackage || !platformRoutes) {
    return (
      <div className="p6-observation-page p6-observation-page--status" style={buildP6CssVariables(baselinePackage)}>
        <div className="p6-observation-status-card">
          <div className="p6-observation-status-card__title">{error ? "串行观察加载失败" : "正在加载串行观察页"}</div>
          <div className="p6-observation-status-card__text">
            {error ?? "正在装载 P6 观察投影、平台基线与路由映射，请稍候。"}
          </div>
          <button type="button" className="p6-observation-status-card__button" onClick={() => setReloadKey((current) => current + 1)}>
            重试加载
          </button>
        </div>
      </div>
    );
  }

  const { projection } = projectionEnvelope;

  return (
    <div className="p6-observation-page" style={buildP6CssVariables(baselinePackage)}>
      <header className="p6-observation-hero">
        <div>
          <span className="p6-observation-hero__badge">P6.2</span>
          <h1 className="p6-observation-hero__title">P6 串行观察页</h1>
          <p className="p6-observation-hero__text">
            统一消费 ObservationProjection、平台展示基线与路由映射，对五阶段状态进行顺序观察、告警归纳与跨阶段比对。
          </p>
        </div>
        <div className="p6-observation-hero__actions">
          {scenarioCatalog?.items.map((item) => (
            <button
              key={item.scenario_id}
              type="button"
              className={["p6-observation-switch", item.scenario_id === selectedScenarioId ? "is-active" : ""].filter(Boolean).join(" ")}
              onClick={() => setSelectedScenarioId(item.scenario_id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <section className="p6-observation-panel">
        <div className="p6-observation-panel__title">平台总览条</div>
        <div className="p6-observation-overview">
          <div className="p6-observation-overview__item">
            <span>当前场景</span>
            <strong>{projectionEnvelope.scenario.label}</strong>
          </div>
          <div className="p6-observation-overview__item">
            <span>聚焦阶段</span>
            <strong>{resolveP6StageName(baselinePackage, focusStageId, focusStageCard?.stage_name ?? focusStageId)}</strong>
          </div>
          <div className="p6-observation-overview__item">
            <span>数据新鲜度</span>
            <strong>{projection.freshness === "fresh" ? "新鲜" : projection.freshness === "stale" ? "过期" : "未知"}</strong>
          </div>
          <div className="p6-observation-overview__item">
            <span>反馈提示</span>
            <strong>{resolveP6FeedbackCopy(baselinePackage, "focus", "切换聚焦阶段以查看比对差异。")}</strong>
          </div>
        </div>
      </section>

      <section className="p6-observation-panel">
        <div className="p6-observation-panel__title">串行观察卡片区</div>
        <div className="p6-observation-stage-grid">
          {projection.stage_cards.map((card) => (
            <button
              key={card.stage_id}
              type="button"
              data-testid={`p6-observation-stage-card-${card.stage_id}`}
              data-active={focusStageId === card.stage_id ? "true" : "false"}
              className={["p6-observation-stage-card", focusStageId === card.stage_id ? "is-active" : ""].filter(Boolean).join(" ")}
              onClick={() => setFocusStageId(card.stage_id)}
            >
              <div className="p6-observation-stage-card__topline">
                <span>{card.stage_id}</span>
                <span className={["p6-observation-chip", toneClassName(card.health_badge.tone)].join(" ")}>{card.health_badge.label}</span>
              </div>
              <div className="p6-observation-stage-card__title">
                {resolveP6StageName(baselinePackage, card.stage_id, card.stage_name)}
              </div>
              <div className="p6-observation-stage-card__headline">{card.headline_value}</div>
              <div className="p6-observation-stage-card__summary">{card.summary_line}</div>
              <div className="p6-observation-stage-card__footer">
                <span>{card.timestamp_label}</span>
                <span className={["p6-observation-chip", toneClassName(card.entry_badge.tone)].join(" ")}>{card.entry_badge.label}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <div className="p6-observation-columns">
        <section className="p6-observation-panel">
          <div className="p6-observation-panel__title">阶段告警区</div>
          <div className="p6-observation-alert">
            <div className="p6-observation-alert__count">{projection.alert_summary.total}</div>
            <div className="p6-observation-alert__message">{projection.alert_summary.message}</div>
            <div className="p6-observation-alert__badges">
              {projection.alert_summary.warning_stage_ids.map((stageId) => (
                <span key={stageId} className="p6-observation-chip p6-observation-chip--warning">
                  {stageId}
                </span>
              ))}
              {projection.alert_summary.blocked_stage_ids.map((stageId) => (
                <span key={stageId} className="p6-observation-chip p6-observation-chip--blocked">
                  {stageId}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="p6-observation-panel">
          <div className="p6-observation-panel__title">降级说明区</div>
          <div className="p6-observation-degraded">
            {projection.degraded_reason ?? resolveP6FeedbackCopy(baselinePackage, "empty", "无数据")}
          </div>
        </section>
      </div>

      <section className="p6-observation-panel">
        <div className="p6-observation-panel__title">跨阶段对比区</div>
        <div className="p6-observation-comparison">
          {projection.comparison_items.map((item) => (
            <div key={item.comparison_id} className="p6-observation-comparison__item">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="p6-observation-panel">
        <div className="p6-observation-panel__title">路由动作区</div>
        <div className="p6-observation-actions">
          {projection.route_actions.map((item) => (
            <button
              key={item.stage_id}
              type="button"
              className="p6-observation-switch"
              disabled={!item.route_available}
              onClick={() => navigate(platformRoutes.stage_routes[item.stage_id]?.path ?? item.route)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {loading ? <div className="p6-observation-loading">刷新中</div> : null}
      {error ? <div className="p6-observation-loading">{error}</div> : null}
    </div>
  );
}
