from __future__ import annotations

from copy import deepcopy
from hashlib import md5, sha256
import json
import re
from typing import Any

POLICY_ACTIONS = [
    "auto_pass",
    "warn_continue",
    "manual_review",
    "block_return",
    "defer_publish",
]

POLICY_EFFECT_KINDS = [
    "filter",
    "score",
    "normalize",
    "merge",
    "split",
    "block",
    "publish_candidate",
]

POLICY_CONTRACT_VERSION = "p1.policy_contract.v1"

EFFECT_KIND_SEMANTICS: dict[str, dict[str, Any]] = {
    "filter": {
        "runtime_decision": "filter_candidates",
        "impact_strategy": "track matched and rejected candidate objects",
        "writes": ["decision", "affected_object_ids", "output_hash"],
    },
    "score": {
        "runtime_decision": "score_candidates",
        "impact_strategy": "track scored objects for threshold recompute",
        "writes": ["decision", "decision_reason", "affected_object_ids", "output_hash"],
    },
    "normalize": {
        "runtime_decision": "normalize_fields",
        "impact_strategy": "track normalized objects and downstream consumers",
        "writes": ["decision", "decision_reason", "affected_object_ids", "output_hash"],
    },
    "merge": {
        "runtime_decision": "merge_objects",
        "impact_strategy": "track merged object and discarded candidates",
        "writes": ["merged_object_id", "discarded_candidate_ids", "affected_object_ids", "output_hash"],
    },
    "split": {
        "runtime_decision": "split_objects",
        "impact_strategy": "track parent object and generated child objects",
        "writes": ["decision", "affected_object_ids", "output_hash"],
    },
    "block": {
        "runtime_decision": "block_return",
        "impact_strategy": "track blocked objects and blocking reason",
        "writes": ["blocked_reason", "affected_object_ids", "output_hash"],
    },
    "publish_candidate": {
        "runtime_decision": "prepare_publication_candidate",
        "impact_strategy": "track machine publication candidates before governance confirmation",
        "writes": ["publication_candidate_ids", "affected_object_ids", "output_hash"],
    },
}

REQUIRED_TRACE_FIELDS = [
    "rule_id",
    "rule_version",
    "rule_hash",
    "stage_id",
    "snapshot_id",
    "input_hash",
    "output_hash",
    "affected_object_ids",
]

DEFAULT_STAGE_ORDER = [
    "asset_intake",
    "parser_router",
    "parser_execution",
    "unified_document_object",
    "evidence_constructor",
    "evidence_graph_chunk_layer",
    "evidence_pack",
    "concept_candidate_review",
    "relation_review_family_normalization",
    "definition_summary_conflict_consolidation",
    "canonical_knowledge",
    "quality_policy_evaluation_governance_gate",
    "indexes_snapshots_apis",
]

QUALITY_GATE_STAGE_ID = "quality_policy_evaluation_governance_gate"

RULE_STRUCTURAL_FIELDS = [
    "threshold",
    "action",
    "effect_kind",
    "scope_selector",
    "input_schema",
    "output_schema",
    "parameters",
    "trace_fields",
    "action_mapping",
]

STAGE_STRUCTURAL_FIELDS = [
    "enabled",
    "default_action",
    "inputs",
    "outputs",
    "observability",
    "rules",
]

RULE_VERSION_RE = re.compile(r"^r(?P<major>\d+)\.(?P<minor>\d+)$")
PACKAGE_VERSION_RE = re.compile(r"^(?P<prefix>.*:policy:v)(?P<number>\d+)$")


def _short_hash(payload: Any) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _field_contract(
    *,
    field_name: str,
    source_artifact: str,
    field_type: str,
    required: bool = True,
    include_in_input_hash: bool = True,
    validation: str = "",
    example: str = "",
    business_meaning: str = "",
    missing_action: str = "block_return",
) -> dict[str, Any]:
    return {
        "field_name": field_name,
        "source_artifact": source_artifact,
        "field_type": field_type,
        "required": required,
        "include_in_input_hash": include_in_input_hash,
        "validation": validation,
        "example": example,
        "business_meaning": business_meaning or field_name,
        "missing_action": missing_action,
    }


def _output_contract(
    *,
    field_name: str,
    target_artifact: str,
    field_type: str,
    producer: str = "rule_engine",
    include_in_output_hash: bool = True,
    write_to_runtime: bool = True,
    write_to_audit: bool = True,
    used_for_impact: bool = False,
    example: str = "",
    business_meaning: str = "",
) -> dict[str, Any]:
    return {
        "field_name": field_name,
        "target_artifact": target_artifact,
        "field_type": field_type,
        "producer": producer,
        "include_in_output_hash": include_in_output_hash,
        "write_to_runtime": write_to_runtime,
        "write_to_audit": write_to_audit,
        "used_for_impact": used_for_impact,
        "example": example,
        "business_meaning": business_meaning or field_name,
    }


def _infer_effect_kind(stage_id: str, rule_key: str, action: str) -> str:
    text = f"{stage_id} {rule_key}".lower()
    if action == "block_return":
        return "block"
    if action == "defer_publish" or "publish" in text or "index" in text:
        return "publish_candidate"
    if "merge" in text or "canonical" in text or "candidate" in text:
        return "merge"
    if "split" in text or "chunk" in text or "segment" in text:
        return "split"
    if "score" in text or "confidence" in text or action == "warn_continue":
        return "score"
    if "normalize" in text or "parser" in text or "document" in text:
        return "normalize"
    return "filter"


def _default_scope_selector(stage_id: str, rule_key: str) -> dict[str, Any]:
    return {
        "object_types": ["candidate_knowledge"],
        "source_stage_id": stage_id,
        "rule_key": rule_key,
        "min_confidence": 0.0,
        "requires_source_anchor": True,
    }


def _default_input_schema(stage_id: str, rule_key: str, threshold: str) -> list[dict[str, Any]]:
    source_artifact = f"{stage_id}.input"
    return [
        _field_contract(
            field_name="candidate_id",
            source_artifact=source_artifact,
            field_type="string",
            validation="non_empty",
            example="CND-001",
            business_meaning="candidate object identifier",
        ),
        _field_contract(
            field_name="source_anchor_ids",
            source_artifact="evidence_anchor",
            field_type="string[]",
            validation="len >= 1",
            example="[A-102, A-115]",
            business_meaning="source anchors used by the rule",
            missing_action="warn_continue",
        ),
        _field_contract(
            field_name="policy_snapshot_id",
            source_artifact="policy_snapshot",
            field_type="string",
            validation="non_empty",
            example="RS-20260506-0948",
            business_meaning="frozen policy snapshot for this run",
        ),
        _field_contract(
            field_name="rule_threshold",
            source_artifact="policy_rule",
            field_type="string",
            validation="non_empty",
            example=threshold,
            business_meaning=f"threshold expression for {rule_key}",
        ),
        _field_contract(
            field_name="input_hash",
            source_artifact="runtime_snapshot",
            field_type="string",
            validation="sha256",
            example="inp_b34e7d...",
            business_meaning="stable digest used for impact and incremental recompute",
        ),
    ]


def _default_output_schema(effect_kind: str) -> list[dict[str, Any]]:
    output_fields = [
        _output_contract(
            field_name="decision",
            target_artifact="rule_execution_record",
            field_type="enum",
            example=effect_kind,
            business_meaning="rule decision or effect kind",
        ),
        _output_contract(
            field_name="decision_reason",
            target_artifact="audit_log",
            field_type="string",
            example="threshold matched",
            business_meaning="human-readable rule decision reason",
        ),
        _output_contract(
            field_name="affected_object_ids",
            target_artifact="impact_set",
            field_type="string[]",
            used_for_impact=True,
            example="[OBJ-M-204]",
            business_meaning="objects that must be tracked for recompute",
        ),
        _output_contract(
            field_name="output_hash",
            target_artifact="runtime_snapshot",
            field_type="string",
            example="out_a91e...",
            business_meaning="stable digest of the rule output",
        ),
    ]
    if effect_kind == "merge":
        output_fields.insert(
            0,
            _output_contract(
                field_name="merged_object_id",
                target_artifact="candidate_knowledge",
                field_type="string",
                used_for_impact=True,
                example="OBJ-M-204",
                business_meaning="merged object produced by this rule",
            ),
        )
        output_fields.insert(
            1,
            _output_contract(
                field_name="discarded_candidate_ids",
                target_artifact="runtime_relation",
                field_type="string[]",
                used_for_impact=True,
                example="[CND-1002, CND-1008]",
                business_meaning="candidates folded into the merged object",
            ),
        )
    if effect_kind == "block":
        output_fields.insert(
            0,
            _output_contract(
                field_name="blocked_reason",
                target_artifact="gate_decision",
                field_type="string",
                used_for_impact=True,
                example="supporting_documents < 2",
                business_meaning="blocking reason returned to the upstream stage",
            ),
        )
    if effect_kind == "publish_candidate":
        output_fields.insert(
            0,
            _output_contract(
                field_name="publication_candidate_ids",
                target_artifact="publication_snapshot",
                field_type="string[]",
                used_for_impact=True,
                example="[PCS-001]",
                business_meaning="candidate objects exposed to publication snapshot",
            ),
        )
    return output_fields


def _default_parameters(rule_key: str, threshold: str) -> dict[str, Any]:
    return {
        "match_mode": "all",
        "conditions": [
            {
                "condition_id": f"{rule_key}:threshold",
                "left": "actual",
                "operator": "matches",
                "right": threshold,
            }
        ],
        "ai_threshold_recommendation": "allowed",
    }


def _default_action_mapping(effect_kind: str, action: str, output_schema: list[dict[str, Any]]) -> dict[str, Any]:
    semantics = EFFECT_KIND_SEMANTICS.get(effect_kind, EFFECT_KIND_SEMANTICS["filter"])
    output_fields = [
        str(field.get("field_name"))
        for field in output_schema
        if isinstance(field, dict) and field.get("field_name")
    ]
    return {
        "effect_kind": effect_kind,
        "on_match": action,
        "on_miss": "auto_pass",
        "runtime_decision": semantics["runtime_decision"],
        "impact_strategy": semantics["impact_strategy"],
        "writes": [field for field in semantics["writes"] if field in output_fields],
        "audit_event_kind": "rule_execution_record",
    }


def _normalize_trace_fields(raw_rule: dict[str, Any]) -> list[str]:
    if "trace_fields" not in raw_rule:
        return REQUIRED_TRACE_FIELDS[:]
    return _normalize_text_list(raw_rule.get("trace_fields"), [])


def _schema_field_errors(schema: Any, *, schema_name: str, required_keys: tuple[str, ...]) -> list[str]:
    if not isinstance(schema, list) or not schema:
        return [f"missing {schema_name}"]

    errors: list[str] = []
    for index, field in enumerate(schema):
        if not isinstance(field, dict):
            errors.append(f"invalid {schema_name}[{index}]")
            continue
        for key in required_keys:
            if not str(field.get(key) or "").strip():
                errors.append(f"missing {schema_name}[{index}].{key}")
    return errors


