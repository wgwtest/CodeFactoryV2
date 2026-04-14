from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

from app.archive_knowledge.service import ITEM_COLLECTIONS
from app.config import settings

REFERENCE_ALIAS_RE = re.compile(
    r"^(?:JP|ADP|ADRP|ATP|FM|AR|TC|AFH|MIL-STD|AJP|APP|DOD|DD)\b",
    re.IGNORECASE,
)
CANONICAL_NOISE_PREFIX_PATTERNS = (
    re.compile(r"^CENTER FOR ARMY LESSONS LEARNED\s+", re.IGNORECASE),
    re.compile(r"^D Code Remarks\.\s*", re.IGNORECASE),
    re.compile(r"^Full Octagon N/A\s+", re.IGNORECASE),
    re.compile(r"^CIVIL AFFAIRS OPERATIONS\s+\d+(?:-\d+)?\.\s*", re.IGNORECASE),
    re.compile(r"^[A-Z]{2,}\s+\d+(?:-\d+)+(?:\.\d+)?\.\s*", re.IGNORECASE),
    re.compile(r"^[A-Za-z][A-Za-z\s/-]{3,}?\s+\d+(?:-\d+)+(?:\.\d+)?\.\s*", re.IGNORECASE),
)
HEADING_RE = re.compile(
    r"^(?:ANNEX|APPENDIX)\b|(?:\bPage\b)|(?:\b5 May 2014\b)|(?:\bAIR FORCE HANDBOOK\b)|(?:\bARMY FIELD MANUALS\b)",
    re.IGNORECASE,
)
ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9/-]{1,19}$")
MIXED_CODE_RE = re.compile(r"(?:[A-Z]?\d+[/-]){2,}|(?:\b[A-Z0-9]{1,6}/){2,}")
MILITARY_UNIT_CODE_RE = re.compile(r"^[A-Z]/\d+-\d+\s+[A-Z][A-Z0-9-]*(?:\s+[A-Z][A-Z0-9-]*)*$")
MILITARY_UNIT_ABBREV_RE = re.compile(
    r"^(?:[A-Z0-9]{1,4}\s+){1,3}(?:CO|BN|BDE|CAV|AV|IN|AR|DET|OPS|TOC)$"
)
SENTENCE_MARKERS = (
    " is ",
    " are ",
    " was ",
    " were ",
    " which ",
    " that ",
    " if ",
    " while ",
    " when ",
    " directly ",
    " assigned ",
    " executed ",
    " developed ",
    " taken ",
    " projected ",
    " supported ",
    " influences ",
    " identify ",
    " identifies ",
    " ensuring ",
    " ensures ",
    " than ",
    " identified ",
    " to ",
)
LOWER_FRAGMENT_PREFIXES = (
    "and ",
    "of ",
    "s ",
)
REJECT_EXACT_PREFIXES = (
    "also called",
    "definitions that",
    "as the key",
    "the examples show",
    "the two key elements",
)
ACTION_STARTERS = {
    "allocate",
    "allocates",
    "calculating",
    "consists",
    "establish",
    "establishing",
    "recommending",
    "notify",
    "identifies",
    "identify",
    "making",
    "ensures",
    "ensure",
    "meets",
    "show",
    "shows",
}
TITLECASE_CONNECTOR_WORDS = {"A", "AN", "AND", "AT", "BY", "FOR", "IN", "OF", "ON", "OR", "THE", "TO"}
LOWERCASE_CONNECTOR_WORDS = {word.casefold() for word in TITLECASE_CONNECTOR_WORDS}
GENERIC_REJECT_EXACT = {
    "assistant chief of staff",
    "civilian",
    "department of defense form",
    "no later than",
    "plan",
    "right or left limit of a unit",
    "small military unit",
}
GENERIC_ALIAS_REJECT_EXACT = {
    "N/A",
    "NONE",
    "OPTIONAL",
    "OPTIONAL FILL",
    "UNSPECIFIED",
}


def _load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_space(value).casefold())


