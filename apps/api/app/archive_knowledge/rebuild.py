from __future__ import annotations

from copy import deepcopy

from app.archive_knowledge.service import ITEM_COLLECTIONS


EDITABLE_FIELDS = ("name", "category", "aliases", "review_status")


def reconcile_curated_payload(base_payload: dict, previous_curated_payload: dict | None) -> dict:
    reconciled = deepcopy(base_payload)
    previous_curated_payload = previous_curated_payload or {}

    for collection_name, _ in ITEM_COLLECTIONS:
        previous_items = {
            item["id"]: item
            for item in previous_curated_payload.get(collection_name, [])
        }
        for item in reconciled.get(collection_name, []):
            previous_item = previous_items.get(item["id"])
            if previous_item is None:
                item["review_status"] = "pending"
                continue
            for field_name in EDITABLE_FIELDS:
                if field_name in previous_item:
                    item[field_name] = deepcopy(previous_item[field_name])
            item.setdefault("review_status", "pending")

    return reconciled