def _contract_errors(rule: dict[str, Any]) -> list[str]:
    input_fields = {str(field.get("field_name")) for field in rule.get("input_schema", []) if isinstance(field, dict)}
    output_fields = {str(field.get("field_name")) for field in rule.get("output_schema", []) if isinstance(field, dict)}
    trace_fields = {str(field) for field in rule.get("trace_fields", [])}
    parameters = rule.get("parameters")
    action_mapping = rule.get("action_mapping")
    errors: list[str] = []

    errors.extend(
        _schema_field_errors(
            rule.get("input_schema"),
            schema_name="input_schema",
            required_keys=("field_name", "source_artifact", "field_type"),
        )
    )
    errors.extend(
        _schema_field_errors(
            rule.get("output_schema"),
            schema_name="output_schema",
            required_keys=("field_name", "target_artifact", "field_type"),
        )
    )
    for field_name in ("input_hash",):
        if field_name not in input_fields:
            errors.append(f"missing input_schema.{field_name}")
    for field_name in ("output_hash", "affected_object_ids"):
        if field_name not in output_fields:
            errors.append(f"missing output_schema.{field_name}")
    if not isinstance(parameters, dict) or not isinstance(parameters.get("conditions"), list) or not parameters.get("conditions"):
        errors.append("missing parameters.conditions")
    if not isinstance(action_mapping, dict):
        errors.append("missing action_mapping")
    else:
        for field_name in ("effect_kind", "on_match", "runtime_decision", "impact_strategy"):
            if not str(action_mapping.get(field_name) or "").strip():
                errors.append(f"missing action_mapping.{field_name}")
    for field_name in REQUIRED_TRACE_FIELDS:
        if field_name not in trace_fields:
            errors.append(f"missing trace_fields.{field_name}")
    return errors


def _rule_hash_payload(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule.get("rule_id"),
        "rule_version": rule.get("rule_version"),
        "effect_kind": rule.get("effect_kind"),
        "scope_selector": rule.get("scope_selector"),
        "input_schema": rule.get("input_schema"),
        "output_schema": rule.get("output_schema"),
        "parameters": rule.get("parameters"),
        "trace_fields": rule.get("trace_fields"),
        "action_mapping": rule.get("action_mapping"),
        "action": rule.get("action"),
        "threshold": rule.get("threshold"),
    }


def _refresh_rule_contract_metadata(rule: dict[str, Any]) -> dict[str, Any]:
    rule["rule_hash"] = _short_hash(_rule_hash_payload(rule))
    rule["contract_errors"] = _contract_errors(rule)
    rule["contract_status"] = "valid" if not rule["contract_errors"] else "invalid"
    return rule


def _enrich_rule_contract(
    stage_id: str,
    raw_rule: dict[str, Any],
    *,
    fallback_action: str,
    index: int,
) -> dict[str, Any]:
    key = str(raw_rule.get("key") or raw_rule.get("rule_id") or f"rule-{index + 1}")
    action = _normalize_stage_action(stage_id, raw_rule.get("action"), fallback=fallback_action)
    effect_kind = str(raw_rule.get("effect_kind") or "")
    if effect_kind not in POLICY_EFFECT_KINDS:
        effect_kind = _infer_effect_kind(stage_id, key, action)

    output_schema = raw_rule.get("output_schema") if isinstance(raw_rule.get("output_schema"), list) else _default_output_schema(effect_kind)
    if "action_mapping" in raw_rule:
        action_mapping = raw_rule.get("action_mapping") if isinstance(raw_rule.get("action_mapping"), dict) else {}
    else:
        action_mapping = _default_action_mapping(effect_kind, action, output_schema)

    enriched: dict[str, Any] = {
        "key": key,
        "rule_id": str(raw_rule.get("rule_id") or key),
        "name": str(raw_rule.get("name") or "未命名规则"),
        "meaning": str(raw_rule.get("meaning") or ""),
        "threshold": str(raw_rule.get("threshold") or ""),
        "action": action,
        "rule_version": str(raw_rule.get("rule_version") or "r1.0"),
        "effect_kind": effect_kind,
        "scope_selector": raw_rule.get("scope_selector") if isinstance(raw_rule.get("scope_selector"), dict) else _default_scope_selector(stage_id, key),
        "input_schema": raw_rule.get("input_schema") if isinstance(raw_rule.get("input_schema"), list) else _default_input_schema(stage_id, key, str(raw_rule.get("threshold") or "")),
        "output_schema": output_schema,
        "parameters": raw_rule.get("parameters") if isinstance(raw_rule.get("parameters"), dict) else _default_parameters(key, str(raw_rule.get("threshold") or "")),
        "trace_fields": _normalize_trace_fields(raw_rule),
        "action_mapping": action_mapping,
    }
    # The server owns the digest so clients cannot accidentally keep a stale hash
    # after editing the rule contract.
    return _refresh_rule_contract_metadata(enriched)


