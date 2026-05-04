from __future__ import annotations

from sqlalchemy import select

from app.db.models.requirements import RequirementSpec


class RequirementSpecRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add_spec(self, spec: RequirementSpec) -> RequirementSpec:
        self.session.add(spec)
        self.session.commit()
        self.session.refresh(spec)
        return spec

    def save_spec(self, spec: RequirementSpec) -> RequirementSpec:
        self.session.commit()
        self.session.refresh(spec)
        return spec

    def get_spec(self, spec_id: str) -> RequirementSpec | None:
        return self.session.get(RequirementSpec, spec_id)

    def list_specs(self) -> list[RequirementSpec]:
        return self.session.scalars(select(RequirementSpec).order_by(RequirementSpec.updated_at.desc())).all()
