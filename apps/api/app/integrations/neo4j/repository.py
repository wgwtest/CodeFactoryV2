from __future__ import annotations


class Neo4jPublishedKnowledgeRepository:
    def __init__(self, client) -> None:
        self.client = client

    def load_latest(self, archive_id: str):  # pragma: no cover - optional backend
        del archive_id
        return None, None

    def get_publication_overview(self, archive_id: str, *, working_summary: dict):  # pragma: no cover - optional backend
        return {
            "archive_id": archive_id,
            "current_version": None,
            "versions": [],
            "working_summary": working_summary,
        }

    def publish(self, archive_id: str, *, payload: dict, version_label: str, publisher: str):  # pragma: no cover - optional backend
        del archive_id, payload
        return {
            "version_label": version_label,
            "publisher": publisher,
            "published_at": None,
            "summary": {},
        }
