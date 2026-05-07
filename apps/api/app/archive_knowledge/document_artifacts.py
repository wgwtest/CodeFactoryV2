from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.knowledge_builder import (
    SourceDocument,
    _default_category,
    _document_id,
    _extract_document_knowledge,
    _normalize_item_kind,
    _resolve_item_id,
    _slug,
)
from app.archive_knowledge.quality_gate_policy import (
    build_quality_gate_runtime_trace as evaluate_quality_gate_policy,
)
from app.archive_knowledge.runtime_policy_contract import attach_policy_contract_trace

ITEM_COLLECTIONS: tuple[tuple[str, str], ...] = (
    ("entities", "entity"),
    ("events", "event"),
    ("processes", "process"),
)


def build_document_contribution(
    document: SourceDocument,
    extraction_service=None,
    *,
    document_id: str | None = None,
    policy_snapshot: dict | None = None,
) -> dict:
    document_id = document_id or _document_id(document.path)
    batch = _extract_document_knowledge(document, document_id, extraction_service)
    runtime_trace = dict(batch.metadata.get("runtime_trace") or {})

    items_by_key: dict[tuple[str, str], dict] = {}
    for candidate in batch.candidates:
        item_kind = _normalize_item_kind(candidate.item_type)
        item_key = (item_kind, candidate.canonical_name)
        item = items_by_key.setdefault(
            item_key,
            {
                "id": candidate.payload.get("id") or f"{item_kind}-{_slug(candidate.canonical_name)}",
                "name": candidate.canonical_name,
                "category": candidate.payload.get("category", _default_category(item_kind)),
                "aliases": [],
                "document_ids": [document_id],
                "evidence": [],
            },
        )
        item["aliases"] = _merge_unique_strings(item["aliases"], candidate.payload.get("aliases", []))
        evidence = candidate.payload.get("evidence")
        if evidence:
            item["evidence"] = _merge_evidence(
                item["evidence"],
                [{"document_id": document_id, "excerpt": str(evidence)[:240]}],
            )

    relations = []
    for relation in batch.relations:
        relation_row: dict[str, str | float] = {
            "type": relation.relation_type,
            "source_name": relation.source_name,
            "target_name": relation.target_name,
        }
        if relation.confidence is not None:
            relation_row["confidence"] = relation.confidence
        evidence = relation.payload.get("evidence")
        if evidence:
            relation_row["evidence"] = evidence
        relations.append(relation_row)

    contribution = {
        "document": {
            "id": document_id,
            "path": document.path,
            "title": document.title,
            "file_type": document.file_type,
            "source_archive": document.source_archive,
            "character_count": len(document.text),
            "parser_name": document.parser_name,
            "segment_count": document.segment_count or len(document.segments or []),
            "source_file_path": document.source_file_path,
            "source_digest": document.source_digest,
        },
        "entities": _finalize_collection(items_by_key, "entity"),
        "events": _finalize_collection(items_by_key, "event"),
        "processes": _finalize_collection(items_by_key, "process"),
        "relations": sorted(relations, key=lambda item: (item["type"], item["source_name"], item["target_name"])),
        "extraction": {
            "strategy": batch.strategy,
            "schema_version": batch.schema_version,
            "candidate_count": len(batch.candidates),
            "relation_count": len(batch.relations),
            **batch.metadata,
        },
    }
    runtime_trace["quality_policy_evaluation_governance_gate"] = _build_quality_gate_runtime_trace(
        document_id=document_id,
        document_title=document.title,
        contribution=contribution,
        policy_snapshot=policy_snapshot,
    )
    contribution["extraction"]["runtime_trace"] = runtime_trace
    attach_policy_contract_trace(
        archive_id=str((policy_snapshot or {}).get("archive_id") or "archive"),
        document_id=document_id,
        document_title=document.title,
        contribution=contribution,
        policy_snapshot=policy_snapshot,
    )
    return contribution


