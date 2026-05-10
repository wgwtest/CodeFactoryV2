import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Empty, Input, Select, Space, Spin, Tag, Typography } from "antd";

import { DocumentProductSurface } from "../components/stageWorkbench/DocumentProductSurface";
import { StageDocumentWorkbench } from "../components/stageWorkbench/StageDocumentWorkbench";
import type {
  StageInputFactsViewModel,
  StageInteractionViewModel,
  StageDocumentWorkbenchViewModel,
} from "../components/stageWorkbench/models";
import { DocumentBodyPanel } from "../components/stageWorkbench/panels/DocumentBodyPanel";
import { DocumentOutlinePanel } from "../components/stageWorkbench/panels/DocumentOutlinePanel";
import { QualityCheckPanel } from "../components/stageWorkbench/panels/QualityCheckPanel";
import { StageProjectionPanel } from "../components/stageWorkbench/panels/StageProjectionPanel";
import type { P3DesignLabInputPackage, P3DesignLabSession } from "../lib/api";
import {
  createSoftwareDesignV2Session,
  generateSoftwareDesignV2Session,
  getSoftwareDesignV2InputPackages,
} from "../lib/softwareDesignV2";
import { buildP3DesignLabWorkbenchViewModel } from "./adapters/p3DesignLabWorkbenchAdapter";
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
            <Tag color="blue">{workbench.header.sourceLabel}</Tag>
            <Tag>布局：左 38% / 右 62%</Tag>
            <Tag>{workbench.header.providerLabel}</Tag>
            {designSession ? <Tag color="green">{workbench.header.statusLabel}</Tag> : <Tag>{workbench.header.statusLabel}</Tag>}
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
      title={workbench.header.title}
      subtitle={workbench.header.subtitle}
      badges={badges}
      actions={actions}
      alert={error ? <Alert type="error" showIcon message={error} style={{ marginTop: 12 }} /> : null}
      leftTop={
          <section className="p3-design-lab-panel" data-testid="p3-design-lab-requirement-pane">
            <div className="p3-design-lab-panel-head">
              <div>
                <h2 className="p3-design-lab-panel-title">需求规格说明（输入事实源）</h2>
                <div className="p3-design-lab-panel-note">{workbench.inputFacts.sourceTitle}</div>
              </div>
              <Tag color="blue">只读</Tag>
            </div>
            <div className="p3-design-lab-panel-body">
              <RequirementDocument inputFacts={workbench.inputFacts} />
            </div>
          </section>
      }
      leftBottom={
          <section className="p3-design-lab-panel" data-testid="p3-design-lab-cli-pane">
            <div className="p3-design-lab-panel-head">
              <div>
                <h2 className="p3-design-lab-panel-title">{workbench.interaction.title}</h2>
                <div className="p3-design-lab-panel-note">{workbench.interaction.description}</div>
              </div>
              <Tag color="green">Design Turn</Tag>
            </div>
            <div className="p3-design-lab-panel-body">
              <InteractionPanel interaction={workbench.interaction} cliInput={cliInput} onCliInputChange={setCliInput} />
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
              {workbench.product.status !== "empty" ? <Tag color="green">正文已生成</Tag> : <Tag>待生成</Tag>}
              {workbench.outline.baseline ? <Tag color="blue">{workbench.outline.baseline.label}</Tag> : null}
              {workbench.projection.status !== "empty" ? <Tag color="gold">工单投影已生成</Tag> : null}
            </Space>
          </div>
          <div className="p3-design-lab-panel-body">
            <DesignProductTabs workbench={workbench} />
          </div>
        </section>
      }
    />
  );
}

function RequirementDocument({ inputFacts }: { inputFacts: StageInputFactsViewModel }) {
  if (inputFacts.sections.length === 0) {
    return <Empty description={inputFacts.emptyDescription} />;
  }

  return (
    <article className="p3-design-lab-paper">
      <h2 className="p3-design-lab-paper-title">{inputFacts.title}</h2>
      {inputFacts.sections.map((section) => (
        <section key={section.sectionId} className="p3-design-lab-section">
          <h3>{section.title}</h3>
          {section.clauses.map((clause) => (
            <p key={clause.clauseId}>
              <Text strong>{clause.title}：</Text>
              {clause.content}
            </p>
          ))}
        </section>
      ))}
    </article>
  );
}

function InteractionPanel({
  interaction,
  cliInput,
  onCliInputChange,
}: {
  interaction: StageInteractionViewModel;
  cliInput: string;
  onCliInputChange: (value: string) => void;
}) {
  return (
    <div className="p3-design-lab-cli">
      <div className="p3-design-lab-runline" aria-label="P3 生成链路">
        {interaction.runline.map((step) => (
          <span className={step.state === "done" ? "is-done" : step.state === "active" ? "is-active" : ""} key={step.key}>
            {step.label}
          </span>
        ))}
      </div>
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
      <div className="p3-design-lab-cli-log">
        {interaction.feed.map((item) => (
          <div key={item.id}>
            <span>{item.speaker}</span>
            <p>{item.content}</p>
          </div>
        ))}
      </div>
      <div className="p3-design-lab-input-row">
        <Input.TextArea
          value={cliInput}
          onChange={(event) => onCliInputChange(event.target.value)}
          aria-label={interaction.composer.ariaLabel}
          autoSize={{ minRows: 2, maxRows: 4 }}
        />
        <Button disabled={interaction.composer.disabled}>{interaction.composer.submitLabel}</Button>
      </div>
    </div>
  );
}

function DesignProductTabs({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  return (
    <DocumentProductSurface
      defaultActiveKey={workbench.layout.defaultActiveProductTab}
      tabs={[
        { key: "document", label: "正文", children: <DocumentBodyPanel document={workbench.product} /> },
        { key: "outline", label: "目录", children: <DocumentOutlinePanel outline={workbench.outline} /> },
        { key: "check", label: "检查", children: <QualityCheckPanel quality={workbench.quality} /> },
        {
          key: "projection",
          label: "投影",
          children: <StageProjectionPanel projection={workbench.projection} note="本页不读取旧 requirements/specs，也不显示旧 P3 订单入口。" />,
        },
      ]}
    />
  );
}
