import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Empty, Input, Select, Space, Spin, Tag, Typography } from "antd";

import { A4DocumentSurface } from "../components/stageWorkbench/A4DocumentSurface";
import { DocumentProductSurface } from "../components/stageWorkbench/DocumentProductSurface";
import { StageDocumentWorkbench } from "../components/stageWorkbench/StageDocumentWorkbench";
import type { P3DesignLabInputPackage, P3DesignLabSession } from "../lib/api";
import {
  createSoftwareDesignV2Session,
  generateSoftwareDesignV2Session,
  getSoftwareDesignV2InputPackages,
} from "../lib/softwareDesignV2";
import "./P3DesignLabPage.css";

const { Text } = Typography;

const DEFAULT_POLICY = {
  architecture_preference: "统一服务优先，保留拆分点",
  module_granularity: "3-5 个业务模块，不拆太细",
  output_style: "按标准软设正文写，不写聊天语气",
};

export function P3DesignLabPage() {
  const [inputPackages, setInputPackages] = useState<P3DesignLabInputPackage[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [designSession, setDesignSession] = useState<P3DesignLabSession | null>(null);
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
          setError(loadError instanceof Error ? loadError.message : "加载 P3 v2 输入包失败");
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
  const visiblePackage = designSession?.input_package ?? selectedPackage;

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
      setError(null);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "生成 P3 设计基线失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="p3-design-lab-page" style={{ display: "grid", placeItems: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  const badges = (
    <>
            <Tag color="blue">输入：P2 authoring frozen_package</Tag>
            <Tag>布局：左 38% / 右 62%</Tag>
            <Tag>Provider：Mock Design Provider</Tag>
            {designSession ? <Tag color="green">状态：{designSession.status}</Tag> : <Tag>状态：待生成</Tag>}
    </>
  );
  const actions = (
    <>
          <Select
            aria-label="选择冻结包"
            style={{ minWidth: 280 }}
            value={selectedPackageId ?? undefined}
            placeholder="选择 P2 冻结包"
            onChange={setSelectedPackageId}
            options={inputPackages.map((item) => ({ label: item.source_title, value: item.input_package_id }))}
          />
          <Button type="primary" loading={submitting} disabled={!selectedPackage} onClick={() => void handleGenerate()}>
            生成设计基线
          </Button>
    </>
  );

  return (
    <StageDocumentWorkbench
      stage="P3"
      className="p3-design-lab-page"
      title="P3 Design Lab"
      subtitle="只消费 P2 新版冻结包，不兼容旧规格池"
      badges={badges}
      actions={actions}
      alert={error ? <Alert type="error" showIcon message={error} style={{ marginTop: 12 }} /> : null}
      leftTop={
          <section className="p3-design-lab-panel" data-testid="p3-design-lab-requirement-pane">
            <div className="p3-design-lab-panel-head">
              <div>
                <h2 className="p3-design-lab-panel-title">需求规格说明（输入事实源）</h2>
                <div className="p3-design-lab-panel-note">{visiblePackage?.source_title ?? "没有可用的 P2 冻结包"}</div>
              </div>
              <Tag color="blue">只读</Tag>
            </div>
            <div className="p3-design-lab-panel-body">
              {visiblePackage ? <RequirementDocument packageItem={visiblePackage} /> : <Empty description="没有 P2 新版冻结包" />}
            </div>
          </section>
      }
      leftBottom={
          <section className="p3-design-lab-panel" data-testid="p3-design-lab-cli-pane">
            <div className="p3-design-lab-panel-head">
              <div>
                <h2 className="p3-design-lab-panel-title">自然语言配置 / CLI</h2>
                <div className="p3-design-lab-panel-note">用于控制转换策略和校正输出，不替代虚规输入</div>
              </div>
              <Tag color="green">Design Turn</Tag>
            </div>
            <div className="p3-design-lab-panel-body">
              <div className="p3-design-lab-cli">
                <div className="p3-design-lab-runline" aria-label="P3 生成链路">
                  <span className={visiblePackage ? "is-done" : ""}>P2 冻结包</span>
                  <span className={designSession ? "is-done" : "is-active"}>设计生成</span>
                  <span className={designSession?.design_baseline ? "is-done" : ""}>基线固化</span>
                  <span className={designSession?.workorder_projection ? "is-done" : ""}>P4 投影</span>
                </div>
                <div className="p3-design-lab-policy-grid">
                  <div className="p3-design-lab-policy">
                    <strong>架构偏好</strong>
                    <br />
                    {DEFAULT_POLICY.architecture_preference}
                  </div>
                  <div className="p3-design-lab-policy">
                    <strong>模块粒度</strong>
                    <br />
                    {DEFAULT_POLICY.module_granularity}
                  </div>
                  <div className="p3-design-lab-policy">
                    <strong>输出风格</strong>
                    <br />
                    {DEFAULT_POLICY.output_style}
                  </div>
                </div>
                <div className="p3-design-lab-message">
                  {designSession
                    ? "已生成设计基线。可继续输入：细化模块 / 重生成接口 / 增加状态机 / 保守一点。"
                    : "选择 P2 冻结包后，可直接生成软件设计说明、设计基线和 P4 工单投影。"}
                </div>
                <div className="p3-design-lab-cli-log">
                  <div>
                    <span>P3</span>
                    <p>读取虚规正文、结构化字段和标注，保持只读。</p>
                  </div>
                  <div>
                    <span>SYS</span>
                    <p>{designSession ? "设计基线已就绪，等待下一轮自然语言配置。" : "等待生成软件设计说明。"}</p>
                  </div>
                </div>
                <div className="p3-design-lab-input-row">
                  <Input.TextArea
                    value={cliInput}
                    onChange={(event) => setCliInput(event.target.value)}
                    aria-label="P3 Design Lab CLI"
                    autoSize={{ minRows: 2, maxRows: 4 }}
                  />
                  <Button disabled={!designSession}>提交</Button>
                </div>
              </div>
            </div>
          </section>
      }
      main={
        <section className="p3-design-lab-panel" data-testid="p3-design-lab-design-pane">
          <div className="p3-design-lab-panel-head">
            <div>
              <h2 className="p3-design-lab-panel-title">软件设计说明（输出主产物）</h2>
              <div className="p3-design-lab-panel-note">由同一份 SoftwareDesignBaseline v2 投影生成</div>
            </div>
            <Space>
              {designSession?.design_document ? <Tag color="green">正文已生成</Tag> : <Tag>待生成</Tag>}
              {designSession?.design_baseline ? <Tag color="blue">SoftwareDesignBaseline v2</Tag> : null}
              {designSession?.workorder_projection ? <Tag color="gold">工单投影已生成</Tag> : null}
            </Space>
          </div>
          <div className="p3-design-lab-panel-body">
            <DesignProductTabs session={designSession} />
          </div>
        </section>
      }
    />
  );
}

