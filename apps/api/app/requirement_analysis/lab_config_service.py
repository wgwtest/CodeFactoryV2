from __future__ import annotations


class RequirementAnalysisLabConfigService:
    """Builds the frontend Lab configuration owned by the Requirement Analysis backend."""

    def get_config(self) -> dict:
        return {
            "page": {
                "title": "P2 XG 需求分析组织器 Lab",
                "subtitle": "独立验证问答组织器、模型 Provider 和结构化 Turn 输出，不写入正式需求规格编辑器。",
            },
            "defaults": {
                "topic": "默认运算软件需求规格说明",
                "orchestrator_id": "xg-heuristic-orchestrator",
                "provider_id": "deepseek",
                "model": "provider-default",
                "template_id": "xg-template-81433-default",
                "knowledge_package_id": "airspace-domain-demo",
                "write_policy": "patch_suggestion_only",
            },
            "startup_fields": [
                {
                    "field": "topic",
                    "label": "课题输入",
                    "control": "textarea",
                    "required": True,
                    "placeholder": "输入本次需求规格探索课题",
                }
            ],
            "write_policies": [
                {
                    "policy_id": "patch_suggestion_only",
                    "label": "只生成 document_patch 建议",
                    "description": "Lab 只生成 document_patch 建议，不直接写入正式需求规格草稿。",
                }
            ],
            "provider_log_schema": {
                "fields": [
                    {
                        "path": "user_input",
                        "label": "User Input",
                        "description": "用户本轮提交的原始输入，用于追溯 Provider 调用从哪段用户表达开始。",
                        "used_when": "每次需求分析轮次触发 Provider 调用时使用。",
                    },
                    {
                        "path": "normalized_input",
                        "label": "Normalized Input",
                        "description": "组织器对用户输入的归一化理解，用于判断输入类型、选项匹配和语义摘要。",
                        "used_when": "用户输入归一化后使用。",
                    },
                    {
                        "path": "provider_request.messages",
                        "label": "Provider Request Messages",
                        "description": "发给模型的最终 messages 数组，模型调用时直接使用。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.assembled_prompt",
                        "label": "Assembled Prompt",
                        "description": "组织器拼装后的完整提示词，用于检查模型实际收到的任务说明。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.stage_id",
                        "label": "Stage ID",
                        "description": "当前模型调用所属的轮次阶段标识，用于区分 intent_understanding、decision_state_delta 与 next_interaction_planning。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.prompt_id",
                        "label": "Prompt ID",
                        "description": "当前阶段使用的 Prompt 资产标识，用于核对是否命中了正确的阶段提示词。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.context_json",
                        "label": "当前 turn 上下文 JSON",
                        "description": "写入提示词的结构化上下文快照，用于确认本轮带入了哪些会话状态。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.stage_task_definition_json",
                        "label": "Stage Task Definition JSON",
                        "description": "本阶段任务定义，用于追溯模型被要求解决什么问题、写入哪些章节和按什么标准接受。",
                        "used_when": "decision_state_delta 和 next_interaction_planning 阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.quality_constraints_json",
                        "label": "Quality Constraints JSON",
                        "description": "本阶段质量约束，用于追溯最低写作深度、必须覆盖维度和助手回复要求。",
                        "used_when": "decision_state_delta 和 next_interaction_planning 阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.working_document_json",
                        "label": "Working Document JSON",
                        "description": "本轮调用前带入模型的临时正文投影快照，用于判断模型是否看到了既有正文视图。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.decision_state_json",
                        "label": "Decision State JSON",
                        "description": "本轮模型调用前的结构化状态快照，用于确认探索阶段的业务主状态。",
                        "used_when": "decision_state_delta 和 next_interaction_planning 阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.decision_state_document_json",
                        "label": "Decision State Document JSON",
                        "description": "结构化状态 A4 承载页投影，用于确认用户可见状态页与模型上下文一致。",
                        "used_when": "结构化状态展示和 next_interaction_planning 阶段使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.working_document_after_apply_json",
                        "label": "Working Document After Apply JSON",
                        "description": "正式落稿校核阶段使用的应用后正文快照；探索阶段通常为空。",
                        "used_when": "正式落稿校核阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.working_document_excerpt",
                        "label": "Working Document Excerpt",
                        "description": "与本轮目标最相关的正文摘录，用于检查模型面对的是哪一段正文。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.review_target_paths",
                        "label": "Review Target Paths",
                        "description": "正式落稿校核阶段重点审查的规格锚点路径；探索阶段不作为主判断依据。",
                        "used_when": "正式落稿校核阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.recent_revision_fragments",
                        "label": "Recent Revision Fragments",
                        "description": "最近几轮命中的修订片段摘要，用于判断模型是否看到了最近修改痕迹。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.review_goal",
                        "label": "Review Goal",
                        "description": "正式落稿校核目标；探索阶段下一步焦点由结构化状态和交互规划决定。",
                        "used_when": "正式落稿校核阶段调用模型前使用。",
                    },
                    {
                        "path": "provider_request.prompt_bundle.schema_json",
                        "label": "输出格式要求 JSON",
                        "description": "要求模型返回的 JSON 输出格式约束，用于校验输出字段是否齐全。",
                        "used_when": "每次调用模型 Provider 前使用。",
                    },
                    {
                        "path": "provider_request.mock_context",
                        "label": "Mock Context",
                        "description": "Mock Provider 的调试上下文，仅在本地模拟调用时使用。",
                        "used_when": "Mock Provider 调用时使用。",
                    },
                    {
                        "path": "provider_request.runner_context",
                        "label": "Runner Context",
                        "description": "运行器传入 Provider 的会话与组织器上下文，用于复盘调用边界。",
                        "used_when": "本地组织器 Runner 调用时使用。",
                    },
                    {
                        "path": "provider_response.raw_content",
                        "label": "Raw Content",
                        "description": "Provider 返回的原始文本，解析失败时优先看这一块。",
                        "used_when": "模型 Provider 返回后使用。",
                    },
                    {
                        "path": "provider_response.parsed_json",
                        "label": "Parsed JSON",
                        "description": "从原始文本解析出的 JSON 对象，用于判断模型是否按输出格式要求返回。",
                        "used_when": "Provider 响应解析后使用。",
                    },
                    {
                        "path": "provider_response.target_review_json",
                        "label": "Target Review JSON",
                        "description": "服务端或模型给出的目标范围回看结果，用于判断本轮命中范围是否已足够。",
                        "used_when": "本轮临时正文回看完成后使用。",
                    },
                    {
                        "path": "provider_response.global_review_json",
                        "label": "Global Review JSON",
                        "description": "服务端或模型给出的全局回看结果，用于判断为什么继续追问或进入下一节点。",
                        "used_when": "本轮临时正文回看完成后使用。",
                    },
                    {
                        "path": "provider_normalized_output",
                        "label": "Provider Normalized Output",
                        "description": "Provider 输出经过规范化后的中间结果，用于屏蔽不同模型返回格式差异。",
                        "used_when": "Provider 适配层归一化后使用。",
                    },
                    {
                        "path": "service_output",
                        "label": "Service Output",
                        "description": "Turn 服务最终采纳的输出，用于生成聊天回应、规格补丁和状态更新。",
                        "used_when": "轮次服务完成后处理后使用。",
                    },
                ]
            },
            "turn_audit_schema": {
                "protocol_version": "xg-turn-audit-v1",
                "required_fields": [
                    "previous_interaction",
                    "input_relation",
                    "intent_understanding_result",
                    "target_document_structure",
                    "stage_task_definition",
                    "stage_quality_constraints",
                    "decision_state_delta",
                    "decision_state_change_summary",
                    "spec_execution",
                    "post_update_review",
                    "next_interaction_plan",
                    "closure_decision",
                    "next_interaction",
                    "decision_trace",
                ],
            },
        }
