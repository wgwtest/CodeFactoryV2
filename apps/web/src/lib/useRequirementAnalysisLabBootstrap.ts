import { useEffect, useState } from "react";

import type {
  RequirementAnalysisLabConfig,
  RequirementAnalysisOrchestratorEnvelope,
  RequirementAnalysisProvider,
} from "./api";
import {
  getRequirementAnalysisLabConfig,
  getRequirementAnalysisOrchestrators,
  getRequirementAnalysisProviders,
} from "./requirementAnalysis";

export type RequirementAnalysisLabBootstrap = {
  labConfig: RequirementAnalysisLabConfig | null;
  orchestratorsEnvelope: RequirementAnalysisOrchestratorEnvelope | null;
  providers: RequirementAnalysisProvider[];
  loading: boolean;
  error: string | null;
};

export function useRequirementAnalysisLabBootstrap(): RequirementAnalysisLabBootstrap {
  const [labConfig, setLabConfig] = useState<RequirementAnalysisLabConfig | null>(null);
  const [orchestratorsEnvelope, setOrchestratorsEnvelope] = useState<RequirementAnalysisOrchestratorEnvelope | null>(null);
  const [providers, setProviders] = useState<RequirementAnalysisProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const [configResponse, orchestratorsResponse, providersResponse] = await Promise.all([
          getRequirementAnalysisLabConfig(),
          getRequirementAnalysisOrchestrators(),
          getRequirementAnalysisProviders(),
        ]);
        if (cancelled) {
          return;
        }
        setLabConfig(configResponse.data);
        setOrchestratorsEnvelope(orchestratorsResponse.data);
        setProviders(providersResponse.data.items);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 XG 需求分析组织器 Lab 失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { labConfig, orchestratorsEnvelope, providers, loading, error };
}
