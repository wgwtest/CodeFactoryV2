import { Layout, Menu, Select, Space, Typography } from "antd";
import { Link, Route, Routes, useLocation } from "react-router-dom";

import { useArchiveContext } from "./context/ArchiveContext";
import { ArchiveManagementPage } from "./pages/ArchiveManagementPage";
import { ApplicationModelerPage } from "./pages/ApplicationModelerPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GovernancePage } from "./pages/GovernancePage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { ProcessViewPage } from "./pages/ProcessViewPage";
import { RequirementsPage } from "./pages/RequirementsPage";

const items = [
  { key: "/archives", label: <Link to="/archives">知识库管理</Link> },
  { key: "/", label: <Link to="/">文档导入</Link> },
  { key: "/governance", label: <Link to="/governance">知识审核发布</Link> },
  { key: "/graph", label: <Link to="/graph">知识图谱</Link> },
  { key: "/processes", label: <Link to="/processes">流程视图</Link> },
  { key: "/requirements", label: <Link to="/requirements">需求规格</Link> },
  { key: "/modeling", label: <Link to="/modeling">建模引导</Link> },
];

export default function App() {
  const { activeArchiveId, archives, loading, setActiveArchiveId } = useArchiveContext();
  const location = useLocation();
  const selectedMenuKey = location.pathname === "/documents" ? "/" : location.pathname;

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
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/processes" element={<ProcessViewPage />} />
          <Route path="/requirements" element={<RequirementsPage />} />
          <Route path="/modeling" element={<ApplicationModelerPage />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}
