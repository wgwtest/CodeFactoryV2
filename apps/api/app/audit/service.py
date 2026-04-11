from app.db.models.knowledge import AuditLog


class AuditService:
    def __init__(self, session) -> None:
        self.session = session

    def record(self, action: str, actor: str, payload: dict) -> None:
        self.session.add(AuditLog(action=action, actor=actor, payload=payload))
        self.session.commit()
