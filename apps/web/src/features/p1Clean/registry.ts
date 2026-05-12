import { IntakePage } from "./modules/intake/page";
import { KnowledgeResultsPage } from "./modules/knowledgeResults/page";
import { PolicyRulesPage } from "./modules/policyRules/page";
import { PublicationPage } from "./modules/publication/page";
import { QualityGraphPage } from "./modules/qualityGraph/page";
import { RuntimePage } from "./modules/runtime/page";
import { SystemOutputPage } from "./modules/systemOutput/page";
import type { P1ModuleDefinition } from "./types";

export const p1WorkspaceModules: P1ModuleDefinition[] = [
  {
    id: "intake",
    navLabel: "资料接入",
    title: "资料接入",
    route: "intake",
    order: 10,
    lifecycle: "scaffold",
    summary: "绑定资料源、扫描文件、解析预检，输出 documentSetId。",
    contract: {
      inputs: ["archiveId", "policyPackageVersionId"],
      outputs: ["documentSetId"],
      owns: ["文档集合", "解析预检状态", "接入任务"],
      consumes: ["知识库基础信息", "策略版本建议"],
    },
    Page: IntakePage,
  },
  {
    id: "policyRules",
    navLabel: "策略规则",
    title: "策略规则",
    route: "policy",
    order: 20,
    lifecycle: "scaffold",
    summary: "管理策略包版本、规则字段合同、动作映射和 RuleExecutionRecord。",
    contract: {
      inputs: ["archiveId"],
      outputs: ["policyPackageVersionId"],
      owns: ["策略包版本", "规则输入输出合同", "规则变更影响面"],
      consumes: ["知识库类型", "资料类型摘要"],
    },
    Page: PolicyRulesPage,
  },
  {
    id: "runtime",
    navLabel: "抽取运行",
    title: "抽取运行",
    route: "runtime",
    order: 30,
    lifecycle: "scaffold",
    summary: "消费 documentSetId 和 policyPackageVersionId，输出 runtimeSnapshotId。",
    contract: {
      inputs: ["archiveId", "documentSetId", "policyPackageVersionId"],
      outputs: ["runtimeSnapshotId"],
      owns: ["实时事件流", "运行阶段状态", "运行态语义图谱"],
      consumes: ["文档集合", "策略规则合同"],
    },
    Page: RuntimePage,
  },
  {
    id: "qualityGraph",
    navLabel: "质量图谱",
    title: "质量图谱",
    route: "quality",
    order: 40,
    lifecycle: "scaffold",
    summary: "消费 runtimeSnapshotId，衡量概念质量、关系质量、对象级质量发现和图谱可解释性。",
    contract: {
      inputs: ["archiveId", "runtimeSnapshotId", "policyPackageVersionId"],
      outputs: [],
      owns: ["质量指标", "对象级质量发现", "门禁解释", "图谱质量视图"],
      consumes: ["运行快照", "策略版本"],
    },
    Page: QualityGraphPage,
  },
  {
    id: "knowledgeResults",
    navLabel: "知识成果",
    title: "知识成果查看",
    route: "results",
    order: 45,
    lifecycle: "scaffold",
    summary: "查看当前知识库已经抽取出的知识对象、关系、证据与入库状态。",
    contract: {
      inputs: ["archiveId", "publicationSnapshotId"],
      outputs: [],
      owns: ["知识对象查看", "关系边查看", "证据与来源追溯"],
      consumes: ["抽取工作态知识", "发布候选快照", "正式入库版本"],
    },
    Page: KnowledgeResultsPage,
  },
  {
    id: "publication",
    navLabel: "发布输出",
    title: "发布输出",
    route: "publication",
    order: 50,
    lifecycle: "scaffold",
    summary: "生成发布候选快照；只有质量放行并治理确认后才输出正式 publicationSnapshotId。",
    contract: {
      inputs: ["archiveId", "runtimeSnapshotId"],
      outputs: ["publicationSnapshotId"],
      owns: ["发布候选", "候选快照", "质量阻断解释", "治理确认状态投影"],
      consumes: ["质量决策", "运行快照"],
    },
    Page: PublicationPage,
  },
  {
    id: "systemOutput",
    navLabel: "系统间输出",
    title: "系统间输出接口",
    route: "system-output",
    order: 60,
    lifecycle: "scaffold",
    summary: "严格消费治理确认后的 publicationSnapshotId，向后续系统供应正式知识接口。",
    contract: {
      inputs: ["archiveId", "publicationSnapshotId"],
      outputs: [],
      owns: ["正式知识供应合同", "系统间 API 范围", "版本输出说明"],
      consumes: ["治理确认后的发布快照"],
    },
    Page: SystemOutputPage,
  },
];
