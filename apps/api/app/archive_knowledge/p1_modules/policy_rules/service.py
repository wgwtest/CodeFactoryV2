from __future__ import annotations

from typing import Any

from app.archive_knowledge.contracts import (
    ArtifactRef,
    PolicyPackage,
    PolicyPackageVersion,
    RuleActionMapping,
    RuleContract,
    RuleFieldContract,
    StageExecutionContract,
)
from app.archive_knowledge.contracts.common import P1LifecycleStatus
from app.archive_knowledge.policy_config import (
    ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID,
    DEFAULT_STAGE_ORDER,
    normalize_archive_policy_config,
)


def build_architecture_midterm_policy_package(
    archive_id: str,
    raw_config: dict[str, Any] | None = None,
) -> PolicyPackage:
    config = normalize_archive_policy_config(archive_id, raw_config)
    version = build_architecture_midterm_policy_package_version(archive_id, config)
    return PolicyPackage(
        policy_package_id=str(config.get("policy_package_id") or ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID),
        policy_package_name=str(config.get("policy_package_name") or "Mid Term 体系结构默认策略包"),
        business_domain="architecture_midterm",
        knowledge_types=[
            "Operational Node",
            "System",
            "Capability",
            "Activity",
            "Information Exchange",
            "Architecture Relationship",
        ],
        owner="p1.policy_rules",
        lifecycle_status=_lifecycle_status(config.get("policy_package_version_status")),
        current_version_id=str(config.get("policy_package_version_id") or version.policy_package_version_id),
        versions=[version],
    )


def build_architecture_midterm_policy_package_version(
    archive_id: str,
    raw_config: dict[str, Any] | None = None,
) -> PolicyPackageVersion:
    config = normalize_archive_policy_config(archive_id, raw_config)
    stage_contracts = [_stage_contract(config, stage_id, index) for index, stage_id in enumerate(config["stage_order"], start=1)]
    rule_contracts = [
        _rule_contract(stage_id, rule)
        for stage_id in config.get("stage_order", DEFAULT_STAGE_ORDER)
        for rule in _stage_rules(config, stage_id)
    ]
    return PolicyPackageVersion(
        policy_package_version_id=str(config.get("policy_package_version_id")),
        version_label=str(config.get("version_label") or "architecture_midterm_default"),
        status=_lifecycle_status(config.get("policy_package_version_status")),
        hash=str(config.get("policy_package_version_hash")),
        created_at=str(config.get("policy_package_version_created_at") or config.get("updated_at") or "pending-freeze"),
        previous_policy_package_version_id=config.get("previous_policy_package_version_id"),
        stage_contracts=stage_contracts,
        rule_contracts=rule_contracts,
        compatible_output_contracts=[
            "PolicyRuntimeSnapshot",
            "RuleExecutionRecord",
            "ImpactSet",
            "DocumentRuntimeContract",
        ],
    )


def build_rule_execution_record_field_contracts() -> list[RuleFieldContract]:
    return [
        RuleFieldContract(field_name="execution_id", source_artifact="rule_engine", field_type="string"),
        RuleFieldContract(field_name="archive_id", source_artifact="archive_context", field_type="string"),
        RuleFieldContract(field_name="document_id", source_artifact="document_runtime", field_type="string"),
        RuleFieldContract(field_name="stage_id", source_artifact="policy_stage", field_type="string"),
        RuleFieldContract(field_name="rule_id", source_artifact="rule_contract", field_type="string"),
        RuleFieldContract(field_name="rule_version", source_artifact="rule_contract", field_type="string"),
        RuleFieldContract(field_name="rule_hash", source_artifact="rule_contract", field_type="string"),
        RuleFieldContract(field_name="policy_snapshot_id", source_artifact="policy_snapshot", field_type="string"),
        RuleFieldContract(field_name="policy_package_id", source_artifact="policy_snapshot", field_type="string"),
        RuleFieldContract(field_name="policy_package_version_id", source_artifact="policy_snapshot", field_type="string"),
        RuleFieldContract(field_name="policy_version", source_artifact="policy_snapshot", field_type="string"),
        RuleFieldContract(field_name="input_artifact_refs", source_artifact="rule_input", field_type="string[]"),
        RuleFieldContract(field_name="input_hash", source_artifact="rule_input", field_type="string"),
        RuleFieldContract(field_name="output_artifact_refs", target_artifact="rule_output", field_type="string[]"),
        RuleFieldContract(field_name="output_hash", target_artifact="rule_output", field_type="string"),
        RuleFieldContract(field_name="affected_object_ids", target_artifact="impact_set", field_type="string[]"),
        RuleFieldContract(field_name="affected_relation_ids", target_artifact="impact_set", field_type="string[]", required=False),
        RuleFieldContract(field_name="decision", target_artifact="rule_execution_record", field_type="string"),
        RuleFieldContract(field_name="metrics", target_artifact="rule_execution_record", field_type="object"),
        RuleFieldContract(field_name="executed_at", target_artifact="rule_execution_record", field_type="date"),
        RuleFieldContract(field_name="source", target_artifact="rule_execution_record", field_type="enum"),
    ]


