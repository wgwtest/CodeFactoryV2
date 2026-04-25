from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DocumentRuntimeRepository:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def save_stage_snapshot(
        self,
        archive_id: str,
        document_id: str,
        stage_id: str,
        snapshot: dict[str, Any],
    ) -> None:
        path = self._resolve_stage_snapshot_path(archive_id, document_id, stage_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_stage_snapshot(
        self,
        archive_id: str,
        document_id: str,
        stage_id: str,
    ) -> dict[str, Any] | None:
        path = self._resolve_stage_snapshot_path(archive_id, document_id, stage_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete_stage_snapshot(
        self,
        archive_id: str,
        document_id: str,
        stage_id: str,
    ) -> None:
        self._resolve_stage_snapshot_path(archive_id, document_id, stage_id).unlink(missing_ok=True)

    def list_stage_snapshot_ids(
        self,
        archive_id: str,
        document_id: str,
    ) -> list[str]:
        root = self.output_root / f"{archive_id}-document-runtime" / document_id
        if not root.exists():
            return []
        return sorted(path.stem for path in root.glob("*.json"))

    def _resolve_stage_snapshot_path(
        self,
        archive_id: str,
        document_id: str,
        stage_id: str,
    ) -> Path:
        return self.output_root / f"{archive_id}-document-runtime" / document_id / f"{stage_id}.json"
