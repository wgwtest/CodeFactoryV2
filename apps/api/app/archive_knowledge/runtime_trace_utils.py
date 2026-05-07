from __future__ import annotations

from typing import Any

from app.archive_knowledge.runtime_contract import (
    RuntimeEvent,
    RuntimeSummaryField,
    RuntimeSummarySection,
)


def build_runtime_events(stage_trace: dict[str, Any] | None) -> list[RuntimeEvent]:
    events: list[RuntimeEvent] = []
    for item in (stage_trace or {}).get("events", []):
        if not isinstance(item, dict):
            continue
        try:
            events.append(RuntimeEvent.model_validate(item))
        except Exception:
            continue
    return events


def build_runtime_sections(stage_trace: dict[str, Any] | None) -> list[RuntimeSummarySection]:
    sections: list[RuntimeSummarySection] = []
    for section in (stage_trace or {}).get("sections", []):
        if not isinstance(section, dict):
            continue
        fields: list[RuntimeSummaryField] = []
        for field in section.get("fields", []):
            if not isinstance(field, dict):
                continue
            try:
                fields.append(RuntimeSummaryField.model_validate(field))
            except Exception:
                continue
        try:
            sections.append(
                RuntimeSummarySection(
                    section_id=str(section.get("section_id") or "runtime-trace"),
                    title=str(section.get("title") or "Runtime Trace"),
                    fields=fields,
                )
            )
        except Exception:
            continue
    return sections


def merge_runtime_events(*event_groups: list[RuntimeEvent]) -> list[RuntimeEvent]:
    merged: list[RuntimeEvent] = []
    seen: set[str] = set()
    for group in event_groups:
        for event in group:
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            merged.append(event)
    return merged


def merge_runtime_sections(*section_groups: list[RuntimeSummarySection]) -> list[RuntimeSummarySection]:
    merged: list[RuntimeSummarySection] = []
    seen: set[str] = set()
    for group in section_groups:
        for section in group:
            if section.section_id in seen:
                continue
            seen.add(section.section_id)
            merged.append(section)
    return merged
