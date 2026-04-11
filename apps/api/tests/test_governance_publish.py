from app.governance.service import GovernanceService


def test_publish_creates_knowledge_version_from_approved_candidates(db_session) -> None:
    service = GovernanceService(db_session)
    candidate_ids = service.seed_candidates_for_test()

    service.approve(candidate_ids[0], reviewer="architect")
    published = service.publish(version_label="v1", publisher="architect")

    assert published.version_label == "v1"
    assert published.status == "published"
    assert service.list_published_items("v1")