def _enrich_stage_rules(stage_id: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched_rules: list[dict[str, Any]] = []
    for index, rule in enumerate(rules):
        fallback_action = str(rule.get("action") or "auto_pass") if isinstance(rule, dict) else "auto_pass"
        enriched_rules.append(
            _enrich_rule_contract(
                stage_id,
                rule if isinstance(rule, dict) else {},
                fallback_action=fallback_action,
                index=index,
            )
        )
    return enriched_rules


def _policy_package_hash(config: dict[str, Any]) -> str:
    return _short_hash(
        {
            "version_label": config.get("version_label"),
            "scope_label": config.get("scope_label"),
            "ai_autoadapt_enabled": config.get("ai_autoadapt_enabled"),
            "stage_order": config.get("stage_order"),
            "stages": config.get("stages"),
        }
    )


def _policy_contract_errors(config: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    stages = config.get("stages", {})
    if not isinstance(stages, dict):
        return [{"stage_id": None, "rule_id": None, "errors": ["missing stages"]}]

    for stage_id in config.get("stage_order", DEFAULT_STAGE_ORDER):
        stage = stages.get(stage_id)
        if not isinstance(stage, dict):
            errors.append({"stage_id": stage_id, "rule_id": None, "errors": ["missing stage"]})
            continue
        for rule in stage.get("rules", []):
            if not isinstance(rule, dict):
                errors.append({"stage_id": stage_id, "rule_id": None, "errors": ["invalid rule"]})
                continue
            rule_errors = rule.get("contract_errors")
            if rule_errors:
                errors.append(
                    {
                        "stage_id": stage_id,
                        "rule_id": rule.get("rule_id") or rule.get("key"),
                        "errors": list(rule_errors),
                    }
                )
    return errors


def _current_policy_version_entry(config: dict[str, Any], *, archived_at: str | None = None) -> dict[str, Any]:
    return {
        "version_id": config.get("policy_package_version_id"),
        "version_label": config.get("version_label"),
        "version_hash": config.get("policy_package_version_hash"),
        "status": "archived" if archived_at else config.get("policy_package_version_status"),
        "created_at": config.get("policy_package_version_created_at") or config.get("updated_at"),
        "archived_at": archived_at,
        "previous_version_id": config.get("previous_policy_package_version_id"),
        "structural_hash": _policy_structure_hash(config),
    }


def _normalize_policy_package_versions(raw_versions: Any, current_entry: dict[str, Any]) -> list[dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    if isinstance(raw_versions, list):
        for raw_entry in raw_versions:
            if not isinstance(raw_entry, dict):
                continue
            version_id = str(raw_entry.get("version_id") or raw_entry.get("policy_package_version_id") or "")
            if not version_id:
                continue
            entries[version_id] = {
                "version_id": version_id,
                "version_label": raw_entry.get("version_label"),
                "version_hash": raw_entry.get("version_hash") or raw_entry.get("policy_package_version_hash"),
                "status": raw_entry.get("status") or raw_entry.get("policy_package_version_status") or "archived",
                "created_at": raw_entry.get("created_at"),
                "archived_at": raw_entry.get("archived_at"),
                "previous_version_id": raw_entry.get("previous_version_id"),
                "structural_hash": raw_entry.get("structural_hash"),
            }

    current_version_id = str(current_entry.get("version_id") or "")
    if current_version_id:
        entries[current_version_id] = current_entry
    return list(entries.values())


def _finalize_policy_config(config: dict[str, Any], *, raw_versions: Any = None) -> dict[str, Any]:
    _refresh_policy_rule_contracts(config)
    config["policy_package_version_hash"] = _policy_package_hash(config)
    config["policy_contract_errors"] = _policy_contract_errors(config)
    config["policy_contract_status"] = "valid" if not config["policy_contract_errors"] else "invalid"
    config["policy_package_versions"] = _normalize_policy_package_versions(
        raw_versions if raw_versions is not None else config.get("policy_package_versions"),
        _current_policy_version_entry(config),
    )
    return config


def _refresh_policy_rule_contracts(config: dict[str, Any]) -> None:
    stages = config.get("stages", {})
    if not isinstance(stages, dict):
        return
    for stage in stages.values():
        if not isinstance(stage, dict):
            continue
        for rule in stage.get("rules", []):
            if isinstance(rule, dict):
                _refresh_rule_contract_metadata(rule)


def _rule_identity(rule: dict[str, Any]) -> str:
    return str(rule.get("rule_id") or rule.get("key") or "")


def _rule_structural_payload(rule: dict[str, Any]) -> dict[str, Any]:
    return {field: rule.get(field) for field in RULE_STRUCTURAL_FIELDS}


def _policy_structure_payload(config: dict[str, Any]) -> dict[str, Any]:
    stages = config.get("stages", {})
    stage_payload: dict[str, Any] = {}
    if isinstance(stages, dict):
        for stage_id in config.get("stage_order", DEFAULT_STAGE_ORDER):
            stage = stages.get(stage_id)
            if not isinstance(stage, dict):
                continue
            stage_payload[stage_id] = {
                field: stage.get(field)
                for field in STAGE_STRUCTURAL_FIELDS
                if field != "rules"
            }
            stage_payload[stage_id]["rules"] = [
                {
                    "key": rule.get("key"),
                    "rule_id": rule.get("rule_id"),
                    "structure": _rule_structural_payload(rule),
                }
                for rule in stage.get("rules", [])
                if isinstance(rule, dict)
            ]

    return {
        "policy_package_id": config.get("policy_package_id"),
        "stage_order": config.get("stage_order"),
        "stages": stage_payload,
    }


def _policy_structure_hash(config: dict[str, Any]) -> str:
    return _short_hash(_policy_structure_payload(config))


def _next_policy_package_version_id(archive_id: str, previous_config: dict[str, Any], proposed_config: dict[str, Any]) -> str:
    version_ids = [
        str(previous_config.get("policy_package_version_id") or ""),
        str(proposed_config.get("policy_package_version_id") or ""),
    ]
    version_ids.extend(
        str(entry.get("version_id") or "")
        for entry in previous_config.get("policy_package_versions", [])
        if isinstance(entry, dict)
    )
    matches = [
        match
        for version_id in version_ids
        if (match := PACKAGE_VERSION_RE.match(version_id))
    ]
    numbers = [int(match.group("number")) for match in matches]
    prefix = matches[0].group("prefix") if matches else f"{archive_id}:{ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID}:policy:v"
    return f"{prefix}{(max(numbers) if numbers else 1) + 1}"


def _next_version_label(label: str, version_id: str) -> str:
    version_suffix = version_id.rsplit(":", 1)[-1]
    if not version_suffix:
        return label
    if re.search(r"\bv\d+$", label):
        return re.sub(r"\bv\d+$", version_suffix, label)
    return f"{label} {version_suffix}"


def _increment_rule_version(rule_version: str) -> str:
    match = RULE_VERSION_RE.match(rule_version)
    if not match:
        return f"{rule_version}.1" if rule_version else "r1.1"
    return f"r{match.group('major')}.{int(match.group('minor')) + 1}"


def _bump_changed_rule_versions(previous_config: dict[str, Any], proposed_config: dict[str, Any]) -> None:
    previous_rules: dict[tuple[str, str], dict[str, Any]] = {}
    for stage_id, stage in previous_config.get("stages", {}).items():
        if not isinstance(stage, dict):
            continue
        for rule in stage.get("rules", []):
            if isinstance(rule, dict):
                previous_rules[(str(stage_id), _rule_identity(rule))] = rule

    for stage_id, stage in proposed_config.get("stages", {}).items():
        if not isinstance(stage, dict):
            continue
        for rule in stage.get("rules", []):
            if not isinstance(rule, dict):
                continue
            previous_rule = previous_rules.get((str(stage_id), _rule_identity(rule)))
            if not previous_rule:
                continue
            if _rule_structural_payload(previous_rule) == _rule_structural_payload(rule):
                continue
            previous_version = str(previous_rule.get("rule_version") or "r1.0")
            if str(rule.get("rule_version") or "") == previous_version:
                rule["rule_version"] = _increment_rule_version(previous_version)
            _refresh_rule_contract_metadata(rule)


def apply_policy_package_versioning(
    archive_id: str,
    previous_config: dict[str, Any] | None,
    proposed_config: dict[str, Any],
    *,
    updated_at: str,
) -> dict[str, Any]:
    proposed = normalize_archive_policy_config(archive_id, proposed_config)
    if previous_config is None:
        proposed["updated_at"] = updated_at
        proposed["policy_package_version_created_at"] = proposed.get("policy_package_version_created_at") or updated_at
        return _finalize_policy_config(proposed, raw_versions=proposed.get("policy_package_versions"))

    previous = normalize_archive_policy_config(archive_id, previous_config)
    structural_changed = _policy_structure_hash(previous) != _policy_structure_hash(proposed)
    if structural_changed:
        previous_version_id = str(previous.get("policy_package_version_id") or "")
        proposed_version_id = str(proposed.get("policy_package_version_id") or "")
        proposed["previous_policy_package_version_id"] = previous_version_id or None
        if proposed_version_id == previous_version_id:
            proposed["policy_package_version_id"] = _next_policy_package_version_id(archive_id, previous, proposed)
            proposed["version_label"] = _next_version_label(str(proposed.get("version_label") or ""), proposed["policy_package_version_id"])
        _bump_changed_rule_versions(previous, proposed)
        proposed["policy_package_version_created_at"] = updated_at
    else:
        proposed["previous_policy_package_version_id"] = (
            proposed.get("previous_policy_package_version_id")
            or previous.get("previous_policy_package_version_id")
        )
        proposed["policy_package_version_created_at"] = (
            proposed.get("policy_package_version_created_at")
            or previous.get("policy_package_version_created_at")
            or updated_at
        )

    proposed["updated_at"] = updated_at
    raw_versions = list(previous.get("policy_package_versions", []))
    if structural_changed:
        raw_versions.append(_current_policy_version_entry(previous, archived_at=updated_at))
    return _finalize_policy_config(proposed, raw_versions=raw_versions)


def _rule(key: str, name: str, meaning: str, threshold: str, action: str) -> dict[str, str]:
    return {
        "key": key,
        "name": name,
        "meaning": meaning,
        "threshold": threshold,
        "action": action,
    }


def _stage(
    *,
    stage_id: str,
    label: str,
    group: str,
    objective: str,
    ai_mode: str,
    default_action: str,
    inputs: list[str],
    ai_adaptation: str,
    rules: list[dict[str, str]],
    branches: list[str],
    outputs: list[str],
    observability: list[str],
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "label": label,
        "group": group,
        "enabled": True,
        "ai_mode": ai_mode,
        "default_action": default_action,
        "objective": objective,
        "inputs": inputs,
        "ai_adaptation": ai_adaptation,
        "rules": rules,
        "branches": branches,
        "outputs": outputs,
        "observability": observability,
    }


STAGE_POLICY_DEFAULTS: dict[str, dict[str, Any]] = {
    "asset_intake": _stage(
        stage_id="asset_intake",
        label="素材接入",
        group="摄取与统一",
        objective="判断当前文档能否进入正式抽取链路，并补齐基础来源标记、语种提示和扫描风险。",
        ai_mode="轻量识别 + 规则兜底",
        default_action="block_return",
        inputs=["原始文件流", "来源标记", "接入白名单"],
        ai_adaptation="AI 自动识别语种、版式和扫描特征，决定是否需要 OCR 预处理。",
        rules=[
            _rule("asset-1", "接入格式完整性", "文件必须可读取并命中允许的类型", "mime_type in allowlist && size > 0", "block_return"),
            _rule("asset-2", "来源标签补齐", "来源标签缺失时保留告警并继续", "source_label missing", "warn_continue"),
            _rule("asset-3", "扫描件分流", "扫描评分较高时自动切到 OCR 预处理", "scan_score >= 0.6", "auto_pass"),
        ],
        branches=["扫描件 -> OCR 预处理", "结构完整 -> 进入解析路由", "格式损坏 -> 阻断并退回素材池"],
        outputs=["接入质量标签", "文档类型初判", "语种提示", "预处理决策"],
        observability=["mime_type", "language_hint", "scan_score", "source_label", "intake_risk"],
    ),
    "parser_router": _stage(
        stage_id="parser_router",
        label="解析路由",
        group="摄取与统一",
        objective="为当前文档选择最合适的解析器组合和增强链路。",
        ai_mode="解析器路由建议",
        default_action="auto_pass",
        inputs=["接入质量标签", "文档类型初判", "解析器能力矩阵"],
        ai_adaptation="AI 根据版式、语言和图文比例给多条解析链路排序。",
        rules=[
            _rule("router-1", "主解析器命中率", "优先采用历史稳定性最高的解析器", "top_parser_confidence >= 0.75", "auto_pass"),
            _rule("router-2", "多语种切换", "检测到双语内容时挂载多语解析模型", "language_mix >= 2", "warn_continue"),
            _rule("router-3", "未知版式", "模板匹配过低时转人工复核候选池", "template_match < 0.45", "manual_review"),
        ],
        branches=["已知模板 -> 高速解析链", "多语文档 -> 多语解析链", "未知模板 -> 保守解析链 + 人工复核"],
        outputs=["解析器选择结果", "模板匹配结果", "增强能力挂载列表"],
        observability=["parser_choice", "template_match", "language_mix", "router_confidence"],
    ),
    "parser_execution": _stage(
        stage_id="parser_execution",
        label="解析执行",
        group="摄取与统一",
        objective="稳定产出结构化解析结果，并对缺页、乱码和表格裂解做自动补偿。",
        ai_mode="结构修复辅助",
        default_action="warn_continue",
        inputs=["解析器选择结果", "原始文件流", "预处理配置"],
        ai_adaptation="AI 对段落续接、表格裂解和标题层级混乱进行修复。",
        rules=[
            _rule("exec-1", "正文覆盖率", "正文覆盖率过低时直接阻断", "body_coverage >= 0.7", "block_return"),
            _rule("exec-2", "表格裂解修复", "表格裂解时尝试结构修复再继续", "table_split_score >= 0.5", "auto_pass"),
            _rule("exec-3", "乱码恢复", "乱码比例偏高时保留告警并继续", "garbled_ratio <= 0.08", "warn_continue"),
        ],
        branches=["解析稳定 -> 统一文档对象", "结构异常 -> 自动修复后继续", "正文缺失 -> 阻断回退"],
        outputs=["结构化正文", "表格与附件提取物", "修复日志", "段落层级结果"],
        observability=["body_coverage", "table_split_score", "garbled_ratio", "repair_count"],
    ),
    "unified_document_object": _stage(
        stage_id="unified_document_object",
        label="统一文档",
        group="摄取与统一",
        objective="把多来源解析结果压成统一文档对象，供后续证据层稳定消费。",
        ai_mode="对象整编与字段对齐",
        default_action="auto_pass",
        inputs=["结构化正文", "表格与附件提取物", "统一对象 schema"],
        ai_adaptation="AI 将标题、段落、表格、注释和附件引用统一到标准字段。",
        rules=[
            _rule("udo-1", "统一对象完整度", "缺少核心字段时不进入证据层", "required_fields >= 0.95", "block_return"),
            _rule("udo-2", "层级冲突修正", "层级冲突时按标准目录结构重排", "heading_conflict > 0", "auto_pass"),
            _rule("udo-3", "附件引用绑定", "附件无法绑定正文时发出告警", "attachment_bind_rate >= 0.85", "warn_continue"),
        ],
        branches=["对象完整 -> 证据构造", "字段缺失 -> 回退解析执行", "附件弱绑定 -> 告警继续"],
        outputs=["统一文档对象", "结构完整度评分", "字段缺失清单"],
        observability=["schema_score", "heading_conflict", "attachment_bind_rate", "missing_fields"],
    ),
    "evidence_constructor": _stage(
        stage_id="evidence_constructor",
        label="证据构造",
        group="证据与知识生成",
        objective="从统一文档对象中切出可回溯的证据片段、证据块和原文锚点。",
        ai_mode="证据片段定位",
        default_action="auto_pass",
        inputs=["统一文档对象", "证据抽取模板", "锚点定位策略"],
        ai_adaptation="AI 按语义边界和章节结构切出证据片段，并补齐原文坐标与上下文摘要。",
        rules=[
            _rule("evi-1", "最小上下文窗口", "证据必须保留前后文窗口", "context_window >= 2", "auto_pass"),
            _rule("evi-2", "锚点可回溯性", "没有原文锚点的证据不能进入图谱", "anchor_present = true", "block_return"),
            _rule("evi-3", "重复证据折叠", "重复率偏高时先做折叠再继续", "duplicate_ratio <= 0.2", "warn_continue"),
        ],
        branches=["证据稳定 -> 图谱/切块层", "锚点缺失 -> 回退统一文档", "重复过高 -> 折叠后继续"],
        outputs=["证据片段集", "原文锚点", "证据上下文摘要"],
        observability=["evidence_count", "anchor_present_rate", "duplicate_ratio", "context_window"],
    ),
    "evidence_graph_chunk_layer": _stage(
        stage_id="evidence_graph_chunk_layer",
        label="证据图谱/切块",
        group="证据与知识生成",
        objective="将证据片段组织成图谱节点和 chunk 分层，为候选知识生成准备结构化上下文。",
        ai_mode="图谱切块编排",
        default_action="auto_pass",
        inputs=["证据片段集", "图谱建模模板", "切块窗口策略"],
        ai_adaptation="AI 根据实体密度、关系密度和章节边界自动生成图谱节点与 chunk 布局。",
        rules=[
            _rule("graph-1", "切块密度控制", "单块证据过密时自动拆块", "chunk_token <= 1200", "auto_pass"),
            _rule("graph-2", "跨章混块保护", "跨章证据默认不直接混块", "cross_section_ratio <= 0.25", "warn_continue"),
            _rule("graph-3", "孤立节点率", "孤立节点过高时转人工复核", "orphan_node_ratio <= 0.18", "manual_review"),
        ],
        branches=["切块稳定 -> 证据包", "跨章混块 -> 保守拆分后继续", "孤立率过高 -> 人工复核"],
        outputs=["证据图谱节点", "chunk 分层结果", "关系候选边"],
        observability=["chunk_token", "cross_section_ratio", "orphan_node_ratio", "relation_density"],
    ),
    "evidence_pack": _stage(
        stage_id="evidence_pack",
        label="证据包",
        group="证据与知识生成",
        objective="将图谱节点、chunk 和原文证据打包成标准证据包，供后续三条 AI 审查支路消费。",
        ai_mode="证据包编排与压缩",
        default_action="auto_pass",
        inputs=["证据图谱节点", "chunk 分层结果", "关系候选边"],
        ai_adaptation="AI 自动裁剪主证据、补证据和风险摘要，保持包体紧凑且可追踪。",
        rules=[
            _rule("pack-1", "支撑文档下限", "每个候选对象至少附带主证据和补证据", "support_doc_count >= 2", "warn_continue"),
            _rule("pack-2", "证据包长度", "包体过长时自动摘要压缩", "pack_token <= 1800", "auto_pass"),
            _rule("pack-3", "引用闭环", "引用链必须能回到原文锚点", "citation_closed = true", "block_return"),
        ],
        branches=["证据包稳定 -> 三条审查支路", "包体过长 -> 摘要压缩后继续", "引用断裂 -> 回退图谱层"],
        outputs=["标准证据包", "主证据/补证据集合", "风险摘要"],
        observability=["support_doc_count", "pack_token", "citation_closed", "pack_risk_score"],
    ),
    "concept_candidate_review": _stage(
        stage_id="concept_candidate_review",
        label="概念审查",
        group="证据与知识生成",
        objective="筛出值得进入规范知识层的概念候选、术语候选和对象候选。",
        ai_mode="概念候选判断",
        default_action="manual_review",
        inputs=["标准证据包", "概念抽取提示词", "术语白名单/黑名单"],
        ai_adaptation="AI 结合证据包和术语策略生成概念候选，并判断可信门槛。",
        rules=[
            _rule("concept-1", "候选可信度", "可信度不足时转人工复核", "confidence >= 0.78", "manual_review"),
            _rule("concept-2", "术语黑名单", "黑名单术语直接剔除", "term not in blacklist", "block_return"),
            _rule("concept-3", "别名折叠", "别名重合较高时折叠到主概念", "alias_overlap >= 0.65", "auto_pass"),
        ],
        branches=["可信度高 -> 规范知识汇流", "别名重合 -> 折叠后继续", "可信度低 -> 人工复核池"],
        outputs=["概念候选集", "别名映射", "可信度评分"],
        observability=["confidence", "alias_overlap", "blacklist_hit", "candidate_count"],
    ),
    "relation_review_family_normalization": _stage(
        stage_id="relation_review_family_normalization",
        label="关系/家族",
        group="证据与知识生成",
        objective="识别关系、家族归属和继承路径，将关系表达归一到统一 schema。",
        ai_mode="关系归一与家族推断",
        default_action="warn_continue",
        inputs=["标准证据包", "关系 schema", "关系家族词表"],
        ai_adaptation="AI 自动判断关系方向、关系家族和归一化名称，避免同义关系重复入图。",
        rules=[
            _rule("relation-1", "关系方向一致性", "方向不一致时先按 schema 重写", "direction_match = true", "auto_pass"),
            _rule("relation-2", "关系证据充分性", "缺少支撑证据的关系不进入发布链", "evidence_span >= 2", "block_return"),
            _rule("relation-3", "家族归一置信度", "置信度不足时保留告警", "family_confidence >= 0.7", "warn_continue"),
        ],
        branches=["关系稳定 -> 规范知识汇流", "方向冲突 -> schema 重写继续", "证据不足 -> 阻断回退"],
        outputs=["归一关系候选", "关系家族标签", "方向修正日志"],
        observability=["direction_match", "evidence_span", "family_confidence", "relation_count"],
    ),
    "definition_summary_conflict_consolidation": _stage(
        stage_id="definition_summary_conflict_consolidation",
        label="定义/冲突",
        group="证据与知识生成",
        objective="生成定义、摘要和冲突结论，并提前清理可见冲突。",
        ai_mode="定义整合与冲突诊断",
        default_action="manual_review",
        inputs=["标准证据包", "定义模板", "冲突检测策略"],
        ai_adaptation="AI 自动汇总定义候选、摘要和冲突说明，并给出合并或阻断建议。",
        rules=[
            _rule("definition-1", "定义字段完整性", "缺少核心定义字段时不进入规范知识", "definition_core_present = true", "block_return"),
            _rule("definition-2", "冲突密度控制", "冲突密度过高时转人工复核", "conflict_density <= 0.25", "manual_review"),
            _rule("definition-3", "摘要可追溯性", "摘要至少要能回查到一个主证据", "summary_traceable = true", "warn_continue"),
        ],
        branches=["冲突可收敛 -> 规范知识汇流", "冲突过高 -> 人工复核", "定义缺失 -> 回退证据包"],
        outputs=["定义候选", "摘要候选", "冲突说明与合并建议"],
        observability=["definition_core_present", "conflict_density", "summary_traceable", "conflict_count"],
    ),
    "canonical_knowledge": _stage(
        stage_id="canonical_knowledge",
        label="规范知识",
        group="规范化与发布",
        objective="汇总三条审查支路，形成可治理、可发布、可追溯的规范知识对象。",
        ai_mode="规范对象整编",
        default_action="auto_pass",
        inputs=["概念候选集", "归一关系候选", "定义/摘要/冲突结论"],
        ai_adaptation="AI 自动拼装规范知识对象，补齐标准字段、引用索引和版本差异摘要。",
        rules=[
            _rule("canonical-1", "规范名称存在", "没有规范名称时不允许进入质量门禁", "canonical_name present", "block_return"),
            _rule("canonical-2", "引用索引完整", "引用索引缺失时保留告警继续", "citation_index >= 0.9", "warn_continue"),
            _rule("canonical-3", "对象合并阈值", "高重合对象优先合并而非重复入库", "merge_similarity >= 0.82", "auto_pass"),
        ],
        branches=["对象稳定 -> 质量门禁", "索引缺失 -> 告警继续", "名称缺失 -> 回退审查支路"],
        outputs=["规范知识对象", "引用索引", "版本差异摘要"],
        observability=["canonical_name", "citation_index", "merge_similarity", "canonical_object_score"],
    ),
    "quality_policy_evaluation_governance_gate": _stage(
        stage_id="quality_policy_evaluation_governance_gate",
        label="质量门禁",
        group="规范化与发布",
        objective="集中执行质量门禁，决定当前对象是进入发布、告警继续还是阻断；本阶段不交由人工参与。",
        ai_mode="质量门禁规则执行",
        default_action="block_return",
        inputs=["规范知识对象", "质量策略集", "阶段级风险信号"],
        ai_adaptation="AI 只负责整理前序风险信号和指标，最终由策略阈值确定通过、告警继续、延迟发布或阻断。",
        rules=[
            _rule("gate-1", "支撑文档下限", "支撑证据不足时直接阻断", "supporting_documents >= 2", "block_return"),
            _rule("gate-2", "风险信号汇总", "风险过高时记录告警并继续发布链", "risk_score < 0.65", "warn_continue"),
            _rule("gate-3", "发布前冲突清零", "存在硬冲突时禁止进入发布链", "hard_conflict = 0", "block_return"),
        ],
        branches=["门禁通过 -> 发布/API", "风险中等 -> 带告警继续发布链", "硬冲突或支撑不足 -> 阻断回退规范知识"],
        outputs=["Gate 决策", "阻断/告警原因", "发布链策略标记"],
        observability=["supporting_documents", "risk_score", "hard_conflict", "gate_decision"],
    ),
    "indexes_snapshots_apis": _stage(
        stage_id="indexes_snapshots_apis",
        label="发布/API",
        group="规范化与发布",
        objective="控制索引、快照和 API 发布的时机、范围与降级策略。",
        ai_mode="发布策略建议",
        default_action="defer_publish",
        inputs=["Gate 决策", "发布通道配置", "索引/快照策略"],
        ai_adaptation="AI 根据对象类型、变更幅度和风险等级建议发布到哪些索引、快照和 API 通道。",
        rules=[
            _rule("publish-1", "仅门禁通过对象可发布", "未通过门禁的对象不能进入发布通道", "gate_decision = pass", "block_return"),
            _rule("publish-2", "高风险对象延迟发布", "高风险对象先保留快照，不直接开放 API", "risk_score < 0.45", "defer_publish"),
            _rule("publish-3", "索引一致性检查", "索引版本不一致时只保存快照", "index_schema_match = true", "warn_continue"),
        ],
        branches=["门禁通过 -> 正式发布", "风险偏高 -> 延迟发布并保留快照", "索引不一致 -> 仅保留快照"],
        outputs=["索引发布决策", "快照策略", "API 暴露范围"],
        observability=["gate_decision", "risk_score", "index_schema_match", "publish_scope"],
    ),
}


ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID = "architecture_midterm_default"
ARCHITECTURE_MIDTERM_DOCUMENT_TYPES = [
    "AV-1",
    "OV-1",
    "OV-2",
    "OV-5",
    "OV-7",
    "SV-1",
    "SV-2",
    "SV-4",
]
ARCHITECTURE_MIDTERM_DOCUMENT_TYPE_SUMMARY = "、".join(ARCHITECTURE_MIDTERM_DOCUMENT_TYPES)


def _midterm_field(field_name: str, field_type: str, validation: str, example: str) -> dict[str, Any]:
    return _field_contract(
        field_name=field_name,
        source_artifact="midterm_policy_runtime.metric",
        field_type=field_type,
        validation=validation,
        example=example,
        business_meaning=f"Mid Term policy metric: {field_name}",
        missing_action="warn_continue",
    )


def _midterm_input_schema(
    *,
    stage_id: str,
    threshold: str,
    metric_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _field_contract(
            field_name="archive_id",
            source_artifact="archive_context",
            field_type="string",
            validation="non_empty",
            example="midterm-architecture",
            business_meaning="archive that owns the frozen policy package",
        ),
        _field_contract(
            field_name="document_set_id",
            source_artifact="archive_context",
            field_type="string",
            validation="non_empty",
            example="midterm-architecture:document-set",
            business_meaning="document set consumed by this policy package",
        ),
        _field_contract(
            field_name="document_type_summary",
            source_artifact="document_inventory",
            field_type="string[]",
            validation="contains AV-1/OV/SV view summary",
            example="AV-1,OV-1,OV-2,OV-5,OV-7,SV-1,SV-2,SV-4",
            business_meaning="Mid Term architecture document type coverage",
        ),
        _field_contract(
            field_name="source_view_type",
            source_artifact="unified_document_object",
            field_type="string",
            validation="one_of Mid Term view types",
            example="OV-5",
            business_meaning="DoDAF/MODAF-style view type inferred from document title or content",
            missing_action="block_return",
        ),
        *metric_fields,
        _field_contract(
            field_name="source_anchor_ids",
            source_artifact="evidence_anchor",
            field_type="string[]",
            validation="len >= 1",
            example="[OV-5:2.1, SV-2:Table-3]",
            business_meaning="source anchors used by the rule",
            missing_action="warn_continue",
        ),
        _field_contract(
            field_name="policy_snapshot_id",
            source_artifact="policy_snapshot",
            field_type="string",
            validation="non_empty",
            example="RS-MIDTERM-001",
            business_meaning="frozen policy snapshot for this run",
        ),
        _field_contract(
            field_name="rule_threshold",
            source_artifact="policy_rule",
            field_type="string",
            validation="non_empty",
            example=threshold,
            business_meaning=f"threshold expression for {stage_id}",
        ),
        _field_contract(
            field_name="input_hash",
            source_artifact="runtime_snapshot",
            field_type="string",
            validation="sha256",
            example="sha256:input-midterm",
            business_meaning="stable digest used for impact and incremental recompute",
        ),
    ]


def _midterm_output_schema(effect_kind: str, extra_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *extra_fields,
        *_default_output_schema(effect_kind),
    ]


def _midterm_output(field_name: str, target_artifact: str, field_type: str, example: str) -> dict[str, Any]:
    return _output_contract(
        field_name=field_name,
        target_artifact=target_artifact,
        field_type=field_type,
        used_for_impact=True,
        example=example,
        business_meaning=f"Mid Term policy output: {field_name}",
    )


def _midterm_rule(
    *,
    stage_id: str,
    key: str,
    name: str,
    meaning: str,
    threshold: str,
    action: str,
    effect_kind: str,
    metric_fields: list[dict[str, Any]],
    output_fields: list[dict[str, Any]],
    object_types: list[str],
    relation_types: list[str] | None = None,
) -> dict[str, Any]:
    output_schema = _midterm_output_schema(effect_kind, output_fields)
    rule_id = f"{ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID}.{key}"
    return {
        "key": key,
        "rule_id": rule_id,
        "name": name,
        "meaning": meaning,
        "threshold": threshold,
        "action": action,
        "rule_version": "r1.0",
        "effect_kind": effect_kind,
        "scope_selector": {
            "policy_package_id": ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID,
            "source_stage_id": stage_id,
            "document_types": ARCHITECTURE_MIDTERM_DOCUMENT_TYPES,
            "object_types": object_types,
            "relation_types": relation_types or [],
            "requires_source_anchor": True,
            "min_confidence": 0.0,
        },
        "input_schema": _midterm_input_schema(
            stage_id=stage_id,
            threshold=threshold,
            metric_fields=metric_fields,
        ),
        "output_schema": output_schema,
        "parameters": {
            "match_mode": "all",
            "conditions": [
                {
                    "condition_id": f"{rule_id}:threshold",
                    "left": "actual",
                    "operator": "matches",
                    "right": threshold,
                    "description": meaning,
                }
            ],
            "document_types": ARCHITECTURE_MIDTERM_DOCUMENT_TYPES,
            "source_kind": "live_or_policy_snapshot",
        },
        "trace_fields": REQUIRED_TRACE_FIELDS[:],
        "action_mapping": _default_action_mapping(effect_kind, action, output_schema),
    }


def _architecture_midterm_stage_policy_defaults() -> dict[str, dict[str, Any]]:
    return {
        "asset_intake": _stage(
            stage_id="asset_intake",
            label="Mid Term 文档接入",
            group="体系结构文档预检",
            objective="确认 Mid Term 样例的 AV、OV、SV 文档集合和 documentSetId 已绑定到策略运行上下文。",
            ai_mode="文档类型摘要识别 + 规则兜底",
            default_action="block_return",
            inputs=["archiveId", "documentSetId", "Mid Term 文档类型摘要"],
            ai_adaptation="AI 只辅助识别标题中的视图编号，最终由策略字段合同判定是否进入抽取链路。",
            rules=[
                _midterm_rule(
                    stage_id="asset_intake",
                    key="doc-type-summary",
                    name="Mid Term 文档类型覆盖",
                    meaning="策略包必须绑定 AV、OV、SV 文档类型摘要，至少命中一个 Mid Term 视图编号。",
                    threshold="source_view_type in midterm_view_types",
                    action="block_return",
                    effect_kind="filter",
                    metric_fields=[
                        _midterm_field("source_view_type", "string", "one_of Mid Term view types", "OV-2"),
                        _midterm_field("document_type_supported", "boolean", "true", "true"),
                    ],
                    output_fields=[
                        _midterm_output("accepted_document_type", "policy_runtime_context", "string", "OV-2"),
                    ],
                    object_types=["document"],
                ),
                _midterm_rule(
                    stage_id="asset_intake",
                    key="document-set-bound",
                    name="documentSetId 绑定",
                    meaning="运行态必须带有 documentSetId，W3/W4 不从策略编辑状态反查。",
                    threshold="document_set_bound = true",
                    action="block_return",
                    effect_kind="filter",
                    metric_fields=[
                        _midterm_field("document_set_bound", "boolean", "true", "true"),
                    ],
                    output_fields=[
                        _midterm_output("policy_context_ref", "policy_runtime_context", "string", "archiveId/documentSetId"),
                    ],
                    object_types=["document_set"],
                ),
            ],
            branches=["文档类型命中 -> 结构识别", "documentSetId 缺失 -> 阻断并退回接入预检"],
            outputs=["Mid Term 文档类型摘要", "策略运行上下文", "接入阻断原因"],
            observability=["source_view_type", "document_type_supported", "document_set_bound"],
        ),
        "parser_router": _stage(
            stage_id="parser_router",
            label="AV/OV/SV 路由",
            group="体系结构文档预检",
            objective="按 AV、OV、SV 视图族选择结构识别和字段抽取规则族。",
            ai_mode="视图族路由建议",
            default_action="auto_pass",
            inputs=["Mid Term 文档类型摘要", "解析器能力矩阵"],
            ai_adaptation="AI 可以建议视图族，但 action_mapping 只输出可消费的路由决策。",
            rules=[
                _midterm_rule(
                    stage_id="parser_router",
                    key="view-family-routing",
                    name="视图族路由",
                    meaning="AV、OV、SV 文档必须进入对应规则族，避免通用规则吞掉体系结构字段。",
                    threshold="document_type_supported = true",
                    action="auto_pass",
                    effect_kind="normalize",
                    metric_fields=[
                        _midterm_field("document_type_supported", "boolean", "true", "true"),
                        _midterm_field("view_family_count", "number", ">= 1", "3"),
                    ],
                    output_fields=[
                        _midterm_output("view_family_route", "parser_router.output", "string", "operational_view"),
                    ],
                    object_types=["document"],
                ),
            ],
            branches=["AV -> 概述结构识别", "OV -> 作战视图结构识别", "SV -> 系统视图结构识别"],
            outputs=["view_family_route", "parser_profile_id"],
            observability=["source_view_type", "view_family_count", "parser_profile_id"],
        ),
        "parser_execution": _stage(
            stage_id="parser_execution",
            label="文档结构识别",
            group="体系结构文档结构化",
            objective="识别章节、表格、段落、视图编号和原文锚点，形成可追踪结构层。",
            ai_mode="结构修复辅助",
            default_action="warn_continue",
            inputs=["文档正文", "表格解析结果", "视图编号"],
            ai_adaptation="AI 可辅助修复表格和章节层级，合同字段仍由规则输出。",
            rules=[
                _midterm_rule(
                    stage_id="parser_execution",
                    key="section-table-paragraph",
                    name="章节表格段落识别",
                    meaning="每份体系结构文档需要可追踪的章节、表格或段落结构。",
                    threshold="structure_element_count >= 1",
                    action="block_return",
                    effect_kind="split",
                    metric_fields=[
                        _midterm_field("structure_element_count", "number", ">= 1", "18"),
                        _midterm_field("section_count", "number", ">= 0", "6"),
                        _midterm_field("table_count", "number", ">= 0", "4"),
                        _midterm_field("paragraph_count", "number", ">= 0", "22"),
                    ],
                    output_fields=[
                        _midterm_output("document_structure_units", "unified_document_object", "object", "sections/tables/paragraphs"),
                    ],
                    object_types=["section", "table", "paragraph"],
                ),
                _midterm_rule(
                    stage_id="parser_execution",
                    key="view-number-anchor",
                    name="视图编号与锚点识别",
                    meaning="AV/OV/SV 视图编号和原文锚点必须进入 trace_fields 和后续证据层。",
                    threshold="view_number_present = true && anchor_count >= 1",
                    action="block_return",
                    effect_kind="normalize",
                    metric_fields=[
                        _midterm_field("view_number_present", "boolean", "true", "true"),
                        _midterm_field("anchor_count", "number", ">= 1", "12"),
                    ],
                    output_fields=[
                        _midterm_output("source_anchor_map", "evidence_anchor", "object", "OV-5:2.1 -> paragraph"),
                    ],
                    object_types=["source_anchor"],
                ),
            ],
            branches=["结构完整 -> 统一文档对象", "视图编号缺失 -> 阻断", "锚点不足 -> 回退结构修复"],
            outputs=["document_structure_units", "source_anchor_map", "view_number_index"],
            observability=["structure_element_count", "section_count", "table_count", "paragraph_count", "anchor_count"],
        ),
        "unified_document_object": _stage(
            stage_id="unified_document_object",
            label="体系结构文档对象",
            group="体系结构文档结构化",
            objective="把结构识别结果冻结为统一文档对象，供对象、关系和证据规则消费。",
            ai_mode="字段对齐辅助",
            default_action="auto_pass",
            inputs=["document_structure_units", "source_anchor_map", "view_number_index"],
            ai_adaptation="AI 只辅助补齐字段含义，不能替代字段合同校验。",
            rules=[
                _midterm_rule(
                    stage_id="unified_document_object",
                    key="architecture-document-object",
                    name="统一体系结构文档对象",
                    meaning="统一对象需要带 document type、view number、source anchors 和 input_hash。",
                    threshold="unified_document_score >= 0.75",
                    action="warn_continue",
                    effect_kind="normalize",
                    metric_fields=[
                        _midterm_field("unified_document_score", "number", ">= 0.75", "0.92"),
                    ],
                    output_fields=[
                        _midterm_output("architecture_document_object", "unified_document_object", "object", "OV-2 document object"),
                    ],
                    object_types=["architecture_document"],
                ),
            ],
            branches=["统一对象完整 -> 证据构造", "字段不足 -> 告警并继续候选链"],
            outputs=["architecture_document_object", "document_contract_errors"],
            observability=["unified_document_score", "source_view_type", "anchor_count"],
        ),
        "evidence_constructor": _stage(
            stage_id="evidence_constructor",
            label="证据锚点构造",
            group="证据与候选生成",
            objective="把章节、表格和段落锚点转换为对象与关系抽取可消费的证据片段。",
            ai_mode="证据片段定位",
            default_action="auto_pass",
            inputs=["architecture_document_object", "source_anchor_map"],
            ai_adaptation="AI 可建议上下文窗口，但锚点和输出哈希由规则合同生成。",
            rules=[
                _midterm_rule(
                    stage_id="evidence_constructor",
                    key="evidence-anchor-coverage",
                    name="证据锚点覆盖",
                    meaning="候选对象或关系必须至少能回查到一个源文档锚点。",
                    threshold="anchor_count >= 1",
                    action="block_return",
                    effect_kind="filter",
                    metric_fields=[
                        _midterm_field("anchor_count", "number", ">= 1", "12"),
                        _midterm_field("evidence_count", "number", ">= 1", "20"),
                    ],
                    output_fields=[
                        _midterm_output("evidence_anchor_refs", "evidence_pack", "string[]", "[OV-2:Table-1]"),
                    ],
                    object_types=["evidence_anchor"],
                ),
            ],
            branches=["锚点充分 -> 证据图谱", "锚点缺失 -> 阻断"],
            outputs=["evidence_anchor_refs", "evidence_span_index"],
            observability=["anchor_count", "evidence_count", "source_view_type"],
        ),
        "evidence_graph_chunk_layer": _stage(
            stage_id="evidence_graph_chunk_layer",
            label="证据图谱切块",
            group="证据与候选生成",
            objective="按章节和视图编号切分证据，保护跨文档合并所需的锚点边界。",
            ai_mode="图谱切块编排",
            default_action="auto_pass",
            inputs=["evidence_anchor_refs", "document_structure_units"],
            ai_adaptation="AI 可调整 chunk 粒度，但不得丢弃 source_anchor_ids。",
            rules=[
                _midterm_rule(
                    stage_id="evidence_graph_chunk_layer",
                    key="chunk-anchor-retention",
                    name="切块锚点保留",
                    meaning="每个证据 chunk 必须保留文档类型、视图编号和原文锚点。",
                    threshold="chunk_anchor_retention >= 0.9",
                    action="warn_continue",
                    effect_kind="split",
                    metric_fields=[
                        _midterm_field("chunk_anchor_retention", "number", ">= 0.9", "0.96"),
                    ],
                    output_fields=[
                        _midterm_output("evidence_chunk_refs", "evidence_graph", "string[]", "[chunk-OV5-01]"),
                    ],
                    object_types=["evidence_chunk"],
                ),
            ],
            branches=["锚点保留达标 -> 证据包", "锚点保留不足 -> 告警"],
            outputs=["evidence_chunk_refs", "chunk_anchor_retention"],
            observability=["chunk_anchor_retention", "anchor_count"],
        ),
        "evidence_pack": _stage(
            stage_id="evidence_pack",
            label="证据包",
            group="证据与候选生成",
            objective="把 AV/OV/SV 证据包冻结为对象抽取、关系抽取和质量门禁可消费输入。",
            ai_mode="证据包压缩",
            default_action="auto_pass",
            inputs=["evidence_chunk_refs", "source_anchor_ids"],
            ai_adaptation="AI 可摘要证据，但必须保留 source_anchor_ids 和 output_hash。",
            rules=[
                _midterm_rule(
                    stage_id="evidence_pack",
                    key="evidence-pack-ready",
                    name="证据包可消费",
                    meaning="证据包需要具备对象候选、关系候选和质量门禁共同消费的字段。",
                    threshold="evidence_coverage_rate >= 0.75",
                    action="warn_continue",
                    effect_kind="normalize",
                    metric_fields=[
                        _midterm_field("evidence_coverage_rate", "number", ">= 0.75", "0.88"),
                    ],
                    output_fields=[
                        _midterm_output("evidence_pack_id", "evidence_pack", "string", "epack-midterm-001"),
                    ],
                    object_types=["evidence_pack"],
                ),
            ],
            branches=["证据包达标 -> 对象抽取", "覆盖不足 -> 告警并记录质量风险"],
            outputs=["evidence_pack_id", "evidence_coverage_rate"],
            observability=["evidence_coverage_rate", "evidence_count", "anchor_count"],
        ),
        "concept_candidate_review": _stage(
            stage_id="concept_candidate_review",
            label="体系结构对象抽取",
            group="对象与关系生成",
            objective="抽取 Operational Node、System、Capability、Activity 和 Information Exchange 候选。",
            ai_mode="体系结构对象候选生成",
            default_action="manual_review",
            inputs=["evidence_pack_id", "体系结构对象词表"],
            ai_adaptation="AI 可生成候选，但每类对象必须由规则字段合同记录来源和输出。",
            rules=[
                _midterm_rule(
                    stage_id="concept_candidate_review",
                    key="object-operational-node",
                    name="Operational Node 抽取",
                    meaning="OV-2/OV-5 中的作战节点候选必须带名称、类型和锚点。",
                    threshold="operational_node_count >= 1",
                    action="warn_continue",
                    effect_kind="score",
                    metric_fields=[_midterm_field("operational_node_count", "number", ">= 1", "4")],
                    output_fields=[_midterm_output("operational_node_candidates", "candidate_knowledge", "object", "Operational Node")],
                    object_types=["Operational Node"],
                ),
                _midterm_rule(
                    stage_id="concept_candidate_review",
                    key="object-system",
                    name="System 抽取",
                    meaning="SV-1/SV-2/SV-4 中的系统候选必须能映射到证据锚点。",
                    threshold="system_count >= 1",
                    action="warn_continue",
                    effect_kind="score",
                    metric_fields=[_midterm_field("system_count", "number", ">= 1", "5")],
                    output_fields=[_midterm_output("system_candidates", "candidate_knowledge", "object", "System")],
                    object_types=["System"],
                ),
                _midterm_rule(
                    stage_id="concept_candidate_review",
                    key="object-capability",
                    name="Capability 抽取",
                    meaning="AV/OV 文档中的能力候选需要保留视图编号和证据片段。",
                    threshold="capability_count >= 1",
                    action="warn_continue",
                    effect_kind="score",
                    metric_fields=[_midterm_field("capability_count", "number", ">= 1", "3")],
                    output_fields=[_midterm_output("capability_candidates", "candidate_knowledge", "object", "Capability")],
                    object_types=["Capability"],
                ),
                _midterm_rule(
                    stage_id="concept_candidate_review",
                    key="object-activity",
                    name="Activity 抽取",
                    meaning="OV-5 活动节点需要抽取为 Activity 候选并进入关系规则。",
                    threshold="activity_count >= 1",
                    action="warn_continue",
                    effect_kind="score",
                    metric_fields=[_midterm_field("activity_count", "number", ">= 1", "7")],
                    output_fields=[_midterm_output("activity_candidates", "candidate_knowledge", "object", "Activity")],
                    object_types=["Activity"],
                ),
                _midterm_rule(
                    stage_id="concept_candidate_review",
                    key="object-information-exchange",
                    name="Information Exchange 抽取",
                    meaning="OV-2/SV-2/SV-4 中的信息交换候选必须连接至少两个对象。",
                    threshold="information_exchange_count >= 1",
                    action="warn_continue",
                    effect_kind="score",
                    metric_fields=[_midterm_field("information_exchange_count", "number", ">= 1", "6")],
                    output_fields=[_midterm_output("information_exchange_candidates", "candidate_knowledge", "object", "Information Exchange")],
                    object_types=["Information Exchange"],
                ),
            ],
            branches=["对象候选达标 -> 关系抽取", "低置信对象 -> 候选复核池"],
            outputs=["object_candidates", "object_type_distribution", "low_confidence_candidates"],
            observability=["operational_node_count", "system_count", "capability_count", "activity_count", "information_exchange_count"],
        ),
        "relation_review_family_normalization": _stage(
            stage_id="relation_review_family_normalization",
            label="关系抽取",
            group="对象与关系生成",
            objective="抽取 performs、exchanges、part_of、supports、mapped_to、depends_on 关系。",
            ai_mode="关系方向与家族归一",
            default_action="warn_continue",
            inputs=["object_candidates", "evidence_pack_id", "关系 schema"],
            ai_adaptation="AI 可建议关系方向，规则合同负责 action_mapping 和输出字段。",
            rules=[
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-performs", name="performs 关系抽取", meaning="Operational Node 或 System 执行 Activity 的关系需要证据锚点。", threshold="performs_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("performs_count", "number", ">= 1", "4")], output_fields=[_midterm_output("performs_relations", "runtime_relation", "object", "node performs activity")], object_types=["Activity"], relation_types=["performs"]),
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-exchanges", name="exchanges 关系抽取", meaning="Information Exchange 需要连接源、目标和交换内容。", threshold="exchanges_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("exchanges_count", "number", ">= 1", "6")], output_fields=[_midterm_output("exchanges_relations", "runtime_relation", "object", "system exchanges information")], object_types=["Information Exchange"], relation_types=["exchanges"]),
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-part-of", name="part_of 关系抽取", meaning="节点、系统、能力和活动层级关系需要跨文档合并前归一。", threshold="part_of_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("part_of_count", "number", ">= 1", "3")], output_fields=[_midterm_output("part_of_relations", "runtime_relation", "object", "system part_of system-of-systems")], object_types=["Operational Node", "System", "Capability", "Activity"], relation_types=["part_of"]),
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-supports", name="supports 关系抽取", meaning="系统或能力支持作战活动的关系需要保留证据覆盖。", threshold="supports_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("supports_count", "number", ">= 1", "3")], output_fields=[_midterm_output("supports_relations", "runtime_relation", "object", "system supports activity")], object_types=["System", "Capability", "Activity"], relation_types=["supports"]),
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-mapped-to", name="mapped_to 关系抽取", meaning="OV 与 SV 之间的对象映射需要 source_view_type 和 source_anchor_ids。", threshold="mapped_to_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("mapped_to_count", "number", ">= 1", "2")], output_fields=[_midterm_output("mapped_to_relations", "runtime_relation", "object", "OV activity mapped_to SV function")], object_types=["Activity", "System"], relation_types=["mapped_to"]),
                _midterm_rule(stage_id="relation_review_family_normalization", key="relation-depends-on", name="depends_on 关系抽取", meaning="系统或活动依赖关系需要进入影响面分析。", threshold="depends_on_count >= 1", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("depends_on_count", "number", ">= 1", "2")], output_fields=[_midterm_output("depends_on_relations", "runtime_relation", "object", "system depends_on interface")], object_types=["System", "Activity"], relation_types=["depends_on"]),
            ],
            branches=["关系完整 -> 跨文档合并", "关系缺证据 -> 告警并记录质量风险"],
            outputs=["relation_candidates", "relation_family_labels", "direction_fix_log"],
            observability=["performs_count", "exchanges_count", "part_of_count", "supports_count", "mapped_to_count", "depends_on_count"],
        ),
        "definition_summary_conflict_consolidation": _stage(
            stage_id="definition_summary_conflict_consolidation",
            label="定义与冲突整理",
            group="跨文档合并",
            objective="整理对象定义、别名、证据冲突和跨视图命名差异。",
            ai_mode="定义摘要与冲突诊断",
            default_action="manual_review",
            inputs=["object_candidates", "relation_candidates", "evidence_anchor_refs"],
            ai_adaptation="AI 可摘要冲突，但冲突数和合并建议必须写入规则输出。",
            rules=[
                _midterm_rule(
                    stage_id="definition_summary_conflict_consolidation",
                    key="merge-conflict-density",
                    name="定义冲突密度",
                    meaning="同名或近似对象的定义冲突过高时进入候选复核。",
                    threshold="conflict_count <= 2",
                    action="manual_review",
                    effect_kind="score",
                    metric_fields=[_midterm_field("conflict_count", "number", "<= 2", "1")],
                    output_fields=[_midterm_output("definition_conflict_report", "merge_candidate", "object", "conflict report")],
                    object_types=["candidate_knowledge"],
                ),
            ],
            branches=["冲突可控 -> 规范知识", "冲突过高 -> 候选复核"],
            outputs=["definition_conflict_report", "merge_recommendations"],
            observability=["conflict_count", "semantic_similarity", "alias_overlap"],
        ),
        "canonical_knowledge": _stage(
            stage_id="canonical_knowledge",
            label="跨文档合并",
            group="跨文档合并",
            objective="按同名、别名、视图编号、证据锚点和语义相似度合并候选对象与关系。",
            ai_mode="合并建议生成",
            default_action="auto_pass",
            inputs=["definition_conflict_report", "object_candidates", "relation_candidates"],
            ai_adaptation="AI 可建议合并，规则合同决定是否进入规范候选。",
            rules=[
                _midterm_rule(stage_id="canonical_knowledge", key="merge-same-name", name="同名合并", meaning="同名候选在证据不冲突时合并为同一规范对象。", threshold="same_name_match = true", action="auto_pass", effect_kind="merge", metric_fields=[_midterm_field("same_name_match", "boolean", "true", "true")], output_fields=[_midterm_output("same_name_merge_candidates", "canonical_knowledge", "object", "same-name merge")], object_types=["candidate_knowledge"]),
                _midterm_rule(stage_id="canonical_knowledge", key="merge-alias", name="别名合并", meaning="别名重合达到阈值时合并候选对象并保留别名来源。", threshold="alias_overlap >= 0.65", action="auto_pass", effect_kind="merge", metric_fields=[_midterm_field("alias_overlap", "number", ">= 0.65", "0.78")], output_fields=[_midterm_output("alias_merge_candidates", "canonical_knowledge", "object", "alias merge")], object_types=["candidate_knowledge"]),
                _midterm_rule(stage_id="canonical_knowledge", key="merge-view-number", name="视图编号合并", meaning="相同视图编号和相邻锚点可增强合并置信度。", threshold="view_number_match = true", action="auto_pass", effect_kind="merge", metric_fields=[_midterm_field("view_number_match", "boolean", "true", "true")], output_fields=[_midterm_output("view_number_merge_candidates", "canonical_knowledge", "object", "OV-5 merge")], object_types=["candidate_knowledge"]),
                _midterm_rule(stage_id="canonical_knowledge", key="merge-evidence-anchor", name="证据锚点合并", meaning="跨文档合并必须保留每个来源锚点，不允许丢失证据链。", threshold="merge_anchor_coverage >= 0.9", action="warn_continue", effect_kind="merge", metric_fields=[_midterm_field("merge_anchor_coverage", "number", ">= 0.9", "0.95")], output_fields=[_midterm_output("merge_anchor_map", "canonical_knowledge", "object", "merged anchor map")], object_types=["candidate_knowledge"]),
                _midterm_rule(stage_id="canonical_knowledge", key="merge-semantic-similarity", name="语义相似度合并", meaning="语义相似但名称不同的候选只进入候选合并，不直接覆盖正式知识。", threshold="semantic_similarity >= 0.82", action="manual_review", effect_kind="merge", metric_fields=[_midterm_field("semantic_similarity", "number", ">= 0.82", "0.87")], output_fields=[_midterm_output("semantic_merge_candidates", "canonical_knowledge", "object", "semantic merge")], object_types=["candidate_knowledge"]),
            ],
            branches=["合并命中 -> 规范候选", "语义合并 -> 候选复核", "锚点不足 -> 告警"],
            outputs=["canonical_candidates", "merge_anchor_map", "merge_decisions"],
            observability=["same_name_match", "alias_overlap", "view_number_match", "merge_anchor_coverage", "semantic_similarity"],
        ),
        "quality_policy_evaluation_governance_gate": _stage(
            stage_id="quality_policy_evaluation_governance_gate",
            label="质量门禁",
            group="质量治理",
            objective="执行证据覆盖率、关系完整性、冲突数、孤立节点比例和低置信候选比例门禁。",
            ai_mode="质量门禁规则执行",
            default_action="block_return",
            inputs=["canonical_candidates", "relation_candidates", "merge_decisions"],
            ai_adaptation="AI 只整理风险信号，最终由门禁阈值决定 pass、warning 或 block。",
            rules=[
                _midterm_rule(stage_id=QUALITY_GATE_STAGE_ID, key="gate-evidence-coverage", name="证据覆盖率门禁", meaning="规范候选证据覆盖率不足时不得进入发布候选。", threshold="evidence_coverage_rate >= 0.8", action="block_return", effect_kind="score", metric_fields=[_midterm_field("evidence_coverage_rate", "number", ">= 0.8", "0.88")], output_fields=[_midterm_output("quality_gate_decision", "gate_decision", "enum", "pass")], object_types=["canonical_knowledge"]),
                _midterm_rule(stage_id=QUALITY_GATE_STAGE_ID, key="gate-relation-integrity", name="关系完整性门禁", meaning="关系两端对象和证据链必须完整。", threshold="relation_integrity >= 0.75", action="block_return", effect_kind="score", metric_fields=[_midterm_field("relation_integrity", "number", ">= 0.75", "0.84")], output_fields=[_midterm_output("relation_integrity_report", "gate_decision", "object", "relation gate")], object_types=["runtime_relation"]),
                _midterm_rule(stage_id=QUALITY_GATE_STAGE_ID, key="gate-conflict-count", name="冲突数门禁", meaning="硬冲突超过阈值时阻断发布候选。", threshold="conflict_count <= 2", action="block_return", effect_kind="score", metric_fields=[_midterm_field("conflict_count", "number", "<= 2", "1")], output_fields=[_midterm_output("conflict_gate_report", "gate_decision", "object", "conflict gate")], object_types=["canonical_knowledge"]),
                _midterm_rule(stage_id=QUALITY_GATE_STAGE_ID, key="gate-orphan-node-ratio", name="孤立节点比例门禁", meaning="孤立节点比例过高表示关系抽取不完整。", threshold="orphan_node_ratio <= 0.18", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("orphan_node_ratio", "number", "<= 0.18", "0.12")], output_fields=[_midterm_output("orphan_node_report", "gate_decision", "object", "orphan node report")], object_types=["canonical_knowledge"]),
                _midterm_rule(stage_id=QUALITY_GATE_STAGE_ID, key="gate-low-confidence-ratio", name="低置信候选比例门禁", meaning="低置信候选比例过高时只输出候选重算结果。", threshold="low_confidence_candidate_ratio <= 0.25", action="warn_continue", effect_kind="score", metric_fields=[_midterm_field("low_confidence_candidate_ratio", "number", "<= 0.25", "0.16")], output_fields=[_midterm_output("low_confidence_report", "gate_decision", "object", "confidence report")], object_types=["candidate_knowledge"]),
            ],
            branches=["门禁通过 -> 发布候选", "告警 -> 候选发布并保留解释", "阻断 -> 回退候选层"],
            outputs=["quality_gate_decision", "quality_explanations", "blocked_reason"],
            observability=["evidence_coverage_rate", "relation_integrity", "conflict_count", "orphan_node_ratio", "low_confidence_candidate_ratio"],
        ),
        "indexes_snapshots_apis": _stage(
            stage_id="indexes_snapshots_apis",
            label="候选发布快照",
            group="质量治理",
            objective="只生成可治理的候选发布快照，不直接写正式知识。",
            ai_mode="发布候选范围建议",
            default_action="defer_publish",
            inputs=["quality_gate_decision", "quality_explanations"],
            ai_adaptation="AI 可建议发布范围，但系统输出仍标记为候选态。",
            rules=[
                _midterm_rule(
                    stage_id="indexes_snapshots_apis",
                    key="candidate-publication-only",
                    name="候选发布边界",
                    meaning="策略变更和机器抽取结果只能生成候选快照，等待治理确认。",
                    threshold="candidate_publication_ready = true",
                    action="defer_publish",
                    effect_kind="publish_candidate",
                    metric_fields=[
                        _midterm_field("candidate_publication_ready", "boolean", "true", "true"),
                    ],
                    output_fields=[
                        _midterm_output("publication_candidate_snapshot_id", "publication_snapshot", "string", "pub-candidate-midterm-001"),
                    ],
                    object_types=["publication_candidate"],
                ),
            ],
            branches=["候选就绪 -> 生成候选快照", "未就绪 -> 延迟发布"],
            outputs=["publication_candidate_snapshot_id", "publication_scope", "candidate_status"],
            observability=["candidate_publication_ready", "quality_gate_decision"],
        ),
    }


