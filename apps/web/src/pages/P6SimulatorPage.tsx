import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  submitP6SimulatorContracts,
  type P6DisplayExportContract,
  type P6SimulatorContractSubmission,
  type P6SimulatorSubmissionResponse,
} from "../lib/p6";

import "./P6SimulatorPage.css";

type StageContractSeed = {
  stageId: "P1" | "P2" | "P3" | "P4" | "P5";
  stageName: string;
  summary: string;
  route: string;
  primaryStatus: string;
  overall: Array<[string, string, number, string, string]>;
  live: Array<[string, string, number, string, string, "input" | "output" | "process"]>;
  inputTarget: string;
  inputLabel: string;
  outputTarget: string;
  outputLabel: string;
  terminalOutput: boolean;
  users: Array<[string, string, string]>;
  queueLabel: string;
  queueItems: string[];
  sourceObject: string;
  prototypeRef: string;
};

const scenarioSeeds: StageContractSeed[] = [
  {
    stageId: "P1",
    stageName: "业务知识库",
    summary: "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人",
    route: "/graph",
    primaryStatus: "knowledge_asset_running",
    overall: [
      ["knowledge_repository_count", "知识库", 12, "个", "累计资产"],
      ["published_knowledge_count", "已发布知识", 12480, "条", "累计产出"],
      ["domain_directory_count", "领域", 36, "个", "累计目录"],
      ["contributor_count", "贡献者", 58, "人", "累计贡献"],
    ],
    live: [
      ["active_knowledge_intake_rate", "正在入库", 18, "条/小时", "1h", "input"],
      ["active_p2_supply_rate", "供给 P2", 12, "条/小时", "1h", "output"],
    ],
    inputTarget: "外部资料",
    inputLabel: "外部知识",
    outputTarget: "P2",
    outputLabel: "发布态知识",
    terminalOutput: false,
    users: [
      ["role:knowledge-governor", "治", "知识治理"],
      ["role:p2-consumer", "需", "P2 接入"],
    ],
    queueLabel: "知识挂载队列",
    queueItems: ["飞行计划约束", "空域移交规则", "异常处置条款", "席位协同规范"],
    sourceObject: "PublishedKnowledge",
    prototypeRef:
      "DOC/CODEX_DOC/08_原型与附图/2026-04-29-183315-CodeFactoryV2-P6业务知识库浅色方形头像端口队列卡详情原型-v12/",
  },
  {
    stageId: "P2",
    stageName: "需求分析系统",
    summary: "支持软件 24 个，需求规格 86 份，业务对象 430 个",
    route: "/requirements",
    primaryStatus: "requirement_modeling_running",
    overall: [
      ["supported_software_count", "支持软件", 24, "个", "累计承载"],
      ["requirement_spec_count", "需求规格", 86, "份", "累计产出"],
      ["business_object_count", "业务对象", 430, "个", "累计建模"],
    ],
    live: [
      ["active_knowledge_receive_rate", "知识接入", 12, "条/小时", "1h", "input"],
      ["active_spec_output_rate", "规格输出", 8, "份/小时", "1h", "output"],
    ],
    inputTarget: "P1",
    inputLabel: "发布态知识",
    outputTarget: "P3",
    outputLabel: "需求规格",
    terminalOutput: false,
    users: [
      ["role:industry-user", "业", "行业用户"],
      ["role:analyst", "析", "需求分析"],
      ["role:domain-expert", "专", "领域专家"],
    ],
    queueLabel: "需求建模队列",
    queueItems: ["空域协同规划", "任务审批流程", "态势看板"],
    sourceObject: "RequirementSpec",
    prototypeRef:
      "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
  },
  {
    stageId: "P3",
    stageName: "软件设计系统",
    summary: "支持软件 36 个，设计基线 112 份，工单包 268 包",
    route: "/modeling",
    primaryStatus: "software_design_running",
    overall: [
      ["supported_software_count", "支持软件", 36, "个", "累计承载"],
      ["design_baseline_count", "设计基线", 112, "份", "累计设计资产"],
      ["work_order_package_count", "工单包", 268, "包", "累计产出"],
    ],
    live: [
      ["active_requirement_input_rate", "规格接入", 8, "份/小时", "1h", "input"],
      ["active_workorder_output_rate", "工单输出", 11, "包/小时", "1h", "output"],
      ["active_design_baseline_sync_rate", "基线同步", 3, "份/小时", "1h", "output"],
    ],
    inputTarget: "P2",
    inputLabel: "需求规格",
    outputTarget: "P4",
    outputLabel: "模块工单包",
    terminalOutput: false,
    users: [
      ["role:architect", "架", "架构设计"],
      ["role:reviewer", "评", "设计评审"],
    ],
    queueLabel: "设计生成队列",
    queueItems: ["边界上下文", "模块接口", "工单包"],
    sourceObject: "SoftwareDesignBaseline",
    prototypeRef:
      "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
  },
  {
    stageId: "P4",
    stageName: "工具仓库",
    summary: "工具定义 286 个，领域目录 42 个，供给结果 620 项",
    route: "/xx-p4",
    primaryStatus: "tool_supply_running",
    overall: [
      ["tool_definition_count", "工具定义", 286, "个", "累计工具资产"],
      ["domain_catalog_count", "领域目录", 42, "个", "累计目录"],
      ["tool_supply_result_count", "供给结果", 620, "项", "累计产出"],
    ],
    live: [
      ["active_matching_rate", "正在匹配", 14, "项/小时", "1h", "process"],
      ["active_supply_output_rate", "工具供给", 10, "项/小时", "1h", "output"],
    ],
    inputTarget: "P3",
    inputLabel: "模块工单包",
    outputTarget: "P5",
    outputLabel: "工具供给",
    terminalOutput: false,
    users: [
      ["role:tool-governor", "治", "资产治理"],
      ["role:tool-dev", "工", "工具开发"],
    ],
    queueLabel: "工具供给队列",
    queueItems: ["能力匹配", "工具补位", "供给校验"],
    sourceObject: "ToolDefinition",
    prototypeRef:
      "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
  },
  {
    stageId: "P5",
    stageName: "软件构建系统",
    summary: "支持软件 24 个，交付版本 86 个，构建尝试 412 次",
    route: "/build",
    primaryStatus: "software_build_running",
    overall: [
      ["supported_software_count", "支持软件", 24, "个", "累计承载"],
      ["delivery_version_count", "交付版本", 86, "个", "累计产出"],
      ["build_attempt_count", "构建尝试", 412, "次", "累计运行事实"],
    ],
    live: [
      ["active_assembly_count", "正在装配", 7, "项", "now", "process"],
      ["delivery_catalog_output_rate", "目录输出", 4, "个/日", "1d", "output"],
    ],
    inputTarget: "P4",
    inputLabel: "工具供给",
    outputTarget: "交付目录",
    outputLabel: "交付目录",
    terminalOutput: true,
    users: [
      ["role:builder", "构", "构建人员"],
      ["role:verifier", "验", "验证人员"],
    ],
    queueLabel: "构建交付队列",
    queueItems: ["装配对象", "构建验证", "目录导出"],
    sourceObject: "P5DeliveryOrder",
    prototypeRef:
      "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
  },
];

