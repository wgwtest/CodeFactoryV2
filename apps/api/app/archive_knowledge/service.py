from __future__ import annotations

import json
from pathlib import Path

from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.repository import JsonPublishedKnowledgeRepository
from app.archive_knowledge.artifact_catalog import build_interpretation
from app.archive_knowledge.language_projection import build_language_projection
from app.config import settings
from app.integrations.neo4j.client import Neo4jClient
from app.integrations.neo4j.repository import Neo4jPublishedKnowledgeRepository

ITEM_COLLECTIONS: tuple[tuple[str, str], ...] = (
    ("entities", "entity"),
    ("events", "event"),
    ("processes", "process"),
)
VALID_REVIEW_STATUSES = {"pending", "approved", "rejected"}
RELATION_SECTION_DEFINITIONS = {
    ("part_of", "incoming"): ("incoming_part_of", "包含的对象与流程", "包含"),
    ("part_of", "outgoing"): ("outgoing_part_of", "所属上位对象", "属于"),
    ("describes", "incoming"): ("incoming_describes", "描述它的架构产物", "被描述于"),
    ("describes", "outgoing"): ("outgoing_describes", "它描述的对象", "描述"),
    ("owned_by", "incoming"): ("incoming_owned_by", "负责的对象", "负责"),
    ("owned_by", "outgoing"): ("outgoing_owned_by", "责任方/发布方", "责任方"),
    ("operational_exchange", "incoming"): ("exchange_neighbors", "交换协同对象", "交换协同"),
    ("operational_exchange", "outgoing"): ("exchange_neighbors", "交换协同对象", "交换协同"),
    ("participates_in_exchange", "incoming"): ("incoming_exchange_participation", "参与该交换的对象", "参与方"),
    ("participates_in_exchange", "outgoing"): ("outgoing_exchange_participation", "参与的信息交换", "参与交换"),
    ("scoped_by", "incoming"): ("incoming_scoped_by", "受其约束的对象", "约束对象"),
    ("scoped_by", "outgoing"): ("outgoing_scoped_by", "相关阶段/约束", "受约束于"),
    ("process_scoped_by", "incoming"): ("incoming_scoped_by", "受其约束的对象", "约束对象"),
    ("process_scoped_by", "outgoing"): ("outgoing_scoped_by", "相关阶段/约束", "受约束于"),
}
RELATION_SECTION_ORDER = [
    "incoming_part_of",
    "outgoing_part_of",
    "incoming_describes",
    "outgoing_describes",
    "outgoing_owned_by",
    "incoming_owned_by",
    "exchange_neighbors",
    "outgoing_exchange_participation",
    "incoming_exchange_participation",
    "outgoing_scoped_by",
    "incoming_scoped_by",
    "other",
]