def _default_stage_policy_defaults() -> dict[str, dict[str, Any]]:
    return _architecture_midterm_stage_policy_defaults()


def build_default_archive_policy_config(archive_id: str) -> dict[str, Any]:
    stages = deepcopy(_default_stage_policy_defaults())
    for stage_id, stage in stages.items():
        stage["rules"] = _enrich_stage_rules(stage_id, stage.get("rules", []))

    config = {
        "archive_id": archive_id,
        "policy_contract_version": POLICY_CONTRACT_VERSION,
        "policy_package_id": ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID,
        "policy_package_name": "Mid Term 体系结构默认策略包",
        "policy_package_version_id": f"{archive_id}:{ARCHITECTURE_MIDTERM_POLICY_PACKAGE_ID}:policy:v1",
        "policy_package_version_status": "published",
        "policy_package_version_hash": None,
        "policy_package_version_created_at": None,
        "previous_policy_package_version_id": None,
        "policy_package_versions": [],
        "policy_contract_status": "valid",
        "policy_contract_errors": [],
        "version_label": "architecture_midterm_default v1",
        "scope_label": f"Mid Term 体系结构文档：{ARCHITECTURE_MIDTERM_DOCUMENT_TYPE_SUMMARY}",
        "ai_autoadapt_enabled": True,
        "updated_at": None,
        "stage_order": DEFAULT_STAGE_ORDER[:],
        "stages": stages,
    }
    return _finalize_policy_config(config)


