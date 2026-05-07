from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path

from app.archive_knowledge.document_artifacts import (
    DocumentArtifactRepository,
    aggregate_document_contributions,
    build_document_contribution,
    build_extraction_report_payload,
    build_parsed_documents_payload,
)
from app.archive_knowledge.runtime_snapshot_service import (
    DocumentRuntimeSnapshotService,
)
from app.archive_knowledge.runtime_contract import RuntimeStatus, STAGE_DEFINITION_MAP
from app.archive_knowledge.runtime_parser_execution import (
    parsed_document_from_source_document,
)
from app.archive_knowledge.policy_config import build_policy_run_snapshot
from app.archive_knowledge.rebuild import reconcile_curated_payload
from app.extraction.service import ExtractionService
from app.knowledge_builder import (
    SourceDocument,
    _document_id,
    build_knowledge_index as runtime_build_knowledge_index,
)
from app.parsing.service import ParsingService

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}
FORMAL_EXTRACTION_SKIPPABLE_SUFFIXES = {".xlsx", ".xls"}
build_knowledge_index = runtime_build_knowledge_index
_ORIGINAL_BUILD_KNOWLEDGE_INDEX = runtime_build_knowledge_index
RUNTIME_SLOW_PROFILE_FILENAME = ".cfv2-runtime-slow.json"
RUNTIME_SEQUENTIAL_SLOW_STAGE_IDS = (
    "evidence_constructor",
    "evidence_graph_chunk_layer",
    "evidence_pack",
    "concept_candidate_review",
    "relation_review_family_normalization",
    "definition_summary_conflict_consolidation",
    "canonical_knowledge",
    "quality_policy_evaluation_governance_gate",
    "indexes_snapshots_apis",
)
RUNTIME_SLOW_STAGE_RUNNING_MESSAGES = {
    "evidence_constructor": "Evidence constructor is consolidating parsed segments into traceable candidates.",
    "evidence_graph_chunk_layer": "Evidence graph and chunk layer are linking chunks, candidates, and anchors.",
    "evidence_pack": "Evidence pack is grouping candidate evidence for downstream review.",
    "concept_candidate_review": "Concept candidates are being screened against the active stage policy.",
    "relation_review_family_normalization": "Relations and family groups are being normalized.",
    "definition_summary_conflict_consolidation": "Definitions, summaries, and conflicts are being consolidated.",
    "canonical_knowledge": "Canonical knowledge objects are being materialized.",
    "quality_policy_evaluation_governance_gate": "Quality gate is evaluating policy rules and runtime metrics.",
    "indexes_snapshots_apis": "Publication candidate snapshot and API exposure range are being prepared.",
}


@dataclass(slots=True)
class ArchiveBuildResult:
    archive_id: str
    archive_name: str
    source_dir: Path
    extract_root: Path
    json_path: Path
    curated_path: Path
    markdown_path: Path
    parsed_documents_path: Path
    extraction_report_path: Path
    summary: dict


@dataclass(slots=True)
class DiscoveredDocument:
    path: str
    title: str
    file_type: str
    source_archive: str
    source_file_path: str
    source_digest: str


@dataclass(slots=True)
class RuntimeAcceptanceSlowProfile:
    enabled: bool = False
    stage_delay_seconds: float = 0.0
    chunk_delay_seconds: float = 0.0
    document_delay_seconds: float = 0.0

    def sleep_stage(self) -> None:
        if self.enabled and self.stage_delay_seconds > 0:
            time.sleep(self.stage_delay_seconds)

    def sleep_chunk(self) -> None:
        if self.enabled and self.chunk_delay_seconds > 0:
            time.sleep(self.chunk_delay_seconds)

    def sleep_document(self) -> None:
        if self.enabled and self.document_delay_seconds > 0:
            time.sleep(self.document_delay_seconds)


def load_runtime_acceptance_slow_profile(source_dir: Path) -> RuntimeAcceptanceSlowProfile:
    profile_path = source_dir / RUNTIME_SLOW_PROFILE_FILENAME
    if not profile_path.exists():
        return RuntimeAcceptanceSlowProfile()

    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RuntimeAcceptanceSlowProfile()

    if not payload.get("enabled", False):
        return RuntimeAcceptanceSlowProfile()

    return RuntimeAcceptanceSlowProfile(
        enabled=True,
        stage_delay_seconds=_delay_seconds_from_ms(payload.get("stage_delay_ms")),
        chunk_delay_seconds=_delay_seconds_from_ms(payload.get("chunk_delay_ms")),
        document_delay_seconds=_delay_seconds_from_ms(payload.get("document_delay_ms")),
    )


def _delay_seconds_from_ms(value: object) -> float:
    try:
        milliseconds = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if milliseconds <= 0:
        return 0.0
    return milliseconds / 1000.0


def _runtime_stage_label(stage_id: str) -> str:
    definition = STAGE_DEFINITION_MAP.get(stage_id)
    return definition.label if definition is not None else stage_id


def _runtime_stage_status_from_snapshot(snapshot: dict | None) -> str:
    status = (snapshot or {}).get("status")
    if isinstance(status, str) and status:
        return status
    return RuntimeStatus.COMPLETED.value


