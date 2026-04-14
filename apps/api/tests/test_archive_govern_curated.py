from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "govern_archive_curated.py"
_SPEC = spec_from_file_location("govern_archive_curated", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
govern_payload = _MODULE.govern_payload


def _document(document_id: str) -> dict:
    return {
        "id": document_id,
        "title": f"{document_id}.pdf",
        "file_type": "pdf",
        "source_archive": "MJ-V1",
        "character_count": 1000,
    }


def _entity(
    entity_id: str,
    name: str,
    *,
    aliases: list[str] | None = None,
    category: str = "domain_concept",
    document_ids: list[str] | None = None,
) -> dict:
    return {
        "id": entity_id,
        "name": name,
        "category": category,
        "aliases": aliases or [],
        "document_ids": document_ids or ["doc-1"],
        "evidence": [],
    }


def _payload(entities: list[dict], *, documents: list[dict] | None = None) -> dict:
    docs = documents or [_document("doc-1")]
    return {
        "summary": {
            "document_count": len(docs),
            "entity_count": len(entities),
            "event_count": 0,
            "process_count": 0,
            "relation_count": 0,
        },
        "documents": docs,
        "entities": entities,
        "events": [],
        "processes": [],
        "relations": [],
    }


def test_govern_payload_rejects_generic_and_unit_code_noise() -> None:
    payload = _payload(
        [
            _entity("entity-plan", "Plan", document_ids=["doc-1", "doc-2"]),
            _entity("entity-dod-form", "Department Of Defense Form"),
            _entity("entity-b-1-52-av", "B/1-52 AV", aliases=["ARB"]),
            _entity("entity-cm-co", "CM CO", aliases=["MX"]),
            _entity("entity-civilian", "CIVILIAN", aliases=["OPTIONAL", "OPTIONAL FILL"]),
        ],
        documents=[_document("doc-1"), _document("doc-2")],
    )

    governed, _ = govern_payload(payload)
    item_index = {item["id"]: item for item in governed["entities"]}

    assert item_index["entity-plan"]["review_status"] == "rejected"
    assert item_index["entity-dod-form"]["review_status"] == "rejected"
    assert item_index["entity-b-1-52-av"]["review_status"] == "rejected"
    assert item_index["entity-cm-co"]["review_status"] == "rejected"
    assert item_index["entity-civilian"]["review_status"] == "rejected"
    assert item_index["entity-civilian"]["aliases"] == []
    assert governed["summary"]["entity_count"] == 0


def test_govern_payload_rejects_noisy_duplicates_when_clean_alias_match_exists() -> None:
    payload = _payload(
        [
            _entity("entity-cop-clean", "Common Operating Picture", aliases=["COP"]),
            _entity(
                "entity-cop-noisy",
                "A lack of a defined common operating picture",
                aliases=["COP"],
            ),
            _entity("entity-fbi-clean", "Federal Bureau of Investigation", aliases=["FBI"]),
            _entity(
                "entity-fbi-noisy",
                "Full Octagon N/A FEDERAL BUREAU OF INVESTIGATION",
                aliases=["FBI"],
                category="architecture_concept",
            ),
        ]
    )

    governed, _ = govern_payload(payload)
    item_index = {item["id"]: item for item in governed["entities"]}

    assert item_index["entity-cop-clean"]["review_status"] == "approved"
    assert item_index["entity-fbi-clean"]["review_status"] == "approved"
    assert item_index["entity-cop-noisy"]["review_status"] == "rejected"
    assert item_index["entity-fbi-noisy"]["review_status"] == "rejected"
    assert governed["summary"]["entity_count"] == 2


def test_govern_payload_salvages_noise_prefixed_terms_without_clean_duplicates() -> None:
    payload = _payload(
        [
            _entity(
                "entity-tvb",
                "CENTER FOR ARMY LESSONS LEARNED Tactical Voice Bridge",
                aliases=["TVB"],
                category="architecture_concept",
            ),
            _entity(
                "entity-vstol",
                "D Code Remarks. Vertical or Short Take-off and Landing",
                aliases=["VSTOL"],
            ),
        ]
    )

    governed, stats = govern_payload(payload)
    item_index = {item["id"]: item for item in governed["entities"]}

    assert item_index["entity-tvb"]["name"] == "Tactical Voice Bridge"
    assert item_index["entity-vstol"]["name"] == "Vertical Or Short Take-off And Landing"
    assert item_index["entity-tvb"]["review_status"] == "approved"
    assert item_index["entity-vstol"]["review_status"] == "approved"
    assert stats["renamed"] == 2


def test_govern_payload_rejects_sentence_fragments_and_code_strings() -> None:
    payload = _payload(
        [
            _entity(
                "entity-sentence",
                "Consists of all personnel operating a particular system",
                category="system_or_service",
            ),
            _entity(
                "entity-code",
                "FT GORDON//NETC-SFC-OPY",
                aliases=["G3"],
            ),
        ]
    )

    governed, _ = govern_payload(payload)
    item_index = {item["id"]: item for item in governed["entities"]}

    assert item_index["entity-sentence"]["review_status"] == "rejected"
    assert item_index["entity-code"]["review_status"] == "rejected"


def test_govern_payload_strips_reference_prefixes_and_rejects_duplicate_roles() -> None:
    payload = _payload(
        [
            _entity("entity-g2", "G-2", aliases=["S-2"]),
            _entity(
                "entity-g2-noisy",
                "Enemy Forces Deployed 12-88. The G-2",
                aliases=["S-2"],
            ),
            _entity(
                "entity-mars",
                "AR 25-6. Military Affiliate Radio System",
                aliases=["MARS"],
                category="system_or_service",
            ),
        ]
    )

    governed, stats = govern_payload(payload)
    item_index = {item["id"]: item for item in governed["entities"]}

    assert item_index["entity-g2"]["review_status"] == "approved"
    assert item_index["entity-g2-noisy"]["name"] == "G-2"
    assert item_index["entity-g2-noisy"]["review_status"] == "rejected"
    assert item_index["entity-mars"]["name"] == "Military Affiliate Radio System"
    assert item_index["entity-mars"]["review_status"] == "approved"
    assert stats["renamed"] == 2