def _normalize_action(value: Any, *, fallback: str) -> str:
    if isinstance(value, str) and value in POLICY_ACTIONS:
        return value
    return fallback


def _normalize_stage_action(stage_id: str, value: Any, *, fallback: str) -> str:
    action = _normalize_action(value, fallback=fallback)
    if stage_id == QUALITY_GATE_STAGE_ID and action == "manual_review":
        return "warn_continue"
    return action


def _normalize_text_list(values: Any, fallback: list[str]) -> list[str]:
    if not isinstance(values, list):
        return fallback
    normalized = [str(item).strip() for item in values if str(item).strip()]
    return normalized or fallback


def _normalize_rules(stage_id: str, raw_rules: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_rules, list):
        return _enrich_stage_rules(stage_id, fallback)

    normalized: list[dict[str, Any]] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            continue

        fallback_rule = fallback[min(index, len(fallback) - 1)] if fallback else {"action": "auto_pass"}
        normalized.append(
            _enrich_rule_contract(
                stage_id,
                raw_rule,
                fallback_action=str(fallback_rule.get("action") or "auto_pass"),
                index=index,
            )
        )

    return normalized or _enrich_stage_rules(stage_id, fallback)


def _normalize_quality_gate_stage(stage: dict[str, Any]) -> dict[str, Any]:
    default_stage = _default_stage_policy_defaults()[QUALITY_GATE_STAGE_ID]
    stage["ai_mode"] = default_stage["ai_mode"]

    if "人工" in str(stage.get("objective", "")) or "复核" in str(stage.get("objective", "")):
        stage["objective"] = default_stage["objective"]
    if "人工" in str(stage.get("ai_adaptation", "")) or "复核" in str(stage.get("ai_adaptation", "")):
        stage["ai_adaptation"] = default_stage["ai_adaptation"]
    if any("人工" in str(item) or "复核" in str(item) for item in stage.get("branches", [])):
        stage["branches"] = default_stage["branches"]
    if any("人工" in str(item) or "复核" in str(item) for item in stage.get("outputs", [])):
        stage["outputs"] = default_stage["outputs"]

    default_rules_by_key = {rule["key"]: rule for rule in default_stage["rules"]}
    for rule in stage.get("rules", []):
        if not isinstance(rule, dict):
            continue

        rule["action"] = _normalize_stage_action(QUALITY_GATE_STAGE_ID, rule.get("action"), fallback="warn_continue")
        default_rule = default_rules_by_key.get(str(rule.get("key")))
        if default_rule and ("人工" in str(rule.get("meaning", "")) or "复核" in str(rule.get("meaning", ""))):
            rule["meaning"] = default_rule["meaning"]

    return stage


