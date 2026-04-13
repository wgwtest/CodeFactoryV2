from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.application_modeling.common_recommendations import (
    COMMON_AUDIENCE_RECOMMENDATIONS,
    COMMON_FLOW_RECOMMENDATIONS,
    COMMON_GOAL_RECOMMENDATIONS,
    COMMON_STRUCTURE_RECOMMENDATIONS,
)
from app.application_modeling.models import (
    ApplicationRequirementModel,
    RecommendationItem,
    RequirementDraft,
    RequirementDraftEnvelope,
    RequirementDraftExport,
    RequirementDraftUpdate,
    now_iso,
)
from app.archive_knowledge.service import ArchiveKnowledgeService


class ApplicationModelingService:
    def __init__(self, draft_root: str | Path, archive_service: ArchiveKnowledgeService) -> None:
        self.draft_root = Path(draft_root)
        self.archive_service = archive_service

    def create_draft(self, archive_id: str) -> RequirementDraftEnvelope:
        draft = RequirementDraft(
            draft_id=f"draft-{uuid4().hex[:12]}",
            archive_id=archive_id,
        )
        self._save_draft(draft)
        return self._build_envelope(draft)

    def list_drafts(self, archive_id: str | None = None) -> list[RequirementDraft]:
        drafts: list[RequirementDraft] = []
        if not self.draft_root.exists():
            return drafts

        for path in self.draft_root.glob("*.json"):
            draft = RequirementDraft.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if archive_id and draft.archive_id != archive_id:
                continue
            drafts.append(draft)
        return sorted(drafts, key=lambda item: item.updated_at, reverse=True)

    def get_draft(self, draft_id: str) -> RequirementDraftEnvelope | None:
        draft = self._load_draft(draft_id)
        if draft is None:
            return None
        return self._build_envelope(draft)

    def save_draft(self, draft_id: str, payload: RequirementDraftUpdate) -> RequirementDraftEnvelope | None:
        draft = self._load_draft(draft_id)
        if draft is None:
            return None

        updated_payload = draft.model_dump(mode="json")
        updated_payload.update(payload.model_dump(mode="json", exclude_none=True))
        updated_payload["updated_at"] = now_iso()
        updated_draft = RequirementDraft.model_validate(updated_payload)
        self._save_draft(updated_draft)
        return self._build_envelope(updated_draft)

    def complete_draft(self, draft_id: str) -> RequirementDraftEnvelope | None:
        draft = self._load_draft(draft_id)
        if draft is None:
            return None

        self._validate_completion(draft)
        completed_payload = draft.model_dump(mode="json")
        completed_payload["status"] = "completed"
        completed_payload["updated_at"] = now_iso()
        completed_draft = RequirementDraft.model_validate(completed_payload)
        self._save_draft(completed_draft)
        return self._build_envelope(completed_draft)

    def export_draft(self, draft_id: str) -> RequirementDraftExport | None:
        draft = self._load_draft(draft_id)
        if draft is None:
            return None

        model = ApplicationRequirementModel.model_validate(
            draft.model_dump(
                mode="json",
                exclude={"draft_id", "status", "current_step", "created_at", "updated_at"},
            )
        )
        model_payload = model.model_dump(mode="json")
        return RequirementDraftExport(
            draft_id=draft_id,
            model=model,
            json_text=json.dumps(model_payload, ensure_ascii=False, indent=2),
            yaml_text=self._to_yaml(model_payload),
            markdown=self._to_markdown(model),
        )

    def _build_envelope(self, draft: RequirementDraft) -> RequirementDraftEnvelope:
        return RequirementDraftEnvelope(
            draft=draft,
            recommendations=self._build_recommendations(draft),
        )

    def _build_recommendations(self, draft: RequirementDraft) -> dict[str, list[RecommendationItem]]:
        entities = self.archive_service.get_entities(draft.archive_id)
        events = self.archive_service.get_events(draft.archive_id)
        processes = self.archive_service.get_processes(draft.archive_id)

        object_event_recommendations = [
            RecommendationItem(
                id=f"object-{item['id']}",
                name=item["name"],
                description=self._recommendation_description(item),
                source="recommended_domain",
                tags=["领域实体"],
                related_knowledge_id=item["id"],
            )
            for item in entities[:6]
        ]
        object_event_recommendations.extend(
            RecommendationItem(
                id=f"event-{item['id']}",
                name=item["name"],
                description=self._recommendation_description(item),
                source="recommended_domain",
                tags=["领域事件"],
                related_knowledge_id=item["id"],
            )
            for item in events[:6]
        )

        structure_recommendations = [RecommendationItem.model_validate(item) for item in COMMON_STRUCTURE_RECOMMENDATIONS]
        if any("审批" in item["name"] for item in processes):
            structure_recommendations.append(
                RecommendationItem(
                    id="structure-approval-center",
                    name="审批中心 + 进度跟踪 + 统计分析",
                    description="基于领域知识中已出现的审批办理能力，适合作为第一版承载方式。",
                    source="recommended_domain",
                    tags=["审批协同", "领域建议"],
                )
            )

        return {
            "goal": [RecommendationItem.model_validate(item) for item in COMMON_GOAL_RECOMMENDATIONS],
            "audience": [RecommendationItem.model_validate(item) for item in COMMON_AUDIENCE_RECOMMENDATIONS],
            "flow": self._build_flow_recommendations(processes),
            "object_event": object_event_recommendations,
            "structure": structure_recommendations,
        }

    def _build_flow_recommendations(self, processes: list[dict]) -> list[RecommendationItem]:
        recommendations = [RecommendationItem.model_validate(item) for item in COMMON_FLOW_RECOMMENDATIONS]
        recommendations.extend(
            RecommendationItem(
                id=f"flow-{item['id']}",
                name=item["name"],
                description=self._recommendation_description(item),
                source="recommended_domain",
                tags=["领域流程"],
                related_knowledge_id=item["id"],
            )
            for item in processes[:8]
        )
        return recommendations

    def _recommendation_description(self, item: dict) -> str:
        evidence = item.get("evidence", [])
        if evidence:
            excerpt = evidence[0].get("excerpt", "").strip()
            if excerpt:
                return excerpt

        interpretation = item.get("interpretation")
        if isinstance(interpretation, str) and interpretation.strip():
            return interpretation.strip()
        if isinstance(interpretation, dict):
            for key in ("meaning", "kind_label", "structure_role", "producer_hint"):
                value = interpretation.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        category = item.get("category")
        if category:
            return str(category)
        return "来自知识仓的推荐项"

    def _validate_completion(self, draft: RequirementDraft) -> None:
        if not draft.application_name.strip():
            raise ValueError("应用名称不能为空")
        if not draft.audiences:
            raise ValueError("至少需要定义一个使用对象")
        if not draft.roles:
            raise ValueError("至少需要定义一个业务角色")
        if not draft.business_flows:
            raise ValueError("至少需要定义一个核心流程")

    def _load_draft(self, draft_id: str) -> RequirementDraft | None:
        path = self._draft_path(draft_id)
        if not path.exists():
            return None
        return RequirementDraft.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _save_draft(self, draft: RequirementDraft) -> None:
        self.draft_root.mkdir(parents=True, exist_ok=True)
        self._draft_path(draft.draft_id).write_text(
            json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _draft_path(self, draft_id: str) -> Path:
        return self.draft_root / f"{draft_id}.json"

    def _to_yaml(self, value, indent: int = 0) -> str:
        if isinstance(value, dict):
            lines: list[str] = []
            for key, current in value.items():
                prefix = " " * indent + f"{key}:"
                if isinstance(current, (dict, list)):
                    if current == {}:
                        lines.append(prefix + " {}")
                    elif current == []:
                        lines.append(prefix + " []")
                    else:
                        lines.append(prefix)
                        lines.append(self._to_yaml(current, indent + 2))
                else:
                    lines.append(prefix + f" {self._yaml_scalar(current)}")
            return "\n".join(lines)

        if isinstance(value, list):
            lines = []
            for current in value:
                prefix = " " * indent + "-"
                if isinstance(current, (dict, list)):
                    if current == {}:
                        lines.append(prefix + " {}")
                    elif current == []:
                        lines.append(prefix + " []")
                    else:
                        lines.append(prefix)
                        lines.append(self._to_yaml(current, indent + 2))
                else:
                    lines.append(prefix + f" {self._yaml_scalar(current)}")
            return "\n".join(lines)

        return " " * indent + self._yaml_scalar(value)

    def _yaml_scalar(self, value) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value)
        if text == "":
            return '""'
        if any(char in text for char in [":", "#", "\n", '"']):
            escaped = text.replace('"', '\\"')
            return f'"{escaped}"'
        return text

    def _to_markdown(self, model: ApplicationRequirementModel) -> str:
        sections = [
            "# 应用需求模型",
            "",
            "## 基本信息",
            f"- 应用名称：{model.application_name or '未命名'}",
            f"- 关联知识仓：{model.archive_id}",
            "",
            "## 业务目标",
            f"- 现状问题：{model.application_goal.problem_statement or '未填写'}",
            f"- 目标结果：{model.application_goal.target_outcome or '未填写'}",
            "- 成功标准："
            if model.application_goal.success_criteria
            else "- 成功标准：未填写",
        ]
        if model.application_goal.success_criteria:
            sections.extend(f"  - {item}" for item in model.application_goal.success_criteria)

        sections.extend(
            [
                "",
                "## 使用对象",
            ]
        )
        if model.audiences:
            sections.extend(f"- {item.name}：{item.description or '未补充说明'}" for item in model.audiences)
        else:
            sections.append("- 未定义")

        sections.extend(
            [
                "",
                "## 核心流程范围",
            ]
        )
        if model.business_flows:
            sections.extend(
                f"- {item.name}（范围：{item.scope or '未定义'}，优先级：{item.priority or '未定义'}）"
                for item in model.business_flows
            )
        else:
            sections.append("- 未定义")

        sections.extend(
            [
                "",
                "## 关键信息对象",
            ]
        )
        if model.business_objects:
            sections.extend(f"- {item.name}：{item.description or '未补充说明'}" for item in model.business_objects)
        else:
            sections.append("- 未定义")

        sections.extend(
            [
                "",
                "## 关键事件",
            ]
        )
        if model.key_events:
            sections.extend(f"- {item.name}：{item.description or '未补充说明'}" for item in model.key_events)
        else:
            sections.append("- 未定义")

        sections.extend(
            [
                "",
                "## 应用承载建议",
                "- 工作空间："
                if model.application_structure.workspaces
                else "- 工作空间：未定义",
            ]
        )
        if model.application_structure.workspaces:
            sections.extend(f"  - {item.name}" for item in model.application_structure.workspaces)

        sections.append("- 页面建议：" if model.application_structure.pages else "- 页面建议：未定义")
        if model.application_structure.pages:
            sections.extend(
                f"  - {item.name}（类型：{item.page_type or '未定义'}）" for item in model.application_structure.pages
            )

        return "\n".join(sections)