def _stage_contract(config: dict[str, Any], stage_id: str, order_hint: int) -> StageExecutionContract:
    stage = config["stages"][stage_id]
    rules = _stage_rules(config, stage_id)
    return StageExecutionContract(
        stage_id=stage_id,
        stage_name=str(stage.get("label") or stage_id),
        enabled=bool(stage.get("enabled", True)),
        order_hint=order_hint,
        input_artifacts=_artifact_refs(rules, schema_key="input_schema", ref_key="source_artifact", artifact_type="input"),
        output_artifacts=_artifact_refs(rules, schema_key="output_schema", ref_key="target_artifact", artifact_type="output"),
        rule_ids=[str(rule.get("rule_id") or rule.get("key")) for rule in rules],
        entry_contract_id=f"{stage_id}:entry",
        exit_contract_id=f"{stage_id}:exit",
        can_run_independently=False,
        downstream_stage_ids=_downstream_stage_ids(config, stage_id),
    )


def _rule_contract(stage_id: str, rule: dict[str, Any]) -> RuleContract:
    output_fields = [
        str(field.get("field_name"))
        for field in rule.get("output_schema", [])
        if isinstance(field, dict) and field.get("field_name")
    ]
    action_mapping = rule.get("action_mapping") if isinstance(rule.get("action_mapping"), dict) else {}
    return RuleContract(
        rule_id=str(rule.get("rule_id") or rule.get("key")),
        rule_name=str(rule.get("name") or rule.get("rule_id") or rule.get("key")),
        rule_version=str(rule.get("rule_version") or "r1.0"),
        rule_hash=str(rule.get("rule_hash") or ""),
        stage_id=stage_id,
        effect_kind=rule.get("effect_kind") or "custom",
        enabled=True,
        scope_selector=rule.get("scope_selector") if isinstance(rule.get("scope_selector"), dict) else {},
        input_schema=[RuleFieldContract.model_validate(field) for field in rule.get("input_schema", [])],
        output_schema=[RuleFieldContract.model_validate(field) for field in rule.get("output_schema", [])],
        parameters=rule.get("parameters") if isinstance(rule.get("parameters"), dict) else {},
        action_mapping=RuleActionMapping(
            when_hit=str(action_mapping.get("on_match") or action_mapping.get("when_hit") or rule.get("action") or ""),
            when_miss=str(action_mapping.get("on_miss") or action_mapping.get("when_miss") or "auto_pass"),
            output_fields=output_fields,
            downstream_stage_ids=[],
        ),
        trace_fields=list(rule.get("trace_fields") or []),
        contract_status=rule.get("contract_status") or "valid",
        contract_errors=list(rule.get("contract_errors") or []),
    )


def _stage_rules(config: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    stage = config.get("stages", {}).get(stage_id, {})
    return [rule for rule in stage.get("rules", []) if isinstance(rule, dict)]


def _artifact_refs(
    rules: list[dict[str, Any]],
    *,
    schema_key: str,
    ref_key: str,
    artifact_type: str,
) -> list[ArtifactRef]:
    refs: dict[str, ArtifactRef] = {}
    for rule in rules:
        for field in rule.get(schema_key, []):
            if not isinstance(field, dict):
                continue
            ref = str(field.get(ref_key) or "").strip()
            if not ref:
                continue
            refs.setdefault(
                ref,
                ArtifactRef(
                    artifact_id=ref,
                    artifact_type=artifact_type,
                    stage_id=str(
                        (rule.get("scope_selector") if isinstance(rule.get("scope_selector"), dict) else {}).get(
                            "source_stage_id",
                        )
                        or ""
                    ),
                    summary=str(field.get("business_meaning") or field.get("field_name") or ref),
                ),
            )
    return list(refs.values())


def _downstream_stage_ids(config: dict[str, Any], stage_id: str) -> list[str]:
    order = list(config.get("stage_order") or DEFAULT_STAGE_ORDER)
    if stage_id not in order:
        return []
    return order[order.index(stage_id) + 1 :]


def _lifecycle_status(value: Any) -> P1LifecycleStatus:
    status = str(value or "draft")
    if status in {"draft", "published", "deprecated", "candidate", "governance_pending", "formalized"}:
        return status  # type: ignore[return-value]
    return "draft"
