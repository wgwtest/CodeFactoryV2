import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Button, Empty, Input, Select, Space, Spin, Tag, Typography } from "antd";

import { StageLabShell, type StageLabNavigationItem } from "../components/stageWorkbench/StageLabShell";
import type {
  StageDocumentWorkbenchViewModel,
  StageInputFactsViewModel,
  StageInteractionViewModel,
} from "../components/stageWorkbench/models";
import { DocumentBodyPanel } from "../components/stageWorkbench/panels/DocumentBodyPanel";
import { QualityCheckPanel } from "../components/stageWorkbench/panels/QualityCheckPanel";
import type { P3DesignLabInputPackage, P3DesignLabSession } from "../lib/api";
import {
  createSoftwareDesignV2Session,
  generateSoftwareDesignV2Session,
  getSoftwareDesignV2InputPackages,
} from "../lib/softwareDesignV2";
import { buildP3DesignLabWorkbenchViewModel } from "./adapters/p3DesignLabWorkbenchAdapter";
import "./P3DesignLabPage.css";

const { Text, Title } = Typography;

const DEFAULT_POLICY = {
  architecture_preference: "统一服务优先，保留拆分点",
  module_granularity: "3-5 个业务模块，不拆太细",
  output_style: "按标准软设正文写，不写聊天语气",
};

type P3DesignLabNavigationKey = "input" | "workspace" | "projection" | "turn" | "review" | "log";
type P3DesignWorkspaceMode = "document" | "structured";

export function P3DesignLabPage() {
  const [inputPackages, setInputPackages] = useState<P3DesignLabInputPackage[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [designSession, setDesignSession] = useState<P3DesignLabSession | null>(null);
  const [activeNavigationKey, setActiveNavigationKey] = useState<P3DesignLabNavigationKey>("workspace");
  const [workspaceMode, setWorkspaceMode] = useState<P3DesignWorkspaceMode>("document");
  const [cliInput, setCliInput] = useState("按保守方案，先不要拆成微服务；模块名要能直接下发给 P4。");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await getSoftwareDesignV2InputPackages();
        if (cancelled) {
          return;
        }
        setInputPackages(response.data.items);
        setSelectedPackageId(response.data.items[0]?.input_package_id ?? null);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 P3 输入包失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedPackage = useMemo(
    () => inputPackages.find((item) => item.input_package_id === selectedPackageId) ?? inputPackages[0] ?? null,
    [inputPackages, selectedPackageId],
  );
  const workbench = useMemo(
    () =>
      buildP3DesignLabWorkbenchViewModel({
        inputPackage: selectedPackage,
        session: designSession,
        policy: DEFAULT_POLICY,
      }),
    [designSession, selectedPackage],
  );

  async function handleGenerate() {
    if (!selectedPackage) {
      return;
    }
    try {
      setSubmitting(true);
      const created = await createSoftwareDesignV2Session({
        input_package_id: selectedPackage.input_package_id,
        generation_policy: DEFAULT_POLICY,
      });
      const generated = await generateSoftwareDesignV2Session(created.data.session_id);
      setDesignSession(generated.data);
      setInputPackages((current) =>
        current.map((item) =>
          item.input_package_id === generated.data.input_package.input_package_id ? generated.data.input_package : item,
        ),
      );
      setActiveNavigationKey("workspace");
      setWorkspaceMode("document");
      setError(null);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "生成软件设计说明失败");
    } finally {
      setSubmitting(false);
    }
  }

  function handleNavigationChange(key: string) {
    setActiveNavigationKey(key as P3DesignLabNavigationKey);
  }

  if (loading) {
    return (
      <div className="p3-design-lab-loading">
        <Spin size="large" />
      </div>
    );
  }

  const navigationItems = buildNavigationItems(workbench, inputPackages.length);
  const workspace = renderWorkspace({
    activeNavigationKey,
    cliInput,
    inputPackages,
    selectedPackageId,
    setCliInput,
    setSelectedPackageId,
    setWorkspaceMode,
    workbench,
    workspaceMode,
  });

  return (
    <StageLabShell
      actions={
        <>
          <Select
            aria-label="选择需规输入包"
            className="p3-design-lab-input-select"
            disabled={!inputPackages.length}
            options={inputPackages.map((item) => ({ label: item.source_title, value: item.input_package_id }))}
            placeholder="选择 P2 冻结包"
            value={selectedPackageId ?? undefined}
            onChange={setSelectedPackageId}
          />
          <Button disabled={!selectedPackage} loading={submitting} type="primary" onClick={() => void handleGenerate()}>
            生成软件设计说明
          </Button>
        </>
      }
      activeNavigationKey={activeNavigationKey}
      alert={error ? <Alert className="p3-design-lab-alert" message={error} showIcon type="error" /> : null}
      badges={
        <>
          <Tag color="blue">{inputPackages.length} 份需规输入</Tag>
          <Tag color={designSession ? "green" : "default"}>{designSession ? `设计会话：${designSession.status}` : "设计会话：待生成"}</Tag>
          <Tag color={workbench.outline.baseline ? "green" : "default"}>
            {workbench.outline.baseline ? `基线：${workbench.outline.baseline.moduleCount} 模块` : "基线：未生成"}
          </Tag>
          <Tag color={workbench.projection.status === "empty" ? "default" : "gold"}>P4 投影：{workbench.projection.items.length} 节点</Tag>
        </>
      }
      className="p3-design-lab-page"
      mark="P3"
      navigationItems={navigationItems}
      navigationLabel="P3 Design Lab 视图导航"
      navigationTestId="p3-design-lab-navigation"
      subtitle="从 P2 需求规格冻结包生成软件设计说明、设计基线和 P4 投影"
      title="P3 Software Design Lab"
      workspace={workspace}
      workspaceTestId="p3-design-lab-workspace"
      onNavigationChange={handleNavigationChange}
    />
  );
}

