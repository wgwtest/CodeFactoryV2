import { api } from "./api";

export type PlatformExchangeStageKey = "P1" | "P2" | "P3" | "P4" | "P5";

export type PlatformExchangeArtifact = {
  artifact_id: string;
  artifact_type: string;
  artifact_version: string;
  schema_version: string;
  producer_stage: string;
  producer_ref_id: string;
  producer_ref_type?: string | null;
  lifecycle_status: string;
  payload_mode: string;
  payload?: Record<string, unknown> | null;
  payload_ref?: string | null;
  payload_hash: string;
  parent_artifact_ids: string[];
  source_trace: Record<string, unknown>;
  idempotency_key: string;
  frozen_at?: string | null;
  published_at: string;
  published_by: string;
  created_at: string;
};

export type PlatformExchangeConsumption = {
  consumption_id: string;
  artifact_id: string;
  consumer_stage: string;
  consumer_ref_id: string;
  consumer_ref_type?: string | null;
  consumption_mode: string;
  accepted_schema_version: string;
  result_status: string;
  result_message?: string | null;
  consumed_at: string;
};

export type PlatformExchangeMonitorStage = {
  stage: PlatformExchangeStageKey;
  published: PlatformExchangeArtifact[];
  consumed: PlatformExchangeConsumption[];
  empty_state: string | null;
};

export type PlatformExchangeMonitorSnapshot = {
  stages: PlatformExchangeMonitorStage[];
  base_platform: {
    artifact_totals: {
      by_type: Record<string, number>;
      by_producer_stage: Record<string, number>;
      by_lifecycle_status: Record<string, number>;
    };
    consumption_totals: {
      by_consumer_stage: Record<string, number>;
      by_result_status: Record<string, number>;
    };
    latest_artifacts: PlatformExchangeArtifact[];
    latest_consumptions: PlatformExchangeConsumption[];
  };
};

export function getPlatformExchangeMonitor() {
  return api.get<PlatformExchangeMonitorSnapshot>("/platform-exchange/monitor");
}
