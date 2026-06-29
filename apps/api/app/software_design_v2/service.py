from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument
from app.platform_exchange.models import ConsumeArtifactCommand
from app.platform_exchange.service import PlatformExchangeService
from app.requirement_spec_work_items.service import RequirementSpecWorkItemService
from app.design_converters.adapters.base import load_design_converter_adapter
from app.design_converters.models import DesignConverterRunRequest, DesignConverterRunResult
from app.design_converters.plugin_registry import get_design_converter_plugin_registry
from app.software_design_v2.models import (
    P3DesignConversionRun,
    P3DesignPatchProposalApply,
    P3DesignSessionCreate,
    P3DesignTurnWrite,
)
from app.software_design_v2.sdd_template_profile import (
    build_sdd_81435_quality_rules,
    build_sdd_81435_template_profile,
)
from app.stage_artifacts.models import StageArtifactCurrentCommand, StageArtifactSnapshotCommand
from app.stage_artifacts.service import StageArtifactService


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


class SoftwareDesignV2Service:
    _sessions: dict[str, dict] = {}
    _supported_patch_ops = {
        "rewrite_block",
        "split_block",
        "insert_block_after",
        "delete_block",
        "merge_blocks",
        "replace_section_blocks",
        "rewrite_section",
        "add_subsection",
        "update_trace_refs",
        "add_quality_note",
    }
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
        self.stage_artifact_service = StageArtifactService(session)

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
        return {"items": [self._converter_to_api(converter) for converter in registry.list_converters()]}

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
            "conversion": self._build_conversion_state(
                "conversion_pending",
                "standard_sdd_draft",
                None,
                None,
                converter=self._default_converter_api(),
            ),
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
        self._persist_design_session(design_session)
        return design_session

    def get_session(self, session_id: str) -> dict | None:
        design_session = self._sessions.get(session_id)
        if design_session is not None:
            return design_session
        return self._load_persisted_design_session(session_id)

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
        converter_api = self._converter_to_api(manifest)
        readiness = dict(converter_api.get("readiness") or {})
        if readiness and readiness.get("ready") is False:
            message = str(readiness.get("message") or "P3 design converter is not ready")
            self._record_conversion_failure(design_session, strategy, converter_api, message)
            raise ValueError(message)

        design_session["conversion"] = self._build_conversion_state(
            "conversion_running",
            strategy,
            None,
            None,
            converter=converter_api,
        )

        request = self._build_converter_request(design_session, payload, strategy)
        adapter = load_design_converter_adapter(manifest)
        try:
            result = adapter.run(request)
        except ValueError as exc:
            self._record_conversion_failure(design_session, strategy, converter_api, str(exc))
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
            converter=self._merge_converter_readiness(result.converter, converter_api),
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
        self._persist_design_session(design_session)

    def _default_converter_api(self) -> dict | None:
        try:
            registry = get_design_converter_plugin_registry()
            return self._converter_to_api(registry.default_converter())
        except ValueError:
            return None

    def _converter_to_api(self, manifest) -> dict:
        converter = manifest.to_api()
        converter["readiness"] = self._build_converter_readiness(converter)
        return converter

    def _merge_converter_readiness(self, converter: dict, fallback_converter: dict) -> dict:
        normalized = dict(converter or {})
        fallback = dict(fallback_converter or {})
        if "readiness" not in normalized and fallback.get("readiness"):
            normalized["readiness"] = fallback["readiness"]
        if "requires" not in normalized and fallback.get("requires"):
            normalized["requires"] = fallback["requires"]
        if "name" not in normalized and fallback.get("name"):
            normalized["name"] = fallback["name"]
        return normalized

    @staticmethod
    def _build_converter_readiness(converter: dict) -> dict:
        requires = dict(converter.get("requires") or {})
        if requires.get("dify_api") is not True:
            return {
                "ready": True,
                "status": "ready",
                "message": "转换器不依赖外部 Dify API 配置。",
                "required_config_keys": [],
                "missing_config_keys": [],
            }

        api_key_configured = bool(_env("CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"))
        required_config_keys = ["CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"]
        if api_key_configured:
            return {
                "ready": True,
                "status": "ready",
                "message": "P3 Dify 转换器已检测到 API Key，可执行需规转软设转换。",
                "required_config_keys": required_config_keys,
                "missing_config_keys": [],
                "configured": {"dify_api_key": True},
            }
        return {
            "ready": False,
            "status": "missing_configuration",
            "message": "DIFY_API_KEY is not configured for requirement-to-sdd-dify-workflow",
            "required_config_keys": required_config_keys,
            "missing_config_keys": required_config_keys,
            "configured": {"dify_api_key": False},
            "operator_hint": "请在本地或部署环境配置 CODEFACTORY_P3_DIFY_API_KEY，或兼容配置 DIFY_API_KEY。",
        }

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
        if payload.turn_type == "scoped_design_edit":
            return self._append_scoped_design_turn(design_session, payload, user_input)

        normalized_intent = "add_state_machine" if "状态" in user_input else "refine_design"
        turn = {
            "turn_id": f"p3turn-{uuid4().hex[:10]}",
            "turn_type": payload.turn_type,
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

    def _append_scoped_design_turn(self, design_session: dict, payload: P3DesignTurnWrite, user_input: str) -> dict:
        if not user_input:
            raise ValueError("P3 scoped design turn user_input cannot be empty")
        scope_anchor = dict(payload.scope_anchor or {})
        if not scope_anchor:
            raise ValueError("P3 scoped design turn requires scope_anchor")
        anchor_type = str(scope_anchor.get("anchor_type") or "").strip()
        if anchor_type not in {
            "design_section",
            "design_block",
            "text_range",
            "function_node",
            "architecture_node",
            "technical_mapping",
            "presentation_shape",
            "p4_projection_node",
            "stage_relation",
        }:
            raise ValueError("unsupported P3 scoped design turn anchor_type")
        scope_anchor["design_revision_id"] = self._current_design_revision_id(design_session)

        turn_id = f"p3turn-{uuid4().hex[:10]}"
        remote_result = self._call_scoped_dify_workflow(
            turn_id=turn_id,
            design_session=design_session,
            payload=payload,
            scope_anchor=scope_anchor,
            user_input=user_input,
        )
        patch_proposal = (
            self._normalize_scoped_patch_proposal(remote_result.get("patch_proposal"), design_session, scope_anchor, user_input)
            if remote_result
            else self._build_scoped_patch_proposal(design_session, scope_anchor, user_input)
        )
        context_receipt = self._normalize_scoped_context_receipt(
            remote_result.get("context_receipt") if remote_result else None,
            design_session,
            scope_anchor,
        )
        provider_call_audit = self._normalize_scoped_provider_call_audit(
            remote_result.get("provider_call_audit") if remote_result else None,
            turn_id,
            payload.interaction_mode,
            remote_result.get("workflow_trace") if remote_result else None,
        )
        assistant_message = (
            str(remote_result.get("assistant_message") or "").strip()
            if remote_result
            else "已生成局部补丁提案：建议将当前对象拆分、重写或补充约束，等待人工确认后应用。"
        )
        if not assistant_message:
            assistant_message = "已生成局部补丁提案：建议将当前对象拆分、重写或补充约束，等待人工确认后应用。"
        turn = {
            "turn_id": turn_id,
            "turn_type": "scoped_design_edit",
            "interaction_mode": payload.interaction_mode,
            "user_input": user_input,
            "normalized_intent": str((remote_result or {}).get("normalized_intent") or "scoped_design_edit"),
            "scope_anchor": scope_anchor,
            "expected_output": list(payload.expected_output),
            "assistant_message": assistant_message,
            "patch_proposal": patch_proposal,
            "context_receipt": context_receipt,
            "provider_call_audit": provider_call_audit,
            "created_at": self._now(),
        }
        design_session["turns"] = [*design_session["turns"], turn]
        design_session["context_summaries"] = self._update_context_summaries(design_session, scope_anchor, user_input)
        design_session["status"] = "patch_ready"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("scoped_turn", f"追加局部设计沟通：{anchor_type}"),
        ]
        self._refresh_related_designs(design_session)
        return {"turn": turn, "session": design_session}

    def apply_patch_proposal(
        self,
        session_id: str,
        proposal_id: str,
        payload: P3DesignPatchProposalApply,
    ) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        self._require_converted_draft(design_session)
        if payload.apply_scope != "document_only":
            raise ValueError("unsupported patch apply_scope")
        patch_turn = self._find_patch_proposal_turn(design_session, proposal_id, payload.turn_id)
        proposal = patch_turn["patch_proposal"]
        if proposal.get("status") == "applied":
            application = self._build_patch_application_record(
                design_session,
                proposal,
                payload,
                updated_targets=[],
                status="applied",
                idempotent=True,
            )
            return {
                "application_id": application["application_id"],
                "status": "applied",
                "application": application,
                "updated_targets": [],
                "warnings": ["补丁提案已应用，本次未重复写入正文。"],
                "updated_session": design_session,
            }
        operations = proposal.get("operations")
        if not isinstance(operations, list) or not operations:
            proposal["proposal_type"] = "advice_only"
            proposal["applicability"] = self._build_patch_applicability(operations if isinstance(operations, list) else [], "operations_empty")
            raise ValueError("operations_empty")
        unsupported_ops = [
            str(operation.get("op") or "")
            for operation in operations
            if not isinstance(operation, dict) or str(operation.get("op") or "") not in self._supported_patch_ops
        ]
        if unsupported_ops:
            proposal["applicability"] = {
                "can_apply": False,
                "reason": "unsupported_operations",
                "supported_ops": sorted(self._supported_patch_ops),
                "unsupported_ops": unsupported_ops,
            }
            raise ValueError("unsupported_operations")
        base_revision_id = str(payload.base_revision_id or "").strip()
        proposal_revision_id = str(proposal.get("base_revision_id") or "").strip()
        current_revision_id = self._current_design_revision_id(design_session)
        if base_revision_id and base_revision_id != proposal_revision_id:
            proposal["status"] = "conflicted"
            proposal["applicability"] = self._build_patch_applicability(operations, "revision_conflict")
            raise ValueError("revision_conflict")
        if proposal_revision_id and proposal_revision_id != current_revision_id:
            proposal["status"] = "conflicted"
            proposal["applicability"] = self._build_patch_applicability(operations, "revision_conflict")
            raise ValueError("revision_conflict")

        document = design_session.get("design_document") or {}
        updated_targets = self._apply_document_patch_operations(document, proposal, operations)
        if not updated_targets:
            proposal["applicability"] = self._build_patch_applicability(operations, "missing_target_object")
            raise ValueError("missing_target_object")

        result_revision_id = self._next_design_revision_id(design_session)
        document["revision_id"] = result_revision_id
        document["version_label"] = result_revision_id
        design_session["version_label"] = result_revision_id
        proposal["status"] = "applied"
        proposal["applicability"] = self._build_patch_applicability(operations, "ready")
        proposal["applied_at"] = self._now()
        application = self._build_patch_application_record(
            design_session,
            proposal,
            payload,
            updated_targets=updated_targets,
            status="applied",
            result_revision_id=result_revision_id,
        )
        application_turn = {
            "turn_id": f"p3turn-{uuid4().hex[:10]}",
            "turn_type": "patch_application",
            "normalized_intent": "apply_patch_proposal",
            "assistant_message": f"已应用补丁提案 {proposal_id} 到软件设计说明正文。",
            "patch_application": application,
            "created_at": self._now(),
        }
        self._merge_patch_application_into_baseline(design_session, updated_targets, application)
        design_session["turns"] = [*design_session["turns"], application_turn]
        design_session["status"] = "patched"
        design_session["updated_at"] = self._now()
        design_session["runtime_events"] = [
            *design_session["runtime_events"],
            self._build_runtime_event("patch_application", f"应用局部补丁提案：{proposal_id}"),
        ]
        self._refresh_related_designs(design_session)
        return {
            "application_id": application["application_id"],
            "status": "applied",
            "application": application,
            "updated_targets": updated_targets,
            "warnings": application["warnings"],
            "updated_session": design_session,
        }

    def _find_patch_proposal_turn(self, design_session: dict, proposal_id: str, turn_id: str | None) -> dict:
        for turn in reversed(list(design_session.get("turns") or [])):
            if turn_id and turn.get("turn_id") != turn_id:
                continue
            proposal = turn.get("patch_proposal")
            if isinstance(proposal, dict) and proposal.get("proposal_id") == proposal_id:
                return turn
        raise ValueError("patch proposal not found")

    def _apply_document_patch_operations(self, document: dict, proposal: dict, operations: list[dict]) -> list[dict]:
        sections = document.get("sections")
        if not isinstance(sections, list):
            raise ValueError("missing_target_object")
        updated_targets: list[dict] = []
        for operation in operations:
            op = str(operation.get("op") or "")
            if op == "rewrite_block":
                updated_targets.extend(self._apply_rewrite_block(sections, proposal, operation))
            elif op == "split_block":
                updated_targets.extend(self._apply_split_block(sections, proposal, operation))
            elif op == "insert_block_after":
                updated_targets.extend(self._apply_insert_block_after(sections, proposal, operation))
            elif op == "replace_section_blocks":
                updated_targets.extend(self._apply_replace_section_blocks(sections, proposal, operation))
            elif op == "rewrite_section":
                updated_targets.extend(self._apply_rewrite_section(sections, proposal, operation))
            elif op == "add_subsection":
                updated_targets.extend(self._apply_add_subsection(sections, proposal, operation))
            elif op == "update_trace_refs":
                updated_targets.extend(self._apply_update_trace_refs(sections, proposal, operation))
            elif op == "add_quality_note":
                updated_targets.extend(self._apply_add_quality_note(sections, proposal, operation))
        return updated_targets

    def _apply_rewrite_block(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        target = self._find_target_block(sections, proposal, operation)
        section, block, block_index = target
        content = str(operation.get("content") or operation.get("new_content") or "").strip()
        if not content:
            raise ValueError("missing_target_object")
        block["content"] = content
        if operation.get("title"):
            block["title"] = str(operation["title"])
        if operation.get("source_refs"):
            block["source_refs"] = [str(ref) for ref in operation.get("source_refs") or []]
        self._sync_section_content_from_blocks(section)
        return [self._updated_block_target(section, block, block_index, "rewrite_block")]

    def _apply_split_block(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        target = self._find_target_block(sections, proposal, operation)
        section, block, block_index = target
        new_blocks = operation.get("new_blocks")
        if not isinstance(new_blocks, list) or not new_blocks:
            raise ValueError("missing_target_object")
        source_refs = [str(ref) for ref in operation.get("source_refs") or block.get("source_refs") or section.get("source_refs") or []]
        replacement_blocks = [
            {
                "block_id": f"{block.get('block_id') or self._target_block_id(proposal, operation)}-split-{index + 1}",
                "kind": "paragraph",
                "title": str(item.get("title") or f"补丁段落 {index + 1}"),
                "content": str(item.get("content") or "").strip(),
                "source_refs": [str(ref) for ref in item.get("source_refs") or source_refs],
                "patched_from": block.get("block_id") or self._target_block_id(proposal, operation),
            }
            for index, item in enumerate(new_blocks)
            if isinstance(item, dict) and str(item.get("content") or "").strip()
        ]
        if not replacement_blocks:
            raise ValueError("missing_target_object")
        blocks = self._ensure_section_blocks(section)
        blocks[block_index : block_index + 1] = replacement_blocks
        self._sync_section_content_from_blocks(section)
        return [
            self._updated_block_target(section, replacement, block_index + index, "split_block")
            for index, replacement in enumerate(replacement_blocks)
        ]

    def _apply_insert_block_after(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        target = self._find_target_block(sections, proposal, operation)
        section, block, block_index = target
        new_block = operation.get("new_block") if isinstance(operation.get("new_block"), dict) else operation
        content = str(new_block.get("content") or "").strip()
        if not content:
            raise ValueError("missing_target_object")
        inserted = {
            "block_id": str(new_block.get("block_id") or f"{block.get('block_id') or self._target_block_id(proposal, operation)}-inserted"),
            "kind": str(new_block.get("kind") or "paragraph"),
            "title": str(new_block.get("title") or "补充段落"),
            "content": content,
            "source_refs": [str(ref) for ref in new_block.get("source_refs") or block.get("source_refs") or section.get("source_refs") or []],
            "patched_after": block.get("block_id") or self._target_block_id(proposal, operation),
        }
        blocks = self._ensure_section_blocks(section)
        blocks.insert(block_index + 1, inserted)
        self._sync_section_content_from_blocks(section)
        return [self._updated_block_target(section, inserted, block_index + 1, "insert_block_after")]

    def _apply_replace_section_blocks(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        section = self._find_target_section(sections, proposal, operation)
        raw_blocks = operation.get("blocks") or operation.get("new_blocks")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise ValueError("missing_target_object")
        source_refs = [str(ref) for ref in operation.get("source_refs") or section.get("source_refs") or []]
        replacement_blocks: list[dict] = []
        for index, item in enumerate(raw_blocks, start=1):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or item.get("text") or "").strip()
            if not content:
                continue
            replacement_blocks.append(
                {
                    "block_id": str(item.get("block_id") or f"{section.get('section_id')}-block-{index}"),
                    "kind": str(item.get("kind") or "paragraph"),
                    "title": str(item.get("title") or f"补丁段落 {index}"),
                    "content": content,
                    "source_refs": [str(ref) for ref in item.get("source_refs") or source_refs],
                    "patched_section": str(section.get("section_id") or ""),
                }
            )
        if not replacement_blocks:
            raise ValueError("missing_target_object")
        section["blocks"] = replacement_blocks
        section["status"] = "patched"
        self._sync_section_content_from_blocks(section)
        return [
            {
                "target_type": "design_section",
                "section_id": str(section.get("section_id") or ""),
                "operation": "replace_section_blocks",
                "updated_block_ids": [block["block_id"] for block in replacement_blocks],
            }
        ]

    def _apply_rewrite_section(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        section = self._find_target_section(sections, proposal, operation)
        content = str(operation.get("content") or operation.get("new_content") or "").strip()
        if not content:
            raise ValueError("missing_target_object")
        if operation.get("title"):
            section["title"] = str(operation["title"])
        section["content"] = content
        section["status"] = "patched"
        section["blocks"] = [
            {
                "block_id": str(operation.get("block_id") or f"{section.get('section_id')}-body"),
                "kind": "paragraph",
                "title": str(operation.get("block_title") or section.get("title") or "补丁段落"),
                "content": content,
                "source_refs": [str(ref) for ref in operation.get("source_refs") or section.get("source_refs") or []],
                "patched_section": str(section.get("section_id") or ""),
            }
        ]
        return [
            {
                "target_type": "design_section",
                "section_id": str(section.get("section_id") or ""),
                "operation": "rewrite_section",
                "updated_block_ids": [section["blocks"][0]["block_id"]],
            }
        ]

    def _apply_add_subsection(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        section = self._find_target_section(sections, proposal, operation)
        title = str(operation.get("title") or operation.get("section_title") or "补充小节").strip()
        content = str(operation.get("content") or "").strip()
        if not content:
            raise ValueError("missing_target_object")
        children = section.setdefault("children", [])
        if not isinstance(children, list):
            section["children"] = []
            children = section["children"]
        subsection = {
            "section_id": str(operation.get("section_id") or f"{section.get('section_id')}-patch-{len(children) + 1}"),
            "title": title,
            "content": content,
            "status": "patched",
            "source_refs": [str(ref) for ref in operation.get("source_refs") or section.get("source_refs") or []],
        }
        children.append(subsection)
        return [
            {
                "target_type": "design_section",
                "section_id": str(subsection["section_id"]),
                "parent_section_id": str(section.get("section_id") or ""),
                "operation": "add_subsection",
            }
        ]

    def _apply_update_trace_refs(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        target = self._find_target_block(sections, proposal, operation)
        section, block, block_index = target
        source_refs = [str(ref) for ref in operation.get("source_refs") or [] if str(ref).strip()]
        if not source_refs:
            return []
        block["source_refs"] = source_refs
        section["source_refs"] = sorted({*list(section.get("source_refs") or []), *source_refs})
        return [self._updated_block_target(section, block, block_index, "update_trace_refs")]

    def _apply_add_quality_note(self, sections: list, proposal: dict, operation: dict) -> list[dict]:
        section = self._find_target_section(sections, proposal, operation)
        note = str(operation.get("note") or operation.get("content") or "").strip()
        if not note:
            return []
        quality = section.setdefault("quality", {})
        notes = quality.setdefault("notes", [])
        if isinstance(notes, list):
            notes.append(note)
        return [
            {
                "target_type": "quality_note",
                "section_id": str(section.get("section_id") or ""),
                "operation": "add_quality_note",
            }
        ]

    def _find_target_block(self, sections: list, proposal: dict, operation: dict) -> tuple[dict, dict, int]:
        target_section_id = self._target_section_id(proposal, operation)
        target_block_id = self._target_block_id(proposal, operation)
        section = self._find_target_section(sections, proposal, operation)
        blocks = self._ensure_section_blocks(section)
        for index, block in enumerate(blocks):
            if str(block.get("block_id") or block.get("blockId") or "") == target_block_id:
                return section, block, index
        if target_block_id in {"", "selected-block", f"{target_section_id}-body"} and blocks:
            return section, blocks[0], 0
        raise ValueError("missing_target_object")

    def _find_target_section(self, sections: list, proposal: dict, operation: dict) -> dict:
        target_section_id = self._target_section_id(proposal, operation)
        for section in self._walk_sections(sections):
            if str(section.get("section_id") or section.get("sectionId") or "") == target_section_id:
                return section
        raise ValueError("missing_target_object")

    def _ensure_section_blocks(self, section: dict) -> list[dict]:
        blocks = section.get("blocks")
        if isinstance(blocks, list) and blocks:
            return blocks
        block_id = f"{section.get('section_id')}-body"
        blocks = [
            {
                "block_id": block_id,
                "kind": "paragraph",
                "content": str(section.get("content") or ""),
                "source_refs": list(section.get("source_refs") or []),
            }
        ]
        section["blocks"] = blocks
        return blocks

    def _sync_section_content_from_blocks(self, section: dict) -> None:
        blocks = self._ensure_section_blocks(section)
        section["content"] = "\n".join(str(block.get("content") or "") for block in blocks if str(block.get("content") or "").strip())

    def _walk_sections(self, sections: list) -> list[dict]:
        walked: list[dict] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            walked.append(section)
            for child_key in ("children", "subsections"):
                children = section.get(child_key)
                if isinstance(children, list):
                    walked.extend(self._walk_sections(children))
        return walked

    @staticmethod
    def _target_section_id(proposal: dict, operation: dict) -> str:
        target_anchor = proposal.get("target_anchor") if isinstance(proposal.get("target_anchor"), dict) else {}
        return str(operation.get("section_id") or target_anchor.get("section_id") or "selected-section")

    @staticmethod
    def _target_block_id(proposal: dict, operation: dict) -> str:
        target_anchor = proposal.get("target_anchor") if isinstance(proposal.get("target_anchor"), dict) else {}
        return str(operation.get("target_block_id") or operation.get("block_id") or target_anchor.get("block_id") or "selected-block")

    @staticmethod
    def _updated_block_target(section: dict, block: dict, index: int, operation: str) -> dict:
        return {
            "target_type": "design_block",
            "section_id": str(section.get("section_id") or ""),
            "block_id": str(block.get("block_id") or block.get("blockId") or ""),
            "operation": operation,
            "index": index,
        }

    def _merge_patch_application_into_baseline(self, design_session: dict, updated_targets: list[dict], application: dict) -> None:
        baseline = design_session.get("design_baseline")
        if not isinstance(baseline, dict):
            return
        applications = baseline.setdefault("patch_applications", [])
        if isinstance(applications, list):
            applications.append(
                {
                    "application_id": application["application_id"],
                    "proposal_id": application["proposal_id"],
                    "updated_targets": updated_targets,
                    "result_revision_id": application["result_revision_id"],
                }
            )
        baseline["pending_confirmations"] = [
            *list(baseline.get("pending_confirmations") or []),
            "局部补丁已应用，需重新运行设计完整性检查。",
        ]

    def _current_design_revision_id(self, design_session: dict) -> str:
        document = design_session.get("design_document") or {}
        return str(document.get("revision_id") or document.get("version_label") or design_session.get("version_label") or "current")

    @staticmethod
    def _next_design_revision_id(design_session: dict) -> str:
        current = str((design_session.get("design_document") or {}).get("revision_id") or design_session.get("version_label") or "rev-0")
        if "-patch-" in current:
            prefix, _, suffix = current.rpartition("-patch-")
            try:
                return f"{prefix}-patch-{int(suffix) + 1}"
            except ValueError:
                pass
        return f"{current}-patch-1"

    def _build_patch_application_record(
        self,
        design_session: dict,
        proposal: dict,
        payload: P3DesignPatchProposalApply,
        *,
        updated_targets: list[dict],
        status: str,
        result_revision_id: str | None = None,
        idempotent: bool = False,
    ) -> dict:
        return {
            "application_id": f"patch-app-{uuid4().hex[:10]}",
            "proposal_id": str(proposal.get("proposal_id") or ""),
            "turn_id": payload.turn_id,
            "status": status,
            "idempotent": idempotent,
            "applied_by": "current_user",
            "applied_at": self._now(),
            "base_revision_id": str(proposal.get("base_revision_id") or payload.base_revision_id),
            "result_revision_id": result_revision_id or self._current_design_revision_id(design_session),
            "updated_targets": updated_targets,
            "warnings": ["补丁应用后需要重新运行设计完整性检查。"],
            "user_note": payload.user_note,
        }

    def _build_patch_applicability(self, operations: list, reason: str) -> dict:
        unsupported_ops = [
            str(operation.get("op") or "")
            for operation in operations
            if isinstance(operation, dict) and str(operation.get("op") or "") not in self._supported_patch_ops
        ]
        return {
            "can_apply": reason == "ready" and bool(operations) and not unsupported_ops,
            "reason": reason,
            "supported_ops": sorted(self._supported_patch_ops),
            "unsupported_ops": unsupported_ops,
        }

    def _normalize_patch_applicability(self, value: Any, operations: list) -> dict:
        fallback = self._build_patch_applicability(operations, "ready" if operations else "operations_empty")
        if isinstance(value, dict):
            reason = str(value.get("reason") or "").strip()
            normalized = {
                "can_apply": bool(value.get("can_apply")) and fallback["can_apply"],
                "reason": reason or fallback["reason"],
                "supported_ops": [str(item) for item in value.get("supported_ops") or sorted(self._supported_patch_ops)],
                "unsupported_ops": [str(item) for item in value.get("unsupported_ops") or fallback["unsupported_ops"]],
            }
            if not operations:
                normalized["can_apply"] = False
                normalized["reason"] = "operations_empty"
            elif fallback["unsupported_ops"]:
                normalized["can_apply"] = False
                normalized["reason"] = "unsupported_operations"
                normalized["unsupported_ops"] = fallback["unsupported_ops"]
            return normalized
        return fallback

    def _infer_patch_proposal_type(self, operations: list) -> str:
        if not operations:
            return "advice_only"
        op_names = {str(operation.get("op") or "") for operation in operations if isinstance(operation, dict)}
        unsupported_ops = sorted(op_name for op_name in op_names if op_name not in self._supported_patch_ops)
        if unsupported_ops:
            return "needs_manual_merge"
        if op_names.intersection({"replace_section_blocks", "rewrite_section"}):
            return "section_replacement_candidate"
        if "replace_document_draft" in op_names:
            return "document_replacement_candidate"
        return "executable_patch"

    def _build_patch_protocol_diagnostics(self, operations: list) -> dict:
        applicability = self._build_patch_applicability(operations, "ready" if operations else "operations_empty")
        if not operations:
            protocol_status = "operations_empty"
        elif applicability["unsupported_ops"]:
            protocol_status = "unsupported_operations"
        else:
            protocol_status = "ok"
        return {
            "protocol_status": protocol_status,
            "operation_count": len(operations),
            "unsupported_ops": applicability["unsupported_ops"],
        }

    def _call_scoped_dify_workflow(
        self,
        *,
        turn_id: str,
        design_session: dict,
        payload: P3DesignTurnWrite,
        scope_anchor: dict,
        user_input: str,
    ) -> dict | None:
        api_key = _env("CODEFACTORY_P3_SCOPED_DIFY_API_KEY")
        if not api_key:
            return None

        base_url = self._normalize_dify_base_url(_env("CODEFACTORY_P3_SCOPED_DIFY_BASE_URL") or "http://localhost/v1")
        workflow_id = _env("CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID")
        timeout_seconds = float(_env("CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS") or "180")
        response_mode = _env("CODEFACTORY_P3_SCOPED_DIFY_RESPONSE_MODE") or "blocking"
        url = self._dify_workflow_run_url(base_url=base_url, workflow_id=workflow_id)
        request_payload = {
            "inputs": self._build_scoped_dify_inputs(design_session, payload, scope_anchor, user_input),
            "response_mode": response_mode,
            "user": f"codefactory-p3-scoped-{design_session['session_id']}",
        }
        candidate_urls = [(url, False)]
        if workflow_id:
            candidate_urls.append((self._dify_workflow_run_url(base_url=base_url, workflow_id=""), True))
        used_default_workflow = False
        remote_payload: dict | None = None
        for candidate_url, is_default_workflow in candidate_urls:
            try:
                response = httpx.post(
                    candidate_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_payload,
                    timeout=timeout_seconds,
                    trust_env=False,
                )
                response.raise_for_status()
                remote_payload = response.json()
                used_default_workflow = is_default_workflow
                break
            except httpx.HTTPStatusError as exc:
                response_text = exc.response.text.strip()
                normalized_response_text = response_text.lower()
                if (
                    not is_default_workflow
                    and workflow_id
                    and exc.response.status_code == 404
                    and "not_found" in normalized_response_text
                    and "workflow" in normalized_response_text
                ):
                    continue
                detail = f"{exc}"
                if response_text:
                    detail = f"{detail}; response_body={response_text[:1200]}"
                raise ValueError(f"remote scoped dify workflow request failed: {detail}") from exc
            except httpx.HTTPError as exc:
                raise ValueError(f"remote scoped dify workflow request failed: {exc}") from exc
            except ValueError as exc:
                raise ValueError("remote scoped dify workflow returned non-JSON response") from exc
        if remote_payload is None:
            raise ValueError("remote scoped dify workflow returned empty response")

        data = dict(remote_payload.get("data") or {})
        workflow_status = str(data.get("status") or "").strip()
        workflow_error = str(data.get("error") or "").strip()
        workflow_run_id = str(remote_payload.get("workflow_run_id") or data.get("id") or "").strip()
        if workflow_status == "failed" or workflow_error:
            detail = workflow_error or "workflow status failed"
            raise ValueError(f"remote scoped dify workflow failed ({workflow_run_id}): {detail}")

        outputs = dict(data.get("outputs") or {})
        result_json = outputs.get("result_json")
        if not isinstance(result_json, str) or not result_json.strip():
            raise ValueError("remote scoped dify workflow did not return data.outputs.result_json")
        try:
            parsed = json.loads(result_json)
        except json.JSONDecodeError as exc:
            raise ValueError("remote scoped dify result_json is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("remote scoped dify result_json is not a JSON object")

        workflow_trace = {
            "provider": "dify_scoped_patch",
            "workflow_id": str(data.get("workflow_id") or workflow_id or "").strip(),
            "workflow_run_id": workflow_run_id,
            "status": workflow_status,
            "response_mode": response_mode,
            "turn_id": turn_id,
        }
        if used_default_workflow and workflow_id:
            workflow_trace["configured_workflow_id"] = workflow_id

        return {
            **dict(parsed),
            "workflow_trace": workflow_trace,
        }

    def _build_scoped_dify_inputs(
        self,
        design_session: dict,
        payload: P3DesignTurnWrite,
        scope_anchor: dict,
        user_input: str,
    ) -> dict:
        edit_task = self._build_long_document_edit_task(design_session, payload, scope_anchor, user_input)
        design_context = {
            "input_package": self._compact_context_dict(design_session.get("input_package") or {}),
            "design_document": self._compact_context_dict(design_session.get("design_document") or {}),
            "design_baseline": self._compact_context_dict(design_session.get("design_baseline") or {}),
            "workorder_projection": self._compact_context_dict(design_session.get("workorder_projection") or {}),
            "context_summaries": self._compact_context_dict(design_session.get("context_summaries") or {}),
        }
        design_context_json = json.dumps(design_context, ensure_ascii=False)
        return {
            "session_id": str(design_session.get("session_id") or ""),
            "design_title": str(design_session.get("design_title") or ""),
            "version_label": str(design_session.get("version_label") or ""),
            "user_input": user_input,
            "interaction_mode": str(payload.interaction_mode or "propose_patch"),
            "scope_anchor_json": json.dumps(scope_anchor, ensure_ascii=False),
            "expected_output_json": json.dumps(list(payload.expected_output), ensure_ascii=False),
            "design_context_json": design_context_json,
            "scoped_context_json": design_context_json,
            "long_document_edit_task_json": json.dumps(edit_task, ensure_ascii=False),
        }

    def _build_long_document_edit_task(
        self,
        design_session: dict,
        payload: P3DesignTurnWrite,
        scope_anchor: dict,
        user_input: str,
    ) -> dict:
        document = design_session.get("design_document") or {}
        sections = document.get("sections") if isinstance(document.get("sections"), list) else []
        target_section = self._find_section_snapshot(sections, str(scope_anchor.get("section_id") or ""))
        target_block = self._find_block_snapshot(target_section, str(scope_anchor.get("block_id") or scope_anchor.get("object_id") or ""))
        previous_block, next_block = self._neighbor_block_snapshots(target_section, target_block)
        return {
            "task_id": f"edit-task-{uuid4().hex[:10]}",
            "document_ref": {
                "document_id": str(scope_anchor.get("document_id") or design_session.get("session_id") or ""),
                "document_type": "software_design",
                "owner_stage": "P3",
                "revision_id": self._current_design_revision_id(design_session),
                "title": str(document.get("title") or design_session.get("design_title") or ""),
            },
            "user_instruction": user_input,
            "edit_intent": str(payload.interaction_mode or "propose_patch"),
            "scope_anchor": scope_anchor,
            "target_snapshot": {
                "target_section": target_section,
                "target_block": target_block,
                "previous_block": previous_block,
                "next_block": next_block,
                "selection_snapshot": scope_anchor.get("selection_snapshot") or {},
            },
            "context_bundle": {
                "input_package_summary": self._build_input_package_summary(design_session.get("input_package") or {}),
                "design_baseline_summary": self._build_design_baseline_summary(design_session.get("design_baseline") or {}),
                "function_tree_summary": self._build_function_tree_summary(design_session.get("design_baseline") or {}),
                "layered_architecture_summary": self._build_layered_architecture_summary(design_session.get("design_baseline") or {}),
                "context_summaries": self._compact_context_dict(design_session.get("context_summaries") or {}),
            },
            "allowed_operations": [
                "rewrite_block",
                "split_block",
                "insert_block_after",
                "delete_block",
                "merge_blocks",
                "replace_section_blocks",
                "rewrite_section",
                "update_trace_refs",
                "add_quality_note",
            ],
            "forbidden_operations": ["replace_document_draft"],
            "output_schema_ref": "LongDocumentPatchProposal.v1",
        }

    def _find_section_snapshot(self, sections: list, section_id: str) -> dict:
        for section in self._walk_sections(sections):
            if str(section.get("section_id") or section.get("sectionId") or "") == section_id:
                return self._section_snapshot(section)
        if sections and isinstance(sections[0], dict):
            return self._section_snapshot(sections[0])
        return {"section_id": section_id, "title": "", "content": "", "blocks": []}

    def _section_snapshot(self, section: dict) -> dict:
        blocks = self._ensure_section_blocks(section)
        return {
            "section_id": str(section.get("section_id") or section.get("sectionId") or ""),
            "title": str(section.get("title") or ""),
            "content": str(section.get("content") or ""),
            "source_refs": [str(ref) for ref in section.get("source_refs") or []],
            "blocks": [self._block_snapshot(block) for block in blocks],
        }

    @staticmethod
    def _block_snapshot(block: dict) -> dict:
        return {
            "block_id": str(block.get("block_id") or block.get("blockId") or ""),
            "kind": str(block.get("kind") or block.get("block_type") or "paragraph"),
            "title": str(block.get("title") or ""),
            "content": str(block.get("content") or block.get("text") or ""),
            "source_refs": [str(ref) for ref in block.get("source_refs") or []],
        }

    def _find_block_snapshot(self, section_snapshot: dict, block_id: str) -> dict:
        blocks = [block for block in section_snapshot.get("blocks") or [] if isinstance(block, dict)]
        for block in blocks:
            if str(block.get("block_id") or "") == block_id:
                return dict(block)
        if blocks:
            return dict(blocks[0])
        return {
            "block_id": block_id or f"{section_snapshot.get('section_id')}-body",
            "kind": "paragraph",
            "title": str(section_snapshot.get("title") or ""),
            "content": str(section_snapshot.get("content") or ""),
            "source_refs": [str(ref) for ref in section_snapshot.get("source_refs") or []],
        }

    @staticmethod
    def _neighbor_block_snapshots(section_snapshot: dict, target_block: dict) -> tuple[dict | None, dict | None]:
        blocks = [block for block in section_snapshot.get("blocks") or [] if isinstance(block, dict)]
        target_id = str(target_block.get("block_id") or "")
        for index, block in enumerate(blocks):
            if str(block.get("block_id") or "") == target_id:
                previous_block = dict(blocks[index - 1]) if index > 0 else None
                next_block = dict(blocks[index + 1]) if index + 1 < len(blocks) else None
                return previous_block, next_block
        return None, None

    @staticmethod
    def _build_input_package_summary(input_package: dict) -> dict:
        standard_document = input_package.get("standard_document") or {}
        structured_spec = input_package.get("structured_spec") or {}
        return {
            "input_package_id": str(input_package.get("input_package_id") or ""),
            "source_title": str(input_package.get("source_title") or standard_document.get("title") or ""),
            "structured_spec_keys": sorted(str(key) for key in structured_spec.keys()) if isinstance(structured_spec, dict) else [],
            "annotations_count": len(input_package.get("annotations") or []),
        }

    @staticmethod
    def _build_design_baseline_summary(design_baseline: dict) -> dict:
        return {
            "baseline_id": str(design_baseline.get("baseline_id") or ""),
            "architecture_mode": str(design_baseline.get("architecture_mode") or ""),
            "module_count": len(design_baseline.get("modules") or []),
            "modules": [
                {
                    "module_id": str(module.get("module_id") or ""),
                    "name": str(module.get("name") or ""),
                    "source_refs": [str(ref) for ref in module.get("source_refs") or []],
                }
                for module in (design_baseline.get("modules") or [])[:8]
                if isinstance(module, dict)
            ],
            "pending_confirmations": [str(item) for item in (design_baseline.get("pending_confirmations") or [])[:8]],
        }

    @staticmethod
    def _build_function_tree_summary(design_baseline: dict) -> dict:
        function_tree = design_baseline.get("function_tree") if isinstance(design_baseline, dict) else {}
        root = function_tree.get("root") if isinstance(function_tree, dict) else {}
        return {
            "tree_id": str(function_tree.get("tree_id") or "") if isinstance(function_tree, dict) else "",
            "root_title": str(root.get("title") or "") if isinstance(root, dict) else "",
            "top_nodes": [
                {"node_id": str(node.get("node_id") or ""), "title": str(node.get("title") or "")}
                for node in (root.get("children") or [])[:8]
                if isinstance(node, dict)
            ]
            if isinstance(root, dict)
            else [],
        }

    @staticmethod
    def _build_layered_architecture_summary(design_baseline: dict) -> dict:
        architecture = design_baseline.get("layered_architecture") or design_baseline.get("layered_architecture_projection") or {}
        if not isinstance(architecture, dict):
            return {}
        layers = []
        for layer in (architecture.get("layers") or [])[:8]:
            if isinstance(layer, dict):
                layers.append(str(layer.get("title") or layer.get("name") or layer.get("layer_id") or ""))
            else:
                layers.append(str(layer))
        return {
            "title": str(architecture.get("title") or architecture.get("name") or ""),
            "layers": [layer for layer in layers if layer],
        }

    @staticmethod
    def _compact_context_dict(value: dict) -> dict:
        text_limit = 6000
        compacted = json.loads(json.dumps(value, ensure_ascii=False, default=str))
        serialized = json.dumps(compacted, ensure_ascii=False)
        if len(serialized) <= text_limit:
            return compacted
        return {
            "truncated": True,
            "summary": serialized[:text_limit],
            "original_char_count": len(serialized),
        }

    @staticmethod
    def _normalize_dify_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        return f"{normalized}/v1"

    @staticmethod
    def _dify_workflow_run_url(*, base_url: str, workflow_id: str) -> str:
        if workflow_id:
            return f"{base_url}/workflows/{workflow_id}/run"
        return f"{base_url}/workflows/run"

    def _normalize_scoped_patch_proposal(
        self,
        value: Any,
        design_session: dict,
        scope_anchor: dict,
        user_input: str,
    ) -> dict:
        if not isinstance(value, dict):
            raise ValueError("remote scoped dify result_json missing patch_proposal")
        patch_proposal = dict(value)
        target_block_id = str(scope_anchor.get("block_id") or scope_anchor.get("object_id") or "selected-block")
        section_id = str(scope_anchor.get("section_id") or "selected-section")
        patch_proposal.setdefault("proposal_id", f"patch-{uuid4().hex[:10]}")
        patch_proposal.setdefault(
            "base_revision_id",
            self._current_design_revision_id(design_session),
        )
        patch_proposal.setdefault(
            "target_anchor",
            {
                "anchor_type": scope_anchor.get("anchor_type"),
                "section_id": section_id,
                "block_id": target_block_id,
            },
        )
        patch_proposal.setdefault("quality_notes", [])
        patch_proposal.setdefault("status", "proposed")
        operations = patch_proposal.get("operations")
        if not isinstance(operations, list):
            raise ValueError("remote scoped dify patch_proposal requires operations")
        patch_proposal["quality_notes"] = self._normalize_scoped_quality_notes(patch_proposal.get("quality_notes"))
        patch_proposal["proposal_type"] = self._infer_patch_proposal_type(operations)
        patch_proposal["applicability"] = self._normalize_patch_applicability(
            patch_proposal.get("applicability"),
            operations,
        )
        patch_proposal["diagnostics"] = self._build_patch_protocol_diagnostics(operations)
        return patch_proposal

    @staticmethod
    def _normalize_scoped_quality_notes(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        notes: list[str] = []
        for item in value:
            if isinstance(item, str):
                note = item.strip()
            elif isinstance(item, dict):
                severity = str(item.get("severity") or "").strip()
                message = str(item.get("message") or item.get("note") or "").strip()
                note = f"{severity}：{message}" if severity and message else message
            else:
                note = str(item).strip()
            if note:
                notes.append(note)
        return notes

    def _normalize_scoped_context_receipt(self, value: Any, design_session: dict, scope_anchor: dict) -> dict:
        context_receipt = self._build_scoped_context_receipt(design_session, scope_anchor)
        if isinstance(value, dict):
            remote_receipt = dict(value)
            included_context = remote_receipt.get("included_context")
            if isinstance(included_context, list):
                context_receipt["included_context"] = included_context
            for key in ("context_receipt_id", "session_summary_id", "scoped_summary_id"):
                if isinstance(remote_receipt.get(key), str) and remote_receipt[key].strip():
                    context_receipt[key] = remote_receipt[key]
        return context_receipt

    def _normalize_scoped_provider_call_audit(
        self,
        value: Any,
        turn_id: str,
        interaction_mode: str,
        workflow_trace: Any,
    ) -> dict:
        if not isinstance(workflow_trace, dict):
            return self._build_scoped_provider_call_audit(turn_id, interaction_mode)
        audit = {
            "provider": "dify_scoped_patch",
            "workflow_id": str(workflow_trace.get("workflow_id") or ""),
            "conversation_id": None,
            "run_id": str(workflow_trace.get("workflow_run_id") or ""),
            "interaction_mode": interaction_mode,
            "observability_level": "full",
        }
        if workflow_trace.get("configured_workflow_id"):
            audit["configured_workflow_id"] = str(workflow_trace["configured_workflow_id"])
        if isinstance(value, dict):
            for key, remote_value in value.items():
                if key not in {"provider", "workflow_id", "run_id"}:
                    audit[key] = remote_value
            if value.get("provider"):
                audit["provider"] = str(value["provider"])
            if value.get("workflow_id"):
                audit["workflow_id"] = str(value["workflow_id"])
            if value.get("run_id"):
                audit["run_id"] = str(value["run_id"])
        return audit

    def _build_scoped_patch_proposal(self, design_session: dict, scope_anchor: dict, user_input: str) -> dict:
        target_block_id = str(scope_anchor.get("block_id") or scope_anchor.get("object_id") or "selected-block")
        section_id = str(scope_anchor.get("section_id") or "selected-section")
        design_revision_id = str(
            scope_anchor.get("design_revision_id")
            or self._current_design_revision_id(design_session)
            or design_session.get("updated_at")
            or "current"
        )
        title = str((scope_anchor.get("selection_snapshot") or {}).get("title") or "当前段落")
        operations = [
            {
                "op": "split_block",
                "target_block_id": target_block_id,
                "new_blocks": [
                    {
                        "title": "职责边界",
                        "content": f"围绕“{title}”重新组织职责边界，保留原段落核心含义并去除混杂表达。",
                    },
                    {
                        "title": "接口约束",
                        "content": f"根据用户意图补充接口边界、输入输出、状态约束和验收关注点：{user_input}",
                    },
                ],
            },
            {
                "op": "update_trace_refs",
                "target_block_id": target_block_id,
                "source_refs": list(scope_anchor.get("source_refs") or ["REQ-3.2"]),
            },
        ]
        return {
            "proposal_id": f"patch-{uuid4().hex[:10]}",
            "base_revision_id": design_revision_id,
            "proposal_type": self._infer_patch_proposal_type(operations),
            "target_anchor": {
                "anchor_type": scope_anchor.get("anchor_type"),
                "section_id": section_id,
                "block_id": target_block_id,
            },
            "operations": operations,
            "quality_notes": ["补丁应用后需要重新运行设计完整性检查。"],
            "applicability": self._build_patch_applicability(operations, "ready"),
            "status": "proposed",
        }

    def _build_scoped_context_receipt(self, design_session: dict, scope_anchor: dict) -> dict:
        anchor_key = self._build_scope_anchor_key(scope_anchor)
        return {
            "context_receipt_id": f"ctx-{uuid4().hex[:10]}",
            "session_summary_id": f"ctxsum-{design_session['session_id']}",
            "scoped_summary_id": f"scopesum-{anchor_key}",
            "included_context": [
                "input_package_summary",
                "design_document_anchor",
                "design_baseline_related_facts",
                "global_session_summary",
                "scoped_object_summary",
            ],
        }

    @staticmethod
    def _build_scoped_provider_call_audit(turn_id: str, interaction_mode: str) -> dict:
        return {
            "provider": "local_scoped_patch",
            "workflow_id": "p3-scoped-design-edit",
            "conversation_id": None,
            "run_id": f"local-{turn_id}",
            "interaction_mode": interaction_mode,
            "observability_level": "full",
        }

    def _update_context_summaries(self, design_session: dict, scope_anchor: dict, user_input: str) -> dict:
        current = dict(design_session.get("context_summaries") or {})
        scoped = dict(current.get("scoped") or {})
        anchor_key = self._build_scope_anchor_key(scope_anchor)
        now = self._now()
        scoped[anchor_key] = {
            "summary_id": f"scopesum-{anchor_key}",
            "anchor_key": anchor_key,
            "summary": f"围绕 {scope_anchor.get('anchor_type')} 的最近沟通：{user_input}",
            "accepted_decisions": [],
            "rejected_options": [],
            "pending_questions": ["等待用户确认是否应用补丁提案。"],
            "updated_at": now,
        }
        return {
            "global": {
                "summary_id": f"ctxsum-{design_session['session_id']}",
                "session_id": design_session["session_id"],
                "revision_id": design_session.get("version_label") or design_session.get("updated_at") or "current",
                "summary": "当前软设会话包含需规输入、软设正文、设计基线、投影状态和局部沟通 Turn。",
                "key_decisions": ["段落级沟通进入主 SoftwareDesignSession，不创建段落私有权威会话。"],
                "open_questions": ["补丁提案需要用户确认后才能应用。"],
                "updated_at": now,
            },
            "scoped": scoped,
        }

    @staticmethod
    def _build_scope_anchor_key(scope_anchor: dict) -> str:
        anchor_type = str(scope_anchor.get("anchor_type") or "object")
        section_id = str(scope_anchor.get("section_id") or "-")
        block_id = str(scope_anchor.get("block_id") or scope_anchor.get("object_id") or "-")
        return f"{anchor_type}:{section_id}:{block_id}"

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
        self._persist_design_session(design_session, lifecycle_status="draft_saved")
        self._create_frozen_stage_snapshot(design_session)
        self._refresh_related_designs(design_session)
        return design_session

    def delete_session(self, session_id: str) -> dict | None:
        design_session = self.get_session(session_id)
        if design_session is None:
            return None
        if design_session["status"] == "frozen":
            raise ValueError("frozen P3 design session cannot be deleted")
        design_session["status"] = "deleted"
        design_session["updated_at"] = self._now()
        self._persist_design_session(design_session, lifecycle_status="deleted")
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
        related_by_id = {}
        persisted = self.stage_artifact_service.list_artifacts(
            producer_stage="P3",
            artifact_type="software_design_session",
            scope_type="p3_design_input",
            scope_id=input_package_id,
        )["items"]
        for artifact in persisted:
            if artifact["lifecycle_status"] == "deleted":
                continue
            payload = artifact.get("payload") or {}
            if payload.get("design_document"):
                related_by_id[payload["session_id"]] = self._build_related_design_summary(payload)

        for design_session in self._sessions.values():
            if (
                design_session.get("input_package", {}).get("input_package_id") == input_package_id
                and design_session.get("design_document")
                and design_session.get("status") != "deleted"
            ):
                related_by_id[design_session["session_id"]] = self._build_related_design_summary(design_session)
        return sorted(related_by_id.values(), key=lambda item: item["updated_at"], reverse=True)

    def _refresh_related_designs(self, design_session: dict) -> None:
        self._persist_design_session(design_session)
        input_package = design_session.get("input_package")
        if input_package:
            input_package["related_designs"] = self._list_related_designs(input_package["input_package_id"])

    def _persist_design_session(self, design_session: dict, *, lifecycle_status: str | None = None) -> None:
        input_package = dict(design_session.get("input_package") or {})
        input_package_id = str(input_package.get("input_package_id") or "").strip()
        if not input_package_id:
            return
        self.stage_artifact_service.upsert_current_artifact(
            StageArtifactCurrentCommand(
                artifact_id=design_session["session_id"],
                owner_user_id="default",
                producer_stage="P3",
                artifact_type="software_design_session",
                artifact_version=str(design_session.get("version_label") or "v0.1"),
                schema_version="p3_software_design_session.v1",
                scope_type="p3_design_input",
                scope_id=input_package_id,
                source_artifact_ids=[input_package_id],
                lifecycle_status=lifecycle_status or self._stage_lifecycle_status(design_session),
                payload=dict(design_session),
                source_trace={
                    "session_id": design_session["session_id"],
                    "input_package_id": input_package_id,
                    "source_document_id": input_package.get("source_document_id"),
                    "source_title": input_package.get("source_title"),
                    "p3_status": design_session.get("status"),
                },
            )
        )

    def _load_persisted_design_session(self, session_id: str) -> dict | None:
        artifact = self.stage_artifact_service.get_artifact(session_id)
        if artifact is None:
            return None
        if artifact["artifact_type"] != "software_design_session" or artifact["lifecycle_status"] == "deleted":
            return None
        payload = artifact.get("payload") or {}
        if not isinstance(payload, dict) or payload.get("session_id") != session_id:
            return None
        self._sessions[session_id] = payload
        input_package = payload.get("input_package")
        if input_package:
            input_package["related_designs"] = self._list_related_designs(input_package["input_package_id"])
        return payload

    def _create_frozen_stage_snapshot(self, design_session: dict) -> None:
        try:
            snapshot = self.stage_artifact_service.create_snapshot(
                design_session["session_id"],
                StageArtifactSnapshotCommand(
                    artifact_type="software_design_package",
                    artifact_version=str(design_session.get("version_label") or "v0.1"),
                    schema_version="p3_software_design_package.v1",
                    lifecycle_status="snapshot",
                    source_trace={
                        "session_id": design_session["session_id"],
                        "snapshot_kind": "p3_frozen_design_package",
                    },
                ),
            )
            self.stage_artifact_service.freeze_artifact(snapshot["artifact_id"])
        except ValueError:
            return

    @staticmethod
    def _stage_lifecycle_status(design_session: dict) -> str:
        status = str(design_session.get("status") or "working")
        if status == "frozen":
            return "frozen"
        if status == "published":
            return "published"
        if status in {"draft_saved", "projection_ready"}:
            return "draft_saved"
        if status == "deleted":
            return "deleted"
        return "working"

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
