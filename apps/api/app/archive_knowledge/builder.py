from __future__ import annotations

import json
import subprocess
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
from app.archive_knowledge.rebuild import reconcile_curated_payload
from app.extraction.service import ExtractionService
from app.knowledge_builder import SourceDocument, build_knowledge_index as runtime_build_knowledge_index
from app.parsing.service import ParsingService

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}
build_knowledge_index = runtime_build_knowledge_index
_ORIGINAL_BUILD_KNOWLEDGE_INDEX = runtime_build_knowledge_index


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


def build_archive_knowledge(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    extract_root: Path,
    output_root: Path,
    formal_extraction_mode: bool = False,
) -> ArchiveBuildResult:
    source_dir = source_dir.expanduser().resolve()
    extract_root = extract_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"源目录不存在或不可读取: {source_dir}")

    extract_archives(source_dir, extract_root)
    document_roots = resolve_document_roots(source_dir, extract_root)
    documents = collect_documents(document_roots, formal_extraction_mode=formal_extraction_mode)
    if not documents:
        raise ValueError(f"目录中未发现可解析文档: {source_dir}")

    if build_knowledge_index is not _ORIGINAL_BUILD_KNOWLEDGE_INDEX:
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
        )

    extraction_service = ExtractionService(formal_extraction_mode=formal_extraction_mode)
    contributions = [build_document_contribution(document, extraction_service) for document in documents]
    extraction_diagnostics = _build_extraction_diagnostics(contributions)
    if formal_extraction_mode:
        _validate_formal_extraction_run(documents, extraction_diagnostics)

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


def collect_documents(document_roots: Path | list[Path], *, formal_extraction_mode: bool = False) -> list[SourceDocument]:
    roots = [document_roots] if isinstance(document_roots, Path) else list(document_roots)
    documents_by_digest: dict[str, tuple[int, SourceDocument]] = {}
    parsing_service = ParsingService(formal_extraction_mode=formal_extraction_mode)

    for priority, root in enumerate(roots):
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("~$"):
                continue

            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                continue
            if formal_extraction_mode and suffix in {".xlsx", ".xls"}:
                raise ValueError(f"正式知识库抽取当前不允许使用非 Docling 的表格解析链路：{path}")

            try:
                parsed = parsing_service.parse_file(path)
            except Exception as exc:
                if formal_extraction_mode:
                    raise ValueError(f"正式知识库抽取失败：{path} ({exc})") from exc
                print(f"SKIP unreadable file: {path} ({exc})")
                continue

            if formal_extraction_mode and suffix in {".pdf", ".doc", ".docx"} and parsed.parser_name not in {"docling_pdf", "docling_docx"}:
                raise ValueError(f"正式知识库抽取要求使用 Docling 解析，但文件实际使用了解析器 {parsed.parser_name}：{path}")

            text = "\n".join(segment.content for segment in parsed.segments)
            if not text.strip():
                if formal_extraction_mode:
                    raise ValueError(f"正式知识库抽取失败：Docling 未能从文件中解析出有效文本：{path}")
                continue

            relative_path = path.relative_to(root)
            source_archive = relative_path.parts[0] if len(relative_path.parts) > 1 else root.name
            document = SourceDocument(
                path=str(relative_path),
                title=path.stem,
                file_type=suffix.lstrip("."),
                source_archive=source_archive,
                text=text,
                parser_name=parsed.parser_name,
                segment_count=len(parsed.segments),
                segments=parsed.segments,
                source_file_path=str(path),
            )

            digest = _file_digest(path)
            existing = documents_by_digest.get(digest)
            if existing is None or priority < existing[0]:
                documents_by_digest[digest] = (priority, document)

    return sorted((item[1] for item in documents_by_digest.values()), key=lambda document: document.path)


def _validate_formal_extraction_run(documents: list[SourceDocument], extraction_diagnostics: list[dict]) -> None:
    if len(extraction_diagnostics) != len(documents):
        raise ValueError("正式知识库抽取失败：抽取执行报告与文档数量不一致")

    for document, diagnostic in zip(documents, extraction_diagnostics, strict=True):
        if document.file_type in {"pdf", "doc", "docx"} and diagnostic.get("parser_name") not in {"docling_pdf", "docling_docx"}:
            raise ValueError(
                f"正式知识库抽取要求使用 Docling 解析，但执行报告记录的解析器不符合要求：{document.path}"
            )
        if not diagnostic.get("llm_enrichment_used"):
            raise ValueError(f"正式知识库抽取要求使用结构化大模型抽取，但文档未启用大模型增强：{document.path}")
        if not diagnostic.get("llm_provider") or not diagnostic.get("llm_model"):
            raise ValueError(f"正式知识库抽取要求记录实际使用的大模型信息，但当前文档缺少记录：{document.path}")


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
