from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.software_build.models import (
    P5AssemblyAttempt,
    P5DeliveryOrder,
    P5DesignInputSource,
    P5SupplyInputSource,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class SoftwareBuildRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.orders_dir = self.root / "orders"
        self.attempts_dir = self.root / "attempts"
        self.design_inputs_dir = self.root / "design-inputs"
        self.supply_inputs_dir = self.root / "supply-inputs"
        self.exports_dir = self.root / "exports"
        for directory in (
            self.orders_dir,
            self.attempts_dir,
            self.design_inputs_dir,
            self.supply_inputs_dir,
            self.exports_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def list_orders(self) -> list[P5DeliveryOrder]:
        return sorted(self._read_models(self.orders_dir, P5DeliveryOrder), key=lambda item: item.updated_at, reverse=True)

    def get_order(self, delivery_order_id: str) -> P5DeliveryOrder | None:
        return self._read_model(self.orders_dir / f"{delivery_order_id}.json", P5DeliveryOrder)

    def get_order_by_p3_order_id(self, p3_order_id: str) -> P5DeliveryOrder | None:
        for order in self.list_orders():
            if order.p3_order_id == p3_order_id:
                return order
        return None

    def get_order_by_design_input_id(self, design_input_id: str) -> P5DeliveryOrder | None:
        for order in self.list_orders():
            if order.active_input_binding.design_input_id == design_input_id:
                return order
        return None

    def save_order(self, order: P5DeliveryOrder) -> P5DeliveryOrder:
        self._write_json(self.orders_dir / f"{order.delivery_order_id}.json", order.model_dump(mode="json"))
        return order

    def list_attempts(self, delivery_order_id: str | None = None) -> list[P5AssemblyAttempt]:
        attempts = sorted(
            self._read_models(self.attempts_dir, P5AssemblyAttempt),
            key=lambda item: (item.delivery_order_id, item.sequence),
        )
        if delivery_order_id is None:
            return attempts
        return [attempt for attempt in attempts if attempt.delivery_order_id == delivery_order_id]

    def get_attempt(self, attempt_id: str) -> P5AssemblyAttempt | None:
        return self._read_model(self.attempts_dir / f"{attempt_id}.json", P5AssemblyAttempt)

    def save_attempt(self, attempt: P5AssemblyAttempt) -> P5AssemblyAttempt:
        self._write_json(self.attempts_dir / f"{attempt.attempt_id}.json", attempt.model_dump(mode="json"))
        return attempt

    def clear_delivery_runtime(self) -> tuple[int, int]:
        cleared_order_count = self._clear_json_directory(self.orders_dir)
        cleared_attempt_count = self._clear_json_directory(self.attempts_dir)
        shutil.rmtree(self.exports_dir, ignore_errors=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        return cleared_order_count, cleared_attempt_count

    def list_design_inputs(self) -> list[P5DesignInputSource]:
        return sorted(
            self._read_models(self.design_inputs_dir, P5DesignInputSource),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def get_design_input(self, design_input_id: str) -> P5DesignInputSource | None:
        return self._read_model(self.design_inputs_dir / f"{design_input_id}.json", P5DesignInputSource)

    def save_design_input(self, design_input: P5DesignInputSource) -> P5DesignInputSource:
        self._write_json(self.design_inputs_dir / f"{design_input.design_input_id}.json", design_input.model_dump(mode="json"))
        return design_input

    def list_supply_inputs(self) -> list[P5SupplyInputSource]:
        return sorted(
            self._read_models(self.supply_inputs_dir, P5SupplyInputSource),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def get_supply_input(self, supply_input_id: str) -> P5SupplyInputSource | None:
        return self._read_model(self.supply_inputs_dir / f"{supply_input_id}.json", P5SupplyInputSource)

    def save_supply_input(self, supply_input: P5SupplyInputSource) -> P5SupplyInputSource:
        self._write_json(self.supply_inputs_dir / f"{supply_input.supply_input_id}.json", supply_input.model_dump(mode="json"))
        return supply_input

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

    def _clear_json_directory(self, directory: Path) -> int:
        paths = list(directory.glob("*.json"))
        for path in paths:
            path.unlink()
        return len(paths)
