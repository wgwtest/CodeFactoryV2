from __future__ import annotations

import re
from copy import deepcopy

from app.archive_knowledge.service import ITEM_COLLECTIONS


EDITABLE_FIELDS = ("name", "category", "aliases", "review_status")


def reconcile_curated_payload(base_payload: dict, previous_curated_payload: dict | None) -> dict:
    reconciled = deepcopy(base_payload)
    previous_curated_payload = previous_curated_payload or {}

    for collection_name, _ in ITEM_COLLECTIONS:
        previous_items_by_id = {
            item["id"]: item
            for item in previous_curated_payload.get(collection_name, [])
        }
        previous_items = list(previous_items_by_id.values())
        for item in reconciled.get(collection_name, []):
            previous_item = previous_items_by_id.get(item["id"]) or _match_previous_item(item, previous_items)
            if previous_item is None:
                item["review_status"] = "pending"
                continue
            for field_name in EDITABLE_FIELDS:
                if field_name in previous_item:
                    item[field_name] = deepcopy(previous_item[field_name])
            item.setdefault("review_status", "pending")

    return reconciled


def _match_previous_item(item: dict, previous_items: list[dict]) -> dict | None:
    current_tokens = _identity_tokens(item)
    if not current_tokens:
        return None

    matches = [candidate for candidate in previous_items if current_tokens.intersection(_identity_tokens(candidate))]
    if len(matches) != 1:
        return None
    return matches[0]


def _identity_tokens(item: dict) -> set[str]:
    tokens = {_slug(item.get("name", ""))}
    tokens.update(_slug(alias) for alias in item.get("aliases", []))
    tokens.discard("")
    return tokens


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")
