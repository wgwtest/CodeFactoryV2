import { Layout, Menu, Select, Space, Typography } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useArchiveContext } from "./context/ArchiveContext";
import { P1CleanApp, P1KnowledgeBaseGateway } from "./features/p1Clean/P1CleanApp";
import { P1RefactorShell } from "./features/p1/shell/P1RefactorShell";
import { ApplicationModelerPage } from "./pages/ApplicationModelerPage";
import { ArchiveManagementPage } from "./pages/ArchiveManagementPage";
import { BuildWorkspacePage } from "./pages/BuildWorkspacePage";
import { DocumentIntakePage } from "./pages/DocumentIntakePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GovernancePage } from "./pages/GovernancePage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import {
  PublicationCandidatePage,
  QualityGateExplanationPage,
  RuleContractEditorPage,
  RuleImpactRecomputePage,
  StagePolicyConfigPage,
  StrategyDiffPage,
  StrategyLibraryPage,
} from "./pages/P1PrototypeWorkflowPages";
import "./pages/P1Workbench.css";
import { P3DesignLabPage } from "./pages/P3DesignLabPage";
import { P3TemplateDetailPage } from "./pages/P3TemplateDetailPage";
import { P6ObservationPage } from "./pages/P6ObservationPage";
import { P6PortalDataPage } from "./pages/P6PortalDataPage";
import { P6PortalPage } from "./pages/P6PortalPage";
import { P6SimulatorPage } from "./pages/P6SimulatorPage";
import { RequirementAnalysisLabPage } from "./pages/RequirementAnalysisLabPage";
import { RequirementAuthoringAdminPage } from "./pages/RequirementAuthoringAdminPage";
import { RequirementAuthoringPage } from "./pages/RequirementAuthoringPage";
import { RequirementsPage } from "./pages/RequirementsPage";
import { XXP1SimPage } from "./pages/XXP1SimPage";
import { XXP2SimPage } from "./pages/XXP2SimPage";
import { XXP3DocSimPage } from "./pages/XXP3DocSimPage";
import { XXP3Page } from "./pages/XXP3Page";
import { XXP3SimPage } from "./pages/XXP3SimPage";
import { XXP4Page } from "./pages/XXP4Page";
import { XXP4SupplySimPage } from "./pages/XXP4SupplySimPage";
import { XXP5SimPage } from "./pages/XXP5SimPage";

const items = [
  { key: "/p1", label: <Link to="/p1">P1 业务入口</Link> },
  { key: "/archives", label: <Link to="/archives">知识库管理</Link> },
  { key: "/documents", label: <Link to="/documents">知识库文档</Link> },
  { key: "/documents/intake", label: <Link to="/documents/intake">接入解析验证</Link> },
  {
    key: "p1-policies",
    label: "策略规则",
    children: [
      { key: "/policies", label: <Link to="/policies">策略库</Link> },
      { key: "/policies/stages", label: <Link to="/policies/stages">阶段策略</Link> },
      { key: "/policies/rule-contract", label: <Link to="/policies/rule-contract">规则合同</Link> },
      { key: "/policies/diff", label: <Link to="/policies/diff">版本差异</Link> },
      { key: "/policies/impact", label: <Link to="/policies/impact">影响重算</Link> },
    ],
  },
  {
    key: "p1-runtime-explain",
    label: "运行解释",
    children: [
      { key: "/runtime/quality-gate", label: <Link to="/runtime/quality-gate">质量门禁</Link> },
      { key: "/runtime/publication", label: <Link to="/runtime/publication">发布候选</Link> },
    ],
  },
  { key: "/governance", label: <Link to="/governance">知识审核发布</Link> },
  { key: "/graph", label: <Link to="/graph">知识图谱</Link> },
  { key: "/requirement-authoring/admin", label: <Link to="/requirement-authoring/admin">P2 配置台</Link> },
  { key: "/requirements", label: <Link to="/requirements">需求规格</Link> },
  { key: "/modeling", label: <Link to="/modeling">建模引导</Link> },
];

function collectMenuRouteKeys(menuItems: typeof items): string[] {
  return menuItems.flatMap((item) =>
    "children" in item && item.children ? collectMenuRouteKeys(item.children) : item.key.startsWith("/") ? [item.key] : [],
  );
}

const mainShellRoutes = new Set(collectMenuRouteKeys(items));