function buildContract(seed: StageContractSeed, index: number): P6DisplayExportContract {
  const capturedAt = `2026-04-29T20:${50 + index}:00+08:00`;
  const flowPorts: P6DisplayExportContract["flow_ports"] = [];
  if (seed.stageId !== "P1") {
    flowPorts.push({
      port_id: `${seed.stageId.toLowerCase()}_input`,
      side: "left",
      direction: "input",
      label: seed.inputLabel,
      connected_target: seed.inputTarget,
      current_rate: `${seed.live[0]?.[2] ?? 0} ${seed.live[0]?.[3] ?? "项/小时"}`,
      terminal: false,
    });
  }
  flowPorts.push({
    port_id: `${seed.stageId.toLowerCase()}_output`,
    side: "right",
    direction: "output",
    label: seed.outputLabel,
    connected_target: seed.outputTarget,
    current_rate: `${seed.live[1]?.[2] ?? 0} ${seed.live[1]?.[3] ?? "项/小时"}`,
    terminal: seed.terminalOutput,
  });
  if (seed.stageId === "P3") {
    const baselineCounter = seed.live.find(([key]) => key === "active_design_baseline_sync_rate");
    flowPorts.push({
      port_id: "p3_p5_baseline_output",
      side: "right",
      direction: "output",
      label: "设计基线",
      connected_target: "P5",
      current_rate: `${baselineCounter?.[2] ?? 3} ${baselineCounter?.[3] ?? "份/小时"}`,
      terminal: false,
    });
  }
  return {
    contract_version: "P6DisplayExportContract.v2",
    stage_overview: {
      stage_id: seed.stageId,
      stage_name: seed.stageName,
      stage_display_name: seed.stageName,
      primary_status: seed.primaryStatus,
      summary: seed.summary,
      updated_at: capturedAt,
      freshness: "fresh",
    },
    entry_projection: {
      entry_route: seed.route,
      entry_available: true,
      entry_reason: `${seed.stageName} 入口可用`,
    },
    system_overall_metrics: seed.overall.map(([key, label, value, unit, basis]) => ({ key, label, value, unit, basis })),
    live_counters: seed.live.map(([key, label, value, unit, window, direction]) => ({
      key,
      label,
      value,
      unit,
      window,
      direction,
    })),
    flow_ports: flowPorts,
    connected_users: seed.users.map(([user_ref, display_label, role_label]) => ({
      user_ref,
      display_label,
      role_label,
      activity_state: "active",
      connected_at: capturedAt,
    })),
    queue_projection: {
      queue_id: `${seed.stageId.toLowerCase()}-display-queue`,
      label: seed.queueLabel,
      items: seed.queueItems.map((label, order_index) => ({
        item_id: `${seed.stageId.toLowerCase()}-queue-${order_index + 1}`,
        label,
        state: order_index === 0 ? "active" : "waiting",
        order_index,
      })),
      active_index: 0,
      advance_rule: "active_done_then_shift_left",
    },
    display_binding: {
      prototype_refs: [seed.prototypeRef],
      regions: {
        top_participants: "connected_users",
        middle_overall: "system_overall_metrics",
        lower_realtime: "live_counters",
        left_input_port: seed.stageId === "P1" ? "queue_projection" : "flow_ports[input]",
        right_output_port: "flow_ports[output]",
        bottom_queue: "queue_projection",
      },
    },
    health_projection: {
      health_level: "healthy",
      health_message: `${seed.stageName} 模拟合同已接入`,
      health_source: "p6_contract_simulator",
      captured_at: capturedAt,
    },
    source_trace: seed.overall.map(([key, label, , , basis]) => ({
      field: `system_overall_metrics.${key}`,
      source_doc: `DOC/CODEX_DOC/02_设计说明/${seed.stageId}_${seed.stageName}/${seed.stageId}-${seed.stageName}设计.md`,
      source_object: seed.sourceObject,
      calculation_basis: basis,
      freshness_policy: "mock-fresh",
      display_reason: `${label} 绑定详情卡中段总体状态`,
    })),
    stage_specific: Object.fromEntries(seed.overall.map(([key, , value]) => [key, value])),
  };
}

