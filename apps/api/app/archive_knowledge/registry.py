from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class ArchiveRegistryService:
    def __init__(
        self,
        output_root: str | Path,
        *,
        default_archive_id: str,
        default_archive_name: str,
        default_source_dir: str | Path,
        default_extract_root: str | Path,
        extract_root_parent: str | Path | None = None,
    ) -> None:
        self.output_root = Path(output_root)
        self.registry_path = self.output_root / "archive-registry.json"
        self.default_archive_id = default_archive_id
        self.default_archive_name = default_archive_name
        self.default_source_dir = Path(default_source_dir)
        self.default_extract_root = Path(default_extract_root)
        self.extract_root_parent = Path(extract_root_parent) if extract_root_parent else self.output_root.parent / "source_archives"

    def list_archives(self) -> list[dict]:
        state = self._load_state()
        return [self._serialize_archive(entry, state["active_archive_id"]) for entry in state["archives"]]

    def get_archive(self, archive_id: str) -> dict | None:
        state = self._load_state()
        entry = self._find_archive(state, archive_id)
        if entry is None:
            return None
        return self._serialize_archive(entry, state["active_archive_id"])

    def create_archive(
        self,
        *,
        archive_id: str,
        name: str,
        source_dir: str | Path,
        extract_root: str | Path | None = None,
    ) -> dict:
        normalized_archive_id = archive_id.strip()
        normalized_name = name.strip()
        if not normalized_archive_id:
            raise ValueError("知识库标识不能为空")
        if not normalized_name:
            raise ValueError("知识库名称不能为空")

        source_path = self._normalize_directory(source_dir, field_name="源目录")
        extract_path = (
            self._normalize_optional_path(extract_root)
            if extract_root
            else (self.extract_root_parent / normalized_archive_id).resolve()
        )

        state = self._load_state()
        if self._find_archive(state, normalized_archive_id) is not None:
            raise ValueError(f"知识库标识已存在: {normalized_archive_id}")

        now = self._now()
        state["archives"].append(
            {
                "archive_id": normalized_archive_id,
                "name": normalized_name,
                "source_dir": str(source_path),
                "extract_root": str(extract_path),
                "status": "empty",
                "last_built_at": None,
                "last_error": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        self._save_state(state)
        return self.get_archive(normalized_archive_id) or {}

    def activate_archive(self, archive_id: str) -> dict | None:
        state = self._load_state()
        entry = self._find_archive(state, archive_id)
        if entry is None:
            return None
        state["active_archive_id"] = archive_id
        entry["updated_at"] = self._now()
        self._save_state(state)
        return self._serialize_archive(entry, archive_id)

    def mark_extracting(self, archive_id: str) -> dict | None:
        return self._update_archive(
            archive_id,
            {
                "status": "extracting",
                "last_error": None,
            },
        )

    def mark_extracted(self, archive_id: str) -> dict | None:
        return self._update_archive(
            archive_id,
            {
                "status": "ready",
                "last_built_at": self._now(),
                "last_error": None,
            },
        )

    def mark_error(self, archive_id: str, *, message: str) -> dict | None:
        return self._update_archive(
            archive_id,
            {
                "status": "error",
                "last_error": message,
            },
        )

    def _update_archive(self, archive_id: str, changes: dict) -> dict | None:
        state = self._load_state()
        entry = self._find_archive(state, archive_id)
        if entry is None:
            return None
        entry.update(changes)
        entry["updated_at"] = self._now()
        self._save_state(state)
        return self._serialize_archive(entry, state["active_archive_id"])

    def _load_state(self) -> dict:
        state = self._load_or_create_registry()
        archives = state.get("archives", [])
        archives.sort(key=lambda item: item["created_at"])
        return {
            "active_archive_id": state.get("active_archive_id") or self.default_archive_id,
            "archives": archives,
        }

    def _load_or_create_registry(self) -> dict:
        self.output_root.mkdir(parents=True, exist_ok=True)
        if self.registry_path.exists():
            state = json.loads(self.registry_path.read_text(encoding="utf-8"))
        else:
            state = {"active_archive_id": self.default_archive_id, "archives": []}

        if not any(item.get("archive_id") == self.default_archive_id for item in state.get("archives", [])):
            now = self._now()
            state.setdefault("archives", []).insert(
                0,
                {
                    "archive_id": self.default_archive_id,
                    "name": self.default_archive_name,
                    "source_dir": str(self.default_source_dir.expanduser().resolve()),
                    "extract_root": str(self.default_extract_root.expanduser().resolve()),
                    "status": "ready" if self._resolve_base_path(self.default_archive_id).exists() else "empty",
                    "last_built_at": None,
                    "last_error": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        if not state.get("active_archive_id"):
            state["active_archive_id"] = self.default_archive_id
        self._save_state(state)
        return state

    def _save_state(self, state: dict) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _serialize_archive(self, entry: dict, active_archive_id: str) -> dict:
        archive_id = entry["archive_id"]
        base_exists = self._resolve_base_path(archive_id).exists()
        curated_exists = self._resolve_curated_path(archive_id).exists()
        publication_exists = self._resolve_publication_path(archive_id).exists()
        summary = self._load_summary(archive_id)

        status = entry.get("status", "empty")
        if status not in {"error", "extracting"}:
            status = "ready" if summary else "empty"

        return {
            "archive_id": archive_id,
            "name": entry["name"],
            "source_dir": entry["source_dir"],
            "extract_root": entry["extract_root"],
            "is_active": archive_id == active_archive_id,
            "status": status,
            "last_built_at": entry.get("last_built_at"),
            "last_error": entry.get("last_error"),
            "summary": summary,
            "artifacts": {
                "base_exists": base_exists,
                "curated_exists": curated_exists,
                "publication_exists": publication_exists,
            },
        }

    def _load_summary(self, archive_id: str) -> dict | None:
        read_path = self._resolve_curated_path(archive_id)
        if not read_path.exists():
            read_path = self._resolve_base_path(archive_id)
        if not read_path.exists():
            return None
        payload = json.loads(read_path.read_text(encoding="utf-8"))
        return payload.get("summary")

    def _normalize_directory(self, value: str | Path, *, field_name: str) -> Path:
        path = Path(value).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError(f"{field_name}不存在或不是目录: {path}")
        return path

    def _normalize_optional_path(self, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    def _find_archive(self, state: dict, archive_id: str) -> dict | None:
        for entry in state.get("archives", []):
            if entry.get("archive_id") == archive_id:
                return entry
        return None

    def _resolve_base_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-knowledge.json"

    def _resolve_curated_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-knowledge-curated.json"

    def _resolve_publication_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-publication.json"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