def normalize_archive_policy_config(archive_id: str, raw_config: dict[str, Any] | None) -> dict[str, Any]:
    config = build_default_archive_policy_config(archive_id)
    if not raw_config:
        return config
    default_stages = _default_stage_policy_defaults()

    config["version_label"] = str(raw_config.get("version_label") or config["version_label"])
    config["scope_label"] = str(raw_config.get("scope_label") or config["scope_label"])
    config["policy_contract_version"] = str(raw_config.get("policy_contract_version") or config["policy_contract_version"])
    config["policy_package_id"] = str(raw_config.get("policy_package_id") or config["policy_package_id"])
    config["policy_package_name"] = str(raw_config.get("policy_package_name") or config["policy_package_name"])
    config["policy_package_version_id"] = str(
        raw_config.get("policy_package_version_id") or config["policy_package_version_id"]
    )
    config["policy_package_version_status"] = str(
        raw_config.get("policy_package_version_status") or config["policy_package_version_status"]
    )
    config["policy_package_version_created_at"] = raw_config.get("policy_package_version_created_at")
    config["previous_policy_package_version_id"] = raw_config.get("previous_policy_package_version_id")
    config["ai_autoadapt_enabled"] = bool(raw_config.get("ai_autoadapt_enabled", config["ai_autoadapt_enabled"]))
    config["updated_at"] = raw_config.get("updated_at")

    candidate_stage_order = [stage_id for stage_id in raw_config.get("stage_order", []) if stage_id in default_stages]
    if candidate_stage_order:
        remaining_stage_ids = [stage_id for stage_id in DEFAULT_STAGE_ORDER if stage_id not in candidate_stage_order]
        config["stage_order"] = candidate_stage_order + remaining_stage_ids

    raw_stages = raw_config.get("stages", {})
    if not isinstance(raw_stages, dict):
        return _finalize_policy_config(config, raw_versions=raw_config.get("policy_package_versions"))

    for stage_id in DEFAULT_STAGE_ORDER:
        stage_default = deepcopy(default_stages[stage_id])
        raw_stage = raw_stages.get(stage_id, {})
        if not isinstance(raw_stage, dict):
            stage_default["rules"] = _enrich_stage_rules(stage_id, stage_default.get("rules", []))
            config["stages"][stage_id] = stage_default
            continue

        stage_default["enabled"] = bool(raw_stage.get("enabled", stage_default["enabled"]))
        stage_default["label"] = str(raw_stage.get("label") or stage_default["label"])
        stage_default["group"] = str(raw_stage.get("group") or stage_default["group"])
        stage_default["ai_mode"] = str(raw_stage.get("ai_mode") or stage_default["ai_mode"])
        stage_default["default_action"] = _normalize_stage_action(
            stage_id,
            raw_stage.get("default_action"),
            fallback=stage_default["default_action"],
        )
        stage_default["objective"] = str(raw_stage.get("objective") or stage_default["objective"])
        stage_default["inputs"] = _normalize_text_list(raw_stage.get("inputs"), stage_default["inputs"])
        stage_default["ai_adaptation"] = str(raw_stage.get("ai_adaptation") or stage_default["ai_adaptation"])
        stage_default["rules"] = _normalize_rules(stage_id, raw_stage.get("rules"), stage_default["rules"])
        stage_default["branches"] = _normalize_text_list(raw_stage.get("branches"), stage_default["branches"])
        stage_default["outputs"] = _normalize_text_list(raw_stage.get("outputs"), stage_default["outputs"])
        stage_default["observability"] = _normalize_text_list(raw_stage.get("observability"), stage_default["observability"])
        if stage_id == QUALITY_GATE_STAGE_ID:
            stage_default = _normalize_quality_gate_stage(stage_default)
        config["stages"][stage_id] = stage_default

    return _finalize_policy_config(config, raw_versions=raw_config.get("policy_package_versions"))