function buildSubmission(): P6SimulatorContractSubmission {
  return {
    scenario_id: "simulator-latest",
    label: "合同模拟器",
    description: "由 P6 合同模拟器发送的五阶段展示输出合同。",
    recommended_focus_stage: "P3",
    contracts: scenarioSeeds.map(buildContract),
  };
}

export function P6SimulatorPage() {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<P6SimulatorSubmissionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const submission = useMemo(buildSubmission, []);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await submitP6SimulatorContracts(submission);
      setResult(response.data);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "发送模拟合同失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="p6-simulator-page">
      <section className="p6-simulator-hero">
        <div>
          <span className="p6-simulator-hero__badge">P6DisplayExportContract.v2</span>
          <h1>P6 合同模拟器</h1>
          <p>在 P1 到 P5 真实读源完成前，由本页发送约定的五阶段展示合同，驱动 P6 门户按当前原型结构显示。</p>
        </div>
        <div className="p6-simulator-hero__actions">
          <button type="button" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "发送中" : "发送模拟合同"}
          </button>
          {result ? <Link to={result.portal_projection_path}>打开 P6 门户</Link> : null}
          {result ? <Link to={result.portal_data_path}>打开图表视图</Link> : null}
        </div>
      </section>

      <section className="p6-simulator-contract-grid">
        {submission.contracts.map((contract) => {
          const inputPort = contract.flow_ports.find((port) => port.direction === "input");
          const outputPort = contract.flow_ports.find((port) => port.direction === "output");
          return (
            <article key={contract.stage_overview.stage_id} className="p6-simulator-contract-card">
              <div className="p6-simulator-contract-card__topline">
                <span>{contract.stage_overview.stage_display_name}</span>
                <strong>{contract.connected_users.length} 人接入</strong>
              </div>
              <div className="p6-simulator-contract-card__summary">{contract.stage_overview.summary}</div>
              <div className="p6-simulator-contract-card__metrics">
                {contract.system_overall_metrics.slice(0, 3).map((metric) => (
                  <span key={metric.key}>
                    {metric.label} {metric.value}
                    {metric.unit}
                  </span>
                ))}
              </div>
              <div className="p6-simulator-contract-card__ports">
                <span>
                  输入 <em>{inputPort?.connected_target ?? contract.queue_projection.label}</em>
                </span>
                <span>
                  输出 <em>{outputPort?.connected_target}</em>
                  {outputPort?.terminal ? " · 终端" : ""}
                </span>
              </div>
              <div className="p6-simulator-contract-card__queue">
                {contract.queue_projection.label} · {contract.queue_projection.items.length} 项顺序前移
              </div>
            </article>
          );
        })}
      </section>

      {result ? <div className="p6-simulator-status">已发送 {result.accepted_contract_count} 个阶段合同</div> : null}
      {error ? <div className="p6-simulator-status p6-simulator-status--error">{error}</div> : null}
    </main>
  );
}
