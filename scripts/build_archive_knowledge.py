from __future__ import annotations

import json
from pathlib import Path

from app.archive_knowledge.builder import (
    build_archive_knowledge,
    collect_documents,
    extract_archives,
    resolve_document_roots,
)


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_DIR = Path("/home/wgw/CodexProject/CodeFactoryV2/20161116体系结构文献翻译汇总")
EXTRACT_ROOT = WORKTREE_ROOT / ".data/source_archives/20161116"
OUTPUT_ROOT = WORKTREE_ROOT / ".data/knowledge_output"


def main() -> None:
    result = build_archive_knowledge(
        archive_id="20161116-nas",
        archive_name="20161116 NAS 知识库",
        source_dir=DEFAULT_ARCHIVE_DIR,
        extract_root=EXTRACT_ROOT,
        output_root=OUTPUT_ROOT,
        formal_extraction_mode=True,
    )
    print(f"Wrote {result.json_path}")
    print(f"Wrote {result.curated_path}")
    print(f"Wrote {result.markdown_path}")
    print(f"Wrote {result.parsed_documents_path}")
    print(f"Wrote {result.extraction_report_path}")
    print(json.dumps(result.summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
