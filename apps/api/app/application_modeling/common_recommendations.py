COMMON_GOAL_RECOMMENDATIONS: list[dict[str, str | list[str]]] = [
    {
        "id": "goal-cycle-efficiency",
        "name": "缩短办理周期",
        "description": "适用于审批链路长、流转等待多、办理超时频繁的场景。",
        "source": "recommended_common",
        "tags": ["效率提升", "流程办理"],
    },
    {
        "id": "goal-collaboration-visibility",
        "name": "提升协同透明度",
        "description": "适用于多角色协同、过程不可见、责任边界不清的场景。",
        "source": "recommended_common",
        "tags": ["协同审批", "过程透明"],
    },
    {
        "id": "goal-compliance-control",
        "name": "强化过程留痕与合规",
        "description": "适用于关键操作需要留痕、追溯与审计的业务。",
        "source": "recommended_common",
        "tags": ["留痕审计", "过程控制"],
    },
]

COMMON_AUDIENCE_RECOMMENDATIONS: list[dict[str, str | list[str]]] = [
    {
        "id": "audience-initiator",
        "name": "业务发起人员",
        "description": "负责提交申请、补充材料和查看进度。",
        "source": "recommended_common",
        "tags": ["办理发起"],
    },
    {
        "id": "audience-approver",
        "name": "审核审批人员",
        "description": "负责处理待办、做出审批判断和退回意见。",
        "source": "recommended_common",
        "tags": ["审批处理"],
    },
    {
        "id": "audience-manager",
        "name": "业务管理人员",
        "description": "负责监控办理效率、查看统计结果和优化规则。",
        "source": "recommended_common",
        "tags": ["运营监控"],
    },
]

COMMON_FLOW_RECOMMENDATIONS: list[dict[str, str | list[str]]] = [
    {
        "id": "flow-submit-review-close",
        "name": "发起-审核-办结",
        "description": "适用于标准审批办理场景，强调发起、审核与办结闭环。",
        "source": "recommended_common",
        "tags": ["审批流程"],
    },
    {
        "id": "flow-submit-collaborate-close",
        "name": "发起-协同处理-办结",
        "description": "适用于需要多个角色共同办理的协同场景。",
        "source": "recommended_common",
        "tags": ["协同办理"],
    },
]

COMMON_STRUCTURE_RECOMMENDATIONS: list[dict[str, str | list[str]]] = [
    {
        "id": "structure-workbench",
        "name": "工作台 + 待办处理页",
        "description": "适用于流程办理场景，承载待办汇总、事项处理和结果回看。",
        "source": "recommended_common",
        "tags": ["工作台", "任务处理"],
    },
    {
        "id": "structure-progress",
        "name": "进度跟踪页",
        "description": "适用于需要跟踪办理过程和状态变化的场景。",
        "source": "recommended_common",
        "tags": ["进度透明", "状态跟踪"],
    },
    {
        "id": "structure-dashboard",
        "name": "业务监控页",
        "description": "适用于管理人员查看效率、瓶颈和办理分布。",
        "source": "recommended_common",
        "tags": ["运营监控", "统计分析"],
    },
]