function buildNavigationItems(workbench: StageDocumentWorkbenchViewModel, inputPackageCount: number): StageLabNavigationItem[] {
  const moduleCount = workbench.outline.baseline?.moduleCount ?? 0;
  return [
    {
      key: "input",
      title: "需规输入",
      subtitle: "需规列表与关联软设",
      badge: `${inputPackageCount} 份`,
    },
    {
      key: "workspace",
      title: "软设工作区",
      subtitle: "文档视图 / 结构化数据",
      badge: workbench.product.status === "empty" ? "待生成" : "草稿",
    },
    {
      key: "projection",
      title: "P4 投影",
      subtitle: "下游工单组织树",
      badge: `${workbench.projection.items.length} 节点`,
    },
    {
      key: "turn",
      title: "当前 Turn",
      subtitle: "回合列表与自然语言 CLI",
      badge: workbench.interaction.lastTurn?.turnId ?? "0 轮",
    },
    {
      key: "review",
      title: "检查评审",
      subtitle: "门禁、证据与阻断项",
      badge: `${workbench.quality.summary.blockingCount} 阻断`,
    },
    {
      key: "log",
      title: "运行日志",
      subtitle: "API、Provider、状态迁移",
      badge: moduleCount ? `${moduleCount + 2} 条` : "2 条",
    },
  ];
}

function renderWorkspace({
  activeNavigationKey,
  cliInput,
  inputPackages,
  selectedPackageId,
  setCliInput,
  setSelectedPackageId,
  setWorkspaceMode,
  workbench,
  workspaceMode,
}: {
  activeNavigationKey: P3DesignLabNavigationKey;
  cliInput: string;
  inputPackages: P3DesignLabInputPackage[];
  selectedPackageId: string | null;
  setCliInput: (value: string) => void;
  setSelectedPackageId: (value: string) => void;
  setWorkspaceMode: (value: P3DesignWorkspaceMode) => void;
  workbench: StageDocumentWorkbenchViewModel;
  workspaceMode: P3DesignWorkspaceMode;
}) {
  if (activeNavigationKey === "input") {
    return (
      <InputPackageView
        inputFacts={workbench.inputFacts}
        inputPackages={inputPackages}
        selectedPackageId={selectedPackageId}
        workbench={workbench}
        onSelectPackage={setSelectedPackageId}
      />
    );
  }

  if (activeNavigationKey === "projection") {
    return <ProjectionTreeView workbench={workbench} />;
  }

  if (activeNavigationKey === "turn") {
    return <CurrentTurnView cliInput={cliInput} interaction={workbench.interaction} onCliInputChange={setCliInput} />;
  }

  if (activeNavigationKey === "review") {
    return (
      <WorkspacePanel title="检查评审" subtitle="检查评审只负责门禁、证据和冻结候选，不生成设计内容。">
        <QualityCheckPanel quality={workbench.quality} />
      </WorkspacePanel>
    );
  }

  if (activeNavigationKey === "log") {
    return <RuntimeLogView workbench={workbench} />;
  }

  return (
    <SoftwareDesignWorkspaceView
      mode={workspaceMode}
      workbench={workbench}
      onModeChange={setWorkspaceMode}
    />
  );
}