def _persist_slow_runtime_stage_snapshot(
    *,
    runtime_snapshot_service: DocumentRuntimeSnapshotService,
    archive_id: str,
    contribution: dict,
    parsed_document,
    stage_id: str,
) -> str | None:
    runtime_trace = ((contribution or {}).get("extraction") or {}).get("runtime_trace", {})
    if stage_id == "evidence_constructor":
        if parsed_document is None:
            return None
        return runtime_snapshot_service.persist_evidence_constructor_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
            runtime_trace=runtime_trace.get(stage_id),
        )
    if stage_id == "evidence_graph_chunk_layer":
        if parsed_document is None:
            return None
        return runtime_snapshot_service.persist_evidence_graph_chunk_layer_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
            runtime_trace=runtime_trace.get(stage_id),
        )
    if stage_id == "evidence_pack":
        return runtime_snapshot_service.persist_evidence_pack_snapshot(archive_id, contribution=contribution)
    if stage_id == "concept_candidate_review":
        return runtime_snapshot_service.persist_concept_candidate_review_snapshot(archive_id, contribution=contribution)
    if stage_id == "relation_review_family_normalization":
        return runtime_snapshot_service.persist_relation_review_family_normalization_snapshot(
            archive_id,
            contribution=contribution,
        )
    if stage_id == "definition_summary_conflict_consolidation":
        return runtime_snapshot_service.persist_definition_summary_conflict_consolidation_snapshot(
            archive_id,
            contribution=contribution,
        )
    if stage_id == "canonical_knowledge":
        return runtime_snapshot_service.persist_canonical_knowledge_snapshot(archive_id, contribution=contribution)
    if stage_id == "quality_policy_evaluation_governance_gate":
        return runtime_snapshot_service.persist_quality_gate_snapshot(
            archive_id,
            contribution=contribution,
            runtime_trace=runtime_trace.get(stage_id),
        )
    if stage_id == "indexes_snapshots_apis":
        return runtime_snapshot_service.persist_indexes_snapshots_apis_snapshot(
            archive_id,
            contribution=contribution,
        )
    return None


def build_archive_knowledge(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    extract_root: Path,
    output_root: Path,
    formal_extraction_mode: bool = False,
    policy_snapshot: dict | None = None,
) -> ArchiveBuildResult:
    source_dir = source_dir.expanduser().resolve()
    extract_root = extract_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if formal_extraction_mode and policy_snapshot is None:
        policy_snapshot = build_policy_run_snapshot(
            archive_id,
            None,
            captured_at=datetime.now(UTC).isoformat(),
        )

    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"源目录不存在或不可读取: {source_dir}")

    extract_archives(source_dir, extract_root)
    document_roots = resolve_document_roots(source_dir, extract_root)
    warnings: list[dict] = []

    if build_knowledge_index is not _ORIGINAL_BUILD_KNOWLEDGE_INDEX:
        documents = collect_documents(
            document_roots,
            formal_extraction_mode=formal_extraction_mode,
            warnings_collector=warnings,
        )
        if not documents:
            raise ValueError(f"目录中未发现可解析文档: {source_dir}")
        extraction_diagnostics: list[dict] = []
        knowledge = build_knowledge_index(
            documents,
            extraction_service=ExtractionService(formal_extraction_mode=formal_extraction_mode),
            diagnostics_collector=extraction_diagnostics,
        )
        if formal_extraction_mode:
            _validate_formal_extraction_run(documents, extraction_diagnostics)
        return persist_legacy_archive_outputs(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            extract_root=extract_root,
            output_root=output_root,
            knowledge=knowledge,
            documents=documents,
            extraction_diagnostics=extraction_diagnostics,
            formal_extraction_mode=formal_extraction_mode,
            warnings=warnings,
        )

    if formal_extraction_mode:
        documents = discover_documents(
            document_roots,
            formal_extraction_mode=True,
            warnings_collector=warnings,
        )
        if not documents:
            raise ValueError(f"目录中未发现可解析文档: {source_dir}")
        extraction_service = ExtractionService(formal_extraction_mode=True)
        artifact_repository = DocumentArtifactRepository(output_root)
        contributions = _build_formal_archive_contributions(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            documents=documents,
            extraction_service=extraction_service,
            artifact_repository=artifact_repository,
            warnings=warnings,
            policy_snapshot=policy_snapshot,
        )
        extraction_diagnostics = _build_extraction_diagnostics(contributions)
        build_state = artifact_repository.load_build_state(archive_id) or {}
        _validate_formal_extraction_run(
            documents,
            extraction_diagnostics,
            skipped_document_ids=build_state.get("skipped_document_ids", []),
        )
        artifact_repository.prune(
            archive_id,
            keep_document_ids={contribution["document"]["id"] for contribution in contributions},
        )
        contributions = artifact_repository.load_contributions(archive_id)
        knowledge = aggregate_document_contributions(
            artifact_repository.load_contributions(archive_id, included_only=True)
        )
        build_state = artifact_repository.load_build_state(archive_id) or {}
        artifact_repository.save_build_state(
            archive_id,
            _build_archive_state(
                archive_id=archive_id,
                archive_name=archive_name,
                documents=documents,
                status="completed",
                completed_document_ids=[contribution["document"]["id"] for contribution in contributions],
                pending_document_ids=[],
                failed_document_id=None,
                failed_message=None,
                current_document_id=None,
                current_document_title=None,
                current_document_path=None,
                started_at=build_state.get("started_at"),
                current_chunk=None,
                skipped_document_ids=build_state.get("skipped_document_ids", []),
                warnings=warnings,
                policy_snapshot=build_state.get("policy_snapshot") or policy_snapshot,
            ),
        )
    else:
        documents = collect_documents(document_roots, formal_extraction_mode=False)
        if not documents:
            raise ValueError(f"目录中未发现可解析文档: {source_dir}")
        extraction_service = ExtractionService(formal_extraction_mode=False)
        contributions = [build_document_contribution(document, extraction_service) for document in documents]
        extraction_diagnostics = _build_extraction_diagnostics(contributions)
        DocumentArtifactRepository(output_root).replace_all(archive_id, contributions)
        knowledge = aggregate_document_contributions(contributions)
    return persist_archive_outputs(
        archive_id=archive_id,
        archive_name=archive_name,
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        knowledge=knowledge,
        contributions=contributions,
        formal_extraction_mode=formal_extraction_mode,
        warnings=warnings,
    )


