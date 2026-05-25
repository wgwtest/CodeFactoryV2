import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Button, Empty, Input, Modal, Select, Space, Spin, Tag, Typography } from "antd";

import {
  buildDesignMorphStageRelationSelection,
  DesignMorphCanvasPlatform,
  type DesignMorphSelectionAction,
  type DesignMorphSelection,
} from "../components/stageWorkbench/DesignMorphCanvasPlatform";
import { StageLabShell, type StageLabNavigationItem } from "../components/stageWorkbench/StageLabShell";
import type {
  StageDocumentWorkbenchViewModel,
  StageInputFactsViewModel,
  StageInteractionViewModel,
} from "../components/stageWorkbench/models";
import { QualityCheckPanel } from "../components/stageWorkbench/panels/QualityCheckPanel";
import type {
  P3DesignLabInputPackage,
  P3DesignPatchApplyResult,
  P3DesignLabSession,
  P3DesignPatchBlockPreview,
  P3DesignPatchOperation,
  P3DesignPatchProposal,
  P3DesignTurn,
  P3DesignTurnScopeAnchor,
} from "../lib/api";
import {
  applySoftwareDesignV2PatchProposal,
  appendSoftwareDesignV2Turn,
  createSoftwareDesignV2Session,
  deleteSoftwareDesignV2Session,
  freezeSoftwareDesignV2Session,
  generateSoftwareDesignV2Projection,
  getSoftwareDesignV2InputPackages,
  getSoftwareDesignV2Session,
  runSoftwareDesignV2Check,
  runSoftwareDesignV2Conversion,
  saveSoftwareDesignV2Draft,
  type SoftwareDesignV2TurnPayload,
} from "../lib/softwareDesignV2";
import { usePollingResource } from "../lib/usePollingResource";
import { buildP3DesignMorphModel } from "./adapters/p3DesignMorphAdapter";
import { buildP3DesignLabWorkbenchViewModel } from "./adapters/p3DesignLabWorkbenchAdapter";
import "./P3DesignLabPage.css";

const { Text, Title } = Typography;

const DEFAULT_POLICY = {
  architecture_preference: "统一服务优先，保留拆分点",
  module_granularity: "3-5 个业务模块，不拆太细",
  output_style: "按标准软设正文写，不写聊天语气",
};

const INPUT_PACKAGE_REFRESH_INTERVAL_MS = 1000;
const CONVERSION_TIMER_INTERVAL_MS = 1000;

type P3DesignLabNavigationKey = "input" | "workspace" | "turn" | "review" | "log";
type P3DesignConversionStrategy = "standard_sdd_draft" | "component_first" | "p4_projection_first";
type P3DesignDraftMeta = {
  title: string;
  versionLabel: string;
};
type InspectorTabKey = "ability" | "common";

function getApiErrorMessage(error: unknown, fallback: string) {
  const detail = getApiErrorDetail(error);
  if (detail) {
    return detail;
  }
  return error instanceof Error ? error.message : fallback;
}

function getApiErrorDetail(error: unknown) {
  if (!error || typeof error !== "object" || !("response" in error)) {
    return "";
  }
  const response = (error as { response?: { data?: unknown } }).response;
  const data = response?.data;
  if (!data || typeof data !== "object" || !("detail" in data)) {
    return "";
  }
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item && typeof (item as { msg?: unknown }).msg === "string") {
          return (item as { msg: string }).msg;
        }
        return "";
      })
      .filter(Boolean)
      .join("；");
  }
  return "";
}