function RequirementDocument({ packageItem }: { packageItem: P3DesignLabInputPackage }) {
  return (
    <article className="p3-design-lab-paper">
      <h2 className="p3-design-lab-paper-title">{packageItem.standard_document.title}</h2>
      {packageItem.standard_document.sections.map((section) => (
        <section key={section.section_id} className="p3-design-lab-section">
          <h3>{section.title}</h3>
          {section.clauses.map((clause) => (
            <p key={clause.clause_id}>
              <Text strong>{clause.title}：</Text>
              {clause.content}
            </p>
          ))}
        </section>
      ))}
    </article>
  );
}

function DesignProductTabs({ session }: { session: P3DesignLabSession | null }) {
  return (
    <DocumentProductSurface
      tabs={[
        { key: "document", label: "正文", children: <DesignDocument session={session} /> },
        { key: "outline", label: "目录", children: <DesignOutline session={session} /> },
        { key: "check", label: "检查", children: <DesignCheckPanel session={session} /> },
        { key: "projection", label: "投影", children: <DesignProjectionPanel session={session} /> },
      ]}
    />
  );
}

function DesignDocument({ session }: { session: P3DesignLabSession | null }) {
  return (
    <A4DocumentSurface
      ariaLabel="A4 软件设计说明预览"
      title={session?.design_document?.title}
      subtitle="基于 P2 需求规格冻结包生成"
      headerLeft="CodeFactoryV2 / P3"
      headerRight="Software Design Description"
      footerLeft="SoftwareDesignBaseline v2"
      sections={session?.design_document?.sections.map((section) => ({
        section_id: section.section_id,
        title: section.title,
        content: section.content,
        status: section.status ?? "generated",
      }))}
      emptyDescription="尚未生成软件设计说明"
    />
  );
}