def resolve_document_roots(source_dir: Path, extract_root: Path) -> list[Path]:
    roots: list[Path] = []

    if _contains_supported_documents(source_dir):
        roots.append(source_dir)
    if extract_root.exists() and _contains_supported_documents(extract_root):
        roots.append(extract_root)

    return roots or [source_dir]


def extract_archives(source_dir: Path, extract_root: Path) -> None:
    extract_root.mkdir(parents=True, exist_ok=True)
    for archive in sorted(source_dir.glob("*.rar")):
        target = extract_root / archive.stem
        if target.exists() and any(target.rglob("*")):
            continue
        target.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["unar", "-force-overwrite", "-output-directory", str(target), str(archive)],
                check=False,
            )
        except FileNotFoundError:
            break


def discover_documents(
    document_roots: Path | list[Path],
    *,
    formal_extraction_mode: bool = False,
    warnings_collector: list[dict] | None = None,
) -> list[DiscoveredDocument]:
    roots = [document_roots] if isinstance(document_roots, Path) else list(document_roots)
    documents_by_digest: dict[str, tuple[int, DiscoveredDocument]] = {}

    for priority, root in enumerate(roots):
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("~$"):
                continue

            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                continue
            if formal_extraction_mode and suffix in FORMAL_EXTRACTION_SKIPPABLE_SUFFIXES:
                if warnings_collector is not None:
                    warnings_collector.append(_build_formal_extraction_warning(path))
                continue

            digest = _file_digest(path)
            relative_path = path.relative_to(root)
            source_archive = relative_path.parts[0] if len(relative_path.parts) > 1 else root.name
            document = DiscoveredDocument(
                path=relative_path.as_posix(),
                title=path.stem,
                file_type=suffix.lstrip("."),
                source_archive=source_archive,
                source_file_path=str(path),
                source_digest=digest,
            )
            existing = documents_by_digest.get(digest)
            if existing is None or priority < existing[0]:
                documents_by_digest[digest] = (priority, document)

    return sorted((item[1] for item in documents_by_digest.values()), key=lambda document: document.path)


def collect_documents(
    document_roots: Path | list[Path],
    *,
    formal_extraction_mode: bool = False,
    warnings_collector: list[dict] | None = None,
) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for document in discover_documents(
        document_roots,
        formal_extraction_mode=formal_extraction_mode,
        warnings_collector=warnings_collector,
    ):
        try:
            documents.append(
                parse_discovered_document(document, formal_extraction_mode=formal_extraction_mode)
            )
        except Exception as exc:
            if formal_extraction_mode:
                raise
            print(f"SKIP unreadable file: {document.source_file_path} ({exc})")
    return documents


def parse_discovered_document(
    document: DiscoveredDocument,
    *,
    formal_extraction_mode: bool = False,
) -> SourceDocument:
    file_path = Path(document.source_file_path)
    parsing_service = ParsingService(formal_extraction_mode=formal_extraction_mode)
    try:
        parsed = parsing_service.parse_file(file_path)
    except Exception as exc:
        if formal_extraction_mode:
            raise ValueError(f"正式知识库抽取失败：{file_path} ({exc})") from exc
        raise

    if (
        formal_extraction_mode
        and document.file_type in {"pdf", "doc", "docx"}
        and parsed.parser_name not in {"docling_pdf", "docling_docx"}
    ):
        raise ValueError(f"正式知识库抽取要求使用 Docling 解析，但文件实际使用了解析器 {parsed.parser_name}：{file_path}")

    text = "\n".join(segment.content for segment in parsed.segments)
    if not text.strip():
        if formal_extraction_mode:
            raise ValueError(f"正式知识库抽取失败：Docling 未能从文件中解析出有效文本：{file_path}")
        raise ValueError(f"文档解析后无有效文本：{file_path}")

    return SourceDocument(
        path=document.path,
        title=document.title,
        file_type=document.file_type,
        source_archive=document.source_archive,
        text=text,
        parser_name=parsed.parser_name,
        segment_count=len(parsed.segments),
        segments=parsed.segments,
        source_file_path=document.source_file_path,
        source_digest=document.source_digest,
    )


def _validate_formal_extraction_run(
    documents: list[SourceDocument] | list[DiscoveredDocument],
    extraction_diagnostics: list[dict],
    *,
    skipped_document_ids: list[str] | None = None,
) -> None:
    skipped_document_id_set = set(skipped_document_ids or [])
    expected_documents = [
        document for document in documents if _document_id(document.path) not in skipped_document_id_set
    ]
    if len(extraction_diagnostics) != len(expected_documents):
        raise ValueError("正式知识库抽取失败：抽取执行报告与文档数量不一致")

    for document, diagnostic in zip(expected_documents, extraction_diagnostics, strict=True):
        if document.file_type in {"pdf", "doc", "docx"} and diagnostic.get("parser_name") not in {"docling_pdf", "docling_docx"}:
            raise ValueError(
                f"正式知识库抽取要求使用 Docling 解析，但执行报告记录的解析器不符合要求：{document.path}"
            )
        if not diagnostic.get("llm_enrichment_used"):
            raise ValueError(f"正式知识库抽取要求使用结构化大模型抽取，但文档未启用大模型增强：{document.path}")
        if not diagnostic.get("llm_provider") or not diagnostic.get("llm_model"):
            raise ValueError(f"正式知识库抽取要求记录实际使用的大模型信息，但当前文档缺少记录：{document.path}")