def build_policy_run_snapshot(
    archive_id: str,
    policy_config: dict[str, Any] | None,
    *,
    captured_at: str | None,
) -> dict[str, Any]:
    normalized = normalize_archive_policy_config(archive_id, policy_config)
    policy_version = str(
        normalized.get("policy_package_version_id")
        or normalized.get("version_label")
        or "unknown-policy-version"
    )
    snapshot_payload = {
        "archive_id": archive_id,
        "policy_contract_version": normalized["policy_contract_version"],
        "policy_package_id": normalized["policy_package_id"],
        "policy_package_name": normalized["policy_package_name"],
        "policy_package_version_id": normalized["policy_package_version_id"],
        "policy_package_version_status": normalized["policy_package_version_status"],
        "policy_package_version_hash": normalized["policy_package_version_hash"],
        "policy_package_version_created_at": normalized.get("policy_package_version_created_at"),
        "previous_policy_package_version_id": normalized.get("previous_policy_package_version_id"),
        "policy_package_versions": deepcopy(normalized.get("policy_package_versions", [])),
        "policy_contract_status": normalized.get("policy_contract_status"),
        "policy_contract_errors": deepcopy(normalized.get("policy_contract_errors", [])),
        "policy_version": policy_version,
        "version_label": normalized["version_label"],
        "scope_label": normalized["scope_label"],
        "ai_autoadapt_enabled": normalized["ai_autoadapt_enabled"],
        "config_updated_at": normalized.get("updated_at"),
        "stage_order": normalized["stage_order"],
        "stages": [
            {
                "stage_id": stage_id,
                "label": normalized["stages"][stage_id]["label"],
                "enabled": normalized["stages"][stage_id]["enabled"],
                "ai_mode": normalized["stages"][stage_id]["ai_mode"],
                "default_action": normalized["stages"][stage_id]["default_action"],
                "rule_count": len(normalized["stages"][stage_id]["rules"]),
                "rules": deepcopy(normalized["stages"][stage_id]["rules"]),
            }
            for stage_id in normalized["stage_order"]
            if stage_id in normalized["stages"]
        ],
    }
    snapshot_json = json.dumps(snapshot_payload, ensure_ascii=False, sort_keys=True)
    snapshot_id = md5(snapshot_json.encode("utf-8")).hexdigest()[:12]
    return {
        "snapshot_id": snapshot_id,
        "policy_snapshot_id": snapshot_id,
        "run_id": f"RUN-{snapshot_id}",
        "captured_at": captured_at,
        **snapshot_payload,
    }