function InputPackageView({
  inputFacts,
  inputPackages,
  selectedPackageId,
  workbench,
  onSelectPackage,
}: {
  inputFacts: StageInputFactsViewModel;
  inputPackages: P3DesignLabInputPackage[];
  selectedPackageId: string | null;
  workbench: StageDocumentWorkbenchViewModel;
  onSelectPackage: (value: string) => void;
}) {
  return (
    <WorkspacePanel title="需规输入" subtitle="先选择可进入 P3 的需求规格说明，再查看或创建它关联的软件设计说明。">
      <div className="p3-design-lab-input-view" data-testid="p3-design-lab-input-view">
        <section className="p3-design-lab-panel">
          <PanelHead title="需规列表" subtitle="来自 P2 authoring frozen_package，P3 只读消费。" />
          <div className="p3-design-lab-card-list">
            {inputPackages.length ? (
              inputPackages.map((item) => (
                <button
                  className={item.input_package_id === selectedPackageId ? "p3-design-lab-list-card is-selected" : "p3-design-lab-list-card"}
                  key={item.input_package_id}
                  onClick={() => onSelectPackage(item.input_package_id)}
                  type="button"
                >
                  <span>
                    <Text strong>{item.source_title}</Text>
                    <Text type="secondary">{item.source_document_id}</Text>
                  </span>
                  <Space wrap>
                    <Tag color={item.p3_consumable ? "green" : "default"}>{item.p3_consumable ? "待设计" : "不可设计"}</Tag>
                    {item.frozen_at ? <Tag>{formatDateTime(item.frozen_at)}</Tag> : null}
                  </Space>
                </button>
              ))
            ) : (
              <Empty description="暂无可进入 P3 的需规输入包" />
            )}
          </div>
        </section>

        <section className="p3-design-lab-panel">
          <PanelHead title="选中需规对象" subtitle="只展示 P3 建模所需的事实源身份，不在这里改写需规正文。" />
          {inputFacts.title ? (
            <div className="p3-design-lab-spec-summary">
              <Title level={4}>{inputFacts.title}</Title>
              <dl>
                <div>
                  <dt>创建来源</dt>
                  <dd>{inputFacts.sourceTitle}</dd>
                </div>
                <div>
                  <dt>章节数量</dt>
                  <dd>{inputFacts.sections.length}</dd>
                </div>
                <div>
                  <dt>当前状态</dt>
                  <dd>已冻结，可进入 P3 设计</dd>
                </div>
              </dl>
              <div className="p3-design-lab-requirement-paper">
                {inputFacts.sections.map((section) => (
                  <section key={section.sectionId}>
                    <h4>{section.title}</h4>
                    {section.clauses.map((clause) => (
                      <p key={clause.clauseId}>
                        <Text strong>{clause.title}：</Text>
                        {clause.content}
                      </p>
                    ))}
                  </section>
                ))}
              </div>
            </div>
          ) : (
            <Empty description={inputFacts.emptyDescription} />
          )}
        </section>

        <section className="p3-design-lab-panel">
          <PanelHead title="关联软设" subtitle="一条需规可以关联多份软件设计说明；发布和冻结不在本视图完成。" />
          <div className="p3-design-lab-related-design-list">
            {inputFacts.relatedDesigns.length ? (
              inputFacts.relatedDesigns.map((design) => (
                <article className="p3-design-lab-related-design-card" key={design.software_design_id}>
                  <span>
                    <Text strong>{design.title}</Text>
                    <Text type="secondary">版本：{design.version_label}</Text>
                  </span>
                  <Space wrap>
                    <Tag color={design.status === "baseline_ready" ? "green" : "default"}>{design.status}</Tag>
                    <Tag>{formatDateTime(design.updated_at)}</Tag>
                    <Button size="small">进入编辑</Button>
                    <Button danger size="small">删除</Button>
                  </Space>
                </article>
              ))
            ) : workbench.product.status === "empty" ? (
              <div className="p3-design-lab-empty-state">当前需规尚未生成关联软设。</div>
            ) : (
              <article className="p3-design-lab-related-design-card">
                <span>
                  <Text strong>{workbench.product.title}</Text>
                  <Text type="secondary">版本：SoftwareDesignBaseline v2</Text>
                </span>
                <Space wrap>
                  <Tag color="green">草稿</Tag>
                  <Button size="small">进入编辑</Button>
                  <Button danger size="small">删除</Button>
                </Space>
              </article>
            )}
            <Button type="primary">新建软设</Button>
          </div>
        </section>
      </div>
    </WorkspacePanel>
  );
}