def _build_formal_extraction_warning(path: Path) -> dict:
    return {
        "code": "unsupported_spreadsheet_skipped",
        "severity": "warning",
        "file_path": str(path),
        "file_type": path.suffix.lower().lstrip("."),
        "message": f"正式知识库抽取已跳过表格文件（当前未接入 Docling 表格链路）：{path}",
    }


def _should_skip_formal_pdf_failure(document: DiscoveredDocument, exc: Exception) -> bool:
    if document.file_type != "pdf":
        return False
    message = str(exc)
    return "Docling" in message or "PDF 使用 Docling 解析" in message or "禁止 PDF 解析降级到非 Docling" in message


def _build_formal_pdf_skip_warning(document: DiscoveredDocument, exc: Exception) -> dict:
    return {
        "code": "docling_pdf_skipped",
        "severity": "warning",
        "file_path": document.source_file_path,
        "file_type": document.file_type,
        "message": f"正式知识库抽取已跳过 PDF 文件（Docling 解析失败）：{document.source_file_path}",
        "reason": str(exc),
    }


def _iter_exception_chain(exc: Exception):
    current: Exception | None = exc
    while current is not None:
        yield current
        if current.__cause__ is not None and isinstance(current.__cause__, Exception):
            current = current.__cause__
            continue
        if current.__context__ is not None and isinstance(current.__context__, Exception):
            current = current.__context__
            continue
        break


def _is_formal_doc_conversion_failure(exc: Exception) -> bool:
    chain = list(_iter_exception_chain(exc))
    if any(isinstance(item, FileNotFoundError) for item in chain):
        return True
    if any(isinstance(item, subprocess.CalledProcessError) for item in chain):
        return True

    messages = " | ".join(str(item) for item in chain)
    return (
        "soffice" in messages
        or "LibreOffice" in messages
        or "No such file or directory" in messages
        or "系统找不到指定的文件" in messages
    )


def _should_skip_formal_docling_failure(document: DiscoveredDocument, exc: Exception) -> bool:
    if document.file_type not in {"pdf", "doc", "docx"}:
        return False

    if document.file_type == "doc" and _is_formal_doc_conversion_failure(exc):
        return True

    message = str(exc)
    if "Docling" not in message and "MsWordDocumentBackend could not load document" not in message:
        return False

    if document.file_type == "pdf":
        return _should_skip_formal_pdf_failure(document, exc)

    return (
        "DOC/DOCX 浣跨敤 Docling 瑙ｆ瀽" in message
        or "绂佹 DOC/DOCX 瑙ｆ瀽闄嶇骇鍒伴潪 Docling" in message
        or "MsWordDocumentBackend could not load document" in message
        or "Docling" in message
    )


def _build_formal_docling_skip_warning(document: DiscoveredDocument, exc: Exception) -> dict:
    if document.file_type == "pdf":
        return _build_formal_pdf_skip_warning(document, exc)

    if document.file_type == "doc" and _is_formal_doc_conversion_failure(exc):
        return {
            "code": "doc_conversion_skipped",
            "severity": "warning",
            "file_path": document.source_file_path,
            "file_type": document.file_type,
            "message": f"正式知识库抽取已跳过 DOC 文件（DOC 转 DOCX 失败）: {document.source_file_path}",
            "reason": str(exc),
        }

    file_type = document.file_type.upper()
    code = "docling_doc_skipped" if document.file_type == "doc" else "docling_docx_skipped"
    return {
        "code": code,
        "severity": "warning",
        "file_path": document.source_file_path,
        "file_type": document.file_type,
        "message": f"姝ｅ紡鐭ヨ瘑搴撴娊鍙栧凡璺宠繃 {file_type} 鏂囦欢锛圖ocling 瑙ｆ瀽澶辫触锛夛細{document.source_file_path}",
        "reason": str(exc),
    }


def extract_text(path: Path) -> str:
    parsed = ParsingService().parse_file(path)
    return "\n".join(segment.content for segment in parsed.segments)


def render_summary(knowledge: dict, *, archive_name: str) -> str:
    lines = [
        f"# {archive_name} 知识构建结果",
        "",
        "## 摘要",
        f"- 文档数：{knowledge['summary']['document_count']}",
        f"- 实体数：{knowledge['summary']['entity_count']}",
        f"- 事件数：{knowledge['summary']['event_count']}",
        f"- 流程数：{knowledge['summary']['process_count']}",
        "",
        "## 关键事件",
    ]
    for item in knowledge["events"][:10]:
        lines.append(f"- {item['name']}：关联文档 {len(item['document_ids'])} 份")

    lines.extend(["", "## 关键流程"])
    for item in knowledge["processes"][:15]:
        lines.append(f"- {item['name']}：关联文档 {len(item['document_ids'])} 份")

    lines.extend(["", "## 关键实体"])
    for item in knowledge["entities"][:30]:
        aliases = f"（别名: {', '.join(item['aliases'])}）" if item["aliases"] else ""
        lines.append(f"- {item['name']}{aliases}：{item['category']}，关联文档 {len(item['document_ids'])} 份")

    return "\n".join(lines) + "\n"


