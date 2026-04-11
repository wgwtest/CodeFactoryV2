import { Layout, Menu, Typography } from "antd";
import { Link, Route, Routes, useLocation } from "react-router-dom";

import { DocumentsPage } from "./pages/DocumentsPage";
import { GovernancePage } from "./pages/GovernancePage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { ProcessViewPage } from "./pages/ProcessViewPage";

const items = [
  { key: "/", label: <Link to="/">Documents</Link> },
  { key: "/governance", label: <Link to="/governance">Governance</Link> },
  { key: "/graph", label: <Link to="/graph">Knowledge Graph</Link> },
  { key: "/processes", label: <Link to="/processes">Process View</Link> }
];

export default function App() {
  const location = useLocation();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
          Knowledge Warehouse
        </Typography.Title>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={items}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <Routes>
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/processes" element={<ProcessViewPage />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}
