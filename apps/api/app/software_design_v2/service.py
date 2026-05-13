from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument
from app.software_design_v2.models import P3DesignSessionCreate, P3DesignTurnWrite


class SoftwareDesignV2Service:
    _sessions: dict[str, dict] = {}

    def __init__(self, session) -> None:
        self.session = session

    def list_input_packages(self) -> dict:
        documents = self.session.scalars(
            select(RequirementAuthoringDocument).order_by(RequirementAuthoringDocument.updated_at.desc())
        ).all()
        items = [
            self._build_input_package(document)
            for document in documents
            if document.frozen_package and document.frozen_package.get("p3_consumable") is True
        ]
        return {"items": items}

    def create_session(self, payload: P3DesignSessionCreate) -> dict:
        input_package = self._get_input_package(payload.input_package_id)
        session_id = f"p3dl-{uuid4().hex[:10]}"
        design_session = {
            "session_id": session_id,
            "input_package": input_package,
            "generation_policy": {
                "architecture_preference": payload.generation_policy.get(
                    "architecture_preference",
                    "统一服务优先，保留拆分点",
                ),
                "module_granularity": payload.generation_policy.get("module_granularity", "3-5 个业务模块，不拆太细"),
                "output_style": payload.generation_policy.get("output_style", "按标准软设正文写，不写聊天语气"),
            },
            "status": "created",
            "design_document": None,
            "design_baseline": None,
            "workorder_projection": None,
            "turns": [],
            "check_result": None,
            "frozen_package": None,
            "runtime_events": [self._build_runtime_event("session_created", "创建设计会话")],
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._sessions[session_id] = design_session
        return design_session

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def generate(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None

        structured_spec = design_session["input_package"]["structured_spec"]
        app_name = structured_spec.get("application", {}).get("name") or "未命名软件"
        design_session["design_document"] = self._build_design_document(app_name)
        design_session["design_baseline"] = self._build_design_baseline(app_name)
        design_session["workorder_projection"] = self._build_workorder_projection()
        design_session["status"] = "baseline_ready"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("generate", "生成软件设计说明、设计基线和 P4 投影"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def append_turn(self, session_id: str, payload: P3DesignTurnWrite) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["design_baseline"] is None:
            self.generate(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None

        user_input = payload.user_input.strip()
        normalized_intent = "add_state_machine" if "状态" in user_input else "refine_design"
        turn = {
            "turn_id": f"p3turn-{uuid4().hex[:10]}",
            "user_input": user_input,
            "normalized_intent": normalized_intent,
            "source_clause_refs": ["REQ-3.2", "REQ-4.1"],
            "target_design_sections": ["SDD-4"],
            "assistant_message": "已补入状态机说明，并将告警反馈时间保留为待确认项。",
            "quick_options": ["继续细化接口", "保守一点", "生成工单预览"],
            "design_patch": {
                "patch_id": f"p3dp-{uuid4().hex[:8]}",
                "section_updates": [
                    {
                        "section_id": "interfaces",
                        "content": "补充规划任务、冲突告警、协同确认的状态流转说明。",
                    }
                ],
                "workorder_updates": ["规划任务管理", "冲突识别与告警"],
            },
            "validation_result": {"valid": True, "warnings": ["告警反馈时间仍需人工确认"]},
            "created_at": self._now(),
        }
        design_session["turns"] = [*design_session["turns"], turn]
        design_session["design_baseline"]["pending_confirmations"] = ["告警反馈时间和状态历史粒度需人工确认。"]
        design_session["design_document"]["sections"] = [
            *design_session["design_document"]["sections"],
            {
                "section_id": "state-machine",
                "title": "4. 状态机与接口约束",
                "content": "规划任务在草稿、冲突识别、协同确认、已归档之间流转，关键状态变化必须留痕。",
                "status": "generated",
            },
        ]
        design_session["status"] = "patch_ready"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("turn", f"追加设计回合：{normalized_intent}"),
        ]
        self._refresh_related_designs(design_session)
        return {"turn": turn, "session": design_session}

    def run_check(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["design_baseline"] is None:
            self.generate(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None
        check_result = {
            "blocking_count": 0,
            "warning_count": len(design_session["design_baseline"].get("pending_confirmations", [])),
            "passed_count": 4,
            "items": [
                {"severity": "passed", "message": "软件设计说明正文已生成。"},
                {"severity": "passed", "message": "结构化设计基线已生成。"},
                {"severity": "passed", "message": "P4 工单投影已生成。"},
                {"severity": "passed", "message": "需求到设计追溯已生成。"},
            ],
        }
        design_session["check_result"] = check_result
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("check", "运行设计完整性检查"),
        ]
        self._refresh_related_designs(design_session)
        return {"session_id": session_id, "check_result": check_result, "session": design_session}

    def save_draft(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["design_baseline"] is None:
            self.generate(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None
        design_session["status"] = "draft_saved"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("save", "保存软件设计说明草稿"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def generate_projection(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["design_baseline"] is None:
            self.generate(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None
        design_session["workorder_projection"] = self._build_workorder_projection()
        design_session["status"] = "projection_ready"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("projection", "生成 P4 工单投影候选"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def freeze(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["design_baseline"] is None:
            self.generate(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None
        if design_session["check_result"] is None:
            self.run_check(session_id)
            design_session = self.get_session(session_id)
            if design_session is None:
                return None
        if design_session["check_result"]["blocking_count"] > 0:
            raise ValueError("P3 design session has blocking check items")

        design_session["status"] = "frozen"
        design_session["frozen_package"] = self._build_frozen_package(design_session)
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("freeze", "冻结软件设计基线和设计包"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def delete_session(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["status"] == "frozen":
            raise ValueError("frozen P3 design session cannot be deleted")
        del self._sessions[session_id]
        return {"deleted_session_id": session_id}

    def _get_input_package(self, input_package_id: str) -> dict:
        packages = self.list_input_packages()["items"]
        for package in packages:
            if package["input_package_id"] == input_package_id:
                return package
        raise ValueError("P3 v2 input package not found")

    def _build_input_package(self, document: RequirementAuthoringDocument) -> dict:
        frozen_package = document.frozen_package or {}
        return {
            "input_package_id": f"p2frozen-{document.id}",
            "source_document_id": document.id,
            "source_title": document.title,
            "standard_document": frozen_package.get("standard_document", document.document),
            "structured_spec": frozen_package.get("structured_spec", {}),
            "annotations": frozen_package.get("annotations", document.annotations),
            "knowledge_binding": (document.semantic_state or {}).get("knowledge_binding"),
            "frozen_at": frozen_package.get("frozen_at"),
            "p3_consumable": frozen_package.get("p3_consumable") is True,
            "related_designs": self._list_related_designs(f"p2frozen-{document.id}"),
        }

    def _list_related_designs(self, input_package_id: str) -> list[dict]:
        related_designs = []
        for design_session in self._sessions.values():
            if (
                design_session.get("input_package", {}).get("input_package_id") == input_package_id
                and design_session.get("design_document")
            ):
                related_designs.append(self._build_related_design_summary(design_session))
        return sorted(related_designs, key=lambda item: item["updated_at"], reverse=True)

    def _refresh_related_designs(self, design_session: dict) -> None:
        input_package = design_session.get("input_package")
        if input_package:
            input_package["related_designs"] = self._list_related_designs(input_package["input_package_id"])

    def _build_related_design_summary(self, design_session: dict) -> dict:
        design_document = design_session["design_document"] or {}
        return {
            "software_design_id": design_session["session_id"],
            "title": design_document.get("title", "未命名软件设计说明"),
            "version_label": "SoftwareDesignBaseline v2",
            "status": design_session["status"],
            "created_at": design_session["created_at"],
            "updated_at": design_session["updated_at"],
        }

    def _build_design_document(self, app_name: str) -> dict:
        return {
            "title": f"{app_name}设计说明",
            "sections": [
                {
                    "section_id": "goal",
                    "title": "1. 设计目标与范围",
                    "content": f"本设计面向{app_name}首版交付，覆盖规划任务创建、冲突识别、协同确认、处置记录和状态追溯能力。",
                    "status": "generated",
                },
                {
                    "section_id": "architecture",
                    "title": "2. 总体架构",
                    "content": "首版采用统一服务架构，前端以 B/S 工作台承载协同规划视图，后端以任务、冲突、确认和审计四类服务对象组织核心能力。",
                    "status": "generated",
                },
                {
                    "section_id": "modules",
                    "title": "3. 模块划分",
                    "content": "系统划分为规划任务管理、冲突识别与告警、协同确认、审计追溯四个模块。",
                    "status": "generated",
                },
            ],
        }

    def _build_design_baseline(self, app_name: str) -> dict:
        return {
            "baseline_id": f"sdb2-{uuid4().hex[:10]}",
            "application_name": app_name,
            "architecture_mode": "unified_service",
            "modules": [
                {"module_id": "planning-task", "name": "规划任务管理", "source_refs": ["REQ-3.2"]},
                {"module_id": "conflict-alert", "name": "冲突识别与告警", "source_refs": ["REQ-3.2", "REQ-4.1"]},
                {"module_id": "collaboration-confirm", "name": "协同确认", "source_refs": ["REQ-3.2"]},
                {"module_id": "audit-trace", "name": "审计追溯", "source_refs": ["REQ-4.1"]},
            ],
            "traceability": [
                {"requirement_clause": "REQ-3.2", "design_section": "3. 模块划分"},
                {"requirement_clause": "REQ-4.1", "design_section": "4. 状态机与接口约束"},
            ],
            "pending_confirmations": [],
        }

    def _build_workorder_projection(self) -> dict:
        return {
            "package_overview": {
                "architecture_recommendation": "unified_service",
                "design_notes": ["统一服务优先，保留后续拆分条件。"],
            },
            "tree": {
                "node_id": "p4-projection-root",
                "title": "P4 模块工单投影包",
                "node_type": "projection_package",
                "children": [
                    {
                        "node_id": "branch-core-service",
                        "title": "统一服务实现分支",
                        "node_type": "module_branch",
                        "children": [
                            {"node_id": "wo-planning-task", "title": "规划任务管理模块实现", "node_type": "module_workorder"},
                            {"node_id": "wo-conflict-alert", "title": "冲突识别与告警模块实现", "node_type": "module_workorder"},
                        ],
                    },
                    {
                        "node_id": "branch-collaboration",
                        "title": "协同与审计实现分支",
                        "node_type": "module_branch",
                        "children": [
                            {"node_id": "wo-collaboration-confirm", "title": "协同确认模块实现", "node_type": "module_workorder"},
                            {"node_id": "wo-audit-trace", "title": "审计追溯模块实现", "node_type": "module_workorder"},
                        ],
                    },
                ],
            },
            "items": [
                {"item_id": "wo-planning-task", "title": "规划任务管理模块实现", "module_id": "planning-task"},
                {"item_id": "wo-conflict-alert", "title": "冲突识别与告警模块实现", "module_id": "conflict-alert"},
                {"item_id": "wo-collaboration-confirm", "title": "协同确认模块实现", "module_id": "collaboration-confirm"},
                {"item_id": "wo-audit-trace", "title": "审计追溯模块实现", "module_id": "audit-trace"},
            ],
        }

    def _build_frozen_package(self, design_session: dict) -> dict:
        return {
            "package_id": f"sdp-{design_session['session_id']}",
            "version_label": "SoftwareDesignBaseline v2",
            "status": "frozen",
            "frozen_at": self._now(),
            "design_document": design_session["design_document"],
            "design_baseline": design_session["design_baseline"],
            "workorder_projection": design_session["workorder_projection"],
        }

    def _build_runtime_event(self, event_type: str, message: str) -> dict:
        return {
            "event_id": f"p3evt-{uuid4().hex[:10]}",
            "event_type": event_type,
            "message": message,
            "created_at": self._now(),
        }

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