def aggregate_document_contributions(contributions: list[dict]) -> dict:
    nodes: dict[tuple[str, str], dict] = {}
    relations: list[dict[str, str | float]] = []
    relation_keys: set[tuple[str, str, str]] = set()
    document_rows: list[dict[str, str | int]] = []
    known_item_ids_by_name: dict[str, str] = {}
    known_item_ids_by_alias: dict[str, str] = {}
    relation_scopes: list[tuple[list[dict], dict[str, str], dict[str, str]]] = []

    for contribution in sorted(contributions, key=lambda item: item["document"]["path"]):
        document = contribution["document"]
        document_rows.append(
            {
                "id": document["id"],
                "path": document["path"],
                "title": document["title"],
                "file_type": document["file_type"],
                "source_archive": document["source_archive"],
                "character_count": document["character_count"],
            }
        )

        local_item_ids_by_name: dict[str, str] = {}
        local_item_ids_by_alias: dict[str, str] = {}

        for collection_name, item_kind in ITEM_COLLECTIONS:
            for item in contribution.get(collection_name, []):
                node = nodes.setdefault(
                    (item_kind, _slug(item["name"])),
                    {
                        "id": item.get("id") or f"{item_kind}-{_slug(item['name'])}",
                        "kind": item_kind,
                        "name": item["name"],
                        "category": item.get("category", _default_category(item_kind)),
                        "aliases": set(),
                        "documents": set(),
                        "evidence": [],
                    },
                )
                node["aliases"].update(item.get("aliases", []))
                node["documents"].update(item.get("document_ids", []))
                node["evidence"] = _merge_evidence(node["evidence"], item.get("evidence", []))

                local_item_ids_by_name[item["name"]] = node["id"]
                local_item_ids_by_alias[_slug(item["name"])] = node["id"]
                known_item_ids_by_name[item["name"]] = node["id"]
                known_item_ids_by_alias[_slug(item["name"])] = node["id"]
                for alias in item.get("aliases", []):
                    alias_slug = _slug(alias)
                    local_item_ids_by_alias.setdefault(alias_slug, node["id"])
                    known_item_ids_by_alias.setdefault(alias_slug, node["id"])

                _add_relation(relations, relation_keys, "document_mentions", document["id"], node["id"])

        relation_scopes.append((contribution.get("relations", []), local_item_ids_by_name, local_item_ids_by_alias))

    for scoped_relations, local_item_ids_by_name, local_item_ids_by_alias in relation_scopes:
        for relation in scoped_relations:
            source_id = _resolve_item_id(
                relation["source_name"],
                local_item_ids_by_name,
                local_item_ids_by_alias,
                known_item_ids_by_name,
                known_item_ids_by_alias,
            )
            target_id = _resolve_item_id(
                relation["target_name"],
                local_item_ids_by_name,
                local_item_ids_by_alias,
                known_item_ids_by_name,
                known_item_ids_by_alias,
            )
            if source_id is None or target_id is None or source_id == target_id:
                continue
            _add_relation(
                relations,
                relation_keys,
                relation["type"],
                source_id,
                target_id,
                confidence=relation.get("confidence"),
                evidence=relation.get("evidence"),
            )

    entities = _finalize_nodes(nodes, "entity")
    events = _finalize_nodes(nodes, "event")
    processes = _finalize_nodes(nodes, "process")

    return {
        "documents": sorted(document_rows, key=lambda item: item["path"]),
        "entities": entities,
        "events": events,
        "processes": processes,
        "relations": sorted(relations, key=lambda item: (item["type"], item["from"], item["to"])),
        "summary": {
            "document_count": len(document_rows),
            "entity_count": len(entities),
            "event_count": len(events),
            "process_count": len(processes),
            "relation_count": len(relations),
        },
    }


def build_parsed_documents_payload(contributions: list[dict]) -> list[dict]:
    return [
        {
            "path": contribution["document"]["path"],
            "title": contribution["document"]["title"],
            "file_type": contribution["document"]["file_type"],
            "source_archive": contribution["document"]["source_archive"],
            "parser_name": contribution["document"].get("parser_name"),
            "segment_count": contribution["document"].get("segment_count", 0),
            "character_count": contribution["document"]["character_count"],
        }
        for contribution in sorted(contributions, key=lambda item: item["document"]["path"])
    ]


