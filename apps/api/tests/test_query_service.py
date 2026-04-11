from app.query.service import QueryService


def test_query_service_returns_graph_and_process_views(db_session) -> None:
    query_service = QueryService(db_session)
    query_service.seed_knowledge_graph_for_test()

    graph = query_service.get_graph("v1")
    processes = query_service.get_processes("v1")

    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1
    assert processes[0]["steps"][0]["label"] == "Submit Incident Report"


def test_search_returns_only_published_items_for_requested_version(db_session) -> None:
    query_service = QueryService(db_session)
    query_service.seed_knowledge_graph_for_test()

    results = query_service.search(version_label="v1", query="incident")

    assert all(item["version_label"] == "v1" for item in results)
    assert any(item["canonical_name"] == "Incident Report" for item in results)
