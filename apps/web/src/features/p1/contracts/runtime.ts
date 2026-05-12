import type { P1RunStatus, P1StageStatus, P1TraceRef } from "./common";
import type { RuntimeGraphProjection } from "./graphProjection";
import type { PolicyRuntimeSnapshot } from "./policy";
import type { RuleExecutionRecord } from "./rule";

export interface StageSnapshot {
  stage_id: string;
  stage_name: string;
  status: P1StageStatus;
  started_at?: string;
  finished_at?: string;
  message?: string;
  input_object_count: number;
  output_object_count: number;
  rule_execution_record_ids: string[];
  graph_projection_id?: string;
}

export interface DocumentRuntimeSnapshot {
  archive_id: string;
  document_id: string;
  run_id: string;
  status: P1RunStatus;
  current_stage_id?: string;
  current_stage_message?: string;
  stream_status: "connected" | "fallback_polling" | "disconnected" | "not_started";
  policy_snapshot: PolicyRuntimeSnapshot;
  stage_snapshots: StageSnapshot[];
  graph_projection: RuntimeGraphProjection;
  rule_execution_records: RuleExecutionRecord[];
  event_trace: P1TraceRef[];
}
