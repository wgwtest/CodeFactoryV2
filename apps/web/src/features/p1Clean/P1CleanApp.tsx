import { useEffect, useState } from "react";

import { Alert, Button, Card, Col, Layout, Menu, Row, Select, Space, Tag, Typography } from "antd";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";

import { useArchiveContext } from "../../context/ArchiveContext";
import { getArchivePolicyConfig } from "../../lib/archives";
import {
  getArchivePolicyLabel,
  getArchiveSnapshotLabel,
  getArchiveStatusColor,
  getArchiveStatusLabel,
} from "./archivePresentation";
import { PageFrame } from "./common/PageFrame";
import { KnowledgeBaseManagementPage } from "./modules/knowledgeBaseManagement/page";
import { P1_POLICY_CONFIG_UPDATED_EVENT } from "./events";
import { p1WorkspaceModules } from "./registry";
import { buildP1WorkspacePath, buildWorkspaceMenuItems, resolveActiveModuleRoute } from "./routing";
import type { P1ModuleDefinition, P1WorkspaceContext } from "./types";
import "./P1CleanApp.css";

export { KnowledgeBaseManagementPage as P1KnowledgeBaseGateway };

type PolicyConfigSummary = {
  policyPackageName: string | null;
  policyPackageVersionId: string | null;
  policyPackageVersionStatus: string | null;
  policyContractStatus: string | null;
};

export function buildWorkspaceContext(
  archiveId: string,
  archive: P1WorkspaceContext["archive"],
  policyPackageVersionIdFromConfig: string | null = null,
): P1WorkspaceContext {
  const policySnapshot = archive.build_state?.policy_snapshot;

  return {
    archiveId,
    archive,
    policyPackageVersionId: policySnapshot?.policy_package_version_id ?? policyPackageVersionIdFromConfig,
    runtimeSnapshotId: policySnapshot?.run_id ?? null,
    documentSetId: `${archiveId}:document-set`,
    publicationSnapshotId: archive.artifacts.publication_exists ? `${archiveId}:latest-publication` : null,
  };
}

function getWorkspacePolicyLabel(archive: P1WorkspaceContext["archive"], policyConfigSummary: PolicyConfigSummary | null) {
  if (policyConfigSummary?.policyPackageVersionId) {
    const parts = [
      policyConfigSummary.policyPackageVersionStatus,
      policyConfigSummary.policyContractStatus,
    ].filter(Boolean);
    return parts.length > 0
      ? `${parts.join(" / ")}：${policyConfigSummary.policyPackageVersionId}`
      : policyConfigSummary.policyPackageVersionId;
  }

  const snapshot = archive.build_state?.policy_snapshot;
  if (snapshot?.policy_package_version_id) {
    return snapshot.policy_package_version_id;
  }
  if (policyConfigSummary?.policyPackageName) {
    return policyConfigSummary.policyPackageName;
  }

  return getArchivePolicyLabel(archive);
}

function P1WorkspaceOverview({
  context,
  modules,
}: {
  context: P1WorkspaceContext;
  modules: P1ModuleDefinition[];
}) {
  const navigate = useNavigate();

  return (
    <PageFrame
      eyebrow="P1 工作区总览"
      title="单知识库工作区"
      description="这里不承载具体业务逻辑，只展示当前知识库上下文、模块边界和模块状态；具体能力由各模块独立实现。"
    >
      <Alert
        className="p1-clean-alert"
        type="info"
        showIcon
        message="模块边界优先"
        description="导航、路由、模块状态都来自统一注册表。后续并行线程只改自己的模块目录，不直接跨模块读内部状态。"
      />
      <Row gutter={[16, 16]}>
        {modules
          .slice()
          .sort((left, right) => left.order - right.order)
          .map((module) => (
            <Col xs={24} md={12} xl={8} key={module.id}>
              <Card
                className="p1-clean-card"
                title={
                  <Space direction="vertical" size={2}>
                    <Typography.Text strong>{module.title}</Typography.Text>
                    <Typography.Text type="secondary">{module.summary}</Typography.Text>
                  </Space>
                }
                extra={<Tag color={module.lifecycle === "active" ? "green" : "blue"}>{module.lifecycle}</Tag>}
              >
                <Space direction="vertical" className="p1-module-card-body">
                  <Typography.Text>输入：{module.contract.inputs.join(" / ") || "无"}</Typography.Text>
                  <Typography.Text>输出：{module.contract.outputs.join(" / ") || "无"}</Typography.Text>
                  <Typography.Text>当前知识库：{context.archive.name}</Typography.Text>
                  <Button type="primary" onClick={() => navigate(buildP1WorkspacePath(context.archiveId, module.route))}>
                    进入模块
                  </Button>
                </Space>
              </Card>
            </Col>
          ))}
      </Row>
    </PageFrame>
  );
}

