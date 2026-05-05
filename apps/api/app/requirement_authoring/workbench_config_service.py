from __future__ import annotations


class RequirementAuthoringWorkbenchConfigService:
    """Builds the frontend workbench configuration owned by the authoring backend."""

    def get_config(self) -> dict:
        return {
            "page": {
                "title": "P2 专家需求规格编写工作台",
                "subtitle": "面向专家的标准需求规格说明正文编写、校对、检查与冻结。",
            },
            "defaults": {
                "document_title": "未命名软件需求规格说明",
                "layout_ratio": "2:3",
                "allow_empty_knowledge_binding": True,
            },
            "layout_options": [
                {"ratio": "2:3", "label": "2:3"},
                {"ratio": "1:1", "label": "1:1"},
            ],
            "document_statuses": [
                {"status": "draft", "label": "草稿", "editable": True},
                {"status": "checking", "label": "检查中", "editable": False},
                {"status": "ready_to_freeze", "label": "待冻结", "editable": True},
                {"status": "frozen", "label": "已冻结", "editable": False},
                {"status": "submitted_to_p3", "label": "已提交 P3", "editable": False},
                {"status": "archived", "label": "已归档", "editable": False},
            ],
            "actions": [
                {"action_id": "create_document", "label": "新建文档", "style": "primary"},
                {"action_id": "open_document", "label": "打开文档"},
                {
                    "action_id": "save_draft",
                    "label": "保存草稿",
                    "requires_document": True,
                    "disabled_when_frozen": True,
                },
                {"action_id": "delete_document", "label": "删除文档", "requires_document": True, "danger": True},
                {"action_id": "run_check", "label": "缺口检查", "requires_document": True},
                {"action_id": "freeze", "label": "冻结版本", "requires_document": True},
            ],
            "document_surface": {
                "title": "标准需求规格说明",
                "badges": ["可导出稿"],
                "ribbon": ["页面 A4", "样式 标准正文", "段落 1.5 倍行距", "导出 DOCX / PDF"],
            },
            "empty_states": {
                "question_mode": "创建规格文档后开始问答协作",
                "form_mode": "创建规格文档后开始表单校对",
                "document": "创建文档后，右侧会持续生成标准正文。",
            },
        }