def _contains_supported_documents(root: Path) -> bool:
    return any(
        path.is_file() and not path.name.startswith("~$") and path.suffix.lower() in SUPPORTED_SUFFIXES
        for path in root.rglob("*")
    )


def _file_digest(path: Path) -> str:
    hasher = md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_formal_archive_contributions(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    documents: list[DiscoveredDocument],
    extraction_service: ExtractionService,
    artifact_repository: DocumentArtifactRepository,
    warnings: list[dict] | None = None,
    policy_snapshot: dict | None = None,
) -> list[dict]:
    started_at = (policy_snapshot or {}).get("captured_at") or datetime.now(UTC).isoformat()
    completed_document_ids: list[str] = []
    skipped_document_ids: list[str] = []
    pending_document_ids = [_document_id(document.path) for document in documents]
    contributions: list[dict] = []
    runtime_snapshot_service = DocumentRuntimeSnapshotService(artifact_repository.output_root)
    slow_profile = load_runtime_acceptance_slow_profile(source_dir)

    artifact_repository.save_build_state(
        archive_id,
        _build_archive_state(
            archive_id=archive_id,
            archive_name=archive_name,
            documents=documents,
            status="running",
            completed_document_ids=completed_document_ids,
            pending_document_ids=pending_document_ids,
            failed_document_id=None,
            failed_message=None,
            current_document_id=None,
            current_document_title=None,
            current_document_path=None,
            started_at=started_at,
            current_chunk=None,
            skipped_document_ids=skipped_document_ids,
            warnings=warnings,
            policy_snapshot=policy_snapshot,
        ),
    )

    for document in documents:
        document_id = _document_id(document.path)
        manifest_document = artifact_repository.get_document_source_info(archive_id, document_id)
        included_in_archive = manifest_document.get("included_in_archive", True) if manifest_document else True
        current_chunk: dict | None = None
        current_stage_id: str | None = None
        current_stage_label: str | None = None
        current_stage_status: str | None = None
        current_stage_message: str | None = None
        parsed_document = None
        runtime_parsed_document = None

        runtime_snapshot_service.persist_asset_intake_snapshot(
            archive_id,
            archive_name=archive_name,
            document_id=document_id,
            document_title=document.title,
            document_path=document.path,
            source_dir=source_dir,
            source_file_path=document.source_file_path,
            file_type=document.file_type,
            source_archive=document.source_archive,
            source_digest=document.source_digest,
            included_in_archive=included_in_archive,
            mode="archive_extract",
            intake_timestamp=started_at,
        )

        def save_running_state(
            *,
            current_chunk_override: dict | None,
            current_stage_id_override: str | None = None,
            current_stage_label_override: str | None = None,
            current_stage_status_override: str | None = None,
            current_stage_message_override: str | None = None,
        ) -> None:
            nonlocal current_stage_id, current_stage_label, current_stage_status, current_stage_message
            if current_stage_id_override is not None:
                current_stage_id = current_stage_id_override
            if current_stage_label_override is not None:
                current_stage_label = current_stage_label_override
            if current_stage_status_override is not None:
                current_stage_status = current_stage_status_override
            if current_stage_message_override is not None:
                current_stage_message = current_stage_message_override
            artifact_repository.save_build_state(
                archive_id,
                _build_archive_state(
                    archive_id=archive_id,
                    archive_name=archive_name,
                    documents=documents,
                    status="running",
                    completed_document_ids=completed_document_ids,
                    pending_document_ids=pending_document_ids,
                    failed_document_id=None,
                    failed_message=None,
                    current_document_id=document_id,
                    current_document_title=document.title,
                    current_document_path=document.path,
                    started_at=started_at,
                    current_chunk=current_chunk_override,
                    current_stage_id=current_stage_id,
                    current_stage_label=current_stage_label,
                    current_stage_status=current_stage_status,
                    current_stage_message=current_stage_message,
                    skipped_document_ids=skipped_document_ids,
                    warnings=warnings,
                    policy_snapshot=policy_snapshot,
                ),
            )

        save_running_state(
            current_chunk_override=None,
            current_stage_id_override="asset_intake",
            current_stage_label_override="Asset Intake",
            current_stage_status_override="completed",
            current_stage_message_override="Source document has entered archive extraction.",
        )
        slow_profile.sleep_stage()

        def handle_chunk_progress(event: dict) -> None:
            nonlocal current_chunk
            event_type = event.get("event")
            if event_type == "stage_transition":
                runtime_trace = event.get("runtime_trace")
                stage_id = event.get("stage_id")
                stage_label = event.get("stage_label")
                stage_status = event.get("status")
                stage_message = event.get("message")
                save_running_state(
                    current_chunk_override=current_chunk,
                    current_stage_id_override=stage_id,
                    current_stage_label_override=stage_label,
                    current_stage_status_override=stage_status,
                    current_stage_message_override=stage_message,
                )
                if runtime_parsed_document is not None and isinstance(runtime_trace, dict):
                    partial_contribution = {
                        "document": {
                            "id": document_id,
                            "title": document.title,
                            "path": document.path,
                            "file_type": document.file_type,
                            "source_archive": document.source_archive,
                            "source_file_path": document.source_file_path,
                            "source_digest": document.source_digest,
                            "character_count": len((parsed_document.text if parsed_document else "") or ""),
                            "parser_name": getattr(runtime_parsed_document, "parser_name", None),
                            "segment_count": len(getattr(runtime_parsed_document, "segments", []) or []),
                        },
                        "entities": [],
                        "events": [],
                        "processes": [],
                        "relations": [],
                        "extraction": {"runtime_trace": {stage_id: runtime_trace}},
                    }
                    if stage_id == "evidence_constructor":
                        runtime_snapshot_service.persist_evidence_constructor_snapshot(
                            archive_id,
                            contribution=partial_contribution,
                            parsed_document=runtime_parsed_document,
                            runtime_trace=runtime_trace,
                            status_override=RuntimeStatus.RUNNING,
                        )
                    elif stage_id == "evidence_graph_chunk_layer":
                        runtime_snapshot_service.persist_evidence_graph_chunk_layer_snapshot(
                            archive_id,
                            contribution=partial_contribution,
                            parsed_document=runtime_parsed_document,
                            runtime_trace=runtime_trace,
                            status_override=RuntimeStatus.RUNNING,
                        )
                slow_profile.sleep_stage()
                return
            if event_type in {None, "chunk_progress"}:
                current_chunk = {
                    "chunk_id": event.get("chunk_id"),
                    "position": event.get("chunk_position"),
                    "total": event.get("chunk_total"),
                    "heading": event.get("chunk_heading"),
                    "char_count": event.get("chunk_char_count"),
                    "segment_count": event.get("chunk_segment_count"),
                    "retry_depth": event.get("retry_depth", 0),
                }
                save_running_state(current_chunk_override=current_chunk)
                slow_profile.sleep_chunk()

        extraction_service.progress_callback = handle_chunk_progress

        try:
            if artifact_repository.has_reusable_artifact(
                archive_id,
                document_id,
                source_digest=document.source_digest,
            ):
                contribution = artifact_repository.load_document_contribution(archive_id, document_id)
                if contribution is None:
                    raise FileNotFoundError(f"文档级正式产物缺失: {document_id}")
            else:
                save_running_state(
                    current_chunk_override=None,
                    current_stage_id_override="parser_execution",
                    current_stage_label_override="Parser Execution",
                    current_stage_status_override="running",
                    current_stage_message_override="Parser is reading the source document and materializing parsed segments.",
                )
                slow_profile.sleep_stage()
                parsed_document = parse_discovered_document(document, formal_extraction_mode=True)
                runtime_parsed_document = parsed_document_from_source_document(
                    parser_name=parsed_document.parser_name,
                    segment_count=parsed_document.segment_count,
                    segments=parsed_document.segments,
                    source_file_path=parsed_document.source_file_path,
                    source_digest=parsed_document.source_digest,
                )
                runtime_snapshot_service.persist_parser_router_snapshot(
                    archive_id,
                    document_id=document_id,
                    document_title=parsed_document.title,
                    file_type=parsed_document.file_type,
                    source_file_path=parsed_document.source_file_path,
                    parser_name=parsed_document.parser_name,
                    parser_version="runtime",
                )
                save_running_state(
                    current_chunk_override=None,
                    current_stage_id_override="parser_router",
                    current_stage_label_override="Parser Router",
                    current_stage_status_override="completed",
                    current_stage_message_override=f"Parser router selected {parsed_document.parser_name}.",
                )
                slow_profile.sleep_stage()
                if runtime_parsed_document is not None:
                    runtime_snapshot_service.persist_parser_execution_snapshot(
                        archive_id,
                        document_id=document_id,
                        document_title=parsed_document.title,
                        file_type=parsed_document.file_type,
                        parsed_document=runtime_parsed_document,
                    )
                    save_running_state(
                        current_chunk_override=None,
                        current_stage_id_override="parser_execution",
                        current_stage_label_override="Parser Execution",
                        current_stage_status_override="completed",
                        current_stage_message_override=(
                            f"Parser execution produced {parsed_document.segment_count} parsed segments."
                        ),
                    )
                    slow_profile.sleep_stage()
                    runtime_snapshot_service.persist_unified_document_object_snapshot(
                        archive_id,
                        document_id=document_id,
                        document_title=parsed_document.title,
                        file_type=parsed_document.file_type,
                        parsed_document=runtime_parsed_document,
                    )
                    save_running_state(
                        current_chunk_override=None,
                        current_stage_id_override="unified_document_object",
                        current_stage_label_override="Unified Document Object",
                        current_stage_status_override="completed",
                        current_stage_message_override="Unified document object snapshot has been materialized.",
                    )
                    slow_profile.sleep_stage()
                contribution = build_document_contribution(
                    parsed_document,
                    extraction_service,
                    document_id=document_id,
                    policy_snapshot=policy_snapshot,
                )
                artifact_repository.upsert(
                    archive_id,
                    contribution,
                    included_in_archive=included_in_archive,
                )
        except Exception as exc:
            if _should_skip_formal_docling_failure(document, exc):
                warning = _build_formal_docling_skip_warning(document, exc)
                if warnings is not None:
                    warnings.append(warning)
                if document_id not in skipped_document_ids:
                    skipped_document_ids.append(document_id)
                pending_document_ids = [pending_id for pending_id in pending_document_ids if pending_id != document_id]
                artifact_repository.save_build_state(
                    archive_id,
                    _build_archive_state(
                        archive_id=archive_id,
                        archive_name=archive_name,
                        documents=documents,
                        status="running",
                        completed_document_ids=completed_document_ids,
                        pending_document_ids=pending_document_ids,
                        failed_document_id=None,
                        failed_message=None,
                        current_document_id=None,
                        current_document_title=None,
                        current_document_path=None,
                        started_at=started_at,
                        current_chunk=None,
                        skipped_document_ids=skipped_document_ids,
                        warnings=warnings,
                        policy_snapshot=policy_snapshot,
                    ),
                )
                continue
            artifact_repository.save_build_state(
                archive_id,
                _build_archive_state(
                    archive_id=archive_id,
                    archive_name=archive_name,
                    documents=documents,
                    status="failed",
                    completed_document_ids=completed_document_ids,
                    pending_document_ids=[
                        pending_id for pending_id in pending_document_ids if pending_id not in completed_document_ids
                    ],
                    failed_document_id=document_id,
                    failed_message=str(exc),
                    current_document_id=document_id,
                    current_document_title=document.title,
                    current_document_path=document.path,
                    started_at=started_at,
                    current_chunk=current_chunk,
                    current_stage_id=current_stage_id,
                    current_stage_label=current_stage_label,
                    current_stage_status=current_stage_status,
                    current_stage_message=current_stage_message,
                    skipped_document_ids=skipped_document_ids,
                    warnings=warnings,
                    policy_snapshot=policy_snapshot,
                ),
            )
            raise
        finally:
            extraction_service.progress_callback = None

        runtime_document_source = {
            "document_id": document_id,
            "title": document.title,
            "path": document.path,
            "file_type": document.file_type,
            "source_archive": document.source_archive,
            "source_file_path": document.source_file_path,
            "source_digest": document.source_digest,
            "included_in_archive": included_in_archive,
            "parser_name": contribution.get("document", {}).get("parser_name"),
            "segment_count": contribution.get("document", {}).get("segment_count", 0),
        }
        if slow_profile.enabled:
            resolved_runtime_parsed_document = (
                runtime_parsed_document
                or runtime_snapshot_service.load_or_derive_parsed_document(runtime_document_source)
            )
            for stage_id in RUNTIME_SEQUENTIAL_SLOW_STAGE_IDS:
                save_running_state(
                    current_chunk_override=current_chunk,
                    current_stage_id_override=stage_id,
                    current_stage_label_override=_runtime_stage_label(stage_id),
                    current_stage_status_override=RuntimeStatus.RUNNING.value,
                    current_stage_message_override=RUNTIME_SLOW_STAGE_RUNNING_MESSAGES.get(
                        stage_id,
                        f"{_runtime_stage_label(stage_id)} is materializing.",
                    ),
                )
                slow_profile.sleep_stage()
                persisted_stage_id = _persist_slow_runtime_stage_snapshot(
                    runtime_snapshot_service=runtime_snapshot_service,
                    archive_id=archive_id,
                    contribution=contribution,
                    parsed_document=resolved_runtime_parsed_document,
                    stage_id=stage_id,
                )
                snapshot = (
                    runtime_snapshot_service.runtime_repository.load_stage_snapshot(
                        archive_id,
                        document_id,
                        persisted_stage_id,
                    )
                    if persisted_stage_id
                    else None
                )
                save_running_state(
                    current_chunk_override=current_chunk,
                    current_stage_id_override=stage_id,
                    current_stage_label_override=_runtime_stage_label(stage_id),
                    current_stage_status_override=_runtime_stage_status_from_snapshot(snapshot),
                    current_stage_message_override=f"{_runtime_stage_label(stage_id)} snapshot has been materialized.",
                )
                slow_profile.sleep_stage()
        else:
            save_running_state(
                current_chunk_override=current_chunk,
                current_stage_id_override="quality_policy_evaluation_governance_gate",
                current_stage_label_override="Quality Policy Evaluation / Governance Gate",
                current_stage_status_override="running",
                current_stage_message_override="Quality gate is materializing from the completed document contribution.",
            )
            runtime_snapshot_service.persist_document_runtime_snapshots(
                archive_id=archive_id,
                archive_name=archive_name,
                source_dir=source_dir,
                document_source=runtime_document_source,
                contribution=contribution,
                mode="archive_extract",
                intake_timestamp=started_at,
                parsed_document=runtime_parsed_document,
                included_in_archive=included_in_archive,
            )

        contributions.append(contribution)
        if document_id not in completed_document_ids:
            completed_document_ids.append(document_id)
        pending_document_ids = [pending_id for pending_id in pending_document_ids if pending_id != document_id]
        artifact_repository.save_build_state(
            archive_id,
            _build_archive_state(
                archive_id=archive_id,
                archive_name=archive_name,
                documents=documents,
                status="running",
                completed_document_ids=completed_document_ids,
                pending_document_ids=pending_document_ids,
                failed_document_id=None,
                failed_message=None,
                current_document_id=None,
                current_document_title=None,
                current_document_path=None,
                started_at=started_at,
                current_chunk=None,
                skipped_document_ids=skipped_document_ids,
                warnings=warnings,
                policy_snapshot=policy_snapshot,
            ),
        )
        slow_profile.sleep_document()

    return contributions


