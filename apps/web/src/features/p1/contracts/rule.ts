import type { P1ArtifactRef, P1RuleEffectKind } from "./common";

export type P1RuleFieldType =
  | "string"
  | "number"
  | "boolean"
  | "enum"
  | "date"
  | "array"
  | "object"
  | "string[]"
  | "number[]"
  | "boolean[]";

export type RuleContractStatus = "valid" | "invalid" | "warning";
export type RuleMissingAction =
  | "block"
  | "warn"
  | "skip"
  | "default"
  | "auto_pass"
  | "warn_continue"
  | "manual_review"
  | "block_return"
  | "defer_publish";

export interface RuleFieldContract {
  field_name: string;
  source_artifact?: string;
  target_artifact?: string;
  field_type: P1RuleFieldType;
  required?: boolean;
  include_in_hash?: boolean;
  include_in_input_hash?: boolean;
  include_in_output_hash?: boolean;
  validation?: string;
  example?: string;
  business_meaning?: string;
  missing_action?: RuleMissingAction;
  producer?: string;
  write_to_runtime?: boolean;
  write_to_audit?: boolean;
  used_for_impact?: boolean;
}

export interface RuleConditionContract {
  condition_id: string;
  left_field?: string;
  left?: string;
  operator: string;
  right_value?: string | number | boolean;
  right?: string | number | boolean;
  description?: string;
}

export interface RuleActionMapping {
  when_hit?: string;
  when_miss?: string;
  on_match?: string;
  on_miss?: string;
  effect_kind?: P1RuleEffectKind;
  runtime_decision?: string;
  impact_strategy?: string;
  writes?: string[];
  audit_event_kind?: string;
  output_fields?: string[];
  downstream_stage_ids?: string[];
}

export interface RuleContract {
  rule_id: string;
  rule_name: string;
  rule_version: string;
  rule_hash: string;
  stage_id: string;
  effect_kind: P1RuleEffectKind;
  enabled: boolean;
  scope_selector: Record<string, unknown>;
  input_schema: RuleFieldContract[];
  output_schema: RuleFieldContract[];
  parameters: {
    conditions?: RuleConditionContract[];
    thresholds?: Record<string, number | string | boolean>;
    ai_adaptation?: "disabled" | "suggest_threshold" | "suggest_rule" | "full_assist";
    [key: string]: unknown;
  };
  action_mapping: RuleActionMapping;
  trace_fields: string[];
  contract_status: RuleContractStatus;
  contract_errors: string[];
}

export interface RuleExecutionRecord {
  execution_id: string;
  run_id: string;
  archive_id: string;
  document_id: string;
  stage_id: string;
  policy_package_version_id?: string;
  rule_id: string;
  rule_version: string;
  rule_hash: string;
  input_artifact_refs: P1ArtifactRef[];
  output_artifact_refs: P1ArtifactRef[];
  input_hash: string;
  output_hash: string;
  affected_object_ids: string[];
  affected_relation_ids: string[];
  metrics: Record<string, number | string | boolean>;
  decision: string;
  executed_at: string;
}