function DesignOutline({ session }: { session: P3DesignLabSession | null }) {
  if (!session?.design_document && !session?.design_baseline) {
    return <Empty description="生成设计基线后显示目录和模块映射" />;
  }

  return (
    <div className="p3-design-lab-tab-panel">
      <div className="p3-design-lab-rail-card">
        <h4>正文目录</h4>
        {session?.design_document ? (
          <ol className="p3-design-lab-list">
            {session.design_document.sections.map((section) => (
              <li key={section.section_id}>{section.title}</li>
            ))}
          </ol>
        ) : (
          <p>尚未生成软件设计说明正文。</p>
        )}
      </div>
      <div className="p3-design-lab-rail-card">
        <h4>设计基线摘要</h4>
        {session?.design_baseline ? (
          <>
            <p>
              <Text strong>SoftwareDesignBaseline v2</Text>
            </p>
            <ul className="p3-design-lab-list">
              <li>架构：{session.design_baseline.architecture_mode}</li>
              <li>模块：{session.design_baseline.modules.length} 个</li>
              <li>追溯：{session.design_baseline.traceability?.length ?? 0} 条</li>
            </ul>
            <div className="p3-design-lab-workorders">
              {session.design_baseline.modules.map((module) => (
                <div className="p3-design-lab-workorder" key={module.module_id}>
                  {module.name}
                </div>
              ))}
            </div>
          </>
        ) : (
          <p>等待生成设计基线。</p>
        )}
      </div>
    </div>
  );
}

function DesignCheckPanel({ session }: { session: P3DesignLabSession | null }) {
  const checkResult = session?.check_result;

  if (!checkResult) {
    return (
      <div className="p3-design-lab-tab-panel">
        <div className="p3-design-lab-rail-card">
          <h4>设计完整性检查</h4>
          <p>尚未运行设计完整性检查</p>
          <p>生成设计基线后，可检查正文、模块、接口、追溯和 P4 投影是否满足冻结准备条件。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p3-design-lab-tab-panel">
      <div className="p3-design-lab-rail-card">
        <h4>设计完整性检查</h4>
        <ul className="p3-design-lab-list">
          <li>阻断项：{checkResult.blocking_count}</li>
          <li>警告项：{checkResult.warning_count}</li>
          <li>通过项：{checkResult.passed_count}</li>
        </ul>
      </div>
    </div>
  );
}

function DesignProjectionPanel({ session }: { session: P3DesignLabSession | null }) {
  return (
    <div className="p3-design-lab-tab-panel">
      <div className="p3-design-lab-rail-card">
        <h4>P4 工单投影</h4>
        {session?.workorder_projection ? (
          <div className="p3-design-lab-workorders">
            {session.workorder_projection.items.map((item) => (
              <div className="p3-design-lab-workorder" key={item.item_id}>
                {item.title}
              </div>
            ))}
          </div>
        ) : (
          <p>生成设计基线后显示工单预览。</p>
        )}
      </div>
      <div className="p3-design-lab-rail-card">
        <h4>不兼容提示</h4>
        <p>本页不读取旧 requirements/specs，也不显示旧 P3 订单入口。</p>
      </div>
    </div>
  );
}
