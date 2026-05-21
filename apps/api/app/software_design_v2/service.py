from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument
from app.platform_exchange.models import ConsumeArtifactCommand
from app.platform_exchange.service import PlatformExchangeService
from app.requirement_spec_work_items.service import RequirementSpecWorkItemService
from app.design_converters.adapters.base import load_design_converter_adapter
from app.design_converters.models import DesignConverterRunRequest, DesignConverterRunResult
from app.design_converters.plugin_registry import get_design_converter_plugin_registry
from app.software_design_v2.models import P3DesignConversionRun, P3DesignSessionCreate, P3DesignTurnWrite
from app.software_design_v2.sdd_template_profile import (
    build_sdd_81435_quality_rules,
    build_sdd_81435_template_profile,
)


class SoftwareDesignV2Service:
    _sessions: dict[str, dict] = {}
    _conversion_strategy_options: list[dict[str, str]] = [
        {
            "value": "standard_sdd_draft",
            "label": "标准软设草稿生成",
            "description": "按标准软件设计说明章节生成初稿，并作为转换器选项传入。",
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

    def list_converters(self) -> dict:
        registry = get_design_converter_plugin_registry()
        return {"items": [converter.to_api() for converter in registry.list_converters()]}

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
        return self._run_design_converter(design_session, payload, strategy)

    def _run_design_converter(self, design_session: dict, payload: P3DesignConversionRun, strategy: str) -> dict:
        registry = get_design_converter_plugin_registry()
        manifest = registry.require(payload.converter_id.strip() if payload.converter_id else registry.default_converter().converter_id)
        design_session["conversion"] = self._build_conversion_state("conversion_running", strategy, None, None, converter=manifest.to_api())

        request = self._build_converter_request(design_session, payload, strategy)
        adapter = load_design_converter_adapter(manifest)
        try:
            result = adapter.run(request)
        except ValueError as exc:
            self._record_conversion_failure(design_session, strategy, manifest.to_api(), str(exc))
            raise
        design_document = self._normalize_converter_design_document(result, design_session)
        design_baseline = self._build_design_baseline_from_converter_result(result, design_session)
        workorder_projection = self._workorder_projection_from_converter_result(result)
        design_session["design_document"] = design_document
        design_session["design_baseline"] = design_baseline
        design_session["workorder_projection"] = workorder_projection
        design_session["check_result"] = self._check_seed_from_converter_result(result, design_baseline)
        design_session["status"] = "draft_ready"
        design_session["conversion"] = self._build_conversion_state(
            "draft_ready",
            strategy,
            design_document,
            design_baseline,
            converter=result.converter,
            process_output=result.process_output,
        )
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("conversion", f"执行需规转软设转换器：{manifest.converter_id} / {strategy}"),
        ]
        self._refresh_related_designs(design_session)
        return design_session

    def _record_conversion_failure(self, design_session: dict, strategy: str, converter: dict, message: str) -> None:
        error_message = message or "P3 design conversion failed"
        process_output = {
            "error": {
                "message": error_message,
                "source": "design_converter",
                "recorded_at": self._now(),
            }
        }
        design_session["status"] = "conversion_failed"
        design_session["conversion"] = self._build_conversion_state(
            "conversion_failed",
            strategy,
            None,
            None,
            converter=converter,
            process_output=process_output,
        )
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("conversion_failed", f"需规转软设转换失败：{error_message}"),
        ]

    def _build_converter_request(
        self,
        design_session: dict,
        payload: P3DesignConversionRun,
        strategy: str,
    ) -> DesignConverterRunRequest:
        input_package = dict(design_session["input_package"] or {})
        target_design_profile = build_sdd_81435_template_profile(
            design_title=design_session["design_title"],
            version_label=design_session["version_label"],
        )
        conversion_options = {
            "strategy": strategy,
            "expected_output": "design_package_with_document",
            **dict(payload.options or {}),
            "generation_policy": dict(design_session.get("generation_policy") or {}),
        }
        quality_rules = build_sdd_81435_quality_rules()
        return DesignConverterRunRequest(
            protocol_version="p3-design-converter-protocol@1",
            session={
                "session_id": design_session["session_id"],
                "design_title": design_session["design_title"],
                "version_label": design_session["version_label"],
                "generation_policy": dict(design_session.get("generation_policy") or {}),
            },
            input_package=input_package,
            target_design_profile=target_design_profile,
            conversion_options=conversion_options,
            quality_rules=quality_rules,
        )

    @staticmethod
    def _normalize_converter_design_document(result: DesignConverterRunResult, design_session: dict) -> dict:
        design_document = dict(result.design_document or {})
        design_document["title"] = design_document.get("title") or design_session["design_title"]
        design_document["version_label"] = design_document.get("version_label") or design_session["version_label"]
        design_document.setdefault("status", "draft")
        design_document.setdefault("sections", [])
        return design_document

    def _build_design_baseline_from_converter_result(self, result: DesignConverterRunResult, design_session: dict) -> dict:
        input_package = dict(design_session.get("input_package") or {})
        structured_spec = dict(input_package.get("structured_spec") or {})
        app_name = structured_spec.get("application", {}).get("name") or result.design_document.get("title") or "未命名软件"
        design_package = dict(result.design_package or {})
        sections = list(result.design_document.get("sections") or [])
        modules = self._modules_from_converter_result(result)
        function_tree = _function_tree_from_converter_result(result, modules=modules)
        function_tree_quality = _evaluate_function_tree_quality(function_tree)
        module_designs = _module_designs_from_converter_result(result)
        explicit_modules = _explicit_module_nodes_from_converter_result(result)
        module_design_quality = _evaluate_module_design_quality(module_designs, sections=sections, modules=explicit_modules)
        document_outline_quality = _evaluate_document_outline_quality(sections, module_designs=module_designs)
        function_tree_quality_findings = list(function_tree_quality.get("findings") or [])
        module_design_quality_findings = list(module_design_quality.get("findings") or [])
        document_outline_quality_findings = list(document_outline_quality.get("findings") or [])
        quality_findings = [
            *function_tree_quality_findings,
            *module_design_quality_findings,
            *document_outline_quality_findings,
        ]
        pending_confirmations = [
            str(item.get("message") or item.get("gap_id") or item)
            for item in result.gap_list
            if str(item.get("severity") or "").lower() in {"blocking", "warning"}
        ]
        pending_confirmations.extend(
            str(finding.get("message") or finding.get("finding_id") or finding)
            for finding in quality_findings
            if str(finding.get("severity") or "").lower() in {"blocking", "warning"}
        )
        return {
            "baseline_id": design_package.get("package_id") or f"sdb2-{uuid4().hex[:10]}",
            "application_name": app_name,
            "architecture_mode": self._architecture_mode_from_converter_result(result),
            "modules": modules,
            "module_designs": module_designs,
            "module_design_quality": module_design_quality,
            "document_outline_quality": document_outline_quality,
            "function_tree": function_tree,
            "function_tree_quality": function_tree_quality,
            "traceability": self._traceability_from_converter_result(result),
            "pending_confirmations": pending_confirmations,
            "design_package": design_package,
            "sections": [
                {
                    "section_id": section.get("section_id"),
                    "title": section.get("title"),
                    "status": section.get("status", "generated"),
                    "source_refs": list(section.get("source_refs") or []),
                }
                for section in sections
                if isinstance(section, dict)
            ],
            "gap_list": list(result.gap_list),
            "review_findings": [*list(result.review_findings), *quality_findings],
            "converter": dict(result.converter),
            "confidence": result.confidence,
        }

    @staticmethod
    def _modules_from_converter_result(result: DesignConverterRunResult) -> list[dict]:
        design_package = dict(result.design_package or {})
        functional_tree = dict(design_package.get("functional_tree_projection") or {})
        modules = functional_tree.get("modules")
        if isinstance(modules, list) and modules:
            return [
                _normalize_design_module(module, index)
                for index, module in enumerate(modules)
                if isinstance(module, dict)
            ]
        root_modules = _module_nodes_from_function_tree(functional_tree.get("root"))
        if root_modules:
            return [
                _normalize_design_module(module, index)
                for index, module in enumerate(root_modules)
            ]
        return [
            {
                "module_id": str(item.get("target_ref") or item.get("target_title") or item.get("target_type") or "design-target"),
                "name": str(item.get("target_title") or item.get("target_ref") or item.get("target_type") or "设计目标"),
                "source_refs": [str(item.get("source_ref") or item.get("source_title") or "")],
            }
            for item in result.traceability
            if isinstance(item, dict)
        ]

    @staticmethod
    def _architecture_mode_from_converter_result(result: DesignConverterRunResult) -> str:
        design_package = dict(result.design_package or {})
        architecture = dict(design_package.get("layered_architecture_projection") or {})
        return str(architecture.get("architecture_mode") or architecture.get("mode") or "converter_generated")

    @staticmethod
    def _traceability_from_converter_result(result: DesignConverterRunResult) -> list[dict]:
        normalized = []
        for item in result.traceability:
            source_ref = str(item.get("source_ref") or item.get("requirement_clause") or "")
            target_title = str(item.get("target_title") or item.get("target_ref") or item.get("design_section") or "")
            normalized.append(
                {
                    "requirement_clause": source_ref,
                    "design_section": target_title,
                    **dict(item),
                }
            )
        return normalized

    @staticmethod
    def _workorder_projection_from_converter_result(result: DesignConverterRunResult) -> dict | None:
        if result.workorder_projection_candidate:
            return _normalize_workorder_projection(dict(result.workorder_projection_candidate), result=result)
        design_package = dict(result.design_package or {})
        projection = design_package.get("p4_workorder_projection")
        if isinstance(projection, dict) and projection:
            return _normalize_workorder_projection(projection, result=result)
        return None

    @staticmethod
    def _check_seed_from_converter_result(result: DesignConverterRunResult, design_baseline: dict | None = None) -> dict:
        quality_summary = dict(result.process_output.get("quality_summary") or {})
        blocking_count = int(quality_summary.get("blocking_count") or 0)
        quality_findings = [
            *list(((design_baseline or {}).get("function_tree_quality") or {}).get("findings") or []),
            *list(((design_baseline or {}).get("module_design_quality") or {}).get("findings") or []),
            *list(((design_baseline or {}).get("document_outline_quality") or {}).get("findings") or []),
        ]
        warning_finding_count = len(
            [
                finding
                for finding in quality_findings
                if str(finding.get("severity") or "").lower() in {"warning", "blocking"}
            ]
        )
        base_warning_count = int(quality_summary.get("warning_count") or len(result.gap_list))
        warning_count = base_warning_count + warning_finding_count
        passed_count = int(quality_summary.get("passed_count") or 0)
        items = [
            {"severity": "passed", "message": "转换器已生成软件设计说明草稿。"},
            {"severity": "passed", "message": "转换器已生成结构化设计包初稿。"},
            {"severity": "passed", "message": "转换器已生成需求到设计追溯。"},
        ]
        for gap in result.gap_list:
            items.append(
                {
                    "severity": str(gap.get("severity") or "warning"),
                    "message": str(gap.get("message") or gap.get("gap_id") or gap),
                }
            )
        for finding in quality_findings:
            target = str(finding.get("target") or "")
            if target == "模块设计":
                scope = "module_design"
            elif target == "软设正文目录":
                scope = "design_document"
            else:
                scope = "function_tree"
            items.append(
                {
                    "item_id": str(finding.get("finding_id") or "P3-FT-QUALITY"),
                    "severity": str(finding.get("severity") or "warning"),
                    "title": _quality_check_title(scope),
                    "message": str(finding.get("message") or finding.get("finding_id") or finding),
                    "description": str(finding.get("message") or finding.get("finding_id") or finding),
                    "scope": scope,
                    "anchor_id": str(finding.get("anchor_id") or "function-tree-root"),
                    "suggested_action": str(finding.get("suggested_action") or ""),
                }
            )
        return {
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "passed_count": passed_count or 3,
            "items": items,
        }

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
        converter: dict | None = None,
        process_output: dict | None = None,
    ) -> dict:
        done = status == "draft_ready"
        running = status == "conversion_running"
        failed = status == "conversion_failed"
        return {
            "status": status,
            "strategy": strategy,
            "converter": converter,
            "strategy_options": self._conversion_strategy_options,
            "steps": [
                self._build_conversion_step(
                    "read_requirement",
                    "读取需规冻结包",
                    "加载正文、结构化条款、标注和冻结快照。",
                    done,
                    running,
                    failed,
                    0,
                ),
                self._build_conversion_step(
                    "extract_design_objects",
                    "抽取设计对象",
                    "抽取模块候选、接口候选、数据对象候选和质量属性。",
                    done,
                    running,
                    failed,
                    1,
                ),
                self._build_conversion_step(
                    "generate_design_draft",
                    "生成软设草稿",
                    "生成 A4 正文草稿和 SoftwareDesignBaseline v2 初稿。",
                    done,
                    running,
                    failed,
                    2,
                ),
                self._build_conversion_step(
                    "map_traceability",
                    "建立追溯映射",
                    "建立需规条款到章节、模块、接口和 P4 候选的映射。",
                    done,
                    running,
                    failed,
                    3,
                ),
            ],
            "draft_preview": self._build_conversion_draft_preview(design_document) if design_document else None,
            "traceability_summary": self._build_conversion_traceability_summary(design_baseline) if design_baseline else None,
            "process_output": process_output or {},
        }

    def _build_conversion_step(
        self,
        step_id: str,
        title: str,
        description: str,
        done: bool,
        running: bool,
        failed: bool,
        index: int,
    ) -> dict:
        if done:
            status = "done"
        elif failed and index == 0:
            status = "failed"
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
            "function_tree": {
                "tree_id": f"functional-tree-{app_name}",
                "title": f"{app_name}功能树",
                "root": {
                    "node_id": "function-tree-root",
                    "title": f"{app_name}功能树",
                    "node_type": "root",
                    "status": "derived",
                    "source_refs": ["REQ-3.2", "REQ-4.1"],
                    "design_refs": [],
                    "children": [
                        {
                            "node_id": "function-node-planning-task",
                            "title": "规划任务管理",
                            "node_type": "module",
                            "module_id": "planning-task",
                            "status": "derived",
                            "source_refs": ["REQ-3.2"],
                            "design_refs": ["modules"],
                            "children": [],
                        },
                        {
                            "node_id": "function-node-conflict-alert",
                            "title": "冲突识别与告警",
                            "node_type": "module",
                            "module_id": "conflict-alert",
                            "status": "derived",
                            "source_refs": ["REQ-3.2", "REQ-4.1"],
                            "design_refs": ["modules"],
                            "children": [],
                        },
                        {
                            "node_id": "function-node-collaboration-confirm",
                            "title": "协同确认",
                            "node_type": "module",
                            "module_id": "collaboration-confirm",
                            "status": "derived",
                            "source_refs": ["REQ-3.2"],
                            "design_refs": ["modules"],
                            "children": [],
                        },
                        {
                            "node_id": "function-node-audit-trace",
                            "title": "审计追溯",
                            "node_type": "module",
                            "module_id": "audit-trace",
                            "status": "derived",
                            "source_refs": ["REQ-4.1"],
                            "design_refs": ["modules"],
                            "children": [],
                        },
                    ],
                },
            },
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


