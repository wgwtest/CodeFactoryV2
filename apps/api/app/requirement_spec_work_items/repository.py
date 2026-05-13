from __future__ import annotations

from sqlalchemy import select

from app.db.models.requirements import RequirementSpecWorkItem


class RequirementSpecWorkItemRepository:
    def __init__(self, session) -> None:
        self.session = session

    def list_items(self) -> list[RequirementSpecWorkItem]:
        return self.session.scalars(
            select(RequirementSpecWorkItem).order_by(RequirementSpecWorkItem.updated_at.desc())
        ).all()

    def get_item(self, spec_item_id: str) -> RequirementSpecWorkItem | None:
        return self.session.get(RequirementSpecWorkItem, spec_item_id)

    def add_item(self, item: RequirementSpecWorkItem) -> RequirementSpecWorkItem:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def save_item(self, item: RequirementSpecWorkItem) -> RequirementSpecWorkItem:
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete_item(self, item: RequirementSpecWorkItem) -> None:
        self.session.delete(item)
        self.session.commit()
