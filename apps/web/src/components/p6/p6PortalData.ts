export type P6PortalNodeId = "user" | "p1" | "p2" | "p3" | "p4" | "p5";

export type P6PortalAnchorSide = "left" | "right" | "top" | "bottom";

export type P6PortalPosition = {
  x: number;
  y: number;
};

export type P6PortalNode = {
  id: P6PortalNodeId;
  title: string;
  stage?: string;
  summary: string;
  status: string;
  metrics: string[];
  route?: string;
  accent: string;
  width: number;
  height: number;
  kind: "user" | "module";
  description: string;
};

export type P6PortalFlow = {
  id: string;
  from: P6PortalNodeId;
  to: P6PortalNodeId;
  fromSide: P6PortalAnchorSide;
  toSide: P6PortalAnchorSide;
  label: string;
  tone: "knowledge" | "analysis" | "design" | "tooling" | "delivery";
};

export const P6_PORTAL_LAYOUT_STORAGE_KEY = "code-factory.p6.portal.layout";

export const P6_PORTAL_WORLD = {
  width: 1920,
  height: 1080,
};

export const p6PortalNodes: P6PortalNode[] = [
  {
    id: "user",
    title: "行业用户",
    summary: "以业务语言提出应用目标",
    status: "持续接入",
    metrics: ["问题定义", "对象确认", "目标澄清"],
    accent: "#2563eb",
    width: 220,
    height: 160,
    kind: "user",
    description: "行业专家以业务视角进入平台，关注对象、场景、边界和目标，而不是技术实现细节。",
  },
  {
    id: "p1",
    title: "业务知识库",
    stage: "P1",
    summary: "沉淀领域对象、事件、流程与释义",
    status: "知识供给运行中",
    metrics: ["实体 1305", "事件 88", "流程 42"],
    route: "/graph",
    accent: "#0f766e",
    width: 330,
    height: 188,
    kind: "module",
    description: "负责把原始资料沉淀为可追溯、可筛选、可查询的业务知识元素，并向下游提供稳定知识出口。",
  },
  {
    id: "p2",
    title: "需求分析系统",
    stage: "P2",
    summary: "把业务语言组织成结构化需求对象",
    status: "建模路径收敛中",
    metrics: ["待建模 7", "规格说明 3", "对象优先"],
    route: "/requirements",
    accent: "#2563eb",
    width: 340,
    height: 196,
    kind: "module",
    description: "通过选配式和表单式建模，把用户输入组织成需求规格说明与结构化需求模型。",
  },
  {
    id: "p3",
    title: "软件设计系统",
    stage: "P3",
    summary: "消费规格说明，转成软件设计说明",
    status: "结构表达准备中",
    metrics: ["设计任务 4", "结构说明 2", "工具化描述"],
    route: "/modeling",
    accent: "#4f46e5",
    width: 340,
    height: 196,
    kind: "module",
    description: "承接需求规格说明，形成软件设计说明，并进一步导出工具可消费的结构化设计表达。",
  },
  {
    id: "p4",
    title: "工具仓库 / 工具中台",
    stage: "P4",
    summary: "承载工具能力、匹配分析与调用编排",
    status: "工具匹配在线推演",
    metrics: ["工具 18", "匹配中 6", "调用链 11"],
    route: "/xx-p4",
    accent: "#ca8a04",
    width: 360,
    height: 196,
    kind: "module",
    description: "沉淀工具能力与匹配规则，支撑设计产物向执行能力映射和后续编排。",
  },
  {
    id: "p5",
    title: "软件构建系统",
    stage: "P5",
    summary: "整合设计说明、组件与工具形成应用",
    status: "构建链准备就绪",
    metrics: ["构建链 5", "应用骨架 2", "集成待验证"],
    route: "/build",
    accent: "#dc2626",
    width: 350,
    height: 196,
    kind: "module",
    description: "结合设计说明、工具中台和组件资产，执行应用构建、集成与结果输出。",
  },
];

export const p6PortalFlows: P6PortalFlow[] = [
  {
    id: "user-p2",
    from: "user",
    to: "p2",
    fromSide: "right",
    toSide: "left",
    label: "需求进入",
    tone: "analysis",
  },
  {
    id: "p1-p2",
    from: "p1",
    to: "p2",
    fromSide: "top",
    toSide: "bottom",
    label: "知识供给",
    tone: "knowledge",
  },
  {
    id: "p2-p3",
    from: "p2",
    to: "p3",
    fromSide: "right",
    toSide: "left",
    label: "规格说明",
    tone: "analysis",
  },
  {
    id: "p3-p4",
    from: "p3",
    to: "p4",
    fromSide: "bottom",
    toSide: "top",
    label: "工具匹配",
    tone: "tooling",
  },
  {
    id: "p4-p5",
    from: "p4",
    to: "p5",
    fromSide: "right",
    toSide: "left",
    label: "构建执行",
    tone: "delivery",
  },
  {
    id: "p3-p5",
    from: "p3",
    to: "p5",
    fromSide: "right",
    toSide: "left",
    label: "设计落地",
    tone: "design",
  },
];

export const defaultP6PortalLayout: Record<P6PortalNodeId, P6PortalPosition> = {
  user: { x: 110, y: 430 },
  p1: { x: 400, y: 660 },
  p2: { x: 410, y: 210 },
  p3: { x: 960, y: 200 },
  p4: { x: 1040, y: 650 },
  p5: { x: 1500, y: 410 },
};

export const p6PortalLegendRoadmap = [
  { id: "p6.2", label: "登录接入", status: "占位" },
  { id: "p6.3", label: "权限与角色控制", status: "占位" },
  { id: "p6.4", label: "入口与导航治理", status: "占位" },
];

export function readP6PortalLayout() {
  if (typeof window === "undefined") {
    return defaultP6PortalLayout;
  }

  try {
    const raw = window.localStorage.getItem(P6_PORTAL_LAYOUT_STORAGE_KEY);
    if (!raw) {
      return defaultP6PortalLayout;
    }

    const parsed = JSON.parse(raw) as Partial<Record<P6PortalNodeId, P6PortalPosition>>;
    return {
      ...defaultP6PortalLayout,
      ...parsed,
    };
  } catch {
    return defaultP6PortalLayout;
  }
}