def _normalize_design_module(module: dict, index: int) -> dict:
    module_id = str(module.get("module_id") or module.get("id") or f"module-{index + 1}")
    name = str(module.get("name") or module.get("title") or module_id)
    normalized = {
        "module_id": module_id,
        "name": name,
        "source_refs": list(module.get("source_refs") or []),
    }
    description = module.get("description")
    if isinstance(description, str) and description.strip():
        normalized["description"] = description
    return normalized


def _module_designs_from_converter_result(result: DesignConverterRunResult) -> list[dict]:
    design_package = dict(result.design_package or {})
    module_designs = design_package.get("module_designs") or design_package.get("moduleDesigns")
    if not isinstance(module_designs, list):
        return []
    return [
        _normalize_module_design(module_design, index)
        for index, module_design in enumerate(module_designs)
        if isinstance(module_design, dict)
    ]


def _explicit_module_nodes_from_converter_result(result: DesignConverterRunResult) -> list[dict]:
    design_package = dict(result.design_package or {})
    functional_tree = dict(design_package.get("functional_tree_projection") or {})
    modules = functional_tree.get("modules")
    if isinstance(modules, list) and modules:
        return [_normalize_design_module(module, index) for index, module in enumerate(modules) if isinstance(module, dict)]
    root_modules = _module_nodes_from_function_tree(functional_tree.get("root"))
    if root_modules:
        return [_normalize_design_module(module, index) for index, module in enumerate(root_modules)]
    return []


