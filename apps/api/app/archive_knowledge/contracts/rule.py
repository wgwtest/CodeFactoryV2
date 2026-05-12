from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.archive_knowledge.contracts.common import ArtifactRef, P1RuleEffectKind


RuleFieldType = Literal[
    "string",
    "number",
    "boolean",
    "enum",
    "date",
    "array",
    "object",
    "string[]",
    "number[]",
    "boolean[]",
]
RuleMissingAction = Literal[
    "block",
    "warn",
    "skip",
    "default",
    "auto_pass",
    "warn_continue",
    "manual_review",
    "block_return",
    "defer_publish",
]
RuleContractStatus = Literal["valid", "invalid", "warning"]

REQUIRED_INPUT_FIELD_NAMES = ("input_hash",)
REQUIRED_OUTPUT_FIELD_NAMES = ("output_hash", "affected_object_ids")
REQUIRED_TRACE_FIELD_NAMES = (
    "rule_id",
    "rule_version",
    "rule_hash",
    "input_hash",
    "output_hash",
    "affected_object_ids",
)


class RuleFieldContract(BaseModel):
    field_name: str
    source_artifact: str | None = None
    target_artifact: str | None = None
    field_type: RuleFieldType
    required: bool = True
    include_in_hash: bool = True
    include_in_input_hash: bool | None = None
    include_in_output_hash: bool | None = None
    validation: str | None = None
    example: str | None = None
    business_meaning: str | None = None
    missing_action: RuleMissingAction | None = None
    producer: str | None = None
    write_to_runtime: bool | None = None
    write_to_audit: bool | None = None
    used_for_impact: bool | None = None


class RuleConditionContract(BaseModel):
    condition_id: str
    left_field: str
    operator: str
    right_value: str | int | float | bool
    description: str | None = None


class RuleActionMapping(BaseModel):
    when_hit: str
    when_miss: str
    output_fields: list[str] = Field(default_factory=list)
    downstream_stage_ids: list[str] = Field(default_factory=list)


class RuleContract(BaseModel):
    rule_id: str
    rule_name: str
    rule_version: str
    rule_hash: str
    stage_id: str
    effect_kind: P1RuleEffectKind
    enabled: bool = True
    scope_selector: dict[str, Any] = Field(default_factory=dict)
    input_schema: list[RuleFieldContract] = Field(default_factory=list)
    output_schema: list[RuleFieldContract] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    action_mapping: RuleActionMapping
    trace_fields: list[str] = Field(default_factory=list)
    contract_status: RuleContractStatus = "valid"
    contract_errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def refresh_contract_status(self) -> "RuleContract":
        errors: list[str] = []

        for field_name in ("rule_id", "rule_name", "rule_version", "rule_hash", "stage_id", "effect_kind"):
            if not str(getattr(self, field_name, "") or "").strip():
                errors.append(f"missing {field_name}")

        errors.extend(_field_contract_errors(self.input_schema, schema_name="input_schema", ref_field="source_artifact"))
        errors.extend(
            _field_contract_errors(
                self.output_schema,
                schema_name="output_schema",
                ref_field="source_artifact_or_target_artifact",
            )
        )

        input_field_names = {field.field_name for field in self.input_schema}
        output_field_names = {field.field_name for field in self.output_schema}
        trace_field_names = set(self.trace_fields)

        for field_name in REQUIRED_INPUT_FIELD_NAMES:
            if field_name not in input_field_names:
                errors.append(f"missing input_schema.{field_name}")
        for field_name in REQUIRED_OUTPUT_FIELD_NAMES:
            if field_name not in output_field_names:
                errors.append(f"missing output_schema.{field_name}")
        for field_name in REQUIRED_TRACE_FIELD_NAMES:
            if field_name not in trace_field_names:
                errors.append(f"missing trace_fields.{field_name}")

        conditions = self.parameters.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            errors.append("missing parameters.conditions")

        if not str(self.action_mapping.when_hit or "").strip():
            errors.append("missing action_mapping.when_hit")
        if not str(self.action_mapping.when_miss or "").strip():
            errors.append("missing action_mapping.when_miss")
        if not self.action_mapping.output_fields:
            errors.append("missing action_mapping.output_fields")

        self.contract_errors = errors
        self.contract_status = "invalid" if errors else ("warning" if self.contract_status == "warning" else "valid")
        return self


class RuleExecutionRecord(BaseModel):
    execution_id: str
    run_id: str
    archive_id: str
    document_id: str
    stage_id: str
    policy_package_version_id: str | None = None
    rule_id: str
    rule_version: str
    rule_hash: str
    input_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    output_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    affected_object_ids: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: str
    executed_at: str


def _field_contract_errors(
    fields: list[RuleFieldContract],
    *,
    schema_name: str,
    ref_field: Literal["source_artifact", "source_artifact_or_target_artifact"],
) -> list[str]:
    if not fields:
        return [f"missing {schema_name}"]

    errors: list[str] = []
    for index, field in enumerate(fields):
        if not field.field_name.strip():
            errors.append(f"missing {schema_name}[{index}].field_name")
        if ref_field == "source_artifact" and not str(field.source_artifact or "").strip():
            errors.append(f"missing {schema_name}[{index}].source_artifact")
        if (
            ref_field == "source_artifact_or_target_artifact"
            and not str(field.source_artifact or field.target_artifact or "").strip()
        ):
            errors.append(f"missing {schema_name}[{index}].source_artifact_or_target_artifact")
    return errors
