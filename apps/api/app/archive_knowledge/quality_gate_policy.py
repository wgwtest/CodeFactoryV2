from __future__ import annotations

import re
from typing import Any

from app.archive_knowledge.policy_config import STAGE_POLICY_DEFAULTS

QUALITY_GATE_STAGE_ID = "quality_policy_evaluation_governance_gate"

ACTION_PRIORITY = {
    "auto_pass": 0,
    "warn_continue": 10,
    "defer_publish": 20,
    "block_return": 40,
}

ACTION_DECISION_STATUS = {
    "auto_pass": "passed",
    "warn_continue": "warning",
    "defer_publish": "deferred",
    "block_return": "blocked",
}

THRESHOLD_PATTERN = re.compile(r"^\s*([A-Za-z_][\w]*)\s*(>=|<=|==|=|>|<)\s*(.+?)\s*$")


def build_quality_gate_runtime_trace(
    *,
    document_id: str,
    document_title: str,
    contribution: dict[str, Any],
    policy_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    knowledge_items = _collect_knowledge_items(contribution)
    metrics = _build_quality_gate_metrics(knowledge_items)
    stage_policy = _resolve_quality_gate_policy(policy_snapshot)
    rule_hits = [
        _evaluate_rule(rule, metrics, default_action=stage_policy.get("default_action", "block_return"))
        for rule in stage_policy.get("rules", [])
    ]
    decision = _select_gate_decision(rule_hits)

    return {
        "input_count": len(knowledge_items),
        "output_count": 1,
        "decision_summary": "evaluate canonical knowledge candidates against executable quality gate policy",
        "ai_summary": stage_policy.get("ai_mode") or "quality policy gate decision",
        "policy": {
            "snapshot_id": (policy_snapshot or {}).get("snapshot_id"),
            "version_label": (policy_snapshot or {}).get("version_label"),
            "stage_id": QUALITY_GATE_STAGE_ID,
            "stage_label": stage_policy.get("label"),
            "default_action": stage_policy.get("default_action"),
            "ai_mode": stage_policy.get("ai_mode"),
        },
        "metrics": metrics,
        "rule_hits": rule_hits,
        "decision": decision,
        "events": _build_events(document_id, document_title, rule_hits, decision),
        "sections": _build_sections(stage_policy, metrics, rule_hits, decision),
    }


def _collect_knowledge_items(contribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"item_type": "entity", **item} for item in contribution.get("entities", [])
    ] + [
        {"item_type": "event", **item} for item in contribution.get("events", [])
    ] + [
        {"item_type": "process", **item} for item in contribution.get("processes", [])
    ]