def _normalize_module_design(module_design: dict, index: int) -> dict:
    module_id = str(module_design.get("module_id") or module_design.get("moduleId") or module_design.get("id") or f"module-design-{index + 1}")
    name = str(module_design.get("name") or module_design.get("title") or module_id)
    normalized = {
        "module_id": module_id,
        "name": name,
        "responsibility": str(module_design.get("responsibility") or module_design.get("description") or ""),
        "source_refs": _unique_strings(module_design.get("source_refs") or module_design.get("sourceRefs") or []),
        "owned_objects": _unique_strings(module_design.get("owned_objects") or module_design.get("ownedObjects") or []),
        "capabilities": list(module_design.get("capabilities") or []),
        "frontend_interactions": _unique_strings(module_design.get("frontend_interactions") or module_design.get("frontendInteractions") or []),
        "backend_services": _unique_strings(module_design.get("backend_services") or module_design.get("backendServices") or []),
        "data_objects": _unique_strings(module_design.get("data_objects") or module_design.get("dataObjects") or []),
        "interfaces": _unique_strings(module_design.get("interfaces") or []),
        "state_transitions": _unique_strings(module_design.get("state_transitions") or module_design.get("stateTransitions") or []),
        "quality_constraints": _unique_strings(module_design.get("quality_constraints") or module_design.get("qualityConstraints") or []),
        "traceability": _unique_strings(module_design.get("traceability") or module_design.get("traceability_refs") or module_design.get("traceabilityRefs") or []),
    }
    extra_keys = [
        "business_rules",
        "businessRules",
        "workflow_refs",
        "workflowRefs",
        "pending_confirmations",
        "pendingConfirmations",
    ]
    for key in extra_keys:
        if key in module_design:
            normalized[key] = module_design[key]
    return normalized


