import type {
  ArchiveIncrementalRebuildTask,
  ArchivePolicyConfig,
  ArchivePolicyImpactSet,
  ArchivePolicyPackageVersion,
  ArchiveRuleInputFieldContract,
  ArchiveRuleOutputFieldContract,
  ArchiveStagePolicyConfig,
  ArchiveStagePolicyRule,
} from "../../../../lib/api";

export type PolicyRuleWithContract = ArchiveStagePolicyRule & {
  action_mapping?: Record<string, unknown>;
  input_schema?: ArchiveRuleInputFieldContract[];
  output_schema?: ArchiveRuleOutputFieldContract[];
};

export type PolicyStageWithRuleContracts = Omit<ArchiveStagePolicyConfig, "rules"> & {
  rules: PolicyRuleWithContract[];
};

export type PolicyRulesConfig = Omit<
  ArchivePolicyConfig,
  "impact_set" | "incremental_rebuild_task" | "policy_package_versions" | "stages"
> & {
  policy_contract_version?: string | null;
  policy_package_versions?: ArchivePolicyPackageVersion[];
  impact_set?: ArchivePolicyImpactSet | null;
  incremental_rebuild_task?: ArchiveIncrementalRebuildTask | null;
  stages: Record<string, PolicyStageWithRuleContracts>;
};

export type PolicyRuleContractRow = {
  rowId: string;
  stageId: string;
  stageLabel: string;
  ruleId: string;
  ruleName: string;
  action: string;
  effectKind: string;
  inputFieldCount: number;
  outputFieldCount: number;
  traceFieldCount: number;
  contractStatus: string;
  contractErrors: string[];
};

export type RuleDraftValidation = {
  status: "valid" | "invalid";
  errors: string[];
  inputSchema: ArchiveRuleInputFieldContract[];
  outputSchema: ArchiveRuleOutputFieldContract[];
  traceFields: string[];
};

export type PolicyRulesModuleOutput = {
  policyPackageVersionId: string;
  policyContractStatus: string;
  impactSetSummary: string | null;
};
