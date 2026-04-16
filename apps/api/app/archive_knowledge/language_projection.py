from __future__ import annotations

import re
from typing import TypedDict

from app.archive_knowledge.artifact_catalog import ArtifactInterpretation


class KnowledgeLanguageProjection(TypedDict):
    display_name_zh: str | None
    display_name_en: str | None
    acronym: str | None
    aliases_zh: list[str]
    aliases_en: list[str]
    description_zh: str | None
    evidence_summary_zh: str | None
    translation_status: str
    translation_confidence: float | None


_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_LATIN_PATTERN = re.compile(r"[A-Za-z]")
_ARTIFACT_CODE_PATTERN = re.compile(r"^[A-Z]{1,4}-\d+[A-Z]?$")
_ACRONYM_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,15}$")
_PAREN_LATIN_PATTERN = re.compile(r"[（(]\s*([A-Za-z][A-Za-z0-9 /&-]{1,80})\s*[)）]")


def build_language_projection(
    *,
    name: str,
    aliases: list[str] | None,
    interpretation: ArtifactInterpretation,
    evidence: list[dict] | None,
) -> KnowledgeLanguageProjection:
    normalized_aliases = [alias.strip() for alias in aliases or [] if alias and alias.strip()]
    aliases_zh = _unique([alias for alias in normalized_aliases if _contains_cjk(alias)])
    aliases_en = _unique([alias for alias in normalized_aliases if _contains_latin(alias) and not _contains_cjk(alias)])

    display_name_zh = _resolve_display_name_zh(name=name, interpretation=interpretation)
    display_name_en = _resolve_display_name_en(name=name, aliases=normalized_aliases, interpretation=interpretation)
    acronym = _resolve_acronym(name=name, aliases=normalized_aliases)
    description_zh = interpretation.get("summary") or None
    evidence_summary_zh = _resolve_evidence_summary_zh(evidence or [])

    populated_fields = sum(
        1
        for value in (
            display_name_zh,
            display_name_en,
            acronym,
            description_zh,
            evidence_summary_zh,
        )
        if value
    )
    translation_status = "derived" if populated_fields > 0 else "none"
    translation_confidence = round(min(0.55 + populated_fields * 0.1, 0.95), 2) if populated_fields > 0 else None

    return {
        "display_name_zh": display_name_zh,
        "display_name_en": display_name_en,
        "acronym": acronym,
        "aliases_zh": aliases_zh,
        "aliases_en": aliases_en,
        "description_zh": description_zh,
        "evidence_summary_zh": evidence_summary_zh,
        "translation_status": translation_status,
        "translation_confidence": translation_confidence,
    }


def _resolve_display_name_zh(*, name: str, interpretation: ArtifactInterpretation) -> str | None:
    direct_zh = _extract_chinese_display_name(name)
    if direct_zh:
        return direct_zh
    if interpretation.get("display_name"):
        return interpretation["display_name"]
    return None


def _resolve_display_name_en(
    *,
    name: str,
    aliases: list[str],
    interpretation: ArtifactInterpretation,
) -> str | None:
    if interpretation.get("standard_name"):
        return interpretation["standard_name"]
    direct_en = _extract_embedded_english_name(name)
    if direct_en:
        return direct_en
    for alias in aliases:
        if _contains_latin(alias) and not _contains_cjk(alias) and not _ACRONYM_PATTERN.fullmatch(alias):
            return alias
    return None


def _resolve_acronym(*, name: str, aliases: list[str]) -> str | None:
    if _ARTIFACT_CODE_PATTERN.fullmatch(name) or _ACRONYM_PATTERN.fullmatch(name):
        return name
    for alias in aliases:
        if _ACRONYM_PATTERN.fullmatch(alias):
            return alias
    return None


def _resolve_evidence_summary_zh(evidence: list[dict]) -> str | None:
    for item in evidence:
        excerpt = str(item.get("excerpt", "")).strip()
        if excerpt and _contains_cjk(excerpt):
            return excerpt[:180]
    return None


def _extract_chinese_display_name(name: str) -> str | None:
    stripped_name = name.strip()
    if _contains_cjk(stripped_name) and not _ARTIFACT_CODE_PATTERN.fullmatch(stripped_name):
        return re.sub(r"\s*[（(][A-Za-z][^）)]*[)）]\s*", "", stripped_name).strip() or stripped_name
    return None


def _extract_embedded_english_name(name: str) -> str | None:
    matched = _PAREN_LATIN_PATTERN.search(name)
    if matched:
        return matched.group(1).strip()
    if _contains_latin(name) and not _contains_cjk(name) and not _ACRONYM_PATTERN.fullmatch(name):
        return name.strip()
    return None


def _contains_cjk(value: str) -> bool:
    return bool(_CJK_PATTERN.search(value))


def _contains_latin(value: str) -> bool:
    return bool(_LATIN_PATTERN.search(value))


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
