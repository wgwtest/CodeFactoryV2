from __future__ import annotations

from app.db.models.knowledge import KnowledgeItem, KnowledgeVersion


class QueryService:
    def __init__(self, session) -> None:
        self.session = session

    def seed_knowledge_graph_for_test(self) -> None:
        version = KnowledgeVersion(version_label="v1", status="published")
        self.session.add(version)
        self.session.flush()

        incident = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="entity",
            canonical_name="Incident Report",
            status="published",
            payload={},
        )
        self.session.add(incident)
        self.session.flush()

        process = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="process",
            canonical_name="Incident Closure Review",
            status="published",
            payload={"steps": [{"label": "Submit Incident Report"}, {"label": "Verify Evidence"}]},
        )
        relation = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="event",
            canonical_name="Submit Incident Report",
            status="published",
            payload={"relation_to": {"target_id": incident.id, "type": "changes"}},
        )
        self.session.add_all([process, relation])
        self.session.commit()

    def get_graph(self, version_label: str) -> dict:
        items = (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label)
            .all()
        )

        nodes = [{"id": item.id, "label": item.canonical_name, "type": item.item_type} for item in items]
        edges = []
        for item in items:
            relation = item.payload.get("relation_to")
            if relation:
                edges.append({"source": item.id, "target": relation["target_id"], "label": relation["type"]})
        return {"nodes": nodes, "edges": edges}

    def get_processes(self, version_label: str) -> list[dict]:
        items = (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label, KnowledgeItem.item_type == "process")
            .all()
        )
        return [{"id": item.id, "name": item.canonical_name, "steps": item.payload.get("steps", [])} for item in items]

    def search(self, version_label: str, query: str) -> list[dict]:
        items = (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label)
            .filter(KnowledgeItem.canonical_name.ilike(f"%{query}%"))
            .all()
        )
        return [
            {
                "id": item.id,
                "canonical_name": item.canonical_name,
                "item_type": item.item_type,
                "version_label": version_label,
            }
            for item in items
        ]