def _build_archive_state(
    *,
    archive_id: str,
    archive_name: str,
    documents: list[DiscoveredDocument],
    status: str,
    completed_document_ids: list[str],
    pending_document_ids: list[str],
    failed_document_id: str | None,
    failed_message: str | None,
    current_document_id: str | None,
    current_document_title: str | None,
    current_document_path: str | None,
    started_at: str | None,
    current_chunk: dict | None,
    current_stage_id: str | None = None,
    current_stage_label: str | None = None,
    current_stage_status: str | None = None,
    current_stage_message: str | None = None,
    skipped_document_ids: list[str] | None = None,
    warnings: list[dict] | None = None,
    policy_snapshot: dict | None = None,
) -> dict:
    completed_set = set(completed_document_ids)
    pending_set = set(pending_document_ids)
    skipped_set = set(skipped_document_ids or [])
    normalized_warnings = list(warnings or [])
    return {
        "archive_id": archive_id,
        "archive_name": archive_name,
        "mode": "formal",
        "status": status,
        "started_at": started_at,
        "expected_document_count": len(documents),
        "completed_document_ids": completed_document_ids,
        "skipped_document_ids": list(skipped_document_ids or []),
        "pending_document_ids": pending_document_ids,
        "failed_document_id": failed_document_id,
        "failed_message": failed_message,
        "current_document_id": current_document_id,
        "current_document_title": current_document_title,
        "current_document_path": current_document_path,
        "current_chunk": current_chunk,
        "current_stage_id": current_stage_id,
        "current_stage_label": current_stage_label,
        "current_stage_status": current_stage_status,
        "current_stage_message": current_stage_message,
        "policy_snapshot": policy_snapshot,
        "warning_count": len(normalized_warnings),
        "warnings": normalized_warnings,
        "documents": [
            {
                "document_id": _document_id(document.path),
                "path": document.path,
                "title": document.title,
                "file_type": document.file_type,
                "source_archive": document.source_archive,
                "source_file_path": document.source_file_path,
                "source_digest": document.source_digest,
                "state": (
                    "failed"
                    if _document_id(document.path) == failed_document_id
                    else "running"
                    if _document_id(document.path) == current_document_id and status == "running"
                    else "completed"
                    if _document_id(document.path) in completed_set
                    else "skipped"
                    if _document_id(document.path) in skipped_set
                    else "pending"
                    if _document_id(document.path) in pending_set
                    else "pending"
                ),
            }
            for document in documents
        ],
    }


