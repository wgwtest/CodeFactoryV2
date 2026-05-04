from __future__ import annotations


class FrozenPackageProjector:
    def project(self, document_detail: dict) -> dict:
        frozen_package = dict(document_detail.get("frozen_package") or {})
        structured_spec = dict(frozen_package.get("structured_spec") or {})
        return {
            "source_document_id": document_detail["document_id"],
            "title": document_detail["title"],
            "archive_id": (document_detail.get("archive_ids") or [None])[0],
            "status": "frozen",
            "payload": structured_spec,
        }

