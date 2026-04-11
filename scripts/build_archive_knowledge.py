\
from __future__ import annotations

import json
import subprocess
import tempfile
from hashlib import md5
from pathlib import Path

from app.knowledge_builder import SourceDocument, build_knowledge_index
from app.parsing.parsers.doc_converter import convert_doc_to_docx
from app.parsing.parsers.docx_parser import parse_docx
from app.parsing.parsers.pdf_parser import parse_pdf


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_DIR = Path('/home/wgw/CodexProject/CodeFactoryV2/20161116体系结构文献翻译汇总')
EXTRACT_ROOT = WORKTREE_ROOT / '.data/source_archives/20161116'
OUTPUT_ROOT = WORKTREE_ROOT / '.data/knowledge_output'
SUPPORTED_SUFFIXES = {'.pdf', '.docx', '.doc'}


def main() -> None:
    extract_archives(DEFAULT_ARCHIVE_DIR, EXTRACT_ROOT)
    documents = collect_documents(resolve_document_roots(DEFAULT_ARCHIVE_DIR, EXTRACT_ROOT))
    knowledge = build_knowledge_index(documents)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_ROOT / '20161116-nas-knowledge.json'
    md_path = OUTPUT_ROOT / '20161116-nas-knowledge.md'

    json_path.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(render_summary(knowledge), encoding='utf-8')

    print(f'Wrote {json_path}')
    print(f'Wrote {md_path}')
    print(json.dumps(knowledge['summary'], ensure_ascii=False, indent=2))


def resolve_document_roots(archive_dir: Path, extract_root: Path) -> list[Path]:
    roots: list[Path] = []

    if _contains_supported_documents(archive_dir):
        roots.append(archive_dir)
    if extract_root.exists() and _contains_supported_documents(extract_root):
        roots.append(extract_root)

    return roots or [archive_dir]


def extract_archives(archive_dir: Path, extract_root: Path) -> None:
    extract_root.mkdir(parents=True, exist_ok=True)
    for archive in sorted(archive_dir.glob('*.rar')):
        target = extract_root / archive.stem
        if any(target.rglob('*')):
            continue
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(['unar', '-force-overwrite', '-output-directory', str(target), str(archive)], check=False)


def collect_documents(document_roots: Path | list[Path]) -> list[SourceDocument]:
    roots = [document_roots] if isinstance(document_roots, Path) else list(document_roots)
    documents_by_digest: dict[str, tuple[int, SourceDocument]] = {}

    for priority, root in enumerate(roots):
        if not root.exists():
            continue

        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.name.startswith('~$'):
                continue

            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                continue

            try:
                text = extract_text(path)
            except Exception as exc:
                print(f'SKIP unreadable file: {path} ({exc})')
                continue
            if not text.strip():
                continue

            relative_path = path.relative_to(root)
            source_archive = relative_path.parts[0] if relative_path.parts else root.name
            document = SourceDocument(
                path=str(relative_path),
                title=path.stem,
                file_type=suffix.lstrip('.'),
                source_archive=source_archive,
                text=text,
            )

            digest = _file_digest(path)
            existing = documents_by_digest.get(digest)
            if existing is None or priority < existing[0]:
                documents_by_digest[digest] = (priority, document)

    return sorted((item[1] for item in documents_by_digest.values()), key=lambda document: document.path)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        pages = parse_pdf(str(path))
        return '\n'.join(text for _, text in pages if text.strip())
    if suffix == '.docx':
        return '\n'.join(parse_docx(str(path)))
    if suffix == '.doc':
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = convert_doc_to_docx(str(path), temp_dir)
            return '\n'.join(parse_docx(docx_path))
    return ''


def render_summary(knowledge: dict) -> str:
    lines = [
        '# 20161116 NAS 架构资料知识构建结果',
        '',
        '## 摘要',
        f"- 文档数：{knowledge['summary']['document_count']}",
        f"- 实体数：{knowledge['summary']['entity_count']}",
        f"- 事件数：{knowledge['summary']['event_count']}",
        f"- 流程数：{knowledge['summary']['process_count']}",
        '',
        '## 关键事件',
    ]
    for item in knowledge['events'][:10]:
        lines.append(f"- {item['name']}：关联文档 {len(item['document_ids'])} 份")

    lines.extend(['', '## 关键流程'])
    for item in knowledge['processes'][:15]:
        lines.append(f"- {item['name']}：关联文档 {len(item['document_ids'])} 份")

    lines.extend(['', '## 关键实体'])
    for item in knowledge['entities'][:30]:
        aliases = f"（别名: {', '.join(item['aliases'])}）" if item['aliases'] else ''
        lines.append(f"- {item['name']}{aliases}：{item['category']}，关联文档 {len(item['document_ids'])} 份")

    return '\n'.join(lines) + '\n'


def _contains_supported_documents(root: Path) -> bool:
    return any(
        path.is_file() and not path.name.startswith('~$') and path.suffix.lower() in SUPPORTED_SUFFIXES
        for path in root.rglob('*')
    )


def _file_digest(path: Path) -> str:
    hasher = md5()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


if __name__ == '__main__':
    main()
