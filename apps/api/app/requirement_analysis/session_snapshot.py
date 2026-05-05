from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    topic: str
    orchestrator_id: str
    provider_id: str
    model: str
    template_id: str
    knowledge_package_id: str
    write_policy: str
    status: str
    payload: dict
