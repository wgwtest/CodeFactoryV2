import { DEFAULT_ARCHIVE_ID } from "./archiveKnowledge";
import type { RequirementSpecPayload, RequirementSpecWriteInput } from "./api";

export type P2SimTemplate = {
  template_id: "platform-business-system" | "monolith-business-software" | "workflow-approval-tool";
  title: string;
  badge: string;
  use_case: string;
  preview_summary: string;
  fit_for: string;
  payload: RequirementSpecPayload;
};

function clonePayload(payload: RequirementSpecPayload): RequirementSpecPayload {
  return JSON.parse(JSON.stringify(payload)) as RequirementSpecPayload;
}

export const p2SimTemplates: P2SimTemplate[] = [
  {
    template_id: "platform-business-system",
    title: "平台级业务系统",
    badge: "平台协同",
    use_case: "适合平台级业务系统、跨角色协同场景和明显的系统边界输入。",
    preview_summary: "围绕平台协同、任务分发和运行留痕构造一份可直接进入 P3 的轻量需规。",
    fit_for: "适合作为平台级软件工厂的标准上游样板。",
    payload: {
      application: {
        name: "空域协同指挥平台",
        domain: "国家空域管理",
        summary: "围绕任务协同、运行监视和状态留痕形成统一平台能力。",
        target_users: ["值班指挥员", "规划员", "体系架构师"],
      },
      objects: [
        {
          id: "coord-task",
          name: "协同任务",
          object_kind: "business",
          source_kind: "temporary",
          category: "domain_object",
          aliases: [],
          summary: "承载跨角色协同处理的核心业务对象。",
          description: "描述任务状态、责任人、协同结果和审计信息。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "coord-plan",
          name: "协同方案",
          object_kind: "business",
          source_kind: "temporary",
          category: "domain_object",
          aliases: [],
          summary: "描述任务对应的方案输出。",
          description: "用于沉淀任务分解、方案建议和执行结论。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "ops-log",
          name: "运行留痕记录",
          object_kind: "supporting",
          source_kind: "temporary",
          category: "audit_record",
          aliases: [],
          summary: "记录关键操作、审批和状态变更。",
          description: "为平台级系统提供可追溯的留痕能力。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      processes: [
        {
          id: "task-collaboration",
          name: "协同任务闭环",
          process_kind: "collaboration",
          source_kind: "temporary",
          description: "任务创建、协同处理、结果确认和留痕归档。",
          participant_object_ids: ["coord-task", "coord-plan", "ops-log"],
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "status-monitor",
          name: "运行状态监视",
          process_kind: "lifecycle",
          source_kind: "temporary",
          description: "监视平台关键任务状态并触发异常提示。",
          participant_object_ids: ["coord-task", "ops-log"],
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      rules: [
        {
          id: "rule-task-trace",
          name: "任务状态必须可追溯",
          description: "协同任务的关键状态流转需要完整记录责任人和时间点。",
        },
        {
          id: "rule-platform-view",
          name: "平台需要统一任务视图",
          description: "不同角色看到的任务状态必须保持统一口径。",
        },
      ],
      metrics: [
        {
          id: "metric-task-cycle",
          name: "任务闭环时长",
          description: "统计协同任务从创建到闭环的平均处理时长。",
        },
        {
          id: "metric-monitor-latency",
          name: "状态刷新时延",
          description: "监视视图中的关键状态更新需要在可接受时延内呈现。",
        },
      ],
      non_functional_constraints: [
        {
          id: "nfr-audit",
          name: "全链路留痕",
          category: "audit",
          description: "关键操作、审批和状态变更需要全链路可追溯。",
        },
        {
          id: "nfr-intranet",
          name: "内网优先部署",
          category: "deployment",
          description: "首版默认以内网部署为前提，不依赖公网服务。",
        },
      ],
    },
  },
  {
    template_id: "monolith-business-software",
    title: "单体业务软件",
    badge: "单体软件",
    use_case: "适合边界明确、模块数量较少的软件级输入。",
    preview_summary: "围绕单一业务域构造轻量需求输入，适合直接展开为软件级软设。",
    fit_for: "适合小到中型业务软件和首版单体服务样板。",
    payload: {
      application: {
        name: "值班排班管理软件",
        domain: "运行保障",
        summary: "围绕排班计划、值班调整和结果查询形成单体业务软件能力。",
        target_users: ["排班员", "值班主管"],
      },
      objects: [
        {
          id: "shift-plan",
          name: "排班计划",
          object_kind: "business",
          source_kind: "temporary",
          category: "domain_object",
          aliases: [],
          summary: "记录班次安排与人员分配。",
          description: "用于维护排班日期、班次和人员信息。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "adjustment-request",
          name: "调班申请",
          object_kind: "business",
          source_kind: "temporary",
          category: "domain_object",
          aliases: [],
          summary: "记录值班调换与确认过程。",
          description: "用于处理临时值班调整和确认记录。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      processes: [
        {
          id: "shift-publishing",
          name: "排班发布流程",
          process_kind: "lifecycle",
          source_kind: "temporary",
          description: "排班编制、确认和发布。",
          participant_object_ids: ["shift-plan"],
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      rules: [
        {
          id: "rule-shift-conflict",
          name: "排班冲突不可发布",
          description: "同一人员在同一时间段存在冲突时不可发布排班。",
        },
        {
          id: "rule-adjustment-confirmed",
          name: "调班必须双向确认",
          description: "值班调整必须由双方确认后方可生效。",
        },
      ],
      metrics: [
        {
          id: "metric-publish-rate",
          name: "按时发布率",
          description: "统计排班计划按时发布的比例。",
        },
        {
          id: "metric-adjustment-cycle",
          name: "调班处理时长",
          description: "统计调班申请从提交到确认的平均时长。",
        },
      ],
      non_functional_constraints: [
        {
          id: "nfr-usability",
          name: "值班场景易用性",
          category: "usability",
          description: "排班和调班操作应支持值班场景下的快速处理。",
        },
        {
          id: "nfr-export",
          name: "导出能力",
          category: "interoperability",
          description: "排班结果应支持标准化导出，便于外部通报。",
        },
      ],
    },
  },
  {
    template_id: "workflow-approval-tool",
    title: "流程审批工具",
    badge: "审批流",
    use_case: "适合审批、会签、状态流转和审计留痕类工具输入。",
    preview_summary: "流程立项、部门会签和状态留痕。",
    fit_for: "适合快速联调 P3 中的状态流、评审和模块工单拆解。",
    payload: {
      application: {
        name: "研发立项审批工具",
        domain: "流程审批",
        summary: "流程立项、部门会签和状态留痕",
        target_users: ["项目经理", "部门负责人", "PMO"],
      },
      objects: [
        {
          id: "approval-request",
          name: "立项申请单",
          object_kind: "business",
          source_kind: "temporary",
          category: "domain_object",
          aliases: [],
          summary: "记录立项申请的主体信息。",
          description: "用于维护申请内容、申请部门和审批状态。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "approval-opinion",
          name: "审批意见",
          object_kind: "supporting",
          source_kind: "temporary",
          category: "review_record",
          aliases: [],
          summary: "记录审批节点的处理意见。",
          description: "用于沉淀会签意见、结论和处理时间。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "approval-log",
          name: "状态留痕",
          object_kind: "supporting",
          source_kind: "temporary",
          category: "audit_record",
          aliases: [],
          summary: "记录申请单状态变化。",
          description: "为审批流提供全链路状态留痕。",
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      processes: [
        {
          id: "approval-flow",
          name: "立项审批流程",
          process_kind: "collaboration",
          source_kind: "temporary",
          description: "提交申请、部门会签、PMO 审核和结论归档。",
          participant_object_ids: ["approval-request", "approval-opinion", "approval-log"],
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
        {
          id: "status-audit",
          name: "状态追踪流程",
          process_kind: "lifecycle",
          source_kind: "temporary",
          description: "跟踪审批流关键状态变化并支持查询。",
          participant_object_ids: ["approval-request", "approval-log"],
          source_archive_id: null,
          source_item_type: null,
          source_item_id: null,
        },
      ],
      rules: [
        {
          id: "rule-sign-required",
          name: "关键节点必须留意见",
          description: "部门会签和 PMO 审核节点必须填写审批意见。",
        },
        {
          id: "rule-status-sequence",
          name: "状态必须按流程顺序流转",
          description: "审批状态不可跳跃更新，必须按既定流程顺序推进。",
        },
      ],
      metrics: [
        {
          id: "metric-approval-cycle",
          name: "平均审批周期",
          description: "统计立项申请从提交到归档的平均时长。",
        },
        {
          id: "metric-return-rate",
          name: "退回率",
          description: "统计申请单被退回修改的比例。",
        },
      ],
      non_functional_constraints: [
        {
          id: "nfr-audit",
          name: "审批留痕完整性",
          category: "audit",
          description: "审批意见、处理人和状态流转必须完整可追溯。",
        },
        {
          id: "nfr-availability",
          name: "工作时段可用性",
          category: "availability",
          description: "工作日审批高峰时段需要保证稳定可用。",
        },
      ],
    },
  },
];

export function buildP2SimWriteInput(template: P2SimTemplate, archiveId?: string | null): RequirementSpecWriteInput {
  return {
    archive_id: archiveId ?? DEFAULT_ARCHIVE_ID,
    status: "ready",
    payload: clonePayload(template.payload),
  };
}