export function P1CleanApp() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ archiveId: string }>();
  const { archives, activeArchiveId, loading, setActiveArchiveId } = useArchiveContext();
  const routeArchiveId = params.archiveId;
  const activeModuleRoute = resolveActiveModuleRoute(location.pathname, p1WorkspaceModules);
  const activeArchive = archives.find((item) => item.archive_id === routeArchiveId) ?? null;
  const [policyPackageVersionIdFromConfig, setPolicyPackageVersionIdFromConfig] = useState<string | null>(null);
  const [policyConfigSummary, setPolicyConfigSummary] = useState<PolicyConfigSummary | null>(null);
  const [policyConfigRefreshKey, setPolicyConfigRefreshKey] = useState(0);

  useEffect(() => {
    if (!routeArchiveId || routeArchiveId === activeArchiveId || !archives.some((archive) => archive.archive_id === routeArchiveId)) {
      return;
    }
    void setActiveArchiveId(routeArchiveId);
  }, [activeArchiveId, archives, routeArchiveId, setActiveArchiveId]);

  useEffect(() => {
    if (!routeArchiveId || !activeArchive) {
      setPolicyPackageVersionIdFromConfig(null);
      setPolicyConfigSummary(null);
      return;
    }

    let cancelled = false;
    getArchivePolicyConfig(routeArchiveId)
      .then((response) => {
        if (!cancelled) {
          const config = response.data;
          setPolicyPackageVersionIdFromConfig(config.policy_package_version_id ?? null);
          setPolicyConfigSummary({
            policyPackageName: config.policy_package_name ?? null,
            policyPackageVersionId: config.policy_package_version_id ?? null,
            policyPackageVersionStatus: config.policy_package_version_status ?? null,
            policyContractStatus: config.policy_contract_status ?? null,
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPolicyPackageVersionIdFromConfig(null);
          setPolicyConfigSummary(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeArchive, location.pathname, policyConfigRefreshKey, routeArchiveId]);

  useEffect(() => {
    const handlePolicyConfigUpdated = (event: Event) => {
      const detail = (event as CustomEvent<{ archiveId?: string }>).detail;
      if (!detail?.archiveId || detail.archiveId === routeArchiveId) {
        setPolicyConfigRefreshKey((value) => value + 1);
      }
    };

    window.addEventListener(P1_POLICY_CONFIG_UPDATED_EVENT, handlePolicyConfigUpdated);
    return () => window.removeEventListener(P1_POLICY_CONFIG_UPDATED_EVENT, handlePolicyConfigUpdated);
  }, [routeArchiveId]);

  if (!routeArchiveId) {
    return <Navigate to="/p1" replace />;
  }

  if (!loading && !activeArchive) {
    return <Navigate to="/p1" replace />;
  }

  if (!activeArchive) {
    return (
      <Layout className="p1-clean-shell">
        <Layout.Content className="p1-clean-content">
          <Card className="p1-clean-card">正在加载知识库上下文...</Card>
        </Layout.Content>
      </Layout>
    );
  }

  const workspaceContext = buildWorkspaceContext(routeArchiveId, activeArchive, policyPackageVersionIdFromConfig);

  return (
    <Layout className="p1-clean-shell">
      <Layout.Header className="p1-clean-header">
        <div className="p1-clean-brand">
          <span>CodeFactoryV2 / P1</span>
          <strong>业务知识库</strong>
        </div>
        <Menu
          className="p1-clean-menu"
          mode="horizontal"
          selectedKeys={[buildP1WorkspacePath(routeArchiveId, activeModuleRoute)]}
          items={buildWorkspaceMenuItems(routeArchiveId, p1WorkspaceModules, { includeOverview: true })}
          onClick={({ key }) => {
            if (key.startsWith("/p1")) {
              navigate(key);
            }
          }}
        />
        <div className="p1-clean-context">
          <Button onClick={() => navigate("/p1")}>返回知识库管理</Button>
          <div className="p1-clean-kb-switcher">
            <Typography.Text type="secondary">当前知识库</Typography.Text>
            <Select
              loading={loading}
              value={activeArchive.archive_id}
              onChange={(value) => {
                navigate(buildP1WorkspacePath(value, activeModuleRoute));
              }}
              options={archives.map((item) => ({
                label: item.name,
                value: item.archive_id,
              }))}
            />
          </div>
          <Tag color={getArchiveStatusColor(activeArchive)}>{getArchiveStatusLabel(activeArchive)}</Tag>
        </div>
      </Layout.Header>
      <section className="p1-clean-workspace-strip">
        <span>当前知识库：{activeArchive.name}</span>
        <span>来源：{activeArchive.source_dir}</span>
        <span>策略：{getWorkspacePolicyLabel(activeArchive, policyConfigSummary)}</span>
        <span>快照：{getArchiveSnapshotLabel(activeArchive)}</span>
      </section>
      <Layout.Content className="p1-clean-content">
        <Routes>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<P1WorkspaceOverview context={workspaceContext} modules={p1WorkspaceModules} />} />
          {p1WorkspaceModules.map((module) => {
            const ModulePage = module.Page;
            return <Route key={module.id} path={module.route} element={<ModulePage context={workspaceContext} />} />;
          })}
          <Route path="run" element={<Navigate to={buildP1WorkspacePath(routeArchiveId, "runtime")} replace />} />
          <Route path="policy/packages" element={<Navigate to={buildP1WorkspacePath(routeArchiveId, "policy")} replace />} />
          <Route path="policy/rules" element={<Navigate to={buildP1WorkspacePath(routeArchiveId, "policy")} replace />} />
          <Route path="*" element={<Navigate to="overview" replace />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}
