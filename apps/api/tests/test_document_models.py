from app.db.models.document import Document, DocumentVersion
from app.db.models.knowledge import CandidateItem, KnowledgeItem, KnowledgeVersion


def test_candidate_and_published_knowledge_use_separate_tables(db_session) -> None:
    document = Document(title="Minimal Policy", source_name="fixture")
    db_session.add(document)
    db_session.flush()

    version = DocumentVersion(document_id=document.id, version_number=1, file_name="policy.pdf")
    db_session.add(version)
    db_session.flush()

    candidate = CandidateItem(
        document_version_id=version.id,
        item_type="entity",
        canonical_name="Incident",
        status="extracted",
    )
    published_version = KnowledgeVersion(version_label="v1", status="published")
    db_session.add_all([candidate, published_version])
    db_session.flush()

    published = KnowledgeItem(
        knowledge_version_id=published_version.id,
        item_type="entity",
        canonical_name="Incident",
        status="published",
    )
    db_session.add(published)
    db_session.commit()

    assert db_session.query(CandidateItem).count() == 1
    assert db_session.query(KnowledgeItem).count() == 1
    assert candidate.id != published.id