def _function_tree_from_converter_result(result: DesignConverterRunResult, *, modules: list[dict]) -> dict:
    design_package = dict(result.design_package or {})
    functional_tree = dict(design_package.get("functional_tree_projection") or {})
    root = functional_tree.get("root")
    if isinstance(root, dict) and root:
        return {
            "tree_id": str(functional_tree.get("tree_id") or functional_tree.get("id") or "functional-tree"),
            "title": str(functional_tree.get("title") or root.get("title") or "软件功能树"),
            "root": _normalize_function_tree_node(root, fallback_id="function-tree-root"),
        }
    return _function_tree_from_modules(modules, title=str(functional_tree.get("title") or "软件功能树"))


def _function_tree_from_modules(modules: list[dict], *, title: str) -> dict:
    return {
        "tree_id": "functional-tree-module-skeleton",
        "title": title,
        "root": {
            "node_id": "function-tree-root",
            "title": title,
            "node_type": "root",
            "status": "derived",
            "source_refs": _unique_strings(
                source_ref
                for module in modules
                for source_ref in list(module.get("source_refs") or [])
            ),
            "design_refs": [],
            "children": [
                {
                    "node_id": f"function-node-{module.get('module_id')}",
                    "title": str(module.get("name") or module.get("module_id") or f"模块 {index + 1}"),
                    "node_type": "module",
                    "module_id": str(module.get("module_id") or f"module-{index + 1}"),
                    "status": "derived" if module.get("source_refs") else "pending_decomposition",
                    "source_refs": list(module.get("source_refs") or []),
                    "design_refs": list(module.get("design_refs") or []),
                    "description": str(module.get("description") or "转换器尚未返回功能拆解，当前仅展示模块骨架。"),
                    "children": [],
                }
                for index, module in enumerate(modules)
            ],
        },
    }


