import { Layout, Menu, Select, Space, Typography } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useArchiveContext } from "./context/ArchiveContext";
import { ArchiveManagementPage } from "./pages/ArchiveManagementPage";
import { ApplicationModelerPage } from "./pages/ApplicationModelerPage";
import { BuildWorkspacePage } from "./pages/BuildWorkspacePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GovernancePage } from "./pages/GovernancePage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { P6PortalPage } from "./pages/P6PortalPage";
import { P3TemplateDetailPage } from "./pages/P3TemplateDetailPage";
import { RequirementsPage } from "./pages/RequirementsPage";
import { XXP2SimPage } from "./pages/XXP2SimPage";
import { XXP3Page } from "./pages/XXP3Page";
import { XXP3SimPage } from "./pages/XXP3SimPage";
import { XXP4Page } from "./pages/XXP4Page";
import { XXP5SimPage } from "./pages/XXP5SimPage";

const items = [
  { key: "/archives", label: <Link to="/archives">知识库管理</Link> },
  { key: "/documents", label: <Link to="/documents">文档导入</Link> },
  { key: "/governance", label: <Link to="/governance">知识审核发布</Link> },
  { key: "/graph", label: <Link to="/graph">知识图谱</Link> },
  { key: "/requirements", label: <Link to="/requirements">需求规格</Link> },
  { key: "/modeling", label: <Link to="/modeling">建模引导</Link> },
];

function MainShell() {
  const { activeArchiveId, archives, loading, setActiveArchiveId } = useArchiveContext();
  const location = useLocation();
  const selectedMenuKey = location.pathname;
  const defaultRoute = import.meta.env.VITE_DEFAULT_ROUTE ?? "/documents";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
          知识仓库
        </Typography.Title>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedMenuKey]}
          items={items}
          style={{ flex: 1, minWidth: 0 }}
        />
        <Space align="center">
          <Typography.Text style={{ color: "#fff" }}>当前知识库</Typography.Text>
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
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/requirements" element={<RequirementsPage />} />
          <Route path="/modeling" element={<ApplicationModelerPage />} />
          <Route path="/build" element={<BuildWorkspacePage />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}

export default function App() {
  const location = useLocation();

  if (location.pathname.startsWith("/portal")) {
    return (
      <Routes>
        <Route path="/portal" element={<P6PortalPage />} />
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

  return <MainShell />;
}
