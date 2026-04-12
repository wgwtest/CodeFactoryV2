from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class PublishedKnowledgeRepository(Protocol):
    def load_latest(self, archive_id: str) -> tuple[dict | None, dict | None]:
        ...

    def get_publication_overview(self, archive_id: str, *, working_summary: dict) -> dict:
        ...

    def publish(self, archive_id: str, *, payload: dict, version_label: str, publisher: str) -> dict:
        ...


class JsonPublishedKnowledgeRepository:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def load_latest(self, archive_id: str) -> tuple[dict | None, dict | None]:
        manifest = self._load_manifest(archive_id)
        current_version = manifest.get("current_version")
        if current_version is None:
            return None, None

        snapshot_path = self._resolve_snapshot_path(archive_id, current_version["version_label"])
        if not snapshot_path.exists():
            return None, current_version

        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return payload, current_version

    def get_publication_overview(self, archive_id: str, *, working_summary: dict) -> dict:
        manifest = self._load_manifest(archive_id)
        return {
            "archive_id": archive_id,
            "current_version": manifest.get("current_version"),
            "versions": manifest.get("versions", []),
            "working_summary": working_summary,
        }

    def publish(self, archive_id: str, *, payload: dict, version_label: str, publisher: str) -> dict:
        self.output_root.mkdir(parents=True, exist_ok=True)
        manifest = self._load_manifest(archive_id)

        published_at = datetime.now(UTC).isoformat()
        entry = {
          "version_label": version_label,
          "publisher": publisher,
          "published_at": published_at,
          "summary": payload["summary"],
        }
        snapshot_payload = {
            **payload,
            "publication": entry,
        }

        self._resolve_snapshot_path(archive_id, version_label).write_text(
            json.dumps(snapshot_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        previous_versions = [
            version
            for version in manifest.get("versions", [])
            if version["version_label"] != version_label
        ]
        manifest["current_version"] = entry
        manifest["versions"] = [entry, *previous_versions]
        self._resolve_manifest_path(archive_id).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return entry

    def _load_manifest(self, archive_id: str) -> dict:
        manifest_path = self._resolve_manifest_path(archive_id)
        if not manifest_path.exists():
            return {
                "archive_id": archive_id,
                "current_version": None,
                "versions": [],
            }
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _resolve_manifest_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-publication.json"

    def _resolve_snapshot_path(self, archive_id: str, version_label: str) -> Path:
        safe_version = re.sub(r"[^a-zA-Z0-9._-]+", "-", version_label).strip("-") or "snapshot"
        return self.output_root / f"{archive_id}-published-{safe_version}.json"
