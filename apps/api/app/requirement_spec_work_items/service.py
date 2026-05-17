from __future__ import annotations

from app.db.models.requirements import RequirementSpecWorkItem
from app.requirement_analysis.models import RequirementAnalysisSessionCreate
from app.requirement_analysis.session_application_service import RequirementAnalysisApplicationService
from app.requirement_analysis.template_service import RequirementAnalysisTemplateService
from app.requirement_authoring.models import RequirementAuthoringDocumentCreate, RequirementAuthoringDocumentSave, RequirementAuthoringFormPatch
from app.requirement_authoring.service import RequirementAuthoringService
from app.requirement_exchange.requirement_spec_service import RequirementSpecApplicationService
from app.platform_exchange.models import PublishArtifactCommand
from app.platform_exchange.service import PlatformExchangeService
from app.requirement_spec_work_items.models import (
    RequirementSpecWorkItemConfigure,
    RequirementSpecWorkItemCreate,
    RequirementSpecWorkItemRevisionCreate,
    RequirementSpecWorkItemSaveAs,
    RequirementSpecWorkItemSaveSessionArtifacts,
    RequirementSpecWorkItemUpdate,
)
from app.requirement_spec_work_items.repository import RequirementSpecWorkItemRepository


class RequirementSpecWorkItemService:
    DEFAULT_TEST_SPEC_TITLE = "空域协同规划软件需求规格说明"

    def __init__(self, session) -> None:
        self.session = session
        self.repository = RequirementSpecWorkItemRepository(session)
        self.authoring_service = RequirementAuthoringService(session)
        self.analysis_service = RequirementAnalysisApplicationService(session)
        self.analysis_template_service = RequirementAnalysisTemplateService()
        self.spec_service = RequirementSpecApplicationService(session)
        self.platform_exchange_service = PlatformExchangeService(session)

    def list_items(self) -> dict:
        if not self.repository.list_items():
            self.ensure_default_published_test_item()
        return {"items": [self.serialize_item(item) for item in self.repository.list_items()]}

    def ensure_default_published_test_item(self) -> RequirementSpecWorkItem:
        item = self._find_default_test_item()
        if item is None:
            item = self._bootstrap_default_publishable_item()
        if item.status != "published_to_p3" or not item.p3_consumable or not item.published_package_id:
            published = self.publish_item(item.id)
            if published is None:
                raise ValueError("Default requirement spec work item not found")
            item = self.repository.get_item(item.id)
            if item is None:
                raise ValueError("Default requirement spec work item not found")
        return item

    def create_item(self, payload: RequirementSpecWorkItemCreate) -> dict:
        document = self.authoring_service.create_document(
            RequirementAuthoringDocumentCreate(
                title=payload.title,
                template_id=self._resolve_authoring_template_id(payload.template_id),
                archive_ids=[],
            )
        )
        if payload.knowledge_binding is not None:
            document = self.authoring_service.save_document(
                document["document_id"],
                RequirementAuthoringDocumentSave(
                    title=payload.title,
                    template_id=self._resolve_authoring_template_id(payload.template_id),
                    knowledge_binding=payload.knowledge_binding,
                ),
            )
            if document is None:
                raise ValueError("Requirement authoring document not found")
        item = RequirementSpecWorkItem(
            title=payload.title.strip() or "未命名需求规格说明",
            initial_description=payload.initial_description.strip(),
            status="draft",
            template_id=payload.template_id,
            knowledge_binding=payload.knowledge_binding,
            authoring_document_id=document["document_id"],
            analysis_session_id=None,
            published_requirement_spec_id=None,
            published_package_id=None,
            version=1,
            p3_consumable=False,
        )
        return self.serialize_item(self.repository.add_item(item), next_action=payload.create_action)

    def get_item(self, spec_item_id: str) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        return self.serialize_item(item)

    def update_item(self, spec_item_id: str, payload: RequirementSpecWorkItemUpdate) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        if item.status == "published_to_p3":
            raise ValueError("published item requires revision before editing")
        if payload.title is not None:
            item.title = payload.title.strip() or "未命名需求规格说明"
        if payload.initial_description is not None:
            item.initial_description = payload.initial_description.strip()
        if payload.template_id is not None:
            item.template_id = payload.template_id
        if "knowledge_binding" in payload.model_fields_set:
            item.knowledge_binding = payload.knowledge_binding
        self.authoring_service.save_document(
            item.authoring_document_id,
            RequirementAuthoringDocumentSave(
                title=item.title,
                template_id=self._resolve_authoring_template_id(item.template_id),
                knowledge_binding=item.knowledge_binding,
            ),
        )
        return self.serialize_item(self.repository.save_item(item))

    def configure_item(self, spec_item_id: str, payload: RequirementSpecWorkItemConfigure) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        if item.status == "published_to_p3":
            raise ValueError("published item requires revision before configure")
        session = self.analysis_service.create_session(
            RequirementAnalysisSessionCreate(
                topic=payload.topic or item.title,
                orchestrator_id=payload.orchestrator_id,
                provider_id=payload.provider_id,
                model=payload.model,
                template_id=payload.template_id,
                knowledge_package_id=payload.knowledge_package_id,
                write_policy=payload.write_policy,
            )
        )
        item.analysis_session_id = session["session_id"]
        item.status = "configured"
        return self.serialize_item(self.repository.save_item(item))

    def publish_item(self, spec_item_id: str) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        document = self.authoring_service.freeze(item.authoring_document_id)
        if document is None:
            raise ValueError("Requirement authoring document not found")
        frozen_package = document["frozen_package"] or {}
        structured_spec = frozen_package.get("structured_spec")
        if not structured_spec:
            raise ValueError("frozen package missing structured spec")
        requirement_spec = self.spec_service.create_from_projected_draft(
            {
                "archive_id": (document.get("archive_ids") or [""])[0] if document.get("archive_ids") else "",
                "status": "ready",
                "payload": structured_spec,
            }
        )
        platform_artifact = self.platform_exchange_service.publish_artifact(
            PublishArtifactCommand(
                artifact_type="requirement_spec_package",
                artifact_version=str(item.version),
                schema_version="requirement_spec_package.v1",
                producer_stage="P2",
                producer_ref_id=item.id,
                producer_ref_type="RequirementSpecWorkItem",
                payload=self._build_requirement_spec_package_payload(
                    item=item,
                    document=document,
                    requirement_spec_id=requirement_spec.id,
                ),
                source_trace={
                    "spec_item_id": item.id,
                    "authoring_document_id": item.authoring_document_id,
                    "requirement_spec_id": requirement_spec.id,
                    "requirement_spec_version": item.version,
                    "title": item.title,
                    "frozen_at": (document.get("frozen_package") or {}).get("frozen_at"),
                    "published_from": "RequirementSpecWorkItemService.publish_item",
                },
                frozen_at=(document.get("frozen_package") or {}).get("frozen_at"),
                published_by="system",
            )
        )
        item.status = "published_to_p3"
        item.p3_consumable = True
        item.published_requirement_spec_id = requirement_spec.id
        item.published_package_id = platform_artifact["artifact_id"]
        return self.serialize_item(self.repository.save_item(item))

    def create_revision(self, spec_item_id: str, payload: RequirementSpecWorkItemRevisionCreate) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        document = self.authoring_service.get_document(item.authoring_document_id)
        if document is None:
            raise ValueError("Requirement authoring document not found")
        next_title = payload.title or f"{item.title} 修订版"
        created = self.authoring_service.create_document(
            RequirementAuthoringDocumentCreate(
                title=next_title,
                template_id=item.template_id,
                archive_ids=document.get("archive_ids", []),
            )
        )
        revision = RequirementSpecWorkItem(
            title=next_title,
            initial_description=item.initial_description,
            status="revision_draft",
            template_id=item.template_id,
            knowledge_binding=item.knowledge_binding,
            authoring_document_id=created["document_id"],
            version=item.version + 1,
            p3_consumable=False,
        )
        return self.serialize_item(self.repository.add_item(revision))

    def save_session_artifacts(self, spec_item_id: str, payload: RequirementSpecWorkItemSaveSessionArtifacts) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        artifacts = self._session_artifacts_for_item(item, session_id=payload.session_id)
        document = self.authoring_service.repository.get_document(item.authoring_document_id)
        if document is None:
            raise ValueError("Requirement authoring document not found")
        if document.status == "frozen":
            raise ValueError("published item requires revision before editing")
        semantic_state = dict(document.semantic_state or {})
        semantic_state["lab_session_artifacts"] = artifacts
        document.semantic_state = semantic_state
        document.status = "draft"
        self.authoring_service.repository.save_document(document)
        item.analysis_session_id = artifacts["session_id"]
        return self.serialize_item(self.repository.save_item(item))

    def save_session_artifacts_as(self, spec_item_id: str, payload: RequirementSpecWorkItemSaveAs) -> dict | None:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return None
        artifacts = self._session_artifacts_for_item(item, session_id=payload.session_id)
        next_title = payload.title.strip() or f"{item.title} 副本"
        created = self.authoring_service.create_document(
            RequirementAuthoringDocumentCreate(
                title=next_title,
                template_id=self._resolve_authoring_template_id(item.template_id),
                archive_ids=[],
            )
        )
        document = self.authoring_service.repository.get_document(created["document_id"])
        if document is None:
            raise ValueError("Requirement authoring document not found")
        semantic_state = dict(document.semantic_state or {})
        semantic_state["lab_session_artifacts"] = {
            **artifacts,
            "source_spec_item_id": item.id,
        }
        document.semantic_state = semantic_state
        self.authoring_service.repository.save_document(document)
        if item.analysis_session_id != artifacts["session_id"]:
            item.analysis_session_id = artifacts["session_id"]
            self.repository.save_item(item)
        saved_as_item = RequirementSpecWorkItem(
            title=next_title,
            initial_description=item.initial_description,
            status="draft",
            template_id=item.template_id,
            knowledge_binding=item.knowledge_binding,
            authoring_document_id=document.id,
            analysis_session_id=artifacts["session_id"],
            version=1,
            p3_consumable=False,
        )
        return self.serialize_item(self.repository.add_item(saved_as_item))

    def delete_item(self, spec_item_id: str) -> bool:
        item = self.repository.get_item(spec_item_id)
        if item is None:
            return False
        if item.status == "published_to_p3":
            raise ValueError("published item cannot be deleted; archive it instead")
        self.repository.delete_item(item)
        return True

    def _bootstrap_default_publishable_item(self) -> RequirementSpecWorkItem:
        self.authoring_service.template_application_service.ensure_default_templates()
        templates = self.authoring_service.template_application_service.list_templates()
        template_id = templates[0]["template_id"]
        title = self.DEFAULT_TEST_SPEC_TITLE
        document = self.authoring_service.create_document(
            RequirementAuthoringDocumentCreate(
                title=title,
                template_id=template_id,
                archive_ids=["20161116-nas"],
            )
        )
        patched = self.authoring_service.patch_form_fields(
            document["document_id"],
            RequirementAuthoringFormPatch(fields=self._default_publishable_fields()),
        )
        if patched is None:
            raise ValueError("Requirement authoring document not found")
        item = RequirementSpecWorkItem(
            title=title,
            initial_description="面向运行协调员和体系架构师的协同规划工具，用于 P2 到 P3 联调测试。",
            status="draft",
            template_id=template_id,
            knowledge_binding={
                "editor_badge": "领域知识：空域规划",
                "domain": {"domain_id": "airspace-planning", "domain_name": "空域规划领域知识"},
            },
            authoring_document_id=document["document_id"],
            analysis_session_id=None,
            published_requirement_spec_id=None,
            published_package_id=None,
            version=1,
            p3_consumable=False,
        )
        return self.repository.add_item(item)

    def _find_default_test_item(self) -> RequirementSpecWorkItem | None:
        for item in self.repository.list_items():
            if item.title == self.DEFAULT_TEST_SPEC_TITLE:
                return item
        return None

    @staticmethod
    def serialize_item(item: RequirementSpecWorkItem, *, next_action: str | None = None) -> dict:
        return {
            "spec_item_id": item.id,
            "title": item.title,
            "initial_description": item.initial_description,
            "status": item.status,
            "template_id": item.template_id,
            "knowledge_binding": item.knowledge_binding,
            "authoring_document_id": item.authoring_document_id,
            "analysis_session_id": item.analysis_session_id,
            "published_requirement_spec_id": item.published_requirement_spec_id,
            "published_package_id": item.published_package_id,
            "version": item.version,
            "p3_consumable": item.p3_consumable,
            "next_action": next_action,
            "available_actions": RequirementSpecWorkItemService.available_actions(item.status),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    @staticmethod
    def available_actions(status: str) -> list[str]:
        if status == "published_to_p3":
            return ["enter_config", "revision"]
        if status in {"archived", "deleted"}:
            return []
        return ["enter_config", "publish"]

    def _session_artifacts_for_item(self, item: RequirementSpecWorkItem, *, session_id: str | None = None) -> dict:
        resolved_session_id = (session_id or "").strip() or item.analysis_session_id
        if not resolved_session_id:
            raise ValueError("Requirement Analysis session not found")
        session = self.analysis_service.get_session(resolved_session_id)
        if session is None:
            raise ValueError("Requirement Analysis session not found")
        return {
            "session_id": session["session_id"],
            "topic": session["topic"],
            "decision_state_document": session.get("decision_state_document") or {},
            "working_document": session.get("working_document") or {},
            "spec_tree": session.get("spec_tree") or [],
            "turn_path": session.get("turn_path") or [],
        }

    def _resolve_authoring_template_id(self, template_id: str) -> str:
        self.authoring_service.template_application_service.ensure_default_templates()
        if self.authoring_service.template_application_service.get_template_model(template_id) is not None:
            return template_id

        lab_template = self.analysis_template_service.get_template(template_id)
        template_code = ""
        if lab_template is not None:
            template_code = str(lab_template.get("template_code") or "")
        if not template_code:
            template_code = "".join(char for char in template_id if char.isdigit())
        if not template_code:
            return template_id

        candidates = self.authoring_service.template_application_service.repository.list_templates_by_code(template_code)
        return candidates[0].id if candidates else template_id

    @staticmethod
    def _default_publishable_fields() -> dict[str, str]:
        return {
            "application_name": "空域协同规划软件",
            "domain_scope": "国家空域管理",
            "application_scope": "空域协同规划任务链",
            "business_goals": "支撑协同规划与冲突处置闭环。",
            "main_scenarios": "规划任务创建、冲突识别、协同确认和处置复核。",
            "usage_modes": "运行协调员主用，体系架构师复核配置。",
            "in_scope": "规划任务、冲突识别、协同确认和处置记录。",
            "out_of_scope": "不包含自动生成最优处置方案。",
            "target_users": "运行协调员、体系架构师、空域规划专家",
            "main_process": "协同规划与冲突处置",
            "normal_flow": "创建规划任务、识别冲突、协同确认、形成处置记录。",
            "exception_flow": "异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。",
            "situational_display": "展示规划任务、冲突状态和处置进展。",
            "gis_analysis_tools": "支持基础地图定位、空间查询和冲突区域查看。",
            "deployment_analysis": "支持规划方案影响范围辅助分析。",
            "result_outputs": "输出处置记录、冲突清单和简化报告。",
            "collaboration_mode": "支持运行协调员提交、体系架构师复核。",
            "input_data_sources": "空域基础数据、规划任务、冲突规则和处置记录。",
            "input_data_mode": "人工录入和文件导入结合。",
            "performance_requirements": "关键告警 2 分钟内反馈。",
            "reliability_requirements": "关键状态变更需留痕。",
            "security_requirements": "按用户身份和任务范围授权。",
            "permission_model": "运行协调员可编辑，体系架构师可复核，其他用户只读。",
            "deployment_environment": "内网环境部署。",
            "accuracy_constraints": "辅助规划级精度，不承诺工程测绘精度。",
            "acceptance_scenarios": "完成规划任务创建、冲突识别、协同确认和处置记录导出。",
            "acceptance_criteria": "关键流程可追溯，超时提醒和处置导出结果可验证。",
        }

    @staticmethod
    def _build_requirement_spec_package_payload(
        *,
        item: RequirementSpecWorkItem,
        document: dict,
        requirement_spec_id: str,
    ) -> dict:
        frozen_package = document.get("frozen_package") or {}
        semantic_state = document.get("semantic_state") or {}
        return {
            "standard_document": frozen_package.get("standard_document", document.get("document")),
            "structured_spec": frozen_package.get("structured_spec", {}),
            "annotations": frozen_package.get("annotations", document.get("annotations") or []),
            "check_result": document.get("check_result") or {},
            "knowledge_binding": item.knowledge_binding or semantic_state.get("knowledge_binding"),
            "source_trace": {
                "spec_item_id": item.id,
                "authoring_document_id": item.authoring_document_id,
                "requirement_spec_id": requirement_spec_id,
                "requirement_spec_version": item.version,
                "title": item.title,
                "frozen_at": frozen_package.get("frozen_at"),
            },
            "p3_consumable": True,
        }