def persist_archive_outputs(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    extract_root: Path,
    output_root: Path,
    knowledge: dict,
    contributions: list[dict],
    formal_extraction_mode: bool,
    warnings: list[dict] | None = None,
) -> ArchiveBuildResult:
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"{archive_id}-knowledge.json"
    curated_path = output_root / f"{archive_id}-knowledge-curated.json"
    markdown_path = output_root / f"{archive_id}-knowledge.md"
    parsed_documents_path = output_root / f"{archive_id}-parsed-documents.json"
    extraction_report_path = output_root / f"{archive_id}-extraction-report.json"

    json_path.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
    curated_path.write_text(
        json.dumps(
            reconcile_curated_payload(
                knowledge,
                _load_json(curated_path),
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(render_summary(knowledge, archive_name=archive_name), encoding="utf-8")
    parsed_documents_path.write_text(
        json.dumps(build_parsed_documents_payload(contributions), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    extraction_report_path.write_text(
        json.dumps(
            build_extraction_report_payload(
                archive_id=archive_id,
                archive_name=archive_name,
                strict_mode=formal_extraction_mode,
                contributions=contributions,
                summary=knowledge["summary"],
                warnings=warnings,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return ArchiveBuildResult(
        archive_id=archive_id,
        archive_name=archive_name,
        source_dir=source_dir,
        extract_root=extract_root,
        json_path=json_path,
        curated_path=curated_path,
        markdown_path=markdown_path,
        parsed_documents_path=parsed_documents_path,
        extraction_report_path=extraction_report_path,
        summary=knowledge["summary"],
    )


def _build_extraction_diagnostics(contributions: list[dict]) -> list[dict]:
    diagnostics = []
    for contribution in sorted(contributions, key=lambda item: item["document"]["path"]):
        document = contribution["document"]
        extraction = contribution.get("extraction", {})
        diagnostics.append(
            {
                "document_id": document["id"],
                "title": document["title"],
                "file_path": document["path"],
                "file_type": document["file_type"],
                "parser_name": document.get("parser_name"),
                "segment_count": document.get("segment_count", 0),
                **extraction,
            }
        )
    return diagnostics


def persist_legacy_archive_outputs(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    extract_root: Path,
    output_root: Path,
    knowledge: dict,
    documents: list[SourceDocument],
    extraction_diagnostics: list[dict],
    formal_extraction_mode: bool,
    warnings: list[dict] | None = None,
) -> ArchiveBuildResult:
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"{archive_id}-knowledge.json"
    curated_path = output_root / f"{archive_id}-knowledge-curated.json"
    markdown_path = output_root / f"{archive_id}-knowledge.md"
    parsed_documents_path = output_root / f"{archive_id}-parsed-documents.json"
    extraction_report_path = output_root / f"{archive_id}-extraction-report.json"

    json_path.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
    curated_path.write_text(
        json.dumps(
            reconcile_curated_payload(
                knowledge,
                _load_json(curated_path),
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(render_summary(knowledge, archive_name=archive_name), encoding="utf-8")
    parsed_documents_path.write_text(
        json.dumps(
            [
                {
                    "path": document.path,
                    "title": document.title,
                    "file_type": document.file_type,
                    "source_archive": document.source_archive,
                    "parser_name": document.parser_name,
                    "segment_count": document.segment_count,
                    "character_count": len(document.text),
                }
                for document in documents
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    extraction_report_path.write_text(
        json.dumps(
            {
                "archive_id": archive_id,
                "archive_name": archive_name,
                "strict_mode": formal_extraction_mode,
                "summary": knowledge["summary"],
                "warning_count": len(warnings or []),
                "warnings": list(warnings or []),
                "documents": extraction_diagnostics,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return ArchiveBuildResult(
        archive_id=archive_id,
        archive_name=archive_name,
        source_dir=source_dir,
        extract_root=extract_root,
        json_path=json_path,
        curated_path=curated_path,
        markdown_path=markdown_path,
        parsed_documents_path=parsed_documents_path,
        extraction_report_path=extraction_report_path,
        summary=knowledge["summary"],
    )