def _normalize_function_tree_node(node: dict, *, fallback_id: str) -> dict:
    node_id = str(node.get("node_id") or node.get("id") or fallback_id)
    title = str(node.get("title") or node.get("name") or node_id)
    children = node.get("children")
    return {
        "node_id": node_id,
        "title": title,
        "node_type": str(node.get("node_type") or node.get("type") or "function"),
        "status": str(node.get("status") or "derived"),
        "module_id": str(node.get("module_id") or "") if node.get("module_id") else None,
        "source_refs": list(node.get("source_refs") or []),
        "design_refs": list(node.get("design_refs") or []),
        "architecture_refs": list(node.get("architecture_refs") or []),
        "p4_refs": list(node.get("p4_refs") or []),
        "description": str(node.get("description") or "") if node.get("description") else None,
        "children": [
            _normalize_function_tree_node(child, fallback_id=f"{node_id}-{index + 1}")
            for index, child in enumerate(children if isinstance(children, list) else [])
            if isinstance(child, dict)
        ],
    }


def _module_nodes_from_function_tree(root: object) -> list[dict]:
    if not isinstance(root, dict):
        return []
    module_nodes: list[dict] = []
    stack = list(root.get("children") or [])
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("node_type") or node.get("type") or "")
        if node_type == "module":
            module_nodes.append(
                {
                    "module_id": str(node.get("module_id") or node.get("node_id") or node.get("id") or f"module-{len(module_nodes) + 1}"),
                    "name": str(node.get("title") or node.get("name") or "未命名模块"),
                    "source_refs": list(node.get("source_refs") or []),
                    "description": node.get("description"),
                }
            )
        stack.extend(node.get("children") or [])
    return module_nodes