def _title_case_phrase(value: str) -> str:
    words = []
    for word in value.split():
        if word.upper() in TITLECASE_CONNECTOR_WORDS:
            words.append(word.capitalize())
        elif ACRONYM_RE.match(word) and (len(word) <= 5 or any(char.isdigit() or char in "/-" for char in word)):
            words.append(word)
        elif word.upper() in {"G-1", "G-2", "G-3", "G-4", "G-5", "G-6", "G-7", "G-8", "G-9", "S-1", "S-2", "S-3", "S-4", "S-5", "S-6", "S-7", "S-8", "S-9"}:
            words.append(word.upper())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def _filter_aliases(name: str, aliases: list[str]) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        normalized = _normalize_space(alias)
        if not normalized:
            continue
        if normalized.casefold() == name.casefold():
            continue
        if normalized.upper() in GENERIC_ALIAS_REJECT_EXACT:
            continue
        if REFERENCE_ALIAS_RE.search(normalized):
            continue
        if MIXED_CODE_RE.search(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(normalized)
    return filtered


def _strip_simple_prefix(name: str) -> str | None:
    stripped = name
    for prefix in ("The ", "A ", "An ", "and ", "s "):
        if stripped.startswith(prefix):
            candidate = _normalize_space(stripped[len(prefix) :].rstrip("."))
            if not candidate:
                return None
            word_count = len(candidate.split())
            if prefix in {"and ", "s "} and not (
                ACRONYM_RE.match(candidate.replace(",", "").strip())
                or len(candidate.split()) <= 3 and "." not in candidate and "," not in candidate
            ):
                return None
            lowered = f" {candidate.lower()} "
            if any(marker in lowered for marker in SENTENCE_MARKERS):
                return None
            if prefix in {"A ", "An "} and word_count > 4:
                return None
            if lowered.split()[0] in ACTION_STARTERS:
                return None
            return _title_case_phrase(candidate)
    return None


def _strip_noise_prefix(name: str) -> str | None:
    normalized = _normalize_space(name.rstrip("."))
    for pattern in CANONICAL_NOISE_PREFIX_PATTERNS:
        candidate = pattern.sub("", normalized)
        if candidate == normalized:
            continue
        candidate = _normalize_space(candidate.rstrip("."))
        candidate = _strip_simple_prefix(candidate) or _title_case_phrase(candidate)
        if candidate:
            return candidate
    return None


def _is_definition_like(name: str) -> bool:
    normalized = _normalize_space(name)
    if not normalized.startswith(("A ", "An ", "The ")):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", normalized)
    lowercase_words = sum(1 for word in words[1:] if word.islower())
    return len(words) >= 5 and lowercase_words >= 3


def _is_generic_reject(name: str, aliases: list[str]) -> bool:
    normalized = _normalize_space(name.rstrip("."))
    lowered = normalized.casefold()
    if lowered in GENERIC_REJECT_EXACT:
        return True
    if MILITARY_UNIT_CODE_RE.match(normalized):
        return True
    if MILITARY_UNIT_ABBREV_RE.match(normalized):
        return True
    if normalized.isupper() and len(normalized.split()) == 1 and len(normalized) >= 6 and not aliases:
        return True
    return False


def _canonicalize_name(name: str) -> str:
    normalized = _normalize_space(name.rstrip("."))
    return _strip_noise_prefix(normalized) or _strip_simple_prefix(normalized) or normalized


def _lowercase_content_word_count(name: str) -> int:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", _normalize_space(name))
    return sum(1 for word in words if word.islower() and word.casefold() not in LOWERCASE_CONNECTOR_WORDS)


def _is_noise_name(name: str) -> bool:
    normalized = _normalize_space(name)
    lowered = normalized.lower()
    tokens = re.findall(r"[a-z0-9-]+", lowered)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", normalized)
    if not normalized:
        return True
    if any(lowered.startswith(prefix) for prefix in REJECT_EXACT_PREFIXES):
        return True
    if any(lowered.startswith(prefix) for prefix in LOWER_FRAGMENT_PREFIXES):
        return True
    if normalized[0].islower():
        return True
    if "Also called" in normalized or "also called" in normalized:
        return True
    if HEADING_RE.search(normalized):
        return True
    if MIXED_CODE_RE.search(normalized):
        return True
    if "//" in normalized:
        return True
    if MILITARY_UNIT_CODE_RE.match(normalized):
        return True
    if MILITARY_UNIT_ABBREV_RE.match(normalized):
        return True
    if sum(ch.isdigit() for ch in normalized) >= 6 and normalized.count(" ") >= 3:
        return True
    if tokens and tokens[0] in ACTION_STARTERS:
        return True
    if tokens and tokens[0].endswith("ing") and len(tokens) > 2:
        return True
    if len(words) >= 6 and _lowercase_content_word_count(normalized) >= 3:
        return True
    if len(tokens) > 4 and any(marker in f" {lowered} " for marker in SENTENCE_MARKERS):
        return True
    if normalized.endswith(".") and any(marker in f" {lowered} " for marker in SENTENCE_MARKERS):
        return True
    if normalized.startswith(("A ", "An ", "The ")) and any(marker in f" {lowered} " for marker in SENTENCE_MARKERS):
        return True
    if normalized.endswith(".") and len(tokens) > 3:
        return True
    if normalized.isupper() and len(normalized.split()) >= 3:
        return True
    return False


def _decide_status(name: str, category: str | None, document_count: int, aliases: list[str]) -> str:
    if _is_noise_name(name) or _is_generic_reject(name, aliases):
        return "rejected"

    effective_name = _canonicalize_name(name)
    word_count = len(effective_name.split())
    lowered = f" {effective_name.lower()} "
    has_short_alias = any(ACRONYM_RE.match(alias) for alias in aliases)

    if _is_definition_like(effective_name) or any(marker in lowered for marker in SENTENCE_MARKERS):
        return "pending"
    if category in {"organization", "system_or_service"}:
        return "approved"
    if document_count >= 2:
        return "approved"
    if has_short_alias and word_count <= 6:
        return "approved"
    if ACRONYM_RE.match(effective_name) and len(effective_name) >= 3:
        return "approved"
    if 1 <= word_count <= 5 and not effective_name.endswith("."):
        return "approved"
    return "pending"


def _should_reject_duplicate(
    original_name: str,
    effective_name: str,
    aliases: list[str],
    canonical_counts: Counter[str],
    clean_reference_keys: set[str],
) -> bool:
    original_key = _normalize_key(original_name)
    effective_key = _normalize_key(effective_name)
    if original_key != effective_key and canonical_counts.get(effective_key, 0) > 1:
        return True
    if _is_definition_like(original_name) and any(_normalize_key(alias) in clean_reference_keys for alias in aliases):
        return True
    return False


def govern_payload(payload: dict) -> tuple[dict, dict]:
    governed = deepcopy(payload)
    stats = {
        "renamed": 0,
        "aliases_filtered": 0,
        "collections": {},
    }

    for collection_name, _ in ITEM_COLLECTIONS:
        collection = governed.get(collection_name, [])
        status_counter: Counter[str] = Counter()
        prepared_items: list[tuple[dict, str, list[str], str]] = []
        for item in collection:
            original_name = _normalize_space(item["name"])
            aliases = item.get("aliases", [])
            filtered_aliases = _filter_aliases(original_name, aliases)
            stats["aliases_filtered"] += max(0, len(aliases) - len(filtered_aliases))
            effective_name = _canonicalize_name(original_name)
            prepared_items.append((item, original_name, filtered_aliases, effective_name))

        canonical_counts: Counter[str] = Counter()
        clean_reference_keys: set[str] = set()
        for item, _, filtered_aliases, effective_name in prepared_items:
            if _is_noise_name(effective_name) or _is_generic_reject(effective_name, filtered_aliases):
                continue
            canonical_key = _normalize_key(effective_name)
            if canonical_key:
                canonical_counts[canonical_key] += 1
                clean_reference_keys.add(canonical_key)
            for alias in filtered_aliases:
                alias_key = _normalize_key(alias)
                if alias_key:
                    clean_reference_keys.add(alias_key)

        for item, original_name, filtered_aliases, effective_name in prepared_items:
            item["aliases"] = filtered_aliases
            if effective_name != item["name"] and not _is_noise_name(effective_name):
                item["name"] = effective_name
                stats["renamed"] += 1

            if _should_reject_duplicate(
                original_name=original_name,
                effective_name=item["name"],
                aliases=item.get("aliases", []),
                canonical_counts=canonical_counts,
                clean_reference_keys=clean_reference_keys,
            ):
                item["review_status"] = "rejected"
            else:
                item["review_status"] = _decide_status(
                    name=item["name"],
                    category=item.get("category"),
                    document_count=len(item.get("document_ids", [])),
                    aliases=item.get("aliases", []),
                )
            status_counter[item["review_status"]] += 1

        stats["collections"][collection_name] = dict(status_counter)

    governed["summary"] = _rebuild_visible_summary(governed)
    return governed, stats


def _rebuild_visible_summary(payload: dict) -> dict:
    visible_item_ids: set[str] = set()
    visible_document_ids = {document["id"] for document in payload.get("documents", [])}
    summary = {
        "document_count": len(payload.get("documents", [])),
        "entity_count": 0,
        "event_count": 0,
        "process_count": 0,
        "relation_count": 0,
    }

    for collection_name, item_type in ITEM_COLLECTIONS:
        visible_items = [
            item
            for item in payload.get(collection_name, [])
            if item.get("review_status", "pending") != "rejected"
        ]
        visible_item_ids.update(item["id"] for item in visible_items)
        summary_key = {
            "entity": "entity_count",
            "event": "event_count",
            "process": "process_count",
        }[item_type]
        summary[summary_key] = len(visible_items)

    summary["relation_count"] = len(
        [
            relation
            for relation in payload.get("relations", [])
            if relation.get("from") in visible_item_ids.union(visible_document_ids)
            and relation.get("to") in visible_item_ids.union(visible_document_ids)
        ]
    )
    return summary


def resolve_paths(archive_id: str) -> tuple[Path, Path]:
    root = Path(settings.knowledge_output_root)
    base_path = root / f"{archive_id}-knowledge.json"
    curated_path = root / f"{archive_id}-knowledge-curated.json"
    source_path = curated_path if curated_path.exists() else base_path
    if not source_path.exists():
        raise FileNotFoundError(f"未找到知识库产物: {archive_id}")
    return source_path, curated_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a first-pass governance heuristic to an archive knowledge base.")
    parser.add_argument("archive_id", help="Archive id, e.g. MJ-V1")
    parser.add_argument("--write", action="store_true", help="Persist the governed curated payload")
    args = parser.parse_args()

    source_path, curated_path = resolve_paths(args.archive_id)
    payload = _load_payload(source_path)
    governed, stats = govern_payload(payload)

    print(json.dumps({"archive_id": args.archive_id, **stats}, ensure_ascii=False, indent=2))
    if args.write:
        _save_payload(curated_path, governed)
        print(f"WROTE {curated_path}")


if __name__ == "__main__":
    main()
