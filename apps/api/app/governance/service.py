from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.knowledge import CandidateItem, KnowledgeItem, KnowledgeVersion


class GovernanceService:
    def __init__(self, session) -> None:
        self.session = session

    def seed_candidates_for_test(self) -> list[str]:
        candidate = CandidateItem(
            document_version_id="seed-version",
            item_type="entity",
            canonical_name="Incident Report",
            status="extracted",
            confidence=0.91,
            review_status="pending",
            payload={"evidence": {"section": "Section 2"}},
        )
        self.session.add(candidate)
        self.session.commit()
        return [candidate.id]

    def approve(self, candidate_id: str, reviewer: str) -> None:
        candidate = self.session.get(CandidateItem, candidate_id)
        candidate.review_status = "approved"
        candidate.payload = {**candidate.payload, "reviewed_by": reviewer}
        self.session.commit()

    def publish(self, version_label: str, publisher: str) -> KnowledgeVersion:
        version = KnowledgeVersion(version_label=version_label, status="published")
        self.session.add(version)
        self.session.flush()

        approved = self.session.query(CandidateItem).filter_by(review_status="approved").all()
        for candidate in approved:
            self.session.add(
                KnowledgeItem(
                    knowledge_version_id=version.id,
                    item_type=candidate.item_type,
                    canonical_name=candidate.canonical_name,
                    status="published",
                    payload={
                        **candidate.payload,
                        "published_by": publisher,
                        "published_at": datetime.now(UTC).isoformat(),
                    },
                )
            )

        self.session.commit()
        return version

    def list_published_items(self, version_label: str) -> list[KnowledgeItem]:
        return (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label)
            .all()
        )
