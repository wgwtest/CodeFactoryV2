from __future__ import annotations


class ProcessArtifactService:
    def fact_for_active_node(self, clause_id: str, semantic: str) -> str:
        if clause_id == "REQ-1.1":
            return f"编写目的初步确认：{semantic}"
        if clause_id == "REQ-2.1":
            return f"软件定位初步确认：{semantic}"
        if clause_id == "REQ-3.1":
            return f"用户与角色初步确认：{semantic}"
        if clause_id == "REQ-3.2":
            return f"核心业务流程初步确认：{semantic}"
        if clause_id == "REQ-3.3":
            return f"异常与补偿初步确认：{semantic}"
        if clause_id == "REQ-4.1":
            return f"性能与可靠性初步确认：{semantic}"
        if clause_id == "REQ-5.1":
            return f"验收准则初步确认：{semantic}"
        return f"需求规格信息初步确认：{semantic}"

    def patch_for_active_node(self, clause_id: str, semantic: str) -> str:
        if clause_id == "REQ-1.1":
            return f"本文档用于定义{semantic}相关的软件需求边界、功能行为和验收准则。"
        if clause_id == "REQ-2.1":
            return f"软件定位为：{semantic}"
        if clause_id == "REQ-3.1":
            return f"本软件的主要使用对象和职责包括：{semantic}"
        if clause_id == "REQ-3.2":
            return f"核心业务流程为：{semantic}"
        if clause_id == "REQ-3.3":
            return f"异常与补偿要求为：{semantic}"
        if clause_id == "REQ-4.1":
            return f"性能与可靠性要求为：{semantic}"
        if clause_id == "REQ-5.1":
            return f"验收准则为：{semantic}"
        return semantic

    def quick_options_for_node(self, node: dict | None) -> list[dict]:
        clause_id = self.clause_id_from_node(node)
        options_by_clause = {
            "REQ-1.1": [
                ("A", "先定义软件名称和目标", True),
                ("B", "先说明业务背景", False),
                ("C", "先限定不做什么", False),
            ],
            "REQ-2.1": [
                ("A", "计算分析工具", True),
                ("B", "协同规划平台", False),
                ("C", "二者兼有但先做分析", False),
            ],
            "REQ-3.1": [
                ("A", "领域专家直接使用", True),
                ("B", "管理员配置后专家使用", False),
                ("C", "多角色协同使用", False),
            ],
            "REQ-3.2": [
                ("A", "导入数据后计算分析", True),
                ("B", "配置任务后批量处理", False),
                ("C", "人工确认后生成报告", False),
            ],
            "REQ-3.3": [
                ("A", "缺数据时阻断并提示", True),
                ("B", "异常时进入人工复核", False),
                ("C", "允许保存为待处理", False),
            ],
            "REQ-4.1": [
                ("A", "优先保证可靠性", True),
                ("B", "优先保证响应速度", False),
                ("C", "先按单机部署约束", False),
            ],
            "REQ-5.1": [
                ("A", "按功能闭环验收", True),
                ("B", "按专家评审验收", False),
                ("C", "按演示样例验收", False),
            ],
        }
        return [
            {"key": key, "label": label, "recommended": recommended}
            for key, label, recommended in options_by_clause.get(clause_id, [])
        ]

    @staticmethod
    def clause_id_from_node(node: dict | None) -> str:
        if not node:
            return ""
        node_id = str(node.get("node_id") or "")
        return node_id.removeprefix("SPEC-")