function SoftwareDesignWorkspaceView({
  mode,
  workbench,
  onModeChange,
}: {
  mode: P3DesignWorkspaceMode;
  workbench: StageDocumentWorkbenchViewModel;
  onModeChange: (value: P3DesignWorkspaceMode) => void;
}) {
  return (
    <WorkspacePanel
      actions={
        <>
          <Button aria-pressed={mode === "document"} type={mode === "document" ? "primary" : "default"} onClick={() => onModeChange("document")}>
            文档视图
          </Button>
          <Button aria-pressed={mode === "structured"} type={mode === "structured" ? "primary" : "default"} onClick={() => onModeChange("structured")}>
            结构化数据
          </Button>
          <Button disabled={workbench.product.status === "empty"}>保存草稿</Button>
        </>
      }
      subtitle="同一份软件设计说明在这里以 A4 正文和结构化基线两种形态展示。"
      title="软设工作区"
    >
      {mode === "document" ? (
        <div className="p3-design-lab-workspace-document">
          <section className="p3-design-lab-section-nav">
            <PanelHead title="章节与设计对象" subtitle="用于定位正文，不承担视图切换。" />
            {workbench.product.sections.length ? (
              <ol>
                {workbench.product.sections.map((section) => (
                  <li key={section.sectionId}>
                    <Text strong>{section.title}</Text>
                    <Tag>{section.status}</Tag>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="p3-design-lab-empty-state">生成后显示软件设计说明章节。</div>
            )}
          </section>
          <DocumentBodyPanel document={workbench.product} />
        </div>
      ) : (
        <StructuredDesignDataView workbench={workbench} />
      )}
    </WorkspacePanel>
  );
}

function StructuredDesignDataView({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const baseline = workbench.outline.baseline;
  return (
    <div className="p3-design-lab-structured-view" data-testid="p3-design-structured-data-view">
      <section className="p3-design-lab-panel">
        <PanelHead title="设计基线摘要" subtitle="结构化数据来自 SoftwareDesignBaseline v2，默认与正文同步。" />
        {baseline ? (
          <div className="p3-design-lab-baseline-summary">
            <Metric label="架构模式" value={baseline.architectureMode} />
            <Metric label="模块数量" value={`${baseline.moduleCount}`} />
            <Metric label="追溯关系" value={`${baseline.traceabilityCount}`} />
          </div>
        ) : (
          <Empty description="生成软件设计说明后显示结构化设计基线" />
        )}
      </section>
      <section className="p3-design-lab-panel">
        <PanelHead title="模块结构" subtitle="模块是 P4 投影的主要来源，不在这里拆成工单。" />
        {baseline?.modules.length ? (
          <div className="p3-design-lab-module-grid">
            {baseline.modules.map((module) => (
              <article key={module.moduleId}>
                <Text strong>{module.name}</Text>
                <Text type="secondary">{module.moduleId}</Text>
              </article>
            ))}
          </div>
        ) : (
          <div className="p3-design-lab-empty-state">暂无模块结构。</div>
        )}
      </section>
      <section className="p3-design-lab-panel">
        <PanelHead title="追溯与投影来源" subtitle="结构化数据、检查评审和 P4 投影共享同一套基线。" />
        <div className="p3-design-lab-trace-grid">
          {workbench.product.traceLinks.length ? (
            workbench.product.traceLinks.map((link, index) => (
              <code key={`trace-${index}`}>{JSON.stringify(link)}</code>
            ))
          ) : (
            <span>当前样例未返回细粒度追溯关系。</span>
          )}
        </div>
      </section>
    </div>
  );
}

function ProjectionTreeView({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  return (
    <WorkspacePanel
      actions={<Button disabled={workbench.projection.status === "empty"}>生成投影候选</Button>}
      subtitle="P4 投影就是从 P3 设计基线派生出的下游工单组织树。"
      title="P4 投影"
    >
      <div className="p3-design-lab-projection-tree-view" data-testid="p3-design-lab-projection-tree">
        <section aria-label="P4 工单投影树" className="p3-design-lab-projection-tree" role="tree">
          <div aria-expanded="true" role="treeitem">
            <Text strong>{workbench.projection.packageName}</Text>
            <Tag>{workbench.projection.status}</Tag>
          </div>
          <div role="group">
            {workbench.projection.items.length ? (
              workbench.projection.items.map((item) => (
                <div className="p3-design-lab-projection-node" key={item.itemId} role="treeitem">
                  <span>{item.title}</span>
                  <Space wrap>
                    <Tag>{item.itemType}</Tag>
                    <Tag color={item.readiness === "ready" ? "green" : "default"}>{item.readiness}</Tag>
                  </Space>
                </div>
              ))
            ) : (
              <div className="p3-design-lab-empty-state">{workbench.projection.emptyDescription}</div>
            )}
          </div>
        </section>
        <section className="p3-design-lab-panel">
          <PanelHead title="投影说明" subtitle="本视图回答这份软设后面怎么变成可执行工作。" />
          <p>
            P4 投影不等于正式推送。正式推送仍需要检查评审通过后，由后续治理动作触发。
          </p>
        </section>
      </div>
    </WorkspacePanel>
  );
}

function CurrentTurnView({
  interaction,
  cliInput,
  onCliInputChange,
}: {
  interaction: StageInteractionViewModel;
  cliInput: string;
  onCliInputChange: (value: string) => void;
}) {
  return (
    <WorkspacePanel title="当前 Turn" subtitle="用回合列表解释从需规到软设的生成和修订过程。">
      <div className="p3-design-lab-turn-view">
        <section className="p3-design-lab-panel">
          <PanelHead title="回合列表" subtitle="首版先用生成链路和系统消息表达回合状态。" />
          <div className="p3-design-lab-runline" aria-label="P3 生成链路">
            {interaction.runline.map((step) => (
              <span className={step.state === "done" ? "is-done" : step.state === "active" ? "is-active" : ""} key={step.key}>
                {step.label}
              </span>
            ))}
          </div>
          <div className="p3-design-lab-cli-log">
            {interaction.feed.map((item) => (
              <div key={item.id}>
                <span>{item.speaker}</span>
                <p>{item.content}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="p3-design-lab-panel">
          <PanelHead title="自然语言 CLI" subtitle={interaction.description} />
          <div className="p3-design-lab-policy-grid">
            {interaction.policies.map((policy) => (
              <div className="p3-design-lab-policy" key={policy.key}>
                <strong>{policy.label}</strong>
                <br />
                {policy.value}
              </div>
            ))}
          </div>
          <div className="p3-design-lab-message">{interaction.message}</div>
          <div className="p3-design-lab-input-row">
            <Input.TextArea
              aria-label={interaction.composer.ariaLabel}
              autoSize={{ minRows: 4, maxRows: 7 }}
              value={cliInput}
              onChange={(event) => onCliInputChange(event.target.value)}
            />
            <Button disabled={interaction.composer.disabled}>{interaction.composer.submitLabel}</Button>
          </div>
        </section>
      </div>
    </WorkspacePanel>
  );
}

function RuntimeLogView({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const logRows = [
    { time: "09:00", scope: "GET", content: "读取 P2 需求规格冻结包" },
    { time: "09:01", scope: "ADAPTER", content: "构建 P3 Design Lab ViewModel" },
    ...(workbench.product.status === "empty"
      ? []
      : [
          { time: "09:02", scope: "POST", content: "生成软件设计说明和结构化设计基线" },
          { time: "09:03", scope: "PROJECTION", content: "生成 P4 投影候选" },
        ]),
  ];
  return (
    <WorkspacePanel title="运行日志" subtitle="运行日志只记录过程，不作为正式设计结论。">
      <div className="p3-design-lab-runtime-log">
        {logRows.map((row) => (
          <article key={`${row.time}-${row.scope}`}>
            <Tag>{row.time}</Tag>
            <Text strong>{row.scope}</Text>
            <span>{row.content}</span>
          </article>
        ))}
      </div>
    </WorkspacePanel>
  );
}

function WorkspacePanel({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="p3-design-lab-workspace-panel">
      <header className="p3-design-lab-workspace-head">
        <div>
          <Title level={3}>{title}</Title>
          <Text type="secondary">{subtitle}</Text>
        </div>
        {actions ? <Space wrap>{actions}</Space> : null}
      </header>
      <div className="p3-design-lab-workspace-body">{children}</div>
    </div>
  );
}

function PanelHead({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="p3-design-lab-local-head">
      <Text strong>{title}</Text>
      <Text type="secondary">{subtitle}</Text>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p3-design-lab-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatDateTime(value: string) {
  return value.slice(0, 16).replace("T", " ");
}
