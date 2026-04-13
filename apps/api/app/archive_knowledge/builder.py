from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path

from app.archive_knowledge.rebuild import reconcile_curated_payload
from app.extraction.service import ExtractionService
from app.knowledge_builder import SourceDocument, build_knowledge_index
from app.parsing.service import ParsingService

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}


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
    summary: dict


def build_archive_knowledge(
    *,
    archive_id: str,
    archive_name: str,
    source_dir: Path,
    extract_root: Path,
    output_root: Path,
) -> ArchiveBuildResult:
    source_dir = source_dir.expanduser().resolve()
    extract_root = extract_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"源目录不存在或不可读取: {source_dir}")

    extract_archives(source_dir, extract_root)
    document_roots = resolve_document_roots(source_dir, extract_root)
    documents = collect_documents(document_roots)
    if not documents:
        raise ValueError(f"目录中未发现可解析文档: {source_dir}")

    knowledge = build_knowledge_index(documents, extraction_service=ExtractionService())

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"{archive_id}-knowledge.json"
    curated_path = output_root / f"{archive_id}-knowledge-curated.json"
    markdown_path = output_root / f"{archive_id}-knowledge.md"
    parsed_documents_path = output_root / f"{archive_id}-parsed-documents.json"
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

    return ArchiveBuildResult(
        archive_id=archive_id,
        archive_name=archive_name,
        source_dir=source_dir,
        extract_root=extract_root,
        json_path=json_path,
        curated_path=curated_path,
        markdown_path=markdown_path,
        parsed_documents_path=parsed_documents_path,
        summary=knowledge["summary"],
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


def collect_documents(document_roots: Path | list[Path]) -> list[SourceDocument]:
    roots = [document_roots] if isinstance(document_roots, Path) else list(document_roots)
    documents_by_digest: dict[str, tuple[int, SourceDocument]] = {}
    parsing_service = ParsingService()

    for priority, root in enumerate(roots):
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("~$"):
                continue

            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                continue

            try:
                parsed = parsing_service.parse_file(path)
            except Exception as exc:
                print(f"SKIP unreadable file: {path} ({exc})")
                continue

            text = "\n".join(segment.content for segment in parsed.segments)
            if not text.strip():
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
            )

            digest = _file_digest(path)
            existing = documents_by_digest.get(digest)
            if existing is None or priority < existing[0]:
                documents_by_digest[digest] = (priority, document)

    return sorted((item[1] for item in documents_by_digest.values()), key=lambda document: document.path)


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