function MainShell() {
  const { activeArchiveId, archives, loading, setActiveArchiveId } = useArchiveContext();
  const location = useLocation();
  const envDefaultRoute = import.meta.env.VITE_DEFAULT_ROUTE;
  const defaultRoute = envDefaultRoute && mainShellRoutes.has(envDefaultRoute) ? envDefaultRoute : "/archives";
  const selectedMenuKey =
    location.pathname === "/"
      ? defaultRoute
      : location.pathname.startsWith("/documents/intake")
        ? "/documents/intake"
        : location.pathname;

  return (
    <Layout className="p1-app-shell">
      <Layout.Header style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
        <div className="p1-brand-lockup">
          <span className="p1-brand-kicker">知识仓库</span>
          <Typography.Title level={3} className="p1-brand-title">
            P1 业务知识库
          </Typography.Title>
          <span className="p1-brand-subtitle">文档接入 → 策略选择 → 机器抽取 → 发布候选 → 治理确认</span>
        </div>
        <Menu
          theme="light"
          mode="horizontal"
          selectedKeys={[selectedMenuKey]}
          items={items}
          style={{ flex: 1, minWidth: 0 }}
        />
        <Space align="center">
          <Typography.Text className="p1-current-archive-label">当前知识库</Typography.Text>
          <Select
            value={activeArchiveId ?? undefined}
            placeholder="选择知识库"
            style={{ width: 240 }}
            loading={loading}
            onChange={(value) => void setActiveArchiveId(value)}
            options={archives.map((item) => ({
              label: item.name,
              value: item.archive_id,
            }))}
          />
        </Space>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <Routes>
          <Route path="/archives" element={<ArchiveManagementPage />} />
          <Route path="/" element={<Navigate to={defaultRoute} replace />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/documents/intake" element={<DocumentIntakePage />} />
          <Route path="/policies" element={<StrategyLibraryPage />} />
          <Route path="/policies/stages" element={<StagePolicyConfigPage />} />
          <Route path="/policies/rule-contract" element={<RuleContractEditorPage />} />
          <Route path="/policies/diff" element={<StrategyDiffPage />} />
          <Route path="/policies/impact" element={<RuleImpactRecomputePage />} />
          <Route path="/runtime/quality-gate" element={<QualityGateExplanationPage />} />
          <Route path="/runtime/publication" element={<PublicationCandidatePage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/requirement-authoring/admin" element={<RequirementAuthoringAdminPage />} />
          <Route path="/requirements" element={<RequirementsPage />} />
          <Route path="/modeling" element={<ApplicationModelerPage />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}

export default function App() {
  const location = useLocation();

  if (location.pathname === "/") {
    return <Navigate to="/portal" replace />;
  }

  if (location.pathname.startsWith("/p1-legacy")) {
    return (
      <Routes>
        <Route path="/p1-legacy/*" element={<P1RefactorShell />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/p1")) {
    return (
      <Routes>
        <Route path="/p1" element={<P1KnowledgeBaseGateway />} />
        <Route path="/p1/archives/:archiveId/*" element={<P1CleanApp />} />
        <Route path="/p1/*" element={<Navigate to="/p1" replace />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/portal-data")) {
    return (
      <Routes>
        <Route path="/portal-data" element={<P6PortalDataPage />} />
      </Routes>
    );
  }

  if (location.pathname === "/portal") {
    return (
      <Routes>
        <Route path="/portal" element={<P6PortalPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/observation")) {
    return (
      <Routes>
        <Route path="/observation" element={<P6ObservationPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/xx-p6-sim")) {
    return (
      <Routes>
        <Route path="/xx-p6-sim" element={<P6SimulatorPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/xx-p1-sim")) {
    return (
      <Routes>
        <Route path="/xx-p1-sim" element={<XXP1SimPage />} />
      </Routes>
    );
  }

  if (location.pathname === "/requirement-authoring") {
    return (
      <Routes>
        <Route path="/requirement-authoring" element={<RequirementAuthoringPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/p3-design-lab")) {
    return (
      <Routes>
        <Route path="/p3-design-lab" element={<P3DesignLabPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/p2-requirement-analysis-lab")) {
    return (
      <Routes>
        <Route path="/p2-requirement-analysis-lab" element={<RequirementAnalysisLabPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/xx-p2-sim")) {
    return (
      <Routes>
        <Route path="/xx-p2-sim" element={<XXP2SimPage />} />
      </Routes>
    );
  }

  if (
    location.pathname.startsWith("/xx-p3-doc-sim") ||
    location.pathname.startsWith("/xx-p4-supply-sim") ||
    location.pathname.startsWith("/xx-p4-sim")
  ) {
    return (
      <Routes>
        <Route path="/xx-p3-doc-sim" element={<XXP3DocSimPage />} />
        <Route path="/xx-p4-supply-sim" element={<XXP4SupplySimPage />} />
        <Route path="/xx-p4-sim" element={<XXP4SupplySimPage />} />
      </Routes>
    );
  }

  if (
    location.pathname.startsWith("/xx-p3-sim") ||
    location.pathname.startsWith("/xx-p4") ||
    location.pathname.startsWith("/xx-p5-sim")
  ) {
    return (
      <Routes>
        <Route path="/xx-p3-sim" element={<XXP3SimPage />} />
        <Route path="/xx-p4" element={<XXP4Page />} />
        <Route path="/xx-p5-sim" element={<XXP5SimPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/xx-p3")) {
    return (
      <Routes>
        <Route path="/xx-p3" element={<XXP3Page />} />
        <Route path="/xx-p3/templates/:templateId" element={<P3TemplateDetailPage />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith("/build")) {
    return (
      <Routes>
        <Route path="/build" element={<BuildWorkspacePage />} />
      </Routes>
    );
  }

  return <MainShell />;
}
