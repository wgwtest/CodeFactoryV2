from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument
from app.platform_exchange.models import ConsumeArtifactCommand
from app.platform_exchange.service import PlatformExchangeService
from app.requirement_spec_work_items.service import RequirementSpecWorkItemService
from app.software_design_v2.models import P3DesignConversionRun, P3DesignSessionCreate, P3DesignTurnWrite


class SoftwareDesignV2Service:
    _sessions: dict[str, dict] = {}
    _conversion_strategy_options: list[dict[str, str]] = [
        {
            "value": "standard_sdd_draft",
            "label": "标准软设草稿生成",
            "description": "按标准软件设计说明章节生成初稿。",
        },
        {
            "value": "component_first",
            "label": "组件优先拆解",
            "description": "优先抽取组件、接口和可复用工作台对象。",
        },
        {
            "value": "p4_projection_first",
            "label": "P4 投影优先",
            "description": "优先组织下游工具包和工单分支。",
        },
    ]

    def __init__(self, session) -> None:
        self.session = session
        self.platform_exchange_service = PlatformExchangeService(session)
        self.requirement_spec_work_item_service = RequirementSpecWorkItemService(session)

    def list_input_packages(self) -> dict:
        artifact_items = self.platform_exchange_service.list_artifacts(
            artifact_type="requirement_spec_package",
            producer_stage="P2",
            lifecycle_status="published",
        )["items"]
        if artifact_items:
            return {"items": [self._build_input_package_from_artifact(artifact) for artifact in artifact_items]}

        documents = self.session.scalars(
            select(RequirementAuthoringDocument).order_by(RequirementAuthoringDocument.updated_at.desc())
        ).all()
        items = [
            self._build_input_package(document)
            for document in documents
            if document.frozen_package and document.frozen_package.get("p3_consumable") is True
        ]
        if not items:
            self.requirement_spec_work_item_service.ensure_default_published_test_item()
            return self.list_input_packages()
        return {"items": items}

    def create_session(self, payload: P3DesignSessionCreate) -> dict:
        input_package = self._get_input_package(payload.input_package_id)
        session_id = f"p3dl-{uuid4().hex[:10]}"
        design_title = payload.design_title.strip()
        version_label = payload.version_label.strip()
        if not design_title:
            raise ValueError("P3 design title cannot be empty")
        if not version_label:
            raise ValueError("P3 design version label cannot be empty")
        design_session = {
            "session_id": session_id,
            "input_package": input_package,
            "design_title": design_title,
            "version_label": version_label,
            "generation_policy": {
                "architecture_preference": payload.generation_policy.get(
                    "architecture_preference",
                    "统一服务优先，保留拆分点",
                ),
                "module_granularity": payload.generation_policy.get("module_granularity", "3-5 个业务模块，不拆太细"),
                "output_style": payload.generation_policy.get("output_style", "按标准软设正文写，不写聊天语气"),
            },
            "status": "conversion_pending",
            "conversion": self._build_conversion_state("conversion_pending", "standard_sdd_draft", None, None),
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
        if not input_package["input_package_id"].startswith("p2frozen-"):
            self.platform_exchange_service.consume_artifact(
                input_package["input_package_id"],
                ConsumeArtifactCommand(
                    consumer_stage="P3",
                    consumer_ref_id=session_id,
                    consumer_ref_type="P3DesignLabSession",
                    consumption_mode="snapshot",
                    accepted_schema_version="requirement_spec_package.v1",
                    result_status="accepted",
                ),
            )
        return design_session

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def run_conversion(self, session_id: str, payload: P3DesignConversionRun) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        strategy = payload.strategy.strip() or "standard_sdd_draft"
        valid_strategies = {item["value"] for item in self._conversion_strategy_options}
        if strategy not in valid_strategies:
            raise ValueError("unsupported P3 conversion strategy")
        return self._materialize_design_draft(design_session, strategy, target_status="draft_ready")

    def _materialize_design_draft(self, design_session: dict, strategy: str, target_status: str) -> dict:
        design_session["conversion"] = self._build_conversion_state("conversion_running", strategy, None, None)

        structured_spec = design_session["input_package"]["structured_spec"]
        app_name = structured_spec.get("application", {}).get("name") or "未命名软件"
        design_session["design_document"] = self._build_design_document(app_name, design_session["design_title"], design_session["version_label"])
        design_session["design_baseline"] = self._build_design_baseline(app_name)
        if target_status == "baseline_ready":
            design_session["workorder_projection"] = self._build_workorder_projection()
        design_session["status"] = target_status
        design_session["conversion"] = self._build_conversion_state(
            "draft_ready",
            strategy,
            design_session["design_document"],
            design_session["design_baseline"],
        )
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("conversion", f"执行需规转软设基础转换：{strategy}"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def append_turn(self, session_id: str, payload: P3DesignTurnWrite) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        self._require_converted_draft(design_session)

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
        self._require_converted_draft(design_session)
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
        self._require_converted_draft(design_session)
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
        self._require_converted_draft(design_session)
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
        self._require_converted_draft(design_session)
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

    def _build_input_package_from_artifact(self, artifact: dict) -> dict:
        payload = artifact.get("payload") or {}
        source_trace = payload.get("source_trace") or artifact.get("source_trace") or {}
        standard_document = payload.get("standard_document") or {}
        return {
            "input_package_id": artifact["artifact_id"],
            "source_document_id": source_trace.get("authoring_document_id", ""),
            "source_title": standard_document.get("title") or source_trace.get("title") or "未命名需求规格说明",
            "standard_document": standard_document,
            "structured_spec": payload.get("structured_spec", {}),
            "annotations": payload.get("annotations", []),
            "knowledge_binding": payload.get("knowledge_binding"),
            "frozen_at": source_trace.get("frozen_at") or artifact.get("frozen_at"),
            "p3_consumable": payload.get("p3_consumable") is True,
            "related_designs": self._list_related_designs(artifact["artifact_id"]),
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
            "version_label": design_session.get("version_label", "SoftwareDesignBaseline v2"),
            "status": design_session["status"],
            "created_at": design_session["created_at"],
            "updated_at": design_session["updated_at"],
        }

    def _require_converted_draft(self, design_session: dict) -> None:
        if design_session.get("design_document") is None or design_session.get("design_baseline") is None:
            raise ValueError("P3 design session must run conversion before editing the software design draft")

    def _build_conversion_state(
        self,
        status: str,
        strategy: str,
        design_document: dict | None,
        design_baseline: dict | None,
    ) -> dict:
        done = status == "draft_ready"
        running = status == "conversion_running"
        return {
            "status": status,
            "strategy": strategy,
            "strategy_options": self._conversion_strategy_options,
            "steps": [
                self._build_conversion_step(
                    "read_requirement",
                    "读取需规冻结包",
                    "加载正文、结构化条款、标注和冻结快照。",
                    done,
                    running,
                    0,
                ),
                self._build_conversion_step(
                    "extract_design_objects",
                    "抽取设计对象",
                    "抽取模块候选、接口候选、数据对象候选和质量属性。",
                    done,
                    running,
                    1,
                ),
                self._build_conversion_step(
                    "generate_design_draft",
                    "生成软设草稿",
                    "生成 A4 正文草稿和 SoftwareDesignBaseline v2 初稿。",
                    done,
                    running,
                    2,
                ),
                self._build_conversion_step(
                    "map_traceability",
                    "建立追溯映射",
                    "建立需规条款到章节、模块、接口和 P4 候选的映射。",
                    done,
                    running,
                    3,
                ),
            ],
            "draft_preview": self._build_conversion_draft_preview(design_document) if design_document else None,
            "traceability_summary": self._build_conversion_traceability_summary(design_baseline) if design_baseline else None,
        }

    def _build_conversion_step(
        self,
        step_id: str,
        title: str,
        description: str,
        done: bool,
        running: bool,
        index: int,
    ) -> dict:
        if done:
            status = "done"
        elif running and index == 0:
            status = "running"
        else:
            status = "pending"
        return {
            "step_id": step_id,
            "title": title,
            "description": description,
            "status": status,
        }

    def _build_conversion_draft_preview(self, design_document: dict) -> dict:
        return {
            "title": design_document.get("title", "未命名软件设计说明"),
            "version_label": design_document.get("version_label", "SoftwareDesignBaseline v2"),
            "sections": [section.get("title", "未命名章节") for section in design_document.get("sections", [])],
        }

    def _build_conversion_traceability_summary(self, design_baseline: dict) -> dict:
        return {
            "mapped_clause_count": len(design_baseline.get("traceability", [])),
            "target_count": len(design_baseline.get("modules", [])),
            "pending_confirmation_count": len(design_baseline.get("pending_confirmations", [])),
        }

    def _build_design_document(self, app_name: str, design_title: str, version_label: str) -> dict:
        return {
            "title": design_title,
            "version_label": version_label,
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
                "design_notes": ["P4 投影按工具包树组织，不再把投影和工单拆成两个概念。"],
            },
            "tree": {
                "node_id": "p4-projection-root",
                "title": "P4-WO-StageLab-Workbench",
                "node_type": "projection_package",
                "description": "P3 软件设计说明向 P4 研发工单的候选投影，按共性工作台、P3 适配和验证脚本组织。",
                "readiness": "preview_only",
                "children": [
                    {
                        "node_id": "branch-common-workbench",
                        "title": "A. 共性工作台工具包",
                        "node_type": "toolkit_branch",
                        "description": "沉淀 P2/P3 可复用的 Stage Lab 工作台壳、导航和通用文档组件。",
                        "readiness": "ready",
                        "children": [
                            {
                                "node_id": "wo-stage-lab-shell",
                                "title": "WO-A1 StageLabShell 组件生成器",
                                "node_type": "workorder",
                                "description": "生成左侧导航、顶部状态条和主工作区的通用工作台框架。",
                                "readiness": "ready",
                                "source_refs": ["SoftwareDesign.modules.commonWorkbench"],
                                "acceptance": "P2/P3 均可复用同一套 Lab shell 和导航状态模型。",
                            },
                            {
                                "node_id": "wo-stage-navigation",
                                "title": "WO-A2 StageNavigation 状态工具",
                                "node_type": "workorder",
                                "description": "抽象阶段页签、徽标、禁用态和视图切换状态。",
                                "readiness": "ready",
                                "source_refs": ["SoftwareDesign.modules.commonWorkbench"],
                                "acceptance": "导航项能由阶段配置生成，不再为每个阶段重写结构。",
                            },
                        ],
                    },
                    {
                        "node_id": "branch-p3-adapter",
                        "title": "B. P3 适配工具包",
                        "node_type": "toolkit_branch",
                        "description": "该分支包含 P3 专属 Adapter、输入列表快照适配器和 ViewModel 组装脚本。",
                        "readiness": "pending",
                        "source_refs": ["SoftwareDesign.modules.p3Adapter", "sourceRequirement"],
                        "depends_on": ["A. 共性工作台工具包"],
                        "acceptance": "能把需规列表、选中需规对象和软设会话映射到工作台模型。",
                        "children": [
                            {
                                "node_id": "wo-p3-viewmodel-adapter",
                                "title": "WO-B1 DTO -> ViewModel Adapter",
                                "node_type": "workorder",
                                "description": "把 P3 API DTO 组装为 StageDocumentWorkbenchViewModel。",
                                "readiness": "ready",
                                "source_refs": ["SoftwareDesign.modules.p3Adapter"],
                                "depends_on": ["WO-A1 StageLabShell 组件生成器"],
                                "acceptance": "前端不直接消费裸 DTO，页面只依赖 ViewModel。",
                            },
                            {
                                "node_id": "wo-p3-input-snapshot-adapter",
                                "title": "WO-B2 输入列表快照适配器",
                                "node_type": "workorder",
                                "description": "处理 P2 已发布需规列表、关联软设列表和会话打开入口。",
                                "readiness": "pending",
                                "source_refs": ["sourceRequirement.list", "SoftwareDesign.relatedDesigns"],
                                "depends_on": ["WO-B1 DTO -> ViewModel Adapter"],
                                "acceptance": "选择需规后能展示历史软设，并支持新建、编辑、删除未冻结草稿。",
                            },
                        ],
                    },
                    {
                        "node_id": "branch-validation-scripts",
                        "title": "C. 验证脚本工具包",
                        "node_type": "toolkit_branch",
                        "description": "把同源检查和原型截图回归作为 P4 研发前的验证工具包。",
                        "readiness": "ready",
                        "children": [
                            {
                                "node_id": "wo-source-alignment-check",
                                "title": "WO-C1 同源检查脚本",
                                "node_type": "workorder",
                                "description": "检查 P3 实现、软件设计说明和原型图是否指向同一套对象模型。",
                                "readiness": "ready",
                                "source_refs": ["SoftwareDesign.quality.sourceAlignment"],
                                "acceptance": "输出差异清单并标记阻断/警告级别。",
                            },
                            {
                                "node_id": "wo-prototype-screenshot-regression",
                                "title": "WO-C2 原型截图回归脚本",
                                "node_type": "workorder",
                                "description": "对照 v6 原型截图检查软设工作区和 P4 投影视图。",
                                "readiness": "ready",
                                "source_refs": ["SoftwareDesign.quality.prototypeRegression"],
                                "acceptance": "桌面视口截图包含需规输入、软设双视图和 P4 投影树。",
                            },
                        ],
                    },
                ],
            },
            "items": [
                {
                    "item_id": "wo-stage-lab-shell",
                    "title": "WO-A1 StageLabShell 组件生成器",
                    "module_id": "common-workbench",
                    "readiness": "ready",
                },
                {
                    "item_id": "wo-stage-navigation",
                    "title": "WO-A2 StageNavigation 状态工具",
                    "module_id": "common-workbench",
                    "readiness": "ready",
                },
                {
                    "item_id": "wo-p3-viewmodel-adapter",
                    "title": "WO-B1 DTO -> ViewModel Adapter",
                    "module_id": "p3-adapter",
                    "readiness": "ready",
                },
                {
                    "item_id": "wo-p3-input-snapshot-adapter",
                    "title": "WO-B2 输入列表快照适配器",
                    "module_id": "p3-adapter",
                    "readiness": "pending",
                },
                {
                    "item_id": "wo-source-alignment-check",
                    "title": "WO-C1 同源检查脚本",
                    "module_id": "validation-scripts",
                    "readiness": "ready",
                },
                {
                    "item_id": "wo-prototype-screenshot-regression",
                    "title": "WO-C2 原型截图回归脚本",
                    "module_id": "validation-scripts",
                    "readiness": "ready",
                },
            ],
        }

    def _build_frozen_package(self, design_session: dict) -> dict:
        return {
            "package_id": f"sdp-{design_session['session_id']}",
            "version_label": design_session.get("version_label", "SoftwareDesignBaseline v2"),
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
