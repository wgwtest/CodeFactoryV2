import type { P1ArtifactRef, P1LifecycleStatus } from "./common";
import type { RuleContract } from "./rule";

export interface StageExecutionContract {
  stage_id: string;
  stage_name: string;
  enabled: boolean;
  order_hint: number;
  input_artifacts: P1ArtifactRef[];
  output_artifacts: P1ArtifactRef[];
  rule_ids: string[];
  entry_contract_id?: string;
  exit_contract_id?: string;
  can_run_independently: boolean;
  downstream_stage_ids: string[];
}

export interface PolicyPackageVersion {
  policy_package_version_id: string;
  version_label: string;
  status: P1LifecycleStatus;
  hash: string;
  created_at: string;
  previous_policy_package_version_id?: string;
  stage_contracts: StageExecutionContract[];
  rule_contracts: RuleContract[];
  compatible_output_contracts: string[];
}

export interface PolicyPackage {
  policy_package_id: string;
  policy_package_name: string;
  business_domain: string;
  knowledge_types: string[];
  owner: string;
  lifecycle_status: P1LifecycleStatus;
  current_version_id: string;
  versions: PolicyPackageVersion[];
}

export interface PolicyRuntimeSnapshot {
  snapshot_id: string;
  archive_id: string;
  run_id: string;
  policy_package_id: string;
  policy_package_version_id: string;
  policy_package_version_hash: string;
  frozen_at: string;
  stage_contract_refs: string[];
  rule_contract_refs: string[];
}