class ArchiveKnowledgeService:
    def __init__(self, output_root: str | Path, published_repository=None) -> None:
        self.output_root = Path(output_root)
        self.published_repository = published_repository or self._build_published_repository()
        self.artifact_repository = DocumentArtifactRepository(self.output_root)

    def get_summary(self, archive_id: str, document_ids: list[str] | None = None) -> dict:
        payload = self._load_public(archive_id, document_ids)
        return {"archive_id": archive_id, **payload["summary"]}

    def get_graph(self, archive_id: str, document_ids: list[str] | None = None) -> dict:
        payload = self._load_public(archive_id, document_ids)
        nodes = []
        for collection_name, node_type in ITEM_COLLECTIONS:
            for item in payload.get(collection_name, []):
                nodes.append(
                    {
                        "id": item["id"],
                        "label": item["name"],
                        "type": item.get("category", node_type),
                        "item_type": node_type,
                        "document_count": len(item.get("document_ids", [])),
                    }
                )

        node_ids = {node["id"] for node in nodes}
        edges = [
            relation
            for relation in payload.get("relations", [])
            if relation.get("from") in node_ids and relation.get("to") in node_ids
        ]
        return {
            "archive_id": archive_id,
            "nodes": nodes,
            "edges": [
                {"source": edge["from"], "target": edge["to"], "label": edge["type"]}
                for edge in edges
            ],
            "summary": payload["summary"],
            "publication": payload.get("publication"),
        }

    def get_processes(self, archive_id: str, document_ids: list[str] | None = None) -> list[dict]:
        payload = self._load_public(archive_id, document_ids)
        processes = [
            self._with_language_projection(
                {
                "id": item["id"],
                "item_type": "process",
                "name": item["name"],
                "category": item.get("category"),
                "aliases": item.get("aliases", []),
                "document_ids": item.get("document_ids", []),
                "document_count": len(item.get("document_ids", [])),
                "evidence": item.get("evidence", []),
                "interpretation": build_interpretation(item["name"], item.get("category", "domain_process")),
                }
            )
            for item in payload.get("processes", [])
        ]
        return sorted(processes, key=lambda item: (-item["document_count"], item["name"]))

    def get_entities(self, archive_id: str, document_ids: list[str] | None = None) -> list[dict]:
        payload = self._load_public(archive_id, document_ids)
        entities = [
            self._with_language_projection(
                {
                "id": item["id"],
                "name": item["name"],
                "category": item.get("category"),
                "aliases": item.get("aliases", []),
                "document_count": len(item.get("document_ids", [])),
                "interpretation": build_interpretation(item["name"], item.get("category", "domain_concept")),
                }
            )
            for item in payload.get("entities", [])
        ]
        return sorted(entities, key=lambda item: (-item["document_count"], item["name"]))

    def get_events(self, archive_id: str, document_ids: list[str] | None = None) -> list[dict]:
        payload = self._load_public(archive_id, document_ids)
        events = [
            self._with_language_projection(
                {
                "id": item["id"],
                "item_type": "event",
                "name": item["name"],
                "category": item.get("category"),
                "aliases": item.get("aliases", []),
                "document_ids": item.get("document_ids", []),
                "evidence": item.get("evidence", []),
                "document_count": len(item.get("document_ids", [])),
                "interpretation": build_interpretation(item["name"], item.get("category", "timeline_event")),
                }
            )
            for item in payload.get("events", [])
        ]
        return sorted(events, key=lambda item: (-item["document_count"], item["name"]))

    def get_item_detail(self, archive_id: str, item_id: str, document_ids: list[str] | None = None) -> dict | None:
        payload = self._load_public(archive_id, document_ids)
        item_info = self._find_item_info(payload, item_id)
        if item_info is None:
            return None
        return self._build_item_detail_response(payload, item_info)

    def get_item_graph(self, archive_id: str, item_id: str, document_ids: list[str] | None = None) -> dict | None:
        payload = self._load_public(archive_id, document_ids)
        item_info = self._find_item_info(payload, item_id)
        if item_info is None:
            return None

        _, item_type, _, item = item_info
        nodes = {
            item["id"]: {
                "id": item["id"],
                "label": item["name"],
                "item_type": item_type,
                "category": item.get("category"),
                "is_focus": True,
            }
        }
        edges = []
        seen_edges: set[tuple[str, str, str]] = set()

        for relation in payload.get("relations", []):
            if relation.get("from") == item_id:
                related_item_id = relation.get("to")
            elif relation.get("to") == item_id:
                related_item_id = relation.get("from")
            else:
                continue

            related_info = self._find_item_info(payload, related_item_id)
            if related_info is None:
                continue

            _, related_type, _, related_item = related_info
            nodes.setdefault(
                related_item["id"],
                {
                    "id": related_item["id"],
                    "label": related_item["name"],
                    "item_type": related_type,
                    "category": related_item.get("category"),
                    "is_focus": False,
                },
            )

            edge_key = (relation["from"], relation["to"], relation["type"])
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": relation["from"],
                    "target": relation["to"],
                    "label": relation["type"],
                }
            )

        return {
            "focus_item_id": item_id,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def get_document_detail(self, archive_id: str, document_id: str) -> dict | None:
        if self.artifact_repository.has_manifest(archive_id):
            document = self.artifact_repository.get_document_source_info(archive_id, document_id)
            contribution = self.artifact_repository.load_document_contribution(archive_id, document_id)
            if document is None or contribution is None:
                return None

            return {
                "document": self._build_document_record(
                    document,
                    self._build_document_stats_from_contribution(contribution),
                ),
                "knowledge_items": self._build_document_knowledge_items_from_contribution(contribution, document),
            }

        payload = self._load_public(archive_id)
        document_index = self._build_document_index(payload)
        document = document_index.get(document_id)
        if document is None:
            return None

        document_stats = self._build_document_stats(payload)
        return {
            "document": self._build_document_record(document, document_stats.get(document_id)),
            "knowledge_items": self._build_document_knowledge_items(payload, document_id, document),
        }

    def get_documents(self, archive_id: str) -> list[dict]:
        if self.artifact_repository.has_manifest(archive_id):
            documents = [
                self._build_document_record(
                    document,
                    {
                        "entity_count": document.get("entity_count", 0),
                        "event_count": document.get("event_count", 0),
                        "process_count": document.get("process_count", 0),
                    },
                )
                for document in self.artifact_repository.list_documents(archive_id)
            ]
            return sorted(documents, key=lambda item: (-item["knowledge_item_count"], item["title"]))

        payload = self._load_public(archive_id)
        document_stats = self._build_document_stats(payload)

        documents = []
        for document in payload.get("documents", []):
            documents.append(self._build_document_record(document, document_stats.get(document["id"])))

        return sorted(documents, key=lambda item: (-item["knowledge_item_count"], item["title"]))

    def get_review_candidates(
        self,
        archive_id: str,
        query: str | None = None,
        item_type: str | None = None,
        review_status: str | None = None,
    ) -> list[dict]:
        payload = self._load_raw(archive_id)
        document_titles = {document["id"]: document["title"] for document in payload.get("documents", [])}
        candidates = []
        normalized_query = (query or "").strip().lower()

        for collection_name, current_item_type in ITEM_COLLECTIONS:
            if item_type and item_type != current_item_type:
                continue

            for item in payload.get(collection_name, []):
                current_review_status = item.get("review_status", "pending")
                if review_status and current_review_status != review_status:
                    continue

                haystack = " ".join([item["name"], *item.get("aliases", [])]).lower()
                if normalized_query and normalized_query not in haystack:
                    continue

                evidence = item.get("evidence", [])
                first_evidence = evidence[0] if evidence else {}
                candidates.append(
                    {
                        "id": item["id"],
                        "item_type": current_item_type,
                        "canonical_name": item["name"],
                        "category": item.get("category"),
                        "document_count": len(item.get("document_ids", [])),
                        "confidence": self._estimate_confidence(item),
                        "review_status": current_review_status,
                        "evidence_excerpt": first_evidence.get("excerpt", ""),
                        "evidence_document_title": document_titles.get(first_evidence.get("document_id")),
                    }
                )

        return sorted(
            candidates,
            key=lambda item: (-item["confidence"], -item["document_count"], item["canonical_name"]),
        )

    def get_publication_overview(self, archive_id: str) -> dict:
        working_payload = self._apply_visibility_filter(self._load_raw(archive_id))
        return self.published_repository.get_publication_overview(
            archive_id,
            working_summary=working_payload["summary"],
        )

    def publish_snapshot(self, archive_id: str, *, version_label: str, publisher: str) -> dict:
        payload = self._load_for_edit(archive_id)
        published_payload = self._build_published_payload(payload)
        if published_payload["summary"]["entity_count"] + published_payload["summary"]["event_count"] + published_payload["summary"]["process_count"] == 0:
            raise ValueError("No approved knowledge items are available for publishing")

        version = self.published_repository.publish(
            archive_id,
            payload=published_payload,
            version_label=version_label,
            publisher=publisher,
        )
        return {
            "archive_id": archive_id,
            **version,
        }

    def search(self, archive_id: str, query: str) -> list[dict]:
        normalized = query.lower().strip()
        payload = self._load_public(archive_id)
        results = []
        for collection_name, item_type in ITEM_COLLECTIONS:
            for item in payload.get(collection_name, []):
                haystack = " ".join([item["name"], *item.get("aliases", [])]).lower()
                if normalized and normalized not in haystack:
                    continue
                results.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "type": item_type,
                        "category": item.get("category"),
                        "document_count": len(item.get("document_ids", [])),
                    }
                )
        return results

    def update_item(self, archive_id: str, item_id: str, *, name: str, category: str, aliases: list[str]) -> dict | None:
        payload = self._load_for_edit(archive_id)
        item_info = self._find_item_info(payload, item_id)
        if item_info is None:
            return None

        _, _, _, item = item_info
        item["name"] = name.strip()
        item["category"] = category.strip()
        item["aliases"] = self._normalize_aliases(item["name"], aliases)
        self._save_payload(archive_id, payload)
        refreshed_payload = self._load_raw(archive_id)
        refreshed_item_info = self._find_item_info(refreshed_payload, item_id)
        if refreshed_item_info is None:
            return None
        return self._build_item_detail_response(refreshed_payload, refreshed_item_info)

    def set_review_status(self, archive_id: str, item_id: str, review_status: str) -> dict | None:
        payload = self._load_for_edit(archive_id)
        item_info = self._find_item_info(payload, item_id)
        if item_info is None:
            return None

        _, _, _, item = item_info
        item["review_status"] = self._normalize_review_status(review_status)
        self._save_payload(archive_id, payload)
        refreshed_payload = self._load_raw(archive_id)
        refreshed_item_info = self._find_item_info(refreshed_payload, item_id)
        if refreshed_item_info is None:
            return None
        return self._build_item_detail_response(refreshed_payload, refreshed_item_info)

    def batch_approve(self, archive_id: str, item_ids: list[str]) -> dict:
        payload = self._load_for_edit(archive_id)
        updated_count = 0
        for item_id in item_ids:
            item_info = self._find_item_info(payload, item_id)
            if item_info is None:
                continue
            _, _, _, item = item_info
            if item.get("review_status", "pending") != "approved":
                item["review_status"] = "approved"
                updated_count += 1

        if updated_count:
            self._save_payload(archive_id, payload)
        return {"updated_count": updated_count}

    def merge_items(self, archive_id: str, primary_item_id: str, secondary_item_id: str) -> dict | None:
        payload = self._load_for_edit(archive_id)
        primary_info = self._find_item_info(payload, primary_item_id)
        secondary_info = self._find_item_info(payload, secondary_item_id)
        if primary_info is None or secondary_info is None:
            return None

        primary_collection_name, primary_item_type, _, primary_item = primary_info
        secondary_collection_name, secondary_item_type, secondary_index, secondary_item = secondary_info
        if primary_item_type != secondary_item_type:
            raise ValueError("Only knowledge items of the same type can be merged")

        primary_item["document_ids"] = self._merge_unique_strings(
            primary_item.get("document_ids", []),
            secondary_item.get("document_ids", []),
        )
        primary_item["evidence"] = self._merge_evidence(
            primary_item.get("evidence", []),
            secondary_item.get("evidence", []),
        )
        primary_item["aliases"] = self._normalize_aliases(
            primary_item["name"],
            [
                *primary_item.get("aliases", []),
                *secondary_item.get("aliases", []),
                secondary_item["name"],
            ],
        )

        payload[secondary_collection_name].pop(secondary_index)
        payload["relations"] = self._merge_relations(
            payload.get("relations", []),
            primary_item_id=primary_item_id,
            secondary_item_id=secondary_item_id,
        )

        if primary_collection_name != secondary_collection_name:
            raise ValueError("Merge target collection mismatch")

        self._save_payload(archive_id, payload)
        refreshed_payload = self._load_raw(archive_id)
        refreshed_item_info = self._find_item_info(refreshed_payload, primary_item_id)
        if refreshed_item_info is None:
            return None
        return self._build_item_detail_response(refreshed_payload, refreshed_item_info)

    def _resolve_base_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-knowledge.json"

    def _resolve_edit_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-knowledge-curated.json"

    def _resolve_read_path(self, archive_id: str) -> Path:
        curated_path = self._resolve_edit_path(archive_id)
        if curated_path.exists():
            return curated_path
        return self._resolve_base_path(archive_id)

    def _load_public(self, archive_id: str, document_ids: list[str] | None = None) -> dict:
        published_payload, publication = self.published_repository.load_latest(archive_id)
        if published_payload is not None:
            payload = published_payload
        else:
            payload = self._apply_visibility_filter(self._load_raw(archive_id))

        filtered_payload = self._apply_document_filter(payload, document_ids)
        filtered_payload["publication"] = publication
        return filtered_payload

    def _load_raw(self, archive_id: str) -> dict:
        archive_path = self._resolve_read_path(archive_id)
        payload = json.loads(archive_path.read_text(encoding="utf-8"))
        self._normalize_payload(payload)
        return payload

    def _load_for_edit(self, archive_id: str) -> dict:
        payload = self._load_raw(archive_id)
        self._normalize_payload(payload)
        return payload

    def _save_payload(self, archive_id: str, payload: dict) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._normalize_payload(payload)
        payload["summary"] = self._rebuild_summary(payload, visible_only=True)
        self._resolve_edit_path(archive_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _build_document_index(payload: dict) -> dict[str, dict]:
        return {document["id"]: document for document in payload.get("documents", [])}

    @staticmethod
    def _find_item_info(payload: dict, item_id: str) -> tuple[str, str, int, dict] | None:
        for collection_name, item_type in ITEM_COLLECTIONS:
            for index, item in enumerate(payload.get(collection_name, [])):
                if item["id"] == item_id:
                    return collection_name, item_type, index, item
        return None

    @staticmethod
    def _estimate_confidence(item: dict) -> float:
        document_count = len(item.get("document_ids", []))
        evidence_count = len(item.get("evidence", []))
        aliases = item.get("aliases", [])
        score = 0.55
        score += 0.1 * min(document_count, 3)
        score += 0.05 * min(evidence_count, 3)
        if aliases:
            score += 0.05
        return round(min(score, 0.99), 2)

    @staticmethod
    def _normalize_label(value: str) -> str:
        if not any(char in value for char in "╠╧╜ß╣╬╫╖╥╗▄"):
            return value
        try:
            return value.encode("cp437").decode("gb18030")
        except UnicodeError:
            return value

    def _normalize_payload(self, payload: dict) -> None:
        for collection_name, _ in ITEM_COLLECTIONS:
            for item in payload.get(collection_name, []):
                item["review_status"] = self._normalize_review_status(item.get("review_status"))
                item["aliases"] = self._normalize_aliases(item["name"], item.get("aliases", []))

    @staticmethod
    def _normalize_document_ids(document_ids: list[str] | None) -> list[str]:
        if not document_ids:
            return []

        normalized_ids: list[str] = []
        seen: set[str] = set()
        for document_id in document_ids:
            normalized_document_id = document_id.strip()
            if not normalized_document_id or normalized_document_id in seen:
                continue
            seen.add(normalized_document_id)
            normalized_ids.append(normalized_document_id)
        return normalized_ids

    def _apply_visibility_filter(self, payload: dict) -> dict:
        filtered = {
            "documents": payload.get("documents", []),
            "relations": [],
        }
        visible_item_ids: set[str] = set()
        visible_document_ids = {document["id"] for document in payload.get("documents", [])}

        for collection_name, _ in ITEM_COLLECTIONS:
            visible_items = [
                item
                for item in payload.get(collection_name, [])
                if item.get("review_status", "pending") != "rejected"
            ]
            filtered[collection_name] = visible_items
            visible_item_ids.update(item["id"] for item in visible_items)

        filtered["relations"] = [
            relation
            for relation in payload.get("relations", [])
            if relation.get("from") in visible_item_ids.union(visible_document_ids)
            and relation.get("to") in visible_item_ids.union(visible_document_ids)
        ]
        filtered["summary"] = self._rebuild_summary(filtered, visible_only=False)
        return filtered

    def _apply_document_filter(self, payload: dict, document_ids: list[str] | None) -> dict:
        normalized_document_ids = self._normalize_document_ids(document_ids)
        if not normalized_document_ids:
            return payload

        visible_document_ids = set(normalized_document_ids)
        filtered = {
            "documents": [
                document for document in payload.get("documents", []) if document.get("id") in visible_document_ids
            ],
            "relations": [],
        }
        visible_item_ids: set[str] = set()

        for collection_name, _ in ITEM_COLLECTIONS:
            visible_items = []
            for item in payload.get(collection_name, []):
                item_document_ids = [
                    document_id for document_id in item.get("document_ids", []) if document_id in visible_document_ids
                ]
                item_evidence = [
                    evidence
                    for evidence in item.get("evidence", [])
                    if evidence.get("document_id") in visible_document_ids
                ]
                if not item_document_ids and not item_evidence:
                    continue

                visible_item = dict(item)
                visible_item["document_ids"] = item_document_ids
                visible_item["evidence"] = item_evidence
                visible_items.append(visible_item)
                visible_item_ids.add(visible_item["id"])

            filtered[collection_name] = visible_items

        visible_relation_targets = visible_item_ids.union(visible_document_ids)
        filtered["relations"] = [
            relation
            for relation in payload.get("relations", [])
            if relation.get("from") in visible_relation_targets and relation.get("to") in visible_relation_targets
        ]
        filtered["summary"] = self._rebuild_summary(filtered, visible_only=False)
        return filtered

    def _build_published_payload(self, payload: dict) -> dict:
        filtered = {
            "documents": [],
            "relations": [],
        }
        visible_item_ids: set[str] = set()
        visible_document_ids: set[str] = set()

        for collection_name, _ in ITEM_COLLECTIONS:
            visible_items = [
                item
                for item in payload.get(collection_name, [])
                if item.get("review_status", "pending") == "approved"
            ]
            filtered[collection_name] = visible_items
            visible_item_ids.update(item["id"] for item in visible_items)
            for item in visible_items:
                visible_document_ids.update(item.get("document_ids", []))

        filtered["documents"] = [
            document
            for document in payload.get("documents", [])
            if document["id"] in visible_document_ids
        ]
        filtered["relations"] = [
            relation
            for relation in payload.get("relations", [])
            if relation.get("from") in visible_item_ids.union(visible_document_ids)
            and relation.get("to") in visible_item_ids.union(visible_document_ids)
        ]
        filtered["summary"] = self._rebuild_summary(filtered, visible_only=False)
        return filtered

    def _build_published_repository(self):
        if settings.published_knowledge_backend == "neo4j":  # pragma: no cover - optional backend
            client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            return Neo4jPublishedKnowledgeRepository(client)
        return JsonPublishedKnowledgeRepository(self.output_root)

    def _rebuild_summary(self, payload: dict, *, visible_only: bool) -> dict:
        def _items(collection_name: str) -> list[dict]:
            items = payload.get(collection_name, [])
            if not visible_only:
                return items
            return [item for item in items if item.get("review_status", "pending") != "rejected"]

        return {
            "document_count": len(payload.get("documents", [])),
            "entity_count": len(_items("entities")),
            "event_count": len(_items("events")),
            "process_count": len(_items("processes")),
        }

    @classmethod
    def _build_document_stats(cls, payload: dict) -> dict[str, dict[str, int]]:
        document_stats = {
            document["id"]: {
                "entity_count": 0,
                "event_count": 0,
                "process_count": 0,
            }
            for document in payload.get("documents", [])
        }

        for collection_name, field_name in (
            ("entities", "entity_count"),
            ("events", "event_count"),
            ("processes", "process_count"),
        ):
            for item in payload.get(collection_name, []):
                for document_id in item.get("document_ids", []):
                    if document_id in document_stats:
                        document_stats[document_id][field_name] += 1

        return document_stats

    @classmethod
    def _build_document_record(cls, document: dict, stats: dict | None) -> dict:
        normalized_stats = stats or {"entity_count": 0, "event_count": 0, "process_count": 0}
        document_id = document.get("id") or document.get("document_id")
        return {
            "id": document_id,
            "title": document["title"],
            "file_type": document["file_type"],
            "source_archive": cls._normalize_label(document["source_archive"]),
            "character_count": document["character_count"],
            "included_in_archive": document.get("included_in_archive", True),
            **normalized_stats,
            "knowledge_item_count": (
                normalized_stats["entity_count"]
                + normalized_stats["event_count"]
                + normalized_stats["process_count"]
            ),
        }

    @classmethod
    def _build_document_knowledge_items(cls, payload: dict, document_id: str, document: dict) -> list[dict]:
        knowledge_items = []
        item_type_order = {"entity": 0, "event": 1, "process": 2}

        for collection_name, item_type in ITEM_COLLECTIONS:
            for item in payload.get(collection_name, []):
                if document_id not in item.get("document_ids", []):
                    continue
                knowledge_items.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "item_type": item_type,
                        "category": item.get("category"),
                        "aliases": item.get("aliases", []),
                        "review_status": item.get("review_status", "pending"),
                        "interpretation": build_interpretation(item["name"], item.get("category", "domain_concept")),
                        "evidence": [
                            {
                                "document_id": evidence_item.get("document_id"),
                                "document_title": document["title"],
                                "excerpt": evidence_item.get("excerpt", ""),
                            }
                            for evidence_item in item.get("evidence", [])
                            if evidence_item.get("document_id") == document_id
                        ],
                    }
                )

        return sorted(knowledge_items, key=lambda item: (item_type_order[item["item_type"]], item["id"]))

    @classmethod
    def _build_document_stats_from_contribution(cls, contribution: dict) -> dict[str, int]:
        return {
            "entity_count": len(contribution.get("entities", [])),
            "event_count": len(contribution.get("events", [])),
            "process_count": len(contribution.get("processes", [])),
        }

    @classmethod
    def _build_document_knowledge_items_from_contribution(cls, contribution: dict, document: dict) -> list[dict]:
        knowledge_items = []
        item_type_order = {"entity": 0, "event": 1, "process": 2}
        collection_map = {
            "entities": "entity",
            "events": "event",
            "processes": "process",
        }

        for collection_name, item_type in collection_map.items():
            for item in contribution.get(collection_name, []):
                knowledge_items.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "item_type": item_type,
                        "category": item.get("category"),
                        "aliases": item.get("aliases", []),
                        "review_status": item.get("review_status", "pending"),
                        "interpretation": build_interpretation(item["name"], item.get("category", "domain_concept")),
                        "evidence": [
                            {
                                "document_id": evidence_item.get("document_id"),
                                "document_title": document["title"],
                                "excerpt": evidence_item.get("excerpt", ""),
                            }
                            for evidence_item in item.get("evidence", [])
                        ],
                    }
                )

        return sorted(knowledge_items, key=lambda item: (item_type_order[item["item_type"]], item["id"]))

    @classmethod
    def _build_item_documents(cls, item: dict, document_index: dict[str, dict]) -> list[dict]:
        documents = []
        for document_id in item.get("document_ids", []):
            document = document_index.get(document_id)
            if not document:
                continue
            documents.append(
                {
                    "id": document["id"],
                    "title": document["title"],
                    "file_type": document["file_type"],
                    "source_archive": cls._normalize_label(document["source_archive"]),
                }
            )
        return documents

    @staticmethod
    def _build_item_evidence(item: dict, document_index: dict[str, dict]) -> list[dict]:
        evidence = []
        for evidence_item in item.get("evidence", []):
            document = document_index.get(evidence_item.get("document_id"))
            evidence.append(
                {
                    "document_id": evidence_item.get("document_id"),
                    "document_title": document["title"] if document else None,
                    "excerpt": evidence_item.get("excerpt", ""),
                }
            )
        return evidence

    def _build_item_detail_response(
        self,
        payload: dict,
        item_info: tuple[str, str, int, dict],
    ) -> dict:
        _, item_type, _, item = item_info
        document_index = self._build_document_index(payload)
        documents = self._build_item_documents(item, document_index)
        evidence = self._build_item_evidence(item, document_index)
        related_items = self._build_related_items(payload, item["id"])
        relationship_sections = self._build_relationship_sections(payload, item["id"])
        interpretation = build_interpretation(item["name"], item.get("category", "domain_concept"))

        return {
            "id": item["id"],
            "name": item["name"],
            "item_type": item_type,
            "category": item.get("category"),
            "aliases": item.get("aliases", []),
            "review_status": item.get("review_status", "pending"),
            "document_count": len(item.get("document_ids", [])),
            "interpretation": interpretation,
            "language_projection": build_language_projection(
                name=item["name"],
                aliases=item.get("aliases", []),
                interpretation=interpretation,
                evidence=evidence,
            ),
            "documents": documents,
            "evidence": evidence,
            "related_items": related_items,
            "relationship_sections": relationship_sections,
        }

    @staticmethod
    def _with_language_projection(item: dict) -> dict:
        return {
            **item,
            "language_projection": build_language_projection(
                name=item["name"],
                aliases=item.get("aliases", []),
                interpretation=item["interpretation"],
                evidence=item.get("evidence", []),
            ),
        }

    def _build_related_items(self, payload: dict, item_id: str) -> list[dict]:
        related_items = []
        seen_relations: set[tuple[str, str]] = set()
        for relation in payload.get("relations", []):
            if relation.get("type") == "document_mentions":
                continue
            if relation.get("from") == item_id:
                related_item_id = relation.get("to")
            elif relation.get("to") == item_id:
                related_item_id = relation.get("from")
            else:
                continue

            related_info = self._find_item_info(payload, related_item_id)
            if related_info is None:
                continue

            _, related_type, _, related_item = related_info
            relation_key = (relation["type"], related_item["id"])
            if relation_key in seen_relations:
                continue

            seen_relations.add(relation_key)
            related_items.append(
                {
                    "id": related_item["id"],
                    "name": related_item["name"],
                    "item_type": related_type,
                    "relation_type": relation["type"],
                }
            )

        return related_items

    def _build_relationship_sections(self, payload: dict, item_id: str) -> list[dict]:
        sections: dict[str, dict] = {}
        item_type_order = {"entity": 0, "event": 1, "process": 2}

        for relation in payload.get("relations", []):
            if relation.get("type") == "document_mentions":
                continue

            if relation.get("from") == item_id:
                related_item_id = relation.get("to")
                direction = "outgoing"
            elif relation.get("to") == item_id:
                related_item_id = relation.get("from")
                direction = "incoming"
            else:
                continue

            related_info = self._find_item_info(payload, related_item_id)
            if related_info is None:
                continue

            _, related_type, _, related_item = related_info
            section_key, section_title, relation_label = RELATION_SECTION_DEFINITIONS.get(
                (relation["type"], direction),
                ("other", "其他直接关联", relation["type"]),
            )
            section = sections.setdefault(section_key, {"key": section_key, "title": section_title, "items": []})
            section["items"].append(
                {
                    "id": related_item["id"],
                    "name": related_item["name"],
                    "item_type": related_type,
                    "relation_type": relation["type"],
                    "relation_label": relation_label,
                    "direction": direction,
                    "evidence": relation.get("evidence"),
                }
            )

        ordered_sections = []
        for section_key in RELATION_SECTION_ORDER:
            section = sections.get(section_key)
            if section is None:
                continue
            section["items"] = sorted(
                section["items"],
                key=lambda item: (item_type_order.get(item["item_type"], 99), item["name"]),
            )
            ordered_sections.append(section)

        for section_key, section in sections.items():
            if section_key in RELATION_SECTION_ORDER:
                continue
            section["items"] = sorted(
                section["items"],
                key=lambda item: (item_type_order.get(item["item_type"], 99), item["name"]),
            )
            ordered_sections.append(section)

        return ordered_sections

    @staticmethod
    def _normalize_review_status(value: str | None) -> str:
        if value in VALID_REVIEW_STATUSES:
            return value
        return "pending"

    @staticmethod
    def _normalize_aliases(name: str, aliases: list[str]) -> list[str]:
        normalized_name = name.strip()
        normalized_aliases = []
        seen: set[str] = set()
        for value in aliases:
            alias = value.strip()
            if not alias or alias == normalized_name or alias in seen:
                continue
            seen.add(alias)
            normalized_aliases.append(alias)
        return normalized_aliases

    @staticmethod
    def _merge_unique_strings(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for values in groups:
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                merged.append(value)
        return merged

    @staticmethod
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

    @staticmethod
    def _merge_relations(relations: list[dict], *, primary_item_id: str, secondary_item_id: str) -> list[dict]:
        merged_relations: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for relation in relations:
            source_id = primary_item_id if relation.get("from") == secondary_item_id else relation.get("from")
            target_id = primary_item_id if relation.get("to") == secondary_item_id else relation.get("to")
            if source_id == target_id:
                continue

            relation_key = (relation["type"], source_id, target_id)
            if relation_key in seen:
                continue

            seen.add(relation_key)
            merged_relations.append(
                {
                    **relation,
                    "from": source_id,
                    "to": target_id,
                }
            )
        return merged_relations
