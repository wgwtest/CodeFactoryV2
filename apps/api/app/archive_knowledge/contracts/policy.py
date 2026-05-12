from __future__ import annotations

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef, P1LifecycleStatus
from app.archive_knowledge.contracts.rule import RuleContract


class StageExecutionContract(BaseModel):
    stage_id: str
    stage_name: str
    enabled: bool = True
    order_hint: int
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    entry_contract_id: str | None = None
    exit_contract_id: str | None = None
    can_run_independently: bool = False
    downstream_stage_ids: list[str] = Field(default_factory=list)


class PolicyPackageVersion(BaseModel):
    policy_package_version_id: str
    version_label: str
    status: P1LifecycleStatus
    hash: str
    created_at: str
    previous_policy_package_version_id: str | None = None
    stage_contracts: list[StageExecutionContract] = Field(default_factory=list)
    rule_contracts: list[RuleContract] = Field(default_factory=list)
    compatible_output_contracts: list[str] = Field(default_factory=list)


class PolicyPackage(BaseModel):
    policy_package_id: str
    policy_package_name: str
    business_domain: str
    knowledge_types: list[str] = Field(default_factory=list)
    owner: str
    lifecycle_status: P1LifecycleStatus
    current_version_id: str
    versions: list[PolicyPackageVersion] = Field(default_factory=list)


class PolicyRuntimeSnapshot(BaseModel):
    snapshot_id: str
    archive_id: str
    run_id: str
    policy_package_id: str
    policy_package_version_id: str
    policy_package_version_hash: str
    frozen_at: str
    stage_contract_refs: list[str] = Field(default_factory=list)
    rule_contract_refs: list[str] = Field(default_factory=list)