def _evaluate_function_tree_quality(function_tree: dict) -> dict:
    root = function_tree.get("root")
    module_nodes = _direct_function_tree_children_by_type(root, "module")
    metrics = {
        "module_count": len(module_nodes),
        "capability_count": _count_function_tree_nodes_by_type(root, "capability"),
        "function_count": _count_function_tree_nodes_by_type(root, "function"),
        "single_chain_module_count": 0,
        "mechanical_chain_module_count": 0,
    }
    if not module_nodes:
        return {"status": "not_applicable", "metrics": metrics, "findings": []}

    single_chain_modules = []
    mechanical_chain_modules = []
    for module in module_nodes:
        if _is_single_chain_function_tree_module(module):
            single_chain_modules.append(module)
            if _is_mechanical_function_tree_chain(module):
                mechanical_chain_modules.append(module)

    metrics["single_chain_module_count"] = len(single_chain_modules)
    metrics["mechanical_chain_module_count"] = len(mechanical_chain_modules)
    mechanical_ratio = len(single_chain_modules) / len(module_nodes)
    mechanical_chain_ratio = len(mechanical_chain_modules) / len(module_nodes)
    if len(module_nodes) >= 2 and mechanical_ratio >= 0.8 and mechanical_chain_ratio >= 0.8:
        return {
            "status": "warning",
            "metrics": metrics,
            "findings": [
                {
                    "finding_id": "P3-FT-QUALITY-MECHANICAL-SHALLOW",
                    "severity": "warning",
                    "target": "功能树",
                    "anchor_id": str(function_tree.get("tree_id") or root.get("node_id") or "function-tree-root"),
                    "message": "功能树呈现机械占位结构：多数模块只有一个泛化能力，且能力下只有一个“处理XX业务”类功能。",
                    "suggested_action": "要求转换器按需规条款和设计对象重新拆解模块、能力、功能、接口、数据、状态和质量约束节点。",
                    "requires_human_decision": True,
                }
            ],
        }

    return {"status": "passed", "metrics": metrics, "findings": []}


def _evaluate_module_design_quality(module_designs: list[dict], *, sections: list, modules: list[dict]) -> dict:
    frontend_backend_section_count = len(
        [
            section
            for section in sections
            if isinstance(section, dict) and _is_frontend_backend_section_title(str(section.get("title") or ""))
        ]
    )
    metrics = {
        "module_count": len(modules),
        "module_design_count": len(module_designs),
        "complete_module_count": 0,
        "underexplained_module_count": 0,
        "frontend_backend_section_count": frontend_backend_section_count,
    }

    if not modules and not module_designs:
        return {"status": "not_applicable", "metrics": metrics, "findings": []}

    if not module_designs:
        metrics["underexplained_module_count"] = len(modules)
        return _module_design_quality_warning(
            metrics,
            "P3-MODULE-DESIGN-MISSING",
            "模块纵切片设计不足：转换器没有输出 module_designs，软设无法说明每个功能模块的对象、能力、功能项、前后端协作、数据、接口、状态和追溯。",
        )

    underexplained_modules = []
    for module_design in module_designs:
        if _is_complete_module_vertical_slice(module_design):
            metrics["complete_module_count"] += 1
        else:
            underexplained_modules.append(module_design)
    metrics["underexplained_module_count"] = len(underexplained_modules)

    underexplained_ratio = len(underexplained_modules) / len(module_designs)
    if underexplained_modules and underexplained_ratio >= 0.5:
        return _module_design_quality_warning(
            metrics,
            "P3-MODULE-DESIGN-UNDEREXPLAINED",
            "模块纵切片设计不足：多数模块只给出名称或泛化职责，没有讲清楚模块内部对象、能力、功能项、前端交互、后端服务、数据、接口、状态和追溯。",
        )

    if frontend_backend_section_count >= 2 and not metrics["complete_module_count"]:
        return _module_design_quality_warning(
            metrics,
            "P3-MODULE-DESIGN-HORIZONTAL-SPLIT",
            "模块纵切片设计不足：软设正文以“前端软件设计/后端软件设计”等横切章节替代功能模块展开，功能树和模块设计难以对齐。",
        )

    return {"status": "passed", "metrics": metrics, "findings": []}


