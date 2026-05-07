from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any

from app.archive_knowledge.runtime_contract import RuleExecutionRecord

THRESHOLD_PATTERN = re.compile(
    r"^\s*([A-Za-z_][\w]*)\s*(>=|<=|==|=|>|<|not\s+in|in)\s*(.+?)\s*$",
    re.IGNORECASE,
)
PRESENT_PATTERN = re.compile(r"^\s*([A-Za-z_][\w]*)\s+(present|missing)\s*$", re.IGNORECASE)

ALLOWLISTS = {
    "allowlist": {"pdf", "docx", "xlsx", "pptx", "txt", "md", "csv"},
    "blacklist": set(),
}


def build_policy_contract_stage_trace(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    stage_id: str,
    contribution: dict[str, Any],
    policy_snapshot: dict[str, Any] | None,
    stage_status: str = "completed",
    stage_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    policy_stage = _policy_stage(policy_snapshot, stage_id)
    if not policy_stage:
        return None

    records = build_policy_contract_rule_execution_records(
        archive_id=archive_id,
        document_id=document_id,
        stage_id=stage_id,
        stage_status=stage_status,
        contribution=contribution,
        policy_snapshot=policy_snapshot,
        stage_payload=stage_payload,
    )
    rules = [rule for rule in policy_stage.get("rules", []) if isinstance(rule, dict)]
    metrics = _build_metric_context(contribution=contribution, stage_payload=stage_payload)
    failed_count = sum(1 for record in records if record.metrics.get("outcome") == "failed")
    invalid_count = sum(1 for rule in rules if rule.get("contract_status") == "invalid")

    return {
        "input_count": len(_schema_refs(policy_stage, "input_schema", "source_artifact")),
        "output_count": len(_schema_refs(policy_stage, "output_schema", "target_artifact")),
        "decision_summary": "policy contract shadow execution recorded without mutating extraction artifacts",
        "ai_summary": policy_stage.get("ai_mode") or "policy contract execution",
        "executed_at": (policy_snapshot or {}).get("captured_at") or _now(),
        "policy": _policy_refs(policy_snapshot, stage_id=stage_id, stage_label=policy_stage.get("label")),
        "metrics": metrics,
        "rule_hits": [_record_to_rule_hit(record) for record in records],
        "rule_execution_records": [record.model_dump(mode="json") for record in records],
        "events": [
            {
                "event_id": f"{document_id}:{stage_id}:contract:{record.rule_id}",
                "kind": "rule",
                "level": _event_level(record),
                "message": (
                    f"规则合同 {record.rule_id} 以 {record.rule_version} 执行，"
                    f"结果 {record.decision}。"
                ),
                "object_id": record.rule_id,
                "object_kind": "stage",
                "timestamp": record.executed_at,
            }
            for record in records
        ],
        "sections": [
            {
                "section_id": "policy-contract-execution",
                "title": "规则合同执行",
                "fields": [
                    {"key": "policy_version", "label": "策略版本", "value": str(_policy_refs(policy_snapshot).get("policy_version") or "-"), "tone": "info"},
                    {"key": "rule_count", "label": "规则数", "value": str(len(records)), "tone": "info"},
                    {"key": "failed_rule_count", "label": "未满足规则", "value": str(failed_count), "tone": "warning" if failed_count else "success"},
                    {"key": "invalid_contract_count", "label": "合同异常", "value": str(invalid_count), "tone": "danger" if invalid_count else "success"},
                ],
            },
            {
                "section_id": "policy-contract-artifacts",
                "title": "输入输出合同",
                "fields": [
                    {"key": "input_refs", "label": "输入产物", "value": " / ".join(_schema_refs(policy_stage, "input_schema", "source_artifact")) or "-", "tone": "info"},
                    {"key": "output_refs", "label": "输出产物", "value": " / ".join(_schema_refs(policy_stage, "output_schema", "target_artifact")) or "-", "tone": "info"},
                ],
            },
        ],
    }


def attach_policy_contract_trace(
    *,
    archive_id: str,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    policy_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(policy_snapshot, dict):
        return contribution

    extraction = contribution.setdefault("extraction", {})
    runtime_trace = extraction.setdefault("runtime_trace", {})
    for stage in policy_snapshot.get("stages", []):
        if not isinstance(stage, dict):
            continue
        stage_id = str(stage.get("stage_id") or "")
        if not stage_id or stage_id == "quality_policy_evaluation_governance_gate":
            continue
        runtime_trace.setdefault(
            stage_id,
            build_policy_contract_stage_trace(
                archive_id=archive_id,
                document_id=document_id,
                document_title=document_title,
                stage_id=stage_id,
                contribution=contribution,
                policy_snapshot=policy_snapshot,
            ),
        )
    return contribution


def attach_policy_contract_to_stage_payload(
    payload: dict[str, Any],
    *,
    archive_id: str,
    document_id: str,
    contribution: dict[str, Any] | None,
    policy_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    stage_id = str(payload.get("stage_id") or "")
    if not stage_id or payload.get("rule_execution_records"):
        return payload

    trace = build_policy_contract_stage_trace(
        archive_id=archive_id,
        document_id=document_id,
        document_title=str(payload.get("label") or document_id),
        stage_id=stage_id,
        contribution=contribution or {},
        policy_snapshot=policy_snapshot,
        stage_status=str(payload.get("status") or "completed"),
        stage_payload=payload,
    )
    if not trace:
        return payload

    payload["rule_execution_records"] = trace["rule_execution_records"]
    observer = payload.get("stage_observer")
    if isinstance(observer, dict):
        observer.setdefault("stream", [])
        observer.setdefault("sections", [])
        existing_section_ids = {
            section.get("section_id")
            for section in observer.get("sections", [])
            if isinstance(section, dict)
        }
        observer["stream"].extend(trace["events"])
        observer["sections"].extend(
            section
            for section in trace["sections"]
            if isinstance(section, dict) and section.get("section_id") not in existing_section_ids
        )
    return payload


def build_policy_contract_rule_execution_records(
    *,
    archive_id: str,
    document_id: str,
    stage_id: str,
    stage_status: str,
    contribution: dict[str, Any],
    policy_snapshot: dict[str, Any] | None,
    stage_payload: dict[str, Any] | None = None,
) -> list[RuleExecutionRecord]:
    policy_stage = _policy_stage(policy_snapshot, stage_id)
    if not policy_stage:
        return []

    policy_refs = _policy_refs(policy_snapshot)
    snapshot_id = policy_refs.get("policy_snapshot_id")
    metrics = _build_metric_context(contribution=contribution, stage_payload=stage_payload)
    affected_object_ids = _affected_object_ids(contribution=contribution, stage_payload=stage_payload)
    records: list[RuleExecutionRecord] = []

    for index, rule in enumerate(policy_stage.get("rules", []), start=1):
        if not isinstance(rule, dict):
            continue
        rule_id = str(rule.get("rule_id") or rule.get("key") or f"{stage_id}-rule-{index}")
        rule_version = str(rule.get("rule_version") or "r1.0")
        input_refs = _field_refs(rule.get("input_schema"), "source_artifact", [f"{stage_id}.input"])
        output_refs = _field_refs(rule.get("output_schema"), "target_artifact", [f"{stage_id}.output"])
        evaluation = _evaluate_rule(rule, metrics, stage_status=stage_status)
        input_payload = {
            "archive_id": archive_id,
            "document_id": document_id,
            "stage_id": stage_id,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "input_refs": input_refs,
            "metrics": evaluation.get("used_metrics", {}),
            "snapshot_id": snapshot_id,
        }
        output_payload = {
            "stage_status": stage_status,
            "rule_id": rule_id,
            "decision": evaluation["decision"],
            "affected_object_ids": affected_object_ids,
            "output_refs": output_refs,
        }
        records.append(
            RuleExecutionRecord(
                execution_id=f"rex-{document_id}-{stage_id}-{rule_id}",
                archive_id=archive_id,
                document_id=document_id,
                stage_id=stage_id,
                rule_id=rule_id,
                rule_version=rule_version,
                rule_hash=rule.get("rule_hash"),
                snapshot_id=snapshot_id,
                policy_snapshot_id=snapshot_id,
                policy_package_id=policy_refs.get("policy_package_id"),
                policy_version=policy_refs.get("policy_version"),
                input_artifact_refs=input_refs,
                input_hash=_runtime_hash(input_payload),
                output_artifact_refs=output_refs,
                output_hash=_runtime_hash(output_payload),
                affected_object_ids=affected_object_ids,
                affected_relation_ids=_affected_relation_ids(contribution),
                decision=evaluation["decision"],
                metrics={
                    "stage_status": stage_status,
                    "threshold": rule.get("threshold"),
                    "effect_kind": rule.get("effect_kind"),
                    "contract_status": rule.get("contract_status"),
                    **evaluation,
                },
                executed_at=(policy_snapshot or {}).get("captured_at") or _now(),
                source="policy_snapshot",
            )
        )
    return records


def _policy_stage(policy_snapshot: dict[str, Any] | None, stage_id: str) -> dict[str, Any] | None:
    if not isinstance(policy_snapshot, dict):
        return None
    for stage in policy_snapshot.get("stages", []):
        if isinstance(stage, dict) and stage.get("stage_id") == stage_id:
            return stage
    return None


def _policy_refs(policy_snapshot: dict[str, Any] | None, *, stage_id: str | None = None, stage_label: str | None = None) -> dict[str, Any]:
    policy_snapshot = policy_snapshot if isinstance(policy_snapshot, dict) else {}
    refs = {
        "snapshot_id": policy_snapshot.get("snapshot_id"),
        "policy_snapshot_id": policy_snapshot.get("policy_snapshot_id") or policy_snapshot.get("snapshot_id"),
        "captured_at": policy_snapshot.get("captured_at"),
        "policy_package_id": policy_snapshot.get("policy_package_id"),
        "policy_package_version_id": policy_snapshot.get("policy_package_version_id"),
        "policy_package_version_hash": policy_snapshot.get("policy_package_version_hash"),
        "policy_version": (
            policy_snapshot.get("policy_version")
            or policy_snapshot.get("policy_package_version_id")
            or policy_snapshot.get("version_label")
        ),
        "version_label": policy_snapshot.get("version_label"),
    }
    if stage_id:
        refs["stage_id"] = stage_id
    if stage_label:
        refs["stage_label"] = stage_label
    return refs


def _build_metric_context(*, contribution: dict[str, Any], stage_payload: dict[str, Any] | None) -> dict[str, Any]:
    document = contribution.get("document", {}) if isinstance(contribution, dict) else {}
    entities = _list(contribution.get("entities")) if isinstance(contribution, dict) else []
    events = _list(contribution.get("events")) if isinstance(contribution, dict) else []
    processes = _list(contribution.get("processes")) if isinstance(contribution, dict) else []
    relations = _list(contribution.get("relations")) if isinstance(contribution, dict) else []
    extraction = contribution.get("extraction", {}) if isinstance(contribution, dict) else {}
    all_items = entities + events + processes
    evidence = [
        evidence_item
        for item in all_items
        for evidence_item in _list(item.get("evidence"))
        if isinstance(evidence_item, dict)
    ]
    source_documents = {
        str(document_id)
        for item in all_items
        for document_id in _list(item.get("document_ids"))
        if document_id
    }
    source_documents.update(
        str(item.get("document_id"))
        for item in evidence
        if item.get("document_id")
    )
    relation_confidences = [
        float(relation.get("confidence"))
        for relation in relations
        if _is_number(relation.get("confidence"))
    ]
    avg_relation_confidence = (
        sum(relation_confidences) / len(relation_confidences)
        if relation_confidences
        else 0.0
    )
    file_type = str(document.get("file_type") or "").lower()
    segment_count = int(document.get("segment_count") or 0)
    character_count = int(document.get("character_count") or 0)
    item_count = len(all_items)
    evidence_count = len(evidence)

    metrics: dict[str, Any] = {
        "actual": item_count or evidence_count or segment_count,
        "mime_type": file_type,
        "size": character_count,
        "source_label": document.get("source_archive"),
        "scan_score": 1.0 if document.get("source_digest") else 0.0,
        "top_parser_confidence": 0.95 if document.get("parser_name") else 0.0,
        "language_mix": 1,
        "template_match": 0.8 if file_type in {"pdf", "docx"} else 0.5,
        "body_coverage": 1.0 if segment_count else 0.0,
        "table_split_score": 0.7 if file_type in {"xlsx", "pdf", "docx"} else 0.5,
        "garbled_ratio": 0.0,
        "required_fields": 1.0 if document.get("title") and document.get("path") else 0.5,
        "heading_conflict": 0,
        "attachment_bind_rate": 1.0 if evidence_count else 0.0,
        "context_window": max(1, min(3, segment_count)),
        "anchor_present": evidence_count > 0,
        "duplicate_ratio": 0.0,
        "chunk_token": max(1, character_count // 4) if character_count else 0,
        "cross_section_ratio": 0.0,
        "orphan_node_ratio": 0.0 if item_count else 1.0,
        "support_doc_count": len(source_documents),
        "pack_token": max(1, evidence_count * 80),
        "citation_closed": evidence_count > 0,
        "confidence": round(avg_relation_confidence or (0.82 if item_count else 0.0), 3),
        "term": "",
        "alias_overlap": 0.7 if any(_list(item.get("aliases")) for item in all_items) else 0.0,
        "direction_match": bool(relations),
        "evidence_span": evidence_count,
        "family_confidence": round(avg_relation_confidence or 0.0, 3),
        "definition_core_present": bool(all_items),
        "conflict_density": 0.0,
        "summary_traceable": evidence_count > 0,
        "canonical_name": all_items[0].get("name") if all_items else "",
        "citation_index": 1.0 if evidence_count else 0.0,
        "merge_similarity": 0.86 if item_count else 0.0,
        "supporting_documents": len(source_documents),
        "risk_score": 0.2 if evidence_count else 0.8,
        "hard_conflict": 0,
        "gate_decision": "pass",
        "index_schema_match": True,
        "candidate_count": int(extraction.get("candidate_count") or item_count),
        "relation_count": int(extraction.get("relation_count") or len(relations)),
        "entity_count": len(entities),
        "event_count": len(events),
        "process_count": len(processes),
        "evidence_count": evidence_count,
        "segment_count": segment_count,
        "character_count": character_count,
    }
    _merge_stage_payload_metrics(metrics, stage_payload)
    return metrics


def _merge_stage_payload_metrics(metrics: dict[str, Any], stage_payload: dict[str, Any] | None) -> None:
    if not isinstance(stage_payload, dict):
        return
    for node in ((stage_payload.get("graph") or {}).get("nodes") or []):
        if not isinstance(node, dict):
            continue
        for key, value in (node.get("metrics") or {}).items():
            metrics.setdefault(str(key), value)
    observer = stage_payload.get("stage_observer") or {}
    for section in observer.get("sections", []) if isinstance(observer, dict) else []:
        if not isinstance(section, dict):
            continue
        for field in section.get("fields", []):
            if isinstance(field, dict) and field.get("key") is not None:
                metrics.setdefault(str(field["key"]), field.get("value"))


def _evaluate_rule(rule: dict[str, Any], metrics: dict[str, Any], *, stage_status: str) -> dict[str, Any]:
    if stage_status == "pending":
        return {
            "outcome": "not_started",
            "decision": "not_started",
            "detail": "stage has not entered runtime yet",
            "used_metrics": {},
        }
    if rule.get("contract_status") == "invalid":
        return {
            "outcome": "invalid_contract",
            "decision": "invalid_contract",
            "detail": "; ".join(str(item) for item in rule.get("contract_errors", [])),
            "used_metrics": {},
        }

    evaluation = _evaluate_expression(str(rule.get("threshold") or ""), metrics)
    if evaluation["outcome"] == "not_evaluated":
        evaluation = _evaluate_conditions(rule.get("parameters"), metrics)
    if evaluation["outcome"] == "passed":
        decision = str((rule.get("action_mapping") or {}).get("runtime_decision") or "contract_matched")
    elif evaluation["outcome"] == "failed":
        decision = str(rule.get("action") or (rule.get("action_mapping") or {}).get("on_match") or "rule_failed")
    else:
        decision = evaluation["outcome"]
    return {**evaluation, "decision": decision}


def _evaluate_conditions(parameters: Any, metrics: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parameters, dict):
        return {"outcome": "not_evaluated", "detail": "parameters.conditions missing", "used_metrics": {}}
    conditions = [item for item in parameters.get("conditions", []) if isinstance(item, dict)]
    if not conditions:
        return {"outcome": "not_evaluated", "detail": "parameters.conditions missing", "used_metrics": {}}
    results = [_evaluate_condition(condition, metrics) for condition in conditions]
    evaluated = [result for result in results if result["outcome"] != "not_evaluated"]
    if not evaluated:
        return {"outcome": "not_evaluated", "detail": "no executable conditions", "used_metrics": {}}
    match_mode = str(parameters.get("match_mode") or "all")
    passed = any(result["outcome"] == "passed" for result in evaluated) if match_mode == "any" else all(
        result["outcome"] == "passed" for result in evaluated
    )
    return {
        "outcome": "passed" if passed else "failed",
        "detail": "; ".join(result["detail"] for result in evaluated),
        "used_metrics": {
            key: value
            for result in evaluated
            for key, value in result.get("used_metrics", {}).items()
        },
    }


def _evaluate_condition(condition: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    left = str(condition.get("left") or "")
    operator = str(condition.get("operator") or "")
    right = condition.get("right")
    if left == "actual" and operator == "matches":
        return _evaluate_expression(str(right or ""), metrics)
    return _compare_metric(left, operator, right, metrics)


def _evaluate_expression(expression: str, metrics: dict[str, Any]) -> dict[str, Any]:
    expression = expression.strip()
    if not expression:
        return {"outcome": "not_evaluated", "detail": "empty threshold", "used_metrics": {}}
    parts = [part.strip() for part in expression.split("&&") if part.strip()]
    if len(parts) > 1:
        results = [_evaluate_expression(part, metrics) for part in parts]
        evaluated = [result for result in results if result["outcome"] != "not_evaluated"]
        if not evaluated:
            return {"outcome": "not_evaluated", "detail": expression, "used_metrics": {}}
        passed = all(result["outcome"] == "passed" for result in evaluated)
        return {
            "outcome": "passed" if passed else "failed",
            "detail": "; ".join(result["detail"] for result in evaluated),
            "used_metrics": {
                key: value
                for result in evaluated
                for key, value in result.get("used_metrics", {}).items()
            },
        }
    present_match = PRESENT_PATTERN.match(expression)
    if present_match:
        metric_key, operator = present_match.groups()
        return _compare_metric(metric_key, operator, None, metrics)
    match = THRESHOLD_PATTERN.match(expression)
    if not match:
        return {"outcome": "not_evaluated", "detail": f"threshold not executable: {expression}", "used_metrics": {}}
    metric_key, operator, expected = match.groups()
    return _compare_metric(metric_key, operator, expected, metrics)


def _compare_metric(metric_key: str, operator: str, expected: Any, metrics: dict[str, Any]) -> dict[str, Any]:
    metric_key = metric_key.strip()
    operator = operator.strip().lower()
    if metric_key not in metrics:
        return {"outcome": "not_evaluated", "detail": f"metric {metric_key} unavailable", "used_metrics": {}}
    actual = metrics.get(metric_key)
    expected_value = _parse_literal(expected)
    passed = _compare(actual, operator, expected_value)
    return {
        "outcome": "passed" if passed else "failed",
        "detail": f"{metric_key} actual={actual} expected {operator} {expected_value}",
        "actual": actual,
        "expected": expected_value,
        "operator": operator,
        "used_metrics": {metric_key: actual},
    }


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "present":
        return actual not in {None, "", False}
    if operator == "missing":
        return actual in {None, "", False}
    if operator in {"in", "not in"}:
        values = ALLOWLISTS.get(str(expected), {str(expected)})
        result = str(actual).lower() in values
        return not result if operator == "not in" else result
    if _is_number(actual) and _is_number(expected):
        actual_number = float(actual)
        expected_number = float(expected)
        if operator == ">=":
            return actual_number >= expected_number
        if operator == "<=":
            return actual_number <= expected_number
        if operator == ">":
            return actual_number > expected_number
        if operator == "<":
            return actual_number < expected_number
        return actual_number == expected_number
    if operator in {"=", "=="}:
        return _normalize_scalar(actual) == _normalize_scalar(expected)
    return False


def _parse_literal(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().strip("'\"")
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    try:
        return float(normalized) if "." in normalized else int(normalized)
    except ValueError:
        return normalized.lower()


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _schema_refs(policy_stage: dict[str, Any], schema_name: str, key: str) -> list[str]:
    refs: list[str] = []
    for rule in policy_stage.get("rules", []):
        if isinstance(rule, dict):
            refs.extend(_field_refs(rule.get(schema_name), key, []))
    return _dedupe(refs)


def _field_refs(schema: Any, key: str, fallback: list[str]) -> list[str]:
    if not isinstance(schema, list):
        return fallback
    refs = [
        str(field.get(key))
        for field in schema
        if isinstance(field, dict) and field.get(key)
    ]
    return _dedupe(refs) or fallback


def _affected_object_ids(*, contribution: dict[str, Any], stage_payload: dict[str, Any] | None) -> list[str]:
    ids: list[str] = []
    if isinstance(stage_payload, dict):
        ids.extend(str(item) for item in ((stage_payload.get("graph") or {}).get("primary_node_ids") or []) if item)
        ids.extend(
            str(node.get("node_id"))
            for node in ((stage_payload.get("graph") or {}).get("nodes") or [])[:8]
            if isinstance(node, dict) and node.get("node_id")
        )
    for collection in ("entities", "events", "processes"):
        ids.extend(
            str(item.get("id"))
            for item in _list(contribution.get(collection)) if isinstance(item, dict) and item.get("id")
        )
    return _dedupe(ids)[:24]


def _affected_relation_ids(contribution: dict[str, Any]) -> list[str]:
    relation_ids = []
    for index, relation in enumerate(_list(contribution.get("relations")), start=1):
        if not isinstance(relation, dict):
            continue
        relation_ids.append(
            str(
                relation.get("id")
                or f"rel-{index}:{relation.get('source_name', '')}->{relation.get('target_name', '')}"
            )
        )
    return relation_ids[:24]


def _record_to_rule_hit(record: RuleExecutionRecord) -> dict[str, Any]:
    return {
        "rule_id": record.rule_id,
        "rule_version": record.rule_version,
        "rule_hash": record.rule_hash,
        "effect_kind": record.metrics.get("effect_kind"),
        "threshold": record.metrics.get("threshold"),
        "decision": record.decision,
        "outcome": record.metrics.get("outcome"),
        "detail": record.metrics.get("detail"),
        "actual": record.metrics.get("actual"),
        "expected": record.metrics.get("expected"),
        "input_artifact_refs": record.input_artifact_refs,
        "output_artifact_refs": record.output_artifact_refs,
        "affected_object_ids": record.affected_object_ids,
    }


def _event_level(record: RuleExecutionRecord) -> str:
    outcome = record.metrics.get("outcome")
    if outcome in {"failed", "invalid_contract"}:
        return "warning"
    if outcome in {"not_evaluated", "not_started"}:
        return "info"
    return "success"


def _runtime_hash(payload: Any) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _now() -> str:
    return datetime.now(UTC).isoformat()
