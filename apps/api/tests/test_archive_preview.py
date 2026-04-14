from app.archive_knowledge.preview_archive import build_preview_archive_payload


def test_build_preview_archive_payload_creates_single_document_archive() -> None:
    preview_payload = {
        "document": {
            "path": "DataSource/doctrine/FM_6-02_Signal_Support_to_Operations_CitizenMilitem.pdf",
            "title": "FM_6-02_Signal_Support_to_Operations_CitizenMilitem",
            "parser": "docling_pdf",
            "segment_count": 385,
            "chunk_count": 16,
            "chunk_char_limit": 32000,
            "character_count": 190994,
        },
        "final_batch": {
            "document_id": "fm-6-02",
            "title": "FM_6-02_Signal_Support_to_Operations_CitizenMilitem",
            "strategy": "chunked_schema_rules+llm",
            "schema_version": "p1.v1",
            "candidates": [
                {
                    "item_type": "entity",
                    "canonical_name": "信号支援",
                    "status": "extracted",
                    "confidence": 0.92,
                    "payload": {
                        "category": "domain_concept",
                        "aliases": ["Signal Support"],
                        "evidence": "Signal support enables operations.",
                        "source_refs": [{"chunk_id": "chunk-001", "chunk_heading": "FM 6-02"}],
                    },
                },
                {
                    "item_type": "process",
                    "canonical_name": "请求信号支援",
                    "status": "extracted",
                    "confidence": 0.88,
                    "payload": {
                        "category": "domain_process",
                        "evidence": "Requesting signal support is a command process.",
                    },
                },
            ],
            "relations": [
                {
                    "relation_type": "part_of",
                    "source_name": "请求信号支援",
                    "target_name": "信号支援",
                    "confidence": 0.8,
                    "payload": {"evidence": "Requesting signal support is part of signal support."},
                }
            ],
            "metadata": {
                "chunking_used": True,
                "chunk_count": 16,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
            },
        },
    }

    base_payload, curated_payload = build_preview_archive_payload(
        preview_payload,
        document_path="FM_6-02_Signal_Support_to_Operations_CitizenMilitem.pdf",
        source_archive="doctrine",
        file_type="pdf",
        character_count=190994,
    )

    assert base_payload["summary"] == {
        "document_count": 1,
        "entity_count": 1,
        "event_count": 0,
        "process_count": 1,
        "relation_count": 3,
    }
    assert base_payload["documents"][0]["path"] == "FM_6-02_Signal_Support_to_Operations_CitizenMilitem.pdf"
    assert base_payload["documents"][0]["character_count"] == 190994
    assert curated_payload["entities"][0]["review_status"] == "pending"
    assert curated_payload["processes"][0]["review_status"] == "pending"
