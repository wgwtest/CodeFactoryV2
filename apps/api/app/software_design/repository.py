from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.software_design.models import ModuleWorkorderBatchPackage, P3Order, ReviewThread, SoftwareDesignBaseline

ModelT = TypeVar("ModelT", bound=BaseModel)


class SoftwareDesignRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.orders_dir = self.root / "orders"
        self.baselines_dir = self.root / "baselines"
        self.review_threads_dir = self.root / "review_threads"
        self.packages_dir = self.root / "packages"
        self.pushes_dir = self.root / "pushes"
        self.reference_assets_dir = self.root / "reference_assets"
        for directory in (
            self.orders_dir,
            self.baselines_dir,
            self.review_threads_dir,
            self.packages_dir,
            self.pushes_dir,
            self.reference_assets_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def list_orders(self) -> list[P3Order]:
        return sorted(self._read_models(self.orders_dir, P3Order), key=lambda item: item.updated_at, reverse=True)

    def get_order(self, order_id: str) -> P3Order | None:
        return self._read_model(self.orders_dir / f"{order_id}.json", P3Order)

    def get_order_by_requirement_spec_id(self, requirement_spec_id: str) -> P3Order | None:
        for order in self.list_orders():
            if order.requirement_spec_id == requirement_spec_id:
                return order
        return None

    def save_order(self, order: P3Order) -> P3Order:
        self._write_json(self.orders_dir / f"{order.order_id}.json", order.model_dump(mode="json"))
        return order

    def get_baseline(self, order_id: str) -> SoftwareDesignBaseline | None:
        return self._read_model(self.baselines_dir / f"{order_id}.json", SoftwareDesignBaseline)

    def save_baseline(self, baseline: SoftwareDesignBaseline) -> SoftwareDesignBaseline:
        self._write_json(self.baselines_dir / f"{baseline.order_id}.json", baseline.model_dump(mode="json"))
        return baseline

    def list_review_threads(self, order_id: str) -> list[ReviewThread]:
        return sorted(
            [thread for thread in self._read_models(self.review_threads_dir, ReviewThread) if thread.order_id == order_id],
            key=lambda item: item.updated_at,
        )

    def save_review_thread(self, thread: ReviewThread) -> ReviewThread:
        self._write_json(self.review_threads_dir / f"{thread.thread_id}.json", thread.model_dump(mode="json"))
        return thread

    def get_package(self, order_id: str) -> ModuleWorkorderBatchPackage | None:
        return self._read_model(self.packages_dir / f"{order_id}.json", ModuleWorkorderBatchPackage)

    def list_packages(self) -> list[ModuleWorkorderBatchPackage]:
        return sorted(
            self._read_models(self.packages_dir, ModuleWorkorderBatchPackage),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def save_package(self, package: ModuleWorkorderBatchPackage) -> ModuleWorkorderBatchPackage:
        self._write_json(self.packages_dir / f"{package.order_id}.json", package.model_dump(mode="json"))
        return package

    def save_push_record(self, order_id: str, payload: dict[str, str]) -> dict[str, str]:
        self._write_json(self.pushes_dir / f"{order_id}.json", payload)
        return payload

    def _read_models(self, directory: Path, model_type: type[ModelT]) -> list[ModelT]:
        items: list[ModelT] = []
        for path in sorted(directory.glob("*.json")):
            items.append(model_type.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items

    def _read_model(self, path: Path, model_type: type[ModelT]) -> ModelT | None:
        if not path.exists():
            return None
        return model_type.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
