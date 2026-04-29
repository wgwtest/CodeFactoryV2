import { startTransition, useEffect, useState } from "react";

import { P6BlueprintCanvas } from "../components/p6/P6BlueprintCanvas";
import { useArchiveContext } from "../context/ArchiveContext";
import {
  getP6DisplayBaseline,
  getP6PlatformLegend,
  getP6PlatformRoutes,
  getP6PortalProjection,
  listP6MockScenarios,
  type P6MockScenarioCatalog,
  type P6PlatformDisplayBaselinePackage,
  type P6PlatformLegend,
  type P6PlatformRoutes,
  type P6PortalProjectionReadEnvelope,
  type P6SourceMode,
} from "../lib/p6";

import "./P6PortalPage.css";

export function P6PortalPage() {
  const { activeArchive } = useArchiveContext();
  const [sourceMode] = useState<P6SourceMode>("mock");
  const [scenarioCatalog, setScenarioCatalog] = useState<P6MockScenarioCatalog | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState("baseline");
  const [projectionEnvelope, setProjectionEnvelope] = useState<P6PortalProjectionReadEnvelope | null>(null);
  const [baselinePackage, setBaselinePackage] = useState<P6PlatformDisplayBaselinePackage | null>(null);
  const [platformRoutes, setPlatformRoutes] = useState<P6PlatformRoutes | null>(null);
  const [platformLegend, setPlatformLegend] = useState<P6PlatformLegend | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [catalogReloadKey, setCatalogReloadKey] = useState(0);
  const [projectionReloadKey, setProjectionReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadSharedConfig() {
      setLoading(true);
      try {
        const [catalogResponse, baselineResponse, routesResponse, legendResponse] = await Promise.all([
          listP6MockScenarios(),
          getP6DisplayBaseline(),
          getP6PlatformRoutes(),
          getP6PlatformLegend(),
        ]);
        if (cancelled) {
          return;
        }

        const catalog = catalogResponse.data;
        startTransition(() => {
          setScenarioCatalog(catalog);
          setBaselinePackage(baselineResponse.data);
          setPlatformRoutes(routesResponse.data);
          setPlatformLegend(legendResponse.data);
          setSelectedScenarioId((current) =>
            catalog.items.some((item) => item.scenario_id === current) ? current : catalog.default_scenario_id,
          );
        });
        setError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载 P6 门户配置失败");
        setLoading(false);
      }
    }

    void loadSharedConfig();

    return () => {
      cancelled = true;
    };
  }, [catalogReloadKey]);

  useEffect(() => {
    if (!scenarioCatalog || !selectedScenarioId || !baselinePackage || !platformRoutes || !platformLegend) {
      return undefined;
    }

    let cancelled = false;

    async function loadProjection() {
      setLoading(true);
      try {
        const response = await getP6PortalProjection({
          source: sourceMode,
          scenario: selectedScenarioId,
        });
        if (cancelled) {
          return;
        }
        startTransition(() => {
          setProjectionEnvelope(response.data);
        });
        setError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载 P6 门户投影失败");
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
  }, [projectionReloadKey, scenarioCatalog, selectedScenarioId, sourceMode, baselinePackage, platformRoutes, platformLegend]);

  if (!projectionEnvelope || !baselinePackage || !platformRoutes || !platformLegend) {
    return (
      <div id="p6-portal-page" className="p6-portal-page p6-portal-page--status">
        <div className="p6-portal-status-card">
          <div className="p6-portal-status-card__title">{error ? "门户投影加载失败" : "正在加载门户投影"}</div>
          <div className="p6-portal-status-card__text">
            {error ?? "正在装载 P6 模拟场景、平台基线与门户投影，请稍候。"}
          </div>
          <button
            type="button"
            className="p6-portal-status-card__button"
            onClick={() => {
              if (scenarioCatalog && baselinePackage && platformRoutes && platformLegend) {
                setProjectionReloadKey((current) => current + 1);
                return;
              }
              setCatalogReloadKey((current) => current + 1);
            }}
          >
            重试加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <P6BlueprintCanvas
      archiveName={activeArchive?.name ?? "未选择知识库"}
      projection={projectionEnvelope.projection}
      sourceMode={sourceMode}
      scenarioCatalog={scenarioCatalog ?? { source_mode: "mock", default_scenario_id: "baseline", items: [] }}
      baseline={baselinePackage}
      routes={platformRoutes}
      legend={platformLegend}
      selectedScenarioId={selectedScenarioId}
      loading={loading}
      error={error}
      onScenarioChange={(scenarioId) => {
        setSelectedScenarioId(scenarioId);
      }}
      onRetry={() => {
        setProjectionReloadKey((current) => current + 1);
      }}
    />
  );
}