def build_extraction_report_payload(
    *,
    archive_id: str,
    archive_name: str,
    strict_mode: bool,
    contributions: list[dict],
    summary: dict,
    warnings: list[dict] | None = None,
) -> dict:
    documents = []
    for contribution in sorted(contributions, key=lambda item: item["document"]["path"]):
        document = contribution["document"]
        extraction = contribution.get("extraction", {})
        documents.append(
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
    return {
        "archive_id": archive_id,
        "archive_name": archive_name,
        "strict_mode": strict_mode,
        "summary": summary,
        "warning_count": len(warnings or []),
        "warnings": list(warnings or []),
        "documents": documents,
    }


class DocumentArtifactRepository:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def has_manifest(self, archive_id: str) -> bool:
        return self._resolve_manifest_path(archive_id).exists()

    def load_manifest(self, archive_id: str) -> dict | None:
        manifest_path = self._resolve_manifest_path(archive_id)
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return self._normalize_manifest(manifest)

    def load_build_state(self, archive_id: str) -> dict | None:
        build_state_path = self._resolve_build_state_path(archive_id)
        if not build_state_path.exists():
            return None
        return json.loads(build_state_path.read_text(encoding="utf-8"))

    def save_build_state(self, archive_id: str, build_state: dict) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        payload = {
            **build_state,
            "archive_id": archive_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._resolve_build_state_path(archive_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_documents(self, archive_id: str) -> list[dict]:
        manifest = self.load_manifest(archive_id)
        if manifest is None:
            return []
        return manifest.get("documents", [])

    def replace_all(self, archive_id: str, contributions: list[dict]) -> None:
        artifact_dir = self._resolve_artifact_dir(archive_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stale_paths = {path.name for path in artifact_dir.glob("*.json")}
        manifest_documents = []

        for contribution in sorted(contributions, key=lambda item: item["document"]["path"]):
            artifact_path = artifact_dir / f"{contribution['document']['id']}.json"
            artifact_path.write_text(json.dumps(contribution, ensure_ascii=False, indent=2), encoding="utf-8")
            stale_paths.discard(artifact_path.name)
            manifest_documents.append(self._build_manifest_document(contribution, artifact_path))

        for stale_name in stale_paths:
            (artifact_dir / stale_name).unlink(missing_ok=True)

        self._write_manifest(archive_id, manifest_documents)

    def upsert(self, archive_id: str, contribution: dict, *, included_in_archive: bool = True) -> None:
        artifact_dir = self._resolve_artifact_dir(archive_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / f"{contribution['document']['id']}.json"
        artifact_path.write_text(json.dumps(contribution, ensure_ascii=False, indent=2), encoding="utf-8")

        manifest = self.load_manifest(archive_id) or {"archive_id": archive_id, "documents": []}
        manifest_documents = [item for item in manifest.get("documents", []) if item.get("document_id") != contribution["document"]["id"]]
        manifest_documents.append(
            self._build_manifest_document(
                contribution,
                artifact_path,
                included_in_archive=included_in_archive,
            )
        )
        manifest_documents.sort(key=lambda item: item["path"])
        self._write_manifest(archive_id, manifest_documents)

    def load_contributions(self, archive_id: str, *, included_only: bool = False) -> list[dict]:
        manifest = self.load_manifest(archive_id)
        if manifest is None:
            return []
        artifact_dir = self._resolve_artifact_dir(archive_id)
        contributions = []
        for document in manifest.get("documents", []):
            if included_only and not document.get("included_in_archive", True):
                continue
            artifact_path = artifact_dir / document["artifact_file"]
            if not artifact_path.exists():
                raise FileNotFoundError(f"文档级正式产物缺失: {artifact_path}")
            contributions.append(json.loads(artifact_path.read_text(encoding="utf-8")))
        return contributions

    def load_document_contribution(self, archive_id: str, document_id: str) -> dict | None:
        document = self.get_document_source_info(archive_id, document_id)
        if document is None:
            return None

        artifact_path = self._resolve_artifact_dir(archive_id) / document["artifact_file"]
        if not artifact_path.exists():
            raise FileNotFoundError(f"文档级正式产物缺失: {artifact_path}")
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    def get_document_source_info(self, archive_id: str, document_id: str) -> dict | None:
        manifest = self.load_manifest(archive_id)
        if manifest is None:
            return None
        for document in manifest.get("documents", []):
            if document.get("document_id") == document_id:
                return document
        return None

    def has_reusable_artifact(
        self,
        archive_id: str,
        document_id: str,
        *,
        source_digest: str | None,
    ) -> bool:
        if not source_digest:
            return False

        document = self.get_document_source_info(archive_id, document_id)
        if document is None:
            return False
        if document.get("source_digest") != source_digest:
            return False

        artifact_path = self._resolve_artifact_dir(archive_id) / document["artifact_file"]
        return artifact_path.exists()

    def set_included_in_archive(self, archive_id: str, document_id: str, *, included_in_archive: bool) -> dict | None:
        manifest = self.load_manifest(archive_id)
        if manifest is None:
            return None

        updated_document = None
        documents = []
        for document in manifest.get("documents", []):
            if document.get("document_id") == document_id:
                document = {**document, "included_in_archive": included_in_archive}
                updated_document = document
            documents.append(document)

        if updated_document is None:
            return None

        self._write_manifest(archive_id, documents)
        return updated_document

    def prune(self, archive_id: str, *, keep_document_ids: set[str]) -> None:
        manifest = self.load_manifest(archive_id)
        if manifest is None:
            return

        artifact_dir = self._resolve_artifact_dir(archive_id)
        kept_documents: list[dict] = []
        removed_any = False
        for document in manifest.get("documents", []):
            if document.get("document_id") in keep_document_ids:
                kept_documents.append(document)
                continue
            removed_any = True
            (artifact_dir / document["artifact_file"]).unlink(missing_ok=True)

        if removed_any:
            self._write_manifest(archive_id, kept_documents)

    def _write_manifest(self, archive_id: str, documents: list[dict]) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._resolve_manifest_path(archive_id).write_text(
            json.dumps(
                {
                    "archive_id": archive_id,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "document_count": len(documents),
                    "documents": documents,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _build_manifest_document(contribution: dict, artifact_path: Path, *, included_in_archive: bool = True) -> dict:
        document = contribution["document"]
        extraction = contribution.get("extraction", {})
        entity_count = len(contribution.get("entities", []))
        event_count = len(contribution.get("events", []))
        process_count = len(contribution.get("processes", []))
        return {
            "document_id": document["id"],
            "path": document["path"],
            "title": document["title"],
            "file_type": document["file_type"],
            "source_archive": document["source_archive"],
            "character_count": document["character_count"],
            "parser_name": document.get("parser_name"),
            "segment_count": document.get("segment_count", 0),
            "source_file_path": document.get("source_file_path"),
            "source_digest": document.get("source_digest"),
            "artifact_file": artifact_path.name,
            "included_in_archive": included_in_archive,
            "entity_count": entity_count,
            "event_count": event_count,
            "process_count": process_count,
            "knowledge_item_count": entity_count + event_count + process_count,
            "candidate_count": extraction.get("candidate_count", 0),
            "relation_count": extraction.get("relation_count", 0),
            "llm_provider": extraction.get("llm_provider"),
            "llm_model": extraction.get("llm_model"),
            "chunking_used": extraction.get("chunking_used"),
        }

    def _resolve_artifact_dir(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-document-artifacts"

    def _resolve_manifest_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-document-artifacts.json"

    def _resolve_build_state_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-document-build-state.json"

    @staticmethod
    def _normalize_manifest(manifest: dict) -> dict:
        return {
            **manifest,
            "documents": [
                DocumentArtifactRepository._normalize_manifest_document(document)
                for document in manifest.get("documents", [])
            ],
        }

    @staticmethod
    def _normalize_manifest_document(document: dict) -> dict:
        normalized = dict(document)
        normalized["included_in_archive"] = normalized.get("included_in_archive", True)
        normalized.setdefault("entity_count", 0)
        normalized.setdefault("event_count", 0)
        normalized.setdefault("process_count", 0)
        normalized.setdefault("source_digest", None)
        normalized.setdefault(
            "knowledge_item_count",
            normalized["entity_count"] + normalized["event_count"] + normalized["process_count"],
        )
        return normalized


def _build_quality_gate_runtime_trace(
    *,
    document_id: str,
    document_title: str,
    contribution: dict,
    policy_snapshot: dict | None = None,
) -> dict:
    return evaluate_quality_gate_policy(
        document_id=document_id,
        document_title=document_title,
        contribution=contribution,
        policy_snapshot=policy_snapshot,
    )


def _finalize_collection(items_by_key: dict[tuple[str, str], dict], item_kind: str) -> list[dict]:
    items = []
    for (kind, _), item in items_by_key.items():
        if kind != item_kind:
            continue
        items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "aliases": sorted(item["aliases"]),
                "document_ids": sorted(item["document_ids"]),
                "evidence": item["evidence"],
            }
        )
    return sorted(items, key=lambda item: item["name"])


def _finalize_nodes(nodes: dict[tuple[str, str], dict], kind: str) -> list[dict]:
    finalized = []
    for (_, _), node in nodes.items():
        if node["kind"] != kind:
            continue
        finalized.append(
            {
                "id": node["id"],
                "name": node["name"],
                "category": node["category"],
                "aliases": sorted(node["aliases"]),
                "document_ids": sorted(node["documents"]),
                "evidence": node["evidence"][:5],
            }
        )
    return sorted(finalized, key=lambda item: (-len(item["document_ids"]), item["name"]))


def _add_relation(
    relations: list[dict[str, str | float]],
    relation_keys: set[tuple[str, str, str]],
    relation_type: str,
    from_id: str,
    to_id: str,
    *,
    confidence: float | None = None,
    evidence: str | None = None,
) -> None:
    key = (relation_type, from_id, to_id)
    if key in relation_keys:
        for relation in relations:
            if relation["type"] != relation_type or relation["from"] != from_id or relation["to"] != to_id:
                continue
            if confidence is not None:
                relation["confidence"] = max(confidence, float(relation.get("confidence", 0)))
            if evidence and not relation.get("evidence"):
                relation["evidence"] = evidence
        return

    relation_keys.add(key)
    relation: dict[str, str | float] = {"type": relation_type, "from": from_id, "to": to_id}
    if confidence is not None:
        relation["confidence"] = confidence
    if evidence:
        relation["evidence"] = evidence
    relations.append(relation)


def _merge_unique_strings(existing: list[str], incoming: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*existing, *incoming]:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def _merge_evidence(*groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str | None, str]] = set()
    for evidence_group in groups:
        for evidence in evidence_group:
            key = (evidence.get("document_id"), evidence.get("excerpt", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(
                {
                    "document_id": evidence.get("document_id"),
                    "excerpt": evidence.get("excerpt", ""),
                }
            )
    return merged