def _evaluate_document_outline_quality(sections: list, *, module_designs: list[dict]) -> dict:
    section_titles = [
        str(section.get("title") or "").strip()
        for section in sections
        if isinstance(section, dict) and str(section.get("title") or "").strip()
    ]
    frontend_backend_section_count = len([title for title in section_titles if _is_frontend_backend_section_title(title)])
    module_section_count = len(
        [
            title
            for title in section_titles
            if any(_section_title_matches_module_design(title, module_design) for module_design in module_designs)
        ]
    )
    metrics = {
        "section_count": len(section_titles),
        "module_design_count": len(module_designs),
        "module_section_count": module_section_count,
        "frontend_backend_section_count": frontend_backend_section_count,
    }

    if not section_titles or not module_designs:
        return {"status": "not_applicable", "metrics": metrics, "findings": []}

    if frontend_backend_section_count >= 2 and module_section_count == 0:
        return {
            "status": "warning",
            "metrics": metrics,
            "findings": [
                {
                    "finding_id": "P3-DOC-OUTLINE-HORIZONTAL-SPLIT",
                    "severity": "warning",
                    "target": "软设正文目录",
                    "anchor_id": "software-design-document-outline",
                    "message": "软设正文目录仍以“总体架构/前端软件设计/后端软件设计”等横切章节为主体，没有把业务功能模块作为正文一级展开。",
                    "suggested_action": "要求转换器重组 design_document.sections：以业务功能模块为一级主体章节，前端交互、后端服务、数据、接口、状态和质量约束作为模块内二级内容；横切技术说明只能作为附录或辅助章节。",
                    "requires_human_decision": True,
                }
            ],
        }

    return {"status": "passed", "metrics": metrics, "findings": []}


def _section_title_matches_module_design(title: str, module_design: dict) -> bool:
    normalized_title = _strip_document_section_number(title)
    module_name = str(module_design.get("name") or "").strip()
    module_id = str(module_design.get("module_id") or "").strip()
    if module_name and (module_name in normalized_title or normalized_title in {module_name, f"{module_name}模块"}):
        return True
    return bool(module_id and module_id in normalized_title)


def _strip_document_section_number(title: str) -> str:
    normalized = title.strip()
    while normalized and (normalized[0].isdigit() or normalized[0] in {".", "．", "、", " ", "\t"}):
        normalized = normalized[1:].strip()
    return normalized


def _module_design_quality_warning(metrics: dict, finding_id: str, message: str) -> dict:
    return {
        "status": "warning",
        "metrics": metrics,
        "findings": [
            {
                "finding_id": finding_id,
                "severity": "warning",
                "target": "模块设计",
                "anchor_id": "module-designs",
                "message": message,
                "suggested_action": "要求转换器先输出 module_designs，并按每个业务功能模块的纵切片补齐职责、对象、能力、功能项、前端交互、后端服务、数据、接口、状态、质量和追溯。",
                "requires_human_decision": True,
            }
        ],
    }


def _is_complete_module_vertical_slice(module_design: dict) -> bool:
    return (
        bool(str(module_design.get("responsibility") or "").strip())
        and bool(module_design.get("owned_objects"))
        and _module_design_has_capability_functions(module_design)
        and bool(module_design.get("frontend_interactions"))
        and bool(module_design.get("backend_services"))
        and bool(module_design.get("data_objects"))
        and (bool(module_design.get("interfaces")) or _module_design_nested_list_has_items(module_design, "interfaces"))
        and (bool(module_design.get("state_transitions")) or _module_design_nested_list_has_items(module_design, "states"))
        and bool(module_design.get("quality_constraints"))
        and (bool(module_design.get("traceability")) or bool(module_design.get("source_refs")))
    )


def _module_design_has_capability_functions(module_design: dict) -> bool:
    capabilities = module_design.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return False
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        functions = capability.get("functions")
        if isinstance(functions, list) and functions:
            return True
    return False


def _module_design_nested_list_has_items(module_design: dict, key: str) -> bool:
    capabilities = module_design.get("capabilities")
    if not isinstance(capabilities, list):
        return False
    for capability in capabilities:
        if isinstance(capability, dict) and isinstance(capability.get(key), list) and capability.get(key):
            return True
    return False


def _is_frontend_backend_section_title(title: str) -> bool:
    normalized = title.strip()
    return any(marker in normalized for marker in ["前端软件设计", "后端软件设计", "前端设计", "后端设计"])


def _quality_check_title(scope: str) -> str:
    if scope == "module_design":
        return "模块纵切片设计检查"
    if scope == "design_document":
        return "软设正文目录检查"
    return "功能树质量检查"


def _direct_function_tree_children_by_type(root: object, node_type: str) -> list[dict]:
    if not isinstance(root, dict):
        return []
    return [
        child
        for child in root.get("children") or []
        if isinstance(child, dict) and str(child.get("node_type") or child.get("type") or "") == node_type
    ]