def _build_quality_gate_metrics(knowledge_items: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_count = sum(len(item.get("evidence", [])) for item in knowledge_items)
    supporting_documents = {
        str(document_id)
        for item in knowledge_items
        for document_id in item.get("document_ids", [])
        if document_id
    }
    supporting_documents.update(
        str(evidence.get("document_id"))
        for item in knowledge_items
        for evidence in item.get("evidence", [])
        if isinstance(evidence, dict) and evidence.get("document_id")
    )
    pending_count = sum(1 for item in knowledge_items if item.get("review_status", "pending") == "pending")
    rejected_count = sum(1 for item in knowledge_items if item.get("review_status") == "rejected")
    approved_count = sum(1 for item in knowledge_items if item.get("review_status") == "approved")
    hard_conflict = sum(
        1
        for item in knowledge_items
        if item.get("hard_conflict")
        or str(item.get("conflict_status") or "").lower() in {"hard", "hard_conflict", "blocked"}
        or int(item.get("hard_conflict_count") or 0) > 0
    )
    item_count = len(knowledge_items)
    pending_ratio = pending_count / item_count if item_count else 1.0
    rejected_ratio = rejected_count / item_count if item_count else 0.0
    support_gap = max(0, 2 - len(supporting_documents)) / 2
    risk_score = min(1.0, pending_ratio * 0.5 + rejected_ratio * 0.35 + support_gap * 0.35 + hard_conflict * 0.5)

    return {
        "knowledge_item_count": item_count,
        "evidence_count": evidence_count,
        "supporting_documents": len(supporting_documents),
        "pending_review_count": pending_count,
        "rejected_count": rejected_count,
        "approved_count": approved_count,
        "hard_conflict": hard_conflict,
        "risk_score": round(risk_score, 3),
    }


def _resolve_quality_gate_policy(policy_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    default_stage = STAGE_POLICY_DEFAULTS[QUALITY_GATE_STAGE_ID]
    for stage in (policy_snapshot or {}).get("stages", []):
        if not isinstance(stage, dict) or stage.get("stage_id") != QUALITY_GATE_STAGE_ID:
            continue
        return {
            **default_stage,
            **stage,
            "rules": stage.get("rules") or default_stage["rules"],
        }
    return default_stage


def _evaluate_rule(rule: dict[str, Any], metrics: dict[str, Any], *, default_action: str) -> dict[str, Any]:
    threshold = str(rule.get("threshold") or "")
    parsed = THRESHOLD_PATTERN.match(threshold)
    action = _normalize_quality_gate_action(str(rule.get("action") or default_action))
    if not parsed:
        return _rule_hit(rule, action=action, outcome="not_evaluated", detail="threshold is not executable")

    metric_key, operator, expected_text = parsed.groups()
    if metric_key not in metrics:
        return _rule_hit(
            rule,
            action=action,
            outcome="not_evaluated",
            metric_key=metric_key,
            operator=operator,
            expected=expected_text,
            detail=f"metric {metric_key} is not available",
        )

    actual = metrics[metric_key]
    expected = _parse_literal(expected_text)
    passed = _compare(actual, operator, expected)
    return _rule_hit(
        rule,
        action=action,
        outcome="passed" if passed else "failed",
        metric_key=metric_key,
        operator=operator,
        actual=actual,
        expected=expected,
        detail=f"{metric_key} actual={actual} expected {operator} {expected}",
    )


def _rule_hit(
    rule: dict[str, Any],
    *,
    action: str,
    outcome: str,
    detail: str,
    metric_key: str | None = None,
    operator: str | None = None,
    actual: Any = None,
    expected: Any = None,
) -> dict[str, Any]:
    passed = outcome in {"passed", "not_evaluated"}
    return {
        "key": str(rule.get("key") or "quality-rule"),
        "label": str(rule.get("name") or rule.get("key") or "quality rule"),
        "meaning": str(rule.get("meaning") or ""),
        "threshold": str(rule.get("threshold") or ""),
        "action": action,
        "metric_key": metric_key,
        "operator": operator,
        "actual": actual,
        "expected": expected,
        "outcome": outcome,
        "passed": passed,
        "detail": detail,
    }


def _select_gate_decision(rule_hits: list[dict[str, Any]]) -> dict[str, Any]:
    failed_hits = [hit for hit in rule_hits if hit.get("outcome") == "failed"]
    if not failed_hits:
        return {
            "status": "passed",
            "reason": "all executable quality gate rules passed",
            "next_action": "publish_target",
            "blocking_rule_key": None,
            "failed_rule_count": 0,
        }

    decisive_hit = max(failed_hits, key=lambda hit: ACTION_PRIORITY.get(str(hit.get("action")), 0))
    decisive_action = _normalize_quality_gate_action(str(decisive_hit.get("action") or "block_return"))
    status = ACTION_DECISION_STATUS.get(decisive_action, "blocked")
    return {
        "status": status,
        "reason": f"{decisive_hit.get('label')} failed: {decisive_hit.get('detail')}",
        "next_action": _next_action_for_status(status),
        "blocking_rule_key": decisive_hit.get("key"),
        "failed_rule_count": len(failed_hits),
    }


def _next_action_for_status(status: str) -> str:
    if status == "blocked":
        return "blocked_result"
    if status == "deferred":
        return "defer_publish"
    if status == "warning":
        return "continue_with_warning"
    return "publish_target"


def _normalize_quality_gate_action(action: str) -> str:
    # Quality gate is a deterministic machine gate. Any legacy/manual action is
    # converted to a rule warning so human review remains after publication.
    if action == "manual_review":
        return "warn_continue"
    if action in ACTION_DECISION_STATUS:
        return action
    return "block_return"


def _parse_literal(value: str) -> Any:
    normalized = value.strip().strip("'\"")
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    try:
        if "." in normalized:
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if operator == ">=":
            return actual >= expected
        if operator == "<=":
            return actual <= expected
        if operator == ">":
            return actual > expected
        if operator == "<":
            return actual < expected
        return actual == expected
    if operator in {"=", "=="}:
        return actual == expected
    return False


def _build_events(
    document_id: str,
    document_title: str,
    rule_hits: list[dict[str, Any]],
    decision: dict[str, Any],
) -> list[dict[str, Any]]:
    events = [
        {
            "event_id": f"{document_id}:quality-gate:rule:{hit['key']}",
            "kind": "rule",
            "level": "success" if hit.get("outcome") == "passed" else "warning",
            "message": f"Quality gate rule {hit['key']} {hit['outcome']}: {hit['detail']}.",
            "object_id": f"{document_id}:quality-gate:rule-hit:{hit['key']}",
            "object_kind": "node",
        }
        for hit in rule_hits
    ]
    events.append(
        {
            "event_id": f"{document_id}:quality-gate:decision",
            "kind": "block" if decision["status"] == "blocked" else "decision",
            "level": "danger" if decision["status"] == "blocked" else ("warning" if decision["status"] != "passed" else "success"),
            "message": f"Quality gate decision for {document_title}: {decision['status']} because {decision['reason']}.",
            "object_id": f"{document_id}:quality-gate:gate",
            "object_kind": "node",
        }
    )
    return events


def _build_sections(
    stage_policy: dict[str, Any],
    metrics: dict[str, Any],
    rule_hits: list[dict[str, Any]],
    decision: dict[str, Any],
) -> list[dict[str, Any]]:
    failed_rule_count = sum(1 for hit in rule_hits if hit.get("outcome") == "failed")
    return [
        {
            "section_id": "trace-quality-gate-policy",
            "title": "Policy Execution",
            "fields": [
                {"key": "stage_policy", "label": "stage_policy", "value": str(stage_policy.get("label") or QUALITY_GATE_STAGE_ID), "tone": "info"},
                {"key": "default_action", "label": "default_action", "value": str(stage_policy.get("default_action")), "tone": "info"},
                {"key": "rule_count", "label": "rule_count", "value": str(len(rule_hits)), "tone": "info"},
                {"key": "failed_rule_count", "label": "failed_rule_count", "value": str(failed_rule_count), "tone": "warning" if failed_rule_count else "success"},
                {"key": "decision", "label": "decision", "value": str(decision["status"]), "tone": "danger" if decision["status"] == "blocked" else ("warning" if decision["status"] != "passed" else "success")},
            ],
        },
        {
            "section_id": "trace-quality-gate-metrics",
            "title": "Policy Metrics",
            "fields": [
                {"key": key, "label": key, "value": str(value), "tone": "info"}
                for key, value in metrics.items()
            ],
        },
    ]
