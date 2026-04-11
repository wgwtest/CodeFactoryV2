from fastapi.testclient import TestClient

from app.db.models.knowledge import AuditLog
from app.main import create_app


def test_publish_requires_publisher_role(db_session) -> None:
    client = TestClient(create_app())

    response = client.post("/api/governance/publish?version_label=v1&publisher=analyst")

    assert response.status_code == 403


def test_successful_publish_writes_audit_log(db_session) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/governance/publish?version_label=v1&publisher=architect",
        headers={"X-Role": "publisher"},
    )

    assert response.status_code in {200, 201}
    logs = db_session.query(AuditLog).all()
    assert any(log.action == "publish_knowledge" for log in logs)
