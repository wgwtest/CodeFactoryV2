from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from app.tool_hub.demand_fixtures import build_mock_blue_force_request, build_mock_demand_request
from app.tool_hub.models import (
    ItemProgressView,
    ToolDemandItem,
    ToolDemandReviewDecisionRequest,
    ToolDemandSheet,
    ToolDemandSheetActionRequest,
    ToolDemandSheetCreateRequest,
    ToolDemandSheetDetail,
    ToolDemandSheetEnvelope,
    ToolDemandTestingClearResult,
    now_iso,
)

TERMINAL_SHEET_LIFECYCLE_STATUSES = {"rejected", "withdrawn", "closed"}

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class DemandService:
    def __init__(self, hub: "ToolHubService") -> None:
        self.hub = hub
        self.repository = hub.repository

    def create_mock_blue_force_demand_sheet(self) -> ToolDemandSheetDetail:
        return self.create_demand_sheet(build_mock_blue_force_request())

    def create_mock_demand_sheet(self, scenario_id: str) -> ToolDemandSheetDetail:
        return self.create_demand_sheet(build_mock_demand_request(scenario_id))

    def create_demand_sheet(self, payload: ToolDemandSheetCreateRequest) -> ToolDemandSheetDetail:
        sheet_id = f"tds-{uuid4().hex[:12]}"
        items = [self.hub._process_demand_item(item) for item in self.hub._build_demand_items(sheet_id, payload.root_node)]
        for item in items:
            self.repository.save_demand_item(item)

        submitted_event = self.hub._build_lifecycle_event(
            event_type="submitted",
            actor_phase=payload.requested_by,
            actor_id=payload.source.producer,
            from_status=None,
            to_status="submitted",
            reason_code="sheet_submitted",
            reason_message="需求方已提交工具需求单。",
        )
        accepted_event = self.hub._build_lifecycle_event(
            event_type="accepted",
            actor_phase="P4",
            actor_id="p4-system",
            from_status="submitted",
            to_status="accepted",
            reason_code="sheet_accepted",
            reason_message="P4 已受理当前工具需求单。",
        )
        sheet = ToolDemandSheet(
            sheet_id=sheet_id,
            sheet_name=payload.sheet_name,
            lifecycle_status="accepted",
            review_status="pending_review",
            delivery_status="not_delivered",
            processing_status="not_started",
            source=payload.source,
            requested_by=payload.requested_by,
            business_case=payload.source.business_case,
            root_node=payload.root_node,
            item_ids=[item.item_id for item in items],
            item_count=len(items),
            lifecycle_events=[submitted_event, accepted_event],
            last_actor_phase="P4",
            last_actor_id="p4-system",
        )
        refreshed = self.hub._refresh_sheet(sheet, items)
        self.repository.save_demand_sheet(refreshed)
        return ToolDemandSheetDetail(**refreshed.model_dump(mode="json"), items=items)

    def list_demand_sheets(self) -> ToolDemandSheetEnvelope:
        sheets = [self.hub._refresh_sheet(sheet) for sheet in self.repository.list_demand_sheets()]
        return ToolDemandSheetEnvelope(items=sheets)

    def get_demand_sheet(self, sheet_id: str) -> ToolDemandSheetDetail | None:
        sheet = self.repository.get_demand_sheet(sheet_id)
        if sheet is None:
            return None
        items = self.hub._get_sheet_items(sheet)
        refreshed = self.hub._refresh_sheet(sheet, items)
        if refreshed.model_dump(mode="json") != sheet.model_dump(mode="json"):
            self.repository.save_demand_sheet(refreshed)
        return ToolDemandSheetDetail(**refreshed.model_dump(mode="json"), items=items)

    def get_demand_item(self, item_id: str) -> ToolDemandItem | None:
        return self.repository.get_demand_item(item_id)

    def review_demand_item(
        self,
        item_id: str,
        payload: ToolDemandReviewDecisionRequest,
    ) -> ToolDemandItem | None:
        item = self.repository.get_demand_item(item_id)
        if item is None:
            return None

        sheet = self.repository.get_demand_sheet(item.sheet_id)
        if sheet is None:
            return None
        if sheet.lifecycle_status in TERMINAL_SHEET_LIFECYCLE_STATUSES:
            raise ValueError("Demand sheet is already in terminal status")
        if item.review_status != "pending_review":
            raise ValueError("Demand item is already reviewed")

        review_update = {
            "importance_score": payload.importance_score,
            "urgency_score": payload.urgency_score,
            "rationality_verdict": payload.rationality_verdict,
            "review_comment": payload.review_comment,
            "reviewed_by": payload.reviewed_by,
            "reviewed_at": now_iso(),
            "updated_at": now_iso(),
        }

        if payload.decision == "approve_delivery":
            if item.recommendation_type != "existing_tool" or not item.recommended_tool_id:
                raise ValueError("Current demand item is not eligible for direct delivery")
            tool = self.repository.get_tool(item.recommended_tool_id)
            if tool is None:
                raise ValueError("Recommended tool is no longer available")
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "approved_delivery",
                    "processing_status": "matched_existing",
                    "supply_result": self.hub._build_existing_tool_supply_result(item, tool),
                }
            )
        elif payload.decision == "approve_manufacture":
            if item.recommendation_type != "manufacture_candidate":
                raise ValueError("Current demand item is not eligible for manufacture approval")
            plan = self.repository.get_manufacture_plan(item.item_id)
            if plan is None:
                plan = self.hub._build_manufacture_plan(item)
                self.repository.save_manufacture_plan(plan)
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "approved_manufacture",
                    "processing_status": "manufacturing_pending",
                    "supply_result": self.hub._build_pending_manufacture_supply_result(item, plan),
                }
            )
            self.hub.runtime_service.enqueue_manufacture_job(plan, payload.reviewed_by)
        else:
            updated_item = item.model_copy(
                update={
                    **review_update,
                    "review_status": "rejected",
                    "supply_result": None,
                }
            )

        self.repository.save_demand_item(updated_item)
        self.hub._refresh_sheet_for_item(updated_item)
        return self.repository.get_demand_item(item_id)

    def withdraw_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        return self.hub._transition_demand_sheet(
            sheet_id=sheet_id,
            event_type="withdrawn",
            actor_phase=payload.actor_phase or "P3",
            actor_id=payload.actor_id,
            reason_code=payload.reason_code,
            reason_message=payload.reason_message,
        )

    def reject_demand_sheet(
        self,
        sheet_id: str,
        payload: ToolDemandSheetActionRequest,
    ) -> ToolDemandSheetDetail | None:
        return self.hub._transition_demand_sheet(
            sheet_id=sheet_id,
            event_type="rejected",
            actor_phase=payload.actor_phase or "P4",
            actor_id=payload.actor_id,
            reason_code=payload.reason_code,
            reason_message=payload.reason_message,
        )

    def clear_demand_chain_for_testing(self) -> ToolDemandTestingClearResult:
        cleared_sheet_count, cleared_item_count, cleared_manufacture_plan_count = (
            self.repository.clear_demand_chain_runtime()
        )
        return ToolDemandTestingClearResult(
            cleared_sheet_count=cleared_sheet_count,
            cleared_item_count=cleared_item_count,
            cleared_manufacture_plan_count=cleared_manufacture_plan_count,
        )

    def get_demand_item_progress(self, item_id: str) -> ItemProgressView | None:
        item = self.repository.get_demand_item(item_id)
        if item is None:
            return None

        sheet = self.repository.get_demand_sheet(item.sheet_id)
        return self.hub._build_progress_view(item, sheet)