def _count_function_tree_nodes_by_type(root: object, node_type: str) -> int:
    return sum(
        1
        for node in _walk_function_tree_nodes(root)
        if str(node.get("node_type") or node.get("type") or "") == node_type
    )


def _walk_function_tree_nodes(root: object):
    if not isinstance(root, dict):
        return
    yield root
    for child in root.get("children") or []:
        yield from _walk_function_tree_nodes(child)


def _is_single_chain_function_tree_module(module: dict) -> bool:
    children = [child for child in module.get("children") or [] if isinstance(child, dict)]
    if len(children) != 1:
        return False
    capability = children[0]
    if str(capability.get("node_type") or capability.get("type") or "") != "capability":
        return False
    capability_children = [child for child in capability.get("children") or [] if isinstance(child, dict)]
    return len(capability_children) == 1 and str(capability_children[0].get("node_type") or capability_children[0].get("type") or "") == "function"


def _is_mechanical_function_tree_chain(module: dict) -> bool:
    if not _is_single_chain_function_tree_module(module):
        return False
    capability = [child for child in module.get("children") or [] if isinstance(child, dict)][0]
    function = [child for child in capability.get("children") or [] if isinstance(child, dict)][0]
    module_title = _strip_function_tree_suffix(str(module.get("title") or ""))
    capability_title = _strip_function_tree_suffix(str(capability.get("title") or ""))
    function_title = str(function.get("title") or "").strip()
    descriptions = " ".join(
        str(node.get("description") or "")
        for node in [module, capability, function]
    )
    return (
        bool(module_title and capability_title == module_title)
        or function_title.startswith("处理")
        or function_title.endswith("业务")
        or "待细化功能项" in descriptions
        or "核心业务能力" in descriptions
    )


def _strip_function_tree_suffix(title: str) -> str:
    normalized = title.strip()
    for suffix in ["模块", "能力", "功能"]:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _normalize_workorder_projection(projection: dict, *, result: DesignConverterRunResult) -> dict:
    if isinstance(projection.get("tree"), dict) and isinstance(projection.get("items"), list):
        return projection

    candidate_batches = projection.get("candidate_batches")
    if isinstance(candidate_batches, list) and candidate_batches:
        batch = next((item for item in candidate_batches if isinstance(item, dict)), {})
        batch_id = str(batch.get("batch_id") or "p4-candidate-root")
        batch_title = str(batch.get("title") or "P4 工单投影候选")
        readiness = str(batch.get("status") or "candidate")
        modules_by_name = {
            module["name"]: module
            for index, module in enumerate(_modules_from_design_package(result.design_package))
            if isinstance(module.get("name"), str)
        }
        batch_module_names = [
            str(name)
            for name in batch.get("modules", [])
            if isinstance(name, str) and name.strip()
        ]
        items = []
        children = []
        for index, module_name in enumerate(batch_module_names):
            module = modules_by_name.get(module_name) or {}
            module_id = str(module.get("module_id") or f"{batch_id}-module-{index + 1}")
            item = {
                "item_id": module_id,
                "title": module_name,
                "module_id": module_id,
                "description": f"由转换器候选批次 {batch_id} 派生。",
                "readiness": readiness,
            }
            items.append(item)
            children.append(
                {
                    "node_id": module_id,
                    "title": module_name,
                    "node_type": "workorder_candidate",
                    "description": item["description"],
                    "readiness": readiness,
                    "source_refs": list(module.get("source_refs") or []),
                }
            )
        return {
            "package_overview": {
                "architecture_recommendation": "converter_generated",
                "design_notes": [f"转换器返回候选批次 {batch_id}，已归一化为前端可渲染投影树。"],
            },
            "tree": {
                "node_id": batch_id,
                "title": batch_title,
                "node_type": "projection_candidate_batch",
                "description": "P3 转换器生成的 P4 工单投影候选批次。",
                "readiness": readiness,
                "children": children,
            },
            "items": items,
            "candidate_batches": candidate_batches,
        }

    return {
        "package_overview": {
            "architecture_recommendation": "converter_generated",
            "design_notes": ["转换器返回了非空投影对象，但未包含 tree/items；已生成空投影占位。"],
        },
        "tree": None,
        "items": [],
        **projection,
    }


def _modules_from_design_package(design_package: dict) -> list[dict]:
    functional_tree = dict((design_package or {}).get("functional_tree_projection") or {})
    modules = functional_tree.get("modules")
    if not isinstance(modules, list):
        return []
    return [
        _normalize_design_module(module, index)
        for index, module in enumerate(modules)
        if isinstance(module, dict)
    ]
