from app.archive_knowledge.rebuild import reconcile_curated_payload


def test_reconcile_curated_payload_preserves_review_state_and_manual_edits() -> None:
    base_payload = {
        "summary": {
            "document_count": 2,
            "entity_count": 2,
            "event_count": 0,
            "process_count": 1,
            "relation_count": 3,
        },
        "documents": [
            {"id": "doc-1", "title": "NAS OV-2"},
            {"id": "doc-2", "title": "NAS OV-5"},
        ],
        "entities": [
            {
                "id": "entity-ov2",
                "name": "OV-2",
                "category": "architecture_artifact",
                "aliases": [],
                "document_ids": ["doc-1"],
                "evidence": [],
            },
            {
                "id": "entity-nas",
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "document_ids": ["doc-1", "doc-2"],
                "evidence": [],
            },
        ],
        "events": [],
        "processes": [
            {
                "id": "process-transfer",
                "name": "管制移交",
                "category": "domain_process",
                "aliases": [],
                "document_ids": ["doc-2"],
                "evidence": [],
            }
        ],
        "relations": [
            {"type": "describes", "from": "entity-ov2", "to": "entity-nas"},
            {"type": "part_of", "from": "process-transfer", "to": "entity-nas"},
            {"type": "document_mentions", "from": "doc-1", "to": "entity-ov2"},
        ],
    }

    previous_curated_payload = {
        "summary": {
            "document_count": 1,
            "entity_count": 1,
            "event_count": 0,
            "process_count": 0,
        },
        "documents": [{"id": "doc-1", "title": "NAS OV-2"}],
        "entities": [
            {
                "id": "entity-ov2",
                "name": "OV-2 运行关系图",
                "category": "architecture_concept",
                "aliases": ["运行关系图", "OV-2"],
                "document_ids": ["doc-1"],
                "evidence": [],
                "review_status": "approved",
            }
        ],
        "events": [],
        "processes": [],
        "relations": [],
    }

    reconciled = reconcile_curated_payload(base_payload, previous_curated_payload)
    entity_index = {item["id"]: item for item in reconciled["entities"]}
    process_index = {item["id"]: item for item in reconciled["processes"]}

    assert entity_index["entity-ov2"]["name"] == "OV-2 运行关系图"
    assert entity_index["entity-ov2"]["category"] == "architecture_concept"
    assert entity_index["entity-ov2"]["aliases"] == ["运行关系图", "OV-2"]
    assert entity_index["entity-ov2"]["review_status"] == "approved"
    assert entity_index["entity-nas"]["review_status"] == "pending"
    assert process_index["process-transfer"]["review_status"] == "pending"
    assert reconciled["summary"] == base_payload["summary"]
    assert reconciled["relations"] == base_payload["relations"]
