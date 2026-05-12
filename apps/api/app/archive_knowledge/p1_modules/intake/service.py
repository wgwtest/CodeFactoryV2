from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.builder import discover_documents
from app.archive_knowledge.contracts import P1ResponseEnvelope
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.knowledge_builder import _document_id


P1IntakeParseStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class P1IntakeDocument(BaseModel):
    document_id: str
    title: str
    file_name: str
    file_type: str
    source_path: str
    parse_status: P1IntakeParseStatus
    parse_error: str | None = None
    segment_count: int = 0
    anchor_count: int = 0
    can_enter_runtime: bool = False


class P1IntakeSummary(BaseModel):
    document_count: int = 0
    parsed_completed_count: int = 0
    parsed_failed_count: int = 0
    pending_count: int = 0
    can_enter_runtime_count: int = 0
    blocked_count: int = 0


class P1IntakeSnapshot(BaseModel):
    archive_id: str
    document_set_id: str
    source_dir: str
    policy_package_version_id: str | None = None
    documents: list[P1IntakeDocument] = Field(default_factory=list)
    summary: P1IntakeSummary = Field(default_factory=P1IntakeSummary)
    preflight_issues: list[str] = Field(default_factory=list)


class P1IntakeService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.artifacts = DocumentArtifactRepository(self.output_root)

    def build_envelope(
        self,
        archive: dict[str, Any],
        *,
        policy_package_version_id: str | None = None,
    ) -> P1ResponseEnvelope[P1IntakeSnapshot]:
        snapshot = self.build_snapshot(
            archive,
            policy_package_version_id=policy_package_version_id,
        )
        return P1ResponseEnvelope[P1IntakeSnapshot](
            contract_version="p1.intake.r1",
            source_kind="live",
            generated_at=datetime.now(UTC).isoformat(),
            data=snapshot,
            warnings=snapshot.preflight_issues,
        )

    def build_snapshot(
        self,
        archive: dict[str, Any],
        *,
        policy_package_version_id: str | None = None,
    ) -> P1IntakeSnapshot:
        archive_id = str(archive["archive_id"])
        source_dir = Path(str(archive.get("source_dir") or "")).expanduser()
        build_state = self.artifacts.load_build_state(archive_id) or archive.get("build_state") or {}
        document_set_id = str(build_state.get("document_set_id") or f"{archive_id}:document-set")
        manifest_documents = self.artifacts.list_documents(archive_id)

        warnings: list[str] = []
        scanned_documents = self._scan_source_documents(source_dir, warnings)
        documents_by_id: dict[str, dict[str, Any]] = {}

        for scanned in scanned_documents:
            documents_by_id[scanned["document_id"]] = scanned

        for manifest_document in manifest_documents:
            document_id = str(manifest_document.get("document_id") or _document_id(str(manifest_document["path"])))
            documents_by_id[document_id] = self._merge_document(
                documents_by_id.get(document_id),
                self._manifest_document_to_row(
                    archive=archive,
                    source_dir=source_dir,
                    document=manifest_document,
                    build_state=build_state,
                ),
            )

        for build_document in build_state.get("documents", []):
            document_id = str(build_document.get("document_id") or _document_id(str(build_document["path"])))
            documents_by_id[document_id] = self._merge_document(
                documents_by_id.get(document_id),
                self._build_state_document_to_row(
                    archive=archive,
                    source_dir=source_dir,
                    document=build_document,
                    build_state=build_state,
                ),
            )

        documents = [
            self._finalize_document(row, archive=archive, build_state=build_state)
            for row in sorted(documents_by_id.values(), key=lambda item: (item["file_name"], item["document_id"]))
        ]
        if not documents:
            warnings.append("当前 source_dir 未发现可接入的 DOCX/DOC/PDF/XLS/XLSX 文档。")

        return P1IntakeSnapshot(
            archive_id=archive_id,
            document_set_id=document_set_id,
            source_dir=str(source_dir),
            policy_package_version_id=policy_package_version_id,
            documents=documents,
            summary=self._build_summary(documents),
            preflight_issues=self._build_preflight_issues(documents, warnings),
        )

    def _scan_source_documents(self, source_dir: Path, warnings: list[str]) -> list[dict[str, Any]]:
        if not source_dir.exists() or not source_dir.is_dir():
            warnings.append(f"资料源目录不存在或不可读取: {source_dir}")
            return []

        rows: list[dict[str, Any]] = []
        for document in discover_documents(source_dir):
            document_id = _document_id(document.path)
            rows.append(
                {
                    "document_id": document_id,
                    "title": document.title,
                    "file_name": Path(document.path).name,
                    "file_type": document.file_type.lower(),
                    "source_path": document.source_file_path,
                    "parse_status": "pending",
                    "parse_error": "尚未完成解析；请先启动资料解析/抽取运行。",
                    "segment_count": 0,
                    "anchor_count": 0,
                    "can_enter_runtime": False,
                }
            )
        return rows

    def _manifest_document_to_row(
        self,
        *,
        archive: dict[str, Any],
        source_dir: Path,
        document: dict[str, Any],
        build_state: dict[str, Any],
    ) -> dict[str, Any]:
        document_id = str(document.get("document_id") or _document_id(str(document["path"])))
        source_path = str(document.get("source_file_path") or (source_dir / str(document["path"])).resolve())
        segment_count = int(document.get("segment_count") or 0)
        anchor_count = self._count_document_anchors(str(archive["archive_id"]), document_id)
        parse_status = self._resolve_status(document_id, document.get("included_in_archive", True), build_state, "completed")

        return {
            "document_id": document_id,
            "title": str(document.get("title") or Path(source_path).stem),
            "file_name": Path(str(document.get("path") or source_path)).name,
            "file_type": str(document.get("file_type") or Path(source_path).suffix.lstrip(".")).lower(),
            "source_path": source_path,
            "parse_status": parse_status,
            "parse_error": self._resolve_parse_error(
                parse_status=parse_status,
                segment_count=segment_count,
                archive=archive,
                build_state=build_state,
            ),
            "segment_count": segment_count,
            "anchor_count": anchor_count,
            "can_enter_runtime": parse_status == "completed" and segment_count > 0,
        }

    def _build_state_document_to_row(
        self,
        *,
        archive: dict[str, Any],
        source_dir: Path,
        document: dict[str, Any],
        build_state: dict[str, Any],
    ) -> dict[str, Any]:
        document_id = str(document.get("document_id") or _document_id(str(document["path"])))
        source_path = str(document.get("source_file_path") or (source_dir / str(document["path"])).resolve())
        parse_status = self._normalize_status(str(document.get("state") or "pending"))
        return {
            "document_id": document_id,
            "title": str(document.get("title") or Path(source_path).stem),
            "file_name": Path(str(document.get("path") or source_path)).name,
            "file_type": str(document.get("file_type") or Path(source_path).suffix.lstrip(".")).lower(),
            "source_path": source_path,
            "parse_status": parse_status,
            "parse_error": self._resolve_parse_error(
                parse_status=parse_status,
                segment_count=int(document.get("segment_count") or 0),
                archive=archive,
                build_state=build_state,
            ),
            "segment_count": int(document.get("segment_count") or 0),
            "anchor_count": 0,
            "can_enter_runtime": False,
        }

    @staticmethod
    def _merge_document(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
        if existing is None:
            return incoming

        merged = {**existing, **incoming}
        if existing.get("parse_status") == "completed" and incoming.get("parse_status") == "pending":
            merged["parse_status"] = existing["parse_status"]
            merged["parse_error"] = existing.get("parse_error")
            merged["segment_count"] = existing.get("segment_count", 0)
            merged["anchor_count"] = existing.get("anchor_count", 0)
            merged["can_enter_runtime"] = existing.get("can_enter_runtime", False)
        if (
            incoming.get("parse_status") == "completed"
            and int(incoming.get("segment_count") or 0) <= 0
            and int(existing.get("segment_count") or 0) > 0
        ):
            merged["segment_count"] = existing.get("segment_count", 0)
            merged["anchor_count"] = existing.get("anchor_count", 0)
            merged["parse_error"] = existing.get("parse_error")
            merged["can_enter_runtime"] = existing.get("can_enter_runtime", False)
        if incoming.get("parse_status") == "completed":
            merged["can_enter_runtime"] = int(merged.get("segment_count") or 0) > 0
        return merged

    def _finalize_document(
        self,
        row: dict[str, Any],
        *,
        archive: dict[str, Any],
        build_state: dict[str, Any],
    ) -> P1IntakeDocument:
        parse_status = self._normalize_status(str(row.get("parse_status") or "pending"))
        segment_count = int(row.get("segment_count") or 0)
        parse_error = row.get("parse_error") or self._resolve_parse_error(
            parse_status=parse_status,
            segment_count=segment_count,
            archive=archive,
            build_state=build_state,
        )
        can_enter_runtime = parse_status == "completed" and segment_count > 0 and not parse_error
        return P1IntakeDocument(
            document_id=str(row["document_id"]),
            title=str(row["title"]),
            file_name=str(row["file_name"]),
            file_type=str(row["file_type"]).lower(),
            source_path=str(row["source_path"]),
            parse_status=parse_status,
            parse_error=parse_error,
            segment_count=segment_count,
            anchor_count=int(row.get("anchor_count") or 0),
            can_enter_runtime=can_enter_runtime,
        )

    @staticmethod
    def _resolve_status(
        document_id: str,
        included_in_archive: bool,
        build_state: dict[str, Any],
        fallback: P1IntakeParseStatus,
    ) -> P1IntakeParseStatus:
        if not included_in_archive:
            return "skipped"
        for build_document in build_state.get("documents", []):
            if build_document.get("document_id") == document_id:
                return P1IntakeService._normalize_status(str(build_document.get("state") or fallback))
        if build_state.get("failed_document_id") == document_id:
            return "failed"
        return fallback

    @staticmethod
    def _normalize_status(value: str) -> P1IntakeParseStatus:
        if value in {"pending", "running", "completed", "failed", "skipped"}:
            return value  # type: ignore[return-value]
        return "pending"

    @staticmethod
    def _resolve_parse_error(
        *,
        parse_status: P1IntakeParseStatus,
        segment_count: int,
        archive: dict[str, Any],
        build_state: dict[str, Any],
    ) -> str | None:
        if parse_status == "failed":
            return str(build_state.get("failed_message") or archive.get("last_error") or "解析失败，需修复源文件后重新运行。")
        if parse_status == "pending":
            if archive.get("status") == "error" and archive.get("last_error"):
                return str(archive["last_error"])
            return "尚未完成解析；请先启动资料解析/抽取运行。"
        if parse_status == "running":
            return str(build_state.get("current_stage_message") or "解析任务正在运行，完成前不可进入抽取运行。")
        if parse_status == "skipped":
            return "该文档未纳入当前知识库集合。"
        if segment_count <= 0:
            return "解析完成但未记录有效 segment_count，暂不可进入抽取运行。"
        return None

    def _count_document_anchors(self, archive_id: str, document_id: str) -> int:
        try:
            contribution = self.artifacts.load_document_contribution(archive_id, document_id)
        except (FileNotFoundError, ValueError, KeyError):
            return 0
        if contribution is None:
            return 0

        anchors: set[tuple[str, str]] = set()
        for collection_name in ("entities", "events", "processes"):
            for item in contribution.get(collection_name, []):
                for evidence in item.get("evidence", []):
                    excerpt = str(evidence.get("excerpt") or "").strip()
                    if excerpt:
                        anchors.add((str(evidence.get("document_id") or document_id), excerpt))
        return len(anchors)

    @staticmethod
    def _build_summary(documents: list[P1IntakeDocument]) -> P1IntakeSummary:
        return P1IntakeSummary(
            document_count=len(documents),
            parsed_completed_count=sum(1 for document in documents if document.parse_status == "completed"),
            parsed_failed_count=sum(1 for document in documents if document.parse_status == "failed"),
            pending_count=sum(1 for document in documents if document.parse_status in {"pending", "running"}),
            can_enter_runtime_count=sum(1 for document in documents if document.can_enter_runtime),
            blocked_count=sum(1 for document in documents if not document.can_enter_runtime),
        )

    @staticmethod
    def _build_preflight_issues(documents: list[P1IntakeDocument], warnings: list[str]) -> list[str]:
        issues = list(dict.fromkeys(warnings))
        blocked = [document for document in documents if not document.can_enter_runtime]
        failed = [document for document in documents if document.parse_status == "failed"]
        pending = [document for document in documents if document.parse_status in {"pending", "running"}]
        if failed:
            issues.append(f"存在 {len(failed)} 个解析失败文档，需修复后重新运行。")
        if pending:
            issues.append(f"存在 {len(pending)} 个尚未完成解析的文档，暂不可进入抽取运行。")
        if blocked and not failed and not pending:
            issues.append(f"存在 {len(blocked)} 个文档缺少有效结构化解析结果。")
        return issues