export function P3DesignLabPage() {
  const [inputPackages, setInputPackages] = useState<P3DesignLabInputPackage[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [designSession, setDesignSession] = useState<P3DesignLabSession | null>(null);
  const [activeNavigationKey, setActiveNavigationKey] = useState<P3DesignLabNavigationKey>("input");
  const [activeMorphWindowId, setActiveMorphWindowId] = useState("reqdoc");
  const [conversionStrategy, setConversionStrategy] = useState<P3DesignConversionStrategy>("standard_sdd_draft");
  const [cliInput, setCliInput] = useState("按保守方案，先不要拆成微服务；模块名要能直接下发给 P4。");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [draftMeta, setDraftMeta] = useState<P3DesignDraftMeta>({ title: "", versionLabel: "v0.1" });
  const [submitting, setSubmitting] = useState(false);
  const [conversionInFlightSessionId, setConversionInFlightSessionId] = useState<string | null>(null);
  const [conversionStartedAtMs, setConversionStartedAtMs] = useState<number | null>(null);
  const [conversionElapsedSeconds, setConversionElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const loadInputPackages = useCallback(async () => {
    const response = await getSoftwareDesignV2InputPackages();
    return response.data.items;
  }, []);

  const { loading, refresh: refreshInputPackages } = usePollingResource({
    intervalMs: INPUT_PACKAGE_REFRESH_INTERVAL_MS,
    load: loadInputPackages,
    onData: useCallback((items: P3DesignLabInputPackage[]) => {
      setInputPackages(items);
      setSelectedPackageId((current) =>
        current && items.some((item) => item.input_package_id === current) ? current : (items[0]?.input_package_id ?? null),
      );
      setError(null);
    }, []),
    onError: useCallback((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : "加载 P3 输入包失败");
    }, []),
  });

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
        conversionRunning: Boolean(designSession && conversionInFlightSessionId === designSession.session_id),
        conversionElapsedSeconds,
      }),
    [conversionElapsedSeconds, conversionInFlightSessionId, designSession, selectedPackage],
  );

  useEffect(() => {
    if (!conversionInFlightSessionId || conversionStartedAtMs === null) {
      return undefined;
    }
    const updateElapsed = () => {
      setConversionElapsedSeconds(Math.max(0, Math.floor((Date.now() - conversionStartedAtMs) / 1000)));
    };
    updateElapsed();
    const timerId = window.setInterval(updateElapsed, CONVERSION_TIMER_INTERVAL_MS);
    return () => window.clearInterval(timerId);
  }, [conversionInFlightSessionId, conversionStartedAtMs]);

  function mergeSessionIntoInputPackages(session: P3DesignLabSession) {
    setInputPackages((current) =>
      current.map((item) =>
        item.input_package_id === session.input_package.input_package_id ? session.input_package : item,
      ),
    );
  }

  function openCreateDesignModal() {
    if (!selectedPackage) {
      return;
    }
    setDraftMeta({
      title: buildDefaultDesignTitle(selectedPackage, workbench.inputFacts.relatedDesigns.length),
      versionLabel: buildDefaultVersionLabel(workbench.inputFacts.relatedDesigns.length),
    });
    setCreateModalOpen(true);
  }

  async function handleCreateConversionSession(meta: P3DesignDraftMeta) {
    if (!selectedPackage) {
      return;
    }
    const designTitle = meta.title.trim();
    const versionLabel = meta.versionLabel.trim();
    if (!designTitle || !versionLabel) {
      setError("新建软件设计说明前必须填写名称和版本。");
      return;
    }
    try {
      setSubmitting(true);
      const created = await createSoftwareDesignV2Session({
        input_package_id: selectedPackage.input_package_id,
        design_title: designTitle,
        version_label: versionLabel,
        generation_policy: DEFAULT_POLICY,
      });
      setDesignSession(created.data);
      setConversionStrategy(toConversionStrategy(created.data.conversion?.strategy));
      mergeSessionIntoInputPackages(created.data);
      setActiveNavigationKey("workspace");
      setActiveMorphWindowId("reqdoc");
      setCreateModalOpen(false);
      setError(null);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "创建软件设计说明失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOpenDesignSession(sessionId: string) {
    try {
      setSubmitting(true);
      const response = await getSoftwareDesignV2Session(sessionId);
      setDesignSession(response.data);
      setConversionStrategy(toConversionStrategy(response.data.conversion?.strategy));
      mergeSessionIntoInputPackages(response.data);
      setActiveNavigationKey("workspace");
      setActiveMorphWindowId(response.data.design_document ? "docfunc" : "reqdoc");
      setError(null);
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "打开软件设计说明失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteDesignSession(sessionId: string) {
    try {
      setSubmitting(true);
      await deleteSoftwareDesignV2Session(sessionId);
      setInputPackages((current) =>
        current.map((item) => ({
          ...item,
          related_designs: item.related_designs?.filter((design) => design.software_design_id !== sessionId) ?? [],
        })),
      );
      if (designSession?.session_id === sessionId) {
        setDesignSession(null);
      }
      setError(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除软件设计说明失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitTurn() {
    if (!designSession || !cliInput.trim()) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await appendSoftwareDesignV2Turn(designSession.session_id, { user_input: cliInput.trim() });
      setDesignSession(response.data.session);
      mergeSessionIntoInputPackages(response.data.session);
      setError(null);
    } catch (turnError) {
      setError(turnError instanceof Error ? turnError.message : "提交设计回合失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitScopedTurn(payload: SoftwareDesignV2TurnPayload) {
    if (!designSession) {
      return null;
    }
    try {
      setSubmitting(true);
      const response = await appendSoftwareDesignV2Turn(designSession.session_id, payload);
      setDesignSession(response.data.session);
      mergeSessionIntoInputPackages(response.data.session);
      setError(null);
      return response.data.turn;
    } catch (turnError) {
      const message = getApiErrorMessage(turnError, "提交局部设计沟通失败");
      setError(message);
      throw new Error(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApplyScopedPatch(
    proposal: P3DesignPatchProposal,
    options: { turnId?: string; userNote?: string } = {},
  ): Promise<P3DesignPatchApplyResult | null> {
    if (!designSession) {
      return null;
    }
    try {
      setSubmitting(true);
      const response = await applySoftwareDesignV2PatchProposal(designSession.session_id, proposal.proposal_id, {
        turn_id: options.turnId,
        base_revision_id: proposal.base_revision_id,
        apply_scope: "document_only",
        ...(options.userNote ? { user_note: options.userNote } : {}),
      });
      setDesignSession(response.data.updated_session);
      mergeSessionIntoInputPackages(response.data.updated_session);
      setError(null);
      return response.data;
    } catch (applyError) {
      const message = getApiErrorMessage(applyError, "应用局部补丁失败");
      setError(message);
      throw new Error(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRunConversion() {
    if (!designSession) {
      return;
    }
    if (conversionInFlightSessionId === designSession.session_id) {
      return;
    }
    const runningSessionId = designSession.session_id;
    try {
      setSubmitting(true);
      setConversionInFlightSessionId(runningSessionId);
      setConversionStartedAtMs(Date.now());
      setConversionElapsedSeconds(0);
      const response = await runSoftwareDesignV2Conversion(runningSessionId, { strategy: conversionStrategy });
      setDesignSession(response.data);
      setConversionStrategy(toConversionStrategy(response.data.conversion?.strategy));
      mergeSessionIntoInputPackages(response.data);
      setActiveMorphWindowId("docfunc");
      setError(null);
    } catch (conversionError) {
      setError(conversionError instanceof Error ? conversionError.message : "执行需规转软设基础转换失败");
    } finally {
      setConversionInFlightSessionId((current) => (current === runningSessionId ? null : current));
      setConversionStartedAtMs(null);
      setSubmitting(false);
    }
  }

  async function handleRunCheck() {
    if (!designSession) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await runSoftwareDesignV2Check(designSession.session_id);
      if (response.data.session) {
        setDesignSession(response.data.session);
        mergeSessionIntoInputPackages(response.data.session);
      } else {
        setDesignSession((current) => (current ? { ...current, check_result: response.data.check_result ?? null } : current));
      }
      setError(null);
    } catch (checkError) {
      setError(checkError instanceof Error ? checkError.message : "运行设计检查失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveDraft() {
    if (!designSession) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await saveSoftwareDesignV2Draft(designSession.session_id);
      setDesignSession(response.data);
      mergeSessionIntoInputPackages(response.data);
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存软件设计说明草稿失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateProjection() {
    if (!designSession) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await generateSoftwareDesignV2Projection(designSession.session_id);
      setDesignSession(response.data);
      mergeSessionIntoInputPackages(response.data);
      setActiveNavigationKey("workspace");
      setActiveMorphWindowId("shapep4");
      setError(null);
    } catch (projectionError) {
      setError(projectionError instanceof Error ? projectionError.message : "生成 P4 投影候选失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFreeze() {
    if (!designSession) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await freezeSoftwareDesignV2Session(designSession.session_id);
      setDesignSession(response.data);
      mergeSessionIntoInputPackages(response.data);
      setError(null);
    } catch (freezeError) {
      setError(freezeError instanceof Error ? freezeError.message : "冻结设计包失败");
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
    conversionStrategy,
    designSession,
    activeMorphWindowId,
    onDeleteDesignSession: (sessionId) => void handleDeleteDesignSession(sessionId),
    onFreeze: () => void handleFreeze(),
    onGenerate: openCreateDesignModal,
    onGenerateProjection: () => void handleGenerateProjection(),
    onOpenDesignSession: (sessionId) => void handleOpenDesignSession(sessionId),
    onOpenWorkspace: () => {
      setActiveNavigationKey("workspace");
      setActiveMorphWindowId("docfunc");
    },
    onRunCheck: () => void handleRunCheck(),
    onSaveDraft: () => void handleSaveDraft(),
    onSubmitTurn: () => void handleSubmitTurn(),
    onRefreshInputPackages: () => void refreshInputPackages(),
    onRunConversion: () => void handleRunConversion(),
    onSetConversionStrategy: setConversionStrategy,
    onSetMorphWindowId: setActiveMorphWindowId,
    onApplyScopedPatch: handleApplyScopedPatch,
    onSubmitScopedTurn: handleSubmitScopedTurn,
    workbench,
  });

  return (
    <>
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
      <CreateDesignSessionModal
        draftMeta={draftMeta}
        open={createModalOpen}
        submitting={submitting}
        onCancel={() => setCreateModalOpen(false)}
        onChange={setDraftMeta}
        onSubmit={() => void handleCreateConversionSession(draftMeta)}
      />
    </>
  );
}

function buildDefaultDesignTitle(inputPackage: P3DesignLabInputPackage, relatedDesignCount: number) {
  const sourceTitle = inputPackage.source_title.replace(/需求规格说明$/, "").trim();
  const serial = `${relatedDesignCount + 1}`.padStart(2, "0");
  return `${sourceTitle || "未命名软件"}设计说明（设计方案 ${serial}）`;
}

function buildDefaultVersionLabel(relatedDesignCount: number) {
  return `v0.${relatedDesignCount + 1}`;
}

function toConversionStrategy(value: string | undefined | null): P3DesignConversionStrategy {
  if (value === "component_first" || value === "p4_projection_first") {
    return value;
  }
  return "standard_sdd_draft";
}

function CreateDesignSessionModal({
  draftMeta,
  open,
  submitting,
  onCancel,
  onChange,
  onSubmit,
}: {
  draftMeta: P3DesignDraftMeta;
  open: boolean;
  submitting: boolean;
  onCancel: () => void;
  onChange: (value: P3DesignDraftMeta) => void;
  onSubmit: () => void;
}) {
  return (
    <Modal
      cancelText="取消"
      okButtonProps={{ disabled: !draftMeta.title.trim() || !draftMeta.versionLabel.trim(), loading: submitting }}
      okText="创建并转换"
      open={open}
      title="新建软件设计说明"
      onCancel={onCancel}
      onOk={onSubmit}
    >
      <div className="p3-design-lab-create-design-form">
        <label>
          <Text strong>软设名称</Text>
          <Input
            aria-label="软设名称"
            value={draftMeta.title}
            onChange={(event) => onChange({ ...draftMeta, title: event.target.value })}
          />
        </label>
        <label>
          <Text strong>版本标识</Text>
          <Input
            aria-label="版本标识"
            value={draftMeta.versionLabel}
            onChange={(event) => onChange({ ...draftMeta, versionLabel: event.target.value })}
          />
        </label>
        <Text type="secondary">名称和版本会写入当前软设会话、关联软设列表、A4 正文页脚和冻结设计包。</Text>
      </div>
    </Modal>
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
      subtitle: "形态链 / Canvas 视口",
      badge: workbench.product.status === "empty" ? "待转换" : `${workbench.projection.items.length} 投影`,
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
  conversionStrategy,
  designSession,
  activeMorphWindowId,
  onDeleteDesignSession,
  onFreeze,
  onGenerate,
  onGenerateProjection,
  onOpenDesignSession,
  onOpenWorkspace,
  onRunCheck,
  onSaveDraft,
  onSubmitTurn,
  onRefreshInputPackages,
  onRunConversion,
  onSetConversionStrategy,
  onSetMorphWindowId,
  onApplyScopedPatch,
  onSubmitScopedTurn,
  workbench,
}: {
  activeNavigationKey: P3DesignLabNavigationKey;
  cliInput: string;
  inputPackages: P3DesignLabInputPackage[];
  selectedPackageId: string | null;
  setCliInput: (value: string) => void;
  setSelectedPackageId: (value: string) => void;
  conversionStrategy: P3DesignConversionStrategy;
  designSession: P3DesignLabSession | null;
  activeMorphWindowId: string;
  onDeleteDesignSession: (sessionId: string) => void;
  onFreeze: () => void;
  onGenerate: () => void;
  onGenerateProjection: () => void;
  onOpenDesignSession: (sessionId: string) => void;
  onOpenWorkspace: () => void;
  onRunCheck: () => void;
  onSaveDraft: () => void;
  onSubmitTurn: () => void;
  onRefreshInputPackages: () => void;
  onRunConversion: () => void;
  onSetConversionStrategy: (value: P3DesignConversionStrategy) => void;
  onSetMorphWindowId: (value: string) => void;
  onApplyScopedPatch: (
    proposal: P3DesignPatchProposal,
    options?: { turnId?: string; userNote?: string },
  ) => Promise<P3DesignPatchApplyResult | null>;
  onSubmitScopedTurn: (payload: SoftwareDesignV2TurnPayload) => Promise<P3DesignTurn | null>;
  workbench: StageDocumentWorkbenchViewModel;
}) {
  if (activeNavigationKey === "input") {
    return (
      <InputPackageView
        inputFacts={workbench.inputFacts}
        inputPackages={inputPackages}
        selectedPackageId={selectedPackageId}
        workbench={workbench}
        onDeleteDesignSession={onDeleteDesignSession}
        onGenerate={onGenerate}
        onOpenDesignSession={onOpenDesignSession}
        onRefreshInputPackages={onRefreshInputPackages}
        onSelectPackage={setSelectedPackageId}
      />
    );
  }

  if (activeNavigationKey === "turn") {
    return (
      <CurrentTurnView
        cliInput={cliInput}
        interaction={workbench.interaction}
        onCliInputChange={setCliInput}
        onSubmitTurn={onSubmitTurn}
      />
    );
  }

  if (activeNavigationKey === "review") {
    return (
      <WorkspacePanel
        actions={
          <>
            <Button aria-label="运行检查" disabled={workbench.product.status === "empty"} onClick={onRunCheck}>
              运行检查
            </Button>
            <Button
              aria-label="冻结设计包"
              disabled={workbench.quality.status === "not_run" || workbench.quality.summary.blockingCount > 0}
              type="primary"
              onClick={onFreeze}
            >
              冻结设计包
            </Button>
          </>
        }
        title="检查评审"
        subtitle="检查评审只负责门禁、证据和冻结候选，不生成设计内容。"
      >
        <QualityCheckPanel quality={workbench.quality} />
      </WorkspacePanel>
    );
  }

  if (activeNavigationKey === "log") {
    return <RuntimeLogView workbench={workbench} />;
  }

  return (
    <SoftwareDesignWorkspaceView
      activeWindowId={activeMorphWindowId}
      session={designSession}
      strategy={conversionStrategy}
      workbench={workbench}
      onGenerateProjection={onGenerateProjection}
      onOpenWorkspace={onOpenWorkspace}
      onRunConversion={onRunConversion}
      onSaveDraft={onSaveDraft}
      onSetStrategy={onSetConversionStrategy}
      onSetWindowId={onSetMorphWindowId}
      onApplyScopedPatch={onApplyScopedPatch}
      onSubmitScopedTurn={onSubmitScopedTurn}
    />
  );
}

function InputPackageView({
  inputFacts,
  inputPackages,
  selectedPackageId,
  workbench,
  onDeleteDesignSession,
  onGenerate,
  onOpenDesignSession,
  onRefreshInputPackages,
  onSelectPackage,
}: {
  inputFacts: StageInputFactsViewModel;
  inputPackages: P3DesignLabInputPackage[];
  selectedPackageId: string | null;
  workbench: StageDocumentWorkbenchViewModel;
  onDeleteDesignSession: (sessionId: string) => void;
  onGenerate: () => void;
  onOpenDesignSession: (sessionId: string) => void;
  onRefreshInputPackages: () => void;
  onSelectPackage: (value: string) => void;
}) {
  return (
    <WorkspacePanel
      actions={
        <Button aria-label="刷新输入包" onClick={onRefreshInputPackages}>
          刷新输入包
        </Button>
      }
      title="需规输入"
      subtitle="先选择可进入 P3 的需求规格说明，再查看或创建它关联的软件设计说明。"
    >
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
                    <Button aria-label="进入编辑" size="small" onClick={() => onOpenDesignSession(design.software_design_id)}>
                      进入编辑
                    </Button>
                    <Button aria-label="删除" danger size="small" onClick={() => onDeleteDesignSession(design.software_design_id)}>
                      删除
                    </Button>
                  </Space>
                </article>
              ))
            ) : workbench.product.status === "empty" ? (
              <div className="p3-design-lab-empty-state">当前需规尚未生成关联软设。</div>
            ) : (
              <article className="p3-design-lab-related-design-card">
                <span>
                  <Text strong>{workbench.product.title ?? "未命名软件设计说明"}</Text>
                  <Text type="secondary">版本：{workbench.product.versionLabel}</Text>
                </span>
                <Space wrap>
                  <Tag color="green">草稿</Tag>
                  <Button size="small">进入编辑</Button>
                  <Button danger size="small">删除</Button>
                </Space>
              </article>
            )}
            <Button disabled={!inputFacts.title} type="primary" onClick={onGenerate}>
              新建软设
            </Button>
          </div>
        </section>
      </div>
    </WorkspacePanel>
  );
}

function SoftwareDesignWorkspaceView({
  activeWindowId,
  session,
  strategy,
  workbench,
  onGenerateProjection,
  onOpenWorkspace,
  onRunConversion,
  onSaveDraft,
  onSetStrategy,
  onSetWindowId,
  onApplyScopedPatch,
  onSubmitScopedTurn,
}: {
  activeWindowId: string;
  session: P3DesignLabSession | null;
  strategy: P3DesignConversionStrategy;
  workbench: StageDocumentWorkbenchViewModel;
  onGenerateProjection: () => void;
  onOpenWorkspace: () => void;
  onRunConversion: () => void;
  onSaveDraft: () => void;
  onSetStrategy: (value: P3DesignConversionStrategy) => void;
  onSetWindowId: (value: string) => void;
  onApplyScopedPatch: (
    proposal: P3DesignPatchProposal,
    options?: { turnId?: string; userNote?: string },
  ) => Promise<P3DesignPatchApplyResult | null>;
  onSubmitScopedTurn: (payload: SoftwareDesignV2TurnPayload) => Promise<P3DesignTurn | null>;
}) {
  const [isWorkspaceFullscreen, setWorkspaceFullscreen] = useState(false);
  const morphModel = useMemo(() => buildP3DesignMorphModel(workbench), [workbench]);
  const activeWindow = useMemo(
    () => morphModel.windows.find((window) => window.id === activeWindowId) ?? morphModel.windows[0],
    [activeWindowId, morphModel.windows],
  );
  const [selectedMorphObject, setSelectedMorphObject] = useState<DesignMorphSelection | null>(() =>
    activeWindow ? buildDesignMorphStageRelationSelection(activeWindow) : null,
  );
  const activeStepId = getActiveConversionStepId(workbench.conversion.status, workbench.conversion.steps);
  const hasSession = workbench.product.documentId !== "p3-design-lab-draft";
  const hasDraft = workbench.product.status !== "empty";
  const conversionRunning = workbench.conversion.running;
  const strategyOptions = workbench.conversion.strategyOptions.map((item) => ({ label: item.label, value: item.value }));
  const fullscreenButtonLabel = isWorkspaceFullscreen ? "缩回工作区" : "网页全屏";

  useEffect(() => {
    if (!isWorkspaceFullscreen) {
      return undefined;
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setWorkspaceFullscreen(false);
      }
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isWorkspaceFullscreen]);

  useEffect(() => {
    if (!activeWindow || selectedMorphObject) {
      return;
    }
    setSelectedMorphObject(buildDesignMorphStageRelationSelection(activeWindow));
  }, [activeWindow, selectedMorphObject]);

  useEffect(() => {
    if (!activeWindow || selectedMorphObject?.kind !== "stage_relation") {
      return;
    }
    if (selectedMorphObject.objectId !== activeWindow.id) {
      setSelectedMorphObject(buildDesignMorphStageRelationSelection(activeWindow));
    }
  }, [activeWindow, selectedMorphObject]);

  function handleMorphWindowChange(windowId: string) {
    onSetWindowId(windowId);
    const nextWindow = morphModel.windows.find((window) => window.id === windowId);
    if (nextWindow) {
      setSelectedMorphObject(buildDesignMorphStageRelationSelection(nextWindow));
    }
  }

  return (
    <WorkspacePanel
      actions={
        <>
          <Button aria-label="保存草稿" disabled={!hasDraft || conversionRunning} onClick={onSaveDraft}>
            保存草稿
          </Button>
          <Button aria-label="生成投影候选" disabled={!hasDraft || conversionRunning} onClick={onGenerateProjection}>
            生成投影候选
          </Button>
          <Button aria-label={fullscreenButtonLabel} onClick={() => setWorkspaceFullscreen((current) => !current)}>
            {fullscreenButtonLabel}
          </Button>
        </>
      }
      compactHeader={isWorkspaceFullscreen}
      fullscreen={isWorkspaceFullscreen}
      subtitle="需规、软设文档、功能树、分层架构、技术实现、展示形态和 P4 投影在同一个 Canvas 工作区中传递。"
      title="软设工作区"
    >
      <div className="p3-design-morph-workspace" data-testid="p3-design-morph-workspace">
        <section className="p3-design-morph-main">
          <DesignMorphCanvasPlatform
            activeWindowId={activeWindow?.id ?? "reqdoc"}
            selectedMorphObjectId={selectedMorphObject?.objectId}
            stages={morphModel.stages}
            windows={morphModel.windows}
            onActiveWindowChange={handleMorphWindowChange}
            onSelectMorphObject={setSelectedMorphObject}
          />
        </section>
        <aside className="p3-design-morph-side" data-testid="design-morph-inspector">
          <SelectedMorphObjectInspector
            activeStepId={activeStepId}
            activeWindowTitle={activeWindow?.title ?? "需规文档 -> 软设文档"}
            hasSession={hasSession}
            selection={selectedMorphObject}
            session={session}
            strategy={strategy}
            strategyOptions={strategyOptions}
            workbench={workbench}
            onRunConversion={onRunConversion}
            onSetStrategy={onSetStrategy}
            onApplyScopedPatch={onApplyScopedPatch}
            onSubmitScopedTurn={onSubmitScopedTurn}
          />
        </aside>
      </div>
    </WorkspacePanel>
  );
}

function getActiveConversionStepId(
  status: string,
  steps: StageDocumentWorkbenchViewModel["conversion"]["steps"],
) {
  if (status === "conversion_pending") {
    return steps[0]?.stepId;
  }
  if (status === "conversion_running") {
    return steps.find((step) => step.status === "running")?.stepId ?? steps.find((step) => step.status !== "done")?.stepId ?? steps[0]?.stepId;
  }
  if (status === "conversion_failed") {
    return steps.find((step) => step.status === "failed")?.stepId ?? steps.find((step) => step.status !== "done")?.stepId;
  }
  if (status === "draft_ready") {
    return steps.at(-1)?.stepId;
  }
  return undefined;
}

function SelectedMorphObjectInspector({
  activeStepId,
  activeWindowTitle,
  hasSession,
  selection,
  session,
  strategy,
  strategyOptions,
  workbench,
  onRunConversion,
  onSetStrategy,
  onApplyScopedPatch,
  onSubmitScopedTurn,
}: {
  activeStepId?: string;
  activeWindowTitle: string;
  hasSession: boolean;
  selection: DesignMorphSelection | null;
  session: P3DesignLabSession | null;
  strategy: P3DesignConversionStrategy;
  strategyOptions: Array<{ label: string; value: string }>;
  workbench: StageDocumentWorkbenchViewModel;
  onRunConversion: () => void;
  onSetStrategy: (value: P3DesignConversionStrategy) => void;
  onApplyScopedPatch: (
    proposal: P3DesignPatchProposal,
    options?: { turnId?: string; userNote?: string },
  ) => Promise<P3DesignPatchApplyResult | null>;
  onSubmitScopedTurn: (payload: SoftwareDesignV2TurnPayload) => Promise<P3DesignTurn | null>;
}) {
  const [activeInspectorTab, setActiveInspectorTab] = useState<InspectorTabKey>("ability");
  const subtitle = selection ? `${getSelectionKindLabel(selection.kind)} · ${selection.status ?? "待处理"}` : activeWindowTitle;

  useEffect(() => {
    setActiveInspectorTab("ability");
  }, [selection?.objectId, selection?.kind]);

  return (
    <>
      <CompactInspectorHead title="当前选中对象" subtitle={subtitle} />
      <InspectorTabBar activeTab={activeInspectorTab} onTabChange={setActiveInspectorTab} />
      <div className="p3-design-morph-tab-panel">
        {activeInspectorTab === "common" ? (
          <MorphCommonInfoInspector activeWindowTitle={activeWindowTitle} selection={selection} workbench={workbench} />
        ) : selection?.kind === "stage_relation" ? (
          <StageRelationInspector
            activeStepId={activeStepId}
            hasSession={hasSession}
            selection={selection}
            strategy={strategy}
            strategyOptions={strategyOptions}
            workbench={workbench}
            onRunConversion={onRunConversion}
            onSetStrategy={onSetStrategy}
          />
        ) : selection ? (
          <MorphObjectDetailInspector
            hasSession={hasSession}
            selection={selection}
            session={session}
            workbench={workbench}
            onApplyScopedPatch={onApplyScopedPatch}
            onSubmitScopedTurn={onSubmitScopedTurn}
          />
        ) : (
          <MorphWorkspaceSummaryInspector activeWindowTitle={activeWindowTitle} workbench={workbench} />
        )}
      </div>
    </>
  );
}

function InspectorTabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: InspectorTabKey;
  onTabChange: (tab: InspectorTabKey) => void;
}) {
  return (
    <div className="p3-design-morph-inspector-tabs" role="tablist" aria-label="Inspector 内容">
      <button
        aria-selected={activeTab === "ability"}
        className={activeTab === "ability" ? "is-active" : ""}
        role="tab"
        type="button"
        onClick={() => onTabChange("ability")}
      >
        能力
      </button>
      <button
        aria-selected={activeTab === "common"}
        className={activeTab === "common" ? "is-active" : ""}
        role="tab"
        type="button"
        onClick={() => onTabChange("common")}
      >
        共性信息
      </button>
    </div>
  );
}

function StageRelationInspector({
  activeStepId,
  hasSession,
  selection,
  strategy,
  strategyOptions,
  workbench,
  onRunConversion,
  onSetStrategy,
}: {
  activeStepId?: string;
  hasSession: boolean;
  selection: DesignMorphSelection;
  strategy: P3DesignConversionStrategy;
  strategyOptions: Array<{ label: string; value: string }>;
  workbench: StageDocumentWorkbenchViewModel;
  onRunConversion: () => void;
  onSetStrategy: (value: P3DesignConversionStrategy) => void;
}) {
  const relationType = typeof selection.payload?.relationType === "string" ? selection.payload.relationType : "";
  const isBasicConversion = selection.objectId === "reqdoc";

  return (
    <>
      <div className="p3-design-morph-inspector-section p3-design-morph-selection-card">
        <Text strong>关系：{selection.title}</Text>
        <div className="p3-design-morph-relation-facts" data-testid="p3-design-morph-relation-facts">
          <RelationFact label="类型" value={formatRelationType(relationType)} />
          <RelationFact label="输入" value={toInspectorText(selection.payload?.inputSummary)} />
          <RelationFact label="输出" value={toInspectorText(selection.payload?.outputSummary)} />
        </div>
      </div>

      {isBasicConversion ? (
        <div className="p3-design-lab-conversion-control" data-testid="p3-design-lab-conversion-control">
          <div className="p3-design-lab-conversion-control-head">
            <Text strong>转换控制</Text>
            <Tag color={workbench.conversion.running ? "processing" : "orange"}>
              {workbench.conversion.running ? "执行中" : formatConversionStatus(workbench.conversion.status)}
            </Tag>
          </div>
          <div className="p3-design-lab-conversion-meta">
            <span>{toInspectorText(selection.payload?.inputSummary)}</span>
            <span>转换为</span>
            <span>{toInspectorText(selection.payload?.outputSummary)}</span>
          </div>
          <div className="p3-design-lab-conversion-strategy-picker">
            <Text className="p3-design-lab-conversion-strategy-label" type="secondary">
              转换策略
            </Text>
            <Select
              aria-label="转换策略"
              className="p3-design-lab-conversion-strategy"
              disabled={!hasSession || workbench.conversion.running}
              options={strategyOptions}
              value={strategy}
              onChange={(value) => onSetStrategy(toConversionStrategy(value))}
            />
          </div>
          <div className="p3-design-lab-conversion-action-stack">
            <Button
              block
              aria-label={workbench.conversion.running ? "正在生成软设" : "执行基础转换"}
              disabled={!hasSession || workbench.conversion.running}
              loading={workbench.conversion.running}
              type="primary"
              onClick={onRunConversion}
            >
              {workbench.conversion.running ? "正在生成软设" : "执行基础转换"}
            </Button>
          </div>
          <ConversionTimeline
            activeStepId={activeStepId}
            progressNote={workbench.conversion.progressNote}
            steps={workbench.conversion.steps}
          />
          <ConversionFeedbackCard workbench={workbench} />
          <div className="p3-design-lab-conversion-secondary-actions">
            <Button type="default">预览参数</Button>
            <Button type="default">查看转换日志</Button>
          </div>
        </div>
      ) : (
        <div className="p3-design-morph-inspector-section">
          <Text strong>关系动作</Text>
          <SelectionActionList actions={selection.actions} />
        </div>
      )}

      <div className="p3-design-morph-inspector-section">
        <div className="p3-design-morph-compact-head">
          <Text strong>转换反馈</Text>
          <Text type="secondary">{workbench.conversion.running ? "实时" : workbench.conversion.status}</Text>
        </div>
        <div className="p3-design-lab-baseline-summary">
          <Metric
            label="功能对象"
            value={`${workbench.conversion.traceabilitySummary?.targetCount ?? workbench.outline.baseline?.moduleCount ?? 0}`}
          />
          <Metric label="章节候选" value={`${workbench.product.sections.length}`} />
          <Metric label="需确认项" value={`${workbench.conversion.traceabilitySummary?.pendingConfirmationCount ?? 0}`} />
        </div>
      </div>

      <SelectedObjectTraceSummary selection={selection} />
    </>
  );
}

function ConversionFeedbackCard({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const featureCount = workbench.conversion.traceabilitySummary?.targetCount ?? workbench.outline.baseline?.moduleCount ?? 0;
  const sectionCount = workbench.product.sections.length;
  const pendingCount = workbench.conversion.traceabilitySummary?.pendingConfirmationCount ?? 0;
  const progressPrefix = workbench.conversion.running
    ? `正在${getCurrentConversionStepTitle(workbench) || "执行基础转换"}`
    : workbench.conversion.status === "draft_ready"
      ? "基础转换已完成"
      : "等待执行基础转换";

  return (
    <div className="p3-design-lab-conversion-feedback-card">
      <div className="p3-design-lab-conversion-feedback-line">
        <span>当前进展</span>
        <strong>
          {progressPrefix}，已识别 {featureCount} 个功能对象、{sectionCount} 个章节候选、{pendingCount} 个需确认项。
        </strong>
      </div>
      <div className="p3-design-lab-conversion-feedback-line">
        <span>输出结果</span>
        <strong>生成软设正文草稿后，自动切换到软设文档并高亮新增章节。</strong>
      </div>
    </div>
  );
}

function getCurrentConversionStepTitle(workbench: StageDocumentWorkbenchViewModel) {
  return (
    workbench.conversion.steps.find((step) => step.status === "running")?.title ??
    workbench.conversion.steps.find((step) => step.status !== "done")?.title ??
    workbench.conversion.steps.at(-1)?.title
  );
}

function ConversionTimeline({
  activeStepId,
  progressNote,
  steps,
}: {
  activeStepId?: string;
  progressNote?: string;
  steps: StageDocumentWorkbenchViewModel["conversion"]["steps"];
}) {
  return (
    <>
      {progressNote ? (
        <Text className="p3-design-lab-conversion-progress-note" type="secondary">
          {progressNote}
        </Text>
      ) : null}
      <div className="p3-design-lab-conversion-timeline" aria-label="需规转软设转换进度">
        {steps.map((step, index) => (
          <div
            className={[
              "p3-design-lab-conversion-step",
              step.status === "done" ? "is-done" : "",
              step.status === "running" ? "is-running" : "",
              step.stepId === activeStepId ? "is-current" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            data-testid={`p3-design-lab-conversion-step-${step.stepId}`}
            key={step.stepId}
          >
            <span>{index + 1}</span>
            <strong>{step.title}</strong>
          </div>
        ))}
      </div>
    </>
  );
}

function MorphObjectDetailInspector({
  hasSession,
  selection,
  session,
  workbench,
  onApplyScopedPatch,
  onSubmitScopedTurn,
}: {
  hasSession: boolean;
  selection: DesignMorphSelection;
  session: P3DesignLabSession | null;
  workbench: StageDocumentWorkbenchViewModel;
  onApplyScopedPatch: (
    proposal: P3DesignPatchProposal,
    options?: { turnId?: string; userNote?: string },
  ) => Promise<P3DesignPatchApplyResult | null>;
  onSubmitScopedTurn: (payload: SoftwareDesignV2TurnPayload) => Promise<P3DesignTurn | null>;
}) {
  if (selection.kind === "function_node") {
    return <FunctionNodeDetailInspector selection={selection} workbench={workbench} />;
  }

  if (selection.kind === "design_block") {
    return (
      <DesignBlockDetailInspector
        hasSession={hasSession}
        selection={selection}
        session={session}
        workbench={workbench}
        onApplyScopedPatch={onApplyScopedPatch}
        onSubmitScopedTurn={onSubmitScopedTurn}
      />
    );
  }

  return (
    <>
      <div className="p3-design-morph-inspector-section p3-design-morph-selection-card">
        <Text strong>对象：{selection.title}</Text>
        {selection.summary ? <Text type="secondary">{selection.summary}</Text> : null}
        <Space wrap>
          <Tag>{getSelectionKindLabel(selection.kind)}</Tag>
          {selection.status ? <Tag color="blue">{selection.status}</Tag> : null}
          {selection.sourceRefs.map((sourceRef) => (
            <Tag key={sourceRef}>{sourceRef}</Tag>
          ))}
        </Space>
      </div>
      <div className="p3-design-morph-inspector-section">
        <Text strong>局部动作</Text>
        <SelectionActionList actions={selection.actions} />
      </div>
      <SelectedObjectTraceSummary selection={selection} />
    </>
  );
}

function DesignBlockDetailInspector({
  hasSession,
  selection,
  session,
  workbench,
  onApplyScopedPatch,
  onSubmitScopedTurn,
}: {
  hasSession: boolean;
  selection: DesignMorphSelection;
  session: P3DesignLabSession | null;
  workbench: StageDocumentWorkbenchViewModel;
  onApplyScopedPatch: (
    proposal: P3DesignPatchProposal,
    options?: { turnId?: string; userNote?: string },
  ) => Promise<P3DesignPatchApplyResult | null>;
  onSubmitScopedTurn: (payload: SoftwareDesignV2TurnPayload) => Promise<P3DesignTurn | null>;
}) {
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [applying, setApplying] = useState(false);
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [latestLocalTurn, setLatestLocalTurn] = useState<P3DesignTurn | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<P3DesignPatchApplyResult | null>(null);
  const scopeAnchor = useMemo(
    () => buildDesignTurnScopeAnchor(selection, session, workbench),
    [selection, session, workbench],
  );
  const latestSessionTurn = useMemo(() => findLatestScopedTurn(session?.turns ?? [], scopeAnchor), [scopeAnchor, session?.turns]);
  const patchProposal = latestLocalTurn?.patch_proposal ?? latestSessionTurn?.patch_proposal ?? null;

  useEffect(() => {
    setLatestLocalTurn(null);
    setInstruction("");
    setStatusMessage(null);
    setLocalError(null);
    setActiveActionId(null);
    setApplyResult(null);
  }, [scopeAnchor.block_id, scopeAnchor.section_id, scopeAnchor.design_revision_id]);

  async function submitScopedInstruction(nextInstruction?: string, actionId?: string) {
    if (submitting) {
      return;
    }
    if (!hasSession || !session) {
      setStatusMessage(null);
      setLocalError("当前没有有效软设会话，请从需规输入中进入编辑或重新生成软设。");
      return;
    }
    const normalizedInstruction = (nextInstruction ?? instruction).trim();
    if (!normalizedInstruction) {
      setStatusMessage(null);
      setLocalError("请先填写局部调整要求。");
      return;
    }
    try {
      setSubmitting(true);
      setActiveActionId(actionId ?? null);
      setInstruction(normalizedInstruction);
      setStatusMessage("正在生成局部补丁提案");
      setLocalError(null);
      const turn = await onSubmitScopedTurn({
        turn_type: "scoped_design_edit",
        interaction_mode: "propose_patch",
        user_input: normalizedInstruction,
        expected_output: ["document_patch", "traceability_update", "quality_note"],
        scope_anchor: scopeAnchor,
      });
      if (turn) {
        setLatestLocalTurn(turn);
        setStatusMessage(turn.assistant_message || "已生成局部补丁提案，等待人工确认。");
      } else {
        setStatusMessage(null);
        setLocalError("局部补丁提案没有返回内容，请检查后端或 Dify 工作流输出。");
      }
    } catch (error) {
      setStatusMessage(null);
      setLocalError(error instanceof Error ? error.message : "局部补丁提案生成失败");
    } finally {
      setSubmitting(false);
      setActiveActionId(null);
    }
  }

  function handleExecuteScopedAction(action: DesignMorphSelectionAction) {
    const actionInstruction = buildScopedActionInstruction(action, selection);
    setInstruction(actionInstruction);
  }

  async function handleApplyPatchProposal() {
    if (!patchProposal || applying) {
      return;
    }
    try {
      setApplying(true);
      setStatusMessage(null);
      setLocalError(null);
      const result = await onApplyScopedPatch(patchProposal, {
        turnId: latestLocalTurn?.turn_id ?? latestSessionTurn?.turn_id,
      });
      if (result) {
        setApplyResult(result);
        setLatestLocalTurn(null);
        setStatusMessage("补丁已应用到文档");
      }
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "应用局部补丁失败");
    } finally {
      setApplying(false);
    }
  }

  return (
    <>
      <div className="p3-design-morph-inspector-section p3-design-morph-selection-card">
        <Text strong>对象：{selection.title}</Text>
        {selection.summary ? <Text type="secondary">{selection.summary}</Text> : null}
        <Space wrap>
          <Tag>{getSelectionKindLabel(selection.kind)}</Tag>
          {selection.status ? <Tag color="blue">{selection.status}</Tag> : null}
          {selection.sourceRefs.map((sourceRef) => (
            <Tag key={sourceRef}>{sourceRef}</Tag>
          ))}
        </Space>
      </div>
      <ScopedDesignTurnPanel
        actions={selection.actions}
        activeActionId={activeActionId}
        applyResult={applyResult}
        applying={applying}
        hasSession={hasSession}
        instruction={instruction}
        localError={localError}
        patchProposal={patchProposal}
        scopeTitle={scopeAnchor.selection_snapshot?.title ?? selection.title}
        session={session}
        statusMessage={statusMessage}
        submitting={submitting}
        onApplyPatch={() => void handleApplyPatchProposal()}
        onExecuteSuggestion={handleExecuteScopedAction}
        onInstructionChange={setInstruction}
        onSubmit={() => void submitScopedInstruction()}
      />
      <SelectedObjectTraceSummary selection={selection} />
    </>
  );
}

function ScopedDesignTurnPanel({
  actions,
  activeActionId,
  applyResult,
  applying,
  hasSession,
  instruction,
  localError,
  patchProposal,
  scopeTitle,
  session,
  statusMessage,
  submitting,
  onApplyPatch,
  onExecuteSuggestion,
  onInstructionChange,
  onSubmit,
}: {
  actions: DesignMorphSelection["actions"];
  activeActionId?: string | null;
  applyResult: P3DesignPatchApplyResult | null;
  applying: boolean;
  hasSession: boolean;
  instruction: string;
  localError: string | null;
  patchProposal: P3DesignPatchProposal | null;
  scopeTitle: string;
  session: P3DesignLabSession | null;
  statusMessage: string | null;
  submitting: boolean;
  onApplyPatch: () => void;
  onExecuteSuggestion: (action: DesignMorphSelectionAction) => void;
  onInstructionChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const hasPatchProposal = Boolean(patchProposal);
  return (
    <div className="p3-design-morph-inspector-section p3-design-scoped-turn-panel">
      <div className="p3-design-morph-compact-head">
        <Text strong>局部提案工作区</Text>
        <Text type="secondary">{scopeTitle}</Text>
      </div>
      {patchProposal ? (
        <ScopedPatchProposalPreview
          applyResult={applyResult}
          applying={applying}
          proposal={patchProposal}
          onApplyPatch={onApplyPatch}
        />
      ) : null}
      <ScopedSuggestionChips
        actions={actions}
        activeActionId={activeActionId}
        disabled={!hasSession || !session || submitting || applying}
        onExecuteSuggestion={onExecuteSuggestion}
      />
      <Input.TextArea
        aria-label="局部 AI 沟通输入"
        autoSize={{ minRows: 3, maxRows: 5 }}
        disabled={!hasSession || !session || submitting || applying}
        placeholder="说明你希望如何调整当前段落，例如拆分、补充接口边界或改写表达。"
        value={instruction}
        onChange={(event) => onInstructionChange(event.target.value)}
      />
      <Button
        aria-label="生成局部补丁提案"
        block
        disabled={!hasSession || !session || submitting || applying}
        loading={submitting}
        type="primary"
        onClick={onSubmit}
      >
        {hasPatchProposal ? "重新生成局部补丁提案" : "生成局部补丁提案"}
      </Button>
      {!hasSession || !session ? (
        <Alert
          showIcon
          className="p3-design-scoped-turn-alert"
          description="请先从需规输入中进入已有软设，或新建并完成基础转换。"
          message="当前没有有效软设会话"
          type="warning"
        />
      ) : null}
      {submitting ? (
        <div className="p3-design-scoped-turn-status" role="status">
          <Spin size="small" />
          <span>
            <Text strong>正在生成局部补丁提案</Text>
            <Text type="secondary">远端工作流通常约 180 秒，本地回退会更快。</Text>
          </span>
        </div>
      ) : null}
      {!submitting && localError ? (
        <Alert
          showIcon
          className="p3-design-scoped-turn-alert"
          description={localError}
          message="局部补丁提案生成失败"
          type="error"
        />
      ) : null}
      {!submitting && !localError && statusMessage ? (
        <Alert showIcon className="p3-design-scoped-turn-alert" message={statusMessage} type="success" />
      ) : null}
    </div>
  );
}

function ScopedSuggestionChips({
  actions,
  activeActionId,
  disabled,
  onExecuteSuggestion,
}: {
  actions: DesignMorphSelection["actions"];
  activeActionId?: string | null;
  disabled: boolean;
  onExecuteSuggestion: (action: DesignMorphSelectionAction) => void;
}) {
  if (!actions.length) {
    return null;
  }
  return (
    <div className="p3-design-scoped-suggestions" aria-label="局部提案输入建议">
      {actions.map((action) => (
        <Button
          aria-label={`填入${action.label}`}
          disabled={disabled || Boolean(action.disabled)}
          key={action.actionId}
          loading={activeActionId === action.actionId}
          size="small"
          type="default"
          onClick={() => onExecuteSuggestion(action)}
        >
          {action.label}
        </Button>
      ))}
    </div>
  );
}

function ScopedPatchProposalPreview({
  applyResult,
  applying,
  proposal,
  onApplyPatch,
}: {
  applyResult: P3DesignPatchApplyResult | null;
  applying: boolean;
  proposal: P3DesignPatchProposal;
  onApplyPatch: () => void;
}) {
  const proposalKind = resolvePatchProposalKind(proposal);
  const previewBlocks = collectPatchPreviewBlocks(proposal.operations);
  const canApply = isPatchProposalApplicable(proposal);
  const isApplied = proposal.status === "applied" || applyResult?.status === "applied";
  const applyLabel = proposalKind.applyLabel;
  const emptyReason = getPatchProposalEmptyReason(proposal);
  return (
    <div className="p3-design-scoped-patch-preview">
      <div className="p3-design-morph-compact-head">
        <Text strong>{proposalKind.title}</Text>
        <Tag color={isApplied ? "green" : canApply ? proposalKind.tagColor : "default"}>
          {isApplied ? "已应用" : canApply ? proposalKind.readyTag : proposalKind.blockedTag}
        </Tag>
      </div>
      {previewBlocks.length ? (
        <div className="p3-design-scoped-patch-blocks">
          {previewBlocks.map((block, index) => (
            <article key={`${block.block_id ?? block.title ?? "patch-block"}-${index}`}>
              <Text strong>{block.title || `补丁段落 ${index + 1}`}</Text>
              <Text type="secondary">{block.content || block.text}</Text>
            </article>
          ))}
        </div>
      ) : (
        <Text type="secondary">{emptyReason}</Text>
      )}
      {proposal.quality_notes?.length ? (
        <div className="p3-design-scoped-patch-notes">
          {proposal.quality_notes.map((note) => (
            <Text key={note} type="secondary">
              {note}
            </Text>
          ))}
        </div>
      ) : null}
      {canApply && !isApplied ? (
        <Button block aria-label={applyLabel} loading={applying} type="primary" onClick={onApplyPatch}>
          {applyLabel}
        </Button>
      ) : null}
      {!canApply && !isApplied ? (
        <Alert
          showIcon
          className="p3-design-scoped-turn-alert"
          message={proposalKind.blockedMessage}
          description={buildPatchBlockedDescription(proposal, proposalKind.blockedDescription)}
          type="warning"
        />
      ) : null}
      {isApplied ? (
        <Alert
          showIcon
          className="p3-design-scoped-turn-alert"
          message="补丁已应用到文档"
          description={applyResult ? `结果版本：${applyResult.application.result_revision_id}` : undefined}
          type="success"
        />
      ) : null}
    </div>
  );
}

function resolvePatchProposalKind(proposal: P3DesignPatchProposal) {
  const proposalType = proposal.proposal_type || inferPatchProposalType(proposal.operations);
  if (proposalType === "needs_manual_merge") {
    return {
      title: "非协议补丁",
      readyTag: "待处理",
      blockedTag: "不可应用",
      tagColor: "orange",
      applyLabel: "应用到文档",
      blockedMessage: "非协议补丁不可应用",
      blockedDescription: "当前结果包含 CodeFactory 不支持的 operations，不能写入正文。",
    };
  }
  if (proposalType === "advice_only") {
    return {
      title: "修改建议",
      readyTag: "待应用",
      blockedTag: "未形成可应用补丁",
      tagColor: "blue",
      applyLabel: "应用到文档",
      blockedMessage: "修改建议，未形成可应用补丁",
      blockedDescription: "当前结果缺少可执行 operations，不能写入正文。",
    };
  }
  if (proposalType === "section_replacement_candidate") {
    return {
      title: "整节替换候选",
      readyTag: "待确认",
      blockedTag: "不可应用",
      tagColor: "gold",
      applyLabel: "确认替换本节",
      blockedMessage: "整节替换候选不可应用",
      blockedDescription: "当前候选缺少可执行的整节替换 operations，不能写入正文。",
    };
  }
  if (proposalType === "document_replacement_candidate") {
    return {
      title: "整文替换候选",
      readyTag: "待确认",
      blockedTag: "不可应用",
      tagColor: "red",
      applyLabel: "确认替换整篇草稿",
      blockedMessage: "整文替换候选不可应用",
      blockedDescription: "当前前端尚未开放整文替换写入，请生成块级或整节补丁。",
    };
  }
  return {
    title: "补丁提案",
    readyTag: "待应用",
    blockedTag: "不可应用",
    tagColor: "blue",
    applyLabel: "应用到文档",
    blockedMessage: "补丁提案不可应用",
    blockedDescription: "当前结果缺少可执行 operations，不能写入正文。",
  };
}

function buildPatchBlockedDescription(proposal: P3DesignPatchProposal, fallback: string) {
  const unsupportedOps = proposal.applicability?.unsupported_ops?.length
    ? proposal.applicability.unsupported_ops
    : (proposal.diagnostics?.unsupported_ops ?? []);
  if (unsupportedOps.length) {
    return `不支持的操作：${unsupportedOps.join("、")}`;
  }
  return fallback;
}

function inferPatchProposalType(operations: P3DesignPatchOperation[]) {
  if (!operations.length) {
    return "advice_only";
  }
  const supportedOps = new Set([
    "rewrite_block",
    "split_block",
    "insert_block_after",
    "delete_block",
    "merge_blocks",
    "replace_section_blocks",
    "rewrite_section",
    "add_subsection",
    "update_trace_refs",
    "add_quality_note",
  ]);
  if (operations.some((operation) => !supportedOps.has(operation.op))) {
    return "needs_manual_merge";
  }
  if (operations.some((operation) => ["replace_section_blocks", "rewrite_section"].includes(operation.op))) {
    return "section_replacement_candidate";
  }
  if (operations.some((operation) => operation.op === "replace_document_draft")) {
    return "document_replacement_candidate";
  }
  return "executable_patch";
}

function collectPatchPreviewBlocks(operations: P3DesignPatchOperation[]): P3DesignPatchBlockPreview[] {
  return operations.flatMap((operation) => {
    if (operation.blocks?.length) {
      return operation.blocks;
    }
    if (operation.new_blocks?.length) {
      return operation.new_blocks;
    }
    if (operation.new_block) {
      return [operation.new_block];
    }
    if ((operation.op === "rewrite_block" || operation.op === "rewrite_section") && (operation.content || operation.new_content)) {
      return [
        {
          block_id: operation.block_id || operation.target_block_id || operation.section_id,
          title: operation.title || "改写内容",
          content: operation.content || operation.new_content,
          source_refs: operation.source_refs,
        },
      ];
    }
    return [];
  });
}

function getPatchProposalEmptyReason(proposal: P3DesignPatchProposal) {
  const proposalType = proposal.proposal_type || inferPatchProposalType(proposal.operations);
  if (proposalType === "advice_only") {
    return "当前结果是修改建议，未形成可直接写入正文的补丁操作。";
  }
  return "已生成结构化补丁，等待预览差异。";
}

function isPatchProposalApplicable(proposal: P3DesignPatchProposal) {
  if (proposal.status === "applied") {
    return false;
  }
  if (proposal.applicability && proposal.applicability.can_apply === false) {
    return false;
  }
  return proposal.operations.some((operation) =>
    [
      "rewrite_block",
      "split_block",
      "insert_block_after",
      "delete_block",
      "merge_blocks",
      "replace_section_blocks",
      "rewrite_section",
      "add_subsection",
      "update_trace_refs",
      "add_quality_note",
    ].includes(operation.op),
  );
}

function FunctionNodeDetailInspector({
  selection,
  workbench,
}: {
  selection: DesignMorphSelection;
  workbench: StageDocumentWorkbenchViewModel;
}) {
  const summary = isFunctionTreeSummary(selection.payload?.summary)
    ? selection.payload.summary
    : {
        nodeCount: 0,
        tracedNodeCount: 0,
        pendingNodeCount: 0,
        maxDepth: 0,
      };
  const originLabel = toInspectorText(selection.payload?.originLabel);
  const designRefs = toStringList(selection.payload?.designRefs);
  const architectureRefs = toStringList(selection.payload?.architectureRefs);
  const p4Refs = toStringList(selection.payload?.p4Refs);
  const moduleId = toInspectorText(selection.payload?.moduleId);
  const pendingAdjustmentSummary = toInspectorText(selection.payload?.pendingAdjustmentSummary);
  const supportingGroups = buildFunctionTreeSupportingGroups(selection.payload?.supportingNodes);

  return (
    <>
      <div className="p3-design-morph-inspector-section p3-design-morph-selection-card">
        <Text strong>对象：{selection.title}</Text>
        {selection.summary ? <Text type="secondary">{selection.summary}</Text> : null}
        <Space wrap>
          <Tag>树节点</Tag>
          {selection.status ? <Tag color="blue">{selection.status}</Tag> : null}
          {selection.sourceRefs.map((sourceRef) => (
            <Tag key={sourceRef}>{sourceRef}</Tag>
          ))}
        </Space>
      </div>

      <div className="p3-design-morph-inspector-section">
        <Text strong>功能树概览</Text>
        <div className="p3-design-lab-baseline-summary">
          <Metric label="功能节点" value={`${summary.nodeCount}`} />
          <Metric label="已追溯" value={`${summary.tracedNodeCount}`} />
          <Metric label="待确认" value={`${summary.pendingNodeCount}`} />
          <Metric label="最大层级" value={`${summary.maxDepth}`} />
        </div>
        <Text type="secondary">{originLabel}</Text>
      </div>

      <div className="p3-design-morph-inspector-section">
        <Text strong>节点详情</Text>
        <div className="p3-design-morph-relation-facts">
          <RelationFact label="节点类型" value={toInspectorText(selection.payload?.nodeType)} />
          <RelationFact label="所属模块" value={moduleId} />
          <RelationFact label="软设引用" value={designRefs.join("、") || "-"} />
          <RelationFact label="架构引用" value={architectureRefs.join("、") || "-"} />
          <RelationFact label="P4 引用" value={p4Refs.join("、") || "-"} />
        </div>
      </div>

      <div className="p3-design-morph-inspector-section">
        <Text strong>待应用调整</Text>
        <Text type="secondary">{pendingAdjustmentSummary}</Text>
      </div>

      {supportingGroups.length ? (
        <div className="p3-design-morph-inspector-section">
          <Text strong>支撑设计信息</Text>
          <div className="p3-design-morph-supporting-groups">
            {supportingGroups.map((group) => (
              <div className="p3-design-morph-supporting-group" key={group.type}>
                <span>{group.label}</span>
                <Space wrap size={[4, 4]}>
                  {group.nodes.map((node) => (
                    <Tag key={node.nodeId}>{node.title}</Tag>
                  ))}
                </Space>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="p3-design-morph-inspector-section">
        <Text strong>局部动作</Text>
        <SelectionActionList actions={selection.actions} />
      </div>

      <SelectedObjectTraceSummary selection={selection} />
    </>
  );
}

function isFunctionTreeSummary(value: unknown): value is {
  nodeCount: number;
  tracedNodeCount: number;
  pendingNodeCount: number;
  maxDepth: number;
} {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.nodeCount === "number" &&
    typeof candidate.tracedNodeCount === "number" &&
    typeof candidate.pendingNodeCount === "number" &&
    typeof candidate.maxDepth === "number"
  );
}

function buildDesignTurnScopeAnchor(
  selection: DesignMorphSelection,
  session: P3DesignLabSession | null,
  workbench: StageDocumentWorkbenchViewModel,
): P3DesignTurnScopeAnchor {
  const sectionId = toOptionalScopeText(selection.payload?.sectionId);
  const sourceRefs = collectScopeSourceRefs(selection, workbench);
  return {
    anchor_type: selection.kind,
    document_id: session?.session_id,
    design_revision_id: session?.version_label ?? workbench.product.versionLabel,
    section_id: sectionId,
    block_id: selection.objectId,
    selection_snapshot: {
      title: toOptionalScopeText(selection.payload?.sectionTitle) ?? selection.title,
      excerpt: selection.summary ?? "",
    },
    source_refs: sourceRefs,
  };
}

function collectScopeSourceRefs(selection: DesignMorphSelection, workbench: StageDocumentWorkbenchViewModel) {
  if (selection.sourceRefs.length) {
    return selection.sourceRefs;
  }

  const sectionId = toOptionalScopeText(selection.payload?.sectionId);
  const sectionTitle = toOptionalScopeText(selection.payload?.sectionTitle) ?? selection.title;
  const traceRefs = workbench.product.traceLinks.flatMap((traceLink) =>
    traceLinkMatchesSelection(traceLink, sectionId, sectionTitle) ? extractTraceSourceRefs(traceLink) : [],
  );
  if (traceRefs.length) {
    return uniqueStrings(traceRefs);
  }

  return workbench.inputFacts.sections.flatMap((section) => section.clauses.map((clause) => clause.clauseId)).slice(0, 3);
}

function traceLinkMatchesSelection(traceLink: Record<string, unknown>, sectionId: string | undefined, sectionTitle: string) {
  const targets = [
    traceLink.design_section,
    traceLink.designSection,
    traceLink.target_ref,
    traceLink.targetRef,
    traceLink.target_title,
    traceLink.targetTitle,
  ].flatMap((value) => (typeof value === "string" ? [value] : []));
  return targets.some((target) => {
    const normalizedTarget = target.toLowerCase();
    return Boolean(
      (sectionId && normalizedTarget.includes(sectionId.toLowerCase())) ||
        normalizedTarget.includes(sectionTitle.toLowerCase()) ||
        sectionTitle.toLowerCase().includes(normalizedTarget),
    );
  });
}

function extractTraceSourceRefs(traceLink: Record<string, unknown>) {
  return [
    traceLink.requirement_clause,
    traceLink.requirementClause,
    traceLink.source_ref,
    traceLink.sourceRef,
    traceLink.source_ref_id,
    traceLink.sourceRefId,
  ].flatMap((value) => (typeof value === "string" && value.trim() ? [value] : []));
}

function findLatestScopedTurn(turns: P3DesignTurn[], scopeAnchor: P3DesignTurnScopeAnchor): P3DesignTurn | null {
  for (let index = turns.length - 1; index >= 0; index -= 1) {
    const turn = turns[index];
    if (turn.turn_type !== "scoped_design_edit" || !turn.patch_proposal) {
      continue;
    }
    if (isSameScopeAnchor(turn.scope_anchor, scopeAnchor)) {
      return turn;
    }
  }
  return null;
}

function isSameScopeAnchor(left: P3DesignTurnScopeAnchor | undefined, right: P3DesignTurnScopeAnchor) {
  if (!left) {
    return false;
  }
  return (
    left.anchor_type === right.anchor_type &&
    left.section_id === right.section_id &&
    left.block_id === right.block_id &&
    left.design_revision_id === right.design_revision_id
  );
}

function toOptionalScopeText(value: unknown) {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function toStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

type FunctionTreeSupportingNode = {
  nodeId: string;
  title: string;
  nodeType: string;
  children?: FunctionTreeSupportingNode[];
};

function buildFunctionTreeSupportingGroups(value: unknown): Array<{
  type: string;
  label: string;
  nodes: FunctionTreeSupportingNode[];
}> {
  const nodes = collectFunctionTreeSupportingNodes(value);
  const orderedGroups = [
    { type: "interface", label: "接口" },
    { type: "data", label: "数据对象" },
    { type: "state", label: "状态" },
    { type: "quality", label: "质量约束" },
  ];
  return orderedGroups
    .map((group) => ({
      ...group,
      nodes: nodes.filter((node) => node.nodeType === group.type),
    }))
    .filter((group) => group.nodes.length > 0);
}

function collectFunctionTreeSupportingNodes(value: unknown): FunctionTreeSupportingNode[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isFunctionTreeSupportingNode(item)) {
      return [];
    }
    return [item, ...collectFunctionTreeSupportingNodes(item.children)];
  });
}

function isFunctionTreeSupportingNode(value: unknown): value is FunctionTreeSupportingNode {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return typeof candidate.nodeId === "string" && typeof candidate.title === "string" && typeof candidate.nodeType === "string";
}

function uniqueStrings(values: string[]) {
  return [...new Set(values.filter((value) => value.trim()))];
}

function MorphWorkspaceSummaryInspector({
  activeWindowTitle,
  workbench,
}: {
  activeWindowTitle: string;
  workbench: StageDocumentWorkbenchViewModel;
}) {
  return (
    <>
      <div className="p3-design-morph-inspector-section">
        <Text strong>{workbench.product.title ?? "待生成软件设计说明草稿"}</Text>
        <Text type="secondary">当前窗口：{activeWindowTitle}</Text>
        <Text type="secondary">版本：{workbench.product.versionLabel}</Text>
      </div>
      <WorkspaceTraceAndStructureSummary workbench={workbench} />
    </>
  );
}

function MorphCommonInfoInspector({
  activeWindowTitle,
  selection,
  workbench,
}: {
  activeWindowTitle: string;
  selection: DesignMorphSelection | null;
  workbench: StageDocumentWorkbenchViewModel;
}) {
  const commonInfo = buildMorphCommonInfo(selection, activeWindowTitle, workbench);
  return (
    <>
      <div className="p3-design-morph-common-banner">
        <div className="p3-design-morph-compact-head">
          <Text strong>共性信息</Text>
          <Tag color="blue">{commonInfo.kindLabel}</Tag>
        </div>
        <Text type="secondary">{commonInfo.note}</Text>
      </div>
      {commonInfo.groups.map((group) => (
        <div className="p3-design-morph-common-group" key={group.title}>
          <div className="p3-design-morph-common-group-head">
            <Text strong>{group.title}</Text>
            <Text type="secondary">{group.meta}</Text>
          </div>
          <div className="p3-design-morph-common-fields">
            {group.fields.map((field) => (
              <RelationFact key={`${group.title}-${field.label}`} label={field.label} value={field.value} />
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

type MorphCommonField = {
  label: string;
  value: string;
};

type MorphCommonGroup = {
  title: string;
  meta: string;
  fields: MorphCommonField[];
};

function buildMorphCommonInfo(
  selection: DesignMorphSelection | null,
  activeWindowTitle: string,
  workbench: StageDocumentWorkbenchViewModel,
): {
  kindLabel: string;
  note: string;
  groups: MorphCommonGroup[];
} {
  if (!selection) {
    return {
      kindLabel: "工作区",
      note: "未选中具体对象时，共性信息页展示当前软设工作区的基础上下文。",
      groups: [
        commonGroup("标识", "基类字段：标识信息", [
          ["名称", activeWindowTitle],
          ["对象类型", "软设形态窗口"],
          ["状态", workbench.product.status],
          ["版本", workbench.product.versionLabel],
        ]),
        commonGroup("布局", "基类字段：布局变换", [
          ["位置", "跟随当前 Canvas 视口"],
          ["尺寸", "窗口自适应"],
          ["缩放", "跟随 Canvas"],
          ["锁定", "否"],
        ]),
        commonGroup("追溯", "基类字段：追溯关系", [
          ["来源", workbench.inputFacts.title],
          ["目标", workbench.product.title ?? "软件设计说明"],
          ["下游", "功能树 / 分层架构 / P4 投影"],
          ["映射状态", workbench.conversion.status],
        ]),
        commonGroup("生命周期", "基类字段：生命周期", [
          ["创建时间", "-"],
          ["更新时间", "-"],
          ["最近操作", workbench.runtimeEvents[0]?.message ?? "等待操作"],
          ["操作人", "系统"],
        ]),
      ],
    };
  }

  const payload = selection.payload ?? {};
  const kindLabel = getSelectionKindLabel(selection.kind);
  const baseGroups = [
    commonGroup("标识", "基类字段：标识信息", [
      ["名称", selection.title],
      ["对象类型", kindLabel],
      ["状态", selection.status ?? "待处理"],
      ["版本", selection.objectId],
    ]),
    commonGroup("布局", "基类字段：布局变换", buildLayoutFields(selection)),
    commonGroup("追溯", "基类字段：追溯关系", [
      ["来源", formatRefs(selection.sourceRefs)],
      ["目标", toInspectorText(payload.toStageId ?? payload.sectionTitle ?? workbench.product.title ?? "软件设计说明")],
      ["下游", formatRefs(selection.qualityRefs ?? []) || "跟随当前软件设计包"],
      ["映射状态", selection.status ?? workbench.conversion.status],
    ]),
    commonGroup("生命周期", "基类字段：生命周期", [
      ["创建时间", toInspectorText(payload.createdAt ?? "-")],
      ["更新时间", toInspectorText(payload.updatedAt ?? "-")],
      ["最近操作", selection.actions[0]?.label ?? workbench.runtimeEvents[0]?.message ?? "等待操作"],
      ["操作人", "系统"],
    ]),
  ];

  if (selection.kind === "stage_relation") {
    baseGroups.push(
      commonGroup("关系扩展", "分型扩展：连接关系", [
        ["起点", toInspectorText(payload.fromStageId)],
        ["终点", toInspectorText(payload.toStageId)],
        ["关系类型", formatRelationType(toInspectorText(payload.relationType))],
        ["转换策略", formatConversionStrategy(workbench.conversion.strategy)],
        ["视觉宽度", "8 px"],
        ["命中宽度", "24 px"],
      ]),
    );
  }

  return {
    kindLabel,
    note:
      selection.kind === "stage_relation"
        ? "关系对象同样继承共性字段，并通过关系扩展承载起点、终点、策略和视觉命中范围。"
        : "当前对象继承 Inspector 共性字段；对象专属工作保留在能力页。",
    groups: baseGroups,
  };
}

function commonGroup(title: string, meta: string, fields: Array<[string, string]>): MorphCommonGroup {
  return {
    title,
    meta,
    fields: fields.map(([label, value]) => ({ label, value })),
  };
}

function buildLayoutFields(selection: DesignMorphSelection): Array<[string, string]> {
  if (selection.kind === "stage_relation") {
    return [
      ["位置", "由起点与终点动态计算"],
      ["尺寸", "连接线自适应"],
      ["缩放", "跟随 Canvas"],
      ["锁定", "否"],
    ];
  }
  if (selection.kind === "requirement_clause" || selection.kind === "design_block") {
    return [
      ["位置", toInspectorText(selection.payload?.sectionTitle ?? "文档正文块")],
      ["尺寸", "正文块自适应"],
      ["缩放", "跟随文档"],
      ["锁定", "是"],
    ];
  }
  return [
    ["位置", "跟随 Canvas 节点布局"],
    ["尺寸", "节点自适应"],
    ["缩放", "跟随 Canvas"],
    ["锁定", "否"],
  ];
}

function SelectionActionList({
  actions,
  activeActionId,
  disabled = false,
  onExecuteAction,
}: {
  actions: DesignMorphSelection["actions"];
  activeActionId?: string | null;
  disabled?: boolean;
  onExecuteAction?: (action: DesignMorphSelectionAction) => void;
}) {
  if (!actions.length) {
    return <div className="p3-design-lab-empty-state">当前对象没有可执行动作。</div>;
  }
  return (
    <div className="p3-design-lab-command-list">
      {actions.map((action) => (
        <CommandRow
          actionAriaLabel={`执行${action.label}`}
          description={action.description ?? action.commandHint ?? "作用于当前选中对象。"}
          disabled={disabled || Boolean(action.disabled)}
          key={action.actionId}
          loading={activeActionId === action.actionId}
          title={action.label}
          onExecute={onExecuteAction ? () => onExecuteAction(action) : undefined}
        />
      ))}
    </div>
  );
}

function SelectedObjectTraceSummary({ selection }: { selection: DesignMorphSelection }) {
  return (
    <div className="p3-design-morph-inspector-section">
      <Text strong>当前对象追溯</Text>
      <div className="p3-design-morph-relation-facts">
        <RelationFact label="来源" value={formatRefs(selection.sourceRefs) || "未绑定来源"} />
        <RelationFact label="下游" value={formatRefs(selection.qualityRefs ?? []) || "跟随当前软设对象"} />
        <RelationFact label="状态" value={selection.status ?? "待处理"} />
      </div>
    </div>
  );
}

function WorkspaceTraceAndStructureSummary({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  return (
    <>
      <div className="p3-design-morph-inspector-section">
        <Text strong>追溯链</Text>
        <div className="p3-design-lab-runline compact" aria-label="软设形态追溯链">
          {workbench.interaction.runline.map((step) => (
            <span className={step.state === "done" ? "is-done" : step.state === "active" ? "is-active" : ""} key={step.key}>
              {step.label}
            </span>
          ))}
        </div>
      </div>

      <div className="p3-design-morph-inspector-section">
        <Text strong>结构化摘要</Text>
        <div className="p3-design-lab-baseline-summary">
          <Metric label="架构模式" value={workbench.outline.baseline?.architectureMode ?? "-"} />
          <Metric label="模块数量" value={`${workbench.outline.baseline?.moduleCount ?? 0}`} />
          <Metric label="投影节点" value={`${workbench.projection.items.length}`} />
        </div>
      </div>

      <div className="p3-design-morph-inspector-section">
        <Text strong>投影树</Text>
        {workbench.projection.tree ? (
          <div className="p3-design-lab-projection-tree compact" role="tree" aria-label="P4 工单投影树">
            <ProjectionTreeNode node={workbench.projection.tree} selectedNodeId={getProjectionDetailNode(workbench.projection.tree)?.nodeId} />
          </div>
        ) : (
          <div className="p3-design-lab-empty-state">{workbench.projection.emptyDescription}</div>
        )}
      </div>
    </>
  );
}

function getSelectionKindLabel(kind: DesignMorphSelection["kind"]) {
  const labels: Record<DesignMorphSelection["kind"], string> = {
    stage: "阶段对象",
    stage_relation: "阶段关系",
    requirement_section: "需规章节",
    requirement_clause: "需规条款",
    design_section: "软设章节",
    design_block: "软设段落",
    function_node: "功能节点",
    architecture_layer: "架构层",
    architecture_module: "架构模块",
    technical_mapping: "技术映射",
    presentation_shape: "展示形态",
    projection_node: "投影节点",
  };
  return labels[kind];
}

function toInspectorText(value: unknown) {
  return typeof value === "string" && value.trim() ? value : "-";
}

function formatRefs(refs: string[]) {
  return refs.filter(Boolean).join(" / ");
}

function DocumentSectionObjectsPanel({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const selectedSection = getSelectedDesignSection(workbench);

  return (
    <section className="p3-design-lab-section-nav">
      <PanelHead title="章节对象" subtitle="同一套软设数据，当前以文档式 A4 正文展示。" />
      {workbench.product.sections.length ? (
        <ol className="p3-design-lab-object-list">
          <li className="is-active">
            <Text strong>生成过程</Text>
            <Text type="secondary">{"需规读取 -> 设计规划 -> 生成草稿 -> 人工复核"}</Text>
          </li>
          {workbench.product.sections.map((section) => (
            <li className={section.sectionId === selectedSection?.sectionId ? "is-selected" : ""} key={section.sectionId}>
              <Text strong>{section.title}</Text>
              <Space wrap>
                <Tag>{section.status}</Tag>
                <Tag>{section.sectionId}</Tag>
              </Space>
            </li>
          ))}
        </ol>
      ) : (
        <div className="p3-design-lab-empty-state">生成后显示软件设计说明章节。</div>
      )}
    </section>
  );
}

function SelectedDesignSectionInteractionPanel({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const selectedSection = getSelectedDesignSection(workbench);
  const boundSectionTitle = selectedSection?.title ?? "待选择章节";
  const baselineLabel = workbench.outline.baseline?.label ?? workbench.product.versionLabel;

  return (
    <section className="p3-design-lab-panel p3-design-lab-section-interaction">
      <PanelHead title="选中章节交互对象" subtitle="快捷动作和 CLI 都作用于当前章节，不在这里发布设计包。" />
      {selectedSection ? (
        <div className="p3-design-lab-interaction-stack">
          <article className="p3-design-lab-info-card">
            <Text strong>需规到软设生成过程</Text>
            <p>{"读取已发布需规 -> 生成设计规划 -> 生成软设草稿 -> 进入章节复核。"}</p>
            <div className="p3-design-lab-runline compact" aria-label="软设生成过程">
              {workbench.interaction.runline.map((step) => (
                <span className={step.state === "done" ? "is-done" : step.state === "active" ? "is-active" : ""} key={step.key}>
                  {step.label}
                </span>
              ))}
            </div>
          </article>
          <article className="p3-design-lab-info-card">
            <Text strong>对象：设计章节 {boundSectionTitle}</Text>
            <p>绑定 {baselineLabel}；映射正文块、结构化对象 architecture、模块边界和 P4 投影来源。</p>
          </article>
          <div className="p3-design-lab-command-list">
            <CommandRow title="扩写本节" description="围绕当前章节补充模块边界、接口关系和设计理由。" />
            <CommandRow title="补充小节" description="在当前章节下增加一个局部小节，并生成 document_patch。" />
            <CommandRow title="应用补丁" description="只更新当前章节正文，同时保持结构化数据默认同步。" />
          </div>
          <div className="p3-design-lab-mini-cli">
            <div className="p3-design-lab-cli-log compact">
              <div>
                <span>P3</span>
                <p>{workbench.interaction.message}</p>
              </div>
            </div>
            <Input.TextArea aria-label="章节交互 CLI 预览" disabled value="在总体架构里补一段文档视图和结构化数据视图的关系。" />
          </div>
        </div>
      ) : (
        <div className="p3-design-lab-empty-state">生成软件设计说明后显示章节交互对象。</div>
      )}
    </section>
  );
}

function buildScopedActionInstruction(action: DesignMorphSelectionAction, selection: DesignMorphSelection) {
  if (action.commandHint?.trim()) {
    return action.commandHint.trim();
  }
  if (action.actionId === "append_subsection") {
    return `在“${selection.title}”所属章节下补充一个局部小节，说明设计边界、接口关系和需要同步的追溯依据。`;
  }
  if (action.actionId === "apply_document_patch") {
    return `围绕“${selection.title}”生成可人工确认的文档补丁提案，说明正文更新、结构化事实同步和追溯更新建议。`;
  }
  return `${action.label}：${action.description ?? "请基于当前选中对象生成局部补丁提案。"}`;
}

function CommandRow({
  actionAriaLabel,
  description,
  disabled = false,
  loading = false,
  title,
  onExecute,
}: {
  actionAriaLabel?: string;
  description: string;
  disabled?: boolean;
  loading?: boolean;
  title: string;
  onExecute?: () => void;
}) {
  return (
    <article className="p3-design-lab-command-row">
      <span>
        <Text strong>{title}</Text>
        <Text type="secondary">{description}</Text>
      </span>
      <Button
        aria-label={actionAriaLabel}
        disabled={disabled}
        loading={loading}
        size="small"
        onClick={onExecute}
      >
        执行
      </Button>
    </article>
  );
}

function StructuredDesignDataView({
  workbench,
  onGenerateProjection,
}: {
  workbench: StageDocumentWorkbenchViewModel;
  onGenerateProjection: () => void;
}) {
  const baseline = workbench.outline.baseline;
  return (
    <div className="p3-design-lab-structured-view" data-testid="p3-design-structured-data-view">
      <section className="p3-design-lab-panel">
        <PanelHead title="结构化数据导航" subtitle="这是软设数据的结构化展示，不再作为左侧独立主 Tab。" />
        {baseline ? (
          <div className="p3-design-lab-data-tree">
            <div className="p3-design-lab-data-tree-node is-active">
              <Text strong>{baseline.label}</Text>
              <Tag>当前</Tag>
            </div>
            <div className="p3-design-lab-data-tree-node level-2">
              <Text strong>sourceRequirement</Text>
              <Tag>REQ</Tag>
            </div>
            <div className="p3-design-lab-data-tree-node level-2 is-selected">
              <Text strong>architecture</Text>
              <Tag color="green">{baseline.moduleCount} 模块</Tag>
            </div>
            {baseline.modules.map((module) => (
              <div className="p3-design-lab-data-tree-node level-3" key={module.moduleId}>
                <Text>{module.name}</Text>
                <Tag>{module.moduleId}</Tag>
              </div>
            ))}
            <div className="p3-design-lab-data-tree-node level-2">
              <Text strong>interfaces</Text>
              <Tag>待细化</Tag>
            </div>
            <div className="p3-design-lab-data-tree-node level-2">
              <Text strong>traceability</Text>
              <Tag color="green">{baseline.traceabilityCount}</Tag>
            </div>
          </div>
        ) : (
          <Empty description="生成软件设计说明后显示结构化设计基线" />
        )}
      </section>
      <section className="p3-design-lab-panel">
        <PanelHead title="选中结构化对象：architecture" subtitle="与 A4 正文共享同一份软设数据，负责模块、接口和追溯事实。" />
        {baseline ? (
          <div className="p3-design-lab-data-table">
            <div className="head">
              <span>字段</span>
              <span>值</span>
              <span>状态</span>
            </div>
            <div>
              <span>architectureMode</span>
              <span>{baseline.architectureMode}</span>
              <span>当前</span>
            </div>
            <div>
              <span>modules</span>
              <span>{baseline.modules.map((module) => module.name).join(" / ")}</span>
              <span>已生成</span>
            </div>
            <div>
              <span>sync</span>
              <span>正文章节与 architecture 对象默认同步</span>
              <span>已建立</span>
            </div>
            <div>
              <span>traceability</span>
              <span>{baseline.traceabilityCount} 条需求到设计追溯</span>
              <span>待复核</span>
            </div>
          </div>
        ) : (
          <div className="p3-design-lab-empty-state">暂无模块结构。</div>
        )}
      </section>
      <section className="p3-design-lab-panel">
        <PanelHead title="结构化数据动作" subtitle="动作作用于当前软设数据，不直接发布或冻结。" />
        <div className="p3-design-lab-baseline-summary">
          <Metric label="架构模式" value={baseline?.architectureMode ?? "-"} />
          <Metric label="模块数量" value={`${baseline?.moduleCount ?? 0}`} />
          <Metric label="追溯关系" value={`${baseline?.traceabilityCount ?? 0}`} />
        </div>
        <div className="p3-design-lab-trace-grid">
          {workbench.product.traceLinks.length ? (
            workbench.product.traceLinks.map((link, index) => <code key={`trace-${index}`}>{JSON.stringify(link)}</code>)
          ) : (
            <span>当前样例未返回细粒度追溯关系。</span>
          )}
        </div>
        <Button disabled={!baseline} type="primary" onClick={onGenerateProjection}>
          生成投影候选
        </Button>
      </section>
    </div>
  );
}

function ProjectionTreeView({
  workbench,
  onGenerateProjection,
}: {
  workbench: StageDocumentWorkbenchViewModel;
  onGenerateProjection: () => void;
}) {
  const selectedNode = getProjectionDetailNode(workbench.projection.tree);

  return (
    <WorkspacePanel
      actions={
        <Button aria-label="生成投影候选" disabled={workbench.product.status === "empty"} onClick={onGenerateProjection}>
          生成投影候选
        </Button>
      }
      subtitle="P4 投影就是从 P3 设计基线派生出的下游工单组织树。"
      title="P4 投影"
    >
      <div className="p3-design-lab-projection-tree-view" data-testid="p3-design-lab-projection-tree">
        <section className="p3-design-lab-projection-tree-panel">
          <PanelHead title="P4 工单投影树" subtitle="P4 投影本身就是下游工单组织形态，不再把投影和工单拆成两个概念。" />
          <div aria-label="P4 工单投影树" className="p3-design-lab-projection-tree" role="tree">
            {workbench.projection.tree ? (
              <ProjectionTreeNode node={workbench.projection.tree} selectedNodeId={selectedNode?.nodeId} />
            ) : workbench.projection.items.length ? (
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
          <PanelHead title="选中树节点详情" subtitle="展示一个分支下的工具包组织关系和来源追溯。" />
          {selectedNode ? (
            <div className="p3-design-lab-projection-detail">
              <article className="p3-design-lab-info-card">
                <Text strong>节点：{selectedNode.title}</Text>
                <p>
                  {selectedNode.description ??
                    "该节点是 P4 工单投影的一部分，描述下游工具包分支、来源追溯和验收边界。"}
                </p>
              </article>
              <div className="p3-design-lab-data-table">
                <div className="head">
                  <span>字段</span>
                  <span>值</span>
                  <span>状态</span>
                </div>
                <div>
                  <span>source</span>
                  <span>{selectedNode.sourceRefs?.join(" / ") || workbench.projection.sourceStateId || "SoftwareDesignBaseline"}</span>
                  <span>已追溯</span>
                </div>
                <div>
                  <span>depends_on</span>
                  <span>{selectedNode.dependsOn?.join(" / ") || "无前置依赖"}</span>
                  <span>已绑定</span>
                </div>
                <div>
                  <span>acceptance</span>
                  <span>{selectedNode.acceptance ?? "检查树节点、来源事实和包内工单是否完整。"}</span>
                  <span>{selectedNode.readiness ?? "待复核"}</span>
                </div>
              </div>
              <article className="p3-design-lab-info-card">
                <Text strong>本视图存在的意义</Text>
                <p>回答这份软设后续会形成哪些 P4 工单，以及这些工单如何按工具包分支组织。</p>
              </article>
            </div>
          ) : (
            <div className="p3-design-lab-empty-state">生成投影候选后显示节点详情。</div>
          )}
        </section>
      </div>
    </WorkspacePanel>
  );
}

function ProjectionTreeNode({
  node,
  selectedNodeId,
}: {
  node: NonNullable<StageDocumentWorkbenchViewModel["projection"]["tree"]>;
  selectedNodeId?: string;
}) {
  return (
    <div className={node.nodeId === selectedNodeId ? "p3-design-lab-projection-node is-selected" : "p3-design-lab-projection-node"} role="treeitem">
      <span>{node.title}</span>
      <Space wrap>
        <Tag>{node.nodeType}</Tag>
        {node.readiness ? <Tag color={node.readiness === "ready" ? "green" : "gold"}>{node.readiness}</Tag> : null}
      </Space>
      {node.children?.length ? (
        <div role="group">
          {node.children.map((child) => (
            <ProjectionTreeNode key={child.nodeId} node={child} selectedNodeId={selectedNodeId} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function getSelectedDesignSection(workbench: StageDocumentWorkbenchViewModel) {
  return (
    workbench.product.sections.find((section) => section.sectionId === "architecture") ??
    workbench.product.sections.find((section) => section.title.includes("总体架构")) ??
    workbench.product.sections[0]
  );
}

function getProjectionDetailNode(tree: StageDocumentWorkbenchViewModel["projection"]["tree"]) {
  if (!tree) {
    return null;
  }
  return findProjectionNode(tree, "B. P3 适配工具包") ?? tree.children?.find((child) => child.nodeType.includes("branch")) ?? tree;
}

function findProjectionNode(
  node: NonNullable<StageDocumentWorkbenchViewModel["projection"]["tree"]>,
  title: string,
): NonNullable<StageDocumentWorkbenchViewModel["projection"]["tree"]> | null {
  if (node.title === title) {
    return node;
  }
  for (const child of node.children ?? []) {
    const match = findProjectionNode(child, title);
    if (match) {
      return match;
    }
  }
  return null;
}

function CurrentTurnView({
  interaction,
  cliInput,
  onCliInputChange,
  onSubmitTurn,
}: {
  interaction: StageInteractionViewModel;
  cliInput: string;
  onCliInputChange: (value: string) => void;
  onSubmitTurn: () => void;
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
            <Button aria-label={interaction.composer.submitLabel} disabled={interaction.composer.disabled} onClick={onSubmitTurn}>
              {interaction.composer.submitLabel}
            </Button>
          </div>
        </section>
      </div>
    </WorkspacePanel>
  );
}

function RuntimeLogView({ workbench }: { workbench: StageDocumentWorkbenchViewModel }) {
  const logRows = workbench.runtimeEvents.length
    ? workbench.runtimeEvents.map((event) => ({
        time: formatDateTime(event.created_at),
        scope: event.event_type,
        content: event.message,
      }))
    : [
        { time: "09:00", scope: "GET", content: "读取 P2 需求规格冻结包" },
        { time: "09:01", scope: "ADAPTER", content: "构建 P3 Design Lab ViewModel" },
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
  fullscreen = false,
  compactHeader = false,
  children,
}: {
  title: string;
  subtitle: string;
  actions?: ReactNode;
  fullscreen?: boolean;
  compactHeader?: boolean;
  children: ReactNode;
}) {
  const panelClassName = [
    "p3-design-lab-workspace-panel",
    fullscreen ? "is-web-fullscreen" : "",
    compactHeader ? "is-compact-head" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={panelClassName} data-testid="p3-workspace-panel">
      <header className="p3-design-lab-workspace-head">
        <div>
          <Title level={3}>{title}</Title>
          {!compactHeader ? <Text type="secondary">{subtitle}</Text> : null}
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

function CompactInspectorHead({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="p3-design-morph-compact-head">
      <Text strong>{title}</Text>
      <Text type="secondary">{subtitle}</Text>
    </div>
  );
}

function RelationFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="p3-design-morph-relation-fact">
      <span>{label}</span>
      <strong>{value}</strong>
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

function formatConversionStatus(status: string) {
  if (status === "conversion_pending") {
    return "待转换";
  }
  if (status === "conversion_running") {
    return "转换中";
  }
  if (status === "draft_ready") {
    return "已生成草稿";
  }
  if (status === "conversion_failed") {
    return "转换失败";
  }
  if (status === "empty") {
    return "待新建";
  }
  return status;
}

function formatRelationType(value: string) {
  const labels: Record<string, string> = {
    requirement_to_design_document: "需规转软设",
    design_document_to_function_tree: "正文转功能树",
    function_tree_to_layered_architecture: "功能归层",
    layered_architecture_to_technical_implementation: "架构转技术",
    technical_implementation_to_presentation_shape: "技术转展示",
    presentation_shape_to_p4_projection: "展示转投影",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatConversionStrategy(value: string) {
  const labels: Record<string, string> = {
    standard_sdd_draft: "标准软设草稿生成",
    component_first: "组件优先拆解",
    p4_projection_first: "P4 投影优先",
  };
  return labels[value] ?? (value || "-");
}

function formatDateTime(value: string) {
  return value.slice(0, 16).replace("T", " ");
}
