from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.archive_knowledge.preview_archive import write_preview_archive_artifacts
from app.archive_knowledge.registry import ArchiveRegistryService
from app.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将单文档正式抽取预览结果注册为可查看的知识库")
    parser.add_argument("--archive-id", required=True)
    parser.add_argument("--archive-name", required=True)
    parser.add_argument("--preview-file", required=True)
    parser.add_argument("--document-path", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--source-archive", default="preview")
    parser.add_argument("--file-type", default="pdf")
    parser.add_argument("--character-count", type=int, required=True)
    parser.add_argument("--activate", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    preview_payload = json.loads(Path(args.preview_file).read_text(encoding="utf-8"))

    artifacts = write_preview_archive_artifacts(
        output_root=settings.knowledge_output_root,
        archive_id=args.archive_id,
        archive_name=args.archive_name,
        preview_payload=preview_payload,
        document_path=args.document_path,
        source_archive=args.source_archive,
        file_type=args.file_type,
        character_count=args.character_count,
    )

    registry_service = ArchiveRegistryService(
        settings.knowledge_output_root,
        default_archive_id=settings.default_archive_id,
        default_archive_name=settings.default_archive_name,
        default_source_dir=settings.default_archive_source_dir,
        default_extract_root=settings.default_archive_extract_root,
        extract_root_parent=settings.archive_extract_root,
    )

    if registry_service.get_archive(args.archive_id) is None:
        registry_service.create_archive(
            archive_id=args.archive_id,
            name=args.archive_name,
            source_dir=args.source_dir,
        )
    registry_service.mark_extracted(args.archive_id)
    activated_archive = registry_service.activate_archive(args.archive_id) if args.activate else registry_service.get_archive(args.archive_id)

    print(
        json.dumps(
            {
                "archive": activated_archive,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
